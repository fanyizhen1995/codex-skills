from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from .fetchers import Fetcher, fetcher_for
from .hashing import content_hash
from .policy import ingest_decision
from .raw_store import write_raw_item
from .settings import Settings


class SourceRunError(Exception):
    pass


class SourceNotFoundError(SourceRunError):
    pass


class SourceDisabledError(SourceRunError):
    pass


def run_source_once(
    settings: Settings,
    db: sqlite3.Connection,
    source_id: str,
    fetcher: Fetcher | None = None,
) -> dict[str, object]:
    profile = _source_profile(db, source_id)
    fetch_run_id = _create_fetch_run(db, source_id)
    db.commit()

    runner: Fetcher | None = fetcher
    should_close = fetcher is None
    fetched_count = 0
    changed_count = 0
    skipped_count = 0
    written_raw_paths: list[Path] = []

    try:
        if runner is None:
            runner = fetcher_for(str(profile["type"]))
        results = runner.fetch(profile)
        for result in results:
            fetched_count += 1
            digest = content_hash(result.content)
            existing = db.execute(
                """
                select id from content_versions
                where source_id = ? and canonical_url = ? and content_hash = ?
                """,
                (source_id, result.canonical_url, digest),
            ).fetchone()
            if existing is not None:
                skipped_count += 1
                continue

            raw_write = write_raw_item(
                settings=settings,
                source_id=source_id,
                target_domain=str(profile["target_domain"]),
                canonical_url=result.canonical_url,
                title=result.title,
                content=result.content,
                metadata=result.metadata,
            )
            written_raw_paths.append(raw_write.path)
            raw_item_id = db.execute(
                """
                insert into raw_items (
                  source_id, fetch_run_id, target_domain, canonical_url, raw_path,
                  title, content_hash, content_bytes, metadata_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    fetch_run_id,
                    profile["target_domain"],
                    result.canonical_url,
                    str(raw_write.path),
                    result.title,
                    raw_write.content_hash,
                    raw_write.content_bytes,
                    raw_write.metadata_json,
                ),
            ).lastrowid
            db.execute(
                """
                insert into content_versions (
                  source_id, canonical_url, content_hash, etag, last_modified, raw_item_id
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    result.canonical_url,
                    raw_write.content_hash,
                    result.etag,
                    result.last_modified,
                    raw_item_id,
                ),
            )
            decision = ingest_decision(profile, raw_write.content_bytes, settings.max_auto_ingest_bytes)
            db.execute(
                """
                insert into ingest_tasks (
                  source_id, raw_item_id, target_domain, status, risk_level, reason
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    raw_item_id,
                    profile["target_domain"],
                    decision.status,
                    decision.risk_level,
                    decision.reason,
                ),
            )
            changed_count += 1

        db.execute(
            """
            update fetch_runs
            set status = 'succeeded',
                finished_at = current_timestamp,
                fetched_count = ?,
                changed_count = ?,
                skipped_count = ?
            where id = ?
            """,
            (fetched_count, changed_count, skipped_count, fetch_run_id),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _cleanup_raw_files(written_raw_paths)
        durable_changed_count = _changed_count(db, fetch_run_id)
        db.execute(
            """
            update fetch_runs
            set status = 'failed',
                finished_at = current_timestamp,
                fetched_count = ?,
                changed_count = ?,
                skipped_count = ?,
                error = ?
            where id = ?
            """,
            (fetched_count, durable_changed_count, skipped_count, str(exc), fetch_run_id),
        )
        db.commit()
        raise
    finally:
        if should_close:
            close = getattr(runner, "close", None) if runner is not None else None
            if close is not None:
                close()

    return {
        "fetch_run_id": fetch_run_id,
        "fetched_count": fetched_count,
        "changed_count": changed_count,
        "skipped_count": skipped_count,
    }


def _source_profile(db: sqlite3.Connection, source_id: str) -> dict[str, Any]:
    row = db.execute("select * from source_profiles where id = ?", (source_id,)).fetchone()
    if row is None:
        raise SourceNotFoundError(f"source not found: {source_id}")
    profile = dict(row)
    if not bool(profile["enabled"]):
        raise SourceDisabledError(f"source is disabled: {source_id}")
    profile["auto_ingest"] = bool(profile["auto_ingest"])
    profile["auth_required"] = bool(profile["auth_required"])
    profile["enabled"] = bool(profile["enabled"])
    return profile


def _create_fetch_run(db: sqlite3.Connection, source_id: str) -> int:
    return db.execute(
        "insert into fetch_runs (source_id, status) values (?, 'running')",
        (source_id,),
    ).lastrowid


def _changed_count(db: sqlite3.Connection, fetch_run_id: int) -> int:
    row = db.execute(
        "select count(*) as count from raw_items where fetch_run_id = ?",
        (fetch_run_id,),
    ).fetchone()
    return int(row["count"])


def _cleanup_raw_files(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
