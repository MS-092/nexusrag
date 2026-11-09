from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/activity")
def list_activity(request: Request, notebook_id: str | None = None, limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    state = request.app.state
    if notebook_id is not None and state.notebooks.get(notebook_id) is None:
        raise HTTPException(404, "Notebook not found")
    return state.activity.list(notebook_id, limit)
