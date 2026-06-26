from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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


def _metadata_json(metadata: dict[str, object]) -> str:
    try:
        return json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    except TypeError as exc:
        raise TypeError(f"metadata must be JSON serializable: {exc}") from exc


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


def write_raw_item(
    settings: Settings,
    source_id: str,
    target_domain: str,
    canonical_url: str,
    title: str,
    content: str,
    metadata: dict[str, object],
) -> RawWrite:
    now = datetime.now(timezone.utc)
    digest = content_hash(content)
    metadata_json = _metadata_json(metadata)
    raw_dir = settings.wiki_root / "domains" / target_domain / "raw" / "crawler" / source_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}-{slugify_url(canonical_url)}-{digest[:10]}.md"
    frontmatter = yaml.safe_dump(
        {
            "source_id": source_id,
            "title": title,
            "canonical_url": canonical_url,
            "captured_at": now.isoformat(),
            "content_hash": digest,
        },
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
    return RawWrite(
        path=path,
        content_hash=digest,
        content_bytes=len(body.encode("utf-8")),
        metadata_json=metadata_json,
    )
