import xml.etree.ElementTree as ET

import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
REQUEST_TIMEOUT_SECONDS = 10


class ArxivSearchError(Exception):
    pass


def search_arxiv(topic: str, max_results: int = 5) -> list[dict]:
    params = {
        "search_query": f"all:{topic}",
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
