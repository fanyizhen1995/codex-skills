"""Streaming migration and shadow gates for the legacy loop runtime."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any
from uuid import uuid4

from scripts.harness_loop_runtime_lock import (
    RunLockBusy,
    acquire_repository_mutation_lock,
)

from .reconciler import (
    _decision_requirement,
    _projection,
    _state_fingerprint,
    _state_revision,
    _open_directory_chain,
    _project_reconcile_lock,
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
class SourceArtifactEvidence:
    relative_path: str
    kind: str
    device: int
    inode: int
    size: int
    sha256: str = ""


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
    service_rows: int
    physical_rows: int
    valid_rows: int
    corrupt_rows: int
    compacted_rows: int
    quarantine_rows: int
    quarantine_path: str
    semantic_parent_completions: int
    snapshot_path: str
    validated: bool
    protected_paths: tuple[str, ...]
    source_artifacts: tuple[SourceArtifactEvidence, ...]
    _transition_expectations: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, repr=False
    )
    _failure_expectations: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, repr=False
    )
    _decision_expectations: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, repr=False
    )
    _run_expectations: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, repr=False
    )
    _service_expectations: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, repr=False
    )
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
    old_scope: str = ""
    new_scope: str = ""
    old_reason: str = ""
    new_reason: str = ""


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


@dataclass(frozen=True)
class _LegacyRow:
    path: Path
    line_number: int
    payload: dict[str, Any]
    raw_sha256: str
    raw_length: int


@dataclass
class _ScanCounts:
    physical: int = 0
    valid: int = 0
    corrupt: int = 0


@dataclass(frozen=True)
class _QuarantineRow:
    source_path: str
    line_number: int
    reason: str
    raw_sha256: str
    raw_length: int
    source_timestamp: str = ""


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
    source_artifacts = _capture_cleanup_sources(root)
    quarantine: list[_QuarantineRow] = []
    scan_counts = _ScanCounts()
    transitions, failures, source_rows = _scan_run_decisions(
        root, quarantine, scan_counts
    )
    decisions, decision_source_rows = _scan_user_decisions(
        root, quarantine, scan_counts
    )
    _merge_decision_failures(failures, decisions)
    records = [record for record in discover_run_records(root) if record.valid]
    _bind_archived_decisions_to_source_state(decisions)
    services = _scan_services(root, quarantine, scan_counts)
    if _capture_cleanup_sources(root) != source_artifacts:
        raise MigrationValidationError("legacy sources changed during migration scan")
    lineage_by_run = infer_loop_lineages(records)
    semantic_ids = _semantic_completion_ids(records)
    cadence_positions = _cadence_positions(records, lineage_by_run, semantic_ids)
    snapshot_path = ""

    transition_expectations = {
        item.transition_id: _expected_transition_row(item) for item in transitions
    }
    decision_expectations = {
        _decision_id(item): _expected_decision_row(item) for item in decisions
    }
    failure_expectations = {
        key: _expected_failure_row(key, item)
        for key, item in failures.items()
    }
    run_expectations = {
        record.run_id: _expected_run_row(
            _projection(
                root,
                record,
                record.payload,
                _state_revision(record.payload),
                loop_lineage_id=lineage_by_run[record.run_id],
            )
        )
        for record in records
    }
    service_expectations = {
        str(item["service_id"]): item for item in services
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
        service_rows=len(services),
        physical_rows=scan_counts.physical,
        valid_rows=scan_counts.valid,
        corrupt_rows=scan_counts.corrupt,
        compacted_rows=len(transitions) + len(decisions) + len(services),
        quarantine_rows=len(quarantine),
        quarantine_path="",
        semantic_parent_completions=sum(len(items) for items in semantic_ids.values()),
        snapshot_path="",
        validated=dry_run,
        protected_paths=inventory.protected_paths,
        source_artifacts=source_artifacts,
        _transition_expectations=transition_expectations,
        _failure_expectations=failure_expectations,
        _decision_expectations=decision_expectations,
        _run_expectations=run_expectations,
        _service_expectations=service_expectations,
        _cadence_positions=cadence_positions,
    )
    if dry_run:
        return report

    snapshot_path = _snapshot_runtime(root)
    quarantine_path = _write_quarantine(Path(snapshot_path), quarantine)
    _import_transitions(store, transitions)
    _import_failures(store, failures)
    _import_user_decisions(store, decisions)
    _import_run_projections(store, root, records, lineage_by_run)
    _import_services(store, services)
    _import_cadence(store, cadence_positions)
    report = MigrationReport(
        **{
            **report.__dict__,
            "snapshot_path": snapshot_path,
            "quarantine_path": quarantine_path,
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
    if report.physical_rows != report.valid_rows + report.corrupt_rows:
        return False
    if report.quarantine_rows != report.corrupt_rows:
        return False
    if report.valid_rows != (
        report.source_rows + report.decision_source_rows + report.service_rows
    ):
        return False
    if report.compacted_rows != (
        report.transition_rows + report.decision_rows + report.service_rows
    ):
        return False
    if not _rows_match_exactly(
        store.fetch_all("transitions"), "transition_id", report._transition_expectations
    ):
        return False
    if not _rows_match_exactly(
        store.fetch_all("failures"), "failure_key", report._failure_expectations
    ):
        return False
    if not _rows_match_exactly(
        store.fetch_all("user_decisions"),
        "decision_id",
        report._decision_expectations,
    ):
        return False
    if not _rows_match_exactly(
        store.fetch_all("runs"), "run_id", report._run_expectations
    ):
        return False
    if not _rows_match_exactly(
        store.fetch_all("services"), "service_id", report._service_expectations
    ):
        return False
    cadence = store.review_cadence_positions()
    return set(cadence) == set(report._cadence_positions) and all(
        int(cadence[lineage]["reviewed_position"]) == position
        and int(cadence[lineage]["reserved_position"]) == position
        and str(cadence[lineage]["reservation_id"]) == ""
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
    with tempfile.TemporaryDirectory(
        prefix=f".{root.name}-shadow-", dir=root.parent
    ) as temporary:
        copied_root = Path(temporary) / "project"
        _copy_shadow_inputs(root, copied_root)
        return _shadow_compare_copied_root(copied_root)


def _shadow_compare_copied_root(root: Path) -> ShadowComparisonReport:
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
        decision = _decision_requirement(record.payload)
        new = {
            "action": "user_decision" if decision is not None else "",
            "scope": decision[0] if decision is not None else "",
            "reason": decision[1] if decision is not None else "",
        }
        if decision is None:
            try:
                request = desired_action_for_run(record.payload)
            except (TypeError, ValueError):
                new = {
                    "action": "user_decision",
                    "scope": "run",
                    "reason": "unsupported_transition",
                }
            else:
                new["action"] = request.action_type.value if request is not None else "none"
                if request is not None and request.action_type is ActionType.ASK_USER:
                    new = {
                        "action": "user_decision",
                        "scope": "run",
                        "reason": (
                            "human_merge_required"
                            if record.payload.get("phase") == "passed_waiting_human_merge"
                            else "registry_user_gate"
                        ),
                    }
                if (
                    request is not None
                    and request.action_type is ActionType.CREATE_CONTINUATION
                    and record.run_id in child_sources
                ):
                    new["action"] = "none"
        classification = _compare_outcomes(old, new)
        counts[classification] += 1
        if classification != "equivalent":
            differences.append(
                ShadowDifference(
                    run_id=record.run_id,
                    classification=classification,
                    old_classification=str(old.get("classification") or ""),
                    old_action=str(old.get("action") or ""),
                    new_action=str(new["action"]),
                    summary=_difference_summary(classification),
                    old_scope=_old_decision_scope(old),
                    new_scope=str(new["scope"]),
                    old_reason=str(old.get("reason") or ""),
                    new_reason=str(new["reason"]),
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
    *,
    store: SupervisorStore,
) -> tuple[str, ...]:
    """Remove only known legacy runtime files after both migration gates pass."""
    root = Path(project_root).resolve()
    if not migration.validated or migration.dry_run:
        raise MigrationValidationError("legacy cleanup requires an applied validated migration")
    if not comparison.passed:
        raise MigrationValidationError("legacy cleanup requires a passing shadow comparison")
    if Path(migration.project_root).resolve() != root:
        raise MigrationValidationError("migration report belongs to another project root")
    _assert_cleanup_ownership(root)
    try:
        with _project_reconcile_lock(root), acquire_repository_mutation_lock(
            root, owner=f"migration-cleanup:{os.getpid()}"
        ):
            if not validate_migration(root, store, migration):
                raise MigrationValidationError(
                    "legacy cleanup requires current exact migration validation"
                )
            if _capture_cleanup_sources(root) != migration.source_artifacts:
                raise MigrationValidationError(
                    "legacy cleanup source artifacts changed since migration"
                )
            return _delete_cleanup_sources(root)
    except RunLockBusy as exc:
        raise MigrationValidationError(
            f"legacy cleanup requires quiescence; repository lock is held: {exc}"
        ) from exc


def _assert_cleanup_ownership(root: Path) -> None:
    supervisor = root / ".codex" / "supervisor"
    _require_cleanup_path(supervisor, root)
    runs = root / ".codex" / "loop-runs"
    _require_cleanup_path(runs, root)
    if runs.is_dir():
        for run_dir in runs.iterdir():
            if run_dir.is_symlink():
                raise MigrationValidationError(
                    f"cleanup path has symlink ancestor: {run_dir}"
                )


def _require_cleanup_path(path: Path, root: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise MigrationValidationError(f"cleanup path escapes project root: {path}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise MigrationValidationError(f"cleanup path has symlink ancestor: {current}")
        if not current.exists():
            break


def _capture_cleanup_sources(root: Path) -> tuple[SourceArtifactEvidence, ...]:
    supervisor = root / ".codex" / "supervisor"
    candidates = [
        supervisor / name
        for name in LEGACY_SUPERVISOR_FILES
        if os.path.lexists(supervisor / name)
    ]
    decisions = supervisor / "needs-user-decisions"
    if os.path.lexists(decisions):
        candidates.append(decisions)
    runs = root / ".codex" / "loop-runs"
    if runs.is_dir() and not runs.is_symlink():
        with os.scandir(runs) as entries:
            for entry in entries:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                audit = Path(entry.path) / "audit-reports"
                if os.path.lexists(audit):
                    candidates.append(audit)
    evidence: list[SourceArtifactEvidence] = []
    for candidate in sorted(candidates, key=lambda path: path.as_posix()):
        evidence.extend(_capture_source_tree(root, candidate))
    return tuple(sorted(evidence, key=lambda item: item.relative_path))


def _capture_source_tree(
    root: Path, path: Path
) -> list[SourceArtifactEvidence]:
    metadata = path.lstat()
    relative = path.relative_to(root).as_posix()
    if stat.S_ISREG(metadata.st_mode):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return [
            SourceArtifactEvidence(
                relative_path=relative,
                kind="file",
                device=metadata.st_dev,
                inode=metadata.st_ino,
                size=metadata.st_size,
                sha256=digest.hexdigest(),
            )
        ]
    if stat.S_ISLNK(metadata.st_mode):
        target = os.readlink(path)
        return [
            SourceArtifactEvidence(
                relative_path=relative,
                kind="symlink",
                device=metadata.st_dev,
                inode=metadata.st_ino,
                size=metadata.st_size,
                sha256=hashlib.sha256(os.fsencode(target)).hexdigest(),
            )
        ]
    if not stat.S_ISDIR(metadata.st_mode):
        return [
            SourceArtifactEvidence(
                relative_path=relative,
                kind="other",
                device=metadata.st_dev,
                inode=metadata.st_ino,
                size=metadata.st_size,
            )
        ]
    result = [
        SourceArtifactEvidence(
            relative_path=relative,
            kind="directory",
            device=metadata.st_dev,
            inode=metadata.st_ino,
            size=metadata.st_size,
        )
    ]
    with os.scandir(path) as entries:
        children = sorted((Path(entry.path) for entry in entries), key=lambda item: item.name)
    for child in children:
        result.extend(_capture_source_tree(root, child))
    return result


def _delete_cleanup_sources(root: Path) -> tuple[str, ...]:
    removed: list[str] = []
    try:
        with _open_directory_chain(
            root, (".codex", "supervisor"), create=False
        ) as supervisor_fd:
            for name in LEGACY_SUPERVISOR_FILES:
                if _unlink_regular_at(supervisor_fd, name):
                    removed.append((root / ".codex" / "supervisor" / name).as_posix())
            if _remove_tree_at(supervisor_fd, "needs-user-decisions"):
                removed.append(
                    (root / ".codex" / "supervisor" / "needs-user-decisions").as_posix()
                )
    except FileNotFoundError:
        pass
    try:
        with _open_directory_chain(
            root, (".codex", "loop-runs"), create=False
        ) as runs_fd:
            for run_id in sorted(os.listdir(runs_fd)):
                try:
                    run_metadata = os.stat(
                        run_id, dir_fd=runs_fd, follow_symlinks=False
                    )
                except FileNotFoundError:
                    continue
                if not stat.S_ISDIR(run_metadata.st_mode):
                    continue
                run_fd = os.open(run_id, _DIRECTORY_FLAGS, dir_fd=runs_fd)
                try:
                    opened = os.fstat(run_fd)
                    if (opened.st_dev, opened.st_ino) != (
                        run_metadata.st_dev,
                        run_metadata.st_ino,
                    ):
                        raise MigrationValidationError(
                            f"cleanup run directory ownership changed: {run_id}"
                        )
                    if _remove_tree_at(run_fd, "audit-reports"):
                        removed.append(
                            (
                                root
                                / ".codex"
                                / "loop-runs"
                                / run_id
                                / "audit-reports"
                            ).as_posix()
                        )
                finally:
                    os.close(run_fd)
    except FileNotFoundError:
        pass
    return tuple(removed)


_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)


def _unlink_regular_at(parent_fd: int, name: str) -> bool:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(metadata.st_mode):
        raise MigrationValidationError(f"cleanup source is not a regular file: {name}")
    os.unlink(name, dir_fd=parent_fd)
    return True


def _remove_tree_at(parent_fd: int, name: str) -> bool:
    try:
        expected = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(expected.st_mode):
        raise MigrationValidationError(f"cleanup source is not a directory: {name}")
    directory_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    try:
        opened = os.fstat(directory_fd)
        if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
            raise MigrationValidationError(
                f"cleanup directory ownership changed: {name}"
            )
        for child in sorted(os.listdir(directory_fd)):
            metadata = os.stat(child, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                _remove_tree_at(directory_fd, child)
            elif stat.S_ISREG(metadata.st_mode):
                os.unlink(child, dir_fd=directory_fd)
            else:
                raise MigrationValidationError(
                    f"cleanup tree contains unsafe entry: {name}/{child}"
                )
    finally:
        os.close(directory_fd)
    os.rmdir(name, dir_fd=parent_fd)
    return True


def _scan_run_decisions(
    root: Path,
    quarantine: list[_QuarantineRow],
    counts: _ScanCounts,
) -> tuple[list[_LegacyTransition], dict[str, _FailureAggregate], int]:
    path = root / ".codex" / "supervisor" / "run-decisions.jsonl"
    transitions: list[_LegacyTransition] = []
    failures: dict[str, _FailureAggregate] = {}
    prior_by_run: dict[str, tuple[Any, ...]] = {}
    revision_by_run: dict[str, int] = defaultdict(int)
    source_rows = 0
    for source in _iter_jsonl(path, quarantine=quarantine, counts=counts):
        row = source.payload
        run_id = str(row.get("run_id") or "")
        try:
            timestamp = _source_timestamp(
                row.get("created_at"), f"{path}:{source.line_number}:created_at"
            )
        except MigrationValidationError:
            _quarantine_source(
                quarantine,
                counts,
                source,
                "invalid_timestamp",
                source_timestamp=str(row.get("created_at") or ""),
            )
            continue
        if not run_id:
            _quarantine_source(quarantine, counts, source, "missing_run_id")
            continue
        counts.valid += 1
        source_rows += 1
        signature = _decision_signature(row)
        if prior_by_run.get(run_id) != signature:
            revision_by_run[run_id] += 1
            revision = revision_by_run[run_id]
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
            aggregate.observe(timestamp)
    return transitions, failures, source_rows


def _scan_user_decisions(
    root: Path,
    quarantine: list[_QuarantineRow],
    counts: _ScanCounts,
) -> tuple[list[dict[str, Any]], int]:
    supervisor = root / ".codex" / "supervisor"
    decisions: dict[str, dict[str, Any]] = {}
    source_rows = 0
    for name in ("user-decisions.jsonl", "archived-user-decisions.jsonl"):
        path = supervisor / name
        for source in _iter_jsonl(path, quarantine=quarantine, counts=counts):
            row = source.payload
            failure_key = str(row.get("failure_key") or "")
            identity = failure_key or str(row.get("decision_id") or "")
            if not identity:
                _quarantine_source(quarantine, counts, source, "missing_decision_identity")
                continue
            candidate = dict(row)
            existing = decisions.get(identity)
            if name.startswith("archived-"):
                candidate = {
                    **(existing or {}),
                    **candidate,
                    "status": "archived",
                    "_archived_source_evidence": {
                        "source_path": path.relative_to(root).as_posix(),
                        "line_number": source.line_number,
                        "source_sha256": source.raw_sha256,
                        "source_size": source.raw_length,
                    },
                }
            timestamp_value = candidate.get("opened_at") or candidate.get("created_at")
            try:
                _source_timestamp(
                    timestamp_value, f"{path}:{source.line_number}:opened_at"
                )
                if name.startswith("archived-"):
                    _source_timestamp(
                        candidate.get("archived_at"),
                        f"{path}:{source.line_number}:archived_at",
                    )
            except MigrationValidationError:
                _quarantine_source(
                    quarantine,
                    counts,
                    source,
                    "invalid_timestamp",
                    source_timestamp=str(
                        timestamp_value or candidate.get("archived_at") or ""
                    ),
                )
                continue
            counts.valid += 1
            source_rows += 1
            if existing is None or candidate.get("status") == "archived":
                decisions[identity] = candidate
    return sorted(decisions.values(), key=lambda item: str(item.get("decision_id") or "")), source_rows


def _scan_services(
    root: Path,
    quarantine: list[_QuarantineRow],
    counts: _ScanCounts,
) -> list[dict[str, Any]]:
    path = root / ".codex" / "supervisor" / "service-health.json"
    if not path.is_file() or path.is_symlink():
        return []
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        if b"\x00" in raw:
            raise ValueError("nul byte")
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        counts.physical += 1
        quarantine.append(
            _QuarantineRow(
                source_path=path.as_posix(),
                line_number=1,
                reason="nul_byte" if b"\x00" in raw else "malformed_json",
                raw_sha256=digest,
                raw_length=len(raw),
            )
        )
        counts.corrupt += 1
        return []
    if not isinstance(payload, Mapping):
        counts.physical += 1
        quarantine.append(
            _QuarantineRow(
                source_path=path.as_posix(),
                line_number=1,
                reason="non_object",
                raw_sha256=digest,
                raw_length=len(raw),
            )
        )
        counts.corrupt += 1
        return []
    counts.physical += len(payload)
    services: list[dict[str, Any]] = []
    for entry_number, (service_id, service) in enumerate(sorted(payload.items()), start=1):
        if (
            not isinstance(service_id, str)
            or not service_id
            or not isinstance(service, Mapping)
        ):
            quarantine.append(
                _QuarantineRow(
                    source_path=path.as_posix(),
                    line_number=entry_number,
                    reason="invalid_service_entry",
                    raw_sha256=digest,
                    raw_length=len(raw),
                )
            )
            counts.corrupt += 1
            continue
        try:
            heartbeat = _source_timestamp(
                service.get("heartbeat_at"), f"{path}:{service_id}:heartbeat_at"
            )
        except MigrationValidationError:
            quarantine.append(
                _QuarantineRow(
                    source_path=path.as_posix(),
                    line_number=1,
                    reason="invalid_timestamp",
                    raw_sha256=digest,
                    raw_length=len(raw),
                    source_timestamp=str(service.get("heartbeat_at") or ""),
                )
            )
            counts.corrupt += 1
            continue
        process_id = service.get("process_id")
        if process_id is not None and (
            not isinstance(process_id, int) or isinstance(process_id, bool) or process_id < 0
        ):
            quarantine.append(
                _QuarantineRow(
                    source_path=path.as_posix(),
                    line_number=entry_number,
                    reason="invalid_process_id",
                    raw_sha256=digest,
                    raw_length=len(raw),
                )
            )
            counts.corrupt += 1
            continue
        details = {
            str(key): value
            for key, value in service.items()
            if key
            not in {
                "status",
                "endpoint",
                "process_id",
                "heartbeat_at",
                "version",
            }
        }
        services.append(
            {
                "service_id": service_id,
                "status": str(service.get("status") or ""),
                "endpoint": str(service.get("endpoint") or ""),
                "process_id": process_id,
                "heartbeat_at": heartbeat,
                "version": str(service.get("version") or ""),
                "details_json": json.dumps(
                    details, sort_keys=True, separators=(",", ":"), ensure_ascii=True
                ),
                "created_at": heartbeat,
                "updated_at": heartbeat,
            }
        )
        counts.valid += 1
    return services


def _merge_decision_failures(
    failures: dict[str, _FailureAggregate], decisions: Sequence[Mapping[str, Any]]
) -> None:
    for decision in decisions:
        failure_key = str(decision.get("failure_key") or "")
        if not failure_key:
            continue
        run_ids = _string_list(decision.get("affected_runs"))
        opened = _source_timestamp(
            decision.get("opened_at") or decision.get("created_at"),
            "legacy user decision opened_at",
        )
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
            if closed:
                closed_at = _source_timestamp(closed, "legacy user decision archived_at")
                if closed_at > aggregate.last_seen_at:
                    aggregate.last_seen_at = closed_at


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
            decision_id = _decision_id(item)
            failure_key = str(item.get("failure_key") or "")
            run_ids = _string_list(item.get("affected_runs"))
            run_id = run_ids[0] if len(run_ids) == 1 else ""
            scope = "run" if run_id else "global"
            closed = item.get("status") == "archived"
            resolution = _archived_resolution(item) if closed else ""
            created_at = _source_timestamp(
                item.get("opened_at") or item.get("created_at"),
                "legacy user decision opened_at",
            )
            updated_at = _source_timestamp(
                item.get("archived_at") or item.get("updated_at") or created_at,
                "legacy user decision updated_at",
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
                    resolution,
                    created_at,
                    updated_at,
                    updated_at if closed else "",
                ),
            )


def _import_services(
    store: SupervisorStore, services: Sequence[Mapping[str, Any]]
) -> None:
    with store._immediate_transaction():
        for item in services:
            store._connection.execute(
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
                  created_at = excluded.created_at,
                  updated_at = excluded.updated_at
                """,
                tuple(
                    item[key]
                    for key in (
                        "service_id",
                        "status",
                        "endpoint",
                        "process_id",
                        "heartbeat_at",
                        "version",
                        "details_json",
                        "created_at",
                        "updated_at",
                    )
                ),
            )


def _bind_archived_decisions_to_source_state(
    decisions: Sequence[dict[str, Any]],
) -> None:
    for item in decisions:
        if item.get("status") != "archived":
            continue
        state = item.get("archived_run_state")
        if not isinstance(state, Mapping):
            continue
        revision = state.get("revision")
        fingerprint = state.get("fingerprint")
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 0
            or not isinstance(fingerprint, str)
            or not fingerprint
        ):
            continue
        item["_archived_run_state"] = {
            "revision": revision,
            "fingerprint": fingerprint,
            **(
                dict(item["_archived_source_evidence"])
                if isinstance(item.get("_archived_source_evidence"), Mapping)
                else {}
            ),
        }


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


def _copy_shadow_inputs(root: Path, destination: Path) -> None:
    before = _capture_shadow_sources(root)
    destination.mkdir(parents=True, exist_ok=False)
    sources = [(root / ".codex" / "loop-runs", destination / ".codex" / "loop-runs")]
    worktrees = root / ".worktrees"
    if worktrees.is_dir() and not worktrees.is_symlink():
        for worktree in worktrees.iterdir():
            if not worktree.is_dir() or worktree.is_symlink():
                continue
            sources.append(
                (
                    worktree / ".codex" / "loop-runs",
                    destination / ".worktrees" / worktree.name / ".codex" / "loop-runs",
                )
            )
    for source, target in sources:
        if not source.exists():
            continue
        _require_tree_without_symlinks(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    legacy = root / ".codex" / "supervisor" / "run-decisions.jsonl"
    if legacy.exists():
        if legacy.is_symlink() or not legacy.is_file():
            raise MigrationValidationError(f"unsafe shadow source: {legacy}")
        target = destination / ".codex" / "supervisor" / legacy.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)
    _rebind_shadow_owners(destination)
    for path in destination.rglob("*"):
        if path.is_file():
            path.chmod(0o400)
    if _capture_shadow_sources(root) != before:
        raise MigrationValidationError("shadow sources changed while copying")


def _capture_shadow_sources(root: Path) -> tuple[SourceArtifactEvidence, ...]:
    candidates = [root / ".codex" / "loop-runs"]
    worktrees = root / ".worktrees"
    if worktrees.is_dir() and not worktrees.is_symlink():
        candidates.extend(
            worktree / ".codex" / "loop-runs"
            for worktree in worktrees.iterdir()
            if worktree.is_dir() and not worktree.is_symlink()
        )
    legacy = root / ".codex" / "supervisor" / "run-decisions.jsonl"
    candidates.append(legacy)
    result: list[SourceArtifactEvidence] = []
    for candidate in candidates:
        if os.path.lexists(candidate):
            result.extend(_capture_source_tree(root, candidate))
    return tuple(sorted(result, key=lambda item: item.relative_path))


def _rebind_shadow_owners(destination: Path) -> None:
    for run_json in destination.rglob(".codex/loop-runs/*/run.json"):
        try:
            payload = json.loads(run_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        copied_repo = run_json.parents[3].resolve()
        changed = False
        if isinstance(payload.get("worktree"), str) and payload["worktree"]:
            payload["worktree"] = str(copied_repo)
            changed = True
        if isinstance(payload.get("project_root"), str) and payload["project_root"]:
            payload["project_root"] = str(copied_repo)
            changed = True
        if changed:
            run_json.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )


def _require_tree_without_symlinks(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise MigrationValidationError(f"unsafe shadow source: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise MigrationValidationError(f"shadow source has symlink: {path}")


def _write_quarantine(
    snapshot_root: Path, quarantine: Sequence[_QuarantineRow]
) -> str:
    if not quarantine:
        return ""
    path = snapshot_root / "migration-quarantine.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for item in quarantine:
            handle.write(
                json.dumps(
                    asdict(item), sort_keys=True, separators=(",", ":"), ensure_ascii=True
                )
                + "\n"
            )
    return path.as_posix()


def _latest_legacy_decisions(root: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for source in _iter_jsonl(root / ".codex/supervisor/run-decisions.jsonl"):
        row = source.payload
        run_id = str(row.get("run_id") or "")
        if run_id:
            latest[run_id] = row
    return latest


def _legacy_classification(run: Mapping[str, Any]) -> dict[str, str]:
    policy = str(run.get("policy") or "")
    phase = str(run.get("phase") or "")
    next_action = str(run.get("next_action") or "")
    base = {"phase": phase, "next_action": next_action}
    if run.get("unsafe_secret_detected") is True or run.get("secret_detected") is True:
        return {
            **base,
            "classification": "needs_user_decision",
            "action": "request_user_decision",
            "scope": "global",
            "reason": "secret_exposure",
        }
    if policy == "autonomous_knowledge":
        if phase in {"planning", "generating", "evaluating", "artifact_hygiene", "cleanup", "audit_blocked"}:
            return {**base, "classification": "actionable_resume", "action": "resume"}
        if phase == "stopped_blocked":
            if next_action in {"inspect_autonomous_dirty_paths", "inspect_required_evidence"}:
                return {**base, "classification": "actionable_resume", "action": "resume"}
            return {
                **base,
                "classification": "needs_user_decision",
                "action": "request_user_decision",
                "scope": "run",
                "reason": "unsupported_state",
            }
        if phase == "stopped_budget":
            return {**base, "classification": "continuation_candidate", "action": "create_continuation"}
    if policy == "demand_development":
        if phase in {
            "preflight", "planned", "generating", "verifying", "evaluating",
            "repair_needed", "artifact_hygiene", "cleanup", "audit_pending",
            "auditing", "child_running",
        }:
            return {**base, "classification": "active", "action": "observe"}
        if phase == "passed_waiting_human_merge":
            return {
                **base,
                "classification": "awaiting_human_merge",
                "action": "await_human_merge",
                "scope": "run",
                "reason": "human_merge_required",
            }
    if phase in {"stopped_no_action", "audit_passed", "committed"}:
        return {**base, "classification": "terminal", "action": "observe"}
    return {
        **base,
        "classification": "needs_user_decision",
        "action": "request_user_decision",
        "scope": "run",
        "reason": "unsupported_state",
    }


def _compare_outcomes(old: Mapping[str, Any], new: Mapping[str, str]) -> str:
    old_action = str(old.get("action") or "")
    old_requires_user = (
        old_action in {"request_user_decision", "await_human_merge"}
        or old.get("classification") in {"needs_user_decision", "awaiting_human_merge"}
    )
    new_action = str(new.get("action") or "")
    new_requires_user = new_action == "user_decision"
    if new_requires_user:
        if (
            old.get("reason") == "archived_user_decision"
            and old.get("phase") == "stopped_blocked"
            and old.get("next_action") == "inspect_blocked_diagnostics"
        ):
            return (
                "equivalent"
                if str(new.get("scope") or "") == "run"
                and str(new.get("reason") or "") == "registry_user_gate"
                else "unsafe_divergence"
            )
        if not old_requires_user:
            return "new_user_intervention"
        if _old_decision_scope(old) != str(new.get("scope") or ""):
            return "unsafe_divergence"
        return (
            "equivalent"
            if _old_decision_reason(old) == str(new.get("reason") or "")
            else "unsafe_divergence"
        )
    if old_requires_user:
        return "new_auto_recovery"
    if old_action == "create_continuation":
        return "equivalent" if new_action == "create_continuation" else "unsafe_divergence"
    if old_action == "observe":
        return (
            "equivalent"
            if new_action in _compatible_observe_actions(old)
            else "unsafe_divergence"
        )
    if old_action == "resume":
        return (
            "equivalent"
            if new_action in _compatible_resume_actions(old)
            else "unsafe_divergence"
        )
    return "equivalent" if new_action == "none" else "unsafe_divergence"


def _old_decision_scope(old: Mapping[str, Any]) -> str:
    explicit = str(old.get("scope") or "")
    if explicit:
        return explicit
    reason = str(old.get("reason") or "").replace("-", "_")
    return "global" if reason in {"unsafe_secret", "secret_exposure", "repo_corruption"} else "run"


def _old_decision_reason(old: Mapping[str, Any]) -> str:
    if str(old.get("action") or "") == "await_human_merge" or old.get(
        "classification"
    ) == "awaiting_human_merge":
        return "human_merge_required"
    return str(old.get("reason") or "").replace("-", "_")


def _compatible_observe_actions(old: Mapping[str, Any]) -> set[str]:
    if old.get("classification") == "terminal":
        return {"none"}
    if old.get("classification") != "active":
        return {"none"}
    phase = str(old.get("phase") or "")
    return {
        "preflight": {"ask_user"},
        "planned": {"run_planner"},
        "planning": {"run_planner"},
        "generating": {"run_generator"},
        "repair_needed": {"run_generator"},
        "verifying": {"run_evidence_gate", "run_evaluator"},
        "evaluating": {"run_evaluator"},
        "artifact_hygiene": {"run_artifact_hygiene"},
        "cleanup": {"cleanup", "commit", "push"},
        "child_running": {"none", "run_planner"},
    }.get(phase, set())


def _compatible_resume_actions(old: Mapping[str, Any]) -> set[str]:
    phase = str(old.get("phase") or "")
    return {
        "planning": {"run_planner"},
        "generating": {"run_generator"},
        "evaluating": {"run_evaluator"},
        "artifact_hygiene": {"run_artifact_hygiene"},
        "cleanup": {"cleanup", "commit", "push"},
        "audit_blocked": {"run_alternate_recovery", "run_planner"},
        "stopped_blocked": {"recover_generator_result"},
    }.get(phase, set())


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


def _decision_id(item: Mapping[str, Any]) -> str:
    decision_id = str(item.get("decision_id") or "")
    if decision_id:
        return decision_id
    failure_key = str(item.get("failure_key") or "")
    return "legacy-decision-" + hashlib.sha256(failure_key.encode("utf-8")).hexdigest()[:24]


def _archived_resolution(item: Mapping[str, Any]) -> str:
    archived_state = item.get("_archived_run_state")
    if not isinstance(archived_state, Mapping):
        return ""
    return "archived during legacy migration:" + json.dumps(
        dict(archived_state), sort_keys=True, separators=(",", ":")
    )


def _expected_transition_row(item: _LegacyTransition) -> dict[str, Any]:
    return {
        "transition_id": item.transition_id,
        "run_id": item.run_id,
        "from_revision": item.from_revision,
        "to_revision": item.to_revision,
        "from_phase": item.from_phase,
        "to_phase": item.to_phase,
        "action_id": "",
        "summary": item.summary,
        "artifact_json": "[]",
        "created_at": item.created_at,
    }


def _expected_failure_row(key: str, item: _FailureAggregate) -> dict[str, Any]:
    return {
        "failure_key": key,
        "run_id": item.run_id,
        "task_id": "",
        "error_class": item.error_class,
        "summary": item.summary,
        "resolution": item.resolution,
        "occurrence_count": item.count,
        "first_seen_at": item.first_seen_at,
        "last_seen_at": item.last_seen_at,
        "created_at": item.first_seen_at,
        "updated_at": item.last_seen_at,
    }


def _expected_decision_row(item: Mapping[str, Any]) -> dict[str, Any]:
    run_ids = _string_list(item.get("affected_runs"))
    run_id = run_ids[0] if len(run_ids) == 1 else ""
    closed = item.get("status") == "archived"
    created_at = _source_timestamp(
        item.get("opened_at") or item.get("created_at"), "legacy user decision opened_at"
    )
    updated_at = _source_timestamp(
        item.get("archived_at") or item.get("updated_at") or created_at,
        "legacy user decision updated_at",
    )
    return {
        "decision_id": _decision_id(item),
        "scope": "run" if run_id else "global",
        "run_id": run_id,
        "failure_key": str(item.get("failure_key") or ""),
        "status": "closed" if closed else "open",
        "summary": str(item.get("summary") or "Legacy user decision."),
        "required_decision": str(
            item.get("required_user_decision") or "Inspect the retained evidence."
        ),
        "resolution": _archived_resolution(item) if closed else "",
        "created_at": created_at,
        "updated_at": updated_at,
        "closed_at": updated_at if closed else "",
    }


def _expected_run_row(projection: Mapping[str, Any]) -> dict[str, Any]:
    summary = {
        "summary": projection.get("summary", ""),
        "artifact_refs": projection.get("artifact_refs", []),
    }
    return {
        "run_id": projection["run_id"],
        "loop_lineage_id": projection.get("loop_lineage_id", ""),
        "parent_run_id": projection.get("parent_run_id", ""),
        "policy": projection.get("policy", ""),
        "phase": projection.get("phase", ""),
        "status": projection.get("status", ""),
        "revision": projection["revision"],
        "repo_relative_root": projection.get("repo_relative_root", "."),
        "state_fingerprint": projection.get("state_fingerprint", ""),
        "summary_json": json.dumps(
            summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ),
    }


def _rows_match_exactly(
    rows: Sequence[Mapping[str, Any]],
    identity_key: str,
    expected: Mapping[str, Mapping[str, Any]],
) -> bool:
    actual = {str(row.get(identity_key) or ""): row for row in rows}
    if set(actual) != set(expected):
        return False
    return all(
        all(actual[identity].get(key) == value for key, value in projection.items())
        for identity, projection in expected.items()
    )


def _iter_jsonl(
    path: Path,
    *,
    quarantine: list[_QuarantineRow] | None = None,
    counts: _ScanCounts | None = None,
) -> Iterator[_LegacyRow]:
    if not path.is_file() or path.is_symlink():
        return
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if counts is not None:
                counts.physical += 1
            digest = hashlib.sha256(raw).hexdigest()
            reason = ""
            stripped = raw.strip()
            if not stripped:
                reason = "blank_row"
            elif b"\x00" in raw:
                reason = "nul_byte"
            else:
                try:
                    text = stripped.decode("utf-8")
                except UnicodeDecodeError:
                    reason = "invalid_utf8"
                else:
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        reason = "malformed_json"
                    else:
                        if not isinstance(payload, dict):
                            reason = "non_object"
                        else:
                            yield _LegacyRow(
                                path=path,
                                line_number=line_number,
                                payload=payload,
                                raw_sha256=digest,
                                raw_length=len(raw),
                            )
                            continue
            if quarantine is None:
                continue
            quarantine.append(
                _QuarantineRow(
                    source_path=path.as_posix(),
                    line_number=line_number,
                    reason=reason,
                    raw_sha256=digest,
                    raw_length=len(raw),
                )
            )
            if counts is not None:
                counts.corrupt += 1


def _quarantine_source(
    quarantine: list[_QuarantineRow],
    counts: _ScanCounts,
    source: _LegacyRow,
    reason: str,
    *,
    source_timestamp: str = "",
) -> None:
    quarantine.append(
        _QuarantineRow(
            source_path=source.path.as_posix(),
            line_number=source.line_number,
            reason=reason,
            raw_sha256=source.raw_sha256,
            raw_length=source.raw_length,
            source_timestamp=source_timestamp,
        )
    )
    counts.corrupt += 1


def _source_timestamp(value: object, source: str) -> str:
    text = str(value or "")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MigrationValidationError(f"invalid source timestamp at {source}: {text!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _git_paths(root: Path, args: Sequence[str]) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, check=False
        )
    except OSError as exc:
        raise MigrationValidationError(
            f"git {' '.join(args)} failed to start: {exc}"
        ) from exc
    if completed.returncode != 0:
        raise MigrationValidationError(
            f"git {' '.join(args)} failed with exit {completed.returncode}: "
            f"{completed.stderr.decode('utf-8', 'replace').strip()}"
        )
    return tuple(sorted(part.decode("utf-8", "surrogateescape") for part in completed.stdout.split(b"\0") if part))


def _git_dirty_paths(root: Path) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise MigrationValidationError(f"git status failed to start: {exc}") from exc
    if completed.returncode != 0:
        raise MigrationValidationError(
            f"git status failed with exit {completed.returncode}: "
            f"{completed.stderr.decode('utf-8', 'replace').strip()}"
        )
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
