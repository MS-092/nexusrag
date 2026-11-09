from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from nexusrag.providers import ProviderError
from nexusrag.routes_common import provider_config
from nexusrag.scope import Scope, resolve_scope
from nexusrag.skills import load_skills, parse_invocation

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
    invocation = parse_invocation(body.question)
    if invocation:
        name, arg = invocation
        skills = load_skills(state.settings.skills_dir)
        skill = skills.get(name)
        if skill is None:
            available = ", ".join(f"/{n}" for n in sorted(skills)) or "none installed"
            raise HTTPException(400, f"Unknown skill /{name}. Available: {available}.")
        # /status always covers the whole Brain, so it ignores the chat Scope.
        ids = set() if skill.name == "status" else resolve_scope(state.store, state.notebooks, body.scope)
        try:
            return state.skills.run(skill, arg, ids, config)
        except ProviderError as exc:
            raise HTTPException(exc.status, exc.message) from None
    try:
        return state.answerer.answer(body.question, resolve_scope(state.store, state.notebooks, body.scope), config)
    except ProviderError as exc:
        raise HTTPException(exc.status, exc.message) from None
