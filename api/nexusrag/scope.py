from __future__ import annotations

from nexusrag.sources import SourceStore


def brain_source_ids(store: SourceStore) -> set[str]:
    """Every Source a chat or Skill may see: ready and not Private.
    All retrieval goes through a scope resolver so privacy cannot be bypassed."""
    return {s["id"] for s in store.list() if s["state"] == "ready" and not s["private"]}
