from __future__ import annotations

import re
from html.parser import HTMLParser

import httpx

from crawler_workbench.hashing import canonicalize_url

from .base import FetchResult, HttpClientOwner


class _TextCaptureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        if tag.lower() in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
            return
        if not self._skip_depth:
            self.text_parts.append(data)


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class WebFetcher(HttpClientOwner):
    def __init__(self, client: httpx.Client | None = None) -> None:
        super().__init__(client)

    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        url = str(profile["url"])
        canonical_url = canonicalize_url(url)
        response = self.client.get(url, timeout=60)
        response.raise_for_status()

        parser = _TextCaptureParser()
        parser.feed(response.text)
        title = _compact_text(" ".join(parser.title_parts)) or str(profile.get("name") or url)
        text = _compact_text(" ".join(parser.text_parts))
        etag = response.headers.get("etag")
        last_modified = response.headers.get("last-modified")
        content_type = response.headers.get("content-type", "text/html")

        header_lines = [
            f"- Content-Type: {content_type}",
            f"- ETag: {etag or ''}",
            f"- Last-Modified: {last_modified or ''}",
        ]
        content = "\n".join(
            [
                f"# {title}",
                "",
                f"URL: {url}",
                "",
                "Headers:",
                *header_lines,
                "",
                text,
            ]
        ).strip()

        return [
            FetchResult(
                canonical_url=canonical_url,
                title=title,
                content=content,
                content_type=content_type,
                metadata={"source_url": url},
                etag=etag,
                last_modified=last_modified,
            )
        ]
