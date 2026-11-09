from __future__ import annotations

import logging
from pathlib import Path

from nexusrag import extractors
from nexusrag.chunking import chunk_blocks
from nexusrag.embedder import Embedder
from nexusrag.extractors import ExtractionError
from nexusrag.index import Index
from nexusrag.sources import SourceStore
from nexusrag.tags import derive_tags

log = logging.getLogger("nexusrag.pipeline")


class Pipeline:
    """hash -> cache lookup -> extract -> chunk -> embed -> index -> ready."""

    def __init__(self, store: SourceStore, index: Index, embedder: Embedder) -> None:
        self.store = store
        self.index = index
        self.embedder = embedder

    def process(self, source_id: str) -> None:
        row = self.store.raw(source_id)
        if row is None:
            return
        try:
            blocks, hit = self._blocks(row)
            chunks = chunk_blocks(blocks)
            dense, sparse = self.embedder.embed_documents([c["text"] for c in chunks])
            if self.store.raw(source_id) is None:   # deleted while processing
                return
            self.index.delete_source(source_id)  # idempotent re-index (retry, edit)
            self.index.upsert(source_id, chunks, dense, sparse)
            text = "\n\n".join(b["text"] for b in blocks)
            self.store.update(
                source_id,
                state="ready",
                error=None,
                cache_hit=hit,
                chunk_count=len(chunks),
                extracted_text=text,
                tags=derive_tags(text),
            )
        except ExtractionError as exc:
            self.store.update(source_id, state="failed", error=str(exc))
        except Exception:
            log.exception("ingestion failed for %s", source_id)
            self.store.update(source_id, state="failed", error="Ingestion failed unexpectedly. See the API log.")

    def _blocks(self, row: dict) -> tuple[list[dict], bool]:
        cached = self.store.cache_get(row["content_hash"], row["kind"])
        if cached is not None:
            return cached, True
        blocks = extractors.extract(row["kind"], Path(row["file_path"]))
        self.store.cache_put(row["content_hash"], row["kind"], blocks)
        return blocks, False
