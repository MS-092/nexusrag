from __future__ import annotations

from fastapi import APIRouter, Request

from nexusrag.skills import load_skills

router = APIRouter()


@router.get("/skills")
def list_skills(request: Request) -> list[dict]:
    skills = load_skills(request.app.state.settings.skills_dir)
    return [
        {"name": s.name, "description": s.description, "usage": s.usage}
        for s in sorted(skills.values(), key=lambda s: s.name)
    ]
