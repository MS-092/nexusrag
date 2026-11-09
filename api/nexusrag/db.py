from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    size INTEGER NOT NULL,
    state TEXT NOT NULL,
    error TEXT,
    private INTEGER NOT NULL DEFAULT 0,
    cache_hit INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    extracted_text TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    captioned INTEGER NOT NULL DEFAULT 0,
    file_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notebooks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    rules TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pins (
    notebook_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('in', 'out')),
    PRIMARY KEY (notebook_id, source_id)
);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('added', 'edited', 'removed')),
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    notebook_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations TEXT NOT NULL DEFAULT '[]',
    mode TEXT,
    skill TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS extraction_cache (
    content_hash TEXT NOT NULL,
    kind TEXT NOT NULL,
    blocks TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (content_hash, kind)
);
"""


class Database:
    """Thin thread-safe SQLite wrapper. One connection, one lock."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def execute(self, sql: str, params: tuple | dict = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def query(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str) -> Any:
    return json.loads(value)
