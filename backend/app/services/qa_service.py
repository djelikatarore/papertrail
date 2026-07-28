import json
import re

from sqlalchemy.orm import Session

from app.models.models import TextBlock
from app.services.embedding_service import cosine_similarity, get_embedding
from app.services.llm_service import call_llm
from app.services.summary_service import _extract_citation, _verify_citation
from app.utils.logging_utils import safe_log

TOP_K_CHUNKS = 3

QA_SYSTEM_PROMPT = (
    "You are an assistant that answers questions about an academic paper. Base your "
    "answer ONLY on the provided excerpts. Never invent information not present in them."
)


def retrieve_relevant_chunks(question: str, paper_id: int, db: Session, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    """Embeds the question and ranks the paper's TextBlocks by cosine similarity.
    Chunk embeddings are precomputed at upload time (TextBlock.embedding) rather
    than recomputed on every question, to keep per-question latency low."""
    question_embedding = get_embedding(question)

    chunks = db.query(TextBlock).filter(TextBlock.paper_id == paper_id, TextBlock.embedding.isnot(None)).all()

    scored = [
        {
            "section_reference": chunk.section_reference,
            "text": chunk.text,
            "score": cosine_similarity(question_embedding, json.loads(chunk.embedding)),
        }
        for chunk in chunks
    ]
    scored.sort(key=lambda c: c["score"], reverse=True)

    return scored[:top_k]


def retrieve_relevant_chunks_multi(
    question: str, paper_ids: list[int], db: Session, top_k: int = TOP_K_CHUNKS
) -> dict[int, list[dict]]:
    """Retrieves the top-k relevant chunks independently for each paper, keyed by
    paper_id. Kept independent per paper (rather than pooling all chunks together
    and taking a global top-k) so that every paper gets a chance to contribute its
    own best-matching content to a comparative answer, instead of one paper with
    generally higher-scoring chunks crowding out the others."""
    return {paper_id: retrieve_relevant_chunks(question, paper_id, db, top_k) for paper_id in paper_ids}


def _build_qa_prompt(question: str, chunks: list[dict]) -> str:
    labeled_text = "\n\n".join(f"[Section: {c['section_reference']}]\n{c['text']}" for c in chunks)
    return (
        f"Answer the following question using ONLY the excerpts below.\n"
        f"Question: {question}\n\n"
        "Respond in exactly this format, with no extra commentary:\n"
        "ANSWER: <your answer> (Source: <section name>)\n\n"
        "If the excerpts don't contain enough information to answer the question, write exactly:\n"
        "ANSWER: Not enough information in the provided excerpts to answer this question (Source: none)\n\n"
        "--- EXCERPTS ---\n"
        f"{labeled_text}"
    )


def generate_grounded_answer(question: str, chunks: list[dict]) -> tuple[str | None, str | None, bool]:
    """Returns (answer, cited_section, refused). Reuses the same anti-hallucination
    citation check as summary_service: a cited section is only trusted if it's one
    of our known chunk labels or appears literally in the excerpt text sent to the
    model. An unverifiable citation (or no citation at all) means the answer is
    discarded and refused=True, rather than shown to the user untrusted."""
    chunk_labels = {c["section_reference"].lower() for c in chunks if c["section_reference"]}
    source_text_lower = "\n\n".join(c["text"] for c in chunks).lower()

    prompt = _build_qa_prompt(question, chunks)
    response = call_llm(prompt, system_prompt=QA_SYSTEM_PROMPT)

    match = re.search(r"ANSWER:\s*(.*)", response, re.DOTALL)
    if not match:
        safe_log(f"[qa_service] Could not parse ANSWER block from LLM response: {response!r}")
        return None, None, True

    block_text = match.group(1).strip()
    if not _verify_citation(block_text, chunk_labels, source_text_lower):
        safe_log(f"[qa_service] Rejected ungrounded answer: {block_text!r}")
        return None, None, True

    cited = _extract_citation(block_text)
    answer_text = re.sub(r"\s*\(Source:[^)]*\)\s*$", "", block_text).strip()
    cited_section = None if cited == ["none"] else ", ".join(cited)

    return answer_text, cited_section, False


COMPARATIVE_QA_SYSTEM_PROMPT = (
    "You are an assistant that answers questions by comparing multiple academic papers. "
    "Base your answer ONLY on the provided excerpts. Never invent information not present in them."
)


def _build_comparative_prompt(question: str, papers_with_chunks: list[dict]) -> str:
    sections = []
    for paper in papers_with_chunks:
        labeled = "\n\n".join(f"[Section: {c['section_reference']}]\n{c['text']}" for c in paper["chunks"])
        sections.append(f"=== Paper {paper['paper_id']}: {paper['title']} ===\n{labeled}")
    excerpts_text = "\n\n".join(sections)
    paper_list = ", ".join(f"Paper {paper['paper_id']}" for paper in papers_with_chunks)

    return (
        f"Answer the following question by comparing the excerpts from multiple papers below.\n"
        f"Question: {question}\n\n"
        f"You MUST cite EVERY paper listed ({paper_list}) individually, even if a paper's excerpts "
        "don't help answer the question (in that case, use 'none' as that paper's source).\n\n"
        "Respond in exactly this format, with no extra commentary:\n"
        "ANSWER: <your comparative answer>\n"
        "CITATIONS:\n"
        "Paper <id>: (Source: <section name>)\n"
        "Paper <id>: (Source: <section name>)\n"
        "(one CITATIONS line per paper listed above)\n\n"
        "--- EXCERPTS ---\n"
        f"{excerpts_text}"
    )


def generate_comparative_answer(
    question: str, papers_with_chunks: list[dict]
) -> tuple[str | None, dict[int, str | None] | None, bool]:
    """Returns (answer, citations_by_paper_id, refused). Requires a verifiable
    citation for EVERY paper in papers_with_chunks — if any paper is missing a
    citation, or its cited section can't be verified against that paper's OWN
    excerpts (each paper is checked in isolation, not against the pooled text),
    the whole comparative answer is discarded and refused=True."""
    prompt = _build_comparative_prompt(question, papers_with_chunks)
    response = call_llm(prompt, system_prompt=COMPARATIVE_QA_SYSTEM_PROMPT)

    answer_match = re.search(r"ANSWER:\s*(.*?)(?=\nCITATIONS:|\Z)", response, re.DOTALL)
    citations_match = re.search(r"CITATIONS:\s*(.*)", response, re.DOTALL)
    if not answer_match or not citations_match:
        safe_log(f"[qa_service] Could not parse comparative ANSWER/CITATIONS blocks: {response!r}")
        return None, None, True

    answer_text = answer_match.group(1).strip()
    citation_lines = re.findall(r"Paper\s+(\d+):\s*\(Source:\s*([^)]+)\)", citations_match.group(1))
    cited_section_by_paper_id = {int(pid): section.strip() for pid, section in citation_lines}

    citations_by_paper: dict[int, str | None] = {}
    for paper in papers_with_chunks:
        paper_id = paper["paper_id"]
        cited_section = cited_section_by_paper_id.get(paper_id)
        if cited_section is None:
            safe_log(f"[qa_service] Missing citation for paper {paper_id} in comparative answer")
            return None, None, True

        chunk_labels = {c["section_reference"].lower() for c in paper["chunks"] if c["section_reference"]}
        source_text_lower = "\n\n".join(c["text"] for c in paper["chunks"]).lower()

        if not _verify_citation(f"(Source: {cited_section})", chunk_labels, source_text_lower):
            safe_log(f"[qa_service] Rejected ungrounded comparative citation for paper {paper_id}: {cited_section!r}")
            return None, None, True

        citations_by_paper[paper_id] = None if cited_section.lower() == "none" else cited_section

    return answer_text, citations_by_paper, False
