from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexusrag.config import Settings
from nexusrag.health import health_report
from nexusrag.db import Database
from nexusrag.embedder import get_embedder
from nexusrag.index import Index
from nexusrag.jobs import JobRunner
from nexusrag.pipeline import Pipeline
from nexusrag.routes_sources import router as sources_router
from nexusrag.sources import SourceStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="NexusRAG", version="0.1.0")
    app.state.settings = settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    app.state.jobs = JobRunner()
    app.state.db = Database(settings.data_dir / "nexusrag.sqlite")
    app.state.store = SourceStore(app.state.db)
    app.state.embedder = get_embedder()
    app.state.index = Index(settings.data_dir / "qdrant")
    app.state.pipeline = Pipeline(app.state.store, app.state.index, app.state.embedder)

    # Single user, single machine: only the local web app may call this API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(sources_router)

    @app.get("/health")
    def health() -> dict:
        return health_report(settings.data_dir, app.state.embedder, app.state.index)

    return app


app = create_app()
