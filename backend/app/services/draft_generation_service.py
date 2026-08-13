import re
from difflib import SequenceMatcher

from app.services.llm_service import call_llm
from app.utils.logging_utils import safe_log

CITATION_MATCH_THRESHOLD = 0.75

DOCUMENT_TYPE_LABELS = {
    "LITERATURE_REVIEW": "Literature Review",
    "RESEARCH_PROPOSAL": "Research Proposal",
    "THESIS_CHAPTER": "Thesis Chapter",
    "CONFERENCE_PAPER": "Conference Paper",
    "OTHER": "Document",
}

# Only the LITERATURE_REVIEW structure was explicitly specified by the user; the
# others are a reasonable default pending confirmation.
DOCUMENT_TYPE_STRUCTURES = {
    "LITERATURE_REVIEW": ["Introduction", "Thematic Synthesis", "Conclusion"],
    "RESEARCH_PROPOSAL": ["Introduction", "Related Work", "Proposed Approach", "Conclusion"],
    "THESIS_CHAPTER": ["Introduction", "Literature Synthesis", "Discussion", "Conclusion"],
    "CONFERENCE_PAPER": ["Introduction", "Related Work", "Discussion", "Conclusion"],
    "OTHER": ["Introduction", "Body", "Conclusion"],
}

# Section names alone ("Proposed Approach" vs "Thematic Synthesis") aren't a
# strong enough signal on their own for every document type to come out
# genuinely distinct — this spells out the actual purpose/register difference
# so the model doesn't default to literature-review-style synthesis under a
# differently-named section header.
DOCUMENT_TYPE_GUIDANCE = {
    "LITERATURE_REVIEW": (
        "This is a retrospective synthesis of existing work: compare, contrast, and critically "
        "evaluate what the source papers found. Do not propose new research, new methods, or "
        "future experiments — stay strictly within describing and analyzing what already exists."
    ),
    "RESEARCH_PROPOSAL": (
        "This is a forward-looking proposal for NEW research the author intends to carry out — not "
        "a summary of the source papers. The 'Related Work' section situates the gap; the "
        "'Proposed Approach' section MUST describe original work that goes beyond the source papers "
        "(new methods, experiments, or extensions), written with forward-looking language ('we will', "
        "'this study proposes', 'we plan to'). It should build on a limitation or open question found "
        "in the source papers rather than re-describing what those papers already did."
    ),
    "THESIS_CHAPTER": (
        "This is one chapter within a larger academic thesis. After synthesizing the literature, the "
        "Discussion section should critically analyze its implications for the thesis's own research "
        "question, in a more exploratory and reflective register than a standalone literature review."
    ),
    "CONFERENCE_PAPER": (
        "This is a short, focused paper for a conference audience. Be concise, and emphasize the "
        "significance and novelty of the findings rather than exhaustively covering every detail."
    ),
    "OTHER": "Write a clear, well-structured academic document.",
}

DRAFT_SYSTEM_PROMPT = (
    "You are an academic writing assistant. Base your writing ONLY on the provided "
    "paper summaries. Never invent information not present in them. Every factual "
    "claim about a specific paper's contribution, method, results, or limitations "
    "must be immediately followed by a citation."
)


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _build_draft_prompt(document_type: str, papers: list[dict]) -> str:
    sections = DOCUMENT_TYPE_STRUCTURES.get(document_type, DOCUMENT_TYPE_STRUCTURES["OTHER"])
    label = DOCUMENT_TYPE_LABELS.get(document_type, "Document")
    guidance = DOCUMENT_TYPE_GUIDANCE.get(document_type, DOCUMENT_TYPE_GUIDANCE["OTHER"])

    papers_text = "\n\n".join(
        f"=== Paper: {p['title']} ===\n"
        f"Contribution: {p['contribution'] or 'Not available'}\n"
        f"Methodology: {p['methodology'] or 'Not available'}\n"
        f"Key Results: {p['key_results'] or 'Not available'}\n"
        f"Limitations: {p['limitations'] or 'Not available'}\n"
        f"Keywords: {p['keywords'] or 'Not available'}"
        for p in papers
    )

    return (
        f"Write a {label} structured into these sections, in this order: {', '.join(sections)}.\n"
        f"{guidance}\n"
        "Use Markdown section headers (## Section Name) for each section.\n\n"
        "Base your writing ONLY on the paper summaries below. Never invent information "
        "not present in them.\n"
        "Do not reference, cite, or describe any paper, author, or prior work other than the ones "
        "listed below — if the source summaries don't cover something, do not fill the gap with "
        "outside knowledge or invented citations (e.g. 'Smith et al., 2020').\n"
        "Every factual claim about a specific paper's contribution, method, results, or "
        "limitations MUST be immediately followed by a citation in the exact format "
        "(Paper: <exact paper title>), using the paper titles exactly as given below.\n\n"
        "--- PAPER SUMMARIES ---\n"
        f"{papers_text}"
    )


def _extract_citations(text: str) -> list[str]:
    return re.findall(r"\(Paper:\s*([^)]+)\)", text)


def _citation_matches_known_paper(cited_title: str, known_titles: list[str]) -> bool:
    normalized_cited = _normalize_title(cited_title)
    for title in known_titles:
        if SequenceMatcher(None, normalized_cited, _normalize_title(title)).ratio() >= CITATION_MATCH_THRESHOLD:
            return True
    return False


async def generate_draft_content(document_type: str, papers: list[dict]) -> tuple[str | None, bool, str | None]:
    """Returns (content, success, error). Requires at least one citation overall
    (evidence the draft actually engaged with the source papers) and every citation
    found must match one of the given papers' titles — an unrecognized citation
    means the model referenced a paper it wasn't given, so the whole draft is
    discarded rather than shown with an unverifiable claim in it."""
    prompt = _build_draft_prompt(document_type, papers)
    content = await call_llm(prompt, system_prompt=DRAFT_SYSTEM_PROMPT)

    known_titles = [p["title"] for p in papers]
    citations = _extract_citations(content)

    if not citations:
        safe_log("[draft_generation_service] Generated draft contained no citations at all")
        return None, False, "The generated draft did not cite any of the selected papers."

    for cited_title in citations:
        if not _citation_matches_known_paper(cited_title, known_titles):
            safe_log(f"[draft_generation_service] Rejected draft citing unrecognized paper: {cited_title!r}")
            return None, False, f"The generated draft cited a paper that wasn't in the selection: '{cited_title}'."

    return content, True, None
