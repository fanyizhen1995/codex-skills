from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, StrictBool, StrictStr, field_validator

from .codex_worker import run_codex_job
from .db import open_db
from .fetch_service import SourceDisabledError, SourceNotFoundError, run_source_once
from .graph_api import domain_graph
from .ingest import (
    IngestInputError,
    InvalidTaskStateError,
    TaskNotFoundError,
    approve_task,
    commit_paths,
    list_queue,
    reject_task,
    run_approved_task,
)
from .profiles import list_profiles
from .search import rebuild_search_index, search_wiki, validate_domain
from .schemas import HealthResponse, SourceProfileResponse
from .wiki_cli import run_validate, wiki_cli_command


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


class RejectRequest(BaseModel):
    reason: str = Field(default="rejected by user", min_length=1)

    @field_validator("reason")
    @classmethod
    def require_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ValidateRequest(BaseModel):
    domain: str | None = None

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class RunQueueRequest(BaseModel):
    auto_commit_enabled: StrictBool = False


class CommitRequest(BaseModel):
    domain: StrictStr = Field(min_length=1)
    paths: list[StrictStr] = Field(min_length=1)
    message: StrictStr = Field(min_length=1)
    source_id: StrictStr | None = None

    @field_validator("domain", "message")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("paths")
    @classmethod
    def require_non_empty_paths(cls, value: list[str]) -> list[str]:
        paths = [path.strip() for path in value]
        if any(not path for path in paths):
            raise ValueError("paths must not contain empty values")
        return paths

    @field_validator("source_id")
    @classmethod
    def normalize_source_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


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


@router.get("/settings")
def settings(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "bind_host": settings.bind_host,
        "bind_port": settings.bind_port,
        "authenticated": False,
        "warning": settings.trusted_network_warning,
        "wiki_root": str(settings.wiki_root),
        "database_path": str(settings.database_path),
    }


@router.get("/domains")
def domains(request: Request) -> list[dict[str, str]]:
    domains_dir = request.app.state.settings.wiki_root / "domains"
    if not domains_dir.exists():
        return []
    return [
        {"id": path.name, "name": path.name}
        for path in sorted(domains_dir.iterdir(), key=lambda candidate: candidate.name)
        if path.is_dir()
    ]


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


@router.get("/queue")
def queue(request: Request) -> list[dict[str, object]]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        return list_queue(db)


@router.post("/queue/{task_id}/approve")
def approve(task_id: int, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return approve_task(request.app.state.settings, db, task_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidTaskStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/queue/{task_id}/reject")
def reject(task_id: int, payload: RejectRequest, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return reject_task(db, task_id, payload.reason)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidTaskStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/queue/{task_id}/run")
def run_queue_task(task_id: int, payload: RunQueueRequest, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return run_approved_task(request.app.state.settings, db, task_id, payload.auto_commit_enabled)
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidTaskStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except IngestInputError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/commit")
def commit(payload: CommitRequest, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    try:
        validate_domain(payload.domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return commit_paths(
                request.app.state.settings,
                db,
                payload.domain,
                payload.paths,
                payload.message,
                payload.source_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.post("/validate")
def validate(payload: ValidateRequest, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    settings = request.app.state.settings
    if payload.domain is not None:
        try:
            validate_domain(payload.domain)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = run_validate(settings, payload.domain)
    status = "succeeded" if result.returncode == 0 else "failed"
    command_args = ["validate"]
    if payload.domain is not None:
        command_args.extend(["--domain", payload.domain])
    command = " ".join(wiki_cli_command(settings, *command_args))
    with open_db(settings.database_path) as db:
        validation_run_id = db.execute(
            """
            insert into validation_runs (target_domain, status, command, output)
            values (?, ?, ?, ?)
            """,
            (payload.domain, status, command, result.stdout + result.stderr),
        ).lastrowid
        db.commit()
    return {
        "status": status,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "validation_run_id": validation_run_id,
    }


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
