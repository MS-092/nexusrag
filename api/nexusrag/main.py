from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexusrag.config import Settings
from nexusrag.health import health_report
from nexusrag.activity import ActivityLog
from nexusrag.answerer import Answerer
from nexusrag.db import Database
from nexusrag.embedder import get_embedder
from nexusrag.index import Index
from nexusrag.jobs import JobRunner
from nexusrag.notebooks import NotebookStore
from nexusrag.pipeline import Pipeline
from nexusrag.routes_activity import router as activity_router
from nexusrag.routes_chat import router as chat_router
from nexusrag.routes_notebooks import router as notebooks_router
from nexusrag.routes_skills import router as skills_router
from nexusrag.routes_notes import router as notes_router
from nexusrag.routes_sources import router as sources_router
from nexusrag.skill_runner import SkillRunner
from nexusrag.sources import SourceStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="NexusRAG", version="0.1.0")
    app.state.settings = settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    app.state.jobs = JobRunner()
    app.state.db = Database(settings.data_dir / "nexusrag.sqlite")
    app.state.store = SourceStore(app.state.db)
    app.state.notebooks = NotebookStore(app.state.db, app.state.store)
    app.state.embedder = get_embedder()
    app.state.index = Index(settings.data_dir / "qdrant")
    app.state.activity = ActivityLog(app.state.db)
    app.state.pipeline = Pipeline(
        app.state.store, app.state.index, app.state.embedder, app.state.activity, app.state.notebooks
    )
    app.state.answerer = Answerer(app.state.store, app.state.index, app.state.embedder)
    app.state.skills = SkillRunner(app.state.store, app.state.answerer)

    # Single user, single machine: only the local web app may call this API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(sources_router)
    app.include_router(chat_router)
    app.include_router(notes_router)
    app.include_router(notebooks_router)
    app.include_router(activity_router)
    app.include_router(skills_router)

    @app.get("/health")
    def health() -> dict:
        return health_report(settings.data_dir, app.state.embedder, app.state.index)

    return app


app = create_app()
