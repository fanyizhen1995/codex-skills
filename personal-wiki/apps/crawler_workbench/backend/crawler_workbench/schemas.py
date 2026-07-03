from __future__ import annotations

from pydantic import BaseModel


class SourceProfileResponse(BaseModel):
    id: str
    name: str
    type: str
    fetcher_type: str | None = None
    target_domain: str
    url: str
    channel_id: str | None = None
    channel_name: str | None = None
    channel_base_url: str | None = None
    channel_auth_state: str | None = None
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


class ChannelResponse(BaseModel):
    id: str
    target_domain: str
    name: str
    base_url: str
    base_url_normalized: str
    probe_url: str | None = None
    probe_method: str
    probe_config_json: str
    kind: str
    connector: str
    trust_level: str
    enabled: bool
    auth_required: bool
    auth_mode: str
    auth_state: str
    last_probe_status: str | None = None
    last_probe_at: str | None = None
    last_probe_summary: str | None = None
    notes: str
    source_count: int
    created_at: str
    updated_at: str


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


class TrustAcceleratorCandidatesResponse(BaseModel):
    domain: str
    accepted_count: int
    candidate_ids: list[int]
    accepted_source_ids: list[str]
    candidates: list[AcceleratorCandidateResponse]


class AcceleratorObservationResponse(BaseModel):
    id: int
    field: str
    value_text: str
    value_number: float | None = None
    unit: str
    source_profile_id: str
    source_rank: str
    raw_item_id: int | None = None
    raw_path: str
    evidence_text: str
    confidence: float


class AcceleratorResolvedSpecResponse(BaseModel):
    field: str
    value_text: str
    value_number: float | None = None
    unit: str
    source_observation_id: int
    resolved_by: str
    confidence: str
    conflict_status: str


class AcceleratorSpecResponse(BaseModel):
    sku_id: str
    vendor: str
    model_name: str
    normalized_model: str
    scope: str
    source_profile_id: str
    source_url: str
    raw_item_id: int | None = None
    raw_path: str
    observations: list[AcceleratorObservationResponse]
    resolved_specs: list[AcceleratorResolvedSpecResponse]


class AcceleratorSpecExtractionResponse(BaseModel):
    skus: int
    observations: int
    resolved: int


class HealthResponse(BaseModel):
    status: str
    bind_host: str
    bind_port: int
    authenticated: bool
    warning: str
