from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .db import migrate, open_db, transaction
from .profiles import load_profiles_from_yaml, mirror_profiles
from .settings import Settings


LOG = logging.getLogger("crawler_workbench")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings(repo_root=_discover_repo_root())

    app = FastAPI(title="Personal Wiki Crawler Workbench", version="0.1.0")
    app.state.settings = resolved
    app.state.db_initialized = False
    app.state.initialize_database = initialize_database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        initialize_database(app)
        LOG.warning(resolved.trusted_network_warning)

    return app


def initialize_database(app: FastAPI) -> None:
    if getattr(app.state, "db_initialized", False):
        return
    settings = app.state.settings
    settings.resolved_state_dir.mkdir(parents=True, exist_ok=True)
    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(settings.sources_yaml_path))
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
