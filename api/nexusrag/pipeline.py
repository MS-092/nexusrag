from __future__ import annotations

import logging
from pathlib import Path

from nexusrag import captioner, extractors
from nexusrag.chunking import chunk_blocks
from nexusrag.embedder import Embedder
from nexusrag.extractors import ExtractionError
from nexusrag.index import Index
from nexusrag.providers import ProviderConfig, ProviderError
from nexusrag.sources import SourceStore
from nexusrag.tags import derive_tags

log = logging.getLogger("nexusrag.pipeline")


class Pipeline:
    """hash -> cache lookup -> extract -> chunk -> embed -> index -> ready."""

    def __init__(self, store: SourceStore, index: Index, embedder: Embedder) -> None:
        self.store = store
        self.index = index
        self.embedder = embedder

    def process(self, source_id: str, provider: ProviderConfig | None = None) -> None:
        """provider is held in memory for this job only and never stored."""
        row = self.store.raw(source_id)
        if row is None:
            return
        try:
            blocks, hit = self._blocks(row)
            caption_note: str | None = None
            captioned = False
            if row["kind"] == "image":
                caption, caption_note = self._caption(row, provider)
                if caption:
                    blocks = blocks + [{"text": f"Image description: {caption}", "position": {}}]
                    captioned = True
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
                error=caption_note,
                captioned=captioned,
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

    def _caption(self, row: dict, provider: ProviderConfig | None) -> tuple[str | None, str | None]:
        cached = self.store.cache_get(row["content_hash"], "image-caption")
        if cached:
            return cached[0]["text"], None
        if provider is None or row["private"]:
            return None, None
        try:
            text = captioner.caption_image(provider, Path(row["file_path"]))
        except ProviderError as exc:
            return None, f"Caption failed: {exc.message}"
        if not text:
            return None, None
        self.store.cache_put(row["content_hash"], "image-caption", [{"text": text}])
        return text, None

    def _blocks(self, row: dict) -> tuple[list[dict], bool]:
        cached = self.store.cache_get(row["content_hash"], row["kind"])
        if cached is not None:
            return cached, True
        blocks = extractors.extract(row["kind"], Path(row["file_path"]))
        self.store.cache_put(row["content_hash"], row["kind"], blocks)
        return blocks, False
