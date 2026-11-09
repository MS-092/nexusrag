from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, field_validator

from nexusrag.notebooks import RULE_TYPES

router = APIRouter()


class Rule(BaseModel):
    type: Literal["file_type", "keyword", "tag"]
    value: str

    @field_validator("value")
    @classmethod
    def value_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Rule value must not be blank.")
        return v


def _name_ok(v: str) -> str:
    v = v.strip()
    if not v or len(v) > 120:
        raise ValueError("Name must be 1-120 characters.")
    return v


class NotebookCreate(BaseModel):
    name: str
    rules: list[Rule] = []

    @field_validator("name")
    @classmethod
    def name_ok(cls, v: str) -> str:
        return _name_ok(v)


class NotebookPatch(BaseModel):
    name: str | None = None
    rules: list[Rule] | None = None

    @field_validator("name")
    @classmethod
    def name_ok(cls, v: str | None) -> str | None:
        return None if v is None else _name_ok(v)


class PinBody(BaseModel):
    mode: Literal["in", "out"]


def _notebook(request: Request, nid: str) -> dict:
    nb = request.app.state.notebooks.get(nid)
    if nb is None:
        raise HTTPException(404, "Notebook not found")
    return nb


def _dump(rules: list[Rule]) -> list[dict]:
    return [r.model_dump() for r in rules]


@router.post("/notebooks", status_code=201)
def create_notebook(request: Request, body: NotebookCreate) -> dict:
    return request.app.state.notebooks.create(body.name, _dump(body.rules))


@router.get("/notebooks")
def list_notebooks(request: Request) -> list[dict]:
    return request.app.state.notebooks.list()


@router.get("/notebooks/{nid}")
def get_notebook(request: Request, nid: str) -> dict:
    return _notebook(request, nid)


@router.patch("/notebooks/{nid}")
def patch_notebook(request: Request, nid: str, body: NotebookPatch) -> dict:
    _notebook(request, nid)
    store = request.app.state.notebooks
    store.update(nid, body.name, None if body.rules is None else _dump(body.rules))
    return store.get(nid)


@router.delete("/notebooks/{nid}", status_code=204)
def delete_notebook(request: Request, nid: str) -> Response:
    _notebook(request, nid)
    request.app.state.notebooks.delete(nid)
    return Response(status_code=204)


@router.get("/notebooks/{nid}/sources")
def notebook_sources(request: Request, nid: str) -> list[dict]:
    _notebook(request, nid)
    return request.app.state.notebooks.members(nid)


@router.put("/notebooks/{nid}/pins/{source_id}")
def pin_source(request: Request, nid: str, source_id: str, body: PinBody) -> dict:
    _notebook(request, nid)
    if request.app.state.store.raw(source_id) is None:
        raise HTTPException(404, "Source not found")
    request.app.state.notebooks.set_pin(nid, source_id, body.mode)
    return {"notebook_id": nid, "source_id": source_id, "mode": body.mode}


@router.delete("/notebooks/{nid}/pins/{source_id}", status_code=204)
def unpin_source(request: Request, nid: str, source_id: str) -> Response:
    _notebook(request, nid)
    request.app.state.notebooks.remove_pin(nid, source_id)
    return Response(status_code=204)
