from __future__ import annotations

from .arxiv import ArxivFetcher
from .base import FetchResult, Fetcher
from .github import GitHubFetcher
from .rss import RssFetcher
from .web import WebFetcher


def fetcher_for(source_type: str) -> Fetcher:
    if source_type == "web":
        return WebFetcher()
    if source_type == "rss":
        return RssFetcher()
    if source_type == "github":
        return GitHubFetcher()
    if source_type == "arxiv":
        return ArxivFetcher()
    raise ValueError(f"Unsupported source type: {source_type}")


__all__ = ["FetchResult", "Fetcher", "fetcher_for"]
