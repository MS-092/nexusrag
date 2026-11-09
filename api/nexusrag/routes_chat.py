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
    conversation_id: str | None = None

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

    # A follow-up stays inside its Conversation's Scope.
    scope = body.scope
    if body.conversation_id:
        saved = state.conversations.scope_of(body.conversation_id)
        if saved is None:
            raise HTTPException(404, "Conversation not found")
        scope = Scope(type=saved[0], id=saved[1])  # type: ignore[arg-type]

    try:
        result = _answer(request, body, scope, config)
    except ProviderError as exc:
        raise HTTPException(exc.status, exc.message) from None

    # Only successful answers are saved. Text and citations only, never the key.
    cid = body.conversation_id
    if cid is None:
        used = scope or Scope()
        cid = state.conversations.create(body.question, used.type, used.id)
    state.conversations.append(cid, body.question, result)
    return {**result, "conversation_id": cid}


def _answer(request: Request, body: ChatRequest, scope: Scope | None, config) -> dict:
    state = request.app.state
    invocation = parse_invocation(body.question)
    if invocation:
        name, arg = invocation
        skills = load_skills(state.settings.skills_dir)
        skill = skills.get(name)
        if skill is None:
            available = ", ".join(f"/{n}" for n in sorted(skills)) or "none installed"
            raise HTTPException(400, f"Unknown skill /{name}. Available: {available}.")
        # /status always covers the whole Brain, so it ignores the chat Scope.
        ids = set() if skill.name == "status" else resolve_scope(state.store, state.notebooks, scope)
        return state.skills.run(skill, arg, ids, config)
    return state.answerer.answer(body.question, resolve_scope(state.store, state.notebooks, scope), config)
