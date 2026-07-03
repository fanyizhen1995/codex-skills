from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    WEB = "web"
    RSS = "rss"
    GITHUB = "github"
    ARXIV = "arxiv"


class TrustLevel(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class AuthState(StrEnum):
    READY = "ready"
    NEEDS_AUTH_CONFIG = "needs_auth_config"
    AUTH_FAILED = "auth_failed"
    NEEDS_BROWSER = "needs_browser"
    NETWORK_FAILED = "network_failed"
    UNSUPPORTED = "unsupported"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
