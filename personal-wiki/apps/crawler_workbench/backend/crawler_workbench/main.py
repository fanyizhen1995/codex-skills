from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .settings import Settings


LOG = logging.getLogger("crawler_workbench")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings(repo_root=_discover_repo_root())
    resolved.resolved_state_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Personal Wiki Crawler Workbench", version="0.1.0")
    app.state.settings = resolved
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.on_event("startup")
    def warn_unauthenticated() -> None:
        LOG.warning(resolved.trusted_network_warning)

    return app


def _discover_repo_root() -> str:
    from pathlib import Path

    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "personal-wiki" / "WIKI.md").exists():
            return str(candidate)
    return str(current)


app = create_app()
