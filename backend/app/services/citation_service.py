import asyncio

from app.services.crossref_service import CrossrefLookupError
from app.services.crossref_service import get_citation_count as get_crossref_citation_count
from app.services.semantic_scholar_service import SemanticScholarLookupError
from app.services.semantic_scholar_service import get_citation_count as get_semantic_scholar_citation_count
from app.utils.logging_utils import safe_log

SOURCE_SEMANTIC_SCHOLAR = "semantic_scholar"
SOURCE_CROSSREF = "crossref"


async def get_citation_count(title: str) -> tuple[int | None, str | None]:
    """Semantic Scholar first — built specifically for CS/ML literature, unlike
    CrossRef which relies on publisher-deposited reference lists and badly
    under-indexes preprints and conference papers (empirically confirmed: see
    crossref_service.py's docstring). Falls back to CrossRef only when
    Semantic Scholar itself fails (network/API error, e.g. rate limit) for
    this specific paper — same pattern as the dual Groq key fallback in
    llm_service.py. A clean None from Semantic Scholar (no confident match)
    is trusted as-is and NOT retried against CrossRef, since CrossRef would
    likely either also find nothing or — worse — attach a wrong paper's
    count (already observed for "Attention Is All You Need").

    Returns (count, source) — source tells the caller which provider the
    count (or the None) actually came from, so a later re-check can avoid
    letting a CrossRef result silently overwrite a Semantic Scholar one (see
    should_replace_citation below). A brand new paper being looked up for the
    first time doesn't need this — it always starts from (None, None) and
    trivially accepts whatever this returns.

    Shared by paper_router.py's background processing and
    scripts/backfill_citation_counts.py so both go through the exact same
    fallback logic rather than each having their own copy."""
    try:
        count = await asyncio.to_thread(get_semantic_scholar_citation_count, title)
        return count, SOURCE_SEMANTIC_SCHOLAR
    except SemanticScholarLookupError as exc:
        safe_log(f"[semantic_scholar_service] Lookup failed for {title!r}, falling back to CrossRef: {exc}")
        count = await asyncio.to_thread(get_crossref_citation_count, title)
        return count, SOURCE_CROSSREF


def should_replace_citation(
    old_count: int | None, old_source: str | None, new_count: int | None, new_source: str | None
) -> bool:
    """Decides whether a fresh lookup result should overwrite what's already
    stored — only relevant when re-checking a paper that already has a
    citation_count (scripts/backfill_citation_counts.py); a brand new paper
    always starts from (None, None) and trivially accepts the first result.

    Two failure modes observed in practice, both guarded against here:
    - A rate-limited Semantic Scholar attempt falling back to CrossRef
      finding nothing wiped out an already-known count with None.
    - The same fallback finding a different, unrelated paper's (much lower)
      count overwrote a correct, previously-recorded Semantic Scholar count.
    """
    if new_count is None and old_count is not None:
        return False
    if new_source == SOURCE_CROSSREF and old_source == SOURCE_SEMANTIC_SCHOLAR:
        return False
    return True
