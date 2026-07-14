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
from pathlib import Path
import secrets
import sqlite3
from typing import Any, Iterator
from uuid import uuid4

from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
)


SCHEMA_VERSION = 1
ALLOWED_PAGE_SIZES = frozenset({20, 50, 100})


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
        payload_json = self._json(request.payload_for_storage())
        artifact_json = self._json(list(artifact_paths))
        now = self._now_text()
        with self._immediate_transaction():
            existing = self._connection.execute(
                "SELECT * FROM actions WHERE idempotency_key = ?",
                (request.idempotency_key,),
            ).fetchone()
            if existing is not None:
                self._connection.execute(
                    """
                    UPDATE actions
                    SET policy = ?, phase = ?, task_id = ?, next_action = ?, priority = ?,
                        recovery_tier = ?, payload_json = ?, artifact_json = ?, updated_at = ?
                    WHERE action_id = ?
                    """,
                    (
                        request.policy,
                        request.phase,
                        request.task_id,
                        request.next_action,
                        priority,
                        recovery_tier,
                        payload_json,
                        artifact_json,
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
        self, worker_id: str, *, lease_seconds: int
    ) -> ActionRecord | None:
        self._validate_lease_input(worker_id, lease_seconds)
        now = self._now_text()
        expires_at = self._time_text(self._now() + timedelta(seconds=lease_seconds))
        with self._immediate_transaction():
            row = self._connection.execute(
                """
                SELECT * FROM actions
                WHERE status = 'pending'
                   OR (
                     status IN ('leased', 'running')
                     AND lease_expires_at <= ?
                     AND (lease_heartbeat_at = '' OR lease_heartbeat_at <= ?)
                   )
                ORDER BY priority ASC, created_at ASC, action_id ASC
                LIMIT 1
                """,
                (now, now),
            ).fetchone()
            if row is None:
                return None
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'leased', lease_owner = ?, lease_expires_at = ?,
                    lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ? AND (
                  status = 'pending'
                  OR (
                    status IN ('leased', 'running')
                    AND lease_expires_at <= ?
                    AND (lease_heartbeat_at = '' OR lease_heartbeat_at <= ?)
                  )
                )
                """,
                (worker_id, expires_at, now, now, row["action_id"], now, now),
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
            updated = self._connection.execute(
                """
                UPDATE actions
                SET lease_expires_at = ?, lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ? AND lease_owner = ?
                  AND status IN ('leased', 'running') AND lease_expires_at > ?
                """,
                (expires_at, now, now, action_id, worker_id, now),
            )
        return updated.rowcount == 1

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
        now = self._now_text()
        attempt_id = f"attempt-{uuid4().hex}"
        started_at = result.started_at or now
        finished_at = result.finished_at or now
        artifact_json = self._json(list(result.artifact_paths))
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
        summary = {
            "summary": projection.get("summary", ""),
            "artifact_refs": projection.get("artifact_refs", []),
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
                changed = (
                    int(existing["revision"]) != revision or existing["phase"] != phase
                )
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
                artifact_paths=artifact_paths,
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
                self._connection.execute(
                    """
                    UPDATE user_decisions SET summary = ?, required_decision = ?, updated_at = ?
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
                    self._json(list(evidence_refs)),
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
                        str(finding.get("summary", "")),
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
        page_size: int = 20,
        cursor: str | None = None,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
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
        filter_hash = self._filter_hash(normalized_filters)
        direction = "next"
        boundary: tuple[str, str] | None = None
        if cursor:
            payload = self._decode_cursor(cursor)
            if payload.get("schema_version") != SCHEMA_VERSION:
                raise CursorError("cursor schema version mismatch")
            if payload.get("table") != table or payload.get("page_size") != page_size:
                raise CursorError("cursor collection mismatch")
            if payload.get("filter_hash") != filter_hash:
                raise CursorError("cursor filter mismatch")
            direction = payload.get("direction")
            if direction not in {"next", "previous"}:
                raise CursorError("cursor direction is invalid")
            sort_timestamp = payload.get("sort_timestamp")
            cursor_primary_key = payload.get("primary_key")
            if not isinstance(sort_timestamp, str) or not isinstance(
                cursor_primary_key, str
            ):
                raise CursorError("cursor boundary is invalid")
            boundary = (sort_timestamp, cursor_primary_key)

        where, parameters = self._filter_clause(normalized_filters)
        if boundary is not None:
            operator = "<" if direction == "next" else ">"
            where.append(
                f"({timestamp_column} {operator} ? OR "
                f"({timestamp_column} = ? AND {primary_key} {operator} ?))"
            )
            parameters.extend((boundary[0], boundary[0], boundary[1]))
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
                "<",
                str(last[timestamp_column]),
                str(last[primary_key]),
            ):
                next_cursor = self._encode_cursor(
                    table,
                    page_size,
                    filter_hash,
                    "next",
                    str(last[timestamp_column]),
                    str(last[primary_key]),
                )
            if self._boundary_exists(
                table,
                timestamp_column,
                primary_key,
                normalized_filters,
                ">",
                str(first[timestamp_column]),
                str(first[primary_key]),
            ):
                previous_cursor = self._encode_cursor(
                    table,
                    page_size,
                    filter_hash,
                    "previous",
                    str(first[timestamp_column]),
                    str(first[primary_key]),
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
                ("reviews", "decision", "reviews"),
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
            for table in ("action_attempts", "reviews", "transitions"):
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
        page_size: int,
        filter_hash: str,
        direction: str,
        timestamp: str,
        primary_key: str,
    ) -> str:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "table": table,
            "page_size": page_size,
            "filter_hash": filter_hash,
            "direction": direction,
            "sort_timestamp": timestamp,
            "primary_key": primary_key,
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
        operator: str,
        timestamp: str,
        key: str,
    ) -> bool:
        where, parameters = self._filter_clause(filters)
        where.append(
            f"({timestamp_column} {operator} ? OR "
            f"({timestamp_column} = ? AND {primary_key} {operator} ?))"
        )
        parameters.extend((timestamp, timestamp, key))
        row = self._connection.execute(
            f"SELECT 1 FROM {table} WHERE {' AND '.join(where)} LIMIT 1", parameters
        ).fetchone()
        return row is not None

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
        if not isinstance(worker_id, str) or not worker_id:
            raise ValueError("worker_id must be a non-empty string")
        if (
            not isinstance(lease_seconds, int)
            or isinstance(lease_seconds, bool)
            or lease_seconds <= 0
        ):
            raise ValueError("lease_seconds must be a positive int")

    @staticmethod
    def _require_known_table(table: str) -> None:
        if table not in {*_TABLE_PAGE_SPECS, "schema_migrations", "store_metadata"}:
            raise ValueError(f"unsupported table: {table}")
