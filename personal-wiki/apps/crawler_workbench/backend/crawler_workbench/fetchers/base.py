from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse
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
    attachment_bytes: bytes | None = None
    attachment_extension: str | None = None
    attachment_content_type: str | None = None


class Fetcher(Protocol):
    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class ResilientHttpClient:
    def __init__(self, client_factory=None) -> None:
        client_factory = client_factory or httpx.Client
        self._env_client = client_factory()
        self._direct_client = client_factory(trust_env=False)

    def get(self, url: str, **kwargs):
        kwargs.setdefault("follow_redirects", True)
        kwargs.setdefault("timeout", 60)
        try:
            response = self._env_client.get(url, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            if _should_retry_without_env_proxy(url):
                return self._direct_client.get(url, **kwargs)
            raise
        if _should_retry_response_without_env_proxy(url, response):
            return self._direct_client.get(url, **kwargs)
        return response

    def close(self) -> None:
        self._env_client.close()
        self._direct_client.close()


class HttpClientOwner:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or ResilientHttpClient()
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def _should_retry_without_env_proxy(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host == "api.github.com":
        return True
    if host == "github.com" or host.endswith(".github.com"):
        return False
    return True


def _should_retry_response_without_env_proxy(url: str, response) -> bool:
    if not _should_retry_without_env_proxy(url):
        return False
    return response.status_code >= 500 and not response.content
