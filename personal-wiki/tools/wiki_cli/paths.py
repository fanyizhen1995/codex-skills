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
    domain_path = Path(domain)
    if domain_path.is_absolute() or not domain_path.parts:
        raise ValueError(f"Invalid domain path: {domain}")
    if any(part in ("", ".", "..") for part in domain_path.parts):
        raise ValueError(f"Invalid domain path: {domain}")

    domains_root = root / "domains"
    resolved = (domains_root / domain_path).resolve(strict=False)
    try:
        resolved.relative_to(domains_root.resolve(strict=False))
    except ValueError as error:
        raise ValueError(f"Invalid domain path: {domain}") from error
    return domains_root / domain_path


def domain_wiki(root: Path, domain: str) -> Path:
    return domain_root(root, domain) / "wiki"


def wiki_pages(root: Path, domain: str | None = None) -> list[Path]:
    if domain is not None:
        base = domain_wiki(root, domain)
        return sorted(base.rglob("*.md")) if base.exists() else []

    pages: list[Path] = []
    global_wiki = root / "global" / "wiki"
    if global_wiki.exists():
        pages.extend(global_wiki.rglob("*.md"))

    domains_root = root / "domains"
    if domains_root.exists():
        for domain_root_path in sorted(path for path in domains_root.iterdir() if path.is_dir()):
            wiki_root = domain_root_path / "wiki"
            if wiki_root.exists():
                pages.extend(wiki_root.rglob("*.md"))

    return sorted(pages)


def raw_pages(root: Path, domain: str | None = None) -> list[Path]:
    base = domain_root(root, domain) / "raw" if domain is not None else root / "global" / "raw"
    return sorted(base.rglob("*.md")) if base.exists() else []
