from __future__ import annotations

from datetime import date
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
    path = paths.domain_root(root, domain) / "raw" / "links" / f"{_url_slug(url)}.md"
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
    image_stem = slugify(Path(image_path).stem)
    path = paths.domain_wiki(root, domain) / "references" / f"{image_stem}-image.md"
    document.write_document(
        path,
        document.MarkdownDocument(
            frontmatter={
                "type": "Reference",
                "title": f"{Path(image_path).stem} image",
                "domain": domain,
                "status": "draft",
                "source_refs": [image_path],
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
    raw = _domain_relative_path(root, domain, raw_path)
    output = raw.with_name(f"{raw.stem}.ingest-plan.md")
    relative_raw = _relative_to_domain(root, domain, raw)
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
    update_ingest_log(root, domain, relative_raw, _relative_to_domain(root, domain, output))
    return output


def update_ingest_log(root: Path, domain: str, raw_path: str, output_path: str) -> Path:
    path = paths.domain_root(root, domain) / "ingest.md"
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


def _domain_relative_path(root: Path, domain: str, value: str) -> Path:
    path = Path(value)
    domain_root = paths.domain_root(root, domain)
    if path.is_absolute():
        return path
    if path.parts[:2] == ("domains", domain):
        return root / path
    return domain_root / path


def _relative_to_domain(root: Path, domain: str, path: Path) -> str:
    return path.relative_to(paths.domain_root(root, domain)).as_posix()
