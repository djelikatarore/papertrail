import threading

import faiss
import numpy as np

from app.config.settings import FAISS_INDEX_PATH
from app.services.embedding_service import EMBEDDING_DIMENSIONS

_lock = threading.Lock()
_index: faiss.IndexIDMap | None = None


def _build_empty_index() -> "faiss.IndexIDMap":
    return faiss.IndexIDMap(faiss.IndexFlatL2(EMBEDDING_DIMENSIONS))


def load_index() -> None:
    """Loads the FAISS index from disk into memory, or creates a fresh empty one
    if no index file exists yet. Must be called once at application startup."""
    global _index
    try:
        _index = faiss.read_index(FAISS_INDEX_PATH)
    except RuntimeError:
        _index = _build_empty_index()


def save_index() -> None:
    faiss.write_index(_index, FAISS_INDEX_PATH)


def add_paper_embedding(paper_id: int, embedding: list[float]) -> None:
    """Adds (or replaces, if paper_id was already indexed) a paper's embedding vector.
    Persists the index to disk immediately so it survives a server restart."""
    with _lock:
        _index.remove_ids(np.array([paper_id], dtype=np.int64))
        vector = np.array([embedding], dtype=np.float32)
        _index.add_with_ids(vector, np.array([paper_id], dtype=np.int64))
        save_index()


def remove_paper_embedding(paper_id: int) -> None:
    with _lock:
        _index.remove_ids(np.array([paper_id], dtype=np.int64))
        save_index()


def search(embedding: list[float], k: int) -> list[tuple[int, float]]:
    """Returns up to k (paper_id, l2_distance) pairs, nearest first. Excludes any
    empty slots (id -1) that IndexFlatL2 returns when the index holds fewer than k vectors."""
    if _index.ntotal == 0:
        return []
    vector = np.array([embedding], dtype=np.float32)
    distances, ids = _index.search(vector, min(k, _index.ntotal))
    return [(int(paper_id), float(dist)) for dist, paper_id in zip(distances[0], ids[0]) if paper_id != -1]
