from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models

from nexusrag.embedder import DENSE_DIM, SparseVec

COLLECTION = "brain"


class Index:
    """One Qdrant collection holding dense + sparse vectors per chunk.
    Hybrid retrieval fuses both legs with reciprocal rank fusion."""

    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(path))
        if not self.client.collection_exists(COLLECTION):
            self.client.create_collection(
                COLLECTION,
                vectors_config={"dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)},
                sparse_vectors_config={"sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)},
            )

    def upsert(self, source_id: str, chunks: list[dict], dense: list[list[float]], sparse: list[SparseVec]) -> None:
        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": d,
                    "sparse": models.SparseVector(indices=s.indices, values=s.values),
                },
                payload={
                    "source_id": source_id,
                    "text": c["text"],
                    "position": c["position"],
                    "chunk_index": i,
                },
            )
            for i, (c, d, s) in enumerate(zip(chunks, dense, sparse))
        ]
        if points:
            self.client.upsert(COLLECTION, points=points, wait=True)

    def delete_source(self, source_id: str) -> None:
        self.client.delete(
            COLLECTION,
            points_selector=models.FilterSelector(filter=_source_filter({source_id})),
            wait=True,
        )

    def count_source(self, source_id: str) -> int:
        return self.client.count(COLLECTION, count_filter=_source_filter({source_id}), exact=True).count

    def search(
        self,
        dense: list[float],
        sparse: SparseVec,
        source_ids: set[str] | None,
        k: int = 4,
    ) -> list[dict[str, Any]]:
        """source_ids=None means everything; an empty set means nothing."""
        if source_ids is not None and not source_ids:
            return []
        flt = _source_filter(source_ids) if source_ids is not None else None
        result = self.client.query_points(
            COLLECTION,
            prefetch=[
                models.Prefetch(query=dense, using="dense", limit=20, filter=flt),
                models.Prefetch(
                    query=models.SparseVector(indices=sparse.indices, values=sparse.values),
                    using="sparse",
                    limit=20,
                    filter=flt,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=k,
            with_payload=True,
        )
        return [{"score": p.score, **p.payload} for p in result.points]

    def close(self) -> None:
        self.client.close()


def _source_filter(source_ids: set[str]) -> models.Filter:
    return models.Filter(
        must=[models.FieldCondition(key="source_id", match=models.MatchAny(any=sorted(source_ids)))]
    )
