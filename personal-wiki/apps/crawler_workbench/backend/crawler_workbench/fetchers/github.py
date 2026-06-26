from __future__ import annotations

import json
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from crawler_workbench.hashing import canonicalize_url

from .base import FetchResult, HttpClientOwner


def _with_closed_query(url: str) -> str:
    parsed = urlsplit(url)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    query_keys = {key for key, value in query_items}
    if "state" not in query_keys:
        query_items.append(("state", "closed"))
    if "per_page" not in query_keys:
        query_items.append(("per_page", "100"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query_items), ""))


def _label_names(labels: object) -> list[str]:
    if not isinstance(labels, list):
        return []
    names: list[str] = []
    for label in labels:
        if isinstance(label, dict):
            name = label.get("name")
            if name:
                names.append(str(name))
        elif label:
            names.append(str(label))
    return names


class GitHubFetcher(HttpClientOwner):
    def __init__(self, client: httpx.Client | None = None) -> None:
        super().__init__(client)

    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        url = str(profile["url"]).rstrip("/")
        headers = self._headers(profile)
        results: list[FetchResult] = []
        seen_urls: set[str] = set()

        for endpoint_url, endpoint_kind in self._endpoint_urls(url):
            response = self.client.get(endpoint_url, headers=headers, timeout=60)
            response.raise_for_status()
            payload = json.loads(response.text)
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                github_kind = self._github_kind(item, str(item.get("html_url") or item.get("url") or ""), endpoint_kind)
                if github_kind != endpoint_kind:
                    continue
                result = self._result_for_item(item, github_kind)
                if result.canonical_url in seen_urls:
                    continue
                seen_urls.add(result.canonical_url)
                results.append(result)

        return results

    def _headers(self, profile: dict[str, object]) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if (
            bool(profile.get("auth_required"))
            and profile.get("auth_method") == "env_token"
            and profile.get("auth_ref") == "GITHUB_TOKEN"
            and _is_github_api_url(str(profile["url"]))
            and token
        ):
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _endpoint_urls(self, url: str) -> list[tuple[str, str]]:
        parsed = urlsplit(url)
        path = parsed.path.rstrip("/")
        if path.endswith("/issues"):
            return [(_with_closed_query(url), "issue")]
        if path.endswith("/pulls"):
            return [(_with_closed_query(url), "pull_request")]
        query = parsed.query
        return [
            (_with_closed_query(urlunsplit((parsed.scheme, parsed.netloc, f"{path}/issues", query, ""))), "issue"),
            (_with_closed_query(urlunsplit((parsed.scheme, parsed.netloc, f"{path}/pulls", query, ""))), "pull_request"),
        ]

    def _result_for_item(self, item: dict[str, object], github_kind: str) -> FetchResult:
        html_url = str(item.get("html_url") or item.get("url") or "")
        title = str(item.get("title") or html_url)
        state = str(item.get("state") or "")
        labels = _label_names(item.get("labels"))
        closed_at = item.get("closed_at")
        merged_at = item.get("merged_at")
        label_text = ", ".join(labels)
        body = str(item.get("body") or "")
        content = "\n".join(
            [
                f"# {title}",
                "",
                f"URL: {html_url}",
                f"State: {state}",
                f"Labels: {label_text}",
                f"Closed at: {closed_at or ''}",
                f"Merged at: {merged_at or ''}",
                "",
                body,
            ]
        ).strip()
        return FetchResult(
            canonical_url=canonicalize_url(html_url),
            title=title,
            content=content,
            content_type="application/vnd.github+json",
            metadata={
                "github_kind": github_kind,
                "number": item.get("number"),
                "state": state,
                "labels": labels,
                "closed_at": closed_at,
                "merged_at": merged_at,
            },
        )

    def _github_kind(self, item: dict[str, object], html_url: str, endpoint_kind: str) -> str:
        if item.get("pull_request") or "/pull/" in html_url:
            return "pull_request"
        return endpoint_kind


def _is_github_api_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.hostname == "api.github.com"
