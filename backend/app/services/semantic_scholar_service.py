import re
import threading
import time
from difflib import SequenceMatcher

import requests

from app.config.settings import SEMANTIC_SCHOLAR_API_KEY

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
REQUEST_TIMEOUT_SECONDS = 10
# Documented limit for this API key tier: 1 request/second. Enforced here
# with a lock + last-call timestamp rather than trusting callers to space
# calls out — paper_router.py schedules this via asyncio.to_thread, which
# runs on real OS threads, so a plain "don't call it too fast" convention
# wouldn't hold once two papers are being processed close together.
MIN_SECONDS_BETWEEN_REQUESTS = 1.0
# Same threshold already used by crossref_service.py for fuzzy title
# matching — kept consistent rather than picking a new number.
TITLE_MATCH_THRESHOLD = 0.75

_rate_limit_lock = threading.Lock()
_last_request_time = 0.0


class SemanticScholarLookupError(Exception):
    pass


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _wait_for_rate_limit() -> None:
    global _last_request_time
    with _rate_limit_lock:
        elapsed = time.monotonic() - _last_request_time
        remaining = MIN_SECONDS_BETWEEN_REQUESTS - elapsed
        if remaining > 0:
            time.sleep(remaining)
        _last_request_time = time.monotonic()


def get_citation_count(title: str) -> int | None:
    """Looks up a paper's real academic citation count via Semantic Scholar
    (built specifically for CS/ML literature, unlike CrossRef which relies on
    publisher-deposited reference lists and badly under-indexes preprints and
    conference papers — see crossref_service.py's docstring for the
    empirical evidence). Same contract as crossref_service.get_citation_count:
    searches by title, confirms the top result's title is actually a close
    match before trusting its count, and returns None (not raise) whenever no
    confident match is found — only a genuine request/parse failure raises
    SemanticScholarLookupError, which is what paper_router.py's CrossRef
    fallback reacts to."""
    if not title or not title.strip():
        return None

    _wait_for_rate_limit()

    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}
    params = {"query": title, "fields": "title,citationCount", "limit": 1}
    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SemanticScholarLookupError(f"Semantic Scholar API request failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise SemanticScholarLookupError(f"Failed to parse Semantic Scholar API response: {exc}") from exc

    items = data.get("data") or []
    if not items:
        return None

    matched_title = items[0].get("title")
    if not matched_title:
        return None

    similarity = SequenceMatcher(None, _normalize_title(title), _normalize_title(matched_title)).ratio()
    if similarity < TITLE_MATCH_THRESHOLD:
        return None

    return items[0].get("citationCount")
