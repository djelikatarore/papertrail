import requests

from app.config.settings import CORE_API_KEY

CORE_API_URL = "https://api.core.ac.uk/v3/search/works/"
# CORE's API has been observed to take 15-25s+ to respond, and response time
# scales with the requested `limit` — unlike arXiv, which is consistently fast
# regardless of result count. A short timeout caused spurious failures during
# testing, and a large over-fetch multiplier alone pushed past 25s.
REQUEST_TIMEOUT_SECONDS = 30


class CoreSearchError(Exception):
    pass


def search_core(
    topic: str,
    max_results: int = 5,
    author: str | None = None,
    date_from: int | None = None,
    date_to: int | None = None,
) -> list[dict]:
    """category is intentionally not supported here — CORE has no arXiv-style
    category taxonomy (cs.CL, cs.CV, ...), so there's nothing meaningful to map it
    to. date_from/date_to and author are applied as POST-FETCH filtering rather
    than in the query string: empirically, CORE's query parser silently drops the
    free-text topic's relevance ranking whenever it's ANDed with an additional
    field filter (verified with both a two-sided yearPublished range and an
    authors: clause — both caused totally irrelevant results to dominate, e.g.
    electrical "power transformer" papers for a "transformer language models"
    search). Fetches a larger pool when filters are active so enough candidates
    remain after filtering. The multiplier is kept modest (2x, not 4x) because
    CORE's response time grows with the requested limit — a larger over-fetch
    risks timing out instead of just returning fewer post-filter results."""
    fetch_count = max_results * 2 if (author or date_from or date_to) else max_results

    headers = {"Authorization": f"Bearer {CORE_API_KEY}"}
    params = {"q": topic, "limit": min(fetch_count, 100)}

    try:
        response = requests.get(CORE_API_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CoreSearchError(f"CORE API request failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise CoreSearchError(f"Failed to parse CORE API response: {exc}") from exc

    results = []
    for item in data.get("results", []):
        year = item.get("yearPublished")
        if date_from is not None and (not year or year < date_from):
            continue
        if date_to is not None and (not year or year > date_to):
            continue

        authors = [a["name"].strip() for a in item.get("authors", []) if a.get("name")]
        if author and not any(author.lower() in a.lower() for a in authors):
            continue

        results.append({
            "title": (item.get("title") or "").strip(),
            "authors": authors,
            "abstract": (item.get("abstract") or "").strip(),
            "pdf_link": item.get("downloadUrl"),
            "published_date": item.get("publishedDate") or (str(year) if year else ""),
        })

        if len(results) >= max_results:
            break

    return results
