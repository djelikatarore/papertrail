import re
from difflib import SequenceMatcher

import requests

CROSSREF_API_URL = "https://api.crossref.org/works"
REQUEST_TIMEOUT_SECONDS = 10
# Same threshold already used elsewhere in this codebase for fuzzy title
# matching (project_router.py's suggest-papers dedup, draft_generation_service.py's
# citation check) — kept consistent rather than picking a new number.
TITLE_MATCH_THRESHOLD = 0.75


class CrossrefLookupError(Exception):
    pass


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def get_citation_count(title: str) -> int | None:
    """Looks up a paper's real academic citation count via CrossRef
    (api.crossref.org/works, free, no API key), searching by title. CrossRef's
    bibliographic search is a ranked/fuzzy match, not an exact lookup — an
    unrelated top result is common for unusual or generic titles, so the top
    result's title is checked against ours before trusting its citation count.
    Returns None whenever no confident match is found (empty title, no
    results, or the top result doesn't actually match), rather than silently
    attaching a different paper's citation count to this one."""
    if not title or not title.strip():
        return None

    params = {"query.bibliographic": title, "rows": 1}
    try:
        response = requests.get(CROSSREF_API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CrossrefLookupError(f"CrossRef API request failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise CrossrefLookupError(f"Failed to parse CrossRef API response: {exc}") from exc

    items = data.get("message", {}).get("items", [])
    if not items:
        return None

    matched_titles = items[0].get("title") or []
    if not matched_titles:
        return None

    similarity = SequenceMatcher(None, _normalize_title(title), _normalize_title(matched_titles[0])).ratio()
    if similarity < TITLE_MATCH_THRESHOLD:
        return None

    return items[0].get("is-referenced-by-count")
