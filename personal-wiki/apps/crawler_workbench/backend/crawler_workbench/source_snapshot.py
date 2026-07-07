from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .channels import list_channels, normalize_base_url
from .profiles import list_profiles


def build_source_profile_snapshot(
    connection: sqlite3.Connection,
    *,
    domain: str,
    run_id: str,
) -> dict[str, Any]:
    db_rows = source_profile_snapshot_db_rows(connection, domain=domain)
    channels = list(db_rows["channels"])
    sources = list(db_rows["sources"])
    return {
        "schema_version": 1,
        "run_id": run_id,
        "domain": domain,
        "captured_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "record_counts": {"channels": len(channels), "sources": len(sources)},
        "channels": channels,
        "sources": sources,
    }


def source_profile_snapshot_db_rows(
    connection: sqlite3.Connection,
    *,
    domain: str,
) -> dict[str, list[dict[str, Any]]]:
    channels = [_snapshot_channel(row) for row in list_channels(connection, domain=domain)]
    sources = [_snapshot_source(row) for row in list_profiles(connection, domain=domain)]
    return {"channels": channels, "sources": sources}


def write_source_profile_snapshot(
    repo_root: Path | str,
    connection: sqlite3.Connection,
    *,
    domain: str,
    run_id: str,
) -> Path:
    root = Path(repo_root)
    snapshot = build_source_profile_snapshot(connection, domain=domain, run_id=run_id)
    path = root / "personal-wiki" / "domains" / domain / f"manifest-{run_id}-source-profile-snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _snapshot_channel(row: dict[str, Any]) -> dict[str, Any]:
    base_url = normalize_base_url(str(row.get("base_url") or ""))
    target_domain = str(row.get("target_domain") or "")
    channel_id = str(row.get("id") or row.get("channel_id") or "")
    return {
        "channel_id": channel_id,
        "target_domain": target_domain,
        "base_url": base_url,
        "trust_level": str(row.get("trust_level") or ""),
        "auth_state": str(row.get("auth_state") or ""),
        "canonical_url": base_url,
        "identity_key": _channel_identity_key(target_domain, base_url),
        "updated_at_watermark": str(row.get("updated_at") or row.get("last_probe_at") or ""),
    }


def _snapshot_source(row: dict[str, Any]) -> dict[str, Any]:
    base_url = normalize_base_url(str(row.get("channel_base_url") or _base_url(str(row.get("url") or ""))))
    source_id = str(row.get("id") or row.get("source_id") or "")
    return {
        "source_id": source_id,
        "channel_id": str(row.get("channel_id") or ""),
        "base_url": base_url,
        "fetcher_type": str(row.get("fetcher_type") or ""),
        "schedule": str(row.get("schedule") or ""),
        "probe_summary": _probe_summary(row),
        "canonical_url": normalize_base_url(str(row.get("url") or "")),
        "identity_key": f"source-profile:{source_id}",
        "updated_at_watermark": str(row.get("updated_at") or row.get("last_run_at") or ""),
        "trust_level": str(row.get("trust_level") or ""),
    }


def _base_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    return url.strip().rstrip("/")


def _channel_identity_key(target_domain: str, base_url: str) -> str:
    parsed = urlparse(base_url)
    canonical = parsed.netloc.lower() if parsed.scheme and parsed.netloc else base_url.lower()
    return f"channel:{target_domain}:{canonical}"


def _probe_summary(row: dict[str, Any]) -> str:
    status = str(row.get("last_run_status") or "").strip()
    timestamp = str(row.get("last_run_at") or "").strip()
    if status and timestamp:
        return f"{status} at {timestamp}"
    if status:
        return status
    return "not_run"
