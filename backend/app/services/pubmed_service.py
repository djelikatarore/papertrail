import xml.etree.ElementTree as ET

import requests

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
REQUEST_TIMEOUT_SECONDS = 15


class PubmedSearchError(Exception):
    pass


def _build_term(topic: str, author: str | None) -> str:
    term = topic
    if author:
        term = f"{term} AND {author}[Author]"
    return term


def search_pubmed(
    topic: str,
    max_results: int = 5,
    author: str | None = None,
    date_from: int | None = None,
    date_to: int | None = None,
) -> list[dict]:
    """category is intentionally not supported — PubMed has no arXiv-style
    category taxonomy (it uses MeSH terms, a much larger and differently
    structured controlled vocabulary with no cs.CL/cs.CV equivalent). Unlike
    arXiv and CORE, PubMed's E-utilities correctly combine free-text search with
    a date range (mindate/maxdate) and an author ([Author] field) filter natively
    — no query-grouping bug observed, no post-fetch fallback needed here."""
    search_params = {
        "db": "pubmed",
        "term": _build_term(topic, author),
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    if date_from is not None or date_to is not None:
        search_params["datetype"] = "pdat"
        search_params["mindate"] = str(date_from or 1900)
        search_params["maxdate"] = str(date_to or 2100)

    try:
        search_response = requests.get(ESEARCH_URL, params=search_params, timeout=REQUEST_TIMEOUT_SECONDS)
        search_response.raise_for_status()
    except requests.RequestException as exc:
        raise PubmedSearchError(f"PubMed esearch request failed: {exc}") from exc

    try:
        pmids = search_response.json()["esearchresult"]["idlist"]
    except (ValueError, KeyError) as exc:
        raise PubmedSearchError(f"Failed to parse PubMed esearch response: {exc}") from exc

    if not pmids:
        return []

    try:
        fetch_response = requests.get(
            EFETCH_URL,
            params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        fetch_response.raise_for_status()
    except requests.RequestException as exc:
        raise PubmedSearchError(f"PubMed efetch request failed: {exc}") from exc

    try:
        root = ET.fromstring(fetch_response.content)
    except ET.ParseError as exc:
        raise PubmedSearchError(f"Failed to parse PubMed efetch response: {exc}") from exc

    results = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", default="")
        title = (article.findtext(".//ArticleTitle") or "").strip()
        abstract = " ".join(
            (node.text or "").strip() for node in article.findall(".//Abstract/AbstractText")
        ).strip()

        authors = []
        for author_el in article.findall(".//AuthorList/Author"):
            last_name = author_el.findtext("LastName", default="")
            fore_name = author_el.findtext("ForeName", default="")
            full_name = f"{fore_name} {last_name}".strip()
            if full_name:
                authors.append(full_name)

        year = article.findtext(".//JournalIssue/PubDate/Year") or article.findtext(".//ArticleDate/Year") or ""
        month = article.findtext(".//JournalIssue/PubDate/Month") or article.findtext(".//ArticleDate/Month") or ""
        day = article.findtext(".//JournalIssue/PubDate/Day") or article.findtext(".//ArticleDate/Day") or ""
        published_date = "-".join(part for part in [year, month, day] if part)

        results.append({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "pdf_link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            "published_date": published_date,
        })

    return results
