from __future__ import annotations

import feedparser
import httpx

from crawler_workbench.hashing import canonicalize_url

from .base import FetchResult, HttpClientOwner


class RssFetcher(HttpClientOwner):
    def __init__(self, client: httpx.Client | None = None) -> None:
        super().__init__(client)

    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        url = str(profile["url"])
        response = self.client.get(url, timeout=30)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        results: list[FetchResult] = []
        for entry in feed.entries:
            entry_url = entry.get("link") or entry.get("id") or entry.get("guid") or url
            canonical_url = canonicalize_url(entry_url)
            title = entry.get("title") or str(profile.get("name") or entry_url)
            summary = entry.get("summary") or entry.get("description") or ""
            content = "\n".join(
                [
                    f"# {title}",
                    "",
                    f"URL: {canonical_url}",
                    "",
                    summary,
                ]
            ).strip()
            results.append(
                FetchResult(
                    canonical_url=canonical_url,
                    title=title,
                    content=content,
                    content_type=response.headers.get("content-type", "application/rss+xml"),
                    metadata={"feed_url": url, "feed_title": feed.feed.get("title", "")},
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
            )
        return results
