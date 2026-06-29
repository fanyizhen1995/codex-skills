from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from .fetchers.base import Fetcher
from .fetch_service import run_source_once
from .hashing import canonicalize_url, slugify_url
from .ingest import CodexRunner, approve_task, run_approved_task
from .settings import Settings


def manual_source_id(url: str) -> str:
    canonical_url = canonicalize_url(url)
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:10]
    slug = slugify_url(canonical_url, max_length=48)
    return f"manual-url-{slug}-{digest}"


def run_manual_url_ingest(
    settings: Settings,
    db: sqlite3.Connection,
    url: str,
    domain: str = "ai_infra",
    auto_commit_enabled: bool = True,
    fetcher: Fetcher | None = None,
    codex_runner: CodexRunner | None = None,
) -> dict[str, object]:
    canonical_url = canonicalize_url(url)
    source_id = manual_source_id(canonical_url)
    _upsert_manual_source(db, source_id, canonical_url, domain)
    fetch_summary = run_source_once(settings, db, source_id, fetcher=fetcher)
    task = _latest_task_for_fetch(db, source_id, int(fetch_summary["fetch_run_id"]))
    if task is None:
        return {
            "status": "skipped",
            "reason": "no changed content fetched",
            "source_id": source_id,
            "url": canonical_url,
            "domain": domain,
            "fetch": fetch_summary,
            "task_id": None,
            "commit_sha": None,
        }

    task_id = int(task["id"])
    if task["status"] in ("pending", "failed"):
        approve_task(settings, db, task_id)
    task_result = run_approved_task(settings, db, task_id, auto_commit_enabled, codex_runner=codex_runner)
    commit_sha = _commit_sha_for_task(db, task_id)
    return {
        "status": task_result["status"],
        "reason": task_result.get("reason"),
        "source_id": source_id,
        "url": canonical_url,
        "domain": domain,
        "fetch": fetch_summary,
        "task_id": task_id,
        "task": task_result,
        "commit_sha": commit_sha,
    }


def _upsert_manual_source(db: sqlite3.Connection, source_id: str, url: str, domain: str) -> None:
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, baseline_on_first_run, run_policy,
          auth_state, topic, enabled
        )
        values (?, ?, 'web', ?, ?, 'trusted', 'manual', 1, 0, 0, 'once', 'ready', ?, 1)
        on conflict(id) do update set
          name = excluded.name,
          target_domain = excluded.target_domain,
          url = excluded.url,
          trust_level = excluded.trust_level,
          schedule = excluded.schedule,
          auto_ingest = excluded.auto_ingest,
          auth_required = excluded.auth_required,
          baseline_on_first_run = excluded.baseline_on_first_run,
          run_policy = excluded.run_policy,
          auth_state = excluded.auth_state,
          topic = excluded.topic,
          enabled = excluded.enabled,
          updated_at = current_timestamp
        """,
        (source_id, f"Manual URL ingest: {url}", domain, url, f"Manual URL ingest for {url}"),
    )
    db.commit()


def _latest_task_for_fetch(db: sqlite3.Connection, source_id: str, fetch_run_id: int) -> sqlite3.Row | None:
    return db.execute(
        """
        select ingest_tasks.*
        from ingest_tasks
        join raw_items on raw_items.id = ingest_tasks.raw_item_id
        where ingest_tasks.source_id = ?
          and raw_items.fetch_run_id = ?
        order by ingest_tasks.id desc
        limit 1
        """,
        (source_id, fetch_run_id),
    ).fetchone()


def _commit_sha_for_task(db: sqlite3.Connection, task_id: int) -> str | None:
    row = db.execute(
        """
        select commit_records.commit_sha
        from ingest_tasks
        join commit_records on commit_records.id = ingest_tasks.commit_id
        where ingest_tasks.id = ?
        """,
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    value: Any = row["commit_sha"]
    return str(value) if value else None
