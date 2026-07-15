"""Reconcile portable loop run files into the Supervisor control store."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Any, Iterator

from scripts.harness_loop_contracts import validate_run_id
from scripts.harness_loop_runtime_lock import (
    RunLockToken,
    acquire_run_lock,
    validate_run_lock_token,
)

from .models import ActionRequest, ActionType
from .recovery import recovery_action_for_run
from .registry import transition_for
from .reviewer import schedule_due_reviews
from .safety_signals import (
    GLOBAL_SAFETY_SIGNAL_SUMMARIES,
    detected_global_safety_signals,
)
from .store import SupervisorStore


_STATE_SUMMARY_KEYS = (
    "task_id",
    "next_action",
    "last_result",
    "run_kind",
    "requirement",
    "constraints",
    "stop_conditions",
    "parent_task_counter",
    "semantic_parent_task_next",
    "_autonomous_completed_task_ids",
    "_autonomous_completed_remediation_task_ids",
    "child_run_ids",
    "aggregate_acceptance",
    "skill_roots",
    "reviewer_directives",
    "legacy_audit_migration",
    "previous_run_id",
    "commit",
    "user_decision_required",
    "unsafe_secret",
    "unsafe_secret_detected",
    "secret_detected",
    "secret_exposure_confirmed",
    "repo_corruption",
    "permission_expansion_required",
    "irreversible_operation_required",
    "explicit_global_stop",
    "supervisor_signals",
)
_FINGERPRINT_OBSERVATION_KEYS = frozenset(
    {
        "state_revision",
        "generated_at",
        "heartbeat_at",
        "last_heartbeat_at",
        "last_seen_at",
        "last_tick_at",
        "observed_at",
        "updated_at",
    }
)


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    repo_root: Path
    run_json_path: Path
    payload: dict[str, Any]
    valid: bool = True
    error: str = ""
    ownership_failure: bool = False
    directory_run_id: str = ""


@dataclass(frozen=True)
class ReconcileResult:
    queued_actions: list[ActionRequest]
    open_user_decisions: list[dict[str, Any]]
    run_records: list[RunRecord]
    shadow: bool = False

    def action_for(self, run_id: str) -> ActionRequest | None:
        return next(
            (item for item in self.queued_actions if item.run_id == run_id), None
        )

    def decision_for(self, run_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in self.open_user_decisions if item.get("run_id") == run_id),
            None,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "shadow": self.shadow,
            "run_records": len(self.run_records),
            "queued_actions": [
                {
                    "action_id": action.action_id,
                    "run_id": action.run_id,
                    "run_revision": action.run_revision,
                    "action_type": action.action_type.value,
                    "phase": action.phase,
                    "task_id": action.task_id,
                }
                for action in self.queued_actions
            ],
            "open_user_decisions": [dict(item) for item in self.open_user_decisions],
        }


def atomic_save_run(
    repo_root: Path,
    run_id: str,
    payload: Mapping[str, Any],
    *,
    expected_revision: int | None = None,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Persist one accepted run transition with a durable atomic replacement."""
    root = Path(repo_root).resolve()
    with _exclusive_run_write_lock(root, run_id) as token:
        return atomic_save_run_locked(
            root,
            run_id,
            payload,
            token=token,
            expected_revision=expected_revision,
            expected_fingerprint=expected_fingerprint,
        )


def atomic_save_run_locked(
    repo_root: Path,
    run_id: str,
    payload: Mapping[str, Any],
    *,
    token: RunLockToken,
    expected_revision: int | None = None,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Persist one run transition while a validated shared run lock is held."""
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    root = Path(repo_root).resolve()
    validate_run_id(run_id)
    validate_run_lock_token(token, root, run_id)
    declared_run_id = str(payload.get("run_id") or "")
    if declared_run_id != run_id:
        raise ValueError(
            f"run id {declared_run_id!r} does not match target directory {run_id!r}"
        )
    target = root / ".codex" / "loop-runs" / run_id / "run.json"
    _require_contained_non_symlink(target, root, allow_missing_leaf=True)
    if token.run_directory_identity is not None:
        return _atomic_save_run_locked(
            token.run_fd,
            target,
            payload,
            run_id=run_id,
            expected_revision=expected_revision,
            expected_fingerprint=expected_fingerprint,
            runs_fd=token.runs_fd,
        )
    with _open_run_directory(root, run_id, create=True):
        pass

    with _open_run_directory(root, run_id, create=False) as (
        runs_fd,
        run_fd,
    ):
        _require_same_directory_entry(runs_fd, run_id, run_fd)
        return _atomic_save_run_locked(
            run_fd,
            target,
            payload,
            run_id=run_id,
            expected_revision=expected_revision,
            expected_fingerprint=expected_fingerprint,
            runs_fd=runs_fd,
        )


def _atomic_save_run_locked(
    run_fd: int,
    target: Path,
    payload: Mapping[str, Any],
    *,
    run_id: str,
    expected_revision: int | None,
    expected_fingerprint: str | None,
    runs_fd: int,
) -> dict[str, Any]:
    current_revision = -1
    try:
        current = _read_json_object_at(run_fd, "run.json", target)
    except FileNotFoundError:
        current = None
    if current is not None:
        stored_run_id = str(current.get("run_id") or "")
        if stored_run_id != run_id:
            raise ValueError(f"run id mismatch at {target}")
        current_revision = _state_revision(current)
    if expected_revision is not None and current_revision != expected_revision:
        raise ValueError(
            f"stale run revision {expected_revision}; current is {current_revision}"
        )
    if current_revision >= 0:
        if not expected_fingerprint:
            raise ValueError("expected fingerprint is required for an existing run")
        current_fingerprint = _state_fingerprint(current)
        if current_fingerprint != expected_fingerprint:
            raise ValueError(
                "stale run fingerprint; current run state changed after discovery"
            )

    saved = dict(payload)
    saved["state_revision"] = 0 if current_revision < 0 else current_revision + 1
    temporary_name, fd = _open_temporary_at(run_fd)
    replaced = False
    try:
        handle = None
        try:
            handle = os.fdopen(fd, "w", encoding="utf-8")
            fd = -1
            json.dump(saved, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            _close_stream_preserving_error(handle)
            if fd >= 0:
                _close_fd_preserving_error(fd)
        _require_same_directory_entry(runs_fd, run_id, run_fd)
        os.replace(
            temporary_name,
            "run.json",
            src_dir_fd=run_fd,
            dst_dir_fd=run_fd,
        )
        replaced = True
        os.fsync(run_fd)
    except BaseException:
        if not replaced:
            _unlink_at_preserving_error(run_fd, temporary_name)
        raise
    return saved


@contextmanager
def _exclusive_run_write_lock(root: Path, run_id: str) -> Iterator[RunLockToken]:
    lock_path = root / ".codex" / "loop-locks" / f"{run_id}.lock"
    _require_contained_non_symlink(lock_path, root, allow_missing_leaf=True)
    with acquire_run_lock(
        root,
        run_id,
        owner="reconciler:atomic-save",
        blocking=True,
    ) as token:
        yield token


@contextmanager
def _project_reconcile_lock(root: Path) -> Iterator[int]:
    lock_path = root / ".codex" / "supervisor" / "reconcile.lock"
    _require_contained_non_symlink(lock_path, root, allow_missing_leaf=True)
    with _open_directory_chain(root, (".codex", "supervisor"), create=True) as lock_fd:
        fd = os.open(
            "reconcile.lock",
            os.O_RDWR | os.O_CREAT | _O_NOFOLLOW | _O_CLOEXEC,
            0o600,
            dir_fd=lock_fd,
        )
        _yield_locked_fd(fd)
        try:
            yield fd
        except BaseException:
            _release_locked_fd(fd, primary_exception=True)
            raise
        else:
            _release_locked_fd(fd, primary_exception=False)


_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY_FLAGS = os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC


@contextmanager
def _open_directory_chain(
    root: Path, parts: tuple[str, ...], *, create: bool
) -> Iterator[int]:
    fds: list[int] = []
    try:
        current = os.open(root, _DIRECTORY_FLAGS)
        fds.append(current)
        for part in parts:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current)
                except FileExistsError:
                    pass
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
            fds.append(child)
            current = child
        yield current
    finally:
        primary_exception = sys.exc_info()[0] is not None
        close_error: BaseException | None = None
        for fd in reversed(fds):
            try:
                os.close(fd)
            except BaseException as exc:
                if close_error is None:
                    close_error = exc
        if close_error is not None and not primary_exception:
            raise close_error


@contextmanager
def _open_run_directory(
    root: Path, run_id: str, *, create: bool
) -> Iterator[tuple[int, int]]:
    with _open_directory_chain(root, (".codex", "loop-runs"), create=create) as runs_fd:
        if create:
            try:
                os.mkdir(run_id, mode=0o700, dir_fd=runs_fd)
            except FileExistsError:
                pass
        run_fd = os.open(run_id, _DIRECTORY_FLAGS, dir_fd=runs_fd)
        try:
            yield runs_fd, run_fd
        finally:
            _close_fd_preserving_error(run_fd)


def _require_same_directory_entry(parent_fd: int, name: str, directory_fd: int) -> None:
    expected = os.fstat(directory_fd)
    actual = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(actual.st_mode) or (
        actual.st_dev,
        actual.st_ino,
    ) != (expected.st_dev, expected.st_ino):
        raise ValueError(f"run directory ownership changed: {name}")


def _open_temporary_at(directory_fd: int) -> tuple[str, int]:
    for _ in range(100):
        name = f".run.json.{os.getpid()}.{secrets.token_hex(8)}.tmp"
        try:
            fd = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW | _O_CLOEXEC,
                0o600,
                dir_fd=directory_fd,
            )
        except FileExistsError:
            continue
        return name, fd
    raise FileExistsError("could not allocate a unique run temp file")


def _yield_locked_fd(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except BaseException:
        _close_fd_preserving_error(fd)
        raise


def _release_locked_fd(fd: int, *, primary_exception: bool) -> None:
    unlock_error: BaseException | None = None
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except BaseException as exc:
        unlock_error = exc
    try:
        os.close(fd)
    except BaseException:
        if not primary_exception and unlock_error is None:
            raise
    if unlock_error is not None and not primary_exception:
        raise unlock_error


def _close_fd_preserving_error(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        if sys.exc_info()[0] is None:
            raise


def _close_stream_preserving_error(handle: Any) -> None:
    if handle is None:
        return
    try:
        handle.close()
    except BaseException:
        if sys.exc_info()[0] is None:
            raise


def _unlink_at_preserving_error(directory_fd: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=directory_fd)
    except FileNotFoundError:
        return
    except OSError:
        if sys.exc_info()[0] is None:
            raise


def discover_run_records(
    project_root: Path, *, include_worktrees: bool = True
) -> list[RunRecord]:
    """Discover root and direct non-symlink worktree runs without path escape."""
    root = Path(project_root).resolve()
    records: list[RunRecord] = []
    with _open_directory_chain(root, (), create=False) as root_fd:
        records.extend(_records_under_repo(root, root, repo_fd=root_fd))
        if include_worktrees:
            records.extend(_records_under_worktrees(root, root_fd))

    counts: dict[str, int] = {}
    for record in records:
        if record.directory_run_id:
            counts[record.directory_run_id] = counts.get(record.directory_run_id, 0) + 1
    duplicate_ids = {run_id for run_id, count in counts.items() if count > 1}
    return [
        replace(
            record,
            run_id=record.directory_run_id,
            payload={},
            valid=False,
            error=f"duplicate run directory id: {record.directory_run_id}",
            ownership_failure=True,
        )
        if record.directory_run_id in duplicate_ids
        else record
        for record in records
    ]


def infer_loop_lineages(records: Sequence[RunRecord]) -> dict[str, str]:
    """Infer stable semantic lineages for legacy continuation chains."""
    by_id = {record.run_id: record for record in records if record.valid}
    result: dict[str, str] = {}

    def has_semantic_parent_evidence(run: Mapping[str, Any]) -> bool:
        counter = run.get("parent_task_counter")
        if isinstance(counter, int) and not isinstance(counter, bool) and counter > 0:
            return True
        values: list[str] = []
        for key in ("completed_semantic_parent_ids", "semantic_parent_ids", "_autonomous_completed_task_ids"):
            raw = run.get(key)
            if isinstance(raw, list):
                values.extend(str(value) for value in raw if isinstance(value, str))
        return any(re.search(r"parent-(\d+)", value) for value in values)

    def resolve(run_id: str, trail: frozenset[str] = frozenset()) -> str:
        if run_id in result:
            return result[run_id]
        if run_id in trail:
            return run_id
        record = by_id[run_id]
        explicit = str(record.payload.get("loop_lineage_id") or "")
        if explicit:
            result[run_id] = explicit
            return explicit
        previous = str(record.payload.get("previous_run_id") or "")
        if previous not in by_id:
            result[run_id] = run_id
            return run_id
        lineage = resolve(previous, trail | {run_id})
        if has_semantic_parent_evidence(record.payload) and not has_semantic_parent_evidence(
            by_id[previous].payload
        ):
            lineage = run_id
        result[run_id] = lineage
        return lineage

    for run_id in by_id:
        resolve(run_id)
    return result


def _records_under_worktrees(root: Path, root_fd: int) -> list[RunRecord]:
    worktrees_root = root / ".worktrees"
    try:
        root_stat = os.stat(".worktrees", dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return []
    if stat.S_ISLNK(root_stat.st_mode):
        return [_ownership_record(worktrees_root, root, "worktrees root is a symlink")]
    if not stat.S_ISDIR(root_stat.st_mode):
        return []
    try:
        worktrees_fd = os.open(".worktrees", _DIRECTORY_FLAGS, dir_fd=root_fd)
    except OSError as exc:
        return [
            _ownership_record(worktrees_root, root, f"unsafe worktrees root: {exc}")
        ]
    records: list[RunRecord] = []
    try:
        if not _same_open_directory(root_stat, worktrees_fd):
            return [
                _ownership_record(
                    worktrees_root, root, "worktrees root ownership changed"
                )
            ]
        for name in sorted(os.listdir(worktrees_fd)):
            worktree = worktrees_root / name
            try:
                child_stat = os.stat(name, dir_fd=worktrees_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(child_stat.st_mode):
                records.append(
                    _ownership_record(worktree, root, "worktree is a symlink")
                )
                continue
            if not stat.S_ISDIR(child_stat.st_mode):
                continue
            try:
                child_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=worktrees_fd)
            except OSError as exc:
                records.append(
                    _ownership_record(
                        worktree, root, f"unsafe worktree directory: {exc}"
                    )
                )
                continue
            try:
                if not _same_open_directory(child_stat, child_fd):
                    records.append(
                        _ownership_record(
                            worktree, root, "worktree directory ownership changed"
                        )
                    )
                    continue
                records.extend(_records_under_repo(worktree, root, repo_fd=child_fd))
            finally:
                _close_fd_preserving_error(child_fd)
    finally:
        _close_fd_preserving_error(worktrees_fd)
    return records


def desired_action_for_run(run: Mapping[str, Any]) -> ActionRequest | None:
    """Return one registry-backed bounded action for a run state."""
    if not isinstance(run, Mapping):
        raise TypeError("run must be a mapping")
    run_id = str(run.get("run_id") or "")
    policy = str(run.get("policy") or "")
    phase = str(run.get("phase") or "")
    next_action = str(run.get("next_action") or "")
    rule = transition_for(policy, phase, next_action)
    if rule.terminal:
        return None

    revision = _state_revision(run)
    task_id = str(run.get("task_id") or "")
    payload: dict[str, Any] = {
        "next_action": next_action,
        "mutates_git": rule.mutates_git,
    }
    if rule.action_type is ActionType.CREATE_CONTINUATION:
        continuation_identity = _continuation_identity(run)
        payload["continuation_identity"] = continuation_identity
        task_id = "continuation:" + ":".join(continuation_identity.values())

    identity = {
        "project": str(
            run.get("_supervisor_project_root")
            or run.get("project_root")
            or run.get("worktree")
            or ""
        ),
        "run_id": run_id,
        "revision": revision,
        "policy": policy,
        "phase": phase,
        "action_type": rule.action_type.value,
        "task_id": task_id,
        "repo_relative_root": str(run.get("_supervisor_repo_relative_root") or "."),
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ActionRequest(
        action_id=f"action-{digest[:24]}",
        run_id=run_id,
        run_revision=revision,
        policy=policy,
        phase=phase,
        action_type=rule.action_type,
        idempotency_key=f"reconcile:{digest}",
        repo_relative_root=identity["repo_relative_root"],
        task_id=task_id,
        next_action=next_action,
        payload=payload,
    )


def reconcile_once(
    project_root: Path,
    store: SupervisorStore,
    *,
    shadow: bool = False,
    include_worktrees: bool = True,
) -> ReconcileResult:
    """Project run files, open scoped decisions, and enqueue one action per leaf run."""
    root = Path(project_root).resolve()
    if store.project_root != root:
        raise ValueError("store project root does not match reconciliation root")
    with _project_reconcile_lock(root):
        with ExitStack() as run_locks:
            return _reconcile_once_locked(
                root,
                store,
                shadow=shadow,
                include_worktrees=include_worktrees,
                run_locks=run_locks,
            )


def _secure_reread_run(project_root: Path, record: RunRecord) -> RunRecord:
    run_dir = record.repo_root / ".codex" / "loop-runs" / record.run_id
    try:
        with _open_run_directory(record.repo_root, record.run_id, create=False) as (
            runs_fd,
            run_fd,
        ):
            _require_same_directory_entry(runs_fd, record.run_id, run_fd)
            refreshed = _record_from_run_fd(
                record.repo_root,
                project_root,
                run_dir,
                run_fd,
            )
    except (OSError, PermissionError, ValueError) as exc:
        ownership = isinstance(exc, PermissionError) or "ownership" in str(exc)
        return RunRecord(
            run_id=record.run_id,
            repo_root=record.repo_root,
            run_json_path=run_dir / "run.json",
            payload={},
            valid=False,
            error=f"secure run reread failed: {exc}",
            ownership_failure=ownership,
            directory_run_id=record.run_id,
        )
    if refreshed is not None:
        return refreshed
    return RunRecord(
        run_id=record.run_id,
        repo_root=record.repo_root,
        run_json_path=run_dir / "run.json",
        payload={},
        valid=False,
        error="secure run reread found no run.json",
        directory_run_id=record.run_id,
    )


def _record_invalid_run_decision(
    store: SupervisorStore,
    record: RunRecord,
    decisions: list[dict[str, Any]],
) -> None:
    scope = "global" if record.ownership_failure else "run"
    failure_key = _failure_key(scope, record.run_id, record.error)
    _record_failure_once(
        store,
        failure_key,
        run_id=record.run_id if scope == "run" else "",
        error_class="repository_ownership" if scope == "global" else "invalid_json",
        summary=record.error,
    )
    opened = store.open_user_decision(
        scope=scope,
        run_id=record.run_id,
        failure_key=failure_key,
        summary=record.error,
        required_decision=(
            "Restore trustworthy repository ownership before reconciliation."
            if scope == "global"
            else "Repair or archive the invalid run file."
        ),
    )
    if not any(
        item.get("decision_id") == opened.get("decision_id") for item in decisions
    ):
        decisions.append(opened)


def _reconcile_once_locked(
    root: Path,
    store: SupervisorStore,
    *,
    shadow: bool,
    include_worktrees: bool,
    run_locks: ExitStack,
) -> ReconcileResult:
    existing_decisions = store.fetch_all("user_decisions")
    open_decisions_by_id = {
        str(item["decision_id"]): item
        for item in existing_decisions
        if item.get("status") == "open"
    }
    archived_legacy_run_ids = {
        str(item.get("run_id") or "")
        for item in existing_decisions
        if item.get("status") == "closed"
        and item.get("resolution") == "archived during legacy migration"
        and str(item.get("failure_key") or "").startswith("unsupported_state:")
    }
    records = discover_run_records(root, include_worktrees=include_worktrees)
    inferred_lineages = infer_loop_lineages(records)
    valid_records: list[RunRecord] = []
    decisions: list[dict[str, Any]] = []
    tokens_by_run: dict[str, RunLockToken] = {}

    ordered_records = sorted(
        enumerate(records),
        key=lambda item: (
            str(item[1].repo_root.resolve()),
            item[1].directory_run_id,
        ),
    )
    for index, record in ordered_records:
        if not record.valid and (
            record.ownership_failure or not record.directory_run_id
        ):
            _record_invalid_run_decision(store, record, decisions)
            continue
        try:
            token = run_locks.enter_context(
                acquire_run_lock(
                    record.repo_root,
                    record.directory_run_id,
                    owner="reconciler:project-run",
                    blocking=True,
                )
            )
            if record.run_id != record.directory_run_id:
                record = replace(record, run_id=record.directory_run_id)
            record = _secure_reread_run(root, record)
            records[index] = record
            if not record.valid:
                _record_invalid_run_decision(store, record, decisions)
                continue
            projected = _project_run(
                root,
                store,
                record,
                token=token,
                loop_lineage_id=inferred_lineages.get(record.run_id, record.run_id),
            )
            tokens_by_run[projected.run_id] = token
        except (OSError, TypeError, ValueError) as exc:
            failure_key = _failure_key("run", record.run_id, str(exc))
            _record_failure_once(
                store,
                failure_key,
                run_id=record.run_id,
                error_class="invalid_run_state",
                summary=str(exc),
            )
            decisions.append(
                store.open_user_decision(
                    scope="run",
                    run_id=record.run_id,
                    failure_key=failure_key,
                    summary=str(exc),
                    required_decision="Repair or archive the invalid run state.",
                )
            )
            continue
        valid_records.append(projected)

    desired_by_run: dict[str, ActionRequest | None] = {}
    observed_decision_keys = {str(item.get("failure_key") or "") for item in decisions}
    for record in valid_records:
        run = record.payload
        try:
            desired_by_run[record.run_id] = desired_action_for_run(
                {
                    **run,
                    "_supervisor_project_root": str(root),
                    "_supervisor_repo_relative_root": record.repo_root.relative_to(root).as_posix(),
                }
            )
        except (TypeError, ValueError) as exc:
            failure_key = _failure_key("run", record.run_id, str(exc))
            _record_failure_once(
                store,
                failure_key,
                run_id=record.run_id,
                error_class="unsupported_transition",
                summary=str(exc),
            )
            decisions.append(
                store.open_user_decision(
                    scope="run",
                    run_id=record.run_id,
                    failure_key=failure_key,
                    summary=str(exc),
                    required_decision="Move the run to a registry-supported state.",
                )
            )
            observed_decision_keys.add(failure_key)
            desired_by_run[record.run_id] = None
            continue

        action = desired_by_run[record.run_id]
        if (
            action is not None
            and action.action_type is ActionType.ASK_USER
            and record.run_id in archived_legacy_run_ids
            and run.get("phase") == "stopped_blocked"
            and run.get("next_action") == "inspect_blocked_diagnostics"
        ):
            desired_by_run[record.run_id] = None
            continue

        decision = _decision_requirement(run)
        if decision is None:
            action = desired_by_run[record.run_id]
            if action is not None and action.action_type is ActionType.ASK_USER:
                decision = (
                    "run",
                    "registry_user_gate",
                    "The current registry transition requires a user decision.",
                )
        if decision is None:
            continue
        scope, reason, summary = decision
        failure_key = f"reconcile:{scope}:{_safe_slug(record.run_id)}:{reason}"
        _record_failure_once(
            store,
            failure_key,
            run_id=record.run_id if scope == "run" else "",
            error_class=reason,
            summary=summary,
        )
        decisions.append(
            store.open_user_decision(
                scope=scope,
                run_id=record.run_id,
                failure_key=failure_key,
                summary=summary,
                required_decision="Resolve the safety or run gate before this run advances.",
            )
        )
        observed_decision_keys.add(failure_key)
        desired_by_run[record.run_id] = None

    for decision in store.fetch_all("user_decisions"):
        failure_key = str(decision.get("failure_key") or "")
        if (
            decision.get("status") == "open"
            and failure_key.startswith("reconcile:")
            and failure_key not in observed_decision_keys
        ):
            closed = store.close_user_decision(
                str(decision["decision_id"]),
                resolution="reconciliation condition cleared",
                expected_updated_at=str(decision["updated_at"]),
            )
            if closed is None:
                continue
            failure = next(
                (
                    item
                    for item in store.fetch_all("failures")
                    if item.get("failure_key") == failure_key
                ),
                None,
            )
            if failure is not None and failure.get("resolution") == "open":
                store.record_failure(
                    failure_key,
                    run_id=str(failure.get("run_id") or ""),
                    task_id=str(failure.get("task_id") or ""),
                    error_class=str(failure.get("error_class") or ""),
                    summary=str(failure.get("summary") or ""),
                    resolution="resolved",
                )

    for item in store.fetch_all("user_decisions"):
        decision_id = str(item["decision_id"])
        if item.get("status") == "open":
            open_decisions_by_id[decision_id] = item
        else:
            open_decisions_by_id.pop(decision_id, None)
    current_open_decisions = list(open_decisions_by_id.values())
    global_stop = any(item.get("scope") == "global" for item in current_open_decisions)
    blocked_run_ids = {
        str(item.get("run_id") or "")
        for item in current_open_decisions
        if item.get("scope") == "run"
    }
    child_sources = {
        str(
            record.payload.get("previous_run_id")
            or record.payload.get("parent_run_id")
            or ""
        )
        for record in valid_records
    }
    payload_by_run = {record.run_id: record.payload for record in valid_records}
    queued: list[ActionRequest] = []
    if not global_stop:
        for record in valid_records:
            if record.run_id in blocked_run_ids:
                continue
            if record.payload.get("run_kind") == "child":
                parent_id = str(record.payload.get("parent_run_id") or "")
                parent = payload_by_run.get(parent_id)
                child_ids = (
                    parent.get("child_run_ids", [])
                    if isinstance(parent, Mapping)
                    else []
                )
                if not (
                    isinstance(parent, Mapping)
                    and parent.get("run_kind") == "parent"
                    and parent.get("phase") == "child_running"
                    and record.run_id in child_ids
                    and parent.get("current_child_run_id") == record.run_id
                ):
                    continue
            action = desired_by_run.get(record.run_id)
            if action is None:
                continue
            if record.payload.get("run_kind") == "parent" and record.payload.get(
                "phase"
            ) == "child_running":
                child_id = str(record.payload.get("current_child_run_id") or "")
                child = payload_by_run.get(child_id)
                if child is None or child.get("phase") != "passed":
                    continue
            if (
                action.action_type is ActionType.CREATE_CONTINUATION
                and record.run_id in child_sources
            ):
                continue
            record = next(item for item in valid_records if item.run_id == record.run_id)
            action = recovery_action_for_run(store, record.payload, action)
            if action is None:
                continue
            store.enqueue_action(
                action,
                recovery_tier=int(action.payload.get("recovery_tier", 0)),
                expected_run_fingerprint=_state_fingerprint(record.payload),
                run_lock_token=tokens_by_run[record.run_id],
            )
            queued.append(action)

        queued.extend(schedule_due_reviews(store, now=store.current_time()))

    return ReconcileResult(
        queued_actions=queued,
        open_user_decisions=decisions,
        run_records=records,
        shadow=shadow,
    )


def _records_under_repo(
    repo_root: Path, project_root: Path, *, repo_fd: int
) -> list[RunRecord]:
    runs_root = repo_root / ".codex" / "loop-runs"
    try:
        codex_stat = os.stat(".codex", dir_fd=repo_fd, follow_symlinks=False)
    except FileNotFoundError:
        return []
    if stat.S_ISLNK(codex_stat.st_mode):
        return [
            _ownership_record(repo_root / ".codex", repo_root, ".codex is a symlink")
        ]
    if not stat.S_ISDIR(codex_stat.st_mode):
        return []
    try:
        codex_fd = os.open(".codex", _DIRECTORY_FLAGS, dir_fd=repo_fd)
    except OSError as exc:
        return [_ownership_record(repo_root / ".codex", repo_root, str(exc))]
    try:
        if not _same_open_directory(codex_stat, codex_fd):
            return [
                _ownership_record(
                    repo_root / ".codex", repo_root, ".codex ownership changed"
                )
            ]
        try:
            runs_stat = os.stat("loop-runs", dir_fd=codex_fd, follow_symlinks=False)
        except FileNotFoundError:
            return []
        if stat.S_ISLNK(runs_stat.st_mode):
            return [
                _ownership_record(runs_root, repo_root, "loop-runs root is a symlink")
            ]
        if not stat.S_ISDIR(runs_stat.st_mode):
            return []
        try:
            runs_fd = os.open("loop-runs", _DIRECTORY_FLAGS, dir_fd=codex_fd)
        except OSError as exc:
            return [_ownership_record(runs_root, repo_root, str(exc))]
        try:
            if not _same_open_directory(runs_stat, runs_fd):
                return [
                    _ownership_record(
                        runs_root, repo_root, "loop-runs root ownership changed"
                    )
                ]
            return _records_under_runs_fd(repo_root, project_root, runs_root, runs_fd)
        finally:
            _close_fd_preserving_error(runs_fd)
    finally:
        _close_fd_preserving_error(codex_fd)


def _records_under_runs_fd(
    repo_root: Path,
    project_root: Path,
    runs_root: Path,
    runs_fd: int,
) -> list[RunRecord]:
    records: list[RunRecord] = []
    for name in sorted(os.listdir(runs_fd)):
        run_dir = runs_root / name
        try:
            run_stat = os.stat(name, dir_fd=runs_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(run_stat.st_mode):
            records.append(
                _ownership_record(
                    run_dir,
                    repo_root,
                    "run directory is a symlink",
                    directory_run_id=name,
                )
            )
            continue
        if not stat.S_ISDIR(run_stat.st_mode):
            continue
        try:
            run_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=runs_fd)
        except OSError as exc:
            records.append(
                _ownership_record(
                    run_dir,
                    repo_root,
                    f"unsafe run directory: {exc}",
                    directory_run_id=name,
                )
            )
            continue
        try:
            if not _same_open_directory(run_stat, run_fd):
                records.append(
                    _ownership_record(
                        run_dir,
                        repo_root,
                        "run directory ownership changed",
                        directory_run_id=name,
                    )
                )
                continue
            record = _record_from_run_fd(
                repo_root,
                project_root,
                run_dir,
                run_fd,
            )
            if record is not None:
                records.append(record)
        finally:
            _close_fd_preserving_error(run_fd)
    return records


def _record_from_run_fd(
    repo_root: Path,
    project_root: Path,
    run_dir: Path,
    run_fd: int,
) -> RunRecord | None:
    path = run_dir / "run.json"
    name = run_dir.name
    try:
        file_stat = os.stat("run.json", dir_fd=run_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(file_stat.st_mode):
        return _ownership_record(
            path, repo_root, "run.json is a symlink", directory_run_id=name
        )
    if not stat.S_ISREG(file_stat.st_mode):
        return _ownership_record(
            path, repo_root, "run.json is not a regular file", directory_run_id=name
        )
    try:
        _require_contained_non_symlink(path, project_root)
        payload = _read_json_object_at(run_fd, "run.json", path)
        declared_run_id = payload.get("run_id")
        if not isinstance(declared_run_id, str) or declared_run_id != name:
            raise PermissionError(
                f"run id {declared_run_id!r} does not match directory {name!r}"
            )
        validate_run_id(declared_run_id)
        declared_worktree = payload.get("worktree")
        if isinstance(declared_worktree, str) and declared_worktree:
            declared_path = Path(declared_worktree)
            if not declared_path.is_absolute():
                declared_path = repo_root / declared_path
            if declared_path.resolve() != repo_root.resolve():
                raise PermissionError("run declares a different repository owner")
        return RunRecord(
            run_id=declared_run_id,
            repo_root=repo_root,
            run_json_path=path,
            payload=payload,
            directory_run_id=name,
        )
    except PermissionError as exc:
        return _ownership_record(path, repo_root, str(exc), directory_run_id=name)
    except ValueError as exc:
        ownership = "symlink" in str(exc) or "escape" in str(exc) or "owner" in str(exc)
        return RunRecord(
            run_id=name,
            repo_root=repo_root,
            run_json_path=path,
            payload={},
            valid=False,
            error=str(exc),
            ownership_failure=ownership,
            directory_run_id=name,
        )
    except OSError as exc:
        ownership = exc.errno in {errno.EACCES, errno.ELOOP, errno.ENOTDIR, errno.EPERM}
        return RunRecord(
            run_id=name,
            repo_root=repo_root,
            run_json_path=path,
            payload={},
            valid=False,
            error=(
                f"unsafe run.json ownership: {exc}"
                if ownership
                else f"invalid run JSON: {exc}"
            ),
            ownership_failure=ownership,
            directory_run_id=name,
        )


def _same_open_directory(expected: os.stat_result, directory_fd: int) -> bool:
    actual = os.fstat(directory_fd)
    return stat.S_ISDIR(actual.st_mode) and (actual.st_dev, actual.st_ino) == (
        expected.st_dev,
        expected.st_ino,
    )


def _project_run(
    project_root: Path,
    store: SupervisorStore,
    record: RunRecord,
    *,
    token: RunLockToken,
    loop_lineage_id: str = "",
) -> RunRecord:
    run = dict(record.payload)
    if run.get("phase") in {"audit_pending", "auditing", "audit_blocked"}:
        run = _migrate_legacy_audit_state(run)
        run = atomic_save_run_locked(
            record.repo_root,
            record.run_id,
            run,
            token=token,
            expected_revision=_state_revision(record.payload),
            expected_fingerprint=_state_fingerprint(record.payload),
        )
        record = RunRecord(
            run_id=record.run_id,
            repo_root=record.repo_root,
            run_json_path=record.run_json_path,
            payload=run,
            directory_run_id=record.directory_run_id,
        )
    incoming_revision = _state_revision(run)
    projection = _projection(project_root, record, run, incoming_revision)
    try:
        existing = store.get_run(record.run_id)
    except KeyError:
        store.upsert_run_projection(projection)
        return record

    current_revision = int(existing["revision"])
    if incoming_revision < current_revision:
        raise ValueError(
            f"stale run revision {incoming_revision}; current is {current_revision}"
        )
    if incoming_revision > current_revision + 1:
        raise ValueError(
            f"run revision jumped from {current_revision} to {incoming_revision}"
        )
    if incoming_revision == current_revision and not _same_projection(
        existing, projection
    ):
        if "state_revision" in run:
            raise ValueError("same-revision run state conflict")
        run = atomic_save_run_locked(
            record.repo_root,
            record.run_id,
            run,
            token=token,
            expected_revision=current_revision,
            expected_fingerprint=_state_fingerprint(record.payload),
        )
        incoming_revision = int(run["state_revision"])
        projection = _projection(
            project_root,
            record,
            run,
            incoming_revision,
            loop_lineage_id=loop_lineage_id,
        )
        record = RunRecord(
            run_id=record.run_id,
            repo_root=record.repo_root,
            run_json_path=record.run_json_path,
            payload=run,
            directory_run_id=record.directory_run_id,
        )
    store.upsert_run_projection(projection)
    return record


def _migrate_legacy_audit_state(run: Mapping[str, Any]) -> dict[str, Any]:
    migrated = dict(run)
    source_phase = str(migrated.get("phase") or "")
    decision = "auto_remediate" if source_phase == "audit_blocked" else "refocus"
    existing_directives = migrated.get("reviewer_directives", [])
    if not isinstance(existing_directives, list):
        raise ValueError("reviewer_directives must be a list")
    directives = list(existing_directives)
    migrated["reviewer_directives"] = directives
    directive = {
        "review_id": "legacy-audit-migration",
        "decision": decision,
        "summary": f"Migrated legacy {source_phase} state into Supervisor planning.",
        "evidence_refs": [],
    }
    if directive not in directives:
        directives.append(directive)
    migrated["legacy_audit_migration"] = {
        "source_phase": source_phase,
        "source_next_action": str(migrated.get("next_action") or ""),
        "status": "migrated",
    }
    migrated["phase"] = "planning"
    migrated["next_action"] = (
        "run_autonomous_planner"
        if migrated.get("policy") == "autonomous_knowledge"
        else "run_parent_planner"
    )
    migrated["last_result"] = "none"
    return migrated


def _projection(
    project_root: Path,
    record: RunRecord,
    run: Mapping[str, Any],
    revision: int,
    *,
    loop_lineage_id: str = "",
) -> dict[str, Any]:
    policy = str(run.get("policy") or "")
    phase = str(run.get("phase") or "")
    next_action = str(run.get("next_action") or "")
    rule = transition_for(policy, phase, next_action)
    status = "terminal" if rule.terminal else "actionable"
    summary = json.dumps(
        {key: run.get(key) for key in _STATE_SUMMARY_KEYS},
        sort_keys=True,
        separators=(",", ":"),
    )
    artifact_ref = record.run_json_path.resolve().relative_to(project_root).as_posix()
    return {
        "run_id": record.run_id,
        "revision": revision,
        "repo_relative_root": record.repo_root.resolve().relative_to(project_root).as_posix()
        or ".",
        "state_fingerprint": _state_fingerprint(run),
        "loop_lineage_id": str(
            run.get("loop_lineage_id") or loop_lineage_id or record.run_id
        ),
        "parent_run_id": str(
            run.get("previous_run_id") or run.get("parent_run_id") or ""
        ),
        "policy": policy,
        "phase": phase,
        "status": status,
        "summary": summary,
        "artifact_refs": [artifact_ref],
    }


def _same_projection(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> bool:
    stored_summary = existing.get("summary")
    if not isinstance(stored_summary, Mapping):
        return False
    return (
        str(existing.get("loop_lineage_id") or "")
        == str(incoming.get("loop_lineage_id") or "")
        and str(existing.get("parent_run_id") or "")
        == str(incoming.get("parent_run_id") or "")
        and str(existing.get("policy") or "") == str(incoming.get("policy") or "")
        and str(existing.get("phase") or "") == str(incoming.get("phase") or "")
        and str(existing.get("status") or "") == str(incoming.get("status") or "")
        and str(existing.get("repo_relative_root") or ".")
        == str(incoming.get("repo_relative_root") or ".")
        and (
            not str(existing.get("state_fingerprint") or "")
            or str(existing.get("state_fingerprint"))
            == str(incoming.get("state_fingerprint") or "")
        )
        and stored_summary.get("summary") == incoming.get("summary")
        and stored_summary.get("artifact_refs") == incoming.get("artifact_refs")
    )


def _decision_requirement(run: Mapping[str, Any]) -> tuple[str, str, str] | None:
    global_signals = detected_global_safety_signals(run)
    if global_signals:
        signal = global_signals[0]
        return "global", signal, GLOBAL_SAFETY_SIGNAL_SUMMARIES[signal]
    if run.get("user_decision_required") is True:
        return "run", "user_decision_required", "This run requires a user decision."
    return None


def _continuation_identity(run: Mapping[str, Any]) -> dict[str, str]:
    run_id = str(run.get("run_id") or "")
    lineage_id = str(run.get("loop_lineage_id") or run_id)
    parent = _semantic_parent(run)
    commit = _source_commit(run)
    return {
        "loop_lineage_id": lineage_id,
        "source_run_id": run_id,
        "semantic_parent": parent,
        "source_commit": commit,
    }


def _semantic_parent(run: Mapping[str, Any]) -> str:
    counter = run.get("parent_task_counter")
    if isinstance(counter, int) and not isinstance(counter, bool) and counter >= 0:
        return f"parent-{counter}"
    for value in (run.get("task_id"), run.get("run_id")):
        match = re.search(r"parent-(\d+)", str(value or ""))
        if match:
            return f"parent-{match.group(1)}"
    return "parent-0"


def _source_commit(run: Mapping[str, Any]) -> str:
    for key in ("commit", "git_head", "head", "previous_commit"):
        value = run.get(key)
        if isinstance(value, str) and value:
            return value
    identity = {
        "run_id": run.get("run_id"),
        "task_id": run.get("task_id"),
        "phase": run.get("phase"),
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"run-identity-{digest[:12]}"


def _state_revision(run: Mapping[str, Any]) -> int:
    value = run.get("state_revision", 0)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("state_revision must be an int")
    if value < 0:
        raise ValueError("state_revision must be non-negative")
    return value


def _state_fingerprint(run: Mapping[str, Any]) -> str:
    state = {
        key: value
        for key, value in run.items()
        if key not in _FINGERPRINT_OBSERVATION_KEYS
    }
    canonical_state = _canonical_json_value(state)
    encoded = json.dumps(
        canonical_state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _canonical_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical mapping keys must be strings")
        return {key: _canonical_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_json_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON numbers must be finite")
        return int(value) if value.is_integer() else value
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle, parse_constant=_reject_json_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid run JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("run JSON must contain an object")
    return value


def _read_json_object_at(
    directory_fd: int, name: str, display_path: Path
) -> dict[str, Any]:
    fd = os.open(name, os.O_RDONLY | _O_NOFOLLOW | _O_CLOEXEC, dir_fd=directory_fd)
    handle = None
    try:
        handle = os.fdopen(fd, "r", encoding="utf-8")
        fd = -1
        try:
            value = json.load(handle, parse_constant=_reject_json_constant)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid run JSON: {exc}") from exc
    finally:
        _close_stream_preserving_error(handle)
        if fd >= 0:
            _close_fd_preserving_error(fd)
    if not isinstance(value, dict):
        raise ValueError(f"run JSON must contain an object: {display_path}")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid run JSON number: {value}")


def _require_contained_non_symlink(
    path: Path,
    root: Path,
    *,
    allow_missing_leaf: bool = False,
) -> None:
    root = Path(root).resolve()
    candidate = Path(path)
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {candidate}") from exc
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {candidate}") from exc
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"path traverses symlink: {current}")
        is_leaf = index == len(relative.parts) - 1
        if not current.exists() and not (allow_missing_leaf and is_leaf):
            continue


def _ownership_record(
    path: Path,
    repo_root: Path,
    error: str,
    *,
    directory_run_id: str = "",
) -> RunRecord:
    return RunRecord(
        run_id=f"ownership-{_safe_slug(path.name)}",
        repo_root=repo_root,
        run_json_path=path,
        payload={},
        valid=False,
        error=error,
        ownership_failure=True,
        directory_run_id=directory_run_id,
    )


def _failure_key(scope: str, run_id: str, error: str) -> str:
    digest = hashlib.sha256(error.encode("utf-8")).hexdigest()[:12]
    return f"reconcile:{scope}:{_safe_slug(run_id)}:{digest}"


def _record_failure_once(
    store: SupervisorStore,
    failure_key: str,
    *,
    run_id: str,
    error_class: str,
    summary: str,
) -> None:
    existing = next(
        (
            item
            for item in store.fetch_all("failures")
            if item["failure_key"] == failure_key
        ),
        None,
    )
    if existing is None or existing.get("resolution") != "open":
        store.record_failure(
            failure_key,
            run_id=run_id,
            error_class=error_class,
            summary=summary,
        )


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    return re.sub(r"-+", "-", normalized).strip("-") or "unknown"
