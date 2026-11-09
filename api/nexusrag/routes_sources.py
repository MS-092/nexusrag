from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from nexusrag import extractors
from nexusrag.routes_common import provider_config

router = APIRouter()


def _safe_name(filename: str | None) -> str:
    return Path(filename or "upload").name or "upload"


@router.post("/sources", status_code=202)
async def upload_source(request: Request, file: UploadFile = File(...), private: bool = False) -> dict:
    state = request.app.state
    provider = provider_config(request)
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
    source = state.store.create(
        kind=kind, name=name, content_hash=content_hash, size=len(data), file_path=None, private=private
    )
    dest = state.settings.data_dir / "files" / source["id"]
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"original{Path(name).suffix.lower()}"
    path.write_bytes(data)
    state.store.update(source["id"], file_path=str(path))

    state.jobs.submit(lambda sid=source["id"]: state.pipeline.process(sid, provider))
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


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(request: Request, source_id: str) -> Response:
    state = request.app.state
    row = state.store.raw(source_id)
    if row is None:
        raise HTTPException(404, "Source not found")
    state.index.delete_source(source_id)
    state.store.delete(source_id)
    # Extracted text must not outlive its Source, unless an identical file is still in the Brain.
    if not state.store.hash_in_use(row["content_hash"], row["kind"]):
        state.store.cache_purge(row["content_hash"])
    shutil.rmtree(state.settings.data_dir / "files" / source_id, ignore_errors=True)
    return Response(status_code=204)


@router.post("/sources/{source_id}/caption", status_code=202)
def caption_source(request: Request, source_id: str) -> dict:
    state = request.app.state
    row = state.store.raw(source_id)
    if row is None:
        raise HTTPException(404, "Source not found")
    if row["kind"] != "image":
        raise HTTPException(400, "Only images can be captioned.")
    if row["private"]:
        raise HTTPException(400, "Private Sources are never sent to an AI provider.")
    provider = provider_config(request)
    if provider is None:
        raise HTTPException(400, "An AI provider is required to caption an image.")
    state.store.update(source_id, state="processing", error=None)
    state.jobs.submit(lambda: state.pipeline.process(source_id, provider))
    return state.store.get(source_id)  # type: ignore[return-value]


class SourcePatch(BaseModel):
    private: bool


@router.patch("/sources/{source_id}")
def patch_source(request: Request, source_id: str, body: SourcePatch) -> dict:
    state = request.app.state
    if state.store.raw(source_id) is None:
        raise HTTPException(404, "Source not found")
    state.store.update(source_id, private=body.private)
    return state.store.get(source_id)  # type: ignore[return-value]
