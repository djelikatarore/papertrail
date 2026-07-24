import re

from app.services.llm_service import call_llm
from app.services.summary_service import _prioritize_and_truncate

PAPER_TYPE_SYSTEM_PROMPT = (
    "You are an assistant that classifies documents. Base your answer ONLY on the provided text."
)

ACADEMIC_PAPER_TYPES = [
    "Research Article",
    "Review Article",
    "Systematic Review",
    "Case Study",
    "Conference Paper",
    "Thesis or Dissertation",
    "Technical Report",
]

NOT_ACADEMIC_LABEL = "Not an academic paper"

CONTENT_WARNING_MESSAGE = (
    "Ce document ne ressemble pas à un article académique — les résumés/mots-clés "
    "générés peuvent être peu pertinents."
)


def _build_prompt(selected_chunks: list[tuple[str, str]]) -> str:
    labeled_text = "\n\n".join(f"[Section: {name}]\n{text}" for name, text in selected_chunks)
    types_list = ", ".join(ACADEMIC_PAPER_TYPES)
    return (
        "Determine whether the following document is a genuine academic paper "
        "(e.g. a research article, review, case study, thesis, technical report, "
        "conference paper) or NOT an academic paper at all (e.g. an invoice, a resume/CV, "
        "an administrative form, a letter, a slide deck, etc.).\n\n"
        f"If it IS an academic paper, classify it into exactly one of: {types_list}.\n"
        f"If it is NOT an academic paper, respond with exactly: {NOT_ACADEMIC_LABEL}\n\n"
        "Respond strictly in this format, with no extra commentary:\n"
        "PAPER_TYPE: <one of the categories above>\n\n"
        "--- DOCUMENT TEXT (chunked by section) ---\n"
        f"{labeled_text}"
    )


def detect_paper_type(chunks: list[tuple[str, str]]) -> tuple[str, str | None]:
    """Classifies the document in a single LLM call. Returns (detected_paper_type,
    content_warning) — content_warning is None for genuine academic papers, and a
    user-facing caution message when the document doesn't appear to be one at all
    (the upload itself is never rejected, this is advisory only)."""
    selected_chunks = _prioritize_and_truncate(chunks)
    prompt = _build_prompt(selected_chunks)
    response = call_llm(prompt, system_prompt=PAPER_TYPE_SYSTEM_PROMPT)

    match = re.search(r"PAPER_TYPE:\s*(.+)", response)
    detected_type = match.group(1).strip() if match else NOT_ACADEMIC_LABEL

    is_recognized_academic_type = any(
        detected_type.lower() == t.lower() for t in ACADEMIC_PAPER_TYPES
    )
    if not is_recognized_academic_type:
        return NOT_ACADEMIC_LABEL, CONTENT_WARNING_MESSAGE

    return detected_type, None
