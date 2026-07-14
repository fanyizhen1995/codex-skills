"""SQLite control store for the unified loop Supervisor."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path, PurePosixPath
import secrets
import sqlite3
from typing import Any, Iterator
from uuid import uuid4

from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
)


SCHEMA_VERSION = 2
ALLOWED_PAGE_SIZES = frozenset({20, 50, 100})
MAX_PAYLOAD_BYTES = 65_536
MAX_SUMMARY_CHARS = 4_096
MAX_SUMMARY_BYTES = 8_192
MAX_ARTIFACT_PATH_CHARS = 1_024
INLINE_LOG_BODY_KEYS = frozenset(
    {
        "command_output",
        "full_log",
        "full_logs",
        "log_body",
        "log_content",
        "logs",
        "raw_log",
        "raw_logs",
        "raw_stderr",
        "raw_stdout",
        "stderr",
        "stderr_content",
        "stderr_text",
        "stdout",
        "stdout_content",
        "stdout_text",
    }
)
ARTIFACT_REFERENCE_KEYS = frozenset(
    {"artifact_ref", "artifact_refs", "evidence_ref", "evidence_refs"}
)


class CursorError(ValueError):
    """Raised when an opaque page cursor is malformed or mismatched."""


class LeaseError(RuntimeError):
    """Raised when a worker no longer owns the action lease it is changing."""


@dataclass(frozen=True)
class ActionRecord:
    action_id: str
    idempotency_key: str
    run_id: str
    run_revision: int
    policy: str
    phase: str
    action_type: str
    status: str
    priority: int
    recovery_tier: int
    lease_owner: str
    lease_expires_at: str
    payload: dict[str, Any]
    artifacts: list[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AttemptRecord:
    attempt_id: str
    action_id: str
    worker_id: str
    result_class: str
    summary: str
    failure_key: str
    error_class: str
    artifact_paths: tuple[str, ...]
    recovery_tier: int
    started_at: str
    finished_at: str


_TABLE_PAGE_SPECS: dict[str, tuple[str, str]] = {
    "runs": ("run_id", "created_at"),
    "actions": ("action_id", "created_at"),
    "action_attempts": ("attempt_id", "created_at"),
    "transitions": ("transition_id", "created_at"),
    "failures": ("failure_key", "created_at"),
    "reviews": ("review_id", "created_at"),
    "review_findings": ("finding_id", "created_at"),
    "user_decisions": ("decision_id", "created_at"),
    "services": ("service_id", "created_at"),
    "freshness_checks": ("check_id", "created_at"),
    "skill_snapshots": ("snapshot_id", "created_at"),
    "aggregates": ("aggregate_id", "created_at"),
}


_DDL = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS store_metadata (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY,
      loop_lineage_id TEXT NOT NULL DEFAULT '',
      parent_run_id TEXT NOT NULL DEFAULT '',
      policy TEXT NOT NULL DEFAULT '',
      phase TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT '',
      revision INTEGER NOT NULL CHECK (revision >= 0),
      summary_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      last_seen_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS actions (
      action_id TEXT PRIMARY KEY,
      idempotency_key TEXT NOT NULL UNIQUE,
      run_id TEXT NOT NULL,
      run_revision INTEGER NOT NULL CHECK (run_revision >= 0),
      policy TEXT NOT NULL DEFAULT '',
      phase TEXT NOT NULL DEFAULT '',
      action_type TEXT NOT NULL,
      task_id TEXT NOT NULL DEFAULT '',
      next_action TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL,
      priority INTEGER NOT NULL DEFAULT 100,
      recovery_tier INTEGER NOT NULL DEFAULT 0,
      lease_owner TEXT NOT NULL DEFAULT '',
      lease_expires_at TEXT NOT NULL DEFAULT '',
      lease_heartbeat_at TEXT NOT NULL DEFAULT '',
      payload_json TEXT NOT NULL DEFAULT '{}',
      artifact_json TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS actions_queue_idx ON actions(status, priority, created_at)",
    """
    CREATE TABLE IF NOT EXISTS action_attempts (
      attempt_id TEXT PRIMARY KEY,
      action_id TEXT NOT NULL REFERENCES actions(action_id),
      worker_id TEXT NOT NULL,
      result_class TEXT NOT NULL,
      summary TEXT NOT NULL,
      failure_key TEXT NOT NULL DEFAULT '',
      error_class TEXT NOT NULL DEFAULT '',
      artifact_json TEXT NOT NULL DEFAULT '[]',
      checkpoint TEXT NOT NULL DEFAULT '',
      recovery_tier INTEGER NOT NULL DEFAULT 0,
      started_at TEXT NOT NULL,
      finished_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS action_attempts_created_idx ON action_attempts(created_at)",
    """
    CREATE TABLE IF NOT EXISTS transitions (
      transition_id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      from_revision INTEGER NOT NULL CHECK (from_revision >= 0),
      to_revision INTEGER NOT NULL CHECK (to_revision >= 0),
      from_phase TEXT NOT NULL DEFAULT '',
      to_phase TEXT NOT NULL DEFAULT '',
      action_id TEXT NOT NULL DEFAULT '',
      summary TEXT NOT NULL DEFAULT '',
      artifact_json TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL,
      UNIQUE(run_id, from_revision, to_revision)
    )
    """,
    "CREATE INDEX IF NOT EXISTS transitions_created_idx ON transitions(created_at)",
    """
    CREATE TABLE IF NOT EXISTS failures (
      failure_key TEXT PRIMARY KEY,
      run_id TEXT NOT NULL DEFAULT '',
      task_id TEXT NOT NULL DEFAULT '',
      error_class TEXT NOT NULL DEFAULT '',
      summary TEXT NOT NULL DEFAULT '',
      resolution TEXT NOT NULL DEFAULT 'open',
      occurrence_count INTEGER NOT NULL DEFAULT 1,
      first_seen_at TEXT NOT NULL,
      last_seen_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
      review_id TEXT PRIMARY KEY,
      trigger TEXT NOT NULL,
      status TEXT NOT NULL,
      decision TEXT NOT NULL DEFAULT '',
      summary TEXT NOT NULL DEFAULT '',
      evidence_json TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS reviews_created_idx ON reviews(created_at)",
    """
    CREATE TABLE IF NOT EXISTS review_findings (
      finding_id TEXT PRIMARY KEY,
      review_id TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
      finding_key TEXT NOT NULL,
      status TEXT NOT NULL,
      summary TEXT NOT NULL DEFAULT '',
      remediation_action_id TEXT NOT NULL DEFAULT '',
      occurrence_count INTEGER NOT NULL DEFAULT 1,
      first_seen_at TEXT NOT NULL,
      last_seen_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(finding_key, status)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_decisions (
      decision_id TEXT PRIMARY KEY,
      scope TEXT NOT NULL,
      run_id TEXT NOT NULL DEFAULT '',
      failure_key TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL,
      summary TEXT NOT NULL,
      required_decision TEXT NOT NULL DEFAULT '',
      resolution TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      closed_at TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS user_decisions_open_failure_idx
    ON user_decisions(scope, run_id, failure_key) WHERE status = 'open'
    """,
    """
    CREATE TABLE IF NOT EXISTS services (
      service_id TEXT PRIMARY KEY,
      status TEXT NOT NULL DEFAULT '',
      endpoint TEXT NOT NULL DEFAULT '',
      process_id INTEGER,
      heartbeat_at TEXT NOT NULL DEFAULT '',
      version TEXT NOT NULL DEFAULT '',
      details_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workers (
      worker_id TEXT PRIMARY KEY,
      heartbeat_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS freshness_checks (
      check_id TEXT PRIMARY KEY,
      target TEXT NOT NULL,
      status TEXT NOT NULL,
      summary TEXT NOT NULL DEFAULT '',
      details_json TEXT NOT NULL DEFAULT '{}',
      checked_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skill_snapshots (
      snapshot_id TEXT PRIMARY KEY,
      total_skills INTEGER NOT NULL DEFAULT 0,
      used_skills INTEGER NOT NULL DEFAULT 0,
      snapshot_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS aggregates (
      aggregate_id TEXT PRIMARY KEY,
      aggregate_day TEXT NOT NULL,
      aggregate_kind TEXT NOT NULL,
      aggregate_key TEXT NOT NULL DEFAULT '',
      count INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(aggregate_day, aggregate_kind, aggregate_key)
    )
    """,
)


class SupervisorStore:
    """Owns one connection to the project-local Supervisor control database."""

    def __init__(
        self,
        project_root: Path,
        connection: sqlite3.Connection,
        clock: Any | None,
    ) -> None:
        self.project_root = project_root
        self.db_path = project_root / ".codex" / "supervisor" / "supervisor.db"
        self._connection = connection
        self._clock = clock

    @classmethod
    def open(cls, project_root: Path, *, clock: Any | None = None) -> "SupervisorStore":
        root = Path(project_root).resolve()
        db_path = root / ".codex" / "supervisor" / "supervisor.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            db_path,
            timeout=5,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return cls(root, connection, clock)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SupervisorStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    @contextmanager
    def _immediate_transaction(self) -> Iterator[None]:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def migrate(self) -> None:
        now = self._now_text()
        with self._immediate_transaction():
            for statement in _DDL:
                self._connection.execute(statement)
            self._connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, now),
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO store_metadata(key, value) VALUES ('cursor_secret', ?)",
                (secrets.token_hex(32),),
            )
            self._connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def table_names(self) -> list[str]:
        rows = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
        return [str(row[0]) for row in rows]

    def pragma(self, name: str) -> Any:
        if name not in {"journal_mode", "foreign_keys", "busy_timeout", "user_version"}:
            raise ValueError(f"unsupported pragma: {name}")
        return self._connection.execute(f"PRAGMA {name}").fetchone()[0]

    def count(self, table: str) -> int:
        self._require_known_table(table)
        return int(
            self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        )

    def fetch_all(self, table: str) -> list[dict[str, Any]]:
        self._require_known_table(table)
        return [
            dict(row)
            for row in self._connection.execute(f"SELECT * FROM {table}").fetchall()
        ]

    def enqueue_action(
        self,
        request: ActionRequest,
        *,
        priority: int = 100,
        recovery_tier: int = 0,
        artifact_paths: tuple[str, ...] | list[str] = (),
    ) -> ActionRecord:
        if not isinstance(request, ActionRequest):
            raise TypeError("request must be an ActionRequest")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise TypeError("priority must be an int")
        if not isinstance(recovery_tier, int) or recovery_tier < 0:
            raise ValueError("recovery_tier must be a non-negative int")
        payload = request.payload_for_storage()
        self._validate_payload(payload)
        artifacts = self._validate_artifact_paths(artifact_paths)
        payload_json = self._json(payload)
        artifact_json = self._json(artifacts)
        now = self._now_text()
        with self._immediate_transaction():
            existing = self._connection.execute(
                "SELECT * FROM actions WHERE idempotency_key = ?",
                (request.idempotency_key,),
            ).fetchone()
            if existing is not None:
                run = self._connection.execute(
                    "SELECT revision, phase FROM runs WHERE run_id = ?",
                    (request.run_id,),
                ).fetchone()
                reopen = (
                    existing["status"] == "completed"
                    and run is not None
                    and int(run["revision"]) == request.run_revision
                    and str(run["phase"]) == request.phase
                )
                stored_payload_json = (
                    str(existing["payload_json"])
                    if payload_json == "{}" and existing["payload_json"] != "{}"
                    else payload_json
                )
                stored_artifact_json = (
                    str(existing["artifact_json"])
                    if artifact_json == "[]" and existing["artifact_json"] != "[]"
                    else artifact_json
                )
                self._connection.execute(
                    """
                    UPDATE actions
                    SET policy = ?, phase = ?, task_id = ?, next_action = ?, priority = ?,
                        recovery_tier = ?, payload_json = ?, artifact_json = ?,
                        status = CASE WHEN ? THEN 'pending' ELSE status END,
                        lease_owner = CASE WHEN ? THEN '' ELSE lease_owner END,
                        lease_expires_at = CASE WHEN ? THEN '' ELSE lease_expires_at END,
                        lease_heartbeat_at = CASE WHEN ? THEN '' ELSE lease_heartbeat_at END,
                        updated_at = ?
                    WHERE action_id = ?
                    """,
                    (
                        request.policy,
                        request.phase,
                        request.task_id,
                        request.next_action,
                        priority,
                        recovery_tier,
                        stored_payload_json,
                        stored_artifact_json,
                        reopen,
                        reopen,
                        reopen,
                        reopen,
                        now,
                        existing["action_id"],
                    ),
                )
                row = self._connection.execute(
                    "SELECT * FROM actions WHERE action_id = ?",
                    (existing["action_id"],),
                ).fetchone()
            else:
                self._connection.execute(
                    """
                    INSERT INTO actions(
                      action_id, idempotency_key, run_id, run_revision, policy, phase,
                      action_type, task_id, next_action, status, priority, recovery_tier,
                      payload_json, artifact_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.action_id,
                        request.idempotency_key,
                        request.run_id,
                        request.run_revision,
                        request.policy,
                        request.phase,
                        request.action_type.value,
                        request.task_id,
                        request.next_action,
                        priority,
                        recovery_tier,
                        payload_json,
                        artifact_json,
                        now,
                        now,
                    ),
                )
                row = self._connection.execute(
                    "SELECT * FROM actions WHERE action_id = ?", (request.action_id,)
                ).fetchone()
        return self._action_record(row)

    def lease_next_action(
        self,
        worker_id: str,
        *,
        lease_seconds: int,
        heartbeat_stale_seconds: int,
    ) -> ActionRecord | None:
        self._validate_lease_input(worker_id, lease_seconds)
        self._validate_heartbeat_stale_seconds(heartbeat_stale_seconds)
        now = self._now_text()
        expires_at = self._time_text(self._now() + timedelta(seconds=lease_seconds))
        heartbeat_cutoff = self._time_text(
            self._now() - timedelta(seconds=heartbeat_stale_seconds)
        )
        with self._immediate_transaction():
            self._write_worker_heartbeat(worker_id, now)
            row = self._connection.execute(
                """
                SELECT a.* FROM actions AS a
                JOIN runs AS r
                  ON r.run_id = a.run_id AND r.revision = a.run_revision
                LEFT JOIN workers AS owner ON owner.worker_id = a.lease_owner
                WHERE a.status = 'pending'
                   OR (
                     a.status IN ('leased', 'running')
                     AND a.lease_expires_at <= ?
                     AND (
                       a.lease_owner = ?
                       OR owner.worker_id IS NULL
                       OR owner.heartbeat_at < ?
                     )
                   )
                ORDER BY a.priority ASC, a.created_at ASC, a.action_id ASC
                LIMIT 1
                """,
                (now, worker_id, heartbeat_cutoff),
            ).fetchone()
            if row is None:
                return None
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'leased', lease_owner = ?, lease_expires_at = ?,
                    lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ? AND (
                  (
                    status = 'pending'
                    AND EXISTS (
                      SELECT 1 FROM runs
                      WHERE runs.run_id = actions.run_id
                        AND runs.revision = actions.run_revision
                    )
                  )
                  OR (
                    status IN ('leased', 'running')
                    AND lease_expires_at <= ?
                    AND EXISTS (
                      SELECT 1 FROM runs
                      WHERE runs.run_id = actions.run_id
                        AND runs.revision = actions.run_revision
                    )
                    AND (
                      lease_owner = ?
                      OR NOT EXISTS (
                        SELECT 1 FROM workers
                        WHERE workers.worker_id = actions.lease_owner
                          AND workers.heartbeat_at >= ?
                      )
                    )
                  )
                )
                """,
                (
                    worker_id,
                    expires_at,
                    now,
                    now,
                    row["action_id"],
                    now,
                    worker_id,
                    heartbeat_cutoff,
                ),
            )
            if updated.rowcount != 1:
                return None
            leased = self._connection.execute(
                "SELECT * FROM actions WHERE action_id = ?", (row["action_id"],)
            ).fetchone()
        return self._action_record(leased)

    def renew_lease(
        self, action_id: str, worker_id: str, *, lease_seconds: int
    ) -> bool:
        self._validate_lease_input(worker_id, lease_seconds)
        now = self._now_text()
        expires_at = self._time_text(self._now() + timedelta(seconds=lease_seconds))
        with self._immediate_transaction():
            self._write_worker_heartbeat(worker_id, now)
            updated = self._connection.execute(
                """
                UPDATE actions
                SET lease_expires_at = ?, lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ? AND lease_owner = ?
                  AND status IN ('leased', 'running')
                  AND EXISTS (
                    SELECT 1 FROM runs
                    WHERE runs.run_id = actions.run_id
                      AND runs.revision = actions.run_revision
                  )
                """,
                (expires_at, now, now, action_id, worker_id),
            )
        return updated.rowcount == 1

    def record_worker_heartbeat(self, worker_id: str) -> dict[str, Any]:
        self._validate_worker_id(worker_id)
        now = self._now_text()
        with self._immediate_transaction():
            self._write_worker_heartbeat(worker_id, now)
            row = self._connection.execute(
                "SELECT * FROM workers WHERE worker_id = ?", (worker_id,)
            ).fetchone()
        return dict(row)

    def complete_action(
        self,
        action_id: str,
        worker_id: str,
        result: ActionResult,
        *,
        recovery_tier: int | None = None,
    ) -> AttemptRecord:
        if not isinstance(result, ActionResult):
            raise TypeError("result must be an ActionResult")
        self._validate_summary(result.summary)
        artifacts = self._validate_artifact_paths(result.artifact_paths)
        now = self._now_text()
        attempt_id = f"attempt-{uuid4().hex}"
        started_at = result.started_at or now
        finished_at = result.finished_at or now
        artifact_json = self._json(artifacts)
        with self._immediate_transaction():
            action = self._connection.execute(
                "SELECT * FROM actions WHERE action_id = ?", (action_id,)
            ).fetchone()
            if (
                action is None
                or action["status"] not in {"leased", "running"}
                or action["lease_owner"] != worker_id
                or action["lease_expires_at"] <= now
            ):
                raise LeaseError(
                    f"worker does not own a live lease for action: {action_id}"
                )
            current_run = self._connection.execute(
                "SELECT revision FROM runs WHERE run_id = ?", (action["run_id"],)
            ).fetchone()
            if current_run is None or int(current_run["revision"]) != int(
                action["run_revision"]
            ):
                raise LeaseError(
                    f"action does not match current run revision: {action_id}"
                )
            tier = (
                int(action["recovery_tier"]) if recovery_tier is None else recovery_tier
            )
            if not isinstance(tier, int) or tier < 0:
                raise ValueError("recovery_tier must be a non-negative int")
            self._connection.execute(
                """
                INSERT INTO action_attempts(
                  attempt_id, action_id, worker_id, result_class, summary, failure_key,
                  error_class, artifact_json, checkpoint, recovery_tier, started_at,
                  finished_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    action_id,
                    worker_id,
                    result.result_class.value,
                    result.summary,
                    result.failure_key,
                    result.error_class,
                    artifact_json,
                    result.checkpoint,
                    tier,
                    started_at,
                    finished_at,
                    now,
                ),
            )
            status = (
                "completed"
                if result.result_class is ActionResultClass.SUCCESS
                else "failed"
            )
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = ?, artifact_json = ?, lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_id = ? AND lease_owner = ?
                """,
                (status, artifact_json, now, action_id, worker_id),
            )
            if updated.rowcount != 1:
                raise LeaseError(f"lost lease while completing action: {action_id}")
        return AttemptRecord(
            attempt_id=attempt_id,
            action_id=action_id,
            worker_id=worker_id,
            result_class=result.result_class.value,
            summary=result.summary,
            failure_key=result.failure_key,
            error_class=result.error_class,
            artifact_paths=result.artifact_paths,
            recovery_tier=tier,
            started_at=started_at,
            finished_at=finished_at,
        )

    def get_action(self, action_id: str) -> ActionRecord:
        row = self._connection.execute(
            "SELECT * FROM actions WHERE action_id = ?", (action_id,)
        ).fetchone()
        if row is None:
            raise KeyError(action_id)
        return self._action_record(row)

    def upsert_run_projection(self, projection: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(projection, Mapping):
            raise TypeError("projection must be a mapping")
        run_id = self._required_text(projection.get("run_id"), "run_id")
        revision = projection.get("revision", projection.get("run_revision"))
        if not isinstance(revision, int) or isinstance(revision, bool):
            raise TypeError("revision must be an int")
        if revision < 0:
            raise ValueError("revision must be non-negative")
        now = self._now_text()
        phase = str(projection.get("phase", ""))
        projection_summary = projection.get("summary", "")
        self._validate_summary(projection_summary)
        artifact_refs = self._validate_artifact_paths(
            projection.get("artifact_refs", []), field_name="artifact_refs"
        )
        summary = {
            "summary": projection_summary,
            "artifact_refs": artifact_refs,
        }
        with self._immediate_transaction():
            existing = self._connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing is None:
                self._connection.execute(
                    """
                    INSERT INTO runs(
                      run_id, loop_lineage_id, parent_run_id, policy, phase, status,
                      revision, summary_json, created_at, updated_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        str(projection.get("loop_lineage_id", "")),
                        str(projection.get("parent_run_id", "")),
                        str(projection.get("policy", "")),
                        phase,
                        str(projection.get("status", "")),
                        revision,
                        self._json(summary),
                        now,
                        now,
                        now,
                    ),
                )
            else:
                current_revision = int(existing["revision"])
                if revision < current_revision:
                    raise ValueError(
                        f"stale run projection revision {revision}; current is {current_revision}"
                    )
                if revision == current_revision and existing["phase"] != phase:
                    raise ValueError(
                        "run projection phase changed without increasing revision"
                    )
                changed = current_revision != revision or existing["phase"] != phase
                if changed:
                    self._insert_transition(
                        run_id=run_id,
                        from_revision=int(existing["revision"]),
                        to_revision=revision,
                        from_phase=str(existing["phase"]),
                        to_phase=phase,
                        action_id="",
                        summary="reconciled run projection",
                        artifact_paths=(),
                        created_at=now,
                    )
                self._connection.execute(
                    """
                    UPDATE runs SET loop_lineage_id = ?, parent_run_id = ?, policy = ?,
                      phase = ?, status = ?, revision = ?, summary_json = ?,
                      updated_at = CASE WHEN ? THEN ? ELSE updated_at END, last_seen_at = ?
                    WHERE run_id = ?
                    """,
                    (
                        str(
                            projection.get(
                                "loop_lineage_id", existing["loop_lineage_id"]
                            )
                        ),
                        str(projection.get("parent_run_id", existing["parent_run_id"])),
                        str(projection.get("policy", existing["policy"])),
                        phase,
                        str(projection.get("status", existing["status"])),
                        revision,
                        self._json(summary),
                        changed,
                        now,
                        now,
                        run_id,
                    ),
                )
            row = self._connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return self._decoded_row(row)

    def get_run(self, run_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._decoded_row(row)

    def record_transition(
        self,
        *,
        run_id: str,
        from_revision: int,
        to_revision: int,
        from_phase: str = "",
        to_phase: str = "",
        action_id: str = "",
        summary: str = "",
        artifact_paths: tuple[str, ...] | list[str] = (),
        created_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        self._validate_summary(summary)
        artifacts = self._validate_artifact_paths(artifact_paths)
        timestamp = self._coerce_time(created_at)
        with self._immediate_transaction():
            transition_id = self._insert_transition(
                run_id=run_id,
                from_revision=from_revision,
                to_revision=to_revision,
                from_phase=from_phase,
                to_phase=to_phase,
                action_id=action_id,
                summary=summary,
                artifact_paths=artifacts,
                created_at=timestamp,
            )
            row = self._connection.execute(
                "SELECT * FROM transitions WHERE transition_id = ?", (transition_id,)
            ).fetchone()
        return self._decoded_row(row)

    def record_failure(
        self,
        failure_key: str,
        *,
        run_id: str = "",
        task_id: str = "",
        error_class: str = "",
        summary: str = "",
        resolution: str = "open",
    ) -> dict[str, Any]:
        self._required_text(failure_key, "failure_key")
        self._validate_summary(summary)
        now = self._now_text()
        with self._immediate_transaction():
            self._connection.execute(
                """
                INSERT INTO failures(
                  failure_key, run_id, task_id, error_class, summary, resolution,
                  occurrence_count, first_seen_at, last_seen_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(failure_key) DO UPDATE SET
                  run_id = excluded.run_id, task_id = excluded.task_id,
                  error_class = excluded.error_class, summary = excluded.summary,
                  resolution = excluded.resolution,
                  occurrence_count = failures.occurrence_count + 1,
                  last_seen_at = excluded.last_seen_at, updated_at = excluded.updated_at
                """,
                (
                    failure_key,
                    run_id,
                    task_id,
                    error_class,
                    summary,
                    resolution,
                    now,
                    now,
                    now,
                    now,
                ),
            )
            row = self._connection.execute(
                "SELECT * FROM failures WHERE failure_key = ?", (failure_key,)
            ).fetchone()
        return self._decoded_row(row)

    def open_user_decision(
        self,
        *,
        scope: str,
        summary: str,
        run_id: str = "",
        failure_key: str = "",
        required_decision: str = "",
        decision_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_summary(summary)
        self._validate_summary(required_decision, field_name="required_decision")
        now = self._now_text()
        with self._immediate_transaction():
            existing = self._connection.execute(
                """
                SELECT * FROM user_decisions
                WHERE scope = ? AND run_id = ? AND failure_key = ? AND status = 'open'
                """,
                (scope, run_id, failure_key),
            ).fetchone()
            if existing is None:
                resolved_id = decision_id or f"decision-{uuid4().hex}"
                self._connection.execute(
                    """
                    INSERT INTO user_decisions(
                      decision_id, scope, run_id, failure_key, status, summary,
                      required_decision, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?)
                    """,
                    (
                        resolved_id,
                        scope,
                        run_id,
                        failure_key,
                        summary,
                        required_decision,
                        now,
                        now,
                    ),
                )
            else:
                resolved_id = str(existing["decision_id"])
                if (
                    existing["summary"] != summary
                    or existing["required_decision"] != required_decision
                ):
                    self._connection.execute(
                        """
                        UPDATE user_decisions
                        SET summary = ?, required_decision = ?, updated_at = ?
                        WHERE decision_id = ?
                        """,
                        (summary, required_decision, now, resolved_id),
                    )
            row = self._connection.execute(
                "SELECT * FROM user_decisions WHERE decision_id = ?", (resolved_id,)
            ).fetchone()
        return self._decoded_row(row)

    def close_user_decision(
        self, decision_id: str, *, resolution: str
    ) -> dict[str, Any]:
        self._validate_summary(resolution, field_name="resolution")
        now = self._now_text()
        with self._immediate_transaction():
            updated = self._connection.execute(
                """
                UPDATE user_decisions SET status = 'closed', resolution = ?,
                  closed_at = ?, updated_at = ?
                WHERE decision_id = ? AND status = 'open'
                """,
                (resolution, now, now, decision_id),
            )
            if updated.rowcount != 1:
                raise KeyError(decision_id)
            row = self._connection.execute(
                "SELECT * FROM user_decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
        return self._decoded_row(row)

    def record_review(
        self,
        *,
        review_id: str,
        trigger: str,
        status: str,
        decision: str = "",
        summary: str = "",
        evidence_refs: tuple[str, ...] | list[str] = (),
        findings: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        created_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        self._validate_summary(summary)
        evidence = self._validate_artifact_paths(
            evidence_refs, field_name="evidence_refs"
        )
        timestamp = self._coerce_time(created_at)
        with self._immediate_transaction():
            self._connection.execute(
                """
                INSERT INTO reviews(
                  review_id, trigger, status, decision, summary, evidence_json,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET status = excluded.status,
                  decision = excluded.decision, summary = excluded.summary,
                  evidence_json = excluded.evidence_json, updated_at = excluded.updated_at
                """,
                (
                    review_id,
                    trigger,
                    status,
                    decision,
                    summary,
                    self._json(evidence),
                    timestamp,
                    timestamp,
                ),
            )
            for finding in findings:
                finding_key = self._required_text(
                    finding.get("finding_key"), "finding_key"
                )
                finding_status = str(finding.get("status", "open"))
                finding_id = str(finding.get("finding_id", f"finding-{uuid4().hex}"))
                finding_summary = finding.get("summary", "")
                self._validate_summary(finding_summary, field_name="finding summary")
                self._connection.execute(
                    """
                    INSERT INTO review_findings(
                      finding_id, review_id, finding_key, status, summary,
                      remediation_action_id, first_seen_at, last_seen_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(finding_key, status) DO UPDATE SET
                      review_id = excluded.review_id, summary = excluded.summary,
                      remediation_action_id = excluded.remediation_action_id,
                      occurrence_count = review_findings.occurrence_count + 1,
                      last_seen_at = excluded.last_seen_at, updated_at = excluded.updated_at
                    """,
                    (
                        finding_id,
                        review_id,
                        finding_key,
                        finding_status,
                        finding_summary,
                        str(finding.get("remediation_action_id", "")),
                        timestamp,
                        timestamp,
                        timestamp,
                        timestamp,
                    ),
                )
            row = self._connection.execute(
                "SELECT * FROM reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
        return self._decoded_row(row)

    def list_page(
        self,
        table: str,
        *,
        resource: str,
        page_size: int = 20,
        cursor: str | None = None,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._required_text(resource, "resource")
        if page_size not in ALLOWED_PAGE_SIZES:
            raise ValueError(f"page_size must be one of {sorted(ALLOWED_PAGE_SIZES)}")
        if table not in _TABLE_PAGE_SPECS:
            raise ValueError(f"unsupported paged table: {table}")
        normalized_filters = dict(filters or {})
        columns = self._table_columns(table)
        for name, value in normalized_filters.items():
            if name not in columns:
                raise ValueError(f"unsupported filter for {table}: {name}")
            if value is not None and not isinstance(value, (str, int, float, bool)):
                raise TypeError(f"filter value must be scalar: {name}")
        primary_key, timestamp_column = _TABLE_PAGE_SPECS[table]
        filter_fingerprint = self._filter_hash(normalized_filters)
        direction = "next"
        boundary: tuple[str, str] | None = None
        snapshot: tuple[str, str] | None = None
        if cursor:
            payload = self._decode_cursor(cursor)
            if payload.get("schema_version") != SCHEMA_VERSION:
                raise CursorError("cursor schema version mismatch")
            if payload.get("resource") != resource:
                raise CursorError("cursor resource mismatch")
            if payload.get("table") != table or payload.get("page_size") != page_size:
                raise CursorError("cursor collection mismatch")
            if payload.get("filter_fingerprint") != filter_fingerprint:
                raise CursorError("cursor filter mismatch")
            direction = payload.get("direction")
            if direction not in {"next", "previous"}:
                raise CursorError("cursor direction is invalid")
            snapshot = self._cursor_position(payload.get("snapshot"), "snapshot")
            boundary = self._cursor_position(payload.get("boundary"), "boundary")
        else:
            snapshot_where, snapshot_parameters = self._filter_clause(
                normalized_filters
            )
            snapshot_where_sql = (
                f" WHERE {' AND '.join(snapshot_where)}" if snapshot_where else ""
            )
            snapshot_row = self._connection.execute(
                f"SELECT {timestamp_column}, {primary_key} FROM {table}"
                f"{snapshot_where_sql} ORDER BY {timestamp_column} DESC, "
                f"{primary_key} DESC LIMIT 1",
                snapshot_parameters,
            ).fetchone()
            if snapshot_row is not None:
                snapshot = (
                    str(snapshot_row[timestamp_column]),
                    str(snapshot_row[primary_key]),
                )

        if cursor and snapshot is None:
            raise CursorError("cursor snapshot is invalid")
        if cursor and boundary is None:
            raise CursorError("cursor boundary is invalid")
        where, parameters = self._filter_clause(normalized_filters)
        if snapshot is not None:
            self._append_position_condition(
                where,
                parameters,
                timestamp_column,
                primary_key,
                "<=",
                snapshot,
            )
        if boundary is not None:
            operator = "<" if direction == "next" else ">"
            self._append_position_condition(
                where,
                parameters,
                timestamp_column,
                primary_key,
                operator,
                boundary,
            )
        order = "DESC" if direction == "next" else "ASC"
        where_sql = f" WHERE {' AND '.join(where)}" if where else ""
        rows = self._connection.execute(
            f"SELECT * FROM {table}{where_sql} "
            f"ORDER BY {timestamp_column} {order}, {primary_key} {order} LIMIT ?",
            (*parameters, page_size + 1),
        ).fetchall()
        selected = list(rows[:page_size])
        if direction == "previous":
            selected.reverse()
        items = [self._decoded_row(row) for row in selected]
        base_where, base_parameters = self._filter_clause(normalized_filters)
        if snapshot is not None:
            self._append_position_condition(
                base_where,
                base_parameters,
                timestamp_column,
                primary_key,
                "<=",
                snapshot,
            )
        base_where_sql = f" WHERE {' AND '.join(base_where)}" if base_where else ""
        total = int(
            self._connection.execute(
                f"SELECT COUNT(*) FROM {table}{base_where_sql}", base_parameters
            ).fetchone()[0]
        )
        next_cursor = None
        previous_cursor = None
        if selected:
            first = selected[0]
            last = selected[-1]
            if self._boundary_exists(
                table,
                timestamp_column,
                primary_key,
                normalized_filters,
                snapshot,
                "<",
                str(last[timestamp_column]),
                str(last[primary_key]),
            ):
                next_cursor = self._encode_cursor(
                    table,
                    resource,
                    page_size,
                    filter_fingerprint,
                    snapshot,
                    "next",
                    (str(last[timestamp_column]), str(last[primary_key])),
                )
            if self._boundary_exists(
                table,
                timestamp_column,
                primary_key,
                normalized_filters,
                snapshot,
                ">",
                str(first[timestamp_column]),
                str(first[primary_key]),
            ):
                previous_cursor = self._encode_cursor(
                    table,
                    resource,
                    page_size,
                    filter_fingerprint,
                    snapshot,
                    "previous",
                    (str(first[timestamp_column]), str(first[primary_key])),
                )
        return {
            "items": items,
            "next_cursor": next_cursor,
            "previous_cursor": previous_cursor,
            "page_size": page_size,
            "total": total,
            "has_more": next_cursor is not None,
        }

    def compact_retention(self, *, retention_days: int = 90) -> dict[str, int]:
        if (
            not isinstance(retention_days, int)
            or isinstance(retention_days, bool)
            or retention_days <= 0
        ):
            raise ValueError("retention_days must be a positive int")
        cutoff = self._time_text(self._now() - timedelta(days=retention_days))
        now = self._now_text()
        deleted: dict[str, int] = {}
        with self._immediate_transaction():
            specs = (
                ("transitions", "to_phase", "transitions"),
                ("action_attempts", "result_class", "action_attempts"),
            )
            for table, key_column, aggregate_kind in specs:
                groups = self._connection.execute(
                    f"""
                    SELECT substr(created_at, 1, 10) AS aggregate_day,
                           {key_column} AS aggregate_key, COUNT(*) AS aggregate_count
                    FROM {table} WHERE created_at < ?
                    GROUP BY aggregate_day, aggregate_key
                    """,
                    (cutoff,),
                ).fetchall()
                for group in groups:
                    self._upsert_aggregate(
                        str(group["aggregate_day"]),
                        aggregate_kind,
                        str(group["aggregate_key"]),
                        int(group["aggregate_count"]),
                        now,
                    )
            eligible_reviews = """
                reviews.created_at < ?
                AND NOT EXISTS (
                  SELECT 1 FROM review_findings AS active_findings
                  WHERE active_findings.review_id = reviews.review_id
                    AND active_findings.status NOT IN ('closed', 'accepted_risk')
                )
                AND NOT EXISTS (
                  SELECT 1 FROM review_findings AS recent_findings
                  WHERE recent_findings.review_id = reviews.review_id
                    AND recent_findings.created_at >= ?
                )
            """
            review_groups = self._connection.execute(
                f"""
                SELECT substr(reviews.created_at, 1, 10) AS aggregate_day,
                       reviews.decision AS aggregate_key,
                       COUNT(*) AS aggregate_count
                FROM reviews
                WHERE {eligible_reviews}
                GROUP BY aggregate_day, aggregate_key
                """,
                (cutoff, cutoff),
            ).fetchall()
            for group in review_groups:
                self._upsert_aggregate(
                    str(group["aggregate_day"]),
                    "reviews",
                    str(group["aggregate_key"]),
                    int(group["aggregate_count"]),
                    now,
                )
            finding_groups = self._connection.execute(
                f"""
                SELECT substr(findings.created_at, 1, 10) AS aggregate_day,
                       findings.status AS aggregate_key,
                       COUNT(*) AS aggregate_count
                FROM review_findings AS findings
                JOIN reviews ON reviews.review_id = findings.review_id
                WHERE findings.created_at < ? AND {eligible_reviews}
                GROUP BY aggregate_day, aggregate_key
                """,
                (cutoff, cutoff, cutoff),
            ).fetchall()
            for group in finding_groups:
                self._upsert_aggregate(
                    str(group["aggregate_day"]),
                    "review_findings",
                    str(group["aggregate_key"]),
                    int(group["aggregate_count"]),
                    now,
                )
            failure_groups = self._connection.execute(
                """
                SELECT substr(created_at, 1, 10) AS aggregate_day,
                       failure_key AS aggregate_key, COUNT(*) AS aggregate_count
                FROM action_attempts
                WHERE created_at < ? AND failure_key != ''
                GROUP BY aggregate_day, aggregate_key
                """,
                (cutoff,),
            ).fetchall()
            for group in failure_groups:
                self._upsert_aggregate(
                    str(group["aggregate_day"]),
                    "failure",
                    str(group["aggregate_key"]),
                    int(group["aggregate_count"]),
                    now,
                )
            finding_delete = self._connection.execute(
                f"""
                DELETE FROM review_findings
                WHERE created_at < ? AND review_id IN (
                  SELECT reviews.review_id FROM reviews WHERE {eligible_reviews}
                )
                """,
                (cutoff, cutoff, cutoff),
            )
            deleted["review_findings"] = finding_delete.rowcount
            review_delete = self._connection.execute(
                f"DELETE FROM reviews WHERE {eligible_reviews}", (cutoff, cutoff)
            )
            deleted["reviews"] = review_delete.rowcount
            for table in ("action_attempts", "transitions"):
                result = self._connection.execute(
                    f"DELETE FROM {table} WHERE created_at < ?", (cutoff,)
                )
                deleted[table] = result.rowcount
        return deleted

    def _insert_transition(
        self,
        *,
        run_id: str,
        from_revision: int,
        to_revision: int,
        from_phase: str,
        to_phase: str,
        action_id: str,
        summary: str,
        artifact_paths: tuple[str, ...] | list[str],
        created_at: str,
    ) -> str:
        transition_id = f"transition-{uuid4().hex}"
        self._connection.execute(
            """
            INSERT INTO transitions(
              transition_id, run_id, from_revision, to_revision, from_phase,
              to_phase, action_id, summary, artifact_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, from_revision, to_revision) DO NOTHING
            """,
            (
                transition_id,
                run_id,
                from_revision,
                to_revision,
                from_phase,
                to_phase,
                action_id,
                summary,
                self._json(list(artifact_paths)),
                created_at,
            ),
        )
        row = self._connection.execute(
            """
            SELECT transition_id FROM transitions
            WHERE run_id = ? AND from_revision = ? AND to_revision = ?
            """,
            (run_id, from_revision, to_revision),
        ).fetchone()
        return str(row["transition_id"])

    def _upsert_aggregate(
        self, day: str, kind: str, key: str, count: int, timestamp: str
    ) -> None:
        identity = f"{day}\0{kind}\0{key}".encode()
        aggregate_id = f"aggregate-{hashlib.sha256(identity).hexdigest()}"
        self._connection.execute(
            """
            INSERT INTO aggregates(
              aggregate_id, aggregate_day, aggregate_kind, aggregate_key,
              count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(aggregate_day, aggregate_kind, aggregate_key) DO UPDATE SET
              count = aggregates.count + excluded.count, updated_at = excluded.updated_at
            """,
            (aggregate_id, day, kind, key, count, timestamp, timestamp),
        )

    def _encode_cursor(
        self,
        table: str,
        resource: str,
        page_size: int,
        filter_fingerprint: str,
        snapshot: tuple[str, str],
        direction: str,
        boundary: tuple[str, str],
    ) -> str:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "table": table,
            "resource": resource,
            "page_size": page_size,
            "filter_fingerprint": filter_fingerprint,
            "direction": direction,
            "snapshot": {
                "sort_timestamp": snapshot[0],
                "primary_key": snapshot[1],
            },
            "boundary": {
                "sort_timestamp": boundary[0],
                "primary_key": boundary[1],
            },
        }
        payload_bytes = self._json(payload).encode()
        signature = hmac.new(
            self._cursor_secret(), payload_bytes, hashlib.sha256
        ).hexdigest()
        envelope = self._json({"payload": payload, "signature": signature}).encode()
        return base64.urlsafe_b64encode(envelope).decode().rstrip("=")

    def _decode_cursor(self, cursor: str) -> dict[str, Any]:
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
            envelope = json.loads(raw)
            payload = envelope["payload"]
            signature = envelope["signature"]
            if not isinstance(payload, dict) or not isinstance(signature, str):
                raise TypeError
            expected = hmac.new(
                self._cursor_secret(), self._json(payload).encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise CursorError("cursor signature is invalid")
            return payload
        except CursorError:
            raise
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise CursorError("cursor is malformed") from exc

    def _cursor_secret(self) -> bytes:
        row = self._connection.execute(
            "SELECT value FROM store_metadata WHERE key = 'cursor_secret'"
        ).fetchone()
        if row is None:
            raise RuntimeError("store must be migrated before cursor use")
        return str(row["value"]).encode()

    def _boundary_exists(
        self,
        table: str,
        timestamp_column: str,
        primary_key: str,
        filters: Mapping[str, Any],
        snapshot: tuple[str, str] | None,
        operator: str,
        timestamp: str,
        key: str,
    ) -> bool:
        where, parameters = self._filter_clause(filters)
        if snapshot is not None:
            self._append_position_condition(
                where,
                parameters,
                timestamp_column,
                primary_key,
                "<=",
                snapshot,
            )
        self._append_position_condition(
            where,
            parameters,
            timestamp_column,
            primary_key,
            operator,
            (timestamp, key),
        )
        row = self._connection.execute(
            f"SELECT 1 FROM {table} WHERE {' AND '.join(where)} LIMIT 1", parameters
        ).fetchone()
        return row is not None

    @staticmethod
    def _append_position_condition(
        clauses: list[str],
        parameters: list[Any],
        timestamp_column: str,
        primary_key: str,
        operator: str,
        position: tuple[str, str],
    ) -> None:
        key_operator = "<=" if operator == "<=" else operator
        timestamp_operator = "<" if operator == "<=" else operator
        clauses.append(
            f"({timestamp_column} {timestamp_operator} ? OR "
            f"({timestamp_column} = ? AND {primary_key} {key_operator} ?))"
        )
        parameters.extend((position[0], position[0], position[1]))

    @staticmethod
    def _cursor_position(value: object, name: str) -> tuple[str, str]:
        if not isinstance(value, dict):
            raise CursorError(f"cursor {name} is invalid")
        timestamp = value.get("sort_timestamp")
        primary_key = value.get("primary_key")
        if not isinstance(timestamp, str) or not isinstance(primary_key, str):
            raise CursorError(f"cursor {name} is invalid")
        return timestamp, primary_key

    @staticmethod
    def _filter_clause(filters: Mapping[str, Any]) -> tuple[list[str], list[Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for name in sorted(filters):
            value = filters[name]
            if value is None:
                clauses.append(f"{name} IS NULL")
            else:
                clauses.append(f"{name} = ?")
                parameters.append(value)
        return clauses, parameters

    def _filter_hash(self, filters: Mapping[str, Any]) -> str:
        return hashlib.sha256(self._json(dict(filters)).encode()).hexdigest()

    def _table_columns(self, table: str) -> set[str]:
        return {
            str(row["name"])
            for row in self._connection.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }

    @staticmethod
    def _action_record(row: sqlite3.Row) -> ActionRecord:
        return ActionRecord(
            action_id=str(row["action_id"]),
            idempotency_key=str(row["idempotency_key"]),
            run_id=str(row["run_id"]),
            run_revision=int(row["run_revision"]),
            policy=str(row["policy"]),
            phase=str(row["phase"]),
            action_type=str(row["action_type"]),
            status=str(row["status"]),
            priority=int(row["priority"]),
            recovery_tier=int(row["recovery_tier"]),
            lease_owner=str(row["lease_owner"]),
            lease_expires_at=str(row["lease_expires_at"]),
            payload=json.loads(row["payload_json"]),
            artifacts=json.loads(row["artifact_json"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _decoded_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for column in tuple(result):
            if column.endswith("_json"):
                value = json.loads(result.pop(column))
                result[column.removesuffix("_json")] = value
        return result

    def _now(self) -> datetime:
        if self._clock is None:
            value = datetime.now(timezone.utc)
        elif callable(self._clock):
            value = self._clock()
        else:
            value = self._clock.now()
        if not isinstance(value, datetime):
            raise TypeError("clock must return datetime")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _now_text(self) -> str:
        return self._time_text(self._now())

    def _coerce_time(self, value: datetime | str | None) -> str:
        if value is None:
            return self._now_text()
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return self._time_text(value)
        raise TypeError("timestamp must be datetime, string, or None")

    @staticmethod
    def _time_text(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _validate_payload(self, payload: Mapping[str, Any]) -> None:
        encoded = self._json(payload).encode("utf-8")
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"payload exceeds {MAX_PAYLOAD_BYTES} encoded bytes")

        def visit(value: Any) -> None:
            if isinstance(value, Mapping):
                for key, item in value.items():
                    normalized_key = key.lower().replace("-", "_")
                    if normalized_key in INLINE_LOG_BODY_KEYS:
                        raise ValueError(
                            f"payload contains forbidden inline log body key: {key}"
                        )
                    if normalized_key == "summary":
                        self._validate_summary(item, field_name="payload summary")
                    if normalized_key.endswith("_path"):
                        self._validate_artifact_paths(
                            (item,), field_name=f"payload {key}"
                        )
                    elif normalized_key.endswith("_paths"):
                        self._validate_artifact_paths(item, field_name=f"payload {key}")
                    elif normalized_key in ARTIFACT_REFERENCE_KEYS:
                        references = item if normalized_key.endswith("s") else (item,)
                        self._validate_artifact_paths(
                            references, field_name=f"payload {key}"
                        )
                    visit(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    visit(item)

        visit(payload)

    def _validate_artifact_paths(
        self,
        artifact_paths: object,
        *,
        field_name: str = "artifact_paths",
    ) -> list[str]:
        if not isinstance(artifact_paths, (list, tuple)):
            raise TypeError(f"{field_name} must be a list or tuple")
        validated: list[str] = []
        for path_value in artifact_paths:
            if not isinstance(path_value, str) or not path_value:
                raise ValueError(f"{field_name} must contain non-empty artifact paths")
            if len(path_value) > MAX_ARTIFACT_PATH_CHARS:
                raise ValueError(f"{field_name} contains an oversized artifact path")
            if (
                "\x00" in path_value
                or "\\" in path_value
                or "://" in path_value
                or (len(path_value) >= 2 and path_value[1] == ":")
            ):
                raise ValueError(f"{field_name} contains an unsafe artifact path")
            relative = PurePosixPath(path_value)
            if relative.is_absolute() or not relative.parts or ".." in relative.parts:
                raise ValueError(
                    f"{field_name} must contain repo-relative artifact paths without '..'"
                )
            candidate = self.project_root
            for part in relative.parts:
                candidate = candidate / part
                if candidate.is_symlink():
                    raise ValueError(
                        f"{field_name} artifact path traverses a symlink: {path_value}"
                    )
            try:
                candidate.resolve(strict=False).relative_to(self.project_root)
            except ValueError as exc:
                raise ValueError(
                    f"{field_name} artifact path escapes the project root"
                ) from exc
            validated.append(path_value)
        return validated

    @staticmethod
    def _validate_summary(value: object, *, field_name: str = "summary") -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        if len(value) > MAX_SUMMARY_CHARS:
            raise ValueError(f"{field_name} exceeds {MAX_SUMMARY_CHARS} characters")
        if len(value.encode("utf-8")) > MAX_SUMMARY_BYTES:
            raise ValueError(f"{field_name} exceeds {MAX_SUMMARY_BYTES} encoded bytes")

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

    @staticmethod
    def _required_text(value: object, field_name: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field_name} must be a non-empty string")
        return value

    @staticmethod
    def _validate_lease_input(worker_id: str, lease_seconds: int) -> None:
        SupervisorStore._validate_worker_id(worker_id)
        if (
            not isinstance(lease_seconds, int)
            or isinstance(lease_seconds, bool)
            or lease_seconds <= 0
        ):
            raise ValueError("lease_seconds must be a positive int")

    @staticmethod
    def _validate_worker_id(worker_id: str) -> None:
        if not isinstance(worker_id, str) or not worker_id:
            raise ValueError("worker_id must be a non-empty string")

    @staticmethod
    def _validate_heartbeat_stale_seconds(heartbeat_stale_seconds: int) -> None:
        if (
            not isinstance(heartbeat_stale_seconds, int)
            or isinstance(heartbeat_stale_seconds, bool)
            or heartbeat_stale_seconds <= 0
        ):
            raise ValueError("heartbeat_stale_seconds must be a positive int")

    def _write_worker_heartbeat(self, worker_id: str, timestamp: str) -> None:
        self._connection.execute(
            """
            INSERT INTO workers(worker_id, heartbeat_at, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(worker_id) DO UPDATE SET
              heartbeat_at = excluded.heartbeat_at, updated_at = excluded.updated_at
            """,
            (worker_id, timestamp, timestamp, timestamp),
        )

    @staticmethod
    def _require_known_table(table: str) -> None:
        if table not in {
            *_TABLE_PAGE_SPECS,
            "schema_migrations",
            "store_metadata",
            "workers",
        }:
            raise ValueError(f"unsupported table: {table}")
