from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from nexusrag.providers import ProviderError
from nexusrag.routes_common import provider_config
from nexusrag.scope import Scope, resolve_scope

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    scope: Scope | None = None

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank.")
        return value


@router.post("/chat")
def chat(request: Request, body: ChatRequest) -> dict:
    state = request.app.state
    config = provider_config(request)
    try:
        return state.answerer.answer(body.question, resolve_scope(state.store, state.notebooks, body.scope), config)
    except ProviderError as exc:
        raise HTTPException(exc.status, exc.message) from None
