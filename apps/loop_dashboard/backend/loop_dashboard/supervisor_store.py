from __future__ import annotations

from collections import OrderedDict
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
from threading import RLock
import time
from typing import Any, Mapping

from .pagination import (
    CursorCodec,
    CursorError,
    CursorPayload,
    Page,
    _cursor_payload,
    _validate_collection_cursor,
    paginate_items,
    validate_page_size,
)
from .redaction import is_sensitive_key, redact_text


EXPECTED_SCHEMA_VERSION = 14
DEFAULT_SQLITE_SNAPSHOT_TTL_SECONDS = 300
DEFAULT_MAX_SQLITE_SNAPSHOTS = 64


@dataclass(frozen=True)
class TablePageSpec:
    primary_key: str
    timestamp: str
    filters: frozenset[str]


TABLE_PAGE_SPECS: dict[str, TablePageSpec] = {
    "services": TablePageSpec("service_id", "created_at", frozenset({"status"})),
    "freshness_checks": TablePageSpec(
        "check_id", "created_at", frozenset({"target", "status"})
    ),
    "actions": TablePageSpec(
        "action_id",
        "created_at",
        frozenset({"run_id", "status", "action_type", "queue_owner"}),
    ),
    "action_attempts": TablePageSpec(
        "attempt_id",
        "created_at",
        frozenset({"action_id", "result_class", "error_class", "recovery_tier"}),
    ),
    "transitions": TablePageSpec(
        "transition_id",
        "created_at",
        frozenset({"run_id", "to_phase", "action_id"}),
    ),
    "reviews": TablePageSpec(
        "review_id",
        "created_at",
        frozenset({"status", "decision", "trigger"}),
    ),
    "review_findings": TablePageSpec(
        "finding_id",
        "created_at",
        frozenset({"review_id", "status", "severity"}),
    ),
    "user_decisions": TablePageSpec(
        "decision_id",
        "created_at",
        frozenset({"scope", "run_id", "status"}),
    ),
    "skill_snapshots": TablePageSpec(
        "snapshot_id", "created_at", frozenset()
    ),
}

REQUIRED_TABLE_COLUMNS: dict[str, frozenset[str]] = {
    "runs": frozenset(
        {
            "run_id", "loop_lineage_id", "parent_run_id", "policy", "phase",
            "status", "revision", "repo_relative_root", "state_fingerprint",
            "summary_json", "created_at", "updated_at", "last_seen_at",
        }
    ),
    "actions": frozenset(
        {
            "action_id", "idempotency_key", "canonical_identity", "run_id",
            "run_revision", "repo_relative_root", "policy", "phase",
            "action_type", "queue_owner", "not_before", "task_id",
            "next_action", "status", "priority", "recovery_tier",
            "lease_owner", "lease_expires_at", "lease_heartbeat_at",
            "payload_json", "artifact_json", "created_at", "updated_at",
        }
    ),
    "action_attempts": frozenset(
        {
            "attempt_id", "action_id", "worker_id", "result_class", "summary",
            "failure_key", "error_class", "artifact_json", "checkpoint",
            "recovery_tier", "started_at", "finished_at", "created_at",
        }
    ),
    "transitions": frozenset(
        {
            "transition_id", "run_id", "from_revision", "to_revision",
            "from_phase", "to_phase", "action_id", "summary", "artifact_json",
            "created_at",
        }
    ),
    "reviews": frozenset(
        {
            "review_id", "trigger", "status", "decision", "summary",
            "evidence_json", "accepted_review_json", "source_action_id",
            "created_at", "updated_at",
        }
    ),
    "review_findings": frozenset(
        {
            "finding_id", "review_id", "finding_key", "status", "severity",
            "summary", "evidence_json", "closure_evidence_json",
            "affected_runs_json", "remediation_action_id", "occurrence_count",
            "first_seen_at", "last_seen_at", "created_at", "updated_at",
        }
    ),
    "user_decisions": frozenset(
        {
            "decision_id", "scope", "run_id", "failure_key", "status",
            "summary", "required_decision", "resolution", "created_at",
            "updated_at", "closed_at",
        }
    ),
    "services": frozenset(
        {
            "service_id", "status", "endpoint", "process_id", "heartbeat_at",
            "version", "details_json", "created_at", "updated_at",
        }
    ),
    "freshness_checks": frozenset(
        {
            "check_id", "target", "status", "summary", "details_json",
            "checked_at", "created_at",
        }
    ),
    "skill_snapshots": frozenset(
        {"snapshot_id", "total_skills", "used_skills", "snapshot_json", "created_at"}
    ),
    "workers": frozenset(
        {"worker_id", "heartbeat_at", "created_at", "updated_at"}
    ),
    "row_sequences": frozenset({"sequence_id", "table_name", "row_key"}),
    "store_metadata": frozenset({"key", "value"}),
}


class SupervisorStoreError(RuntimeError):
    status = "unavailable"


class SupervisorStoreUnavailable(SupervisorStoreError):
    status = "unavailable"


class SupervisorSchemaIncompatible(SupervisorStoreError):
    status = "schema_incompatible"


@dataclass
class SQLitePageSession:
    snapshot_id: str
    connection: sqlite3.Connection
    table: str
    endpoint: str
    filter_fingerprint: str
    filters: dict[str, Any]
    predicates: tuple[str, ...]
    snapshot: tuple[str, str]
    snapshot_sequence: int
    total: int
    expires_at: float
    lock: RLock = field(default_factory=RLock)
    closed: bool = False

    def close(self) -> None:
        with self.lock:
            if self.closed:
                return
            try:
                self.connection.rollback()
            finally:
                self.connection.close()
                self.closed = True


class SQLiteSnapshotRegistry:
    """Owns read transactions for one single-process Dashboard namespace."""

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_SQLITE_SNAPSHOT_TTL_SECONDS,
        max_sessions: int = DEFAULT_MAX_SQLITE_SNAPSHOTS,
    ) -> None:
        if ttl_seconds <= 0 or max_sessions <= 0:
            raise ValueError("SQLite snapshot bounds must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        self._sessions: OrderedDict[str, SQLitePageSession] = OrderedDict()
        self._lock = RLock()
        self._owners = 0

    def acquire_owner(self) -> None:
        with self._lock:
            self._owners += 1

    def release_owner(self) -> None:
        sessions: list[SQLitePageSession] = []
        with self._lock:
            if self._owners > 0:
                self._owners -= 1
            if self._owners == 0:
                sessions = list(self._sessions.values())
                self._sessions.clear()
        for session in sessions:
            session.close()

    def deadline(self) -> float:
        return time.monotonic() + self._ttl_seconds

    def add(self, session: SQLitePageSession) -> SQLitePageSession:
        with self._lock:
            self._prune_locked(time.monotonic())
            self._sessions[session.snapshot_id] = session
            self._sessions.move_to_end(session.snapshot_id)
            while len(self._sessions) > self._max_sessions:
                _snapshot_id, evicted = self._sessions.popitem(last=False)
                evicted.close()
        return session

    def get(
        self,
        payload: CursorPayload,
        *,
        table: str,
        endpoint: str,
        filter_fingerprint: str,
    ) -> SQLitePageSession:
        with self._lock:
            self._prune_locked(time.monotonic())
            return self._validated_session(
                payload,
                table=table,
                endpoint=endpoint,
                filter_fingerprint=filter_fingerprint,
            )

    @contextmanager
    def lease(
        self,
        payload: CursorPayload,
        *,
        table: str,
        endpoint: str,
        filter_fingerprint: str,
    ):
        with self._lock:
            self._prune_locked(time.monotonic())
            session = self._validated_session(
                payload,
                table=table,
                endpoint=endpoint,
                filter_fingerprint=filter_fingerprint,
            )
            session.lock.acquire()
        try:
            if session.closed:
                raise CursorError("cursor snapshot is unavailable or expired")
            yield session
        finally:
            session.lock.release()

    def discard(self, snapshot_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(snapshot_id, None)
        if session is not None:
            session.close()

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.close()

    def reap_expired(self) -> None:
        with self._lock:
            self._prune_locked(time.monotonic())

    def _prune_locked(self, now: float) -> None:
        expired = [
            snapshot_id
            for snapshot_id, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for snapshot_id in expired:
            session = self._sessions.pop(snapshot_id)
            session.close()

    def _validated_session(
        self,
        payload: CursorPayload,
        *,
        table: str,
        endpoint: str,
        filter_fingerprint: str,
    ) -> SQLitePageSession:
        session = self._sessions.get(payload.snapshot_id)
        if session is None:
            raise CursorError("cursor snapshot is unavailable or expired")
        if (
            session.table != table
            or session.endpoint != endpoint
            or session.filter_fingerprint != filter_fingerprint
        ):
            raise CursorError("cursor snapshot collection mismatch")
        if (
            session.snapshot
            != (payload.snapshot_timestamp, payload.snapshot_primary_key)
            or session.snapshot_sequence != payload.snapshot_sequence
            or session.total != payload.snapshot_total
        ):
            raise CursorError("cursor snapshot metadata mismatch")
        self._sessions.move_to_end(payload.snapshot_id)
        return session


_SQLITE_SNAPSHOT_REGISTRIES: OrderedDict[
    tuple[str, str, float, int], SQLiteSnapshotRegistry
] = OrderedDict()
_SQLITE_SNAPSHOT_REGISTRIES_LOCK = RLock()
_SQLITE_SNAPSHOT_REGISTRY_LIMIT = 64


class SupervisorDashboardStore:
    """Read-only Dashboard projection over the canonical Supervisor database."""

    def __init__(
        self,
        project_root: Path | str,
        *,
        cursor_codec: CursorCodec | None = None,
        snapshot_ttl_seconds: float = DEFAULT_SQLITE_SNAPSHOT_TTL_SECONDS,
        max_snapshot_sessions: int = DEFAULT_MAX_SQLITE_SNAPSHOTS,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.db_path = self.project_root / ".codex" / "supervisor" / "supervisor.db"
        self._cursor_codec = cursor_codec or CursorCodec(
            secrets.token_bytes(32)
        )
        registry_key = (
            str(self.db_path),
            self._cursor_codec.namespace,
            snapshot_ttl_seconds,
            max_snapshot_sessions,
        )
        with _SQLITE_SNAPSHOT_REGISTRIES_LOCK:
            self._sqlite_snapshots = _SQLITE_SNAPSHOT_REGISTRIES.get(registry_key)
            if self._sqlite_snapshots is None:
                self._sqlite_snapshots = SQLiteSnapshotRegistry(
                    ttl_seconds=snapshot_ttl_seconds,
                    max_sessions=max_snapshot_sessions,
                )
                _SQLITE_SNAPSHOT_REGISTRIES[registry_key] = self._sqlite_snapshots
            self._sqlite_snapshots.acquire_owner()
            _SQLITE_SNAPSHOT_REGISTRIES.move_to_end(registry_key)
            while (
                len(_SQLITE_SNAPSHOT_REGISTRIES)
                > _SQLITE_SNAPSHOT_REGISTRY_LIMIT
            ):
                _key, evicted = _SQLITE_SNAPSHOT_REGISTRIES.popitem(last=False)
                evicted.close_all()
        self.closed = False

    def reap_expired(self) -> None:
        self._sqlite_snapshots.reap_expired()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self._sqlite_snapshots.release_owner()

    def summary(self) -> dict[str, Any]:
        try:
            with closing(self._connect()) as connection:
                counts = {
                    name: int(
                        connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                    )
                    for name in TABLE_PAGE_SPECS
                }
                counts["runs"] = int(
                    connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                )
                counts["workers"] = int(
                    connection.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
                )
            return {
                "status": "available",
                "schema_version": EXPECTED_SCHEMA_VERSION,
                "counts": counts,
                "diagnostics": [],
            }
        except SupervisorStoreError as exc:
            return self._diagnostic_payload(exc)
        except sqlite3.Error as exc:
            return self._diagnostic_payload(
                SupervisorStoreUnavailable(f"could not query Supervisor database: {exc}")
            )

    def page(
        self,
        table: str,
        *,
        endpoint: str,
        page_size: int,
        cursor: str | None,
        filters: Mapping[str, Any] | None = None,
        _predicates: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        validate_page_size(page_size)
        if table not in TABLE_PAGE_SPECS:
            raise ValueError(f"unsupported Supervisor collection: {table}")
        normalized_filters = dict(filters or {})
        self._validate_filters(table, normalized_filters)
        cursor_filters = {
            "filters": normalized_filters,
            "predicates": list(_predicates),
        }
        fingerprint = self._cursor_codec.filter_fingerprint(cursor_filters)
        payload: CursorPayload | None = None
        if cursor:
            payload = self._cursor_codec.decode(cursor)
            _validate_collection_cursor(
                payload,
                endpoint=endpoint,
                page_size=page_size,
                fingerprint=fingerprint,
            )
            if payload.snapshot_sequence is None:
                raise CursorError("cursor snapshot sequence is invalid")
        try:
            if payload is not None:
                with self._sqlite_snapshots.lease(
                    payload,
                    table=table,
                    endpoint=endpoint,
                    filter_fingerprint=fingerprint,
                ) as session:
                    return self._page_from_sqlite_session(
                        session,
                        payload=payload,
                        page_size=page_size,
                    ).to_dict()
            return self._first_sqlite_page(
                table,
                endpoint=endpoint,
                page_size=page_size,
                filters=normalized_filters,
                predicates=_predicates,
                filter_fingerprint=fingerprint,
            ).to_dict()
        except SupervisorStoreError as exc:
            return self._error_payload(exc)
        except sqlite3.Error as exc:
            return self._error_payload(
                SupervisorStoreUnavailable(
                    f"could not query Supervisor collection {table}: {exc}"
                ),
            )

    def recovery_page(
        self,
        *,
        endpoint: str,
        page_size: int,
        cursor: str | None,
        filters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.page(
            "action_attempts",
            endpoint=endpoint,
            page_size=page_size,
            cursor=cursor,
            filters=filters,
            _predicates=("recovery_tier > 0",),
        )

    def skill_rows(
        self,
        snapshot_id: str,
        *,
        page_size: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        validate_page_size(page_size)
        endpoint = f"supervisor-skills:{snapshot_id}:rows"
        filters = {"snapshot_id": snapshot_id}
        if cursor:
            return paginate_items(
                [],
                endpoint=endpoint,
                page_size=page_size,
                cursor=cursor,
                filters=filters,
                timestamp_key="created_at",
                primary_key="skill_id",
                codec=self._cursor_codec,
            ).to_dict()
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT snapshot_json, created_at FROM skill_snapshots "
                    "WHERE snapshot_id = ?",
                    (snapshot_id,),
                ).fetchone()
                if row is None:
                    items: list[dict[str, Any]] = []
                    created_at = ""
                else:
                    snapshot = self._load_json(str(row["snapshot_json"]), {})
                    inventory = snapshot.get("inventory", [])
                    created_at = str(row["created_at"])
                    items = [
                        self._skill_row(item, index, created_at)
                        for index, item in enumerate(inventory)
                    ] if isinstance(inventory, list) else []
                page = paginate_items(
                    items,
                    endpoint=endpoint,
                    page_size=page_size,
                    cursor=cursor,
                    filters=filters,
                    timestamp_key="created_at",
                    primary_key="skill_id",
                    codec=self._cursor_codec,
                )
            return page.to_dict()
        except SupervisorStoreError as exc:
            return self._error_payload(exc)
        except sqlite3.Error as exc:
            return self._error_payload(
                SupervisorStoreUnavailable(f"could not query skill rows: {exc}"),
            )

    def attempt_log_path(
        self,
        run_id: str,
        attempt_id: str,
        stream: str,
    ) -> Path | None:
        if stream not in {"stdout", "stderr"}:
            raise ValueError("stream must be stdout or stderr")
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    """
                    SELECT attempts.artifact_json
                    FROM action_attempts AS attempts
                    JOIN actions ON actions.action_id = attempts.action_id
                    WHERE attempts.attempt_id = ? AND actions.run_id = ?
                    """,
                    (attempt_id, run_id),
                ).fetchone()
                if row is None:
                    return None
                artifacts = self._load_json(str(row["artifact_json"]), [])
                if not isinstance(artifacts, list):
                    return None
                matches = [
                    value
                    for value in artifacts
                    if isinstance(value, str) and value.endswith(f".{stream}.log")
                ]
                if len(matches) != 1:
                    return None
                candidate = Path(matches[0])
                if candidate.is_absolute():
                    return candidate
                return self.project_root / candidate
        except (SupervisorStoreError, sqlite3.Error):
            return None

    def attempt_log_references(self, run_id: str) -> list[dict[str, Any]]:
        try:
            with closing(self._connect()) as connection:
                rows = connection.execute(
                    """
                    SELECT attempts.attempt_id, attempts.artifact_json,
                           attempts.created_at
                    FROM action_attempts AS attempts
                    JOIN actions ON actions.action_id = attempts.action_id
                    WHERE actions.run_id = ?
                    ORDER BY attempts.created_at, attempts.attempt_id
                    """,
                    (run_id,),
                ).fetchall()
            references: list[dict[str, Any]] = []
            for row in rows:
                artifacts = self._load_json(str(row["artifact_json"]), [])
                if not isinstance(artifacts, list):
                    continue
                for stream in ("stdout", "stderr"):
                    matches = [
                        value
                        for value in artifacts
                        if isinstance(value, str)
                        and value.endswith(f".{stream}.log")
                    ]
                    if len(matches) != 1:
                        continue
                    path = Path(matches[0])
                    references.append(
                        {
                            "attempt_id": str(row["attempt_id"]),
                            "stream": stream,
                            "path": path if path.is_absolute() else self.project_root / path,
                            "created_at": str(row["created_at"]),
                        }
                    )
            return references
        except (SupervisorStoreError, sqlite3.Error):
            return []

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.is_file():
            raise SupervisorStoreUnavailable("Supervisor database is unavailable")
        try:
            connection = sqlite3.connect(
                f"{self.db_path.as_uri()}?mode=ro",
                uri=True,
                timeout=5,
                isolation_level=None,
                check_same_thread=False,
            )
        except sqlite3.Error as exc:
            raise SupervisorStoreUnavailable(
                f"could not open Supervisor database read-only: {exc}"
            ) from exc
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA query_only=ON")
            if int(connection.execute("PRAGMA query_only").fetchone()[0]) != 1:
                raise SupervisorStoreUnavailable("SQLite query_only could not be enabled")
            self._validate_schema(connection)
        except BaseException:
            connection.close()
            raise
        return connection

    def _validate_schema(self, connection: sqlite3.Connection) -> None:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version != EXPECTED_SCHEMA_VERSION:
            raise SupervisorSchemaIncompatible(
                "Supervisor schema version mismatch: "
                f"expected {EXPECTED_SCHEMA_VERSION}, found {version}"
            )
        for table, expected in REQUIRED_TABLE_COLUMNS.items():
            columns = {
                str(row["name"])
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if not expected <= columns:
                missing = ", ".join(sorted(expected - columns))
                raise SupervisorSchemaIncompatible(
                    f"Supervisor table {table} is missing required columns: {missing}"
                )
        trigger_sql = {
            str(row["name"]): " ".join(str(row["sql"] or "").lower().split())
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type = 'trigger'"
            ).fetchall()
        }
        for table, spec in TABLE_PAGE_SPECS.items():
            trigger = f"row_sequence_{table}_insert"
            sql = trigger_sql.get(trigger)
            if sql is None:
                raise SupervisorSchemaIncompatible(
                    f"Supervisor membership trigger is unavailable: {trigger}"
                )
            expected_sql = " ".join(
                (
                    f"create trigger row_sequence_{table}_insert",
                    f"after insert on {table}",
                    "begin insert into row_sequences(table_name, row_key)",
                    f"values ('{table}', cast(new.{spec.primary_key} as text)); end",
                )
            )
            if sql != expected_sql:
                raise SupervisorSchemaIncompatible(
                    f"Supervisor membership trigger contract is invalid: {trigger}"
                )
            missing_membership = connection.execute(
                f"""
                SELECT 1
                FROM {table} AS source
                LEFT JOIN row_sequences AS membership
                  ON membership.table_name = ?
                 AND membership.row_key = CAST(source.{spec.primary_key} AS TEXT)
                WHERE membership.sequence_id IS NULL
                LIMIT 1
                """,
                (table,),
            ).fetchone()
            if missing_membership is not None:
                raise SupervisorSchemaIncompatible(
                    f"Supervisor membership coverage is incomplete: {table}"
                )
        secret = connection.execute(
            "SELECT value FROM store_metadata WHERE key = 'cursor_secret'"
        ).fetchone()
        if secret is None or not str(secret["value"]):
            raise SupervisorSchemaIncompatible(
                "Supervisor cursor metadata is unavailable"
            )

    def _first_sqlite_page(
        self,
        table: str,
        *,
        endpoint: str,
        page_size: int,
        filters: dict[str, Any],
        predicates: tuple[str, ...],
        filter_fingerprint: str,
    ) -> Page[dict[str, Any]]:
        connection = self._connect()
        registered = False
        try:
            connection.execute("BEGIN")
            spec = TABLE_PAGE_SPECS[table]
            snapshot_sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(sequence_id), 0) FROM row_sequences"
                ).fetchone()[0]
            )
            where, parameters = self._filter_clause(filters)
            where.extend(predicates)
            self._append_membership(
                where,
                parameters,
                table,
                spec.primary_key,
                snapshot_sequence,
            )
            where_sql = f" WHERE {' AND '.join(where)}" if where else ""
            snapshot_row = connection.execute(
                f"SELECT {spec.timestamp}, {spec.primary_key} FROM {table}"
                f"{where_sql} ORDER BY {spec.timestamp} DESC, "
                f"{spec.primary_key} DESC LIMIT 1",
                parameters,
            ).fetchone()
            if snapshot_row is None:
                connection.rollback()
                connection.close()
                return Page([], None, None, page_size, 0, False)
            snapshot = (
                str(snapshot_row[spec.timestamp]),
                str(snapshot_row[spec.primary_key]),
            )
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table}{where_sql}", parameters
                ).fetchone()[0]
            )
            session = SQLitePageSession(
                snapshot_id=secrets.token_urlsafe(18),
                connection=connection,
                table=table,
                endpoint=endpoint,
                filter_fingerprint=filter_fingerprint,
                filters=dict(filters),
                predicates=predicates,
                snapshot=snapshot,
                snapshot_sequence=snapshot_sequence,
                total=total,
                expires_at=self._sqlite_snapshots.deadline(),
            )
            self._sqlite_snapshots.add(session)
            registered = True
            page = self._page_from_sqlite_session(
                session,
                payload=None,
                page_size=page_size,
            )
            if page.next_cursor is None and page.previous_cursor is None:
                self._sqlite_snapshots.discard(session.snapshot_id)
            return page
        except BaseException:
            if not registered:
                try:
                    connection.rollback()
                finally:
                    connection.close()
            raise

    def _page_from_sqlite_session(
        self,
        session: SQLitePageSession,
        *,
        payload: CursorPayload | None,
        page_size: int,
    ) -> Page[dict[str, Any]]:
        spec = TABLE_PAGE_SPECS[session.table]
        direction = payload.direction if payload is not None else "next"
        boundary = (
            (payload.timestamp, payload.primary_key)
            if payload is not None
            else None
        )
        where, parameters = self._filter_clause(session.filters)
        where.extend(session.predicates)
        self._append_membership(
            where,
            parameters,
            session.table,
            spec.primary_key,
            session.snapshot_sequence,
        )
        self._append_position(
            where,
            parameters,
            spec.timestamp,
            spec.primary_key,
            "<=",
            session.snapshot,
        )
        if boundary is not None:
            self._append_position(
                where,
                parameters,
                spec.timestamp,
                spec.primary_key,
                "<" if direction == "next" else ">",
                boundary,
            )
        order = "DESC" if direction == "next" else "ASC"
        rows = session.connection.execute(
            f"SELECT * FROM {session.table} WHERE {' AND '.join(where)} "
            f"ORDER BY {spec.timestamp} {order}, {spec.primary_key} {order} "
            "LIMIT ?",
            (*parameters, page_size + 1),
        ).fetchall()
        selected = list(rows[:page_size])
        if direction == "previous":
            selected.reverse()
        items = [self._decoded_row(row) for row in selected]
        if session.table == "skill_snapshots":
            items = [self._skill_snapshot_descriptor(item) for item in items]
        next_cursor = None
        previous_cursor = None
        if selected:
            first = (
                str(selected[0][spec.timestamp]),
                str(selected[0][spec.primary_key]),
            )
            last = (
                str(selected[-1][spec.timestamp]),
                str(selected[-1][spec.primary_key]),
            )
            if self._position_exists(
                session.connection,
                session.table,
                spec,
                session.filters,
                session.predicates,
                session.snapshot,
                session.snapshot_sequence,
                "<",
                last,
            ):
                next_cursor = self._session_cursor(
                    session,
                    page_size,
                    "next",
                    last,
                )
            if self._position_exists(
                session.connection,
                session.table,
                spec,
                session.filters,
                session.predicates,
                session.snapshot,
                session.snapshot_sequence,
                ">",
                first,
            ):
                previous_cursor = self._session_cursor(
                    session,
                    page_size,
                    "previous",
                    first,
                )
        elif payload is not None:
            if direction == "next":
                previous_cursor = self._session_cursor(
                    session,
                    page_size,
                    "previous",
                    boundary,
                )
            else:
                next_cursor = self._session_cursor(
                    session,
                    page_size,
                    "next",
                    boundary,
                )
        return Page(
            items,
            next_cursor,
            previous_cursor,
            page_size,
            session.total,
            next_cursor is not None,
        )

    def _session_cursor(
        self,
        session: SQLitePageSession,
        page_size: int,
        direction: str,
        position: tuple[str, str],
    ) -> str:
        return self._cursor_codec.encode(
            _cursor_payload(
                session.endpoint,
                session.filter_fingerprint,
                page_size,
                direction,
                position,
                session.snapshot,
                session.total,
                session.snapshot_id,
                session.snapshot_sequence,
            )
        )

    def _position_exists(
        self,
        connection: sqlite3.Connection,
        table: str,
        spec: TablePageSpec,
        filters: Mapping[str, Any],
        predicates: tuple[str, ...],
        snapshot: tuple[str, str],
        snapshot_sequence: int,
        operator: str,
        position: tuple[str, str],
    ) -> bool:
        where, parameters = self._filter_clause(filters)
        where.extend(predicates)
        self._append_membership(
            where,
            parameters,
            table,
            spec.primary_key,
            snapshot_sequence,
        )
        self._append_position(
            where,
            parameters,
            spec.timestamp,
            spec.primary_key,
            "<=",
            snapshot,
        )
        self._append_position(
            where,
            parameters,
            spec.timestamp,
            spec.primary_key,
            operator,
            position,
        )
        return connection.execute(
            f"SELECT 1 FROM {table} WHERE {' AND '.join(where)} LIMIT 1",
            parameters,
        ).fetchone() is not None

    def _validate_filters(self, table: str, filters: Mapping[str, Any]) -> None:
        allowed = TABLE_PAGE_SPECS[table].filters
        for name, value in filters.items():
            if name not in allowed:
                raise ValueError(f"unsupported filter for {table}: {name}")
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise ValueError(f"invalid filter for {table}: {name}")
            if isinstance(value, str) and not value:
                raise ValueError(f"invalid filter for {table}: {name}")

    @staticmethod
    def _filter_clause(filters: Mapping[str, Any]) -> tuple[list[str], list[Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for name in sorted(filters):
            clauses.append(f"{name} = ?")
            parameters.append(filters[name])
        return clauses, parameters

    @staticmethod
    def _append_membership(
        clauses: list[str],
        parameters: list[Any],
        table: str,
        primary_key: str,
        snapshot_sequence: int,
    ) -> None:
        clauses.append(
            "EXISTS (SELECT 1 FROM row_sequences AS membership "
            "WHERE membership.table_name = ? "
            f"AND membership.row_key = CAST({table}.{primary_key} AS TEXT) "
            "AND membership.sequence_id <= ?)"
        )
        parameters.extend((table, snapshot_sequence))

    @staticmethod
    def _append_position(
        clauses: list[str],
        parameters: list[Any],
        timestamp: str,
        primary_key: str,
        operator: str,
        position: tuple[str, str],
    ) -> None:
        key_operator = "<=" if operator == "<=" else operator
        timestamp_operator = "<" if operator == "<=" else operator
        clauses.append(
            f"({timestamp} {timestamp_operator} ? OR "
            f"({timestamp} = ? AND {primary_key} {key_operator} ?))"
        )
        parameters.extend((position[0], position[0], position[1]))

    def _decoded_row(self, row: sqlite3.Row) -> dict[str, Any]:
        decoded: dict[str, Any] = {}
        for key in row.keys():
            value = row[key]
            if key.endswith("_json"):
                decoded[key.removesuffix("_json")] = self._redact_value(
                    self._load_json(str(value), [] if str(value).startswith("[") else {})
                )
            else:
                decoded[key] = self._redact_value(value, key)
        return decoded

    def _redact_value(self, value: Any, key: str = "") -> Any:
        if self._sensitive_key(key):
            return "[REDACTED]"
        if isinstance(value, str):
            return redact_text(value)
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        if isinstance(value, dict):
            return {
                str(child_key): self._redact_value(child_value, str(child_key))
                for child_key, child_value in value.items()
            }
        return value

    @staticmethod
    def _sensitive_key(key: str) -> bool:
        return is_sensitive_key(key)

    @staticmethod
    def _load_json(value: str, fallback: Any) -> Any:
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return fallback

    def _skill_row(
        self,
        value: Any,
        index: int,
        created_at: str,
    ) -> dict[str, Any]:
        item = dict(value) if isinstance(value, dict) else {"name": str(value)}
        natural_key = str(item.get("name") or item.get("path") or index)
        item["skill_id"] = hashlib.sha256(
            json.dumps(
                {"natural_key": natural_key, "item": item},
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()[:24]
        item["created_at"] = created_at
        return self._redact_value(item)

    @staticmethod
    def _skill_snapshot_descriptor(item: dict[str, Any]) -> dict[str, Any]:
        descriptor = dict(item)
        snapshot = descriptor.pop("snapshot", {})
        if not isinstance(snapshot, dict):
            snapshot = {}
        inventory = snapshot.get("inventory", [])
        duplicate_groups = snapshot.get("duplicate_groups", [])
        recommendations = snapshot.get("recommendations", [])
        descriptor["skill_row_count"] = (
            len(inventory) if isinstance(inventory, list) else 0
        )
        descriptor["duplicate_group_count"] = (
            len(duplicate_groups) if isinstance(duplicate_groups, list) else 0
        )
        descriptor["recommendation_count"] = (
            len(recommendations) if isinstance(recommendations, list) else 0
        )
        return descriptor

    @staticmethod
    def _error_payload(error: SupervisorStoreError) -> dict[str, Any]:
        return {
            "status": error.status,
            "error": {
                "code": error.status,
                "message": redact_text(str(error)),
            },
        }

    @staticmethod
    def _diagnostic_payload(error: SupervisorStoreError) -> dict[str, Any]:
        return {
            "status": error.status,
            "schema_version": None,
            "counts": {},
            "diagnostics": [
                {"status": error.status, "message": redact_text(str(error))}
            ],
        }
