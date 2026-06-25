from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx


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

    def close(self) -> None:
        raise NotImplementedError


class HttpClientOwner:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client()
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
