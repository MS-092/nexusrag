from __future__ import annotations

from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, model_validator

from nexusrag.notebooks import NotebookStore
from nexusrag.sources import SourceStore


class Scope(BaseModel):
    """What a chat or Skill can see: the whole Brain, or one Notebook."""

    type: Literal["brain", "notebook"] = "brain"
    id: str | None = None

    @model_validator(mode="after")
    def notebook_needs_id(self) -> "Scope":
        if self.type == "notebook" and not self.id:
            raise ValueError("A notebook scope needs a notebook id.")
        return self


def resolve_scope(sources: SourceStore, notebooks: NotebookStore, scope: Scope | None) -> set[str]:
    """The single place retrieval is bounded. Private Sources are never in scope,
    so no chat, Skill or summary can send them to a provider."""
    scope = scope or Scope()
    eligible = {s["id"] for s in sources.list() if s["state"] == "ready" and not s["private"]}
    if scope.type == "brain":
        return eligible
    assert scope.id is not None
    if notebooks.get(scope.id) is None:
        raise HTTPException(404, "Notebook not found")
    return eligible & notebooks.member_ids(scope.id)
