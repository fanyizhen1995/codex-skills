from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .store import LoopDashboardStore


def create_app(project_root: Path | str | None = None) -> FastAPI:
    resolved_root = Path(project_root or os.getenv("LOOP_DASHBOARD_PROJECT_ROOT") or _discover_project_root()).resolve()
    store = LoopDashboardStore(resolved_root)
    app = FastAPI(title="Loop Dashboard", version="0.1.0")
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/projects/current")
    def current_project() -> dict:
        return store.project_info()

    @app.get("/api/runs")
    def list_runs() -> list[dict]:
        return store.list_runs()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return run

    @app.get("/api/runs/{run_id}/events")
    def get_events(run_id: str) -> dict:
        events = store.get_events(run_id)
        if events is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return {"run_id": run_id, "events": events}

    @app.get("/api/runs/{run_id}/logs")
    def get_logs(run_id: str) -> dict:
        logs = store.get_logs(run_id)
        if logs is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return {"run_id": run_id, "logs": logs}

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        assets_dir = frontend_dir
        app.mount("/assets", StaticFiles(directory=assets_dir), name="loop-dashboard-assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(index_path)

    return app


def _discover_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "tasks.json").exists():
            return candidate
    return current


app = create_app()
