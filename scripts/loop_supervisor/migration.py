"""Streaming migration and shadow gates for the legacy loop runtime."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from typing import Any
from uuid import uuid4

from .reconciler import (
    _decision_requirement,
    _projection,
    desired_action_for_run,
    discover_run_records,
    infer_loop_lineages,
)
from .models import ActionType
from .reviewer import REVIEW_INTERVAL_PARENTS, _completion_ids
from .store import SupervisorStore


LEGACY_SUPERVISOR_FILES = (
    "run-decisions.jsonl",
    "user-decisions.jsonl",
    "archived-user-decisions.jsonl",
    "continuation-plans.jsonl",
    "events.jsonl",
    "freshness-targets.jsonl",
    "recovery-attempts.jsonl",
    "service-health.json",
    "supervisor-state.json",
)


class MigrationValidationError(RuntimeError):
    """Raised when imported control data does not match its streamed source."""


@dataclass(frozen=True)
class RuntimeInventory:
    project_root: str
    tracked_paths: tuple[str, ...]
    dirty_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    runtime_paths: tuple[str, ...]
    parent22_paths: tuple[str, ...]
    crawler_raw_paths: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MigrationReport:
    project_root: str
    dry_run: bool
    source_rows: int
    transition_rows: int
    failure_rows: int
    decision_source_rows: int
    decision_rows: int
    archived_decisions: int
    open_decisions: int
    run_rows: int
    semantic_parent_completions: int
    snapshot_path: str
    validated: bool
    protected_paths: tuple[str, ...]
    _transition_ids: tuple[str, ...] = field(default=(), repr=False)
    _failure_expectations: Mapping[str, tuple[int, str, str]] = field(
        default_factory=dict, repr=False
    )
    _decision_expectations: Mapping[str, str] = field(default_factory=dict, repr=False)
    _run_ids: tuple[str, ...] = field(default=(), repr=False)
    _cadence_positions: Mapping[str, int] = field(default_factory=dict, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if not key.startswith("_")
        }


@dataclass(frozen=True)
class ShadowDifference:
    run_id: str
    classification: str
    old_classification: str
    old_action: str
    new_action: str
    summary: str


@dataclass(frozen=True)
class ShadowComparisonReport:
    compared_runs: int
    equivalent: int
    new_auto_recovery: int
    new_user_intervention: int
    unsafe_divergence: int
    differences: tuple[ShadowDifference, ...]

    @property
    def passed(self) -> bool:
        return self.new_user_intervention == 0 and self.unsafe_divergence == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "compared_runs": self.compared_runs,
            "equivalent": self.equivalent,
            "new_auto_recovery": self.new_auto_recovery,
            "new_user_intervention": self.new_user_intervention,
            "unsafe_divergence": self.unsafe_divergence,
            "passed": self.passed,
            "differences": [asdict(item) for item in self.differences],
        }


@dataclass
class _FailureAggregate:
    count: int = 0
    first_seen_at: str = ""
    last_seen_at: str = ""
    run_id: str = ""
    error_class: str = ""
    summary: str = ""
    resolution: str = "open"

    def observe(self, timestamp: str) -> None:
        self.count += 1
        if not self.first_seen_at or timestamp < self.first_seen_at:
            self.first_seen_at = timestamp
        if not self.last_seen_at or timestamp > self.last_seen_at:
            self.last_seen_at = timestamp


@dataclass(frozen=True)
class _LegacyTransition:
    transition_id: str
    run_id: str
    from_revision: int
    to_revision: int
    from_phase: str
    to_phase: str
    summary: str
    created_at: str


def inventory_runtime(project_root: Path) -> RuntimeInventory:
    """Inventory Git dirt, run baselines, and migration-sensitive evidence."""
    root = Path(project_root).resolve()
    tracked = _git_paths(root, ["ls-files", "-z"])
    dirty = _git_dirty_paths(root)
    runtime_paths = _existing_runtime_paths(root)
    parent22 = _matching_files(
        root,
        (
            root / "personal-wiki" / "domains",
            root / ".codex" / "loop-runs",
        ),
        lambda path: "parent-22" in path.as_posix().lower(),
    )
    crawler_candidates = _matching_files(
        root,
        (root / "personal-wiki" / "domains",),
        lambda path: "/raw/crawler/" in f"/{path.as_posix()}",
    )
    crawler_raw = (
        tuple(path for path in crawler_candidates if path in set(dirty))
        if tracked
        else crawler_candidates
    )
    baseline = _baseline_dirty_paths(root)
    protected = tuple(sorted(set(dirty) | set(parent22) | set(crawler_raw) | set(baseline)))
    return RuntimeInventory(
        project_root=str(root),
        tracked_paths=tuple(tracked),
        dirty_paths=tuple(dirty),
        protected_paths=protected,
        runtime_paths=tuple(runtime_paths),
        parent22_paths=tuple(parent22),
        crawler_raw_paths=tuple(crawler_raw),
    )


def migrate_jsonl(
    project_root: Path,
    store: SupervisorStore,
    *,
    dry_run: bool,
) -> MigrationReport:
    """Stream legacy JSONL, compact repeated ticks, and rebuild projections."""
    root = Path(project_root).resolve()
    if store.project_root != root:
        raise ValueError("Supervisor store does not belong to project_root")
    inventory = inventory_runtime(root)
    transitions, failures, source_rows = _scan_run_decisions(root)
    decisions, decision_source_rows = _scan_user_decisions(root)
    _merge_decision_failures(failures, decisions)
    records = [record for record in discover_run_records(root) if record.valid]
    lineage_by_run = infer_loop_lineages(records)
    semantic_ids = _semantic_completion_ids(records)
    cadence_positions = _cadence_positions(records, lineage_by_run, semantic_ids)
    snapshot_path = ""

    transition_ids = tuple(item.transition_id for item in transitions)
    decision_expectations = {
        str(item["decision_id"]): "closed" if item["status"] == "archived" else "open"
        for item in decisions
    }
    failure_expectations = {
        key: (item.count, item.first_seen_at, item.last_seen_at)
        for key, item in failures.items()
    }
    report = MigrationReport(
        project_root=str(root),
        dry_run=dry_run,
        source_rows=source_rows,
        transition_rows=len(transitions),
        failure_rows=len(failures),
        decision_source_rows=decision_source_rows,
        decision_rows=len(decisions),
        archived_decisions=sum(item["status"] == "archived" for item in decisions),
        open_decisions=sum(item["status"] != "archived" for item in decisions),
        run_rows=len(records),
        semantic_parent_completions=sum(len(items) for items in semantic_ids.values()),
        snapshot_path="",
        validated=dry_run,
        protected_paths=inventory.protected_paths,
        _transition_ids=transition_ids,
        _failure_expectations=failure_expectations,
        _decision_expectations=decision_expectations,
        _run_ids=tuple(sorted(record.run_id for record in records)),
        _cadence_positions=cadence_positions,
    )
    if dry_run:
        return report

    snapshot_path = _snapshot_runtime(root)
    _import_transitions(store, transitions)
    _import_failures(store, failures)
    _import_user_decisions(store, decisions)
    _import_run_projections(store, root, records, lineage_by_run)
    _import_cadence(store, cadence_positions)
    report = MigrationReport(
        **{
            **report.__dict__,
            "snapshot_path": snapshot_path,
        }
    )
    if not validate_migration(root, store, report):
        raise MigrationValidationError(
            "legacy migration validation failed; source artifacts were retained"
        )
    return MigrationReport(**{**report.__dict__, "validated": True})


def validate_migration(
    project_root: Path,
    store: SupervisorStore,
    report: MigrationReport,
) -> bool:
    """Validate imported identities, counts, statuses, timestamps, and cadence."""
    if Path(project_root).resolve() != store.project_root:
        return False
    transition_ids = {
        str(row["transition_id"]) for row in store.fetch_all("transitions")
    }
    if not set(report._transition_ids) <= transition_ids:
        return False
    failures = {
        str(row["failure_key"]): row for row in store.fetch_all("failures")
    }
    for key, (count, first_seen, last_seen) in report._failure_expectations.items():
        row = failures.get(key)
        if row is None:
            return False
        if int(row["occurrence_count"]) < count:
            return False
        if str(row["first_seen_at"]) != first_seen or str(row["last_seen_at"]) != last_seen:
            return False
    decisions = {
        str(row["decision_id"]): str(row["status"])
        for row in store.fetch_all("user_decisions")
    }
    if any(decisions.get(key) != status for key, status in report._decision_expectations.items()):
        return False
    run_ids = {str(row["run_id"]) for row in store.fetch_all("runs")}
    if not set(report._run_ids) <= run_ids:
        return False
    cadence = store.review_cadence_positions()
    return all(
        int(cadence.get(lineage, {}).get("reviewed_position", -1)) == position
        for lineage, position in report._cadence_positions.items()
    )


def shadow_compare(
    project_root: Path,
    store: SupervisorStore,
) -> ShadowComparisonReport:
    """Compare legacy classifications with registry outcomes without mutation."""
    root = Path(project_root).resolve()
    if store.project_root != root:
        raise ValueError("Supervisor store does not belong to project_root")
    legacy = _latest_legacy_decisions(root)
    differences: list[ShadowDifference] = []
    counts = defaultdict(int)
    records = [record for record in discover_run_records(root) if record.valid]
    child_sources = {
        str(record.payload.get("previous_run_id") or record.payload.get("parent_run_id") or "")
        for record in records
    }
    for record in records:
        old = legacy.get(record.run_id) or _legacy_classification(record.payload)
        new_action = ""
        new_requires_user = _decision_requirement(record.payload) is not None
        if not new_requires_user:
            try:
                request = desired_action_for_run(record.payload)
            except (TypeError, ValueError):
                new_requires_user = True
            else:
                new_action = request.action_type.value if request is not None else "none"
                new_requires_user = (
                    request is not None and request.action_type is ActionType.ASK_USER
                )
                if (
                    request is not None
                    and request.action_type is ActionType.CREATE_CONTINUATION
                    and record.run_id in child_sources
                ):
                    new_action = "none"
        classification = _compare_outcomes(old, new_action, new_requires_user)
        counts[classification] += 1
        if classification != "equivalent":
            differences.append(
                ShadowDifference(
                    run_id=record.run_id,
                    classification=classification,
                    old_classification=str(old.get("classification") or ""),
                    old_action=str(old.get("action") or ""),
                    new_action="user_decision" if new_requires_user else new_action,
                    summary=_difference_summary(classification),
                )
            )
    return ShadowComparisonReport(
        compared_runs=len(records),
        equivalent=counts["equivalent"],
        new_auto_recovery=counts["new_auto_recovery"],
        new_user_intervention=counts["new_user_intervention"],
        unsafe_divergence=counts["unsafe_divergence"],
        differences=tuple(differences),
    )


def cleanup_legacy_runtime(
    project_root: Path,
    migration: MigrationReport,
    comparison: ShadowComparisonReport,
) -> tuple[str, ...]:
    """Remove only known legacy runtime files after both migration gates pass."""
    root = Path(project_root).resolve()
    if not migration.validated or migration.dry_run:
        raise MigrationValidationError("legacy cleanup requires an applied validated migration")
    if not comparison.passed:
        raise MigrationValidationError("legacy cleanup requires a passing shadow comparison")
    if Path(migration.project_root).resolve() != root:
        raise MigrationValidationError("migration report belongs to another project root")
    supervisor = root / ".codex" / "supervisor"
    removed: list[str] = []
    for name in LEGACY_SUPERVISOR_FILES:
        path = supervisor / name
        if path.is_file() and not path.is_symlink():
            path.unlink()
            removed.append(path.as_posix())
    decision_dir = supervisor / "needs-user-decisions"
    if decision_dir.is_dir() and not decision_dir.is_symlink():
        shutil.rmtree(decision_dir)
        removed.append(decision_dir.as_posix())
    for audit_dir in (root / ".codex" / "loop-runs").glob("*/audit-reports"):
        if audit_dir.is_dir() and not audit_dir.is_symlink():
            shutil.rmtree(audit_dir)
            removed.append(audit_dir.as_posix())
    return tuple(removed)


def _scan_run_decisions(
    root: Path,
) -> tuple[list[_LegacyTransition], dict[str, _FailureAggregate], int]:
    path = root / ".codex" / "supervisor" / "run-decisions.jsonl"
    transitions: list[_LegacyTransition] = []
    failures: dict[str, _FailureAggregate] = {}
    prior_by_run: dict[str, tuple[Any, ...]] = {}
    revision_by_run: dict[str, int] = defaultdict(int)
    source_rows = 0
    for row in _iter_jsonl(path):
        source_rows += 1
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        signature = _decision_signature(row)
        if prior_by_run.get(run_id) != signature:
            revision_by_run[run_id] += 1
            revision = revision_by_run[run_id]
            timestamp = _timestamp(row.get("created_at"))
            identity = json.dumps(
                {"run_id": run_id, "revision": revision, "signature": signature},
                sort_keys=True,
                separators=(",", ":"),
            )
            transitions.append(
                _LegacyTransition(
                    transition_id="legacy-transition-"
                    + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32],
                    run_id=run_id,
                    from_revision=revision - 1,
                    to_revision=revision,
                    from_phase=(str(prior_by_run.get(run_id, ("", ""))[1]) if run_id in prior_by_run else ""),
                    to_phase=str(row.get("phase") or ""),
                    summary=(
                        "legacy supervisor classification: "
                        f"{row.get('classification') or 'unknown'} / {row.get('action') or 'none'}"
                    ),
                    created_at=timestamp,
                )
            )
            prior_by_run[run_id] = signature
        failure_key = _decision_failure_key(row)
        if failure_key:
            aggregate = failures.setdefault(
                failure_key,
                _FailureAggregate(
                    run_id=run_id,
                    error_class=str(row.get("reason") or "unsupported_state"),
                    summary=f"Legacy Supervisor repeatedly classified {run_id} for user intervention.",
                ),
            )
            aggregate.observe(_timestamp(row.get("created_at")))
    return transitions, failures, source_rows


def _scan_user_decisions(root: Path) -> tuple[list[dict[str, Any]], int]:
    supervisor = root / ".codex" / "supervisor"
    decisions: dict[str, dict[str, Any]] = {}
    source_rows = 0
    for name in ("user-decisions.jsonl", "archived-user-decisions.jsonl"):
        for row in _iter_jsonl(supervisor / name):
            source_rows += 1
            failure_key = str(row.get("failure_key") or "")
            identity = failure_key or str(row.get("decision_id") or "")
            if not identity:
                continue
            candidate = dict(row)
            if name.startswith("archived-"):
                candidate["status"] = "archived"
            existing = decisions.get(identity)
            if existing is None or candidate.get("status") == "archived":
                decisions[identity] = candidate
    return sorted(decisions.values(), key=lambda item: str(item.get("decision_id") or "")), source_rows


def _merge_decision_failures(
    failures: dict[str, _FailureAggregate], decisions: Sequence[Mapping[str, Any]]
) -> None:
    for decision in decisions:
        failure_key = str(decision.get("failure_key") or "")
        if not failure_key:
            continue
        run_ids = _string_list(decision.get("affected_runs"))
        opened = _timestamp(decision.get("opened_at") or decision.get("created_at"))
        closed = str(decision.get("archived_at") or "")
        aggregate = failures.get(failure_key)
        if aggregate is None:
            aggregate = _FailureAggregate(
                run_id=run_ids[0] if len(run_ids) == 1 else "",
                error_class=str(decision.get("reason") or "legacy_user_decision"),
                summary=str(decision.get("summary") or "Legacy user decision."),
            )
            aggregate.observe(opened)
            failures[failure_key] = aggregate
        if decision.get("status") == "archived":
            aggregate.resolution = "archived"
            if closed and closed > aggregate.last_seen_at:
                aggregate.last_seen_at = _timestamp(closed)


def _import_transitions(
    store: SupervisorStore, transitions: Sequence[_LegacyTransition]
) -> None:
    with store._immediate_transaction():
        for item in transitions:
            store._connection.execute(
                """
                INSERT OR IGNORE INTO transitions(
                  transition_id, run_id, from_revision, to_revision, from_phase,
                  to_phase, action_id, summary, artifact_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, '', ?, '[]', ?)
                """,
                (
                    item.transition_id,
                    item.run_id,
                    item.from_revision,
                    item.to_revision,
                    item.from_phase,
                    item.to_phase,
                    item.summary,
                    item.created_at,
                ),
            )


def _import_failures(
    store: SupervisorStore, failures: Mapping[str, _FailureAggregate]
) -> None:
    with store._immediate_transaction():
        for key, item in failures.items():
            store._connection.execute(
                """
                INSERT INTO failures(
                  failure_key, run_id, task_id, error_class, summary, resolution,
                  occurrence_count, first_seen_at, last_seen_at, created_at, updated_at
                ) VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(failure_key) DO UPDATE SET
                  run_id = excluded.run_id,
                  error_class = excluded.error_class,
                  summary = excluded.summary,
                  resolution = CASE
                    WHEN failures.resolution = 'open' THEN excluded.resolution
                    ELSE failures.resolution
                  END,
                  occurrence_count = MAX(failures.occurrence_count, excluded.occurrence_count),
                  first_seen_at = MIN(failures.first_seen_at, excluded.first_seen_at),
                  last_seen_at = MAX(failures.last_seen_at, excluded.last_seen_at),
                  updated_at = MAX(failures.updated_at, excluded.updated_at)
                """,
                (
                    key,
                    item.run_id,
                    item.error_class,
                    item.summary,
                    item.resolution,
                    item.count,
                    item.first_seen_at,
                    item.last_seen_at,
                    item.first_seen_at,
                    item.last_seen_at,
                ),
            )


def _import_user_decisions(
    store: SupervisorStore, decisions: Sequence[Mapping[str, Any]]
) -> None:
    with store._immediate_transaction():
        for item in decisions:
            decision_id = str(item.get("decision_id") or "")
            failure_key = str(item.get("failure_key") or "")
            if not decision_id:
                decision_id = "legacy-decision-" + hashlib.sha256(
                    failure_key.encode("utf-8")
                ).hexdigest()[:24]
            run_ids = _string_list(item.get("affected_runs"))
            run_id = run_ids[0] if len(run_ids) == 1 else ""
            scope = "run" if run_id else "global"
            closed = item.get("status") == "archived"
            created_at = _timestamp(item.get("opened_at") or item.get("created_at"))
            updated_at = _timestamp(
                item.get("archived_at") or item.get("updated_at") or created_at
            )
            store._connection.execute(
                """
                INSERT INTO user_decisions(
                  decision_id, scope, run_id, failure_key, status, summary,
                  required_decision, resolution, created_at, updated_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                  status = excluded.status,
                  summary = excluded.summary,
                  required_decision = excluded.required_decision,
                  resolution = excluded.resolution,
                  updated_at = excluded.updated_at,
                  closed_at = excluded.closed_at
                """,
                (
                    decision_id,
                    scope,
                    run_id,
                    failure_key,
                    "closed" if closed else "open",
                    str(item.get("summary") or "Legacy user decision."),
                    str(item.get("required_user_decision") or "Inspect the retained evidence."),
                    "archived during legacy migration" if closed else "",
                    created_at,
                    updated_at,
                    updated_at if closed else "",
                ),
            )


def _import_run_projections(
    store: SupervisorStore,
    root: Path,
    records: Sequence[Any],
    lineage_by_run: Mapping[str, str],
) -> None:
    for record in records:
        run = record.payload
        revision = run.get("state_revision", 0)
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            revision = 0
        store.upsert_run_projection(
            _projection(
                root,
                record,
                run,
                revision,
                loop_lineage_id=lineage_by_run[record.run_id],
            )
        )


def _import_cadence(
    store: SupervisorStore, cadence_positions: Mapping[str, int]
) -> None:
    now = store.format_time(store.current_time())
    with store._immediate_transaction():
        for lineage, position in cadence_positions.items():
            store._connection.execute(
                """
                INSERT INTO review_cadence(
                  lineage_id, reviewed_position, reserved_position, reservation_id, updated_at
                ) VALUES (?, ?, ?, '', ?)
                ON CONFLICT(lineage_id) DO UPDATE SET
                  reviewed_position = MAX(review_cadence.reviewed_position, excluded.reviewed_position),
                  reserved_position = MAX(review_cadence.reserved_position, excluded.reserved_position),
                  updated_at = excluded.updated_at
                """,
                (lineage, position, position, now),
            )


def _semantic_completion_ids(records: Sequence[Any]) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for record in records:
        run = record.payload
        raw = _completion_ids(run)
        numeric = []
        for value in raw:
            match = re.search(r"parent-(\d+)", value)
            if match:
                numeric.append(f"parent-{int(match.group(1))}")
        counter = run.get("parent_task_counter")
        if (
            isinstance(counter, int)
            and not isinstance(counter, bool)
            and counter >= len(raw)
            and raw
        ):
            numeric = [
                f"parent-{number}"
                for number in range(counter - len(raw) + 1, counter + 1)
            ]
        result[record.run_id] = tuple(dict.fromkeys(numeric))
    return result


def _cadence_positions(
    records: Sequence[Any],
    lineage_by_run: Mapping[str, str],
    semantic_ids: Mapping[str, tuple[str, ...]],
) -> dict[str, int]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for record in records:
        grouped[lineage_by_run[record.run_id]].update(semantic_ids.get(record.run_id, ()))
    return {
        lineage: len(items) - (len(items) % REVIEW_INTERVAL_PARENTS)
        for lineage, items in grouped.items()
        if items
    }


def _snapshot_runtime(root: Path) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = root.parent / f".{root.name}-supervisor-snapshots" / f"{stamp}-{uuid4().hex[:8]}"
    destination.mkdir(parents=True, exist_ok=False)
    for relative in (Path(".codex/loop-runs"), Path(".codex/supervisor")):
        source = root / relative
        if not source.exists() or source.is_symlink():
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("supervisor.db", "supervisor.db-wal", "supervisor.db-shm"),
        )
    manifest = {
        "schema_version": 1,
        "project_root": str(root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_paths": [".codex/loop-runs", ".codex/supervisor"],
    }
    (destination / "snapshot.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return destination.as_posix()


def _latest_legacy_decisions(root: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(root / ".codex/supervisor/run-decisions.jsonl"):
        run_id = str(row.get("run_id") or "")
        if run_id:
            latest[run_id] = row
    return latest


def _legacy_classification(run: Mapping[str, Any]) -> dict[str, str]:
    policy = str(run.get("policy") or "")
    phase = str(run.get("phase") or "")
    next_action = str(run.get("next_action") or "")
    if run.get("unsafe_secret_detected") is True or run.get("secret_detected") is True:
        return {"classification": "needs_user_decision", "action": "request_user_decision"}
    if policy == "autonomous_knowledge":
        if phase in {"planning", "generating", "evaluating", "artifact_hygiene", "cleanup", "audit_blocked"}:
            return {"classification": "actionable_resume", "action": "resume"}
        if phase == "stopped_blocked":
            if next_action in {"inspect_autonomous_dirty_paths", "inspect_required_evidence"}:
                return {"classification": "actionable_resume", "action": "resume"}
            return {"classification": "needs_user_decision", "action": "request_user_decision"}
        if phase == "stopped_budget":
            return {"classification": "continuation_candidate", "action": "create_continuation"}
    if policy == "demand_development":
        if phase in {
            "preflight", "planned", "generating", "verifying", "evaluating",
            "repair_needed", "artifact_hygiene", "cleanup", "audit_pending",
            "auditing", "child_running",
        }:
            return {"classification": "active", "action": "observe"}
        if phase == "passed_waiting_human_merge":
            return {"classification": "awaiting_human_merge", "action": "await_human_merge"}
    if phase in {"stopped_no_action", "audit_passed", "committed"}:
        return {"classification": "terminal", "action": "observe"}
    return {"classification": "needs_user_decision", "action": "request_user_decision"}


def _compare_outcomes(
    old: Mapping[str, Any], new_action: str, new_requires_user: bool
) -> str:
    old_action = str(old.get("action") or "")
    old_requires_user = (
        old_action in {"request_user_decision", "await_human_merge"}
        or old.get("classification") in {"needs_user_decision", "awaiting_human_merge"}
    )
    if new_requires_user:
        if (
            old.get("reason") == "archived_user_decision"
            and old.get("phase") == "stopped_blocked"
            and old.get("next_action") == "inspect_blocked_diagnostics"
        ):
            return "equivalent"
        return "equivalent" if old_requires_user else "new_user_intervention"
    if old_requires_user:
        return "new_auto_recovery"
    if old_action == "create_continuation":
        return "equivalent" if new_action == "create_continuation" else "unsafe_divergence"
    if old_action in {"observe", "await_human_merge"}:
        if new_action == "none" or old.get("classification") == "active":
            return "equivalent"
        return "unsafe_divergence"
    if old_action == "resume":
        return "equivalent" if new_action not in {"", "none"} else "unsafe_divergence"
    return "equivalent" if new_action == "none" else "unsafe_divergence"


def _difference_summary(classification: str) -> str:
    return {
        "new_auto_recovery": "Registry recovery replaces a legacy user gate.",
        "new_user_intervention": "Registry introduces user intervention absent from the legacy outcome.",
        "unsafe_divergence": "Legacy and registry actions are not semantically compatible.",
    }.get(classification, "Outcomes are equivalent.")


def _decision_signature(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("run_policy") or ""),
        str(row.get("phase") or ""),
        str(row.get("next_action") or ""),
        str(row.get("classification") or ""),
        str(row.get("action") or ""),
        str(row.get("reason") or ""),
    )


def _decision_failure_key(row: Mapping[str, Any]) -> str:
    if row.get("classification") != "needs_user_decision" and row.get("action") != "request_user_decision":
        return ""
    run_id = _slug(str(row.get("run_id") or "project"))
    reason = _slug(str(row.get("reason") or "unsupported_state"))
    if reason == "unsafe-secret":
        return f"unsafe_secret:{run_id}:run-artifacts:secret-signal"
    if reason == "auditor-stop":
        return f"auditor_stop:{run_id}:latest-audit:stop"
    return f"unsupported_state:{run_id}:run-state:{reason}"


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file() or path.is_symlink():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip().rstrip("\x00").strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise MigrationValidationError(
                    f"invalid legacy JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(payload, dict):
                raise MigrationValidationError(
                    f"legacy JSONL row must be an object at {path}:{line_number}"
                )
            yield payload


def _timestamp(value: object) -> str:
    text = str(value or "")
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _git_paths(root: Path, args: Sequence[str]) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, check=False
        )
    except OSError:
        return ()
    if completed.returncode != 0:
        return ()
    return tuple(sorted(part.decode("utf-8", "surrogateescape") for part in completed.stdout.split(b"\0") if part))


def _git_dirty_paths(root: Path) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return ()
    if completed.returncode != 0:
        return ()
    entries = completed.stdout.split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        value = entry[3:].decode("utf-8", "surrogateescape")
        if status[:1] in {b"R", b"C"} and index < len(entries):
            old = entries[index].decode("utf-8", "surrogateescape")
            index += 1
            if old:
                paths.append(old)
        paths.append(value)
    return tuple(sorted(set(paths)))


def _baseline_dirty_paths(root: Path) -> tuple[str, ...]:
    result: set[str] = set()
    for record in discover_run_records(root):
        if not record.valid:
            continue
        for value in _string_list(record.payload.get("baseline_dirty_paths")):
            normalized = value[3:] if len(value) > 3 and value[2] == " " else value
            path = PurePosixPath(normalized)
            if not path.is_absolute() and ".." not in path.parts:
                result.add(path.as_posix())
    return tuple(sorted(result))


def _existing_runtime_paths(root: Path) -> tuple[str, ...]:
    result: list[str] = []
    for relative in (Path(".codex/loop-runs"), Path(".codex/supervisor")):
        path = root / relative
        if path.exists() and not path.is_symlink():
            result.append(relative.as_posix())
    return tuple(result)


def _matching_files(
    root: Path,
    roots: Sequence[Path],
    predicate: Any,
) -> tuple[str, ...]:
    result: set[str] = set()
    for search_root in roots:
        if not search_root.is_dir() or search_root.is_symlink():
            continue
        for path in search_root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(root)
                if predicate(relative):
                    result.add(relative.as_posix())
    return tuple(sorted(result))


def _string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _slug(value: str, *, separator: str = "-") -> str:
    normalized = re.sub(r"[^a-z0-9]+", separator, value.strip().lower())
    normalized = re.sub(re.escape(separator) + r"+", separator, normalized).strip(separator)
    return normalized or "unknown"
