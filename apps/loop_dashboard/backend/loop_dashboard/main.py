from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import hashlib
import hmac
import os
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .pagination import (
    CursorCodec,
    CursorError,
    PageSizeError,
    SnapshotCapacityError,
)
from .store import LoopDashboardStore
from .supervisor_store import SupervisorDashboardStore


_CURSOR_CODECS: OrderedDict[
    tuple[str, str, int, int], CursorCodec
] = OrderedDict()
_CURSOR_CODECS_LOCK = RLock()
_CURSOR_CODEC_LIMIT = 64


def create_app(
    project_root: Path | str | None = None,
    *,
    cursor_secret: bytes | str | None = None,
    sqlite_snapshot_ttl_seconds: float = 300,
    reaper_interval_seconds: float = 1,
    max_snapshot_row_bytes: int = 256 * 1024,
    max_snapshot_bytes: int = 16 * 1024 * 1024,
    supervisor_clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    if reaper_interval_seconds <= 0:
        raise ValueError("reaper interval must be positive")
    resolved_root = Path(project_root or os.getenv("LOOP_DASHBOARD_PROJECT_ROOT") or _discover_project_root()).resolve()
    resolved_secret = _resolve_cursor_secret(resolved_root, cursor_secret)
    codec_key = (
        str(resolved_root),
        hashlib.sha256(resolved_secret).hexdigest(),
        max_snapshot_row_bytes,
        max_snapshot_bytes,
    )
    with _CURSOR_CODECS_LOCK:
        cursor_codec = _CURSOR_CODECS.get(codec_key)
        if cursor_codec is None:
            cursor_codec = CursorCodec(
                resolved_secret,
                max_snapshot_row_bytes=max_snapshot_row_bytes,
                max_snapshot_bytes=max_snapshot_bytes,
            )
            _CURSOR_CODECS[codec_key] = cursor_codec
        _CURSOR_CODECS.move_to_end(codec_key)
        while len(_CURSOR_CODECS) > _CURSOR_CODEC_LIMIT:
            _CURSOR_CODECS.popitem(last=False)
    log_secret = hmac.new(
        resolved_secret,
        b"loop-dashboard-log-handles",
        hashlib.sha256,
    ).digest()
    store = LoopDashboardStore(
        resolved_root,
        cursor_codec=cursor_codec,
        log_secret=log_secret,
    )
    supervisor_store = SupervisorDashboardStore(
        resolved_root,
        cursor_codec=cursor_codec,
        snapshot_ttl_seconds=sqlite_snapshot_ttl_seconds,
        clock=supervisor_clock,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        stop_reaper = asyncio.Event()

        async def reap_idle_state() -> None:
            while not stop_reaper.is_set():
                try:
                    await asyncio.wait_for(
                        stop_reaper.wait(),
                        timeout=reaper_interval_seconds,
                    )
                    continue
                except TimeoutError:
                    pass
                await asyncio.to_thread(store.reap_expired)
                await asyncio.to_thread(supervisor_store.reap_expired)

        store.start()
        try:
            supervisor_store.start()
        except BaseException:
            store.close()
            raise
        reaper = asyncio.create_task(reap_idle_state())
        try:
            yield
        finally:
            stop_reaper.set()
            await asyncio.gather(reaper, return_exceptions=True)
            supervisor_store.close()
            store.close()

    app = FastAPI(title="Loop Dashboard", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.state.supervisor_store = supervisor_store

    @app.exception_handler(SnapshotCapacityError)
    async def snapshot_capacity_error(
        _request: Request,
        exc: SnapshotCapacityError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "status": "capacity_exceeded",
                "error": {
                    "code": "snapshot_capacity_exceeded",
                    "message": str(exc),
                },
            },
        )
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

    @app.get("/api/supervisor")
    def supervisor_summary() -> dict:
        return supervisor_store.summary()

    @app.get("/api/supervisor/health")
    def supervisor_health() -> dict:
        return supervisor_store.health_snapshot()

    @app.get("/api/supervisor/services")
    def supervisor_services(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "services",
            "supervisor-services",
            {"status"},
        )

    @app.get("/api/supervisor/services/freshness")
    def supervisor_freshness(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "freshness_checks",
            "supervisor-freshness",
            {"target", "status"},
        )

    @app.get("/api/supervisor/actions")
    def supervisor_actions(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "actions",
            "supervisor-actions",
            {"run_id", "status", "action_type", "queue_owner"},
        )

    @app.get("/api/supervisor/actions/{action_id}/attempts")
    def supervisor_action_attempts(action_id: str, request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "action_attempts",
            f"supervisor-actions:{action_id}:attempts",
            {"result_class", "error_class", "recovery_tier"},
            fixed_filters={"action_id": action_id},
        )

    @app.get("/api/supervisor/transitions")
    def supervisor_transitions(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "transitions",
            "supervisor-transitions",
            {"run_id", "to_phase", "action_id"},
        )

    @app.get("/api/supervisor/reviews")
    def supervisor_reviews(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "reviews",
            "supervisor-reviews",
            {"status", "decision", "trigger"},
        )

    @app.get("/api/supervisor/reviews/{review_id}/findings")
    def supervisor_review_findings(review_id: str, request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "review_findings",
            f"supervisor-reviews:{review_id}:findings",
            {"status", "severity"},
            fixed_filters={"review_id": review_id},
        )

    @app.get("/api/supervisor/decisions")
    def supervisor_decisions(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "user_decisions",
            "supervisor-decisions",
            {"scope", "run_id", "status"},
        )

    @app.get("/api/supervisor/skills")
    def supervisor_skills(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "skill_snapshots",
            "supervisor-skills",
            set(),
        )

    @app.get("/api/supervisor/skills/{snapshot_id}/rows")
    def supervisor_skill_rows(snapshot_id: str, request: Request) -> dict:
        page_size, cursor, _filters = _page_query(request, set())
        try:
            return supervisor_store.skill_rows(
                snapshot_id,
                page_size=page_size,
                cursor=cursor,
            )
        except (CursorError, PageSizeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/supervisor/recovery")
    def supervisor_recovery(request: Request) -> dict:
        page_size, cursor, filters = _page_query(
            request,
            {"result_class", "error_class", "recovery_tier"},
        )
        if "recovery_tier" in filters and filters["recovery_tier"] not in {
            "1",
            "2",
            "3",
        }:
            raise HTTPException(
                status_code=400,
                detail="recovery_tier must be 1, 2, or 3",
            )
        try:
            return supervisor_store.recovery_page(
                endpoint="supervisor-recovery",
                page_size=page_size,
                cursor=cursor,
                filters=filters,
            )
        except (CursorError, PageSizeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/supervisor/decision-required")
    def supervisor_decision_required(request: Request) -> dict:
        return _supervisor_page(
            request,
            supervisor_store,
            "user_decisions",
            "supervisor-decision-required",
            {"scope", "run_id"},
            fixed_filters={"status": "open"},
        )

    @app.get("/api/runs")
    def list_runs(request: Request) -> dict:
        page_size, cursor, filters = _page_query(
            request, {"phase", "policy", "query"}
        )
        try:
            return store.page_runs(
                page_size=page_size,
                cursor=cursor,
                filters=filters,
            )
        except (CursorError, PageSizeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return run

    @app.get("/api/runs/{run_id}/events")
    def get_events(run_id: str, request: Request, response: Response) -> dict:
        response.headers["X-Loop-Event-Retention"] = (
            "structured=last-1000-lines-within-1048576-bytes;"
            "sessions=last-200-matching-supported-events-scanning-last-10000-"
            "lines-from-newest-128-files-within-2097152-bytes-each-and-"
            "at-most-4096-inspected-entries;"
            "logs=newest-1000"
        )
        return _run_page(
            request,
            run_id,
            store.page_events,
            {"kind", "query"},
        )

    @app.get("/api/runs/{run_id}/logs")
    def get_logs(run_id: str, request: Request) -> dict:
        page_size, cursor, filters = _page_query(request, {"stream", "query"})
        if filters.get("stream") not in {None, "stdout", "stderr"}:
            raise HTTPException(
                status_code=400, detail="stream must be stdout or stderr"
            )
        try:
            page = store.page_logs(
                run_id,
                page_size=page_size,
                cursor=cursor,
                filters=filters,
                supervisor_store=supervisor_store,
            )
        except (CursorError, PageSizeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if page is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return page

    @app.get("/api/runs/{run_id}/logs/{log_id}")
    def get_log_detail(run_id: str, log_id: str) -> dict:
        detail = store.get_log_detail(
            run_id,
            log_id,
            supervisor_store=supervisor_store,
        )
        if detail is None:
            raise HTTPException(status_code=404, detail="log not found")
        return detail

    @app.get("/api/runs/{run_id}/children")
    def get_children(run_id: str, request: Request) -> dict:
        return _run_page(
            request,
            run_id,
            store.page_children,
            {"status"},
        )

    @app.get("/api/runs/{run_id}/acceptance")
    def get_acceptance(run_id: str, request: Request) -> dict:
        return _run_page(
            request,
            run_id,
            store.page_acceptance,
            {"status"},
        )

    @app.get("/api/runs/{run_id}/diagnostics")
    def get_diagnostics(run_id: str, request: Request) -> dict:
        return _run_page(
            request,
            run_id,
            store.page_diagnostics,
            {"kind", "severity"},
        )

    @app.get("/api/runs/{run_id}/artifacts")
    def get_artifacts(run_id: str, request: Request) -> dict:
        return _run_page(
            request,
            run_id,
            store.page_artifacts,
            {"query"},
        )

    frontend_dir = _frontend_root()
    index_path, assets_dir = _frontend_paths(frontend_dir)
    if index_path.exists():
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="loop-dashboard-assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(index_path)

    return app


def _frontend_root() -> Path:
    return Path(__file__).resolve().parents[2] / "frontend"


def _frontend_paths(frontend_dir: Path) -> tuple[Path, Path]:
    dist_dir = frontend_dir / "dist"
    dist_index = dist_dir / "index.html"
    if dist_index.exists():
        return dist_index, dist_dir / "assets"
    return frontend_dir / "index.html", frontend_dir


def _discover_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "tasks.json").exists():
            return candidate
    return current


def _resolve_cursor_secret(
    project_root: Path,
    configured: bytes | str | None,
) -> bytes:
    del project_root
    value = (
        configured
        if configured is not None
        else os.getenv("LOOP_DASHBOARD_CURSOR_SECRET")
    )
    if isinstance(value, str):
        value = value.encode()
    if not isinstance(value, bytes) or not value:
        raise RuntimeError(
            "LOOP_DASHBOARD_CURSOR_SECRET must be configured with random data"
        )
    if len(value) < 32:
        raise ValueError("cursor secret must contain at least 32 bytes")
    return hashlib.sha256(value).digest()


def _supervisor_page(
    request: Request,
    store: SupervisorDashboardStore,
    table: str,
    endpoint: str,
    allowed_filters: set[str],
    *,
    fixed_filters: dict[str, object] | None = None,
) -> dict:
    page_size, cursor, filters = _page_query(request, allowed_filters)
    filters.update(fixed_filters or {})
    if "recovery_tier" in filters:
        raw_tier = str(filters["recovery_tier"])
        if raw_tier not in {"0", "1", "2", "3"}:
            raise HTTPException(
                status_code=400,
                detail="recovery_tier must be 0, 1, 2, or 3",
            )
    try:
        return store.page(
            table,
            endpoint=endpoint,
            page_size=page_size,
            cursor=cursor,
            filters=filters,
        )
    except (CursorError, PageSizeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _page_query(
    request: Request,
    allowed_filters: set[str],
) -> tuple[int, str | None, dict[str, str]]:
    allowed = {"page_size", "cursor", *allowed_filters}
    seen: set[str] = set()
    for name, _value in request.query_params.multi_items():
        if name not in allowed:
            raise HTTPException(status_code=400, detail=f"unsupported filter: {name}")
        if name in seen:
            raise HTTPException(status_code=400, detail=f"duplicate query parameter: {name}")
        seen.add(name)
    raw_page_size = request.query_params.get("page_size", "20")
    if raw_page_size not in {"20", "50", "100"}:
        raise HTTPException(status_code=400, detail="page_size must be 20, 50, or 100")
    raw_cursor = request.query_params.get("cursor")
    if raw_cursor == "":
        raise HTTPException(status_code=400, detail="cursor must not be empty")
    cursor = raw_cursor or None
    filters: dict[str, str] = {}
    for name in sorted(allowed_filters):
        if name not in request.query_params:
            continue
        value = request.query_params[name]
        if not value:
            raise HTTPException(status_code=400, detail=f"invalid filter: {name}")
        filters[name] = value
    return int(raw_page_size), cursor, filters


def _run_page(
    request: Request,
    run_id: str,
    page_method: Callable[..., dict[str, Any] | None],
    allowed_filters: set[str],
) -> dict:
    page_size, cursor, filters = _page_query(request, allowed_filters)
    try:
        page = page_method(
            run_id,
            page_size=page_size,
            cursor=cursor,
            filters=filters,
        )
    except (CursorError, PageSizeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if page is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return page


app = create_app()
