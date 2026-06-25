from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, StrictBool, StrictStr, field_validator

from .codex_worker import run_codex_job
from .db import open_db
from .fetch_service import SourceDisabledError, SourceNotFoundError, run_source_once
from .graph_api import domain_graph
from .profiles import list_profiles
from .search import rebuild_search_index, search_wiki
from .schemas import HealthResponse, SourceProfileResponse


router = APIRouter(prefix="/api")


class AskRequest(BaseModel):
    domain: StrictStr = Field(min_length=1)
    question: StrictStr = Field(min_length=1)
    persist: StrictBool = False

    @field_validator("domain", "question")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


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


@router.get("/search")
def search(q: str, request: Request, domain: str | None = None) -> list[dict[str, object]]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return search_wiki(db, q, domain=domain)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search/rebuild")
def rebuild_search(request: Request, domain: str | None = None) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    settings = request.app.state.settings
    with open_db(settings.database_path) as db:
        try:
            count = rebuild_search_index(settings, db, domain=domain)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"indexed": count}


@router.get("/graph")
def graph(request: Request, domain: str | None = None) -> dict[str, object]:
    return domain_graph(request.app.state.settings, domain)


@router.post("/ask")
def ask(payload: AskRequest, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    settings = request.app.state.settings
    with open_db(settings.database_path) as db:
        # Task 7 intentionally executes synchronously; background job dispatch is out of scope.
        job_id = run_codex_job(settings, db, "query", payload.domain, payload.question, persist=payload.persist)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def job(job_id: int, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        row = db.execute("select * from codex_jobs where id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    return dict(row)
