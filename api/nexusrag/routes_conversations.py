from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()


@router.get("/conversations")
def list_conversations(request: Request, scope: str | None = None, notebook_id: str | None = None) -> list[dict]:
    return request.app.state.conversations.list(scope, notebook_id)


@router.get("/conversations/{cid}")
def get_conversation(request: Request, cid: str) -> dict:
    conv = request.app.state.conversations.get(cid)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.delete("/conversations/{cid}", status_code=204)
def delete_conversation(request: Request, cid: str) -> Response:
    store = request.app.state.conversations
    if not store.exists(cid):
        raise HTTPException(404, "Conversation not found")
    store.delete(cid)
    return Response(status_code=204)
