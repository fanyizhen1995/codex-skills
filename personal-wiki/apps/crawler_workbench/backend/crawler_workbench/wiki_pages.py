from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .settings import Settings


class WikiPageError(ValueError):
    pass


def list_wiki_pages(settings: Settings, domain: str) -> list[dict[str, object]]:
    wiki_root = _domain_wiki_root(settings, domain)
    if not wiki_root.exists():
        return []

    pages = []
    resolved_root = wiki_root.resolve()
    for page in sorted(wiki_root.rglob("*.md")):
        if not page.resolve().is_relative_to(resolved_root):
            continue
        relative = page.relative_to(wiki_root).as_posix()
        if page.name == "index.md":
            continue
        pages.append(_page_summary(settings, domain, wiki_root, page))
    return pages


def read_wiki_page(settings: Settings, domain: str, page_path: str) -> dict[str, object]:
    wiki_root = _domain_wiki_root(settings, domain)
    page = _resolve_page_path(wiki_root, page_path)
    content = page.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(content)
    summary = _summary_from_frontmatter(settings, domain, wiki_root, page, frontmatter)
    summary["content"] = content
    summary["body"] = body
    return summary


def _domain_wiki_root(settings: Settings, domain: str) -> Path:
    _validate_domain(domain)
    return settings.wiki_root / "domains" / domain / "wiki"


def _validate_domain(domain: str) -> None:
    if not domain or not domain.strip():
        raise WikiPageError("domain must not be empty")
    path = Path(domain)
    if path.is_absolute() or len(path.parts) != 1 or domain in {".", ".."}:
        raise WikiPageError("invalid domain")
    if "/" in domain or "\\" in domain or ".." in domain:
        raise WikiPageError("invalid domain")


def _resolve_page_path(wiki_root: Path, page_path: str) -> Path:
    if not page_path or not page_path.strip():
        raise WikiPageError("path must not be empty")
    path = Path(page_path)
    if path.is_absolute() or "\\" in page_path or ".." in page_path or not page_path.endswith(".md"):
        raise WikiPageError("invalid wiki page path")

    root = wiki_root.resolve()
    page = wiki_root / path
    resolved = page.resolve()
    if not resolved.is_relative_to(root):
        raise WikiPageError("invalid wiki page path")
    return page


def _page_summary(settings: Settings, domain: str, wiki_root: Path, page: Path) -> dict[str, object]:
    text = page.read_text(encoding="utf-8")
    frontmatter, _body = _parse_frontmatter(text)
    return _summary_from_frontmatter(settings, domain, wiki_root, page, frontmatter)


def _summary_from_frontmatter(
    settings: Settings,
    domain: str,
    wiki_root: Path,
    page: Path,
    frontmatter: dict[str, Any],
) -> dict[str, object]:
    return {
        "domain": domain,
        "path": page.relative_to(wiki_root).as_posix(),
        "full_path": page.relative_to(settings.wiki_root).as_posix(),
        "type": _string_value(frontmatter.get("type")),
        "title": _string_value(frontmatter.get("title")) or page.stem.replace("-", " "),
        "description": _string_value(frontmatter.get("description")),
        "status": _string_value(frontmatter.get("status")),
        "tags": _list_value(frontmatter.get("tags")),
        "source_refs": _list_value(frontmatter.get("source_refs")),
    }


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() != "---":
            continue
        raw_frontmatter = "".join(lines[1:index])
        try:
            loaded = yaml.safe_load(raw_frontmatter) if raw_frontmatter.strip() else {}
        except yaml.YAMLError:
            return {}, "".join(lines[index + 1 :])
        frontmatter = loaded if isinstance(loaded, dict) else {}
        return frontmatter, "".join(lines[index + 1 :])

    return {}, text


def _string_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _list_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []
