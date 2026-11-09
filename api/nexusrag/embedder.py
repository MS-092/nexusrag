from __future__ import annotations

import threading
from dataclasses import dataclass

DENSE_MODEL = "BAAI/bge-small-en-v1.5"  # 384-dim, English, runs locally
SPARSE_MODEL = "Qdrant/bm25"
DENSE_DIM = 384


@dataclass
class SparseVec:
    indices: list[int]
    values: list[float]


class Embedder:
    """Local dense + sparse (keyword) embedder. No key, no network after the
    one-time model download. Models load lazily and are shared per process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._dense = None
        self._sparse = None

    def _load(self) -> None:
        with self._lock:
            if self._dense is None:
                from fastembed import SparseTextEmbedding, TextEmbedding

                self._dense = TextEmbedding(DENSE_MODEL)
                self._sparse = SparseTextEmbedding(SPARSE_MODEL)

    @property
    def loaded(self) -> bool:
        return self._dense is not None

    def embed_documents(self, texts: list[str]) -> tuple[list[list[float]], list[SparseVec]]:
        self._load()
        dense = [v.tolist() for v in self._dense.embed(texts)]
        sparse = [SparseVec(s.indices.tolist(), s.values.tolist()) for s in self._sparse.embed(texts)]
        return dense, sparse

    def embed_query(self, text: str) -> tuple[list[float], SparseVec]:
        self._load()
        dense = next(iter(self._dense.query_embed(text))).tolist()
        s = next(iter(self._sparse.query_embed(text)))
        return dense, SparseVec(s.indices.tolist(), s.values.tolist())


_shared: Embedder | None = None


def get_embedder() -> Embedder:
    global _shared
    if _shared is None:
        _shared = Embedder()
    return _shared
