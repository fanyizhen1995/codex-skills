from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class FetchResult:
    canonical_url: str
    title: str
    content: str
    content_type: str
    metadata: dict[str, object] = field(default_factory=dict)
    etag: str | None = None
    last_modified: str | None = None


class Fetcher(Protocol):
    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        raise NotImplementedError
