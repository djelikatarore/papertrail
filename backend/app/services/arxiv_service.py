import xml.etree.ElementTree as ET

import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
REQUEST_TIMEOUT_SECONDS = 10


class ArxivSearchError(Exception):
    pass


def _build_search_query(
    topic: str,
    category: str | None,
    author: str | None,
    date_from: int | None,
    date_to: int | None,
) -> str:
    filters = []
    if category:
        filters.append(f"cat:{category}")
    if author:
        filters.append(f'au:"{author}"')
    if date_from is not None or date_to is not None:
        start = f"{date_from or 1990}01010000"
        end = f"{date_to or 2100}12312359"
        filters.append(f"submittedDate:[{start} TO {end}]")

    if not filters:
        # No filters: keep the exact original unfiltered query untouched.
        return f"all:{topic}"

    # arXiv's query parser doesn't correctly scope a bare multi-word "all:" clause
    # when it's ANDed with other fielded terms (the words spill outside the
    # intended grouping and the AND is effectively ignored). Explicitly ANDing
    # each topic word inside parentheses keeps the topic match meaningful while
    # forcing correct grouping with the other filters.
    topic_words = topic.split()
    if len(topic_words) <= 1:
        topic_clause = f"all:{topic}"
    else:
        topic_clause = "(" + " AND ".join(f"all:{word}" for word in topic_words) + ")"

    return " AND ".join([topic_clause] + filters)


def search_arxiv(
    topic: str,
    max_results: int = 5,
    category: str | None = None,
    author: str | None = None,
    date_from: int | None = None,
    date_to: int | None = None,
) -> list[dict]:
    params = {
        "search_query": _build_search_query(topic, category, author, date_from, date_to),
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        response = requests.get(ARXIV_API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ArxivSearchError(f"arXiv API request failed: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise ArxivSearchError(f"Failed to parse arXiv API response: {exc}") from exc

    results = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = " ".join(entry.findtext("atom:title", default="", namespaces=ATOM_NS).split())
        abstract = " ".join(entry.findtext("atom:summary", default="", namespaces=ATOM_NS).split())
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NS).strip()
        authors = [
            author.findtext("atom:name", default="", namespaces=ATOM_NS).strip()
            for author in entry.findall("atom:author", ATOM_NS)
        ]

        pdf_link = None
        for link in entry.findall("atom:link", ATOM_NS):
            if link.get("title") == "pdf":
                pdf_link = link.get("href")
                break

        results.append({
            "title": title,
            "authors": [a for a in authors if a],
            "abstract": abstract,
            "pdf_link": pdf_link,
            "published_date": published,
        })

    return results
