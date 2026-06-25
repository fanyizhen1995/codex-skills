from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .db import open_db
from .fetch_service import SourceDisabledError, SourceNotFoundError, run_source_once
from .profiles import list_profiles
from .schemas import HealthResponse, SourceProfileResponse


router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        bind_host=settings.bind_host,
        bind_port=settings.bind_port,
        authenticated=False,
        warning=settings.trusted_network_warning,
    )


@router.get("/sources", response_model=list[SourceProfileResponse])
def sources(request: Request) -> list[SourceProfileResponse]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        rows = list_profiles(db)
    return [
        SourceProfileResponse(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            target_domain=row["target_domain"],
            url=row["url"],
            trust_level=row["trust_level"],
            schedule=row["schedule"],
            auto_ingest=bool(row["auto_ingest"]),
            auth_required=bool(row["auth_required"]),
            auth_state=row["auth_state"],
            topic=row["topic"],
            enabled=bool(row["enabled"]),
        )
        for row in rows
    ]


@router.post("/sources/{source_id}/run")
def run_source(source_id: str, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    settings = request.app.state.settings
    with open_db(settings.database_path) as db:
        try:
            return run_source_once(settings, db, source_id)
        except SourceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SourceDisabledError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runs")
def runs(request: Request) -> list[dict[str, object]]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        rows = db.execute("select * from fetch_runs order by id desc limit 100").fetchall()
    return [dict(row) for row in rows]
