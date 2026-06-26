from __future__ import annotations

import feedparser
import httpx
from html.parser import HTMLParser
import re

from crawler_workbench.hashing import canonicalize_url

from .base import FetchResult, HttpClientOwner


class _ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.article_parts: list[str] = []
        self.main_parts: list[str] = []
        self.body_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0
        self._article_depth = 0
        self._main_depth = 0
        self._body_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "article":
            self._article_depth += 1
        if tag == "main":
            self._main_depth += 1
        if tag == "body":
            self._body_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag == "body" and self._body_depth:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
            return
        if self._skip_depth:
            return
        if self._article_depth:
            self.article_parts.append(data)
        elif self._main_depth:
            self.main_parts.append(data)
        elif self._body_depth:
            self.body_parts.append(data)

    def article_text(self) -> str:
        for parts in [self.article_parts, self.main_parts, self.body_parts]:
            text = _compact_text("\n".join(parts))
            if text:
                return text
        return ""

    def title(self) -> str:
        return _compact_text(" ".join(self.title_parts))


def _compact_text(value: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t\r\f\v]+", " ", value)).strip()


def _profile_list(profile: dict[str, object], key: str) -> list[str]:
    value = profile.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _profile_int(profile: dict[str, object], key: str) -> int | None:
    value = profile.get(key)
    if value is None:
        return None
    try:
        parsed = int(str(value))
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _matches_keywords(entry, keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack = " ".join(
        str(entry.get(key, ""))
        for key in ["title", "summary", "description", "content", "tags"]
    ).lower()
    return any(keyword.lower() in haystack for keyword in keywords)


class RssFetcher(HttpClientOwner):
    def __init__(self, client: httpx.Client | None = None) -> None:
        super().__init__(client)

    def fetch(self, profile: dict[str, object]) -> list[FetchResult]:
        url = str(profile["url"])
        response = self.client.get(url, timeout=60)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        results: list[FetchResult] = []
        include_keywords = _profile_list(profile, "include_keywords")
        fetch_article_body = bool(profile.get("fetch_article_body"))
        max_entries = _profile_int(profile, "max_entries")
        for entry in feed.entries:
            if not _matches_keywords(entry, include_keywords):
                continue
            if max_entries is not None and len(results) >= max_entries:
                break
            entry_url = entry.get("link") or entry.get("id") or entry.get("guid") or url
            canonical_url = canonicalize_url(entry_url)
            title = entry.get("title") or str(profile.get("name") or entry_url)
            summary = entry.get("summary") or entry.get("description") or ""
            metadata: dict[str, object] = {
                "feed_url": url,
                "feed_title": feed.feed.get("title", ""),
                "entry_url": entry_url,
                "entry_id": entry.get("id") or entry.get("guid") or "",
                "published": entry.get("published") or "",
                "updated": entry.get("updated") or "",
                "rss_summary": summary,
            }
            content_type = response.headers.get("content-type", "application/rss+xml")
            last_modified = response.headers.get("last-modified")
            article_text = ""
            article_url = entry_url
            if fetch_article_body and article_url:
                article_text, article_title, article_response = self._fetch_article(article_url, metadata)
                if article_title:
                    title = title or article_title
                if article_response is not None:
                    content_type = article_response.headers.get("content-type", content_type)
                    last_modified = article_response.headers.get("last-modified", last_modified)
            content = "\n".join(
                [
                    f"# {title}",
                    "",
                    f"URL: {canonical_url}",
                    "",
                    "RSS Summary:",
                    summary,
                    "",
                    "Article Body:",
                    article_text,
                ]
            ).strip()
            results.append(
                FetchResult(
                    canonical_url=canonical_url,
                    title=title,
                    content=content,
                    content_type=content_type,
                    metadata=metadata,
                    etag=response.headers.get("etag"),
                    last_modified=last_modified,
                )
            )
        return results

    def _fetch_article(
        self,
        article_url: str,
        metadata: dict[str, object],
    ) -> tuple[str, str, httpx.Response | None]:
        try:
            response = self.client.get(article_url, timeout=60)
            metadata["article_fetch_status"] = response.status_code
            metadata["article_content_type"] = response.headers.get("content-type", "")
            response.raise_for_status()
            parser = _ArticleTextParser()
            parser.feed(response.text)
            article_text = parser.article_text()
            if article_text:
                metadata["article_fetch_method"] = "http"
                return article_text, parser.title(), response
            metadata["article_fetch_method"] = "summary"
            metadata["article_fetch_error"] = "empty article text"
            return "", parser.title(), response
        except Exception as exc:
            metadata["article_fetch_method"] = "summary"
            metadata.setdefault("article_fetch_status", None)
            metadata["article_fetch_error"] = str(exc)
            return "", "", None
