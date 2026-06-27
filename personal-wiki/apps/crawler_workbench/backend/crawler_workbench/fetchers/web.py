from __future__ import annotations

import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

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


def _is_pdf_response(url: str, content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type == "application/pdf":
        return True
    return urlsplit(url).path.lower().endswith(".pdf")


def _extract_pdf_text(pdf_bytes: bytes) -> tuple[str, str | None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "input.pdf"
        text_path = Path(tmpdir) / "output.txt"
        pdf_path.write_bytes(pdf_bytes)
        try:
            completed = subprocess.run(
                ["/usr/bin/pdftotext", str(pdf_path), str(text_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception as exc:
            return "", str(exc)
        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or f"pdftotext exited {completed.returncode}").strip()
            return "", error
        try:
            return text_path.read_text(encoding="utf-8").strip(), None
        except OSError as exc:
            return "", str(exc)


class WebFetcher(HttpClientOwner):
    def __init__(self, client: httpx.Client | None = None) -> None:
        super().__init__(client)

    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        url = str(profile["url"])
        canonical_url = canonicalize_url(url)
        response = self.client.get(url, timeout=60)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "text/html")
        etag = response.headers.get("etag")
        last_modified = response.headers.get("last-modified")
        if _is_pdf_response(url, content_type):
            return [self._pdf_result(url, canonical_url, profile, response.content, content_type, etag, last_modified)]

        parser = _TextCaptureParser()
        parser.feed(response.text)
        title = _compact_text(" ".join(parser.title_parts)) or str(profile.get("name") or url)
        text = _compact_text(" ".join(parser.text_parts))

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

    def _pdf_result(
        self,
        url: str,
        canonical_url: str,
        profile: dict[str, object],
        pdf_bytes: bytes,
        content_type: str,
        etag: str | None,
        last_modified: str | None,
    ) -> FetchResult:
        title = str(profile.get("name") or Path(urlsplit(url).path).name or url)
        extracted_text, extract_error = _extract_pdf_text(pdf_bytes)
        metadata: dict[str, object] = {"source_url": url}
        if extract_error:
            metadata["pdf_extract_error"] = extract_error
        body_lines = [
            f"# {title}",
            "",
            f"URL: {url}",
            "",
            "Headers:",
            f"- Content-Type: {content_type}",
            f"- ETag: {etag or ''}",
            f"- Last-Modified: {last_modified or ''}",
            "",
        ]
        if extracted_text:
            body_lines.append(extracted_text)
        else:
            body_lines.append(f"PDF text extraction failed: {extract_error or 'no text extracted'}")
        return FetchResult(
            canonical_url=canonical_url,
            title=title,
            content="\n".join(body_lines).strip(),
            content_type=content_type,
            metadata=metadata,
            etag=etag,
            last_modified=last_modified,
            attachment_bytes=pdf_bytes,
            attachment_extension=".pdf",
            attachment_content_type="application/pdf",
        )
