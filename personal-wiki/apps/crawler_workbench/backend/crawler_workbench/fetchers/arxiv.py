from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from crawler_workbench.hashing import canonicalize_url

from .base import FetchResult, HttpClientOwner


ATOM = {"atom": "http://www.w3.org/2005/Atom"}


def _text(element: ET.Element, path: str) -> str:
    found = element.find(path, ATOM)
    return _compact(found.text or "") if found is not None else ""


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class ArxivFetcher(HttpClientOwner):
    def __init__(self, client: httpx.Client | None = None) -> None:
        super().__init__(client)

    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        url = str(profile["url"])
        response = self.client.get(url, timeout=60)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        results: list[FetchResult] = []
        for entry in root.findall("atom:entry", ATOM):
            paper_url = _text(entry, "atom:id") or url
            canonical_paper_url = canonicalize_url(paper_url)
            title = _text(entry, "atom:title") or str(profile.get("name") or paper_url)
            summary = _text(entry, "atom:summary")
            authors = [_compact(author.text or "") for author in entry.findall("atom:author/atom:name", ATOM)]
            authors = [author for author in authors if author]
            published = _text(entry, "atom:published")
            updated = _text(entry, "atom:updated")
            content = "\n".join(
                [
                    f"# {title}",
                    "",
                    f"URL: {paper_url}",
                    f"Authors: {', '.join(authors)}",
                    f"Published: {published}",
                    f"Updated: {updated}",
                    "",
                    summary,
                ]
            ).strip()
            results.append(
                FetchResult(
                    canonical_url=canonical_paper_url,
                    title=title,
                    content=content,
                    content_type=response.headers.get("content-type", "application/atom+xml"),
                    metadata={
                        "source_url": url,
                        "authors": authors,
                        "published": published,
                        "updated": updated,
                    },
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
            )
        return results
