from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IngestDecision:
    status: str
    risk_level: str
    reason: str


def ingest_decision(
    profile: dict[str, object],
    content_bytes: int,
    max_auto_ingest_bytes: int = 2_000_000,
) -> IngestDecision:
    if bool(profile.get("auth_required")):
        return IngestDecision("pending", "auth_required", "source requires auth configuration and user confirmation")
    if profile.get("trust_level") != "trusted":
        return IngestDecision("pending", "untrusted", "source is not trusted for automatic ingest")
    if not bool(profile.get("auto_ingest")):
        return IngestDecision("pending", "manual", "auto ingest is disabled")
    if content_bytes > max_auto_ingest_bytes:
        return IngestDecision("pending", "large", "content is larger than automatic ingest limit")
    return IngestDecision("approved", "low", "trusted low-risk source eligible for automatic ingest")
