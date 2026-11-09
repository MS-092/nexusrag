from __future__ import annotations

import uuid
from typing import Any

from nexusrag.db import Database, dumps, loads
from nexusrag.sources import SourceStore, now

TITLE_CHARS = 80


class ConversationStore:
    """Saved chats, one Scope each. Only text, citations and modes are stored:
    never a provider key, and never the request headers."""

    def __init__(self, db: Database, sources: SourceStore) -> None:
        self.db = db
        self.sources = sources

    def create(self, first_question: str, scope_type: str, scope_id: str | None) -> str:
        cid = uuid.uuid4().hex
        ts = now()
        title = " ".join(first_question.split())[:TITLE_CHARS] or "Conversation"
        self.db.execute(
            "INSERT INTO conversations (id, title, scope_type, scope_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (cid, title, scope_type, scope_id, ts, ts),
        )
        return cid

    def exists(self, cid: str) -> bool:
        return self.db.one("SELECT 1 AS x FROM conversations WHERE id = ?", (cid,)) is not None

    def scope_of(self, cid: str) -> tuple[str, str | None] | None:
        row = self.db.one("SELECT scope_type, scope_id FROM conversations WHERE id = ?", (cid,))
        return (row["scope_type"], row["scope_id"]) if row else None

    def append(self, cid: str, question: str, result: dict[str, Any]) -> None:
        ts = now()
        self.db.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
            (cid, question, ts),
        )
        self.db.execute(
            "INSERT INTO messages (conversation_id, role, content, citations, mode, skill, created_at)"
            " VALUES (?, 'assistant', ?, ?, ?, ?, ?)",
            (cid, result["answer"], dumps(result.get("citations", [])), result.get("mode"), result.get("skill"), ts),
        )
        self.db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (ts, cid))

    def list(self, scope: str | None = None, notebook_id: str | None = None) -> list[dict[str, Any]]:
        sql = (
            "SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count"
            " FROM conversations c"
        )
        where, params = [], []
        if scope:
            where.append("c.scope_type = ?")
            params.append(scope)
        if notebook_id:
            where.append("c.scope_id = ?")
            params.append(notebook_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY c.updated_at DESC, c.created_at DESC"
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "scope": {"type": r["scope_type"], "id": r["scope_id"]},
                "message_count": r["message_count"],
                "updated_at": r["updated_at"],
            }
            for r in self.db.query(sql, tuple(params))
        ]

    def get(self, cid: str) -> dict[str, Any] | None:
        row = self.db.one("SELECT * FROM conversations WHERE id = ?", (cid,))
        if row is None:
            return None
        messages = []
        for m in self.db.query("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (cid,)):
            citations = loads(m["citations"])
            for c in citations:
                c["removed"] = self.sources.raw(c["source_id"]) is None   # computed at read time
            messages.append(
                {
                    "role": m["role"],
                    "content": m["content"],
                    "citations": citations,
                    "mode": m["mode"],
                    "skill": m["skill"],
                    "created_at": m["created_at"],
                }
            )
        return {
            "id": row["id"],
            "title": row["title"],
            "scope": {"type": row["scope_type"], "id": row["scope_id"]},
            "messages": messages,
        }

    def delete(self, cid: str) -> None:
        self.db.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
        self.db.execute("DELETE FROM conversations WHERE id = ?", (cid,))
