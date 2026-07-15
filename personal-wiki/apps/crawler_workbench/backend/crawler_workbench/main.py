from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .db import migrate, open_db
from .profiles import initialize_profiles_from_seed
from .scheduler import Scheduler
from .settings import Settings


LOG = logging.getLogger("crawler_workbench")


def create_app(settings: Settings | None = None) -> FastAPI:
    repo_root = os.environ.get("PW_WORKBENCH_REPO_ROOT") or _discover_repo_root()
    resolved = settings or Settings(repo_root=repo_root)

    app = FastAPI(title="Personal Wiki Crawler Workbench", version="0.1.0")
    app.state.settings = resolved
    app.state.db_initialized = False
    app.state.scheduler = None
    app.state.initialize_database = initialize_database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request, exc):
        return JSONResponse(status_code=400, content={"detail": jsonable_encoder(exc.errors())})

    app.include_router(router)

    @app.on_event("startup")
    async def startup() -> None:
        initialize_database(app)
        LOG.warning(resolved.trusted_network_warning)
        if os.getenv("PW_WORKBENCH_DISABLE_SCHEDULER") != "1":
            scheduler = Scheduler(resolved)
            app.state.scheduler = scheduler
            await scheduler.start()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        scheduler = app.state.scheduler
        if scheduler is not None:
            await scheduler.stop()
            app.state.scheduler = None

    return app


def initialize_database(app: FastAPI) -> None:
    if getattr(app.state, "db_initialized", False):
        return
    settings = app.state.settings
    settings.resolved_state_dir.mkdir(parents=True, exist_ok=True)
    with open_db(settings.database_path) as db:
        migrate(db)
        initialize_profiles_from_seed(db, settings.sources_yaml_path)
    app.state.db_path = settings.database_path
    app.state.db_initialized = True


def _discover_repo_root() -> str:
    from pathlib import Path

    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "personal-wiki" / "WIKI.md").exists():
            return str(candidate)
    return str(current)


app = create_app()
