from __future__ import annotations

from pathlib import Path
import shutil
import sys

try:
    from . import document, paths
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import document  # type: ignore
    import paths  # type: ignore


PAGE_TYPES = ("Concept", "Paper", "Project", "Decision", "Reference")
SECTION_TITLES = {
    "Concept": "Concepts",
    "Paper": "Papers",
    "Project": "Projects",
    "Decision": "Decisions",
    "Reference": "References",
}


def init_domain(root: Path, domain: str) -> list[Path]:
    root = Path(root)
    domain_root = paths.domain_root(root, domain)
    created = [
        domain_root / "DOMAIN.md",
        domain_root / "ingest.md",
        domain_root / "raw/inbox",
        domain_root / "raw/links",
        domain_root / "raw/notes",
        domain_root / "raw/papers",
        domain_root / "raw/images",
        domain_root / "raw/snapshots",
        domain_root / "wiki/index.md",
        domain_root / "wiki/assets/images",
        domain_root / "wiki/concepts",
        domain_root / "wiki/papers",
        domain_root / "wiki/projects",
        domain_root / "wiki/decisions",
        domain_root / "wiki/references",
    ]

    _copy_template(root / "templates/domain/DOMAIN.md", domain_root / "DOMAIN.md")
    _copy_template(root / "templates/domain/ingest.md", domain_root / "ingest.md")
    _copy_template(root / "templates/domain/wiki/index.md", domain_root / "wiki/index.md")

    for path in created:
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("", encoding="utf-8")
        else:
            path.mkdir(parents=True, exist_ok=True)

    return created


def build_index(root: Path, domain: str) -> Path:
    root = Path(root)
    wiki_root = paths.domain_wiki(root, domain)
    index_path = wiki_root / "index.md"
    grouped: dict[str, list[dict[str, str]]] = {page_type: [] for page_type in PAGE_TYPES}

    for page in _domain_wiki_pages(root, domain):
        doc = document.load_document(page)
        page_type = str(doc.frontmatter.get("type", ""))
        if page_type not in grouped:
            continue
        title = str(doc.frontmatter.get("title") or page.stem)
        description = str(doc.frontmatter.get("description") or "")
        grouped[page_type].append(
            {
                "title": title,
                "description": description,
                "link": page.relative_to(wiki_root).as_posix(),
            }
        )

    lines = [
        "---",
        "type: Index",
        f"title: {domain} Index",
        f"description: Generated index for {domain}.",
        f"domain: {domain}",
        "---",
        "",
        f"# {domain} Index",
        "",
    ]
    for page_type in PAGE_TYPES:
        lines.append(f"## {SECTION_TITLES[page_type]}")
        lines.append("")
        entries = sorted(grouped[page_type], key=lambda item: item["title"].casefold())
        if entries:
            for entry in entries:
                suffix = f" - {entry['description']}" if entry["description"] else ""
                lines.append(f"- [{entry['title']}]({entry['link']}){suffix}")
        else:
            lines.append("_No pages yet._")
        lines.append("")

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return index_path


def _copy_template(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.exists() and not target.exists():
        shutil.copyfile(source, target)


def _domain_wiki_pages(root: Path, domain: str) -> list[Path]:
    return [
        page
        for page in paths.wiki_pages(root, domain)
        if page.name != "index.md"
    ]
