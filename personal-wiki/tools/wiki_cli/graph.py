from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
import sys
from urllib.parse import urlparse

try:
    from . import document, paths
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import document  # type: ignore
    import paths  # type: ignore


LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def collect_backlinks(root: Path, domain: str | None = None) -> dict[str, list[str]]:
    root = Path(root)
    pages = _wiki_pages(root, domain)
    page_ids = {_page_id(root, page): page for page in pages}
    backlinks: dict[str, list[str]] = {}

    for source in pages:
        source_id = _page_id(root, source)
        for target_id in _resolved_targets(root, source, page_ids):
            backlinks.setdefault(target_id, []).append(source_id)

    return {
        target: sorted(sources)
        for target, sources in sorted(backlinks.items())
    }


def build_graph(root: Path, domain: str | None = None) -> dict[str, Any]:
    root = Path(root)
    pages = _wiki_pages(root, domain)
    page_ids = {_page_id(root, page): page for page in pages}
    nodes = [_node(root, page) for page in pages]
    edges = []

    for source in pages:
        source_id = _page_id(root, source)
        for target_id in _resolved_targets(root, source, page_ids):
            edges.append({"source": source_id, "target": target_id})

    return {
        "nodes": sorted(nodes, key=lambda node: node["id"]),
        "edges": sorted(edges, key=lambda edge: (edge["source"], edge["target"])),
    }


def write_graph(root: Path, domain: str | None, out: Path) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_graph(root, domain), indent=2) + "\n", encoding="utf-8")
    return out


def _wiki_pages(root: Path, domain: str | None) -> list[Path]:
    return [
        page
        for page in paths.wiki_pages(root, domain)
        if page.name != "index.md"
    ]


def _node(root: Path, page: Path) -> dict[str, Any]:
    doc = document.load_document(page)
    return {
        "id": _page_id(root, page),
        "path": page.relative_to(root).as_posix(),
        "title": str(doc.frontmatter.get("title") or page.stem),
        "type": str(doc.frontmatter.get("type") or ""),
        "tags": _list_value(doc.frontmatter.get("tags")),
        "description": str(doc.frontmatter.get("description") or ""),
    }


def _resolved_targets(
    root: Path,
    source: Path,
    page_ids: dict[str, Path],
) -> list[str]:
    doc = document.load_document(source)
    targets: list[str] = []
    seen: set[str] = set()

    for link in LINK_RE.findall(doc.body):
        if not _is_local_markdown_link(link):
            continue
        target = (source.parent / link.split("#", 1)[0]).resolve()
        try:
            target_id = target.relative_to(root.resolve()).with_suffix("").as_posix()
        except ValueError:
            continue
        if target_id in page_ids and target_id not in seen:
            targets.append(target_id)
            seen.add(target_id)

    return targets


def _page_id(root: Path, page: Path) -> str:
    return page.relative_to(root).with_suffix("").as_posix()


def _is_local_markdown_link(link: str) -> bool:
    parsed = urlparse(link)
    if parsed.scheme or parsed.netloc or link.startswith("#"):
        return False
    return link.split("#", 1)[0].endswith(".md")


def _list_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [str(value)]
