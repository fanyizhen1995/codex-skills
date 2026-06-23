from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

try:
    from . import document, paths
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import document  # type: ignore
    import paths  # type: ignore


REQUIRED_FIELDS = ("type", "title", "description", "domain")
ACCEPTED_TYPES = {"Concept", "Paper", "Project", "Decision", "Reference"}
ACCEPTED_STATUSES = {"draft", "reviewed", "stale", "deprecated"}

IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: Path
    message: str


def validate(root: Path, domain: str | None = None) -> list[ValidationIssue]:
    root = Path(root)
    issues: list[ValidationIssue] = []
    pages = [page for page in paths.wiki_pages(root, domain) if page.name != "index.md"]
    docs = [(page, document.load_document(page)) for page in pages]

    for page, doc in docs:
        frontmatter = doc.frontmatter
        for field in REQUIRED_FIELDS:
            if not _has_value(frontmatter.get(field)):
                issues.append(
                    ValidationIssue(
                        code="missing_required",
                        path=page,
                        message=f"Missing required frontmatter field: {field}",
                    )
                )

        wiki_type = frontmatter.get("type")
        if _has_value(wiki_type) and wiki_type not in ACCEPTED_TYPES:
            issues.append(
                ValidationIssue(
                    code="invalid_type",
                    path=page,
                    message=f"Invalid wiki type: {wiki_type}",
                )
            )

        status = frontmatter.get("status")
        if _has_value(status) and status not in ACCEPTED_STATUSES:
            issues.append(
                ValidationIssue(
                    code="invalid_status",
                    path=page,
                    message=f"Invalid status: {status}",
                )
            )

        source_refs = _list_value(frontmatter.get("source_refs"))
        for source_ref in source_refs:
            if _is_local_ref(source_ref) and not _valid_local_target(root, page, source_ref):
                issues.append(
                    ValidationIssue(
                        code="missing_source_ref",
                        path=page,
                        message=f"Missing source_ref target: {source_ref}",
                    )
                )

        for link in _markdown_links(doc.body):
            if _is_markdown_page_ref(link) and not _valid_local_target(root, page, link):
                issues.append(
                    ValidationIssue(
                        code="broken_link",
                        path=page,
                        message=f"Broken Markdown link: {link}",
                    )
                )

        for image in _markdown_images(doc.body):
            if _is_local_ref(image) and not _valid_local_target(root, page, image):
                issues.append(
                    ValidationIssue(
                        code="missing_image",
                        path=page,
                        message=f"Missing image target: {image}",
                    )
                )

        if status == "reviewed" and not _has_sources(source_refs, doc.body):
            issues.append(
                ValidationIssue(
                    code="reviewed_without_sources",
                    path=page,
                    message="Reviewed page requires source_refs or citations",
                )
            )

    issues.extend(_duplicate_issues(docs))
    return issues


def _duplicate_issues(
    docs: list[tuple[Path, document.MarkdownDocument]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    titles: dict[str, Path] = {}
    aliases: dict[str, Path] = {}

    for page, doc in docs:
        title = doc.frontmatter.get("title")
        if _has_value(title):
            normalized_title = str(title).casefold()
            if normalized_title in titles:
                issues.append(
                    ValidationIssue(
                        code="duplicate_title",
                        path=page,
                        message=f"Duplicate title: {title}",
                    )
                )
            else:
                titles[normalized_title] = page

        for alias in _list_value(doc.frontmatter.get("aliases")):
            normalized_alias = alias.casefold()
            if normalized_alias in aliases:
                issues.append(
                    ValidationIssue(
                        code="duplicate_alias",
                        path=page,
                        message=f"Duplicate alias: {alias}",
                    )
                )
            else:
                aliases[normalized_alias] = page

    return issues


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_value(item) for item in value)
    return True


def _list_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _page_relative_path(page: Path, raw_ref: str) -> Path:
    ref = raw_ref.split("#", 1)[0]
    return (page.parent / ref).resolve()


def _valid_local_target(root: Path, page: Path, raw_ref: str) -> bool:
    ref = raw_ref.split("#", 1)[0]
    if Path(ref).is_absolute():
        return False
    target = _page_relative_path(page, raw_ref)
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return False
    return target.exists()


def _is_local_ref(ref: str) -> bool:
    parsed = urlparse(ref)
    return not parsed.scheme and not parsed.netloc and not ref.startswith("#")


def _is_markdown_page_ref(ref: str) -> bool:
    if not _is_local_ref(ref):
        return False
    without_anchor = ref.split("#", 1)[0]
    return without_anchor.endswith(".md")


def _markdown_links(body: str) -> list[str]:
    return [match.group(1) for match in LINK_RE.finditer(body)]


def _markdown_images(body: str) -> list[str]:
    return [match.group(1) for match in IMAGE_RE.finditer(body)]


def _has_sources(source_refs: list[str], body: str) -> bool:
    if source_refs:
        return True

    in_citations = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if stripped.casefold() == "# citations":
                in_citations = True
                continue
            if in_citations:
                break
        elif in_citations and stripped:
            return True
    return False
