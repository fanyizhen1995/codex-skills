"""Reconcile portable loop run files into the Supervisor control store."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from scripts.harness_loop_contracts import validate_run_id

from .models import ActionRequest, ActionType
from .registry import transition_for
from .store import SupervisorStore


_GLOBAL_DECISION_SIGNALS = {
    "repo_corruption": "repository corruption prevents trustworthy ownership checks",
    "permission_expansion_required": "required permission expansion affects the project",
    "irreversible_operation_required": "irreversible operation requires approval",
    "explicit_global_stop": "explicit global stop requested",
}
_SECRET_SIGNAL_KEYS = {
    "unsafe_secret",
    "unsafe_secret_detected",
    "secret_detected",
    "secret_exposure_confirmed",
}
_STATE_SUMMARY_KEYS = (
    "task_id",
    "next_action",
    "last_result",
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


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    repo_root: Path
    run_json_path: Path
    payload: dict[str, Any]
    valid: bool = True
    error: str = ""
    ownership_failure: bool = False


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
    payload: Mapping[str, Any],
    *,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    """Persist one accepted run transition with a durable atomic replacement."""
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    root = Path(repo_root).resolve()
    run_id = str(payload.get("run_id") or "")
    validate_run_id(run_id)
    target = root / ".codex" / "loop-runs" / run_id / "run.json"
    _require_contained_non_symlink(target, root, allow_missing_leaf=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    _require_contained_non_symlink(target.parent, root)

    current_revision = -1
    if target.exists():
        current = _read_json_object(target)
        stored_run_id = str(current.get("run_id") or "")
        if stored_run_id != run_id:
            raise ValueError(f"run id mismatch at {target}")
        current_revision = _state_revision(current)
    if expected_revision is not None and current_revision != expected_revision:
        raise ValueError(
            f"stale run revision {expected_revision}; current is {current_revision}"
        )

    saved = dict(payload)
    saved["state_revision"] = 0 if current_revision < 0 else current_revision + 1
    fd, temporary_name = tempfile.mkstemp(
        prefix=".run.json.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(saved, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(
            target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return saved


def discover_run_records(project_root: Path) -> list[RunRecord]:
    """Discover root and direct non-symlink worktree runs without path escape."""
    root = Path(project_root).resolve()
    records: list[RunRecord] = []
    records.extend(_records_under_repo(root, root))
    worktrees_root = root / ".worktrees"
    if worktrees_root.exists():
        if worktrees_root.is_symlink():
            records.append(
                _ownership_record(worktrees_root, root, "worktrees root is a symlink")
            )
        else:
            for worktree in sorted(
                worktrees_root.iterdir(), key=lambda item: item.name
            ):
                if worktree.is_symlink():
                    records.append(
                        _ownership_record(worktree, root, "worktree is a symlink")
                    )
                    continue
                if not worktree.is_dir():
                    continue
                try:
                    _require_contained_non_symlink(worktree, worktrees_root)
                except ValueError as exc:
                    records.append(_ownership_record(worktree, root, str(exc)))
                    continue
                records.extend(_records_under_repo(worktree.resolve(), root))

    seen: dict[str, RunRecord] = {}
    result: list[RunRecord] = []
    for record in records:
        if not record.valid:
            result.append(record)
            continue
        previous = seen.get(record.run_id)
        if previous is not None:
            result.append(
                RunRecord(
                    run_id=record.run_id,
                    repo_root=record.repo_root,
                    run_json_path=record.run_json_path,
                    payload={},
                    valid=False,
                    error=f"duplicate run id also owned by {previous.run_json_path}",
                    ownership_failure=True,
                )
            )
            continue
        seen[record.run_id] = record
        result.append(record)
    return result


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
        task_id=task_id,
        next_action=next_action,
        payload=payload,
    )


def reconcile_once(
    project_root: Path,
    store: SupervisorStore,
    *,
    shadow: bool = False,
) -> ReconcileResult:
    """Project run files, open scoped decisions, and enqueue one action per leaf run."""
    root = Path(project_root).resolve()
    if store.project_root != root:
        raise ValueError("store project root does not match reconciliation root")
    records = discover_run_records(root)
    valid_records: list[RunRecord] = []
    decisions: list[dict[str, Any]] = []

    for record in records:
        if not record.valid:
            scope = "global" if record.ownership_failure else "run"
            failure_key = _failure_key(scope, record.run_id, record.error)
            _record_failure_once(
                store,
                failure_key,
                run_id=record.run_id if scope == "run" else "",
                error_class="repository_ownership"
                if scope == "global"
                else "invalid_json",
                summary=record.error,
            )
            decisions.append(
                store.open_user_decision(
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
            )
            continue
        try:
            projected = _project_run(root, store, record)
        except (TypeError, ValueError) as exc:
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
                {**run, "_supervisor_project_root": str(root)}
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
            store.close_user_decision(
                str(decision["decision_id"]),
                resolution="reconciliation condition cleared",
            )
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

    global_stop = any(item.get("scope") == "global" for item in decisions) or any(
        item.get("scope") == "global" and item.get("status") == "open"
        for item in store.fetch_all("user_decisions")
    )
    child_sources = {
        str(
            record.payload.get("previous_run_id")
            or record.payload.get("parent_run_id")
            or ""
        )
        for record in valid_records
    }
    queued: list[ActionRequest] = []
    if not global_stop:
        for record in valid_records:
            action = desired_by_run.get(record.run_id)
            if action is None:
                continue
            if (
                action.action_type is ActionType.CREATE_CONTINUATION
                and record.run_id in child_sources
            ):
                continue
            store.enqueue_action(action)
            queued.append(action)

    return ReconcileResult(
        queued_actions=queued,
        open_user_decisions=decisions,
        run_records=records,
        shadow=shadow,
    )


def _records_under_repo(repo_root: Path, project_root: Path) -> list[RunRecord]:
    runs_root = repo_root / ".codex" / "loop-runs"
    if not runs_root.exists():
        return []
    try:
        _require_contained_non_symlink(runs_root, project_root)
    except ValueError as exc:
        return [_ownership_record(runs_root, repo_root, str(exc))]
    records: list[RunRecord] = []
    for run_dir in sorted(runs_root.iterdir(), key=lambda item: item.name):
        if not run_dir.is_dir() and not run_dir.is_symlink():
            continue
        path = run_dir / "run.json"
        if not path.exists() and not path.is_symlink():
            continue
        try:
            _require_contained_non_symlink(path, repo_root)
            payload = _read_json_object(path)
            run_id = str(payload.get("run_id") or run_dir.name)
            validate_run_id(run_id)
            declared_worktree = payload.get("worktree")
            if isinstance(declared_worktree, str) and declared_worktree:
                declared_path = Path(declared_worktree)
                if not declared_path.is_absolute():
                    declared_path = repo_root / declared_path
                if declared_path.resolve() != repo_root.resolve():
                    raise PermissionError("run declares a different repository owner")
            records.append(
                RunRecord(
                    run_id=run_id,
                    repo_root=repo_root,
                    run_json_path=path,
                    payload=payload,
                )
            )
        except PermissionError as exc:
            records.append(_ownership_record(path, repo_root, str(exc)))
        except ValueError as exc:
            ownership = (
                "symlink" in str(exc) or "escape" in str(exc) or "owner" in str(exc)
            )
            records.append(
                RunRecord(
                    run_id=run_dir.name,
                    repo_root=repo_root,
                    run_json_path=path,
                    payload={},
                    valid=False,
                    error=str(exc),
                    ownership_failure=ownership,
                )
            )
        except (OSError, json.JSONDecodeError) as exc:
            records.append(
                RunRecord(
                    run_id=run_dir.name,
                    repo_root=repo_root,
                    run_json_path=path,
                    payload={},
                    valid=False,
                    error=f"invalid run JSON: {exc}",
                )
            )
    return records


def _project_run(
    project_root: Path, store: SupervisorStore, record: RunRecord
) -> RunRecord:
    run = dict(record.payload)
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
        run = atomic_save_run(
            record.repo_root,
            run,
            expected_revision=current_revision,
        )
        incoming_revision = int(run["state_revision"])
        projection = _projection(project_root, record, run, incoming_revision)
        record = RunRecord(
            run_id=record.run_id,
            repo_root=record.repo_root,
            run_json_path=record.run_json_path,
            payload=run,
        )
    store.upsert_run_projection(projection)
    return record


def _projection(
    project_root: Path,
    record: RunRecord,
    run: Mapping[str, Any],
    revision: int,
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
        "loop_lineage_id": str(run.get("loop_lineage_id") or record.run_id),
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
        and stored_summary.get("summary") == incoming.get("summary")
        and stored_summary.get("artifact_refs") == incoming.get("artifact_refs")
    )


def _decision_requirement(run: Mapping[str, Any]) -> tuple[str, str, str] | None:
    for key in _SECRET_SIGNAL_KEYS:
        if run.get(key) is True:
            return (
                "global",
                "secret_exposure",
                "Confirmed secret or credential exposure.",
            )
    signals = run.get("supervisor_signals")
    if isinstance(signals, Mapping) and signals.get("unsafe_secret") is True:
        return "global", "secret_exposure", "Confirmed secret or credential exposure."
    for key, summary in _GLOBAL_DECISION_SIGNALS.items():
        if run.get(key) is True or (
            isinstance(signals, Mapping) and signals.get(key) is True
        ):
            return "global", key, summary
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


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid run JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("run JSON must contain an object")
    return value


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


def _ownership_record(path: Path, repo_root: Path, error: str) -> RunRecord:
    return RunRecord(
        run_id=f"ownership-{_safe_slug(path.name)}",
        repo_root=repo_root,
        run_json_path=path,
        payload={},
        valid=False,
        error=error,
        ownership_failure=True,
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
