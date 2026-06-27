from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import yaml

from .hashing import content_hash, slugify_url
from .settings import Settings


@dataclass(frozen=True)
class RawWrite:
    path: Path
    content_hash: str
    content_bytes: int
    metadata_json: str
    attachment_path: Path | None = None


def _metadata_json(metadata: dict[str, object]) -> str:
    try:
        return json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    except TypeError as exc:
        raise TypeError(f"metadata must be JSON serializable: {exc}") from exc


def _validate_single_path_segment(value: str, label: str) -> None:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or len(path.parts) != 1
        or "/" in value
        or "\\" in value
        or ".." in path.parts
    ):
        raise ValueError(f"Invalid {label} path: {value}")


def raw_capture_hash(content: str, attachment_bytes: bytes | None = None) -> str:
    if attachment_bytes is None:
        return content_hash(content)
    attachment_sha256 = hashlib.sha256(attachment_bytes).hexdigest()
    return content_hash(f"{content.strip()}\n\nAttachment-SHA256: {attachment_sha256}")


def _exclusive_write(path: Path, body: str) -> Path:
    for suffix in ["", *[f"-{index}" for index in range(2, 1000)]]:
        candidate = path.with_name(f"{path.stem}{suffix}{path.suffix}")
        try:
            with candidate.open("x", encoding="utf-8") as file:
                file.write(body)
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError(f"could not create unique raw capture path for {path}")


def _exclusive_write_bytes(path: Path, body: bytes) -> Path:
    for suffix in ["", *[f"-{index}" for index in range(2, 1000)]]:
        candidate = path.with_name(f"{path.stem}{suffix}{path.suffix}")
        try:
            with candidate.open("xb") as file:
                file.write(body)
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError(f"could not create unique raw attachment path for {path}")


def write_raw_item(
    settings: Settings,
    source_id: str,
    target_domain: str,
    canonical_url: str,
    title: str,
    content: str,
    metadata: dict[str, object],
    attachment_bytes: bytes | None = None,
    attachment_extension: str | None = None,
    attachment_content_type: str | None = None,
) -> RawWrite:
    _validate_single_path_segment(source_id, "source id")
    _validate_single_path_segment(target_domain, "domain")
    now = datetime.now(timezone.utc)
    digest = raw_capture_hash(content, attachment_bytes)
    metadata_for_write = dict(metadata)
    attachment_fields: dict[str, object] = {}
    if attachment_bytes is not None:
        extension = attachment_extension or ".bin"
        if not extension.startswith("."):
            extension = f".{extension}"
        attachment_fields = {
            "attachment_filename": "",
            "attachment_sha256": hashlib.sha256(attachment_bytes).hexdigest(),
            "attachment_content_type": attachment_content_type or "application/octet-stream",
        }
        metadata_for_write.update(attachment_fields)
    metadata_json = _metadata_json(metadata_for_write)
    raw_dir = settings.wiki_root / "domains" / target_domain / "raw" / "crawler" / source_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}-{slugify_url(canonical_url)}-{digest[:10]}.md"
    frontmatter_data: dict[str, object] = {
        "source_id": source_id,
        "title": title,
        "canonical_url": canonical_url,
        "captured_at": now.isoformat(),
        "content_hash": digest,
    }
    frontmatter_data.update(attachment_fields)
    frontmatter = yaml.safe_dump(
        frontmatter_data,
        sort_keys=False,
        allow_unicode=True,
    ).rstrip()
    body = (
        "---\n"
        f"{frontmatter}\n"
        "---\n"
        f"{content.strip()}\n"
    )
    path = _exclusive_write(path, body)
    attachment_path: Path | None = None
    if attachment_bytes is not None:
        try:
            attachment_path = path.with_suffix(extension)
            attachment_path = _exclusive_write_bytes(attachment_path, attachment_bytes)
            metadata_for_write["attachment_filename"] = attachment_path.name
            metadata_json = _metadata_json(metadata_for_write)
            frontmatter_data["attachment_filename"] = attachment_path.name
            frontmatter = yaml.safe_dump(
                frontmatter_data,
                sort_keys=False,
                allow_unicode=True,
            ).rstrip()
            body = (
                "---\n"
                f"{frontmatter}\n"
                "---\n"
                f"{content.strip()}\n"
            )
            path.write_text(body, encoding="utf-8")
        except Exception:
            path.unlink(missing_ok=True)
            if attachment_path is not None:
                attachment_path.unlink(missing_ok=True)
            raise
    return RawWrite(
        path=path,
        content_hash=digest,
        content_bytes=len(body.encode("utf-8")),
        metadata_json=metadata_json,
        attachment_path=attachment_path,
    )
