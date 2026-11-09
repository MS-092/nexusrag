from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from nexusrag import extractors

router = APIRouter()


def _safe_name(filename: str | None) -> str:
    return Path(filename or "upload").name or "upload"


@router.post("/sources", status_code=202)
async def upload_source(request: Request, file: UploadFile = File(...)) -> dict:
    state = request.app.state
    name = _safe_name(file.filename)
    kind = extractors.kind_for(name)
    if kind is None:
        accepted = ", ".join(extractors.accepted_extensions())
        raise HTTPException(415, f"Unsupported file type. Accepted: {accepted}")

    limit = state.settings.max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is over the {limit // (1024 * 1024)} MB limit.")

    content_hash = hashlib.sha256(data).hexdigest()
    source = state.store.create(kind=kind, name=name, content_hash=content_hash, size=len(data), file_path=None)
    dest = state.settings.data_dir / "files" / source["id"]
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "original"
    path.write_bytes(data)
    state.store.update(source["id"], file_path=str(path))

    state.jobs.submit(lambda sid=source["id"]: state.pipeline.process(sid))
    return source  # snapshot taken before the job starts: state == processing


@router.get("/sources")
def list_sources(request: Request) -> list[dict]:
    return request.app.state.store.list()


@router.get("/sources/{source_id}")
def get_source(request: Request, source_id: str) -> dict:
    source = request.app.state.store.get(source_id, with_text=True)
    if source is None:
        raise HTTPException(404, "Source not found")
    return source


@router.post("/sources/{source_id}/retry", status_code=202)
def retry_source(request: Request, source_id: str) -> dict:
    state = request.app.state
    source = state.store.get(source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    state.store.update(source_id, state="processing", error=None)
    state.jobs.submit(lambda: state.pipeline.process(source_id))
    return state.store.get(source_id)  # type: ignore[return-value]
