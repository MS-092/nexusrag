from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

router = APIRouter()
MAX_NOTE_BYTES = 1024 * 1024


class NoteBody(BaseModel):
    title: str
    content: str
    private: bool = False

    @field_validator("title")
    @classmethod
    def title_ok(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("Title must be 1-200 characters.")
        return v

    @field_validator("content")
    @classmethod
    def content_ok(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content must not be blank.")
        if len(v.encode("utf-8")) > MAX_NOTE_BYTES:
            raise ValueError("Note is over the 1 MB limit.")
        return v


def _note_or_error(request: Request, note_id: str) -> dict:
    row = request.app.state.store.raw(note_id)
    if row is None:
        raise HTTPException(404, "Note not found")
    if row["kind"] != "note":
        raise HTTPException(400, "This Source is not a Note.")
    return row


def _write(request: Request, note_id: str, content: str) -> Path:
    dest = request.app.state.settings.data_dir / "files" / note_id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "note.md"
    path.write_text(content, encoding="utf-8")
    return path


@router.post("/notes", status_code=202)
def create_note(request: Request, body: NoteBody) -> dict:
    state = request.app.state
    data = body.content.encode("utf-8")
    note = state.store.create(
        kind="note",
        name=body.title,
        content_hash=hashlib.sha256(data).hexdigest(),
        size=len(data),
        file_path=None,
        private=body.private,
    )
    path = _write(request, note["id"], body.content)
    state.store.update(note["id"], file_path=str(path))
    state.jobs.submit(lambda nid=note["id"]: state.pipeline.process(nid))
    return note


@router.get("/notes/{note_id}")
def get_note(request: Request, note_id: str) -> dict:
    row = _note_or_error(request, note_id)
    content = Path(row["file_path"]).read_text(encoding="utf-8")
    return {"id": note_id, "title": row["name"], "content": content}


@router.put("/notes/{note_id}", status_code=202)
def update_note(request: Request, note_id: str, body: NoteBody) -> dict:
    state = request.app.state
    row = _note_or_error(request, note_id)
    data = body.content.encode("utf-8")
    new_hash = hashlib.sha256(data).hexdigest()
    path = _write(request, note_id, body.content)
    state.store.update(
        note_id,
        name=body.title,
        content_hash=new_hash,
        size=len(data),
        file_path=str(path),
        state="processing",
        error=None,
        cache_hit=False,
    )
    # Old text must not outlive the edit in the extraction cache.
    if row["content_hash"] != new_hash and not state.store.hash_in_use(row["content_hash"], "note"):
        state.store.cache_purge(row["content_hash"])
    state.activity.record("edited", note_id, body.title, state.notebooks.notebooks_containing(note_id))
    state.jobs.submit(lambda: state.pipeline.process(note_id))
    return state.store.get(note_id)  # type: ignore[return-value]
