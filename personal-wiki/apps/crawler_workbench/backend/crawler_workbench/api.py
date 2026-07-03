from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, StrictBool, StrictStr, field_validator

from .accelerator_specs import extract_specs_for_all_raw_items, list_accelerator_specs
from .codex_worker import create_codex_job, run_existing_codex_job
from .channel_probe import list_probe_runs, run_channel_probe
from .channel_secrets import (
    SecretDecryptError,
    SecretKeyUnavailableError,
    delete_channel_secret,
    set_channel_secret,
)
from .channels import (
    ChannelInUseError,
    ChannelNotFoundError,
    create_channel,
    delete_channel,
    list_channels,
    update_channel,
)
from .db import open_db
from .discovery import accept_candidate, list_candidates, reject_candidate, trust_candidate_source
from .fetch_service import ChannelNotReadyError, SourceDisabledError, SourceNotFoundError, run_source_once
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
from .manual_ingest import run_manual_url_ingest
from .profiles import create_profile, delete_profile, list_profiles, update_profile
from .search import refresh_search_index_if_stale, rebuild_search_index, search_wiki, validate_domain
from .schemas import (
    AcceptAcceleratorCandidateRequest,
    AcceleratorCandidateResponse,
    AcceleratorSpecExtractionResponse,
    AcceleratorSpecResponse,
    ChannelResponse,
    ChannelDeleteResponse,
    ChannelProbeRunResponse,
    ChannelSecretResponse,
    HealthResponse,
    SourceDeleteResponse,
    SourceProfileResponse,
    TrustAcceleratorCandidatesResponse,
)
from .trusted_sources import TrustSourceInputError, trust_task_source
from .wiki_metrics import collect_wiki_metrics
from .wiki_cli import run_validate, wiki_cli_command
from .wiki_pages import WikiPageError, list_wiki_pages, read_wiki_page


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


class ManualIngestRequest(BaseModel):
    url: StrictStr = Field(min_length=1)
    domain: StrictStr = "ai_infra"
    auto_commit_enabled: StrictBool = True

    @field_validator("url", "domain")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ChannelCreateRequest(BaseModel):
    id: StrictStr | None = None
    target_domain: StrictStr = Field(min_length=1)
    name: StrictStr | None = None
    base_url: StrictStr = Field(min_length=1)
    probe_url: StrictStr | None = None
    probe_method: StrictStr = "GET"
    probe_config_json: StrictStr = "{}"
    kind: StrictStr = "web"
    connector: StrictStr = "generic"
    trust_level: StrictStr = "untrusted"
    enabled: StrictBool = True
    auth_required: StrictBool = False
    auth_mode: StrictStr = "none"
    auth_state: StrictStr | None = None
    notes: StrictStr = ""


class ChannelUpdateRequest(BaseModel):
    name: StrictStr | None = None
    base_url: StrictStr | None = None
    probe_url: StrictStr | None = None
    probe_method: StrictStr | None = None
    probe_config_json: StrictStr | None = None
    kind: StrictStr | None = None
    connector: StrictStr | None = None
    trust_level: StrictStr | None = None
    enabled: StrictBool | None = None
    auth_required: StrictBool | None = None
    auth_mode: StrictStr | None = None
    auth_state: StrictStr | None = None
    notes: StrictStr | None = None


class ChannelSecretRequest(BaseModel):
    secret_kind: StrictStr = Field(min_length=1)
    secret: StrictStr = Field(min_length=1)


class SourceCreateRequest(BaseModel):
    id: StrictStr = Field(min_length=1)
    name: StrictStr = Field(min_length=1)
    type: StrictStr = Field(min_length=1)
    target_domain: StrictStr = Field(min_length=1)
    url: StrictStr = Field(min_length=1)
    channel_id: StrictStr | None = None
    trust_level: StrictStr = "untrusted"
    schedule: StrictStr = "manual"
    auto_ingest: StrictBool = False
    auth_required: StrictBool = False
    baseline_on_first_run: StrictBool = False
    run_policy: StrictStr = "scheduled"
    auth_method: StrictStr | None = None
    auth_ref: StrictStr | None = None
    fetcher_type: StrictStr | None = None
    topic: StrictStr = Field(min_length=1)
    enabled: StrictBool = True


class SourceUpdateRequest(BaseModel):
    name: StrictStr | None = None
    type: StrictStr | None = None
    target_domain: StrictStr | None = None
    url: StrictStr | None = None
    channel_id: StrictStr | None = None
    trust_level: StrictStr | None = None
    schedule: StrictStr | None = None
    auto_ingest: StrictBool | None = None
    auth_required: StrictBool | None = None
    baseline_on_first_run: StrictBool | None = None
    run_policy: StrictStr | None = None
    auth_method: StrictStr | None = None
    auth_ref: StrictStr | None = None
    fetcher_type: StrictStr | None = None
    topic: StrictStr | None = None
    enabled: StrictBool | None = None


class TrustSourceRequest(BaseModel):
    mode: StrictStr = Field(pattern="^(manual|scheduled)$")
    frequency: StrictStr | None = None

    @field_validator("frequency")
    @classmethod
    def normalize_frequency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


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


@router.get("/channels", response_model=list[ChannelResponse])
def channels(request: Request, domain: str | None = None) -> list[ChannelResponse]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        rows = list_channels(db, domain=domain)
    return [ChannelResponse(**row) for row in rows]


@router.post("/channels", response_model=ChannelResponse)
def create_channel_endpoint(payload: ChannelCreateRequest, request: Request) -> ChannelResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return ChannelResponse(**create_channel(db, payload.model_dump(exclude_none=True)))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
def update_channel_endpoint(channel_id: str, payload: ChannelUpdateRequest, request: Request) -> ChannelResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return ChannelResponse(**update_channel(db, channel_id, payload.model_dump(exclude_none=True)))
        except ChannelNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/channels/{channel_id}", response_model=ChannelDeleteResponse)
def delete_channel_endpoint(channel_id: str, request: Request) -> ChannelDeleteResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return ChannelDeleteResponse(**delete_channel(db, channel_id))
        except ChannelNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ChannelInUseError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/channels/{channel_id}/secret", response_model=ChannelSecretResponse)
def set_channel_secret_endpoint(
    channel_id: str,
    payload: ChannelSecretRequest,
    request: Request,
) -> ChannelSecretResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return ChannelSecretResponse(
                **set_channel_secret(
                    request.app.state.settings,
                    db,
                    channel_id,
                    secret_kind=payload.secret_kind,
                    secret=payload.secret,
                )
            )
        except ChannelNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/channels/{channel_id}/secret", response_model=ChannelSecretResponse)
def delete_channel_secret_endpoint(channel_id: str, request: Request) -> ChannelSecretResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return ChannelSecretResponse(**delete_channel_secret(request.app.state.settings, db, channel_id))
        except ChannelNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/channels/{channel_id}/probe", response_model=ChannelProbeRunResponse)
def probe_channel_endpoint(channel_id: str, request: Request) -> ChannelProbeRunResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return ChannelProbeRunResponse(**run_channel_probe(request.app.state.settings, db, channel_id))
        except ChannelNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (SecretKeyUnavailableError, SecretDecryptError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/channels/{channel_id}/probe-runs", response_model=list[ChannelProbeRunResponse])
def channel_probe_runs(channel_id: str, request: Request) -> list[ChannelProbeRunResponse]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return [ChannelProbeRunResponse(**row) for row in list_probe_runs(db, channel_id)]
        except ChannelNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sources", response_model=list[SourceProfileResponse])
def sources(request: Request, domain: str | None = None, channel_id: str | None = None) -> list[SourceProfileResponse]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        rows = list_profiles(db, domain=domain, channel_id=channel_id)
    return [_source_response(row) for row in rows]


@router.post("/sources", response_model=SourceProfileResponse)
def create_source_endpoint(payload: SourceCreateRequest, request: Request) -> SourceProfileResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            row = create_profile(db, payload.model_dump(exclude_none=True))
            return _source_response(row)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/sources/{source_id}", response_model=SourceProfileResponse)
def update_source_endpoint(source_id: str, payload: SourceUpdateRequest, request: Request) -> SourceProfileResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            row = update_profile(db, source_id, payload.model_dump(exclude_none=True))
            return _source_response(row)
        except ValueError as exc:
            if str(exc).startswith("source not found:"):
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/sources/{source_id}", response_model=SourceDeleteResponse)
def delete_source_endpoint(source_id: str, request: Request) -> SourceDeleteResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return SourceDeleteResponse(**delete_profile(db, source_id))
        except ValueError as exc:
            if str(exc).startswith("source not found:"):
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        except ChannelNotReadyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/manual-ingests")
def manual_ingest(payload: ManualIngestRequest, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    try:
        validate_domain(payload.domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    settings = request.app.state.settings
    with open_db(settings.database_path) as db:
        try:
            return run_manual_url_ingest(
                settings,
                db,
                payload.url,
                domain=payload.domain,
                auto_commit_enabled=payload.auto_commit_enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs")
def runs(request: Request) -> list[dict[str, object]]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        rows = db.execute("select * from fetch_runs order by id desc limit 100").fetchall()
    return [_fetch_run_response(row) for row in rows]


def _fetch_run_response(row) -> dict[str, object]:
    record = dict(row)
    error = record.get("error")
    record["failure_reason"] = error if isinstance(error, str) and error.strip() else None
    record["failed_count"] = 1 if record.get("status") == "failed" else 0
    return record


def _source_response(row: dict[str, object]) -> SourceProfileResponse:
    return SourceProfileResponse(
        id=str(row["id"]),
        name=str(row["name"]),
        type=str(row["type"]),
        fetcher_type=row.get("fetcher_type") if row.get("fetcher_type") is None else str(row.get("fetcher_type")),
        target_domain=str(row["target_domain"]),
        url=str(row["url"]),
        channel_id=row.get("channel_id") if row.get("channel_id") is None else str(row.get("channel_id")),
        channel_name=row.get("channel_name") if row.get("channel_name") is None else str(row.get("channel_name")),
        channel_base_url=(
            row.get("channel_base_url") if row.get("channel_base_url") is None else str(row.get("channel_base_url"))
        ),
        channel_auth_state=(
            row.get("channel_auth_state") if row.get("channel_auth_state") is None else str(row.get("channel_auth_state"))
        ),
        trust_level=str(row["trust_level"]),
        schedule=str(row["schedule"]),
        auto_ingest=bool(row["auto_ingest"]),
        auth_required=bool(row["auth_required"]),
        baseline_on_first_run=bool(row["baseline_on_first_run"]),
        run_policy=str(row["run_policy"]),
        auth_state=str(row["auth_state"]),
        topic=str(row["topic"]),
        enabled=bool(row["enabled"]),
        last_run_at=row.get("last_run_at") if row.get("last_run_at") is None else str(row.get("last_run_at")),
        last_run_status=(
            row.get("last_run_status") if row.get("last_run_status") is None else str(row.get("last_run_status"))
        ),
    )


@router.get("/queue")
def queue(request: Request) -> list[dict[str, object]]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        return list_queue(db)


@router.get("/accelerator-candidates", response_model=list[AcceleratorCandidateResponse])
def accelerator_candidates(request: Request) -> list[AcceleratorCandidateResponse]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        return [AcceleratorCandidateResponse(**row) for row in list_candidates(db)]


@router.post("/accelerator-candidates/{candidate_id}/reject", response_model=AcceleratorCandidateResponse)
def reject_accelerator_candidate(candidate_id: int, request: Request) -> AcceleratorCandidateResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return AcceleratorCandidateResponse(**reject_candidate(db, candidate_id))
        except ValueError as exc:
            status_code = _candidate_error_status_code(exc)
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/accelerator-candidates/{candidate_id}/accept", response_model=AcceleratorCandidateResponse)
def accept_accelerator_candidate(
    candidate_id: int,
    payload: AcceptAcceleratorCandidateRequest,
    request: Request,
) -> AcceleratorCandidateResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            accept_payload = payload.model_dump()
            accept_payload["sources_yaml_path"] = request.app.state.settings.sources_yaml_path
            return AcceleratorCandidateResponse(**accept_candidate(db, candidate_id, accept_payload))
        except ValueError as exc:
            status_code = _candidate_error_status_code(exc)
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/accelerator-candidates/{candidate_id}/trust-source", response_model=TrustAcceleratorCandidatesResponse)
def trust_accelerator_candidate_source(candidate_id: int, request: Request) -> TrustAcceleratorCandidatesResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            result = trust_candidate_source(db, candidate_id, request.app.state.settings.sources_yaml_path)
            return TrustAcceleratorCandidatesResponse(**result)
        except ValueError as exc:
            status_code = _candidate_error_status_code(exc)
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


def _candidate_error_status_code(exc: ValueError) -> int:
    if _is_candidate_not_found(exc):
        return 404
    if _is_candidate_state_conflict(exc):
        return 409
    return 400


def _is_candidate_not_found(exc: ValueError) -> bool:
    return str(exc).startswith("candidate not found:")


def _is_candidate_state_conflict(exc: ValueError) -> bool:
    return "must be pending" in str(exc)


@router.get("/accelerator-specs", response_model=list[AcceleratorSpecResponse])
def accelerator_specs(request: Request) -> list[AcceleratorSpecResponse]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        return [AcceleratorSpecResponse(**row) for row in list_accelerator_specs(db)]


@router.post("/accelerator-specs/extract", response_model=AcceleratorSpecExtractionResponse)
def extract_accelerator_specs(request: Request) -> AcceleratorSpecExtractionResponse:
    request.app.state.initialize_database(request.app)
    settings = request.app.state.settings
    with open_db(settings.database_path) as db:
        counts = extract_specs_for_all_raw_items(settings, db)
        db.commit()
        return AcceleratorSpecExtractionResponse(**counts)


@router.get("/wiki/metrics")
def wiki_metrics(request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    settings = request.app.state.settings
    with open_db(settings.database_path) as db:
        return collect_wiki_metrics(settings, db)


@router.get("/wiki/pages")
def wiki_pages(request: Request, domain: str) -> list[dict[str, object]]:
    try:
        return list_wiki_pages(request.app.state.settings, domain)
    except WikiPageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wiki/page")
def wiki_page(request: Request, domain: str, path: str) -> dict[str, object]:
    try:
        return read_wiki_page(request.app.state.settings, domain, path)
    except WikiPageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="wiki page not found") from exc


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


@router.post("/queue/{task_id}/trust-source")
def trust_source(task_id: int, payload: TrustSourceRequest, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return trust_task_source(
                request.app.state.settings,
                db,
                task_id,
                payload.mode,
                payload.frequency,
            )
        except TaskNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except TrustSourceInputError as exc:
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
    settings = request.app.state.settings
    with open_db(request.app.state.settings.database_path) as db:
        try:
            refresh_search_index_if_stale(settings, db, domain=domain)
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
        job_id = create_codex_job(settings, db, "query", payload.domain, payload.question, persist=payload.persist)
    worker = threading.Thread(
        target=_run_codex_job_background,
        args=(settings, job_id, payload.persist),
        daemon=True,
    )
    worker.start()
    return {"job_id": job_id}


def _run_codex_job_background(settings, job_id: int, persist: bool) -> None:
    with open_db(settings.database_path) as db:
        run_existing_codex_job(settings, db, job_id, persist=persist)


@router.get("/jobs/latest")
def latest_job(request: Request, domain: str | None = None) -> dict[str, object] | None:
    request.app.state.initialize_database(request.app)
    query = "select * from codex_jobs where job_type = ?"
    params: list[object] = ["query"]
    if domain is not None:
        query += " and target_domain = ?"
        params.append(domain)
    query += " order by id desc limit 1"
    with open_db(request.app.state.settings.database_path) as db:
        row = db.execute(query, params).fetchone()
    return dict(row) if row is not None else None


@router.get("/jobs/{job_id}")
def job(job_id: int, request: Request) -> dict[str, object]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        row = db.execute("select * from codex_jobs where id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    return dict(row)
