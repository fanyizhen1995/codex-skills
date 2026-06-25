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
    auth_state: str
    topic: str
    enabled: bool


class HealthResponse(BaseModel):
    status: str
    bind_host: str
    bind_port: int
    authenticated: bool
    warning: str
