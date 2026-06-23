from __future__ import annotations

from pathlib import Path


def repo_root_from(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for path in (current, *current.parents):
        child = path / "personal-wiki"
        if (child / "WIKI.md").is_file():
            return child
        if path.name == "personal-wiki" and (path / "WIKI.md").is_file():
            return path
    raise FileNotFoundError(f"Could not find repository root from {start}")


def domain_root(root: Path, domain: str) -> Path:
    return root / "domains" / domain


def domain_wiki(root: Path, domain: str) -> Path:
    return domain_root(root, domain) / "wiki"


def wiki_pages(root: Path, domain: str | None = None) -> list[Path]:
    base = domain_wiki(root, domain) if domain is not None else root / "global" / "wiki"
    return sorted(base.rglob("*.md")) if base.exists() else []


def raw_pages(root: Path, domain: str | None = None) -> list[Path]:
    base = domain_root(root, domain) / "raw" if domain is not None else root / "global" / "raw"
    return sorted(base.rglob("*.md")) if base.exists() else []
