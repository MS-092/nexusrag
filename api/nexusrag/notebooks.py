from __future__ import annotations

import uuid
from typing import Any

from nexusrag.db import Database, dumps, loads
from nexusrag.sources import SourceStore, now

RULE_TYPES = ("file_type", "keyword", "tag")


class NotebookStore:
    """A Notebook is a named subset of the Brain: Rules fill it, Pins override.
    Membership is computed live so it can never go stale:
        members = (Sources matching any Rule) + (pinned in) - (pinned out)
    """

    def __init__(self, db: Database, sources: SourceStore) -> None:
        self.db = db
        self.sources = sources

    # ---- notebooks
    def create(self, name: str, rules: list[dict]) -> dict[str, Any]:
        nid = uuid.uuid4().hex
        ts = now()
        self.db.execute(
            "INSERT INTO notebooks (id, name, rules, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (nid, name, dumps(rules), ts, ts),
        )
        return self.get(nid)  # type: ignore[return-value]

    def _row(self, nid: str) -> dict[str, Any] | None:
        return self.db.one("SELECT * FROM notebooks WHERE id = ?", (nid,))

    def get(self, nid: str) -> dict[str, Any] | None:
        row = self._row(nid)
        if row is None:
            return None
        pins = self.db.query("SELECT source_id, mode FROM pins WHERE notebook_id = ? ORDER BY source_id", (nid,))
        return {"id": row["id"], "name": row["name"], "rules": loads(row["rules"]), "pins": pins}

    def list(self) -> list[dict[str, Any]]:
        out = []
        for row in self.db.query("SELECT id FROM notebooks ORDER BY created_at, id"):
            nb = self.get(row["id"])
            assert nb is not None
            out.append(
                {"id": nb["id"], "name": nb["name"], "rules": nb["rules"], "member_count": len(self.members(nb["id"]))}
            )
        return out

    def update(self, nid: str, name: str | None, rules: list[dict] | None) -> None:
        if name is not None:
            self.db.execute("UPDATE notebooks SET name = ?, updated_at = ? WHERE id = ?", (name, now(), nid))
        if rules is not None:
            self.db.execute("UPDATE notebooks SET rules = ?, updated_at = ? WHERE id = ?", (dumps(rules), now(), nid))

    def delete(self, nid: str) -> None:
        self.db.execute("DELETE FROM pins WHERE notebook_id = ?", (nid,))
        self.db.execute("DELETE FROM notebooks WHERE id = ?", (nid,))

    # ---- pins
    def set_pin(self, nid: str, source_id: str, mode: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO pins (notebook_id, source_id, mode) VALUES (?, ?, ?)", (nid, source_id, mode)
        )

    def remove_pin(self, nid: str, source_id: str) -> None:
        self.db.execute("DELETE FROM pins WHERE notebook_id = ? AND source_id = ?", (nid, source_id))

    def forget_source(self, source_id: str) -> None:
        self.db.execute("DELETE FROM pins WHERE source_id = ?", (source_id,))

    # ---- membership
    def members(self, nid: str) -> list[dict[str, Any]]:
        """Member sources (public fields) with the reasons each one is in."""
        nb = self.get(nid)
        if nb is None:
            return []
        pins = {p["source_id"]: p["mode"] for p in nb["pins"]}
        out: list[dict[str, Any]] = []
        for row in self.db.query("SELECT * FROM sources ORDER BY created_at, id"):
            if pins.get(row["id"]) == "out":
                continue
            reasons: list[dict[str, Any]] = [
                {"via": "rule", "rule": rule} for rule in nb["rules"] if _matches(rule, row)
            ]
            if pins.get(row["id"]) == "in":
                reasons.append({"via": "pin"})
            if reasons:
                public = self.sources.get(row["id"])
                assert public is not None
                out.append({**public, "reasons": reasons})
        return out

    def notebooks_containing(self, source_id: str) -> list[str]:
        return [
            row["id"]
            for row in self.db.query("SELECT id FROM notebooks ORDER BY created_at, id")
            if source_id in self.member_ids(row["id"])
        ]

    def member_ids(self, nid: str) -> set[str]:
        return {m["id"] for m in self.members(nid)}


def _matches(rule: dict, row: dict[str, Any]) -> bool:
    value = rule["value"].strip().lower()
    if rule["type"] == "file_type":
        return row["kind"] == value
    if rule["type"] == "tag":
        return value in [t.lower() for t in loads(row["tags"])]
    if rule["type"] == "keyword":
        return value in row["extracted_text"].lower() or value in row["name"].lower()
    return False
