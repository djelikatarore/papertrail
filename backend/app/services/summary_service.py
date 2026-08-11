import re

from app.services.llm_service import call_llm
from app.utils.logging_utils import safe_log

SUMMARY_SYSTEM_PROMPT = (
    "You are an academic paper summarization assistant. Base your summary ONLY on "
    "the provided text. Never invent information that is not present in the text."
)

SUMMARY_FIELDS = ["CONTRIBUTION", "METHODOLOGY", "KEY_RESULTS", "LIMITATIONS"]

# The model's own explicit "nothing here" answer (see _build_prompt below) —
# a real, non-empty string, so a backfill script's "don't overwrite existing
# content with an empty result" guard has to check for this specifically, not
# just falsiness. Confirmed happening in practice: a backfill regenerated
# paper 88's key_results as this placeholder, silently overwriting 1093 chars
# of real, previously-verified content, because the guard only checked
# `if new_value:` and this string is truthy.
NOT_FOUND_PLACEHOLDER = "Not clearly stated in the paper (Source: none)"


def is_real_summary_content(value: str | None) -> bool:
    """True only for an actual generated claim — False for both empty/None
    and the model's own explicit "not found" placeholder. Use this (not a
    plain truthiness check) anywhere a regenerated field is being compared
    against what's already stored, so a placeholder can never look like an
    improvement over real content."""
    return bool(value) and value.strip() != NOT_FOUND_PLACEHOLDER

# This line replaces the generic length instruction below — putting the
# per-type steering directly in the sentence-count instruction the model
# anchors on, rather than as a secondary note, since a secondary "also
# prioritize X" note was too easy for the model to acknowledge without
# actually changing length/content (confirmed by testing: RAPID summaries
# came back nearly as long as SYSTEMATIC ones before this change).
# NARRATIVE (and any unrecognized/None review_type) keeps the original
# baseline line, updated 2026-08-07 from "1-3 concise sentences" to
# "8-12 substantial sentences" — 1-3 sentences per block turned out to be too
# short to be useful for a multi-page paper without re-reading it; each block
# now targets a real paragraph or two of technical substance instead of a
# superficial one-liner.
DEFAULT_LENGTH_INSTRUCTION = (
    "For each block, write 8-12 substantial sentences (roughly one to two "
    "well-developed paragraphs) covering enough technical substance that a "
    "reader would not need to re-read the paper to understand this aspect of it"
)
REVIEW_TYPE_LENGTH_INSTRUCTIONS = {
    "SYSTEMATIC": (
        "For each block, write 10-14 substantial sentences, prioritizing exact "
        "figures, statistics, and quantitative results, and describing the "
        "methodology in detail (sample sizes, procedures, metrics)"
    ),
    "SCOPING": (
        "For each block, write 8-12 substantial sentences, prioritizing a broad "
        "overview of how this paper fits into the wider research landscape and "
        "its general themes rather than granular numeric detail"
    ),
    "CRITICAL": (
        "For each block, write 8-12 substantial sentences, prioritizing critical "
        "analysis — emphasize limitations, potential biases, and methodological "
        "weaknesses, even beyond what is listed in a dedicated Limitations section"
    ),
    "RAPID": (
        "For each block, write 3-5 concise sentences covering only the essential "
        "points — noticeably shorter than a standard summary, omitting secondary detail"
    ),
}

# Sections most relevant to a Contribution/Methodology/Results/Limitations summary,
# in priority order. Anything not listed here (Background, References, Acknowledgements,
# fallback "Chunk N" pieces...) is sent last and is the first to be cut off.
PRIORITY_SECTIONS = [
    "abstract", "introduction", "method", "methods", "methodology",
    "materials and methods", "experiments", "experiment", "experimental setup",
    "results", "discussion", "conclusion", "conclusions", "limitations",
]

# Groq's free tier caps a single request (input + MAX_COMPLETION_TOKENS
# combined) at 8000 tokens. 16000 assumed ~4 chars/token, which held for most
# papers but not all — confirmed in practice on BERT: 16000 chars of paper
# text + prompt instructions measured 17718 total chars, and the resulting
# 413 ("Requested 8082, Limit 8000") implies only ~3.49 chars/token for that
# paper's dense technical prose. 12000 leaves enough margin to stay under the
# combined limit even at that measured worst-case density, without touching
# MAX_COMPLETION_TOKENS (reducing that instead would reintroduce the
# mid-sentence output truncation this project already fixed once — see
# llm_service.py).
MAX_PROMPT_CHARS = 12000


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


def _build_prompt(selected_chunks: list[tuple[str, str]], review_type: str | None = None) -> str:
    labeled_text = "\n\n".join(f"[Section: {name}]\n{text}" for name, text in selected_chunks)
    length_instruction = REVIEW_TYPE_LENGTH_INSTRUCTIONS.get(review_type or "", DEFAULT_LENGTH_INSTRUCTION)
    return (
        "Summarize the following academic paper into exactly four blocks: "
        "Contribution, Methodology, Key Results, Limitations.\n"
        f"{length_instruction}. Write in a formal academic register with the "
        "technical precision expected of a graduate-level research summary — "
        "name the specific methods, datasets, metrics, and figures given in the "
        "text rather than vague paraphrase. For Key Results especially, use "
        "short itemized sub-points (e.g. \"- <finding>\") when the paper reports "
        "multiple distinct findings, instead of forcing them into a single "
        "run-on sentence.\n"
        "Cite the section each claim is drawn from inline, in the format "
        "(Source: <section name>) — a block may include more than one such tag "
        "if it draws on multiple sections. Writing in more detail must never "
        "mean adding claims, numbers, or interpretations that are not "
        "explicitly present in the provided text.\n"
        "If a block cannot be determined from the text, write exactly: "
        f"{NOT_FOUND_PLACEHOLDER}\n\n"
        "Respond strictly in this format, with no extra commentary and no "
        "markdown formatting (no **bold**, no headers, no numbering) around "
        "the block labels themselves:\n"
        "CONTRIBUTION: <text> (Source: <section>)\n"
        "METHODOLOGY: <text> (Source: <section>)\n"
        "KEY_RESULTS: <text> (Source: <section>)\n"
        "LIMITATIONS: <text> (Source: <section>)\n\n"
        "--- PAPER TEXT (chunked by section) ---\n"
        f"{labeled_text}"
    )


def _field_pattern(field: str) -> str:
    """Matches a block label even when the model wraps it in markdown
    (**CONTRIBUTION:**, **CONTRIBUTION**:, ### CONTRIBUTION:) instead of the
    plain format requested in the prompt — confirmed happening in practice.
    Without this, a wrapped label doesn't match the exact "FIELD:" boundary
    the block-splitting regex below looks for, so one block's (non-greedy)
    capture never finds where it's supposed to stop and swallows every
    following block instead of just its own text."""
    return rf"[#\s]*\**\s*{field}\s*\**:\**"


def _split_cited_sections(raw: str) -> list[str]:
    """A (Source: ...) tag listing multiple sections is comma-separated per
    the prompt's instructions, but the model sometimes uses a semicolon
    instead (observed: "(Source: Results; English Constituency Parsing)") —
    splitting on comma alone left the whole "results; english constituency
    parsing" string treated as one section name, which of course never
    matches anything and wrongly fails an otherwise well-grounded claim."""
    return [s.strip().lower() for s in re.split(r"[,;]", raw)]


def _extract_citation(text: str) -> list[str] | None:
    """First (Source: ...) tag only — kept as-is for qa_service.py, which
    grounds a single answer with exactly one trailing citation and needs the
    flat list this returns (not the list-of-lists _extract_citations below)."""
    match = re.search(r"\(Source:\s*([^)]+)\)", text)
    if not match:
        return None
    return _split_cited_sections(match.group(1))


_SECTION_REFERENCE_PATTERN = re.compile(r"^(table|figure|section|equation|algorithm|appendix)\s*[\divxlc]*$", re.IGNORECASE)
# A bare parenthetical is worth checking as a citation attempt if it reads
# like a section/subsection title (letters, spaces, and title-ish punctuation
# only) — covers real cases like "(Clipped Surrogate Objective)" or
# "(Adaptive KL Penalty Coefficient)" that are too specific to be a known
# chunk_label but are still a genuine (if unlabeled) reference to a real
# subsection. Deliberately excludes anything containing a digit or symbol
# outside title punctuation, so incidental asides — "(2019)", "(p < 0.05)",
# "(38% reduction)" — are never nonsensically treated as a section name in
# the first place (the risk being: extracting a non-citation aside as a
# "citation" would fail verification and wrongly reject an otherwise
# well-grounded block, the opposite of what this tolerance is for).
_TITLE_LIKE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z\s\-:;,']{1,80}$")


def _extract_citations(text: str, chunk_labels: set[str] | None = None) -> list[list[str]]:
    """Every citation tag found in a block, not just the first. Blocks are
    now 8-12+ sentences and explicitly allowed to cite more than one section
    (see _build_prompt) — checking only the first tag, as before, would leave
    every claim after it unverified.

    The prompt asks for "(Source: <section>)", and most of the time that's
    exactly what comes back — but confirmed in practice across several real
    papers (RoBERTa, PPO, Sparse Attention...) the model sometimes drifts to
    "(Table 1, Source: Results)" (extra text before "Source:", same parens)
    or drops the "Source:" prefix entirely, e.g. "(Introduction)" or
    "(Clipped Surrogate Objective)". Both are accepted here — the underlying
    fact-check in _verify_citation is unchanged and just as strict; this only
    widens what counts as a citation *attempt* worth checking:
      1. "Source:" anywhere inside the parens -> take everything after it.
      2. No "Source:" at all -> only treated as a citation if the bare
         parenthetical is a known chunk label, a "Table/Figure/Section N"
         reference, or otherwise reads like a section/subsection title
         (_TITLE_LIKE_PATTERN) — not any parenthetical, so a numeric or
         symbol-bearing aside is correctly left alone rather than
         nonsensically checked as a "section name"."""
    chunk_labels = chunk_labels or set()
    citations = []
    for paren_match in re.finditer(r"\(([^)]+)\)", text):
        content = paren_match.group(1)
        source_match = re.search(r"Source:\s*(.+)", content, re.IGNORECASE)
        if source_match:
            citations.append(_split_cited_sections(source_match.group(1)))
            continue

        candidate = content.strip()
        normalized_candidate = _normalize_for_matching(candidate).lower()
        is_plausible_reference = (
            normalized_candidate in chunk_labels
            or _SECTION_REFERENCE_PATTERN.match(candidate)
            or _TITLE_LIKE_PATTERN.match(candidate)
        )
        if is_plausible_reference:
            citations.append(_split_cited_sections(candidate))

    return citations


# The model's own prose regularly uses typographic Unicode punctuation
# (non-breaking/narrow spaces, non-breaking hyphens, en/em dashes) inside a
# citation's section name — e.g. "Table 3" — that never appears in the
# plain-ASCII text extracted from the PDF. A citation that's semantically
# correct then fails a byte-exact match purely on punctuation, wrongly
# rejecting an otherwise well-grounded block. This is the same root cause
# already found and fixed for feedback_service.py's citation check
# (difflib-based there); here a direct character normalization is enough
# since section names are short and don't need fuzzy-ratio matching.
_UNICODE_PUNCTUATION_NORMALIZATIONS = str.maketrans({
    " ": " ", " ": " ",  # non-breaking / narrow no-break space
    "‑": "-", "–": "-", "—": "-",  # non-breaking hyphen, en dash, em dash
    "‘": "'", "’": "'", "“": '"', "”": '"',  # curly quotes
})


def _normalize_for_matching(text: str) -> str:
    return text.translate(_UNICODE_PUNCTUATION_NORMALIZATIONS)


def _verify_citation(text: str, chunk_labels: set[str], source_text_lower: str) -> bool:
    """Anti-hallucination check: a block is only trusted if EVERY (Source: ...)
    tag within it either explicitly states the info wasn't found (Source:
    none), or cites a section name that genuinely appears in the text sent to
    the model — either as one of our chunk labels (Abstract, Results...) or as
    a literal subsection title within the source text itself (e.g. "Model
    Architecture", "Model Variations"). A block with no citation tag at all is
    rejected outright; a block with several tags is rejected if even one of
    them cites a name that appears nowhere in the source text — writing more
    is never allowed to dilute how strictly each individual claim is checked.
    """
    citations = _extract_citations(text, chunk_labels)
    if not citations:
        return False

    normalized_source_text = _normalize_for_matching(source_text_lower)

    for cited in citations:
        if cited == ["none"]:
            continue
        for section in cited:
            normalized_section = _normalize_for_matching(section)
            if section in chunk_labels or normalized_section in chunk_labels:
                continue
            if re.search(r"\b" + re.escape(normalized_section) + r"\b", normalized_source_text):
                continue
            return False
    return True


async def generate_summary(
    chunks: list[tuple[str, str]], review_type: str | None = None
) -> tuple[dict[str, str | None], list[str]]:
    selected_chunks = _prioritize_and_truncate(chunks)
    chunk_labels = {name.lower() for name, _ in selected_chunks}
    source_text_lower = "\n\n".join(text for _, text in selected_chunks).lower()

    prompt = _build_prompt(selected_chunks, review_type)
    response = await call_llm(prompt, system_prompt=SUMMARY_SYSTEM_PROMPT)

    result: dict[str, str | None] = {field.lower(): None for field in SUMMARY_FIELDS}
    flagged_fields: list[str] = []

    for i, field in enumerate(SUMMARY_FIELDS):
        next_field = SUMMARY_FIELDS[i + 1] if i + 1 < len(SUMMARY_FIELDS) else None
        pattern = (
            rf"{_field_pattern(field)}\s*(.*?)(?=\n{_field_pattern(next_field)}|\Z)"
            if next_field
            else rf"{_field_pattern(field)}\s*(.*)"
        )
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
