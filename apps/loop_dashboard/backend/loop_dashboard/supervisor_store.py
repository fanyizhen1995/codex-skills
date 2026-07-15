from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
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
from .redaction import redact_text


EXPECTED_SCHEMA_VERSION = 14


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


class SupervisorDashboardStore:
    """Read-only Dashboard projection over the canonical Supervisor database."""

    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root).resolve()
        self.db_path = self.project_root / ".codex" / "supervisor" / "supervisor.db"

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
    ) -> dict[str, Any]:
        validate_page_size(page_size)
        if table not in TABLE_PAGE_SPECS:
            raise ValueError(f"unsupported Supervisor collection: {table}")
        normalized_filters = dict(filters or {})
        self._validate_filters(table, normalized_filters)
        try:
            with closing(self._connect()) as connection:
                page = self._page_table(
                    connection,
                    table,
                    endpoint=endpoint,
                    page_size=page_size,
                    cursor=cursor,
                    filters=normalized_filters,
                )
            return self._available_page(page)
        except SupervisorStoreError as exc:
            return self._empty_page(page_size, exc)
        except sqlite3.Error as exc:
            return self._empty_page(
                page_size,
                SupervisorStoreUnavailable(
                    f"could not query Supervisor collection {table}: {exc}"
                ),
            )

    def skill_rows(
        self,
        snapshot_id: str,
        *,
        page_size: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        validate_page_size(page_size)
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
                codec = self._codec(connection)
                page = paginate_items(
                    items,
                    endpoint=f"supervisor-skills:{snapshot_id}:rows",
                    page_size=page_size,
                    cursor=cursor,
                    filters={"snapshot_id": snapshot_id},
                    timestamp_key="created_at",
                    primary_key="skill_id",
                    codec=codec,
                )
            return self._available_page(page)
        except SupervisorStoreError as exc:
            return self._empty_page(page_size, exc)
        except sqlite3.Error as exc:
            return self._empty_page(
                page_size,
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
        trigger_names = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger'"
            ).fetchall()
        }
        for table in TABLE_PAGE_SPECS:
            trigger = f"row_sequence_{table}_insert"
            if trigger not in trigger_names:
                raise SupervisorSchemaIncompatible(
                    f"Supervisor membership trigger is unavailable: {trigger}"
                )
        secret = connection.execute(
            "SELECT value FROM store_metadata WHERE key = 'cursor_secret'"
        ).fetchone()
        if secret is None or not str(secret["value"]):
            raise SupervisorSchemaIncompatible(
                "Supervisor cursor metadata is unavailable"
            )

    def _page_table(
        self,
        connection: sqlite3.Connection,
        table: str,
        *,
        endpoint: str,
        page_size: int,
        cursor: str | None,
        filters: Mapping[str, Any],
    ) -> Page[dict[str, Any]]:
        spec = TABLE_PAGE_SPECS[table]
        codec = self._codec(connection)
        fingerprint = codec.filter_fingerprint(filters)
        payload: CursorPayload | None = None
        if cursor:
            payload = codec.decode(cursor)
            _validate_collection_cursor(
                payload,
                endpoint=endpoint,
                page_size=page_size,
                fingerprint=fingerprint,
            )
            if payload.snapshot_sequence is None:
                raise CursorError("cursor snapshot sequence is invalid")

        where, parameters = self._filter_clause(filters)
        if payload is None:
            snapshot_sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(sequence_id), 0) FROM row_sequences"
                ).fetchone()[0]
            )
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
            direction = "next"
            boundary: tuple[str, str] | None = None
        else:
            snapshot_sequence = payload.snapshot_sequence
            snapshot = (
                payload.snapshot_timestamp,
                payload.snapshot_primary_key,
            )
            total = payload.snapshot_total
            direction = payload.direction
            boundary = (payload.timestamp, payload.primary_key)
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
        where_sql = f" WHERE {' AND '.join(where)}" if where else ""
        rows = connection.execute(
            f"SELECT * FROM {table}{where_sql} "
            f"ORDER BY {spec.timestamp} {order}, {spec.primary_key} {order} "
            "LIMIT ?",
            (*parameters, page_size + 1),
        ).fetchall()
        selected = list(rows[:page_size])
        if direction == "previous":
            selected.reverse()
        items = [self._decoded_row(row) for row in selected]
        if table == "skill_snapshots":
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
                connection,
                table,
                spec,
                filters,
                snapshot,
                snapshot_sequence,
                "<",
                last,
            ):
                next_cursor = codec.encode(
                    _cursor_payload(
                        endpoint,
                        fingerprint,
                        page_size,
                        "next",
                        last,
                        snapshot,
                        total,
                        snapshot_sequence,
                    )
                )
            if self._position_exists(
                connection,
                table,
                spec,
                filters,
                snapshot,
                snapshot_sequence,
                ">",
                first,
            ):
                previous_cursor = codec.encode(
                    _cursor_payload(
                        endpoint,
                        fingerprint,
                        page_size,
                        "previous",
                        first,
                        snapshot,
                        total,
                        snapshot_sequence,
                    )
                )
        return Page(
            items,
            next_cursor,
            previous_cursor,
            page_size,
            total,
            next_cursor is not None,
        )

    def _position_exists(
        self,
        connection: sqlite3.Connection,
        table: str,
        spec: TablePageSpec,
        filters: Mapping[str, Any],
        snapshot: tuple[str, str],
        snapshot_sequence: int,
        operator: str,
        position: tuple[str, str],
    ) -> bool:
        where, parameters = self._filter_clause(filters)
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

    def _codec(self, connection: sqlite3.Connection) -> CursorCodec:
        row = connection.execute(
            "SELECT value FROM store_metadata WHERE key = 'cursor_secret'"
        ).fetchone()
        if row is None:
            raise SupervisorSchemaIncompatible(
                "Supervisor cursor metadata is unavailable"
            )
        return CursorCodec(str(row["value"]).encode())

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
        normalized = key.lower().replace("-", "_")
        return any(
            part in normalized
            for part in ("authorization", "password", "secret", "token", "api_key")
        )

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
        item["skill_id"] = f"{index:06d}:{natural_key}"
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
    def _available_page(page: Page[dict[str, Any]]) -> dict[str, Any]:
        return {
            **page.to_dict(),
            "status": "available",
            "diagnostics": [],
        }

    @staticmethod
    def _empty_page(page_size: int, error: SupervisorStoreError) -> dict[str, Any]:
        return {
            **Page([], None, None, page_size, 0, False).to_dict(),
            "status": error.status,
            "diagnostics": [
                {"status": error.status, "message": redact_text(str(error))}
            ],
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
