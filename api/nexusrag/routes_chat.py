from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from nexusrag.providers import ProviderConfigError, ProviderError, build_config
from nexusrag.scope import brain_source_ids

router = APIRouter()


class ChatRequest(BaseModel):
    question: str

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
    h = request.headers
    try:
        config = build_config(
            h.get("x-provider"), h.get("x-provider-model"), h.get("x-provider-key"), h.get("x-provider-base-url")
        )
    except ProviderConfigError as exc:
        raise HTTPException(400, str(exc)) from None
    try:
        return state.answerer.answer(body.question, brain_source_ids(state.store), config)
    except ProviderError as exc:
        raise HTTPException(exc.status, exc.message) from None
