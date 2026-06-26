from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import urlparse

import yaml

from .ingest import TaskNotFoundError


VALID_MODES = {"manual", "scheduled"}
VALID_FREQUENCIES = {"daily", "weekly", "monthly"}


class TrustSourceInputError(ValueError):
    pass


def trust_task_source(
    settings: Any,
    db: sqlite3.Connection,
    task_id: int,
    mode: str,
    frequency: str | None = None,
) -> dict[str, object]:
    schedule = _schedule_for(mode, frequency)
    task = _load_task_with_raw(db, task_id)
    source_domain = _source_domain(str(task["canonical_url"]))
    source_id = str(task["source_id"])

    db.execute(
        """
        update source_profiles
        set trust_level = 'trusted',
            auto_ingest = 1,
            schedule = ?,
            next_run_at = ?,
            updated_at = current_timestamp
        where id = ?
        """,
        (schedule, _initial_next_run_at(schedule), source_id),
    )
    approved_task_ids = _approve_matching_pending_tasks(db, source_domain)
    db.commit()
    _update_sources_yaml(settings.sources_yaml_path, source_id, schedule)
    return {
        "source_id": source_id,
        "domain": source_domain,
        "schedule": schedule,
        "approved_count": len(approved_task_ids),
        "task_ids": approved_task_ids,
    }


def _schedule_for(mode: str, frequency: str | None) -> str:
    if mode not in VALID_MODES:
        raise TrustSourceInputError(f"invalid source trust mode: {mode}")
    if mode == "manual":
        return "manual"
    if frequency not in VALID_FREQUENCIES:
        raise TrustSourceInputError(f"invalid scheduled source frequency: {frequency}")
    return str(frequency)


def _load_task_with_raw(db: sqlite3.Connection, task_id: int) -> sqlite3.Row:
    row = db.execute(
        """
        select ingest_tasks.*, raw_items.canonical_url
        from ingest_tasks
        join raw_items on raw_items.id = ingest_tasks.raw_item_id
        where ingest_tasks.id = ?
        """,
        (task_id,),
    ).fetchone()
    if row is None:
        raise TaskNotFoundError(f"ingest task not found: {task_id}")
    return row


def _source_domain(url: str) -> str:
    hostname = urlparse(url).hostname
    if not hostname:
        raise TrustSourceInputError(f"task source URL has no hostname: {url}")
    host = hostname.lower()
    for prefix in ("www.", "blog."):
        if host.startswith(prefix):
            return host[len(prefix) :]
    return host


def _approve_matching_pending_tasks(db: sqlite3.Connection, source_domain: str) -> list[int]:
    rows = db.execute(
        """
        select ingest_tasks.id, raw_items.canonical_url
        from ingest_tasks
        join raw_items on raw_items.id = ingest_tasks.raw_item_id
        where ingest_tasks.status = 'pending'
        order by ingest_tasks.id
        """
    ).fetchall()
    task_ids = [
        int(row["id"])
        for row in rows
        if _domain_matches(_source_domain(str(row["canonical_url"])), source_domain)
    ]
    if not task_ids:
        return []

    placeholders = ", ".join("?" for _ in task_ids)
    db.execute(
        f"""
        update ingest_tasks
        set status = 'approved',
            reason = ?,
            updated_at = current_timestamp
        where status = 'pending' and id in ({placeholders})
        """,
        ["approved by trusted source site", *task_ids],
    )
    return task_ids


def _domain_matches(candidate: str, trusted_domain: str) -> bool:
    return candidate == trusted_domain or candidate.endswith(f".{trusted_domain}") or trusted_domain.endswith(f".{candidate}")


def _initial_next_run_at(schedule: str) -> str | None:
    if schedule == "manual":
        return None
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def _update_sources_yaml(path: Path, source_id: str, schedule: str) -> None:
    if not path.exists():
        return
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources")
    if not isinstance(sources, list):
        return
    changed = False
    for source in sources:
        if isinstance(source, dict) and source.get("id") == source_id:
            source["trust_level"] = "trusted"
            source["auto_ingest"] = True
            source["schedule"] = schedule
            changed = True
            break
    if changed:
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
