from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import re
import sys
from urllib.error import URLError
from urllib.request import urlopen


try:
    from . import document, paths
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import document  # type: ignore
    import paths  # type: ignore


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def snapshot_url(root: Path, domain: str, url: str, *, fetch: bool = False) -> Path:
    domain_root = _domain_root(root, domain)
    path = domain_root / "raw" / "links" / f"{_url_slug(url)}.md"
    captured = date.today().isoformat()
    body = _snapshot_body(url, fetch)
    document.write_document(
        path,
        document.MarkdownDocument(
            frontmatter={
                "type": "RawSource",
                "title": url,
                "source_kind": "web",
                "url": url,
                "captured": captured,
                "status": "pending",
            },
            body=body,
        ),
    )
    return path


def image_note(root: Path, domain: str, image_path: str) -> Path:
    domain_root = _domain_root(root, domain)
    raw_image = _domain_relative_path(domain_root, image_path)
    image_stem = slugify(Path(image_path).stem)
    path = domain_root / "wiki" / "references" / f"{image_stem}-image.md"
    source_ref = _relative_between(path.parent, raw_image)
    document.write_document(
        path,
        document.MarkdownDocument(
            frontmatter={
                "type": "Reference",
                "title": f"{Path(image_path).stem} image",
                "description": f"Reference note for {Path(image_path).stem} image.",
                "domain": domain,
                "status": "draft",
                "source_refs": [source_ref],
            },
            body=(
                "# Image Meaning\n"
                "- Describe what the image shows and why it matters.\n\n"
                "# Image Source\n"
                f"- Raw image: {image_path}\n"
            ),
        ),
    )
    return path


def ingest_plan(root: Path, domain: str, raw_path: str) -> Path:
    domain_root = _domain_root(root, domain)
    raw = _domain_relative_path(domain_root, raw_path)
    output = raw.with_name(f"{raw.stem}.ingest-plan.md")
    relative_raw = _relative_to_domain(domain_root, raw)
    body = (
        "# Ingest Plan\n\n"
        f"Source path: {relative_raw}\n\n"
        "## Candidate page types\n"
        "- Concept\n"
        "- Paper\n"
        "- Reference\n"
        "- Project\n\n"
        "## Next steps\n"
        "- Review the raw source and identify durable claims.\n"
        "- Choose the smallest appropriate wiki page type for each claim.\n"
        "- Preserve source_refs back to the raw source.\n"
        "- Update the ingest log after drafted pages are reviewed.\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    update_ingest_log(root, domain, relative_raw, _relative_to_domain(domain_root, output))
    return output


def update_ingest_log(root: Path, domain: str, raw_path: str, output_path: str) -> Path:
    path = _domain_root(root, domain) / "ingest.md"
    entry = f"- [ ] {raw_path} -> {output_path} (pending)"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if entry in text:
            return path
        if text and not text.endswith("\n"):
            text += "\n"
    else:
        text = "# Ingest Log\n\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + entry + "\n", encoding="utf-8")
    return path


def _url_slug(url: str) -> str:
    cleaned = re.sub(r"^https?://", "", url.lower())
    cleaned = re.sub(r"^www\.", "", cleaned)
    return slugify(cleaned)


def _snapshot_body(url: str, fetch: bool) -> str:
    if not fetch:
        return (
            "# Snapshot\n\n"
            f"URL: {url}\n\n"
            "Live fetching was not requested. Re-run with fetch enabled to store "
            "the current page text.\n"
        )

    try:
        with urlopen(url, timeout=10) as response:
            content_type = response.headers.get("content-type", "")
            payload = response.read(500_000)
        text = payload.decode("utf-8", errors="replace")
        return f"# Snapshot\n\nURL: {url}\n\nContent-Type: {content_type}\n\n{text}\n"
    except (OSError, URLError) as error:
        return f"# Snapshot\n\nURL: {url}\n\nFetch failed: {error}\n"


def _domain_root(root: Path, domain: str) -> Path:
    _validate_domain(domain)
    return paths.domain_root(root, domain)


def _validate_domain(domain: str) -> None:
    path = Path(domain)
    if path.is_absolute() or not path.parts:
        raise ValueError(f"Invalid domain path: {domain}")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"Invalid domain path: {domain}")


def _domain_relative_path(domain_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (domain_root / path).resolve()
    _ensure_inside_domain(domain_root, resolved)
    return resolved


def _relative_to_domain(domain_root: Path, path: Path) -> str:
    return path.resolve().relative_to(domain_root.resolve()).as_posix()


def _relative_between(base: Path, target: Path) -> str:
    return Path(os.path.relpath(target.resolve(), start=base.resolve())).as_posix()


def _ensure_inside_domain(domain_root: Path, path: Path) -> None:
    try:
        path.relative_to(domain_root.resolve())
    except ValueError as error:
        raise ValueError(f"Path is outside domain: {path}") from error
