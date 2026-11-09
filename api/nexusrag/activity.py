from __future__ import annotations

from typing import Any

from nexusrag.db import Database, dumps, loads
from nexusrag.sources import now


class ActivityLog:
    """Append-only record of Sources added, edited and removed. The notebooks a
    Source belonged to are captured at event time, so history survives deletes."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def record(self, kind: str, source_id: str, source_name: str, notebook_ids: list[str]) -> None:
        self.db.execute(
            "INSERT INTO activity (kind, source_id, source_name, notebook_ids, created_at) VALUES (?, ?, ?, ?, ?)",
            (kind, source_id, source_name, dumps(notebook_ids), now()),
        )

    def has(self, kind: str, source_id: str) -> bool:
        return self.db.one("SELECT 1 AS x FROM activity WHERE kind = ? AND source_id = ? LIMIT 1", (kind, source_id)) is not None

    def list(self, notebook_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM activity ORDER BY id DESC")
        out: list[dict[str, Any]] = []
        for row in rows:
            ids = loads(row["notebook_ids"])
            if notebook_id is not None and notebook_id not in ids:
                continue
            out.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "source_id": row["source_id"],
                    "source_name": row["source_name"],
                    "notebook_ids": ids,
                    "created_at": row["created_at"],
                }
            )
            if len(out) >= limit:
                break
        return out
