from __future__ import annotations

from pathlib import Path
import re
import sqlite3
from typing import Any

import yaml

from .settings import Settings


BODY_EXCERPT_CHARS = 2_000


def rebuild_search_index(settings: Settings, db: sqlite3.Connection, domain: str | None = None) -> int:
    if domain is not None:
        _validate_domain(domain)

    if domain is None:
        db.execute("delete from wiki_search_fts")
    else:
        db.execute("delete from wiki_search_fts where domain = ?", (domain,))

    count = 0
    for page in _wiki_pages(settings, domain):
        count += _insert_wiki_page(settings, db, page)
    count += _insert_raw_items(db, domain)
    db.commit()
    return count


def search_wiki(
    db: sqlite3.Connection,
    query: str,
    domain: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    if domain is not None:
        _validate_domain(domain)

    if limit <= 0:
        return []

    normalized_query = _fts_query(query)
    if normalized_query:
        where = ["wiki_search_fts match ?"]
        params: list[object] = [normalized_query]
        if domain is not None:
            where.append("domain = ?")
            params.append(domain)
        params.append(limit)
        rows = db.execute(
            f"""
            select
              path,
              domain,
              title,
              description,
              snippet(wiki_search_fts, -1, '<mark>', '</mark>', '...', 24) as snippet,
              bm25(wiki_search_fts) as score
            from wiki_search_fts
            where {' and '.join(where)}
            order by score
            limit ?
            """,
            params,
        ).fetchall()
    else:
        where = []
        params = []
        if domain is not None:
            where.append("domain = ?")
            params.append(domain)
        params.append(limit)
        where_sql = f"where {' and '.join(where)}" if where else ""
        rows = db.execute(
            f"""
            select
              path,
              domain,
              title,
              description,
              coalesce(nullif(description, ''), nullif(body, ''), raw_metadata, title) as snippet,
              0.0 as score
            from wiki_search_fts
            {where_sql}
            order by path
            limit ?
            """,
            params,
        ).fetchall()

    return [
        {
            "path": row["path"],
            "domain": row["domain"],
            "title": row["title"],
            "description": row["description"],
            "snippet": row["snippet"],
            "score": row["score"],
        }
        for row in rows
    ]


def _wiki_pages(settings: Settings, domain: str | None) -> list[Path]:
    domains_root = settings.wiki_root / "domains"
    if domain is not None:
        wiki_roots = [_domain_wiki_root(domains_root, domain)]
    elif domains_root.exists():
        wiki_roots = [
            domain_root / "wiki"
            for domain_root in sorted(path for path in domains_root.iterdir() if path.is_dir())
        ]
    else:
        wiki_roots = []

    pages: list[Path] = []
    for wiki_root in wiki_roots:
        if not wiki_root.exists():
            continue
        pages.extend(
            page
            for page in wiki_root.rglob("*.md")
            if page.name != "index.md" and page.name != "backlinks.json"
        )
    return sorted(pages)


def _domain_wiki_root(domains_root: Path, domain: str) -> Path:
    _validate_domain(domain)
    return domains_root / domain / "wiki"


def _validate_domain(domain: str) -> None:
    domain_path = Path(domain)
    if (
        not domain
        or domain_path.is_absolute()
        or len(domain_path.parts) != 1
        or "/" in domain
        or "\\" in domain
        or ".." in domain_path.parts
    ):
        raise ValueError(f"Invalid domain path: {domain}")


def _insert_wiki_page(settings: Settings, db: sqlite3.Connection, page: Path) -> int:
    text = page.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(text)
    path = page.relative_to(settings.wiki_root).as_posix()
    page_domain = _domain_from_path(settings, page)
    title = _string_value(frontmatter.get("title")) or page.stem.replace("-", " ")
    description = _string_value(frontmatter.get("description"))
    source_refs = _joined_values(frontmatter.get("source_refs"))
    db.execute(
        """
        insert into wiki_search_fts (
          path, domain, title, description, body, source_refs, raw_metadata
        )
        values (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            path,
            page_domain,
            title,
            description,
            body.strip()[:BODY_EXCERPT_CHARS],
            source_refs,
            "",
        ),
    )
    return 1


def _insert_raw_items(db: sqlite3.Connection, domain: str | None) -> int:
    if domain is None:
        rows = db.execute(
            """
            select raw_path, target_domain, title, canonical_url
            from raw_items
            order by id
            """
        ).fetchall()
    else:
        rows = db.execute(
            """
            select raw_path, target_domain, title, canonical_url
            from raw_items
            where target_domain = ?
            order by id
            """,
            (domain,),
        ).fetchall()

    for row in rows:
        raw_metadata = "\n".join(
            value
            for value in (str(row["title"] or ""), str(row["canonical_url"] or ""))
            if value
        )
        db.execute(
            """
            insert into wiki_search_fts (
              path, domain, title, description, body, source_refs, raw_metadata
            )
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["raw_path"],
                row["target_domain"],
                row["title"],
                "",
                "",
                "",
                raw_metadata,
            ),
        )
    return len(rows)


def _domain_from_path(settings: Settings, page: Path) -> str:
    relative = page.relative_to(settings.wiki_root / "domains")
    return relative.parts[0]


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


def _joined_values(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _fts_query(query: str) -> str:
    terms = [term.replace('"', '""') for term in re.findall(r"\w+", query)]
    return " ".join(f'"{term}"' for term in terms)
