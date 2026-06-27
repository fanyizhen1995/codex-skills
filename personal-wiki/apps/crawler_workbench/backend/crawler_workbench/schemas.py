from __future__ import annotations

from pydantic import BaseModel


class SourceProfileResponse(BaseModel):
    id: str
    name: str
    type: str
    target_domain: str
    url: str
    trust_level: str
    schedule: str
    auto_ingest: bool
    auth_required: bool
    baseline_on_first_run: bool
    run_policy: str
    auth_state: str
    topic: str
    enabled: bool
    last_run_at: str | None = None
    last_run_status: str | None = None


class AcceleratorCandidateResponse(BaseModel):
    id: int
    vendor: str
    model_name: str
    normalized_model: str
    scope: str
    source_profile_id: str
    source_url: str
    evidence_url: str | None = None
    evidence_text: str
    confidence: float
    status: str
    accepted_source_id: str | None = None
    created_at: str
    updated_at: str


class AcceptAcceleratorCandidateRequest(BaseModel):
    source_id: str
    name: str
    url: str
    scope: list[str]
    source_rank: str = "S1"


class HealthResponse(BaseModel):
    status: str
    bind_host: str
    bind_port: int
    authenticated: bool
    warning: str
