from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexusrag.config import Settings
from nexusrag.health import health_report
from nexusrag.jobs import JobRunner


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="NexusRAG", version="0.1.0")
    app.state.settings = settings
    app.state.jobs = JobRunner()

    # Single user, single machine: only the local web app may call this API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return health_report(settings.data_dir)

    return app


app = create_app()
