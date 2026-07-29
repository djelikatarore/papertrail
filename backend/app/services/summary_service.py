import re

from app.services.llm_service import call_llm
from app.utils.logging_utils import safe_log

SUMMARY_SYSTEM_PROMPT = (
    "You are an academic paper summarization assistant. Base your summary ONLY on "
    "the provided text. Never invent information that is not present in the text."
)

SUMMARY_FIELDS = ["CONTRIBUTION", "METHODOLOGY", "KEY_RESULTS", "LIMITATIONS"]

# Sections most relevant to a Contribution/Methodology/Results/Limitations summary,
# in priority order. Anything not listed here (Background, References, Acknowledgements,
# fallback "Chunk N" pieces...) is sent last and is the first to be cut off.
PRIORITY_SECTIONS = [
    "abstract", "introduction", "method", "methods", "methodology",
    "materials and methods", "experiments", "experiment", "experimental setup",
    "results", "discussion", "conclusion", "conclusions", "limitations",
]

# Groq's free tier caps requests at 8000 tokens/minute. At ~4 chars/token, 16000
# characters of paper text (plus prompt overhead) stays comfortably under that limit.
MAX_PROMPT_CHARS = 16000


def _prioritize_and_truncate(chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    def priority(item: tuple[str, str]) -> int:
        try:
            return PRIORITY_SECTIONS.index(item[0].lower())
        except ValueError:
            return len(PRIORITY_SECTIONS)

    ordered = sorted(chunks, key=priority)

    selected = []
    total_chars = 0
    for name, text in ordered:
        remaining = MAX_PROMPT_CHARS - total_chars
        if remaining <= 0:
            break
        selected.append((name, text[:remaining]))
        total_chars += len(text[:remaining])

    return selected


def _build_prompt(selected_chunks: list[tuple[str, str]]) -> str:
    labeled_text = "\n\n".join(f"[Section: {name}]\n{text}" for name, text in selected_chunks)
    return (
        "Summarize the following academic paper into exactly four blocks: "
        "Contribution, Methodology, Key Results, Limitations.\n"
        "For each block, write 1-3 concise sentences and explicitly cite the section(s) "
        "you drew the information from, in the format (Source: <section name>).\n"
        "If a block cannot be determined from the text, write exactly: "
        "Not clearly stated in the paper (Source: none)\n\n"
        "Respond strictly in this format, with no extra commentary:\n"
        "CONTRIBUTION: <text> (Source: <section>)\n"
        "METHODOLOGY: <text> (Source: <section>)\n"
        "KEY_RESULTS: <text> (Source: <section>)\n"
        "LIMITATIONS: <text> (Source: <section>)\n\n"
        "--- PAPER TEXT (chunked by section) ---\n"
        f"{labeled_text}"
    )


def _extract_citation(text: str) -> list[str] | None:
    match = re.search(r"\(Source:\s*([^)]+)\)", text)
    if not match:
        return None
    return [s.strip().lower() for s in match.group(1).split(",")]


def _verify_citation(text: str, chunk_labels: set[str], source_text_lower: str) -> bool:
    """Anti-hallucination check: a block is only trusted if it either explicitly
    states the info wasn't found (Source: none), or cites a section name that
    genuinely appears in the text sent to the model — either as one of our chunk
    labels (Abstract, Results...) or as a literal subsection title within the
    source text itself (e.g. "Model Architecture", "Model Variations"). A citation
    to a name that appears nowhere in the source text is treated as fabricated.
    """
    cited = _extract_citation(text)
    if cited is None:
        return False
    if cited == ["none"]:
        return True

    for section in cited:
        if section in chunk_labels:
            continue
        if re.search(r"\b" + re.escape(section) + r"\b", source_text_lower):
            continue
        return False
    return True


async def generate_summary(chunks: list[tuple[str, str]]) -> tuple[dict[str, str | None], list[str]]:
    selected_chunks = _prioritize_and_truncate(chunks)
    chunk_labels = {name.lower() for name, _ in selected_chunks}
    source_text_lower = "\n\n".join(text for _, text in selected_chunks).lower()

    prompt = _build_prompt(selected_chunks)
    response = await call_llm(prompt, system_prompt=SUMMARY_SYSTEM_PROMPT)

    result: dict[str, str | None] = {field.lower(): None for field in SUMMARY_FIELDS}
    flagged_fields: list[str] = []

    for i, field in enumerate(SUMMARY_FIELDS):
        next_field = SUMMARY_FIELDS[i + 1] if i + 1 < len(SUMMARY_FIELDS) else None
        pattern = rf"{field}:\s*(.*?)(?=\n{next_field}:|\Z)" if next_field else rf"{field}:\s*(.*)"
        match = re.search(pattern, response, re.DOTALL)
        if not match:
            continue

        block_text = match.group(1).strip()
        if _verify_citation(block_text, chunk_labels, source_text_lower):
            result[field.lower()] = block_text
        else:
            flagged_fields.append(field.lower())
            safe_log(f"[summary_service] Rejected ungrounded {field} claim: {block_text!r}")

    return result, flagged_fields
