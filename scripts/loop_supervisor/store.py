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
import re
import secrets
import sqlite3
import sys
from threading import RLock
from typing import Any, Iterator, Sequence
from uuid import uuid4

from scripts.harness_loop_runtime_lock import (
    RunLockToken,
    acquire_runtime_database_writer_lock,
    validate_run_lock_token,
)
from scripts.harness_loop_agents import validate_owned_regular_file
from scripts.harness_loop_contracts import validate_run_payload
from scripts.loop_supervisor.models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
    validate_repo_relative_root,
)


SCHEMA_VERSION = 16
ALLOWED_PAGE_SIZES = frozenset({20, 50, 100})
MAX_PAYLOAD_BYTES = 65_536
MAX_SUMMARY_CHARS = 4_096
MAX_SUMMARY_BYTES = 8_192
MAX_ARTIFACT_PATH_CHARS = 1_024
MAX_CHECKPOINT_CHARS = 512
MAX_CHECKPOINT_BYTES = 1_024
DEFAULT_HEARTBEAT_STALE_SECONDS = 120
SAFE_CHECKPOINT_PATTERN = re.compile(r"\A[A-Za-z0-9.][A-Za-z0-9._:/-]{0,511}\Z")
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
    canonical_identity: str
    run_id: str
    run_revision: int
    repo_relative_root: str
    policy: str
    phase: str
    action_type: str
    queue_owner: str
    not_before: str
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


_LEGACY_TIMESTAMP_COLUMNS: dict[str, tuple[str, ...]] = {
    "schema_migrations": ("applied_at",),
    "runs": ("created_at", "updated_at", "last_seen_at"),
    "actions": (
        "lease_expires_at",
        "lease_heartbeat_at",
        "created_at",
        "updated_at",
    ),
    "action_idempotency_aliases": ("created_at",),
    "action_attempts": ("started_at", "finished_at", "created_at"),
    "transitions": ("created_at",),
    "failures": ("first_seen_at", "last_seen_at", "created_at", "updated_at"),
    "reviews": ("created_at", "updated_at"),
    "review_reservations": ("due_at", "not_before", "created_at", "updated_at"),
    "review_cadence": ("updated_at",),
    "review_safety_gates": ("checked_at", "created_at"),
    "review_applications": ("created_at", "updated_at"),
    "review_application_targets": ("created_at", "updated_at"),
    "skill_invocations": ("created_at",),
    "review_findings": (
        "first_seen_at",
        "last_seen_at",
        "created_at",
        "updated_at",
    ),
    "user_decisions": ("created_at", "updated_at", "closed_at"),
    "services": ("heartbeat_at", "created_at", "updated_at"),
    "freshness_checks": ("checked_at", "created_at"),
    "skill_snapshots": ("created_at",),
    "aggregates": ("created_at", "updated_at"),
    "workers": ("heartbeat_at", "created_at", "updated_at"),
}


_OPTIONAL_LEGACY_TIMESTAMPS = frozenset(
    {
        ("actions", "lease_expires_at"),
        ("actions", "lease_heartbeat_at"),
        ("user_decisions", "closed_at"),
        ("services", "heartbeat_at"),
    }
)


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
    CREATE TABLE IF NOT EXISTS row_sequences (
      sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
      table_name TEXT NOT NULL,
      row_key TEXT NOT NULL,
      UNIQUE(table_name, row_key)
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
      repo_relative_root TEXT NOT NULL DEFAULT '.',
      state_fingerprint TEXT NOT NULL DEFAULT '',
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
      canonical_identity TEXT NOT NULL,
      run_id TEXT NOT NULL,
      run_revision INTEGER NOT NULL CHECK (run_revision >= 0),
      repo_relative_root TEXT NOT NULL DEFAULT '.',
      policy TEXT NOT NULL DEFAULT '',
      phase TEXT NOT NULL DEFAULT '',
      action_type TEXT NOT NULL,
      queue_owner TEXT NOT NULL DEFAULT 'worker',
      not_before TEXT NOT NULL DEFAULT '',
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
    """
    CREATE TABLE IF NOT EXISTS action_idempotency_aliases (
      idempotency_key TEXT PRIMARY KEY,
      canonical_identity TEXT NOT NULL,
      action_id TEXT NOT NULL REFERENCES actions(action_id),
      created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS actions_queue_idx ON actions(status, priority, created_at)",
    "CREATE INDEX IF NOT EXISTS actions_owner_queue_idx ON actions(queue_owner, status, not_before, priority, created_at)",
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
      accepted_review_json TEXT NOT NULL DEFAULT '{}',
      source_action_id TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS reviews_created_idx ON reviews(created_at)",
    """
    CREATE TABLE IF NOT EXISTS review_reservations (
      reservation_id TEXT PRIMARY KEY,
      action_id TEXT NOT NULL UNIQUE REFERENCES actions(action_id),
      status TEXT NOT NULL,
      due_at TEXT NOT NULL,
      not_before TEXT NOT NULL,
      lineages_json TEXT NOT NULL,
      positions_json TEXT NOT NULL,
      review_id TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_cadence (
      lineage_id TEXT PRIMARY KEY,
      reviewed_position INTEGER NOT NULL DEFAULT 0,
      deferred_position INTEGER NOT NULL DEFAULT 0,
      reserved_position INTEGER NOT NULL DEFAULT 0,
      reservation_id TEXT NOT NULL DEFAULT '',
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_safety_gates (
      gate_id TEXT PRIMARY KEY,
      status TEXT NOT NULL,
      checks_json TEXT NOT NULL,
      checked_at TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_applications (
      review_id TEXT PRIMARY KEY REFERENCES reviews(review_id) ON DELETE CASCADE,
      decision TEXT NOT NULL,
      status TEXT NOT NULL,
      target_count INTEGER NOT NULL,
      applied_count INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_application_targets (
      review_id TEXT NOT NULL REFERENCES review_applications(review_id) ON DELETE CASCADE,
      run_id TEXT NOT NULL,
      action_id TEXT NOT NULL UNIQUE REFERENCES actions(action_id),
      expected_revision INTEGER NOT NULL,
      expected_fingerprint TEXT NOT NULL,
      expected_post_write_fingerprint TEXT NOT NULL DEFAULT '',
      source_phase TEXT NOT NULL,
      target_phase TEXT NOT NULL,
      target_next_action TEXT NOT NULL,
      target_last_result TEXT NOT NULL,
      status TEXT NOT NULL,
      applied_revision INTEGER NOT NULL DEFAULT 0,
      error TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      PRIMARY KEY(review_id, run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_findings (
      finding_id TEXT PRIMARY KEY,
      review_id TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
      finding_key TEXT NOT NULL,
      status TEXT NOT NULL,
      severity TEXT NOT NULL DEFAULT '',
      summary TEXT NOT NULL DEFAULT '',
      evidence_json TEXT NOT NULL DEFAULT '[]',
      closure_evidence_json TEXT NOT NULL DEFAULT '[]',
      affected_runs_json TEXT NOT NULL DEFAULT '[]',
      remediation_action_id TEXT NOT NULL DEFAULT '',
      occurrence_count INTEGER NOT NULL DEFAULT 1,
      first_seen_at TEXT NOT NULL,
      last_seen_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(finding_key)
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
    CREATE INDEX IF NOT EXISTS freshness_checks_target_latest_idx
    ON freshness_checks(target, checked_at DESC, check_id DESC)
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
    CREATE TABLE IF NOT EXISTS skill_invocations (
      invocation_id TEXT PRIMARY KEY,
      action_id TEXT NOT NULL REFERENCES actions(action_id),
      attempt_id TEXT NOT NULL REFERENCES action_attempts(attempt_id),
      skill_path TEXT NOT NULL,
      artifact_path TEXT NOT NULL,
      artifact_sha256 TEXT NOT NULL,
      created_at TEXT NOT NULL,
      UNIQUE(attempt_id, skill_path)
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
        maintenance_lock: Any | None = None,
    ) -> None:
        self.project_root = project_root
        self.db_path = project_root / ".codex" / "supervisor" / "supervisor.db"
        self._connection = connection
        self._clock = clock
        self._lock = RLock()
        self._maintenance_lock = maintenance_lock
        self._closed = False

    @classmethod
    def open(cls, project_root: Path, *, clock: Any | None = None) -> "SupervisorStore":
        root = Path(project_root).resolve()
        db_path = root / ".codex" / "supervisor" / "supervisor.db"
        maintenance_lock = acquire_runtime_database_writer_lock(
            root, owner="supervisor-store"
        )
        maintenance_lock.__enter__()
        connection: sqlite3.Connection | None = None
        try:
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
        except BaseException:
            if connection is not None:
                connection.close()
            maintenance_lock.__exit__(*sys.exc_info())
            raise
        return cls(root, connection, clock, maintenance_lock)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self._connection.close()
            finally:
                if self._maintenance_lock is not None:
                    self._maintenance_lock.__exit__(None, None, None)
                    self._maintenance_lock = None

    def __enter__(self) -> "SupervisorStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    @contextmanager
    def _immediate_transaction(self) -> Iterator[None]:
        with self._lock:
            if self._connection.in_transaction:
                savepoint = f"nested_{uuid4().hex}"
                self._connection.execute(f"SAVEPOINT {savepoint}")
                try:
                    yield
                    self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                except BaseException:
                    self._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                    raise
                return
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield
                self._connection.commit()
            except BaseException:
                self._connection.rollback()
                raise

    def migrate(self) -> None:
        now = self._now_text()
        with self._immediate_transaction():
            for statement in _DDL:
                self._connection.execute(statement)
            self._connection.execute(
                """
                INSERT OR IGNORE INTO store_metadata(key, value)
                VALUES ('legacy_naive_timestamp_policy', 'assume_utc')
                """
            )
            self._ensure_run_state_fingerprint()
            self._ensure_run_execution_root()
            self._ensure_review_target_post_write_fingerprint()
            self._ensure_action_execution_root()
            self._ensure_action_ownership()
            self._ensure_review_resume_state()
            self._ensure_review_cadence_deferred_position()
            self._migrate_bounded_run_projection_summaries()
            self._migrate_v13_review_target_post_write_fingerprints()
            self._normalize_legacy_timestamps()
            self._ensure_action_canonical_identity()
            self._ensure_action_idempotency_aliases()
            self._ensure_stable_review_finding_identity()
            self._ensure_review_finding_evidence()
            self._ensure_membership_sequences()
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
        with self._lock:
            rows = self._connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        return [str(row[0]) for row in rows]

    def _normalize_legacy_timestamps(self) -> None:
        for table, configured_columns in _LEGACY_TIMESTAMP_COLUMNS.items():
            available_columns = {
                str(row["name"])
                for row in self._connection.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }
            columns = [
                column for column in configured_columns if column in available_columns
            ]
            if not columns:
                continue
            rows = self._connection.execute(
                f"SELECT rowid AS legacy_rowid, {', '.join(columns)} FROM {table}"
            ).fetchall()
            for row in rows:
                normalized: dict[str, str] = {}
                for column in columns:
                    raw_value = row[column]
                    try:
                        normalized[column] = self._normalize_legacy_timestamp(
                            raw_value,
                            allow_empty=(table, column) in _OPTIONAL_LEGACY_TIMESTAMPS,
                        )
                    except (TypeError, ValueError) as exc:
                        raise ValueError(
                            "invalid legacy timestamp in "
                            f"{table}.{column} at rowid {row['legacy_rowid']}"
                        ) from exc
                assignments = ", ".join(f"{column} = ?" for column in columns)
                self._connection.execute(
                    f"UPDATE {table} SET {assignments} WHERE rowid = ?",
                    (*[normalized[column] for column in columns], row["legacy_rowid"]),
                )

    def _ensure_run_state_fingerprint(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(runs)").fetchall()
        }
        if "state_fingerprint" not in columns:
            self._connection.execute(
                "ALTER TABLE runs ADD COLUMN state_fingerprint TEXT NOT NULL DEFAULT ''"
            )

    def _ensure_run_execution_root(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(runs)").fetchall()
        }
        if "repo_relative_root" not in columns:
            self._connection.execute(
                "ALTER TABLE runs "
                "ADD COLUMN repo_relative_root TEXT NOT NULL DEFAULT '.'"
            )
        self._backfill_run_execution_roots()

    def _backfill_run_execution_roots(self) -> None:
        """Recover v12 worktree roots only from canonical, fingerprint-bound state."""
        from .reconciler import _state_fingerprint, _state_revision

        rows = self._connection.execute(
            "SELECT * FROM runs WHERE repo_relative_root = '.'"
        ).fetchall()
        for row in rows:
            try:
                summary = json.loads(str(row["summary_json"]))
                refs = summary.get("artifact_refs", [])
                if not isinstance(refs, list):
                    raise ValueError("run projection artifact refs must be a list")
                run_id = str(row["run_id"])
                tail = (".codex", "loop-runs", run_id, "run.json")
                roots: set[str] = set()
                for ref in refs:
                    if not isinstance(ref, str):
                        continue
                    relative = PurePosixPath(ref)
                    if (
                        relative.is_absolute()
                        or relative.as_posix() != ref
                        or tuple(relative.parts[-4:]) != tail
                    ):
                        continue
                    root = PurePosixPath(*relative.parts[:-4]).as_posix() or "."
                    root = validate_repo_relative_root(root)
                    if root == ".":
                        continue
                    root_parts = PurePosixPath(root).parts
                    if root_parts[:1] != (".worktrees",) or len(root_parts) != 2:
                        continue
                    path = self.project_root.joinpath(*relative.parts)
                    payload = json.loads(
                        validate_owned_regular_file(
                            self.project_root,
                            path,
                            "legacy run projection",
                        ).read_text(encoding="utf-8")
                    )
                    if not isinstance(payload, dict):
                        continue
                    validate_run_payload(payload)
                    if (
                        payload.get("run_id") != run_id
                        or _state_revision(payload) != int(row["revision"])
                        or not str(row["state_fingerprint"])
                        or _state_fingerprint(payload) != str(row["state_fingerprint"])
                    ):
                        continue
                    roots.add(root)
                if len(roots) != 1:
                    continue
                self._connection.execute(
                    "UPDATE runs SET repo_relative_root = ? WHERE run_id = ?",
                    (roots.pop(), run_id),
                )
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue

    def _ensure_review_target_post_write_fingerprint(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute(
                "PRAGMA table_info(review_application_targets)"
            ).fetchall()
        }
        if "expected_post_write_fingerprint" not in columns:
            self._connection.execute(
                "ALTER TABLE review_application_targets "
                "ADD COLUMN expected_post_write_fingerprint TEXT NOT NULL DEFAULT ''"
            )

    def _migrate_v13_review_target_post_write_fingerprints(self) -> None:
        """Anchor only exact pre-write v13 applications; block every other legacy state."""
        from .reconciler import _state_fingerprint, _state_revision
        from .reviewer import validate_review_payload

        reviews = self._connection.execute(
            "SELECT * FROM reviews WHERE status = 'review_applying'"
        ).fetchall()
        for review_row in reviews:
            review_id = str(review_row["review_id"])
            targets = self._connection.execute(
                """
                SELECT * FROM review_application_targets
                WHERE review_id = ? ORDER BY run_id
                """,
                (review_id,),
            ).fetchall()
            if not targets or not any(
                not str(target["expected_post_write_fingerprint"]) for target in targets
            ):
                continue
            try:
                accepted = json.loads(str(review_row["accepted_review_json"]))
                if not isinstance(accepted, dict):
                    raise ValueError("accepted review must be an object")
                reviewed_runs = accepted.get("reviewed_runs")
                candidate = dict(accepted)
                candidate.pop("reviewed_runs", None)
                review = validate_review_payload(
                    candidate,
                    reviewed_runs=reviewed_runs,
                    allow_legacy_skill_governance_without_hash=True,
                )
                if (
                    review.review_id != review_id
                    or review.decision.value != str(review_row["decision"])
                    or set(review.affected_run_ids)
                    != {str(target["run_id"]) for target in targets}
                ):
                    raise ValueError("accepted review does not match legacy targets")
                source = self._connection.execute(
                    "SELECT * FROM actions WHERE action_id = ?",
                    (str(review_row["source_action_id"]),),
                ).fetchone()
                if source is None or str(source["action_type"]) != "run_reviewer":
                    raise ValueError("legacy review lacks a Reviewer source action")
                derived: list[tuple[str, str]] = []
                for target in targets:
                    if str(target["expected_post_write_fingerprint"]):
                        continue
                    action = self._connection.execute(
                        "SELECT * FROM actions WHERE action_id = ?",
                        (str(target["action_id"]),),
                    ).fetchone()
                    run = self._connection.execute(
                        "SELECT * FROM runs WHERE run_id = ?",
                        (str(target["run_id"]),),
                    ).fetchone()
                    if (
                        action is None
                        or run is None
                        or str(action["queue_owner"]) != ActionOwner.SUPERVISOR.value
                        or str(action["run_id"]) != str(target["run_id"])
                        or int(action["run_revision"]) != int(target["expected_revision"])
                        or str(action["repo_relative_root"])
                        != str(run["repo_relative_root"])
                        or int(run["revision"]) != int(target["expected_revision"])
                        or str(run["state_fingerprint"])
                        != str(target["expected_fingerprint"])
                    ):
                        raise ValueError("legacy target identity is not immutable")
                    payload = self._validated_legacy_target_payload(run)
                    if (
                        _state_revision(payload) != int(target["expected_revision"])
                        or _state_fingerprint(payload)
                        != str(target["expected_fingerprint"])
                    ):
                        raise ValueError("legacy target is not exact pre-write state")
                    updated = dict(payload)
                    directives = list(updated.get("reviewer_directives") or [])
                    directive = {
                        "review_id": review.review_id,
                        "decision": review.decision.value,
                        "summary": review.summary,
                        "evidence_refs": list(review.evidence_refs),
                    }
                    if directive not in directives:
                        directives.append(directive)
                    updated["reviewer_directives"] = directives
                    updated["phase"] = str(target["target_phase"])
                    updated["next_action"] = str(target["target_next_action"])
                    updated["last_result"] = str(target["target_last_result"])
                    updated["state_revision"] = int(target["expected_revision"]) + 1
                    derived.append((str(target["run_id"]), _state_fingerprint(updated)))
                for run_id, fingerprint in derived:
                    self._connection.execute(
                        """
                        UPDATE review_application_targets
                        SET expected_post_write_fingerprint = ?, updated_at = ?
                        WHERE review_id = ? AND run_id = ?
                          AND expected_post_write_fingerprint = ''
                        """,
                        (fingerprint, self._now_text(), review_id, run_id),
                    )
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                self._connection.execute(
                    """
                    UPDATE reviews
                    SET status = 'review_migration_blocked', summary = ?, updated_at = ?
                    WHERE review_id = ? AND status = 'review_applying'
                    """,
                    (
                        "v13 review target lacks immutable pre-write state; "
                        "operator resolution is required",
                        self._now_text(),
                        review_id,
                    ),
                )

    def _validated_legacy_target_payload(self, run: sqlite3.Row) -> dict[str, Any]:
        summary = json.loads(str(run["summary_json"]))
        if not isinstance(summary, dict):
            raise ValueError("legacy run projection summary is invalid")
        root = validate_repo_relative_root(str(run["repo_relative_root"]))
        expected_parts = (
            *PurePosixPath(root).parts,
            ".codex",
            "loop-runs",
            str(run["run_id"]),
            "run.json",
        )
        refs = summary.get("artifact_refs", [])
        candidates = [
            ref
            for ref in refs
            if isinstance(ref, str)
            and not PurePosixPath(ref).is_absolute()
            and PurePosixPath(ref).as_posix() == ref
            and tuple(PurePosixPath(ref).parts) == expected_parts
        ]
        if len(candidates) != 1:
            raise ValueError("legacy run projection lacks one canonical artifact")
        path = self.project_root.joinpath(*PurePosixPath(candidates[0]).parts)
        payload = json.loads(
            validate_owned_regular_file(
                self.project_root,
                path,
                "legacy review target",
            ).read_text(encoding="utf-8")
        )
        if not isinstance(payload, dict) or payload.get("run_id") != run["run_id"]:
            raise ValueError("legacy review target run id mismatch")
        validate_run_payload(payload)
        return payload

    def _ensure_action_execution_root(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(actions)").fetchall()
        }
        if "repo_relative_root" not in columns:
            self._connection.execute(
                "ALTER TABLE actions "
                "ADD COLUMN repo_relative_root TEXT NOT NULL DEFAULT '.'"
            )

    def _ensure_action_ownership(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(actions)").fetchall()
        }
        if "queue_owner" not in columns:
            self._connection.execute(
                "ALTER TABLE actions "
                "ADD COLUMN queue_owner TEXT NOT NULL DEFAULT 'worker'"
            )
        if "not_before" not in columns:
            self._connection.execute(
                "ALTER TABLE actions ADD COLUMN not_before TEXT NOT NULL DEFAULT ''"
            )
        self._connection.execute(
            "UPDATE actions SET queue_owner = 'reviewer' "
            "WHERE action_type = 'run_reviewer' AND queue_owner != 'reviewer'"
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS actions_owner_queue_idx "
            "ON actions(queue_owner, status, not_before, priority, created_at)"
        )

    def _ensure_review_resume_state(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(reviews)").fetchall()
        }
        missing_immutable_anchor = (
            "accepted_review_json" not in columns
            or "source_action_id" not in columns
        )
        if "accepted_review_json" not in columns:
            self._connection.execute(
                "ALTER TABLE reviews "
                "ADD COLUMN accepted_review_json TEXT NOT NULL DEFAULT '{}'"
            )
        if "source_action_id" not in columns:
            self._connection.execute(
                "ALTER TABLE reviews "
                "ADD COLUMN source_action_id TEXT NOT NULL DEFAULT ''"
            )
        if missing_immutable_anchor:
            self._migrate_legacy_applying_reviews()

    def _ensure_review_cadence_deferred_position(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute(
                "PRAGMA table_info(review_cadence)"
            ).fetchall()
        }
        if "deferred_position" not in columns:
            self._connection.execute(
                "ALTER TABLE review_cadence "
                "ADD COLUMN deferred_position INTEGER NOT NULL DEFAULT 0"
            )

    def _migrate_bounded_run_projection_summaries(self) -> None:
        rows = self._connection.execute(
            "SELECT run_id, summary_json FROM runs"
        ).fetchall()
        for row in rows:
            outer = json.loads(str(row["summary_json"]))
            if not isinstance(outer, dict):
                raise ValueError("run projection summary must be an object")
            if "summary" not in outer:
                continue
            raw_summary = outer.get("summary")
            if not isinstance(raw_summary, str):
                raise ValueError("run projection inner summary must be a string")
            if not raw_summary:
                continue
            summary = json.loads(raw_summary)
            if not isinstance(summary, dict):
                raise ValueError("run projection inner summary must be an object")
            if "reviewer_directives" not in summary:
                continue
            summary.pop("reviewer_directives")
            bounded_summary = self._json(summary)
            self._validate_summary(
                bounded_summary,
                field_name="run projection summary",
            )
            outer["summary"] = bounded_summary
            self._connection.execute(
                "UPDATE runs SET summary_json = ? WHERE run_id = ?",
                (self._json(outer), row["run_id"]),
            )

    def _migrate_legacy_applying_reviews(self) -> None:
        """Block pre-v11 applying rows that lack persisted immutable acceptance."""
        rows = self._connection.execute(
            """
            SELECT * FROM reviews
            WHERE status = 'review_applying'
              AND accepted_review_json = '{}'
            ORDER BY created_at, review_id
            """
        ).fetchall()
        for row in rows:
            self._connection.execute(
                """
                UPDATE reviews
                SET status = 'review_migration_blocked',
                    summary = ?, updated_at = ?
                WHERE review_id = ? AND status = 'review_applying'
                """,
                (
                    "pre-v11 applying review has no immutable acceptance anchor; "
                    "operator resolution is required",
                    self._now_text(),
                    row["review_id"],
                ),
            )

    @staticmethod
    def _normalize_legacy_timestamp(value: object, *, allow_empty: bool) -> str:
        if not isinstance(value, str):
            raise TypeError("legacy timestamp must be a string")
        if not value:
            if allow_empty:
                return ""
            raise ValueError("legacy timestamp must be non-empty")
        candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return SupervisorStore._time_text(parsed)

    def _ensure_action_canonical_identity(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(actions)").fetchall()
        }
        if "canonical_identity" not in columns:
            self._connection.execute(
                "ALTER TABLE actions "
                "ADD COLUMN canonical_identity TEXT NOT NULL DEFAULT ''"
            )
        rows = self._connection.execute(
            """
            SELECT action_id, run_id, run_revision, repo_relative_root,
                   policy, phase, action_type, task_id, queue_owner
            FROM actions
            """
        ).fetchall()
        for row in rows:
            canonical_identity = self._canonical_action_identity(
                run_id=str(row["run_id"]),
                run_revision=int(row["run_revision"]),
                repo_relative_root=str(row["repo_relative_root"]),
                policy=str(row["policy"]),
                phase=str(row["phase"]),
                action_type=str(row["action_type"]),
                task_id=str(row["task_id"]),
                queue_owner=str(row["queue_owner"]),
            )
            self._connection.execute(
                "UPDATE actions SET canonical_identity = ? WHERE action_id = ?",
                (canonical_identity, row["action_id"]),
            )
        try:
            self._connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS actions_canonical_identity_idx "
                "ON actions(canonical_identity)"
            )
        except sqlite3.IntegrityError as exc:
            raise RuntimeError(
                "cannot migrate duplicate canonical action identities"
            ) from exc

    def _ensure_action_idempotency_aliases(self) -> None:
        self._connection.execute(
            """
            INSERT OR IGNORE INTO action_idempotency_aliases(
              idempotency_key, canonical_identity, action_id, created_at
            )
            SELECT idempotency_key, canonical_identity, action_id, created_at
            FROM actions
            """
        )
        self._connection.execute(
            """
            UPDATE action_idempotency_aliases
            SET canonical_identity = (
              SELECT actions.canonical_identity
              FROM actions
              WHERE actions.action_id = action_idempotency_aliases.action_id
            )
            """
        )

    def _ensure_stable_review_finding_identity(self) -> None:
        has_stable_unique_key = False
        for index in self._connection.execute(
            "PRAGMA index_list(review_findings)"
        ).fetchall():
            if not int(index["unique"]):
                continue
            columns = [
                str(row["name"])
                for row in self._connection.execute(
                    f"PRAGMA index_info({index['name']})"
                ).fetchall()
            ]
            if columns == ["finding_key"]:
                has_stable_unique_key = True
                break
        if has_stable_unique_key:
            return

        self._connection.execute(
            """
            CREATE TABLE review_findings_v4 (
              finding_id TEXT PRIMARY KEY,
              review_id TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
              finding_key TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              remediation_action_id TEXT NOT NULL DEFAULT '',
              occurrence_count INTEGER NOT NULL DEFAULT 1,
              first_seen_at TEXT NOT NULL,
              last_seen_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            WITH ranked AS (
              SELECT findings.*,
                     ROW_NUMBER() OVER (
                       PARTITION BY finding_key
                       ORDER BY last_seen_at DESC, updated_at DESC, rowid DESC
                     ) AS identity_rank,
                     SUM(occurrence_count) OVER (
                       PARTITION BY finding_key
                     ) AS total_occurrences,
                     MIN(first_seen_at) OVER (
                       PARTITION BY finding_key
                     ) AS earliest_first_seen,
                     MAX(last_seen_at) OVER (
                       PARTITION BY finding_key
                     ) AS latest_last_seen,
                     MIN(created_at) OVER (
                       PARTITION BY finding_key
                     ) AS earliest_created_at
              FROM review_findings AS findings
            )
            INSERT INTO review_findings_v4(
              finding_id, review_id, finding_key, status, summary,
              remediation_action_id, occurrence_count, first_seen_at,
              last_seen_at, created_at, updated_at
            )
            SELECT finding_id, review_id, finding_key, status, summary,
                   remediation_action_id, total_occurrences, earliest_first_seen,
                   latest_last_seen, earliest_created_at, updated_at
            FROM ranked WHERE identity_rank = 1
            """
        )
        self._connection.execute("DROP TABLE review_findings")
        self._connection.execute(
            "ALTER TABLE review_findings_v4 RENAME TO review_findings"
        )

    def _ensure_review_finding_evidence(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute(
                "PRAGMA table_info(review_findings)"
            ).fetchall()
        }
        additions = {
            "severity": "TEXT NOT NULL DEFAULT ''",
            "evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "closure_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "affected_runs_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, definition in additions.items():
            if column not in columns:
                self._connection.execute(
                    f"ALTER TABLE review_findings ADD COLUMN {column} {definition}"
                )

    def _ensure_membership_sequences(self) -> None:
        for table, (primary_key, _timestamp_column) in _TABLE_PAGE_SPECS.items():
            self._connection.execute(
                f"""
                INSERT OR IGNORE INTO row_sequences(table_name, row_key)
                SELECT ?, CAST({primary_key} AS TEXT) FROM {table} ORDER BY rowid
                """,
                (table,),
            )
            self._connection.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS row_sequence_{table}_insert
                AFTER INSERT ON {table}
                BEGIN
                  INSERT INTO row_sequences(table_name, row_key)
                  VALUES ('{table}', CAST(NEW.{primary_key} AS TEXT));
                END
                """
            )

    def pragma(self, name: str) -> Any:
        if name not in {"journal_mode", "foreign_keys", "busy_timeout", "user_version"}:
            raise ValueError(f"unsupported pragma: {name}")
        with self._lock:
            return self._connection.execute(f"PRAGMA {name}").fetchone()[0]

    def count(self, table: str) -> int:
        self._require_known_table(table)
        with self._lock:
            return int(
                self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            )

    def fetch_all(self, table: str) -> list[dict[str, Any]]:
        self._require_known_table(table)
        with self._lock:
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
        expected_run_fingerprint: str = "",
        run_lock_token: RunLockToken | None = None,
    ) -> ActionRecord:
        if not isinstance(request, ActionRequest):
            raise TypeError("request must be an ActionRequest")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise TypeError("priority must be an int")
        if not isinstance(recovery_tier, int) or recovery_tier < 0:
            raise ValueError("recovery_tier must be a non-negative int")
        if not isinstance(expected_run_fingerprint, str):
            raise TypeError("expected_run_fingerprint must be a string")
        locked_snapshot = run_lock_token is not None
        if run_lock_token is not None:
            expected_execution_root = (
                self.project_root / request.repo_relative_root
            ).resolve()
            validate_run_lock_token(
                run_lock_token, expected_execution_root, request.run_id
            )
        payload = request.payload_for_storage()
        self._validate_payload(payload)
        artifacts = self._validate_artifact_paths(artifact_paths)
        payload_json = self._json(payload)
        artifact_json = self._json(artifacts)
        canonical_identity = self._canonical_action_identity(
            run_id=request.run_id,
            run_revision=request.run_revision,
            policy=request.policy,
            phase=request.phase,
            action_type=request.action_type.value,
            task_id=request.task_id,
            repo_relative_root=request.repo_relative_root,
            queue_owner=request.queue_owner.value,
        )
        not_before = (
            self._coerce_time(request.not_before) if request.not_before else ""
        )
        now = self._now_text()
        with self._immediate_transaction():
            existing_by_key = self._connection.execute(
                """
                SELECT actions.* FROM action_idempotency_aliases AS aliases
                JOIN actions ON actions.action_id = aliases.action_id
                WHERE aliases.idempotency_key = ?
                """,
                (request.idempotency_key,),
            ).fetchone()
            existing_by_identity = self._connection.execute(
                "SELECT * FROM actions WHERE canonical_identity = ?",
                (canonical_identity,),
            ).fetchone()
            if (
                existing_by_key is not None
                and existing_by_identity is not None
                and existing_by_key["action_id"] != existing_by_identity["action_id"]
            ):
                raise ValueError("idempotency identity conflict spans multiple actions")
            existing = existing_by_key or existing_by_identity
            if existing is not None:
                expected_identity = (
                    request.run_id,
                    request.run_revision,
                    request.phase,
                    request.action_type.value,
                    request.task_id,
                    request.policy,
                    request.repo_relative_root,
                    request.queue_owner.value,
                    canonical_identity,
                )
                stored_identity = (
                    str(existing["run_id"]),
                    int(existing["run_revision"]),
                    str(existing["phase"]),
                    str(existing["action_type"]),
                    str(existing["task_id"]),
                    str(existing["policy"]),
                    str(existing["repo_relative_root"]),
                    str(existing["queue_owner"]),
                    str(existing["canonical_identity"]),
                )
                if stored_identity != expected_identity:
                    raise ValueError(
                        "idempotency identity conflict between stored and incoming action"
                    )
                self._connection.execute(
                    """
                    INSERT INTO action_idempotency_aliases(
                      idempotency_key, canonical_identity, action_id, created_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(idempotency_key) DO NOTHING
                    """,
                    (
                        request.idempotency_key,
                        canonical_identity,
                        existing["action_id"],
                        now,
                    ),
                )
                run = self._connection.execute(
                    "SELECT revision, phase, state_fingerprint FROM runs WHERE run_id = ?",
                    (existing["run_id"],),
                ).fetchone()
                reopen = (
                    existing["status"] == "completed"
                    and locked_snapshot
                    and bool(expected_run_fingerprint)
                    and run is not None
                    and int(run["revision"]) == int(existing["run_revision"])
                    and str(run["phase"]) == str(existing["phase"])
                    and str(run["state_fingerprint"])
                    == expected_run_fingerprint
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
                    SET next_action = ?, priority = ?, recovery_tier = ?,
                        payload_json = ?, artifact_json = ?, not_before = ?,
                        status = CASE WHEN ? THEN 'pending' ELSE status END,
                        lease_owner = CASE WHEN ? THEN '' ELSE lease_owner END,
                        lease_expires_at = CASE WHEN ? THEN '' ELSE lease_expires_at END,
                        lease_heartbeat_at = CASE WHEN ? THEN '' ELSE lease_heartbeat_at END,
                        updated_at = ?
                    WHERE action_id = ?
                    """,
                    (
                        request.next_action,
                        priority,
                        recovery_tier,
                        stored_payload_json,
                        stored_artifact_json,
                        not_before,
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
                      action_id, idempotency_key, canonical_identity,
                      run_id, run_revision, repo_relative_root, policy, phase,
                      action_type, queue_owner, not_before, task_id, next_action,
                      status, priority, recovery_tier,
                      payload_json, artifact_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.action_id,
                        request.idempotency_key,
                        canonical_identity,
                        request.run_id,
                        request.run_revision,
                        request.repo_relative_root,
                        request.policy,
                        request.phase,
                        request.action_type.value,
                        request.queue_owner.value,
                        not_before,
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
                self._connection.execute(
                    """
                    INSERT INTO action_idempotency_aliases(
                      idempotency_key, canonical_identity, action_id, created_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        request.idempotency_key,
                        canonical_identity,
                        request.action_id,
                        now,
                    ),
                )
                row = self._connection.execute(
                    "SELECT * FROM actions WHERE action_id = ?", (request.action_id,)
                ).fetchone()
        return self._action_record(row)

    def reserve_review_action(
        self,
        request: ActionRequest,
        *,
        reservation_id: str,
        lineage_positions: Mapping[str, int],
        due_at: datetime | str,
        not_before: datetime | str,
        priority: int = 25,
    ) -> ActionRecord:
        """Atomically enqueue a project review and reserve its cadence positions."""
        self._required_text(reservation_id, "reservation_id")
        if request.queue_owner is not ActionOwner.REVIEWER:
            raise ValueError("review reservations require Reviewer-owned actions")
        positions = self._validate_lineage_positions(lineage_positions)
        due = self._coerce_time(due_at)
        ready = self._coerce_time(not_before)
        now = self._now_text()
        with self._immediate_transaction():
            action = self.enqueue_action(request, priority=priority)
            if action.status == "cancelled":
                self._connection.execute(
                    """
                    UPDATE actions
                    SET status = 'pending', lease_owner = '', lease_expires_at = '',
                        lease_heartbeat_at = '', updated_at = ?
                    WHERE action_id = ? AND status = 'cancelled'
                    """,
                    (now, action.action_id),
                )
                action = self._action_record(
                    self._connection.execute(
                        "SELECT * FROM actions WHERE action_id = ?", (action.action_id,)
                    ).fetchone()
                )
            self._connection.execute(
                """
                INSERT INTO review_reservations(
                  reservation_id, action_id, status, due_at, not_before,
                  lineages_json, positions_json, created_at, updated_at
                ) VALUES (?, ?, 'reserved', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reservation_id) DO UPDATE SET
                  status = 'reserved', due_at = excluded.due_at,
                  not_before = excluded.not_before,
                  lineages_json = excluded.lineages_json,
                  positions_json = excluded.positions_json,
                  review_id = '', updated_at = excluded.updated_at
                WHERE review_reservations.status = 'released'
                """,
                (
                    reservation_id,
                    action.action_id,
                    due,
                    ready,
                    self._json(sorted(positions)),
                    self._json(positions),
                    now,
                    now,
                ),
            )
            for lineage_id, position in positions.items():
                existing = self._connection.execute(
                    "SELECT * FROM review_cadence WHERE lineage_id = ?",
                    (lineage_id,),
                ).fetchone()
                if existing is not None and str(existing["reservation_id"]):
                    raise ValueError(f"lineage already has a review reservation: {lineage_id}")
                reviewed = int(existing["reviewed_position"]) if existing else 0
                self._connection.execute(
                    """
                    INSERT INTO review_cadence(
                      lineage_id, reviewed_position, reserved_position,
                      reservation_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(lineage_id) DO UPDATE SET
                      reserved_position = excluded.reserved_position,
                      reservation_id = excluded.reservation_id,
                      updated_at = excluded.updated_at
                    """,
                    (lineage_id, reviewed, position, reservation_id, now),
                )
        return action

    def release_review_reservation(
        self,
        reservation_id: str,
        *,
        reason: str,
        defer_through_positions: Mapping[str, int] | None = None,
    ) -> None:
        self._required_text(reservation_id, "reservation_id")
        self._validate_summary(reason, field_name="reservation release reason")
        deferred = (
            self._validate_lineage_positions(defer_through_positions)
            if defer_through_positions is not None
            else None
        )
        now = self._now_text()
        with self._immediate_transaction():
            reservation = self._connection.execute(
                "SELECT * FROM review_reservations WHERE reservation_id = ?",
                (reservation_id,),
            ).fetchone()
            if reservation is None:
                raise KeyError(reservation_id)
            if reservation["status"] == "released":
                return
            if reservation["status"] != "reserved":
                raise ValueError("only reserved review cadence can be released")
            positions = json.loads(str(reservation["positions_json"]))
            if deferred is not None and set(deferred) != set(positions):
                raise ValueError("deferred review lineages do not match reservation")
            for lineage_id, position in positions.items():
                deferred_position = (
                    max(int(position), deferred[lineage_id])
                    if deferred is not None
                    else int(position)
                )
                self._connection.execute(
                    """
                    UPDATE review_cadence
                    SET deferred_position = CASE
                          WHEN ? THEN MAX(deferred_position, ?)
                          ELSE deferred_position
                        END,
                        reserved_position = 0, reservation_id = '', updated_at = ?
                    WHERE lineage_id = ? AND reservation_id = ?
                    """,
                    (
                        1 if deferred is not None else 0,
                        deferred_position,
                        now,
                        lineage_id,
                        reservation_id,
                    ),
                )
            self._connection.execute(
                """
                UPDATE review_reservations
                SET status = 'released', review_id = ?, updated_at = ?
                WHERE reservation_id = ?
                """,
                (reason, now, reservation_id),
            )
            self._connection.execute(
                """
                UPDATE actions
                SET status = 'cancelled', lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_id = ? AND status IN ('pending', 'leased')
                """,
                (now, reservation["action_id"]),
            )

    def coalesce_review_reservation(
        self,
        request: ActionRequest,
        *,
        reservation_id: str,
        lineage_positions: Mapping[str, int],
    ) -> ActionRecord:
        positions = self._validate_lineage_positions(lineage_positions)
        now = self._now_text()
        with self._immediate_transaction():
            reservation = self._connection.execute(
                "SELECT * FROM review_reservations WHERE reservation_id = ?",
                (reservation_id,),
            ).fetchone()
            if reservation is None or reservation["status"] != "reserved":
                raise ValueError("review reservation is not pending")
            if str(reservation["action_id"]) != request.action_id:
                raise ValueError("review reservation action identity changed")
            action = self.update_pending_action(request)
            self._connection.execute(
                """
                UPDATE review_reservations
                SET lineages_json = ?, positions_json = ?, updated_at = ?
                WHERE reservation_id = ? AND status = 'reserved'
                """,
                (
                    self._json(sorted(positions)),
                    self._json(positions),
                    now,
                    reservation_id,
                ),
            )
            for lineage_id, position in positions.items():
                existing = self._connection.execute(
                    "SELECT * FROM review_cadence WHERE lineage_id = ?",
                    (lineage_id,),
                ).fetchone()
                if existing is not None and str(existing["reservation_id"]) not in {
                    "",
                    reservation_id,
                }:
                    raise ValueError(f"lineage already has a review reservation: {lineage_id}")
                reviewed = int(existing["reviewed_position"]) if existing else 0
                self._connection.execute(
                    """
                    INSERT INTO review_cadence(
                      lineage_id, reviewed_position, reserved_position,
                      reservation_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(lineage_id) DO UPDATE SET
                      reserved_position = excluded.reserved_position,
                      reservation_id = excluded.reservation_id,
                      updated_at = excluded.updated_at
                    """,
                    (lineage_id, reviewed, position, reservation_id, now),
                )
        return action

    def complete_review_reservation(
        self,
        reservation_id: str,
        *,
        review_id: str,
    ) -> None:
        now = self._now_text()
        with self._immediate_transaction():
            reservation = self._connection.execute(
                "SELECT * FROM review_reservations WHERE reservation_id = ?",
                (reservation_id,),
            ).fetchone()
            if reservation is None:
                raise KeyError(reservation_id)
            if reservation["status"] == "completed":
                if str(reservation["review_id"]) != review_id:
                    raise ValueError("review reservation completed by another review")
                return
            positions = json.loads(str(reservation["positions_json"]))
            for lineage_id, position in positions.items():
                updated = self._connection.execute(
                    """
                    UPDATE review_cadence
                    SET reviewed_position = ?, reserved_position = 0,
                        reservation_id = '', updated_at = ?
                    WHERE lineage_id = ? AND reservation_id = ?
                    """,
                    (int(position), now, lineage_id, reservation_id),
                )
                if updated.rowcount != 1:
                    raise ValueError("review cadence reservation ownership changed")
            self._connection.execute(
                """
                UPDATE review_reservations
                SET status = 'completed', review_id = ?, updated_at = ?
                WHERE reservation_id = ?
                """,
                (review_id, now, reservation_id),
            )

    def complete_reviewer_action(
        self,
        action_id: str,
        owner_id: str,
        result: ActionResult,
        *,
        reservation_id: str,
        review_id: str,
    ) -> AttemptRecord:
        """Atomically complete the Reviewer lease and its cadence reservation."""
        with self._immediate_transaction():
            attempt = self.complete_action(action_id, owner_id, result)
            self.complete_review_reservation(
                reservation_id,
                review_id=review_id,
            )
        return attempt

    def review_cadence_positions(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM review_cadence ORDER BY lineage_id"
            ).fetchall()
        return {str(row["lineage_id"]): dict(row) for row in rows}

    def record_review_safety_gate(
        self,
        gate_id: str,
        *,
        status: str,
        checks: Mapping[str, Any],
        checked_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        self._required_text(gate_id, "gate_id")
        if status not in {"pass", "fail"}:
            raise ValueError("safety gate status must be pass or fail")
        self._validate_payload(checks)
        timestamp = self._coerce_time(checked_at)
        with self._immediate_transaction():
            self._connection.execute(
                """
                INSERT INTO review_safety_gates(
                  gate_id, status, checks_json, checked_at, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (gate_id, status, self._json(checks), timestamp, timestamp),
            )
            row = self._connection.execute(
                "SELECT * FROM review_safety_gates WHERE gate_id = ?", (gate_id,)
            ).fetchone()
        return self._decoded_row(row)

    def prepare_review_application(
        self,
        *,
        review_id: str,
        decision: str,
        targets: Sequence[tuple[ActionRequest, Mapping[str, Any]]],
    ) -> list[ActionRecord]:
        """Persist every target action before any review side effect runs."""
        self._required_text(review_id, "review_id")
        if not targets:
            return []
        now = self._now_text()
        with self._immediate_transaction():
            review = self._connection.execute(
                "SELECT * FROM reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
            if review is None:
                self._connection.execute(
                    """
                    INSERT INTO reviews(
                      review_id, trigger, status, decision, summary,
                      evidence_json, created_at, updated_at
                    ) VALUES (?, 'direct_application', 'review_applying', ?, '', '[]', ?, ?)
                    """,
                    (review_id, decision, now, now),
                )
            elif review["status"] not in {"review_applying", "review_complete"}:
                self._connection.execute(
                    """
                    UPDATE reviews SET status = 'review_applying', decision = ?, updated_at = ?
                    WHERE review_id = ?
                    """,
                    (decision, now, review_id),
                )
            self._connection.execute(
                """
                INSERT INTO review_applications(
                  review_id, decision, status, target_count, applied_count,
                  created_at, updated_at
                ) VALUES (?, ?, 'applying', ?, 0, ?, ?)
                ON CONFLICT(review_id) DO NOTHING
                """,
                (review_id, decision, len(targets), now, now),
            )
            application = self._connection.execute(
                "SELECT * FROM review_applications WHERE review_id = ?", (review_id,)
            ).fetchone()
            if (
                str(application["decision"]) != decision
                or int(application["target_count"]) != len(targets)
            ):
                raise ValueError("review application identity changed")
            actions: list[ActionRecord] = []
            for request, target in targets:
                if request.queue_owner is not ActionOwner.SUPERVISOR:
                    raise ValueError("review application targets must be Supervisor-owned")
                action = self.enqueue_action(request, priority=20)
                actions.append(action)
                values = (
                    review_id,
                    request.run_id,
                    request.action_id,
                    int(target["expected_revision"]),
                    str(target["expected_fingerprint"]),
                    str(target.get("expected_post_write_fingerprint", "")),
                    str(target["source_phase"]),
                    str(target["target_phase"]),
                    str(target["target_next_action"]),
                    str(target["target_last_result"]),
                    now,
                    now,
                )
                self._connection.execute(
                    """
                    INSERT INTO review_application_targets(
                      review_id, run_id, action_id, expected_revision,
                      expected_fingerprint, expected_post_write_fingerprint,
                      source_phase, target_phase,
                      target_next_action, target_last_result, status,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                    ON CONFLICT(review_id, run_id) DO NOTHING
                    """,
                    values,
                )
                stored = self._connection.execute(
                    """
                    SELECT * FROM review_application_targets
                    WHERE review_id = ? AND run_id = ?
                    """,
                    (review_id, request.run_id),
                ).fetchone()
                expected = values[:10]
                actual = tuple(stored[key] for key in (
                    "review_id",
                    "run_id",
                    "action_id",
                    "expected_revision",
                    "expected_fingerprint",
                    "expected_post_write_fingerprint",
                    "source_phase",
                    "target_phase",
                    "target_next_action",
                    "target_last_result",
                ))
                if actual != expected:
                    raise ValueError("review application target identity changed")
        return actions

    def review_application_targets(self, review_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM review_application_targets
                WHERE review_id = ? ORDER BY run_id
                """,
                (review_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def review_application_targets_for_recovery(
        self, review_id: str
    ) -> list[dict[str, Any]]:
        """Return the complete durable target set for an interrupted review application."""
        self._required_text(review_id, "review_id")
        with self._lock:
            application = self._connection.execute(
                """
                SELECT target_count FROM review_applications WHERE review_id = ?
                """,
                (review_id,),
            ).fetchone()
            rows = self._connection.execute(
                """
                SELECT * FROM review_application_targets
                WHERE review_id = ? ORDER BY run_id
                """,
                (review_id,),
            ).fetchall()
        if application is None:
            raise ValueError("review application is missing")
        if int(application["target_count"]) != len(rows):
            raise ValueError("review application target count changed")
        return [dict(row) for row in rows]

    def complete_review_application_target(
        self,
        *,
        review_id: str,
        run_id: str,
        action_id: str,
        owner_id: str,
        result: ActionResult,
        applied_revision: int,
    ) -> AttemptRecord:
        """Atomically complete one outbox action and advance aggregate review status."""
        with self._immediate_transaction():
            target = self._connection.execute(
                """
                SELECT * FROM review_application_targets
                WHERE review_id = ? AND run_id = ?
                """,
                (review_id, run_id),
            ).fetchone()
            if target is None or str(target["action_id"]) != action_id:
                raise ValueError("review application target does not match action")
            if target["status"] == "applied":
                attempts = self._connection.execute(
                    """
                    SELECT * FROM action_attempts WHERE action_id = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (action_id,),
                ).fetchone()
                if attempts is None:
                    raise RuntimeError("applied review target lacks action attempt")
                return AttemptRecord(
                    attempt_id=str(attempts["attempt_id"]),
                    action_id=action_id,
                    worker_id=str(attempts["worker_id"]),
                    result_class=str(attempts["result_class"]),
                    summary=str(attempts["summary"]),
                    failure_key=str(attempts["failure_key"]),
                    error_class=str(attempts["error_class"]),
                    artifact_paths=tuple(json.loads(attempts["artifact_json"])),
                    recovery_tier=int(attempts["recovery_tier"]),
                    started_at=str(attempts["started_at"]),
                    finished_at=str(attempts["finished_at"]),
                )
            application = self._connection.execute(
                "SELECT decision FROM review_applications WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            if application is None:
                raise ValueError("review application is missing")
            if str(application["decision"]) == "ask_user":
                provenance = self._action_review_decision_provenance(action_id)
                if (
                    not provenance.get("decision_id")
                    or provenance.get("review_id") != review_id
                    or provenance.get("run_id") != run_id
                ):
                    raise ValueError(
                        "ask_user review target lacks action decision provenance"
                    )
                decision = self._connection.execute(
                    """
                    SELECT decision_id FROM user_decisions
                    WHERE decision_id = ? AND run_id = ? AND status = 'open'
                    """,
                    (provenance["decision_id"], run_id),
                ).fetchone()
                if decision is None:
                    raise ValueError(
                        "ask_user review target lacks decision provenance"
                    )
            attempt = self.complete_action(action_id, owner_id, result)
            now = self._now_text()
            self._connection.execute(
                """
                UPDATE review_application_targets
                SET status = 'applied', applied_revision = ?, error = '', updated_at = ?
                WHERE review_id = ? AND run_id = ? AND status = 'pending'
                """,
                (applied_revision, now, review_id, run_id),
            )
            applied = int(
                self._connection.execute(
                    """
                    SELECT COUNT(*) FROM review_application_targets
                    WHERE review_id = ? AND status = 'applied'
                    """,
                    (review_id,),
                ).fetchone()[0]
            )
            total = int(
                self._connection.execute(
                    "SELECT target_count FROM review_applications WHERE review_id = ?",
                    (review_id,),
                ).fetchone()[0]
            )
            status = "completed" if applied == total else "applying"
            self._connection.execute(
                """
                UPDATE review_applications
                SET status = ?, applied_count = ?, updated_at = ?
                WHERE review_id = ?
                """,
                (status, applied, now, review_id),
            )
            if status == "completed":
                self._connection.execute(
                    """
                    UPDATE reviews SET status = 'review_complete', updated_at = ?
                    WHERE review_id = ?
                    """,
                    (now, review_id),
                )
        return attempt

    def supersede_review_application(self, review_id: str, *, reason: str) -> None:
        """Terminalize stale review work without advancing its cadence reservation."""
        self._required_text(review_id, "review_id")
        self._validate_summary(reason, field_name="review supersession reason")
        now = self._now_text()
        with self._immediate_transaction():
            review = self._connection.execute(
                "SELECT status FROM reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
            if review is None:
                return
            if str(review["status"]) == "review_superseded":
                return
            application = self._connection.execute(
                "SELECT status, decision FROM review_applications WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            if application is not None and str(application["status"]) == "completed":
                raise ValueError("completed review application cannot be superseded")
            if application is not None and str(application["decision"]) == "ask_user":
                targets = self._connection.execute(
                    """
                    SELECT run_id, action_id FROM review_application_targets
                    WHERE review_id = ?
                    """,
                    (review_id,),
                ).fetchall()
                for target in targets:
                    action_id = str(target["action_id"])
                    run_id = str(target["run_id"])
                    provenance = self._action_review_decision_provenance(action_id)
                    if not provenance:
                        continue
                    if (
                        provenance.get("review_id") != review_id
                        or provenance.get("run_id") != run_id
                    ):
                        raise ValueError(
                            "superseded review decision provenance is invalid"
                        )
                    decision = self._connection.execute(
                        "SELECT * FROM user_decisions WHERE decision_id = ?",
                        (provenance["decision_id"],),
                    ).fetchone()
                    if (
                        decision is None
                        or str(decision["scope"]) != "run"
                        or str(decision["run_id"]) != run_id
                        or str(decision["failure_key"])
                        != f"review:{review_id}:{run_id}"
                    ):
                        raise ValueError(
                            "superseded review decision provenance does not resolve"
                        )
                    if str(decision["status"]) == "open":
                        self._connection.execute(
                            """
                            UPDATE user_decisions
                            SET status = 'closed', resolution = ?, closed_at = ?,
                                updated_at = ?
                            WHERE decision_id = ? AND status = 'open'
                            """,
                            (
                                "Reviewer application superseded before completion.",
                                now,
                                now,
                                provenance["decision_id"],
                            ),
                        )
            self._connection.execute(
                """
                UPDATE actions
                SET status = 'cancelled', lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_id IN (
                  SELECT action_id FROM review_application_targets
                  WHERE review_id = ? AND status = 'pending'
                ) AND status IN ('pending', 'leased', 'running')
                """,
                (now, review_id),
            )
            self._connection.execute(
                """
                UPDATE review_application_targets
                SET status = 'superseded', error = ?, updated_at = ?
                WHERE review_id = ? AND status = 'pending'
                """,
                (reason, now, review_id),
            )
            self._connection.execute(
                """
                UPDATE review_applications
                SET status = 'superseded', updated_at = ?
                WHERE review_id = ? AND status = 'applying'
                """,
                (now, review_id),
            )
            self._connection.execute(
                "DELETE FROM review_findings WHERE review_id = ?",
                (review_id,),
            )
            updated = self._connection.execute(
                """
                UPDATE reviews SET status = 'review_superseded', updated_at = ?
                WHERE review_id = ? AND status = 'review_applying'
                """,
                (now, review_id),
            )
            if updated.rowcount != 1:
                raise ValueError("only an applying review can be superseded")

    def database_integrity_ok(self) -> bool:
        with self._lock:
            row = self._connection.execute("PRAGMA quick_check").fetchone()
        return row is not None and str(row[0]).lower() == "ok"

    def pending_review_reservations(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT reservations.*, actions.payload_json, actions.run_id,
                       actions.run_revision, actions.policy, actions.phase,
                       actions.action_type, actions.queue_owner,
                       actions.repo_relative_root, actions.task_id,
                       actions.next_action, actions.idempotency_key
                FROM review_reservations AS reservations
                JOIN actions ON actions.action_id = reservations.action_id
                WHERE reservations.status = 'reserved'
                  AND actions.status = 'pending'
                ORDER BY reservations.due_at, reservations.reservation_id
                """
            ).fetchall()
        return [self._decoded_row(row) for row in rows]

    def reviewer_launcher_needed(
        self,
        *,
        now: datetime | None = None,
        heartbeat_stale_seconds: int = DEFAULT_HEARTBEAT_STALE_SECONDS,
    ) -> bool:
        """Report whether a Reviewer child could lease or reclaim due work."""
        self._validate_heartbeat_stale_seconds(heartbeat_stale_seconds)
        current = now or self._now()
        if not isinstance(current, datetime):
            raise TypeError("now must be a datetime")
        current_text = self._time_text(current)
        heartbeat_cutoff = self._time_text(
            current - timedelta(seconds=heartbeat_stale_seconds)
        )
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1
                FROM review_reservations AS reservations
                JOIN actions ON actions.action_id = reservations.action_id
                LEFT JOIN workers AS owner ON owner.worker_id = actions.lease_owner
                WHERE reservations.status = 'reserved'
                  AND actions.action_type = 'run_reviewer'
                  AND actions.queue_owner = 'reviewer'
                  AND (actions.not_before = '' OR actions.not_before <= ?)
                  AND (
                    actions.status = 'pending'
                    OR (
                      actions.status IN ('leased', 'running')
                      AND actions.lease_expires_at <= ?
                      AND (
                        owner.worker_id IS NULL
                        OR owner.heartbeat_at < ?
                      )
                    )
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM user_decisions
                    WHERE status = 'open' AND scope = 'global'
                  )
                LIMIT 1
                """,
                (current_text, current_text, heartbeat_cutoff),
            ).fetchone()
        return row is not None

    def active_reviewer_lease_exists(
        self,
        *,
        now: datetime | None = None,
        heartbeat_stale_seconds: int = DEFAULT_HEARTBEAT_STALE_SECONDS,
    ) -> bool:
        """Return whether one live Reviewer already owns project-global work."""
        self._validate_heartbeat_stale_seconds(heartbeat_stale_seconds)
        current = now or self._now()
        if not isinstance(current, datetime):
            raise TypeError("now must be a datetime")
        current_text = self._time_text(current)
        heartbeat_cutoff = self._time_text(
            current - timedelta(seconds=heartbeat_stale_seconds)
        )
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1
                FROM actions
                JOIN workers AS owner ON owner.worker_id = actions.lease_owner
                WHERE actions.action_type = 'run_reviewer'
                  AND actions.queue_owner = 'reviewer'
                  AND actions.status IN ('leased', 'running')
                  AND actions.lease_expires_at > ?
                  AND owner.heartbeat_at >= ?
                LIMIT 1
                """,
                (current_text, heartbeat_cutoff),
            ).fetchone()
        return row is not None

    @staticmethod
    def _validate_lineage_positions(value: Mapping[str, int]) -> dict[str, int]:
        if not isinstance(value, Mapping) or not value:
            raise ValueError("lineage_positions must be a non-empty mapping")
        positions = dict(value)
        if not all(
            isinstance(key, str)
            and key
            and isinstance(position, int)
            and not isinstance(position, bool)
            and position > 0
            for key, position in positions.items()
        ):
            raise ValueError("lineage_positions contains invalid entries")
        return positions

    def lease_next_action(
        self,
        worker_id: str,
        *,
        lease_seconds: int,
        heartbeat_stale_seconds: int = DEFAULT_HEARTBEAT_STALE_SECONDS,
        allowed_action_types: set[str] | frozenset[str] | None = None,
        allowed_queue_owners: set[str] | frozenset[str] | None = None,
    ) -> ActionRecord | None:
        self._validate_lease_input(worker_id, lease_seconds)
        self._validate_heartbeat_stale_seconds(heartbeat_stale_seconds)
        if allowed_action_types is not None and not all(
            isinstance(item, str) and item for item in allowed_action_types
        ):
            raise ValueError("allowed_action_types must contain non-empty strings")
        queue_owners = (
            {ActionOwner.WORKER.value}
            if allowed_queue_owners is None
            else set(allowed_queue_owners)
        )
        if not queue_owners or not all(
            owner in {item.value for item in ActionOwner} for owner in queue_owners
        ):
            raise ValueError("allowed_queue_owners must contain supported owners")
        with self._immediate_transaction():
            now_value = self._now()
            now = self._time_text(now_value)
            if allowed_action_types is not None and not allowed_action_types:
                self._write_worker_heartbeat(worker_id, now)
                return None
            expires_at = self._time_text(now_value + timedelta(seconds=lease_seconds))
            heartbeat_cutoff = self._time_text(
                now_value - timedelta(seconds=heartbeat_stale_seconds)
            )
            action_type_clause = ""
            owner_placeholders = ", ".join("?" for _ in sorted(queue_owners))
            select_parameters: list[Any] = [now, heartbeat_cutoff, now]
            if allowed_action_types is not None:
                ordered_types = sorted(allowed_action_types)
                placeholders = ", ".join("?" for _ in ordered_types)
                action_type_clause = f"AND a.action_type IN ({placeholders})"
                select_parameters.extend(ordered_types)
            select_parameters.extend(sorted(queue_owners))
            row = self._connection.execute(
                f"""
                SELECT a.* FROM actions AS a
                LEFT JOIN runs AS r ON r.run_id = a.run_id
                LEFT JOIN workers AS owner ON owner.worker_id = a.lease_owner
                WHERE (
                  a.status = 'pending'
                   OR (
                     a.status IN ('leased', 'running')
                     AND a.lease_expires_at <= ?
                     AND (
                       owner.worker_id IS NULL
                       OR owner.heartbeat_at < ?
                     )
                   )
                )
                AND (a.not_before = '' OR a.not_before <= ?)
                AND a.action_type != 'restart_service'
                AND (
                  (a.queue_owner = 'worker'
                   AND r.revision = a.run_revision AND r.phase = a.phase)
                  OR (a.queue_owner IN ('reviewer', 'supervisor')
                      AND r.run_id IS NOT NULL
                      AND r.repo_relative_root = a.repo_relative_root)
                )
                AND (
                  a.idempotency_key NOT LIKE 'recovery:%'
                  OR (r.revision = a.run_revision AND r.phase = a.phase)
                  OR (a.queue_owner = 'reviewer' AND EXISTS (
                    SELECT 1 FROM reviews AS accepted_recovery_reviews
                    WHERE accepted_recovery_reviews.source_action_id = a.action_id
                      AND accepted_recovery_reviews.status IN ('review_applying', 'review_complete')
                      AND accepted_recovery_reviews.accepted_review_json != '{{}}'
                  ))
                )
                AND NOT EXISTS (
                  SELECT 1 FROM user_decisions AS decisions
                  WHERE decisions.status = 'open'
                    AND (
                      decisions.scope = 'global'
                      OR (
                        decisions.scope = 'run'
                        AND decisions.run_id = a.run_id
                        AND a.queue_owner != 'reviewer'
                      )
                    )
                )
                {action_type_clause}
                AND a.queue_owner IN ({owner_placeholders})
                ORDER BY
                  CASE
                    WHEN a.queue_owner = 'reviewer' AND EXISTS (
                      SELECT 1 FROM reviews AS resumable_reviews
                      JOIN review_applications AS resumable_applications
                        ON resumable_applications.review_id = resumable_reviews.review_id
                      WHERE resumable_reviews.source_action_id = a.action_id
                        AND resumable_reviews.status IN ('review_applying', 'review_complete')
                        AND resumable_reviews.accepted_review_json != '{{}}'
                        AND resumable_applications.status IN ('applying', 'completed')
                    ) THEN 0
                    WHEN a.queue_owner = 'reviewer' AND EXISTS (
                      SELECT 1 FROM reviews AS accepted_reviews
                      WHERE accepted_reviews.source_action_id = a.action_id
                        AND accepted_reviews.status IN ('review_applying', 'review_complete')
                        AND accepted_reviews.accepted_review_json != '{{}}'
                    ) THEN 1
                    ELSE 2
                  END ASC,
                  a.priority ASC, a.created_at ASC, a.action_id ASC
                LIMIT 1
                """,
                select_parameters,
            ).fetchone()
            if row is None:
                self._write_worker_heartbeat(worker_id, now)
                return None
            updated = self._connection.execute(
                f"""
                UPDATE actions
                SET status = 'leased', lease_owner = ?, lease_expires_at = ?,
                    lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ? AND action_type != 'restart_service' AND (
                  (
                    status = 'pending'
                    AND (not_before = '' OR not_before <= ?)
                    AND (
                      (queue_owner = 'worker' AND EXISTS (
                        SELECT 1 FROM runs
                        WHERE runs.run_id = actions.run_id
                          AND runs.revision = actions.run_revision
                          AND runs.phase = actions.phase
                      ))
                      OR (queue_owner IN ('reviewer', 'supervisor') AND EXISTS (
                        SELECT 1 FROM runs
                        WHERE runs.run_id = actions.run_id
                          AND runs.repo_relative_root = actions.repo_relative_root
                      ))
                    )
                  )
                  OR (
                    status IN ('leased', 'running')
                    AND lease_expires_at <= ?
                   AND EXISTS (
                      SELECT 1 WHERE
                        (actions.queue_owner = 'worker' AND EXISTS (
                           SELECT 1 FROM runs
                           WHERE runs.run_id = actions.run_id
                             AND runs.revision = actions.run_revision
                             AND runs.phase = actions.phase
                        ))
                        OR (actions.queue_owner IN ('reviewer', 'supervisor') AND EXISTS (
                           SELECT 1 FROM runs
                           WHERE runs.run_id = actions.run_id
                             AND runs.repo_relative_root = actions.repo_relative_root
                        ))
                    )
                    AND NOT EXISTS (
                      SELECT 1 FROM workers
                      WHERE workers.worker_id = actions.lease_owner
                        AND workers.heartbeat_at >= ?
                    )
                  )
                ) AND (
                  actions.idempotency_key NOT LIKE 'recovery:%'
                  OR EXISTS (
                    SELECT 1 FROM runs
                    WHERE runs.run_id = actions.run_id
                      AND runs.revision = actions.run_revision
                      AND runs.phase = actions.phase
                  )
                  OR (actions.queue_owner = 'reviewer' AND EXISTS (
                    SELECT 1 FROM reviews AS accepted_recovery_reviews
                    WHERE accepted_recovery_reviews.source_action_id = actions.action_id
                      AND accepted_recovery_reviews.status IN ('review_applying', 'review_complete')
                      AND accepted_recovery_reviews.accepted_review_json != '{{}}'
                  ))
                ) AND NOT EXISTS (
                  SELECT 1 FROM user_decisions AS decisions
                  WHERE decisions.status = 'open'
                    AND (
                      decisions.scope = 'global'
                      OR (
                        decisions.scope = 'run'
                        AND decisions.run_id = actions.run_id
                        AND actions.queue_owner != 'reviewer'
                      )
                    )
                ) AND queue_owner IN ({owner_placeholders})
                """,
                (
                    worker_id,
                    expires_at,
                    now,
                    now,
                    row["action_id"],
                    now,
                    now,
                    heartbeat_cutoff,
                    *sorted(queue_owners),
                ),
            )
            self._write_worker_heartbeat(worker_id, now)
            if updated.rowcount != 1:
                return None
            leased = self._connection.execute(
                "SELECT * FROM actions WHERE action_id = ?", (row["action_id"],)
            ).fetchone()
        return self._action_record(leased)

    def claim_pending_action(
        self,
        action_id: str,
        owner_id: str,
        *,
        lease_seconds: int,
        expected_queue_owner: ActionOwner = ActionOwner.SUPERVISOR,
    ) -> ActionRecord | None:
        """Claim one known pending Supervisor-owned action without scanning the queue."""
        self._required_text(action_id, "action_id")
        self._validate_lease_input(owner_id, lease_seconds)
        if not isinstance(expected_queue_owner, ActionOwner):
            raise TypeError("expected_queue_owner must be an ActionOwner")
        with self._immediate_transaction():
            now_value = self._now()
            now = self._time_text(now_value)
            expires_at = self._time_text(now_value + timedelta(seconds=lease_seconds))
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'leased', lease_owner = ?, lease_expires_at = ?,
                    lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ? AND status = 'pending'
                  AND queue_owner = ?
                  AND EXISTS (
                    SELECT 1 FROM runs
                    WHERE runs.run_id = actions.run_id
                      AND runs.repo_relative_root = actions.repo_relative_root
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM user_decisions AS decisions
                    WHERE decisions.status = 'open'
                      AND (
                        decisions.scope = 'global'
                        OR (
                          decisions.scope = 'run'
                          AND decisions.run_id = actions.run_id
                          AND actions.action_type != 'ask_user'
                        )
                      )
                  )
                """,
                (
                    owner_id,
                    expires_at,
                    now,
                    now,
                    action_id,
                    expected_queue_owner.value,
                ),
            )
            self._write_worker_heartbeat(owner_id, now)
            if updated.rowcount != 1:
                return None
            row = self._connection.execute(
                "SELECT * FROM actions WHERE action_id = ?", (action_id,)
            ).fetchone()
        return self._action_record(row)

    def claim_service_restart_action(
        self,
        action_id: str,
        owner_id: str,
        *,
        service_id: str,
        outage_id: str,
        lease_seconds: int,
    ) -> ActionRecord | None:
        """Claim one project service restart without impersonating a Worker."""
        self._required_text(action_id, "action_id")
        self._required_text(service_id, "service_id")
        self._required_text(outage_id, "outage_id")
        self._validate_lease_input(owner_id, lease_seconds)
        with self._immediate_transaction():
            now_value = self._now()
            now = self._time_text(now_value)
            expires_at = self._time_text(now_value + timedelta(seconds=lease_seconds))
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'leased', lease_owner = ?, lease_expires_at = ?,
                    lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ?
                  AND action_type = 'restart_service'
                  AND queue_owner = 'supervisor'
                  AND run_id = 'service-keeper'
                  AND repo_relative_root = '.'
                  AND json_extract(payload_json, '$.service_id') = ?
                  AND json_extract(payload_json, '$.outage_id') = ?
                  AND EXISTS (
                    SELECT 1 FROM services
                    WHERE services.service_id = ?
                      AND services.status != 'healthy'
                      AND json_extract(services.details_json, '$.outage_id') = ?
                  )
                  AND (not_before = '' OR not_before <= ?)
                  AND (
                    status = 'pending'
                    OR (
                      status IN ('leased', 'running')
                      AND lease_expires_at <= ?
                    )
                  )
                  AND NOT EXISTS (
                    SELECT 1
                    FROM actions AS active
                    WHERE active.action_id != actions.action_id
                      AND active.action_type = 'restart_service'
                      AND active.queue_owner = 'supervisor'
                      AND json_extract(active.payload_json, '$.service_id') = ?
                      AND active.status IN ('leased', 'running')
                      AND active.lease_expires_at > ?
                  )
                """,
                (
                    owner_id,
                    expires_at,
                    now,
                    now,
                    action_id,
                    service_id,
                    outage_id,
                    service_id,
                    outage_id,
                    now,
                    now,
                    service_id,
                    now,
                ),
            )
            if updated.rowcount != 1:
                self._connection.execute(
                    """
                    UPDATE actions
                    SET status = 'cancelled', lease_owner = '',
                        lease_expires_at = '', lease_heartbeat_at = '', updated_at = ?
                    WHERE action_id = ?
                      AND action_type = 'restart_service'
                      AND queue_owner = 'supervisor'
                      AND json_extract(payload_json, '$.service_id') = ?
                      AND json_extract(payload_json, '$.outage_id') = ?
                      AND (
                        status = 'pending'
                        OR (
                          status IN ('leased', 'running')
                          AND lease_expires_at <= ?
                        )
                      )
                      AND NOT EXISTS (
                        SELECT 1 FROM services
                        WHERE services.service_id = ?
                          AND services.status != 'healthy'
                          AND json_extract(services.details_json, '$.outage_id') = ?
                      )
                    """,
                    (
                        now,
                        action_id,
                        service_id,
                        outage_id,
                        now,
                        service_id,
                        outage_id,
                    ),
                )
                return None
            row = self._connection.execute(
                "SELECT * FROM actions WHERE action_id = ?", (action_id,)
            ).fetchone()
        return self._action_record(row)

    def cancel_pending_service_restarts(
        self, service_id: str, *, outage_id: str
    ) -> int:
        """Cancel pending restart work for one exact service outage."""
        self._required_text(service_id, "service_id")
        self._required_text(outage_id, "outage_id")
        with self._immediate_transaction():
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'cancelled', lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_type = 'restart_service'
                  AND queue_owner = 'supervisor'
                  AND json_extract(payload_json, '$.service_id') = ?
                  AND json_extract(payload_json, '$.outage_id') = ?
                  AND status = 'pending'
                """,
                (self._now_text(), service_id, outage_id),
            )
        return updated.rowcount

    def cancel_stale_service_restart(
        self,
        action_id: str,
        *,
        service_id: str,
        outage_id: str,
        current_outage_id: str,
    ) -> bool:
        """Cancel one expired action proven stale against current service state."""
        self._required_text(action_id, "action_id")
        self._required_text(service_id, "service_id")
        self._required_text(outage_id, "outage_id")
        self._required_text(current_outage_id, "current_outage_id")
        if outage_id == current_outage_id:
            return False
        with self._immediate_transaction():
            now = self._now_text()
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'cancelled', lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_id = ?
                  AND action_type = 'restart_service'
                  AND queue_owner = 'supervisor'
                  AND json_extract(payload_json, '$.service_id') = ?
                  AND json_extract(payload_json, '$.outage_id') = ?
                  AND (
                    status = 'pending'
                    OR (
                      status IN ('leased', 'running')
                      AND lease_expires_at <= ?
                    )
                  )
                  AND EXISTS (
                    SELECT 1 FROM services
                    WHERE services.service_id = ?
                      AND services.status != 'healthy'
                      AND json_extract(services.details_json, '$.outage_id') = ?
                  )
                """,
                (
                    now,
                    action_id,
                    service_id,
                    outage_id,
                    now,
                    service_id,
                    current_outage_id,
                ),
            )
        return updated.rowcount == 1

    def rearm_current_cancelled_service_restart(
        self,
        action_id: str,
        *,
        service_id: str,
        outage_id: str,
    ) -> bool:
        """Rearm one cancelled action only while its outage remains current."""
        self._required_text(action_id, "action_id")
        self._required_text(service_id, "service_id")
        self._required_text(outage_id, "outage_id")
        with self._immediate_transaction():
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'pending', lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_id = ?
                  AND status = 'cancelled'
                  AND action_type = 'restart_service'
                  AND queue_owner = 'supervisor'
                  AND json_extract(payload_json, '$.service_id') = ?
                  AND json_extract(payload_json, '$.outage_id') = ?
                  AND EXISTS (
                    SELECT 1 FROM services
                    WHERE services.service_id = ?
                      AND services.status != 'healthy'
                      AND json_extract(services.details_json, '$.outage_id') = ?
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM actions AS active
                    WHERE active.action_id != actions.action_id
                      AND active.action_type = 'restart_service'
                      AND active.queue_owner = 'supervisor'
                      AND json_extract(active.payload_json, '$.service_id') = ?
                      AND json_extract(active.payload_json, '$.outage_id') = ?
                      AND active.status IN ('pending', 'leased', 'running')
                  )
                """,
                (
                    self._now_text(),
                    action_id,
                    service_id,
                    outage_id,
                    service_id,
                    outage_id,
                    service_id,
                    outage_id,
                ),
            )
        return updated.rowcount == 1

    def rearm_retryable_service_restart(
        self,
        action_id: str,
        *,
        service_id: str,
        backoff_seconds: int,
    ) -> bool:
        """Re-arm one failed restart only when its latest attempt is retryable."""
        self._required_text(action_id, "action_id")
        self._required_text(service_id, "service_id")
        if (
            not isinstance(backoff_seconds, int)
            or isinstance(backoff_seconds, bool)
            or not 1 <= backoff_seconds <= 3600
        ):
            raise ValueError("backoff_seconds must be an int between 1 and 3600")
        with self._immediate_transaction():
            now_value = self._now()
            now = self._time_text(now_value)
            not_before = self._time_text(
                now_value + timedelta(seconds=backoff_seconds)
            )
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'pending', recovery_tier = recovery_tier + 1,
                    not_before = ?, lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_id = ?
                  AND status = 'failed'
                  AND action_type = 'restart_service'
                  AND queue_owner = 'supervisor'
                  AND run_id = 'service-keeper'
                  AND repo_relative_root = '.'
                  AND json_extract(payload_json, '$.service_id') = ?
                  AND (
                    SELECT result_class
                    FROM action_attempts
                    WHERE action_attempts.action_id = actions.action_id
                    ORDER BY action_attempts.rowid DESC
                    LIMIT 1
                  ) = 'retryable_failure'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM actions AS active
                    WHERE active.action_id != actions.action_id
                      AND active.action_type = 'restart_service'
                      AND active.queue_owner = 'supervisor'
                      AND json_extract(active.payload_json, '$.service_id') = ?
                      AND active.status IN ('pending', 'leased', 'running')
                  )
                """,
                (not_before, now, action_id, service_id, service_id),
            )
        return updated.rowcount == 1

    def update_pending_action(self, request: ActionRequest) -> ActionRecord:
        """Atomically replace metadata on one unclaimed, identity-stable action."""
        if not isinstance(request, ActionRequest):
            raise TypeError("request must be an ActionRequest")
        payload = request.payload_for_storage()
        self._validate_payload(payload)
        with self._immediate_transaction():
            existing = self._connection.execute(
                "SELECT * FROM actions WHERE action_id = ?", (request.action_id,)
            ).fetchone()
            if existing is None or existing["status"] != "pending":
                raise ValueError("action is not pending")
            identity = (
                str(existing["run_id"]),
                int(existing["run_revision"]),
                str(existing["policy"]),
                str(existing["phase"]),
                str(existing["action_type"]),
                str(existing["task_id"]),
                str(existing["repo_relative_root"]),
                str(existing["idempotency_key"]),
                str(existing["queue_owner"]),
            )
            incoming = (
                request.run_id,
                request.run_revision,
                request.policy,
                request.phase,
                request.action_type.value,
                request.task_id,
                request.repo_relative_root,
                request.idempotency_key,
                request.queue_owner.value,
            )
            if incoming != identity:
                raise ValueError("pending action identity cannot change")
            updated = self._connection.execute(
                """
                UPDATE actions
                SET next_action = ?, payload_json = ?, not_before = ?, updated_at = ?
                WHERE action_id = ? AND status = 'pending'
                """,
                (
                    request.next_action,
                    self._json(payload),
                    self._coerce_time(request.not_before) if request.not_before else "",
                    self._now_text(),
                    request.action_id,
                ),
            )
            if updated.rowcount != 1:
                raise ValueError("pending action changed during update")
            row = self._connection.execute(
                "SELECT * FROM actions WHERE action_id = ?", (request.action_id,)
            ).fetchone()
        return self._action_record(row)

    def renew_lease(
        self, action_id: str, worker_id: str, *, lease_seconds: int
    ) -> bool:
        self._validate_lease_input(worker_id, lease_seconds)
        with self._immediate_transaction():
            now_value = self._now()
            now = self._time_text(now_value)
            expires_at = self._time_text(now_value + timedelta(seconds=lease_seconds))
            self._write_worker_heartbeat(worker_id, now)
            updated = self._connection.execute(
                """
                UPDATE actions
                SET lease_expires_at = ?, lease_heartbeat_at = ?, updated_at = ?
                WHERE action_id = ? AND lease_owner = ?
                  AND status IN ('leased', 'running')
                  AND (
                    (queue_owner = 'worker'
                     OR NOT EXISTS (
                      SELECT 1 FROM user_decisions AS decisions
                      WHERE decisions.status = 'open'
                        AND decisions.scope = 'global'
                    ))
                  )
                  AND (
                    (action_type = 'restart_service'
                     AND queue_owner = 'supervisor'
                     AND run_id = 'service-keeper'
                     AND repo_relative_root = '.')
                    OR (queue_owner = 'worker' AND EXISTS (
                      SELECT 1 FROM runs
                      WHERE runs.run_id = actions.run_id
                        AND runs.revision = actions.run_revision
                        AND runs.phase = actions.phase
                    ))
                    OR (queue_owner IN ('reviewer', 'supervisor') AND EXISTS (
                      SELECT 1 FROM runs
                      WHERE runs.run_id = actions.run_id
                        AND runs.repo_relative_root = actions.repo_relative_root
                    ))
                  )
                """,
                (expires_at, now, now, action_id, worker_id),
            )
        return updated.rowcount == 1

    def touch_worker(self, worker_id: str) -> dict[str, Any]:
        """Upsert the current heartbeat for one long-running Worker process."""
        self._validate_worker_id(worker_id)
        with self._immediate_transaction():
            now = self._now_text()
            self._write_worker_heartbeat(worker_id, now)
            row = self._connection.execute(
                "SELECT * FROM workers WHERE worker_id = ?", (worker_id,)
            ).fetchone()
        return dict(row)

    def record_worker_heartbeat(self, worker_id: str) -> dict[str, Any]:
        """Compatibility wrapper for action-scoped Worker heartbeats."""
        return self.touch_worker(worker_id)

    def upsert_service_observation(
        self,
        *,
        service_id: str,
        status: str,
        endpoint: str = "",
        process_id: int | None = None,
        heartbeat_at: datetime | str | None = None,
        version: str = "",
        details: Mapping[str, Any] | None = None,
        cadence_seconds: int = 30,
    ) -> bool:
        """Project one service state, writing only changed or due observations."""
        self._validate_observation_fields(
            identifier=service_id,
            status=status,
            details=details,
            cadence_seconds=cadence_seconds,
        )
        if not isinstance(endpoint, str) or not isinstance(version, str):
            raise TypeError("endpoint and version must be strings")
        if process_id is not None and (
            not isinstance(process_id, int)
            or isinstance(process_id, bool)
            or process_id <= 0
        ):
            raise ValueError("process_id must be a positive int or None")
        incoming_details = dict(details or {})
        with self._immediate_transaction():
            now = self._now()
            now_text = self._time_text(now)
            existing = self._connection.execute(
                "SELECT * FROM services WHERE service_id = ?", (service_id,)
            ).fetchone()
            if status == "healthy":
                incoming_details.pop("outage_id", None)
            else:
                outage_id = ""
                if existing is not None and str(existing["status"]) != "healthy":
                    try:
                        existing_details = json.loads(str(existing["details_json"]))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        existing_details = {}
                    if isinstance(existing_details, Mapping):
                        outage_id = str(existing_details.get("outage_id") or "")
                incoming_details["outage_id"] = outage_id or f"outage-{uuid4().hex}"
            details_json = self._json(incoming_details)
            heartbeat_text = self._coerce_time(heartbeat_at) if heartbeat_at else ""
            if existing is not None and not self._observation_due(
                existing["updated_at"],
                now,
                cadence_seconds,
                changed=(
                    str(existing["status"]) != status
                    or str(existing["endpoint"]) != endpoint
                    or existing["process_id"] != process_id
                    or str(existing["heartbeat_at"]) != heartbeat_text
                    or str(existing["version"]) != version
                    or str(existing["details_json"]) != details_json
                ),
            ):
                return False
            self._connection.execute(
                """
                INSERT INTO services(
                  service_id, status, endpoint, process_id, heartbeat_at, version,
                  details_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(service_id) DO UPDATE SET
                  status = excluded.status,
                  endpoint = excluded.endpoint,
                  process_id = excluded.process_id,
                  heartbeat_at = excluded.heartbeat_at,
                  version = excluded.version,
                  details_json = excluded.details_json,
                  updated_at = excluded.updated_at
                """,
                (
                    service_id,
                    status,
                    endpoint,
                    process_id,
                    heartbeat_text,
                    version,
                    details_json,
                    now_text,
                    now_text,
                ),
            )
        return True

    def record_freshness_observation(
        self,
        *,
        target: str,
        status: str,
        summary: str,
        details: Mapping[str, Any] | None = None,
        cadence_seconds: int = 300,
    ) -> bool:
        """Append meaningful freshness history without recording every watch tick."""
        self._validate_observation_fields(
            identifier=target,
            status=status,
            details=details,
            cadence_seconds=cadence_seconds,
        )
        self._validate_summary(summary)
        details_json = self._json(dict(details or {}))
        with self._immediate_transaction():
            now = self._now()
            now_text = self._time_text(now)
            existing = self._connection.execute(
                """
                SELECT * FROM freshness_checks
                WHERE target = ?
                ORDER BY checked_at DESC, check_id DESC
                LIMIT 1
                """,
                (target,),
            ).fetchone()
            if existing is not None and not self._observation_due(
                existing["checked_at"],
                now,
                cadence_seconds,
                changed=(
                    str(existing["status"]) != status
                    or str(existing["summary"]) != summary
                    or str(existing["details_json"]) != details_json
                ),
            ):
                return False
            self._connection.execute(
                """
                INSERT INTO freshness_checks(
                  check_id, target, status, summary, details_json, checked_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"freshness-{uuid4().hex}",
                    target,
                    status,
                    summary,
                    details_json,
                    now_text,
                    now_text,
                ),
            )
        return True

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
        self._validate_checkpoint(result.checkpoint)
        artifacts = self._validate_artifact_paths(result.artifact_paths)
        artifact_json = self._json(artifacts)
        with self._immediate_transaction():
            now = self._time_text(self._now())
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
                "SELECT revision, phase, repo_relative_root FROM runs WHERE run_id = ?",
                (action["run_id"],),
            ).fetchone()
            if action["queue_owner"] == ActionOwner.WORKER.value and (
                current_run is None
                or int(current_run["revision"]) != int(action["run_revision"])
                or str(current_run["phase"]) != str(action["phase"])
            ):
                raise LeaseError(
                    f"action does not match current run revision and phase: {action_id}"
                )
            if action["queue_owner"] in {
                ActionOwner.REVIEWER.value,
                ActionOwner.SUPERVISOR.value,
            } and action["action_type"] != ActionType.RESTART_SERVICE.value and (
                current_run is None
                or str(current_run["repo_relative_root"])
                != str(action["repo_relative_root"])
            ):
                raise LeaseError(
                    f"action lacks authoritative run projection: {action_id}"
                )
            open_decision = self._connection.execute(
                """
                SELECT decision_id, scope FROM user_decisions
                WHERE status = 'open'
                  AND (
                    scope = 'global'
                    OR (scope = 'run' AND run_id = ?)
                  )
                LIMIT 1
                """,
                (action["run_id"],),
            ).fetchone()
            if open_decision is not None and (
                action["queue_owner"] == ActionOwner.WORKER.value
                or str(open_decision["scope"]) == "global"
            ):
                raise LeaseError(
                    f"open user decision blocks action completion: {action_id}"
                )
            attempt_id = f"attempt-{uuid4().hex}"
            started_at = (
                self._coerce_time(result.started_at) if result.started_at else now
            )
            finished_at = (
                self._coerce_time(result.finished_at) if result.finished_at else now
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
            for invocation in result.skill_invocations:
                skill_path, invocation_artifact = self._validate_skill_invocation_files(
                    invocation.skill_path,
                    invocation.artifact_path,
                    invocation.artifact_sha256,
                )
                self._connection.execute(
                    """
                    INSERT INTO skill_invocations(
                      invocation_id, action_id, attempt_id, skill_path,
                      artifact_path, artifact_sha256, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invocation.invocation_id,
                        action_id,
                        attempt_id,
                        skill_path,
                        invocation_artifact,
                        invocation.artifact_sha256,
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
        with self._lock:
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
        summary_json = self._json(summary)
        loop_lineage_id = str(projection.get("loop_lineage_id", ""))
        parent_run_id = str(projection.get("parent_run_id", ""))
        policy = str(projection.get("policy", ""))
        status = str(projection.get("status", ""))
        state_fingerprint = projection.get("state_fingerprint", "")
        if not isinstance(state_fingerprint, str):
            raise TypeError("state_fingerprint must be a string")
        repo_relative_root = validate_repo_relative_root(
            projection.get("repo_relative_root", ".")
        )
        with self._immediate_transaction():
            existing = self._connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing is None:
                self._connection.execute(
                    """
                    INSERT INTO runs(
                      run_id, loop_lineage_id, parent_run_id, policy, phase, status,
                      revision, repo_relative_root, state_fingerprint, summary_json, created_at,
                      updated_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        loop_lineage_id,
                        parent_run_id,
                        policy,
                        phase,
                        status,
                        revision,
                        repo_relative_root,
                        state_fingerprint,
                        summary_json,
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
                if revision == current_revision:
                    incoming_projection = (
                        loop_lineage_id,
                        parent_run_id,
                        policy,
                        phase,
                        status,
                        repo_relative_root,
                        state_fingerprint,
                        summary_json,
                    )
                    stored_projection = (
                        str(existing["loop_lineage_id"]),
                        str(existing["parent_run_id"]),
                        str(existing["policy"]),
                        str(existing["phase"]),
                        str(existing["status"]),
                        str(existing["repo_relative_root"]),
                        str(existing["state_fingerprint"]),
                        str(existing["summary_json"]),
                    )
                    fingerprint_backfill = (
                        not stored_projection[-2]
                        and bool(incoming_projection[-2])
                        and incoming_projection[:-2] == stored_projection[:-2]
                        and incoming_projection[-1] == stored_projection[-1]
                    )
                    root_backfill = (
                        str(existing["repo_relative_root"]) == "."
                        and repo_relative_root != "."
                        and incoming_projection[:5] == stored_projection[:5]
                        and incoming_projection[6:] == stored_projection[6:]
                    )
                    if (
                        incoming_projection != stored_projection
                        and not fingerprint_backfill
                        and not root_backfill
                    ):
                        raise ValueError(
                            "same-revision run projection conflict: "
                            "only last_seen_at may change"
                        )
                    self._connection.execute(
                        """
                        UPDATE runs SET state_fingerprint = ?, repo_relative_root = ?, last_seen_at = ?
                        WHERE run_id = ?
                        """,
                        (state_fingerprint, repo_relative_root, now, run_id),
                    )
                else:
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
                          phase = ?, status = ?, revision = ?, state_fingerprint = ?,
                          repo_relative_root = ?, summary_json = ?, updated_at = ?, last_seen_at = ?
                        WHERE run_id = ?
                        """,
                        (
                            loop_lineage_id,
                            parent_run_id,
                            policy,
                            phase,
                            status,
                            revision,
                            state_fingerprint,
                            repo_relative_root,
                            summary_json,
                            now,
                            now,
                            run_id,
                        ),
                    )
                    self._connection.execute(
                        """
                        UPDATE actions
                        SET status = 'cancelled', lease_owner = '',
                            lease_expires_at = '', lease_heartbeat_at = '',
                            updated_at = ?
                        WHERE run_id = ? AND run_revision < ?
                          AND (
                            (status = 'pending' AND queue_owner = 'worker')
                            OR (
                              status IN ('pending', 'leased', 'running')
                              AND idempotency_key LIKE 'recovery:%'
                              AND NOT EXISTS (
                                SELECT 1
                                FROM reviews
                                JOIN review_applications
                                  ON review_applications.review_id = reviews.review_id
                                JOIN review_application_targets
                                  ON review_application_targets.review_id = reviews.review_id
                                 AND review_application_targets.run_id = actions.run_id
                                WHERE reviews.source_action_id = actions.action_id
                                  AND review_applications.status = 'applying'
                                  AND review_application_targets.status = 'pending'
                                  AND review_application_targets.expected_revision + 1 = ?
                                  AND review_application_targets.target_phase = ?
                                  AND review_application_targets.expected_post_write_fingerprint = ?
                              )
                            )
                          )
                        """,
                        (now, run_id, revision, revision, phase, state_fingerprint),
                    )
            row = self._connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return self._decoded_row(row)

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
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

    def update_failure_resolution(
        self, failure_key: str, resolution: str
    ) -> dict[str, Any]:
        self._required_text(failure_key, "failure_key")
        if not isinstance(resolution, str) or not resolution:
            raise ValueError("resolution must be a non-empty string")
        now = self._now_text()
        with self._immediate_transaction():
            updated = self._connection.execute(
                """
                UPDATE failures SET resolution = ?, updated_at = ?
                WHERE failure_key = ?
                """,
                (resolution, now, failure_key),
            )
            if updated.rowcount != 1:
                raise KeyError(failure_key)
            row = self._connection.execute(
                "SELECT * FROM failures WHERE failure_key = ?", (failure_key,)
            ).fetchone()
        return self._decoded_row(row)

    def requeue_failed_action(self, action_id: str, *, recovery_tier: int) -> bool:
        self._required_text(action_id, "action_id")
        if not isinstance(recovery_tier, int) or isinstance(recovery_tier, bool):
            raise TypeError("recovery_tier must be an int")
        if recovery_tier < 0:
            raise ValueError("recovery_tier must be non-negative")
        now = self._now_text()
        with self._immediate_transaction():
            updated = self._connection.execute(
                """
                UPDATE actions
                SET status = 'pending', recovery_tier = ?, lease_owner = '',
                    lease_expires_at = '', lease_heartbeat_at = '', updated_at = ?
                WHERE action_id = ? AND status = 'failed'
                """,
                (recovery_tier, now, action_id),
            )
        return updated.rowcount == 1

    def current_time(self) -> datetime:
        return self._now()

    def format_time(self, value: datetime) -> str:
        return self._time_text(value)

    def open_user_decision(
        self,
        *,
        scope: str,
        summary: str,
        run_id: str = "",
        failure_key: str = "",
        required_decision: str = "",
        decision_id: str | None = None,
        source_action_id: str = "",
        source_action_owner: str = "",
        provenance_token: str = "",
    ) -> dict[str, Any]:
        self._validate_summary(summary)
        self._validate_summary(required_decision, field_name="required_decision")
        now = self._now_text()
        with self._immediate_transaction():
            source_review_id = self._validate_review_decision_source(
                scope=scope,
                run_id=run_id,
                source_action_id=source_action_id,
                source_action_owner=source_action_owner,
                provenance_token=provenance_token,
            )
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
                if source_review_id:
                    provenance = self._action_review_decision_provenance(
                        source_action_id
                    )
                    if provenance.get("decision_id") != resolved_id:
                        raise ValueError(
                            "review decision collides with an unproven open decision"
                        )
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
            if source_review_id:
                self._record_review_decision_provenance(
                    review_id=source_review_id,
                    action_id=source_action_id,
                    run_id=run_id,
                    decision_id=resolved_id,
                )
            row = self._connection.execute(
                "SELECT * FROM user_decisions WHERE decision_id = ?", (resolved_id,)
            ).fetchone()
        return self._decoded_row(row)

    def _validate_review_decision_source(
        self,
        *,
        scope: str,
        run_id: str,
        source_action_id: str,
        source_action_owner: str,
        provenance_token: str,
    ) -> str:
        values = (source_action_id, source_action_owner, provenance_token)
        if not any(values):
            return ""
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError("decision provenance requires action, owner, and token")
        if scope != "run":
            raise ValueError("Reviewer decision provenance requires run scope")
        row = self._connection.execute(
            """
            SELECT targets.review_id, targets.run_id, actions.payload_json,
                   actions.status, actions.lease_owner
            FROM review_application_targets AS targets
            JOIN review_applications AS applications
              ON applications.review_id = targets.review_id
            JOIN reviews ON reviews.review_id = targets.review_id
            JOIN actions ON actions.action_id = targets.action_id
            WHERE applications.decision = 'ask_user'
              AND applications.status = 'applying'
              AND reviews.decision = 'ask_user'
              AND reviews.status = 'review_applying'
              AND targets.action_id = ? AND targets.run_id = ?
              AND targets.status = 'pending'
              AND actions.status IN ('leased', 'running')
              AND actions.lease_owner = ?
              AND actions.action_type = 'ask_user'
              AND actions.queue_owner = 'supervisor'
            """,
            (source_action_id, run_id, source_action_owner),
        ).fetchone()
        if row is None:
            raise ValueError("decision provenance does not match a leased review target")
        payload = json.loads(str(row["payload_json"]))
        expected_token = (
            str(payload.get("decision_provenance_token") or "")
            if isinstance(payload, dict)
            else ""
        )
        if not expected_token or not hmac.compare_digest(
            expected_token, provenance_token
        ):
            raise ValueError("decision provenance token is invalid")
        return str(row["review_id"])

    def _action_review_decision_provenance(self, action_id: str) -> dict[str, str]:
        row = self._connection.execute(
            "SELECT payload_json FROM actions WHERE action_id = ?", (action_id,)
        ).fetchone()
        if row is None:
            return {}
        payload = json.loads(str(row["payload_json"]))
        value = payload.get("review_user_decision") if isinstance(payload, dict) else None
        if not isinstance(value, dict):
            return {}
        keys = {"decision_id", "review_id", "run_id"}
        if set(value) != keys or not all(
            isinstance(value[key], str) and value[key] for key in keys
        ):
            raise ValueError("review decision action provenance is invalid")
        return {key: str(value[key]) for key in keys}

    def _record_review_decision_provenance(
        self,
        *,
        review_id: str,
        action_id: str,
        run_id: str,
        decision_id: str,
    ) -> None:
        target = self._connection.execute(
            """
            SELECT targets.action_id
            FROM review_application_targets AS targets
            JOIN review_applications AS applications
              ON applications.review_id = targets.review_id
            WHERE targets.review_id = ? AND targets.run_id = ?
              AND targets.action_id = ? AND applications.decision = 'ask_user'
            """,
            (review_id, run_id, action_id),
        ).fetchone()
        if target is None:
            raise ValueError("decision provenance lacks a review application target")
        expected = {
            "decision_id": decision_id,
            "review_id": review_id,
            "run_id": run_id,
        }
        existing = self._action_review_decision_provenance(action_id)
        if existing and existing != expected:
            raise ValueError("review decision action provenance changed")
        action = self._connection.execute(
            "SELECT payload_json FROM actions WHERE action_id = ?", (action_id,)
        ).fetchone()
        if action is None:
            raise ValueError("decision provenance action is missing")
        payload = json.loads(str(action["payload_json"]))
        if not isinstance(payload, dict):
            raise ValueError("decision provenance action payload is invalid")
        payload["review_user_decision"] = expected
        self._validate_payload(payload)
        self._connection.execute(
            "UPDATE actions SET payload_json = ?, updated_at = ? WHERE action_id = ?",
            (self._json(payload), self._now_text(), action_id),
        )

    def close_user_decision(
        self,
        decision_id: str,
        *,
        resolution: str,
        expected_updated_at: str | None = None,
    ) -> dict[str, Any] | None:
        self._validate_summary(resolution, field_name="resolution")
        now = self._now_text()
        with self._immediate_transaction():
            if expected_updated_at is None:
                updated = self._connection.execute(
                    """
                UPDATE user_decisions SET status = 'closed', resolution = ?,
                  closed_at = ?, updated_at = ?
                WHERE decision_id = ? AND status = 'open'
                    """,
                    (resolution, now, now, decision_id),
                )
            else:
                updated = self._connection.execute(
                    """
                    UPDATE user_decisions SET status = 'closed', resolution = ?,
                      closed_at = ?, updated_at = ?
                    WHERE decision_id = ? AND status = 'open' AND updated_at = ?
                    """,
                    (resolution, now, now, decision_id, expected_updated_at),
                )
            if updated.rowcount != 1:
                if expected_updated_at is not None:
                    return None
                raise KeyError(decision_id)
            row = self._connection.execute(
                "SELECT * FROM user_decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
        return self._decoded_row(row)

    def close_reviewer_scope_incident_decisions(
        self,
        *,
        review_id: str,
        expected_run_ids: Sequence[str],
        resolution: str,
    ) -> list[dict[str, Any]]:
        """Close only a reviewed, explicitly enumerated Reviewer decision incident."""
        self._required_text(review_id, "review_id")
        self._validate_summary(resolution, field_name="resolution")
        run_ids = tuple(
            sorted(
                {
                    self._required_text(value, "expected_run_id")
                    for value in expected_run_ids
                }
            )
        )
        if not run_ids:
            raise ValueError("expected_run_ids must not be empty")
        now = self._now_text()
        with self._immediate_transaction():
            review = self._connection.execute(
                """
                SELECT reviews.decision, applications.decision AS application_decision
                FROM reviews
                JOIN review_applications AS applications
                  ON applications.review_id = reviews.review_id
                WHERE reviews.review_id = ?
                """,
                (review_id,),
            ).fetchone()
            if (
                review is None
                or str(review["decision"]) != "ask_user"
                or str(review["application_decision"]) != "ask_user"
            ):
                raise ValueError("scope incident must identify an ask_user review")
            targets = self._connection.execute(
                """
                SELECT targets.run_id, targets.action_id, actions.payload_json
                FROM review_application_targets AS targets
                JOIN actions ON actions.action_id = targets.action_id
                WHERE targets.review_id = ?
                  AND actions.action_type = 'ask_user'
                  AND actions.queue_owner = 'supervisor'
                ORDER BY targets.run_id
                """,
                (review_id,),
            ).fetchall()
            if {str(row["run_id"]) for row in targets} != set(run_ids):
                raise ValueError("scope incident decisions do not match expected set")
            if not targets:
                raise ValueError("scope incident decisions were not found")
            decision_ids: list[str] = []
            for target in targets:
                payload = json.loads(str(target["payload_json"]))
                token = (
                    str(payload.get("decision_provenance_token") or "")
                    if isinstance(payload, dict)
                    else ""
                )
                if not token:
                    raise ValueError(
                        "scope incident action lacks explicit provenance token"
                    )
                provenance = self._action_review_decision_provenance(
                    str(target["action_id"])
                )
                if (
                    provenance.get("review_id") != review_id
                    or provenance.get("run_id") != str(target["run_id"])
                    or not provenance.get("decision_id")
                ):
                    raise ValueError("scope incident decision provenance is invalid")
                decision_ids.append(provenance["decision_id"])
            placeholders = ", ".join("?" for _ in decision_ids)
            rows = self._connection.execute(
                f"""
                SELECT * FROM user_decisions
                WHERE decision_id IN ({placeholders})
                ORDER BY decision_id
                """,
                tuple(decision_ids),
            ).fetchall()
            if {
                (str(row["decision_id"]), str(row["run_id"])) for row in rows
            } != set(zip(decision_ids, run_ids, strict=True)):
                raise ValueError("scope incident decision provenance does not resolve")
            self._connection.execute(
                f"""
                UPDATE user_decisions
                SET status = 'closed', resolution = ?, closed_at = ?, updated_at = ?
                WHERE status = 'open' AND decision_id IN ({placeholders})
                """,
                (resolution, now, now, *decision_ids),
            )
            closed = self._connection.execute(
                f"""
                SELECT * FROM user_decisions
                WHERE decision_id IN ({placeholders})
                ORDER BY decision_id
                """,
                tuple(decision_ids),
            ).fetchall()
        return [self._decoded_row(row) for row in closed]

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
        accepted_review: Mapping[str, Any] | None = None,
        source_action_id: str = "",
        idempotent_findings: bool = False,
        created_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        self._validate_summary(summary)
        evidence = self._validate_artifact_paths(
            evidence_refs, field_name="evidence_refs"
        )
        accepted = dict(accepted_review or {})
        if accepted:
            self._validate_payload(accepted)
        if not isinstance(source_action_id, str):
            raise TypeError("source_action_id must be a string")
        if not isinstance(idempotent_findings, bool):
            raise TypeError("idempotent_findings must be a bool")
        timestamp = self._coerce_time(created_at)
        with self._immediate_transaction():
            if source_action_id:
                source = self._connection.execute(
                    "SELECT action_type FROM actions WHERE action_id = ?",
                    (source_action_id,),
                ).fetchone()
                if source is None or str(source["action_type"]) != "run_reviewer":
                    raise ValueError("source_action_id must identify a Reviewer action")
            self._connection.execute(
                """
                INSERT INTO reviews(
                  review_id, trigger, status, decision, summary, evidence_json,
                  accepted_review_json, source_action_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET status = excluded.status,
                  decision = excluded.decision, summary = excluded.summary,
                  evidence_json = excluded.evidence_json,
                  accepted_review_json = CASE
                    WHEN excluded.accepted_review_json = '{}' THEN reviews.accepted_review_json
                    ELSE excluded.accepted_review_json
                  END,
                  source_action_id = CASE
                    WHEN excluded.source_action_id = '' THEN reviews.source_action_id
                    ELSE excluded.source_action_id
                  END,
                  updated_at = excluded.updated_at
                """,
                (
                    review_id,
                    trigger,
                    status,
                    decision,
                    summary,
                    self._json(evidence),
                    self._json(accepted),
                    source_action_id,
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
                severity = str(finding.get("severity") or "")
                finding_evidence = list(finding.get("evidence_refs") or [])
                closure_evidence = list(finding.get("closure_evidence_refs") or [])
                affected_runs = list(finding.get("affected_run_ids") or [])
                existing = self._connection.execute(
                    "SELECT * FROM review_findings WHERE finding_key = ?",
                    (finding_key,),
                ).fetchone()
                if (
                    idempotent_findings
                    and existing is not None
                    and str(existing["review_id"]) == review_id
                ):
                    expected = (
                        finding_id,
                        finding_status,
                        severity,
                        finding_summary,
                        self._json(finding_evidence),
                        self._json(closure_evidence),
                        self._json(affected_runs),
                        str(finding.get("remediation_action_id", "")),
                    )
                    actual = tuple(
                        existing[column]
                        for column in (
                            "finding_id",
                            "status",
                            "severity",
                            "summary",
                            "evidence_json",
                            "closure_evidence_json",
                            "affected_runs_json",
                            "remediation_action_id",
                        )
                    )
                    if actual != expected:
                        raise ValueError("published review finding identity changed")
                    continue
                if existing is None and finding_status != "open" and trigger != "migration":
                    raise ValueError("new findings must enter lifecycle as open")
                if existing is not None:
                    if str(existing["finding_id"]) != finding_id:
                        raise ValueError("finding_key must retain stable identity")
                    previous_status = str(existing["status"])
                    allowed = {
                        "open": {"open", "closed", "accepted_risk"},
                        "closed": {"closed"},
                        "accepted_risk": {"accepted_risk"},
                    }
                    if finding_status not in allowed.get(previous_status, set()):
                        raise ValueError("finding lifecycle transition is not allowed")
                    if finding_status == "closed":
                        prior_refs = set(json.loads(str(existing["evidence_json"])))
                        prior_refs.update(
                            json.loads(str(existing["closure_evidence_json"]))
                        )
                        if not set(closure_evidence) - prior_refs:
                            raise ValueError(
                                "closed finding requires fresh closure evidence"
                            )
                self._connection.execute(
                    """
                    INSERT INTO review_findings(
                      finding_id, review_id, finding_key, status, severity, summary,
                      evidence_json, closure_evidence_json, affected_runs_json,
                      remediation_action_id, first_seen_at, last_seen_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(finding_key) DO UPDATE SET
                      review_id = excluded.review_id, status = excluded.status,
                      severity = excluded.severity, summary = excluded.summary,
                      evidence_json = excluded.evidence_json,
                      closure_evidence_json = excluded.closure_evidence_json,
                      affected_runs_json = excluded.affected_runs_json,
                      remediation_action_id = excluded.remediation_action_id,
                      occurrence_count = review_findings.occurrence_count + 1,
                      last_seen_at = excluded.last_seen_at, updated_at = excluded.updated_at
                    """,
                    (
                        finding_id,
                        review_id,
                        finding_key,
                        finding_status,
                        severity,
                        finding_summary,
                        self._json(finding_evidence),
                        self._json(closure_evidence),
                        self._json(affected_runs),
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

    def resumable_review_for_action(self, source_action_id: str) -> dict[str, Any] | None:
        """Return a complete accepted review associated with an unfinished source action."""
        self._required_text(source_action_id, "source_action_id")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT reviews.* FROM reviews
                JOIN actions ON actions.action_id = reviews.source_action_id
                WHERE reviews.source_action_id = ?
                  AND reviews.status IN ('review_applying', 'review_complete')
                  AND reviews.accepted_review_json != '{}'
                  AND actions.status IN ('pending', 'leased', 'running')
                ORDER BY reviews.created_at, reviews.review_id
                """,
                (source_action_id,),
            ).fetchall()
        if len(rows) > 1:
            raise RuntimeError("Reviewer action has multiple accepted reviews")
        return self._decoded_row(rows[0]) if rows else None

    def has_blocked_review_migration(self) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM reviews WHERE status = 'review_migration_blocked' LIMIT 1"
            ).fetchone()
        return row is not None

    def resolve_blocked_review_migration(
        self,
        review_id: str,
        *,
        reason: str,
        retry_source_action: bool = False,
    ) -> dict[str, str]:
        """Supersede an unapplied migrated review and optionally retry its source."""
        self._required_text(review_id, "review_id")
        self._validate_summary(reason, field_name="review migration resolution")
        now = self._now_text()
        retried_action_id = ""
        with self._immediate_transaction():
            review = self._connection.execute(
                "SELECT * FROM reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
            if review is None:
                raise KeyError(review_id)
            if str(review["status"]) != "review_migration_blocked":
                raise ValueError("only a blocked review migration can be resolved")
            source_action_id = str(review["source_action_id"] or "")
            source_action = (
                self._connection.execute(
                    "SELECT * FROM actions WHERE action_id = ?", (source_action_id,)
                ).fetchone()
                if source_action_id
                else None
            )

            self._connection.execute(
                """
                UPDATE actions
                SET status = 'cancelled', lease_owner = '', lease_expires_at = '',
                    lease_heartbeat_at = '', updated_at = ?
                WHERE action_id IN (
                  SELECT action_id FROM review_application_targets
                  WHERE review_id = ? AND status = 'pending'
                ) AND status IN ('pending', 'leased', 'running')
                """,
                (now, review_id),
            )
            self._connection.execute(
                """
                UPDATE review_application_targets
                SET status = 'superseded', error = ?, updated_at = ?
                WHERE review_id = ? AND status = 'pending'
                """,
                (reason, now, review_id),
            )
            self._connection.execute(
                """
                UPDATE review_applications
                SET status = 'superseded', updated_at = ?
                WHERE review_id = ? AND status = 'applying'
                """,
                (now, review_id),
            )
            self._connection.execute(
                "DELETE FROM review_findings WHERE review_id = ?", (review_id,)
            )
            self._connection.execute(
                """
                UPDATE reviews
                SET status = 'review_superseded', summary = ?, updated_at = ?
                WHERE review_id = ? AND status = 'review_migration_blocked'
                """,
                (f"Operator superseded blocked migration: {reason}", now, review_id),
            )
            if source_action is not None:
                self._connection.execute(
                    """
                    UPDATE actions
                    SET status = 'cancelled', lease_owner = '', lease_expires_at = '',
                        lease_heartbeat_at = '', updated_at = ?
                    WHERE action_id = ? AND status IN ('pending', 'leased', 'running')
                    """,
                    (now, source_action_id),
                )
                self._connection.execute(
                    """
                    UPDATE review_reservations
                    SET status = 'released', updated_at = ?
                    WHERE action_id = ? AND status = 'reserved'
                    """,
                    (now, source_action_id),
                )

            if retry_source_action:
                if source_action is None:
                    raise ValueError("blocked review has no source action to retry")
                try:
                    source_payload = json.loads(str(source_action["payload_json"] or "{}"))
                except json.JSONDecodeError as exc:
                    raise ValueError("blocked review source payload is invalid") from exc
                if (
                    not isinstance(source_payload, dict)
                    or source_payload.get("recovery_stage") != "reviewer"
                ):
                    raise ValueError("blocked review is not a recovery escalation")
                retried_action_id = str(source_payload.get("source_action_id") or "")
                retry_action = self._connection.execute(
                    "SELECT * FROM actions WHERE action_id = ?",
                    (retried_action_id,),
                ).fetchone()
                if (
                    retry_action is None
                    or str(retry_action["status"]) != "failed"
                    or str(retry_action["run_id"]) != str(source_action["run_id"])
                ):
                    raise ValueError("recovery source action is not retryable")
                self._connection.execute(
                    """
                    UPDATE actions
                    SET status = 'pending', lease_owner = '', lease_expires_at = '',
                        lease_heartbeat_at = '', not_before = '', updated_at = ?
                    WHERE action_id = ? AND status = 'failed'
                    """,
                    (now, retried_action_id),
                )

        return {
            "review_id": review_id,
            "source_action_id": source_action_id,
            "retried_action_id": retried_action_id,
            "status": "review_superseded",
        }

    def set_review_status(self, review_id: str, status: str) -> None:
        self._required_text(review_id, "review_id")
        self._required_text(status, "status")
        with self._immediate_transaction():
            updated = self._connection.execute(
                "UPDATE reviews SET status = ?, updated_at = ? WHERE review_id = ?",
                (status, self._now_text(), review_id),
            )
            if updated.rowcount != 1:
                raise KeyError(review_id)

    def record_skill_snapshot(
        self,
        snapshot: Mapping[str, Any],
        *,
        snapshot_id: str = "",
        created_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(snapshot, Mapping):
            raise TypeError("snapshot must be a mapping")
        self._validate_payload(snapshot)
        inventory = snapshot.get("inventory", [])
        confirmed_usage = snapshot.get("confirmed_usage", [])
        if not isinstance(inventory, (list, tuple)) or not isinstance(
            confirmed_usage, (list, tuple)
        ):
            raise TypeError("skill snapshot collections must be lists or tuples")
        timestamp = self._coerce_time(created_at)
        identifier = snapshot_id or (
            "skill-snapshot-"
            + hashlib.sha256(self._json(snapshot).encode("utf-8")).hexdigest()[:24]
        )
        snapshot_json = self._json(snapshot)
        expected = (len(inventory), len(confirmed_usage), snapshot_json)
        with self._immediate_transaction():
            self._connection.execute(
                """
                INSERT INTO skill_snapshots(
                  snapshot_id, total_skills, used_skills, snapshot_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO NOTHING
                """,
                (
                    identifier,
                    expected[0],
                    expected[1],
                    snapshot_json,
                    timestamp,
                ),
            )
            row = self._connection.execute(
                "SELECT * FROM skill_snapshots WHERE snapshot_id = ?", (identifier,)
            ).fetchone()
            actual = (
                int(row["total_skills"]),
                int(row["used_skills"]),
                str(row["snapshot_json"]),
            )
            if actual != expected:
                raise ValueError("skill snapshot identity changed")
        return self._decoded_row(row)

    def record_skill_invocation(
        self,
        *,
        invocation_id: str,
        action_id: str,
        attempt_id: str,
        skill_path: str,
        artifact_path: str,
        artifact_sha256: str,
    ) -> dict[str, Any]:
        """Record Supervisor-validated skill provenance for one completed attempt."""
        self._required_text(invocation_id, "invocation_id")
        self._required_text(action_id, "action_id")
        self._required_text(attempt_id, "attempt_id")
        validated_skill, validated_artifact = self._validate_skill_invocation_files(
            skill_path,
            artifact_path,
            artifact_sha256,
        )
        now = self._now_text()
        with self._immediate_transaction():
            attempt = self._connection.execute(
                """
                SELECT attempts.*, actions.action_id AS owning_action_id
                FROM action_attempts AS attempts
                JOIN actions ON actions.action_id = attempts.action_id
                WHERE attempts.attempt_id = ?
                """,
                (attempt_id,),
            ).fetchone()
            if (
                attempt is None
                or str(attempt["owning_action_id"]) != action_id
                or str(attempt["result_class"]) != ActionResultClass.SUCCESS.value
                or validated_artifact not in json.loads(str(attempt["artifact_json"]))
            ):
                raise ValueError("skill invocation is not tied to trusted action evidence")
            self._connection.execute(
                """
                INSERT INTO skill_invocations(
                  invocation_id, action_id, attempt_id, skill_path,
                  artifact_path, artifact_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(invocation_id) DO NOTHING
                """,
                (
                    invocation_id,
                    action_id,
                    attempt_id,
                    validated_skill,
                    validated_artifact,
                    artifact_sha256,
                    now,
                ),
            )
            row = self._connection.execute(
                "SELECT * FROM skill_invocations WHERE invocation_id = ?",
                (invocation_id,),
            ).fetchone()
            if (
                str(row["action_id"]) != action_id
                or str(row["attempt_id"]) != attempt_id
                or str(row["skill_path"]) != validated_skill
                or str(row["artifact_sha256"]) != artifact_sha256
            ):
                raise ValueError("skill invocation identity changed")
        return dict(row)

    def _validate_skill_invocation_files(
        self,
        skill_path: str,
        artifact_path: str,
        artifact_sha256: str,
    ) -> tuple[str, str]:
        validated_skill = self._validate_artifact_paths(
            (skill_path,), field_name="skill_path"
        )[0]
        validated_artifact = self._validate_artifact_paths(
            (artifact_path,), field_name="artifact_path"
        )[0]
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_sha256):
            raise ValueError("artifact_sha256 must be a lowercase SHA-256 reference")
        skill = self.project_root / validated_skill
        if not skill.is_file() or skill.is_symlink():
            raise ValueError("skill invocation skill must be an owned regular file")
        artifact = self.project_root / validated_artifact
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError("skill invocation artifact must be an owned regular file")
        actual_hash = f"sha256:{hashlib.sha256(artifact.read_bytes()).hexdigest()}"
        if actual_hash != artifact_sha256:
            raise ValueError("skill invocation artifact hash does not match")
        return validated_skill, validated_artifact

    def list_page(
        self,
        table: str,
        *,
        resource: str,
        page_size: int = 20,
        cursor: str | None = None,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            return self._list_page_locked(
                table,
                resource=resource,
                page_size=page_size,
                cursor=cursor,
                filters=filters,
            )

    def _list_page_locked(
        self,
        table: str,
        *,
        resource: str,
        page_size: int,
        cursor: str | None,
        filters: Mapping[str, Any] | None,
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
        snapshot_sequence = 0
        snapshot_total = 0
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
            snapshot_sequence = self._cursor_non_negative_int(
                payload.get("snapshot_sequence"), "snapshot_sequence"
            )
            snapshot_total = self._cursor_non_negative_int(
                payload.get("snapshot_total"), "snapshot_total"
            )
        else:
            snapshot_sequence = int(
                self._connection.execute(
                    "SELECT COALESCE(MAX(sequence_id), 0) FROM row_sequences"
                ).fetchone()[0]
            )
            snapshot_where, snapshot_parameters = self._filter_clause(
                normalized_filters
            )
            self._append_membership_condition(
                snapshot_where,
                snapshot_parameters,
                table,
                primary_key,
                snapshot_sequence,
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
        self._append_membership_condition(
            where, parameters, table, primary_key, snapshot_sequence
        )
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
        self._append_membership_condition(
            base_where,
            base_parameters,
            table,
            primary_key,
            snapshot_sequence,
        )
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
        if cursor:
            total = snapshot_total
        else:
            total = int(
                self._connection.execute(
                    f"SELECT COUNT(*) FROM {table}{base_where_sql}", base_parameters
                ).fetchone()[0]
            )
            snapshot_total = total
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
                snapshot_sequence,
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
                    snapshot_sequence,
                    snapshot_total,
                    "next",
                    (str(last[timestamp_column]), str(last[primary_key])),
                )
            if self._boundary_exists(
                table,
                timestamp_column,
                primary_key,
                normalized_filters,
                snapshot,
                snapshot_sequence,
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
                    snapshot_sequence,
                    snapshot_total,
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
            eligible_attempts = """
                action_attempts.created_at < ?
                AND NOT EXISTS (
                  SELECT 1
                  FROM review_application_targets AS retained_targets
                  JOIN review_applications AS retained_applications
                    ON retained_applications.review_id = retained_targets.review_id
                  WHERE retained_targets.action_id = action_attempts.action_id
                    AND retained_applications.status NOT IN ('completed', 'superseded')
                )
                AND NOT EXISTS (
                  SELECT 1 FROM reviews AS retained_source_reviews
                  WHERE retained_source_reviews.source_action_id = action_attempts.action_id
                    AND retained_source_reviews.status = 'review_applying'
                )
            """
            specs = (("transitions", "to_phase", "transitions"),)
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
            attempt_groups = self._connection.execute(
                f"""
                SELECT substr(action_attempts.created_at, 1, 10) AS aggregate_day,
                       action_attempts.result_class AS aggregate_key,
                       COUNT(*) AS aggregate_count
                FROM action_attempts WHERE {eligible_attempts}
                GROUP BY aggregate_day, aggregate_key
                """,
                (cutoff,),
            ).fetchall()
            for group in attempt_groups:
                self._upsert_aggregate(
                    str(group["aggregate_day"]),
                    "action_attempts",
                    str(group["aggregate_key"]),
                    int(group["aggregate_count"]),
                    now,
                )
            invocation_groups = self._connection.execute(
                f"""
                SELECT substr(skill_invocations.created_at, 1, 10) AS aggregate_day,
                       skill_invocations.skill_path AS aggregate_key,
                       COUNT(*) AS aggregate_count
                FROM skill_invocations
                JOIN action_attempts
                  ON action_attempts.attempt_id = skill_invocations.attempt_id
                WHERE {eligible_attempts}
                GROUP BY aggregate_day, aggregate_key
                """,
                (cutoff,),
            ).fetchall()
            for group in invocation_groups:
                self._upsert_aggregate(
                    str(group["aggregate_day"]),
                    "skill_invocations",
                    str(group["aggregate_key"]),
                    int(group["aggregate_count"]),
                    now,
                )
            eligible_reviews = """
                reviews.created_at < ?
                AND reviews.updated_at < ?
                AND reviews.status != 'review_applying'
                AND NOT EXISTS (
                  SELECT 1 FROM review_applications AS incomplete_applications
                  WHERE incomplete_applications.review_id = reviews.review_id
                    AND incomplete_applications.status NOT IN ('completed', 'superseded')
                )
                AND NOT EXISTS (
                  SELECT 1 FROM actions AS nonterminal_review_sources
                  WHERE nonterminal_review_sources.action_id = reviews.source_action_id
                    AND nonterminal_review_sources.status
                      NOT IN ('completed', 'failed', 'cancelled')
                )
                AND NOT EXISTS (
                  SELECT 1 FROM review_findings AS active_findings
                  WHERE active_findings.review_id = reviews.review_id
                    AND active_findings.status NOT IN ('closed', 'accepted_risk')
                )
                AND NOT EXISTS (
                  SELECT 1 FROM review_findings AS recent_findings
                  WHERE recent_findings.review_id = reviews.review_id
                    AND (
                      recent_findings.last_seen_at >= ?
                      OR recent_findings.updated_at >= ?
                    )
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
                (cutoff, cutoff, cutoff, cutoff),
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
                SELECT substr(findings.last_seen_at, 1, 10) AS aggregate_day,
                       findings.status AS aggregate_key,
                       SUM(findings.occurrence_count) AS aggregate_count
                FROM review_findings AS findings
                JOIN reviews ON reviews.review_id = findings.review_id
                WHERE findings.last_seen_at < ? AND findings.updated_at < ?
                  AND {eligible_reviews}
                GROUP BY aggregate_day, aggregate_key
                """,
                (cutoff, cutoff, cutoff, cutoff, cutoff, cutoff),
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
                f"""
                SELECT substr(action_attempts.created_at, 1, 10) AS aggregate_day,
                       action_attempts.failure_key AS aggregate_key,
                       COUNT(*) AS aggregate_count
                FROM action_attempts
                WHERE {eligible_attempts} AND action_attempts.failure_key != ''
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
            eligible_freshness = """
                freshness_checks.checked_at < ?
                AND EXISTS (
                  SELECT 1 FROM freshness_checks AS newer_freshness
                  WHERE newer_freshness.target = freshness_checks.target
                    AND (
                      newer_freshness.checked_at > freshness_checks.checked_at
                      OR (
                        newer_freshness.checked_at = freshness_checks.checked_at
                        AND newer_freshness.check_id > freshness_checks.check_id
                      )
                    )
                )
            """
            freshness_groups = self._connection.execute(
                f"""
                SELECT substr(freshness_checks.checked_at, 1, 10) AS aggregate_day,
                       freshness_checks.target || ':' || freshness_checks.status
                         AS aggregate_key,
                       COUNT(*) AS aggregate_count
                FROM freshness_checks
                WHERE {eligible_freshness}
                GROUP BY aggregate_day, aggregate_key
                """,
                (cutoff,),
            ).fetchall()
            for group in freshness_groups:
                self._upsert_aggregate(
                    str(group["aggregate_day"]),
                    "freshness_checks",
                    str(group["aggregate_key"]),
                    int(group["aggregate_count"]),
                    now,
                )
            finding_delete = self._connection.execute(
                f"""
                DELETE FROM review_findings
                WHERE last_seen_at < ? AND updated_at < ? AND review_id IN (
                  SELECT reviews.review_id FROM reviews WHERE {eligible_reviews}
                )
                """,
                (cutoff, cutoff, cutoff, cutoff, cutoff, cutoff),
            )
            deleted["review_findings"] = finding_delete.rowcount
            review_delete = self._connection.execute(
                f"DELETE FROM reviews WHERE {eligible_reviews}",
                (cutoff, cutoff, cutoff, cutoff),
            )
            deleted["reviews"] = review_delete.rowcount
            self._connection.execute(
                f"""
                DELETE FROM skill_invocations WHERE attempt_id IN (
                  SELECT action_attempts.attempt_id FROM action_attempts
                  WHERE {eligible_attempts}
                )
                """,
                (cutoff,),
            )
            attempt_delete = self._connection.execute(
                f"DELETE FROM action_attempts WHERE {eligible_attempts}",
                (cutoff,),
            )
            deleted["action_attempts"] = attempt_delete.rowcount
            transition_delete = self._connection.execute(
                "DELETE FROM transitions WHERE created_at < ?", (cutoff,)
            )
            deleted["transitions"] = transition_delete.rowcount
            freshness_delete = self._connection.execute(
                f"DELETE FROM freshness_checks WHERE {eligible_freshness}",
                (cutoff,),
            )
            if freshness_delete.rowcount:
                deleted["freshness_checks"] = freshness_delete.rowcount
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
        snapshot_sequence: int,
        snapshot_total: int,
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
            "snapshot_sequence": snapshot_sequence,
            "snapshot_total": snapshot_total,
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
        snapshot_sequence: int,
        operator: str,
        timestamp: str,
        key: str,
    ) -> bool:
        where, parameters = self._filter_clause(filters)
        self._append_membership_condition(
            where, parameters, table, primary_key, snapshot_sequence
        )
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
    def _append_membership_condition(
        clauses: list[str],
        parameters: list[Any],
        table: str,
        primary_key: str,
        snapshot_sequence: int,
    ) -> None:
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM row_sequences AS membership "
            "WHERE membership.table_name = ? "
            f"AND membership.row_key = CAST({table}.{primary_key} AS TEXT) "
            "AND membership.sequence_id <= ?"
            ")"
        )
        parameters.extend((table, snapshot_sequence))

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
    def _cursor_non_negative_int(value: object, name: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CursorError(f"cursor {name} is invalid")
        return value

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
            canonical_identity=str(row["canonical_identity"]),
            run_id=str(row["run_id"]),
            run_revision=int(row["run_revision"]),
            repo_relative_root=str(row["repo_relative_root"]),
            policy=str(row["policy"]),
            phase=str(row["phase"]),
            action_type=str(row["action_type"]),
            queue_owner=str(row["queue_owner"]),
            not_before=str(row["not_before"]),
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
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("timestamp must be valid ISO-8601") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("timestamp string must include a timezone offset")
            return self._time_text(parsed)
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
                    is_stream_key = (
                        "stdout" in normalized_key or "stderr" in normalized_key
                    )
                    is_explicit_stream_reference = normalized_key.endswith(
                        ("_path", "_ref")
                    )
                    if normalized_key in INLINE_LOG_BODY_KEYS or (
                        is_stream_key and not is_explicit_stream_reference
                    ):
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
                    elif is_stream_key and normalized_key.endswith("_ref"):
                        self._validate_artifact_paths(
                            (item,), field_name=f"payload {key}"
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

    def _validate_checkpoint(self, value: object) -> None:
        if not isinstance(value, str):
            raise TypeError("checkpoint must be a string")
        if not value:
            return
        if len(value) > MAX_CHECKPOINT_CHARS:
            raise ValueError(f"checkpoint exceeds {MAX_CHECKPOINT_CHARS} characters")
        if len(value.encode("utf-8")) > MAX_CHECKPOINT_BYTES:
            raise ValueError(f"checkpoint exceeds {MAX_CHECKPOINT_BYTES} encoded bytes")
        if (
            "\n" in value
            or "\r" in value
            or "\x00" in value
            or "\\" in value
            or "://" in value
            or SAFE_CHECKPOINT_PATTERN.fullmatch(value) is None
        ):
            raise ValueError("checkpoint must be a safe single-line reference")
        if "/" in value:
            self._validate_artifact_paths((value,), field_name="checkpoint")

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

    @staticmethod
    def _canonical_action_identity(
        *,
        run_id: str,
        run_revision: int,
        policy: str,
        phase: str,
        action_type: str,
        task_id: str,
        repo_relative_root: str,
        queue_owner: str,
    ) -> str:
        canonical = SupervisorStore._json(
            {
                "action_type": action_type,
                "phase": phase,
                "policy": policy,
                "run_id": run_id,
                "run_revision": run_revision,
                "repo_relative_root": repo_relative_root,
                "queue_owner": queue_owner,
                "task_id": task_id,
            }
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(canonical).hexdigest()}"

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

    @staticmethod
    def _validate_observation_fields(
        *,
        identifier: object,
        status: object,
        details: Mapping[str, Any] | None,
        cadence_seconds: object,
    ) -> None:
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("observation identifier must be a non-empty string")
        if not isinstance(status, str) or not status:
            raise ValueError("observation status must be a non-empty string")
        if details is not None and not isinstance(details, Mapping):
            raise TypeError("observation details must be a mapping")
        if (
            not isinstance(cadence_seconds, int)
            or isinstance(cadence_seconds, bool)
            or cadence_seconds <= 0
        ):
            raise ValueError("observation cadence_seconds must be a positive int")

    @staticmethod
    def _observation_due(
        observed_at: object,
        now: datetime,
        cadence_seconds: int,
        *,
        changed: bool,
    ) -> bool:
        if changed:
            return True
        try:
            previous = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
        except ValueError:
            return True
        if previous.tzinfo is None or previous.utcoffset() is None:
            return True
        return previous.astimezone(timezone.utc) + timedelta(seconds=cadence_seconds) <= now

    def _write_worker_heartbeat(self, worker_id: str, timestamp: str) -> None:
        self._connection.execute(
            """
            INSERT INTO workers(worker_id, heartbeat_at, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(worker_id) DO UPDATE SET
              heartbeat_at = excluded.heartbeat_at, updated_at = excluded.updated_at
            WHERE excluded.heartbeat_at > workers.heartbeat_at
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
            "action_idempotency_aliases",
            "row_sequences",
            "review_reservations",
            "review_cadence",
            "review_safety_gates",
            "review_applications",
            "review_application_targets",
            "skill_invocations",
        }:
            raise ValueError(f"unsupported table: {table}")
