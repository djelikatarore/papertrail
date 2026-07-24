import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_DIMENSIONS = 384

_model = SentenceTransformer("all-MiniLM-L6-v2")


def get_embedding(text: str) -> list[float]:
    return _model.encode(text, normalize_embeddings=True).tolist()


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Both vectors from get_embedding() are already unit-normalized, so their
    dot product is directly the cosine similarity."""
    return float(np.dot(v1, v2))


def average_embedding(vectors: list[list[float]]) -> list[float]:
    """Averages embeddings and re-normalizes the result to unit length, since
    the average of normalized vectors isn't itself normalized."""
    mean = np.mean(vectors, axis=0)
    norm = np.linalg.norm(mean)
    if norm > 0:
        mean = mean / norm
    return mean.tolist()


def get_paper_embedding_source(raw_text: str, chunks: list[tuple[str, str]]) -> str:
    """Uses the paper's Abstract chunk if one was detected, otherwise falls back
    to the first 500 words of the raw text."""
    for section_reference, text in chunks:
        if section_reference.lower() == "abstract":
            return text
    return " ".join(raw_text.split()[:500])
