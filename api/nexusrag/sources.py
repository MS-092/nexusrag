from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from nexusrag.db import Database, dumps, loads

PUBLIC_FIELDS = (
    "id", "kind", "name", "size", "state", "error", "private", "cache_hit",
    "chunk_count", "tags", "captioned", "created_at", "updated_at",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public(row: dict[str, Any], with_text: bool = False) -> dict[str, Any]:
    out = {k: row[k] for k in PUBLIC_FIELDS}
    out["private"] = bool(out["private"])
    out["cache_hit"] = bool(out["cache_hit"])
    out["captioned"] = bool(out["captioned"])
    out["tags"] = loads(out["tags"])
    if with_text:
        out["extracted_text"] = row["extracted_text"]
    return out


class SourceStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, *, kind: str, name: str, content_hash: str, size: int, file_path: str | None) -> dict[str, Any]:
        sid = uuid.uuid4().hex
        ts = now()
        self.db.execute(
            "INSERT INTO sources (id, kind, name, content_hash, size, state, file_path, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, 'processing', ?, ?, ?)",
            (sid, kind, name, content_hash, size, file_path, ts, ts),
        )
        return self.get(sid)  # type: ignore[return-value]

    def raw(self, sid: str) -> dict[str, Any] | None:
        return self.db.one("SELECT * FROM sources WHERE id = ?", (sid,))

    def get(self, sid: str, with_text: bool = False) -> dict[str, Any] | None:
        row = self.raw(sid)
        return _public(row, with_text) if row else None

    def list(self) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM sources ORDER BY created_at, id")
        return [_public(r) for r in rows]

    def update(self, sid: str, **fields: Any) -> None:
        if "tags" in fields:
            fields["tags"] = dumps(fields["tags"])
        for flag in ("private", "cache_hit", "captioned"):
            if flag in fields:
                fields[flag] = int(bool(fields[flag]))
        fields["updated_at"] = now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.db.execute(f"UPDATE sources SET {cols} WHERE id = ?", (*fields.values(), sid))

    def delete(self, sid: str) -> None:
        self.db.execute("DELETE FROM sources WHERE id = ?", (sid,))

    # extraction cache (keyed by content hash + kind)
    def cache_get(self, content_hash: str, kind: str) -> list[dict[str, Any]] | None:
        row = self.db.one(
            "SELECT blocks FROM extraction_cache WHERE content_hash = ? AND kind = ?",
            (content_hash, kind),
        )
        return loads(row["blocks"]) if row else None

    def cache_put(self, content_hash: str, kind: str, blocks: list[dict[str, Any]]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO extraction_cache (content_hash, kind, blocks, created_at) VALUES (?, ?, ?, ?)",
            (content_hash, kind, dumps(blocks), now()),
        )
