"""Independent Worker that leases and executes one bounded action at a time."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import hashlib
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import signal
import stat
import threading
from typing import Any

from scripts.harness_loop_runtime_lock import (
    RunLockToken,
    acquire_repository_mutation_lock,
    acquire_run_lock,
)
import scripts.harness_loop_orchestrator as legacy

from .executor import execute_action
from .failures import (
    BoundedFailure,
    classify_bounded_failure,
    redact_bounded_text as _redact_text,
)
from .models import ActionRequest, ActionResult, ActionResultClass, ActionType
from .reconciler import _state_fingerprint, atomic_save_run_locked
from .registry import transition_for
from .store import ActionRecord, SupervisorStore


LEASE_SECONDS = 120
HEARTBEAT_SECONDS = 30.0
HEARTBEAT_STALE_SECONDS = 120

_stop_requested = threading.Event()
_stop_lock = threading.Lock()
_stop_reason = ""


@dataclass(frozen=True)
class WorkerResult:
    action_id: str = ""
    run_id: str = ""
    status: str = "idle"
    result_class: str = ""
    summary: str = ""
    interruption_evidence: str = ""
    recovery_evidence: str = ""


def request_stop(reason: str = "SIGTERM") -> None:
    global _stop_reason
    with _stop_lock:
        _stop_reason = str(reason or "SIGTERM")
        _stop_requested.set()


def clear_stop_request() -> None:
    global _stop_reason
    with _stop_lock:
        _stop_reason = ""
        _stop_requested.clear()


def _current_stop_reason() -> str:
    with _stop_lock:
        return _stop_reason


def _request_from_record(store: SupervisorStore, action: ActionRecord) -> ActionRequest:
    row = next(
        item
        for item in store.fetch_all("actions")
        if item["action_id"] == action.action_id
    )
    return ActionRequest(
        action_id=action.action_id,
        run_id=action.run_id,
        run_revision=action.run_revision,
        policy=action.policy,
        phase=action.phase,
        action_type=ActionType(action.action_type),
        idempotency_key=action.idempotency_key,
        repo_relative_root=action.repo_relative_root,
        task_id=str(row.get("task_id") or ""),
        next_action=str(row.get("next_action") or ""),
        payload=action.payload,
    )


def _mutates_git(request: ActionRequest) -> bool:
    rule = transition_for(request.policy, request.phase, request.next_action)
    if rule.action_type is not request.action_type:
        recovery_for = request.payload.get("recovery_for_action_type")
        failure_key = request.payload.get("recovery_failure_key")
        if (
            request.action_type
            in {
                ActionType.RECOVER_GENERATOR_RESULT,
                ActionType.RUN_ALTERNATE_RECOVERY,
                ActionType.RUN_REVIEWER,
            }
            and recovery_for == rule.action_type.value
            and isinstance(failure_key, str)
            and failure_key.startswith("recovery:")
        ):
            return request.action_type is not ActionType.RUN_REVIEWER and rule.mutates_git
        raise ValueError(
            "leased action type does not match current registry transition: "
            f"{request.action_type.value} != {rule.action_type.value}"
        )
    return rule.mutates_git


def _heartbeat(
    project_root: Path,
    action_id: str,
    worker_id: str,
    finished: threading.Event,
    lease_lost: threading.Event,
    heartbeat_errors: list[BaseException],
) -> None:
    try:
        with SupervisorStore.open(project_root) as store:
            store.migrate()
            while not finished.wait(HEARTBEAT_SECONDS):
                if not store.renew_lease(
                    action_id,
                    worker_id,
                    lease_seconds=LEASE_SECONDS,
                ):
                    lease_lost.set()
                    return
    except BaseException as exc:
        heartbeat_errors.append(exc)
        lease_lost.set()


def _evidence_filename(prefix: str, action_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", action_id):
        safe_action = action_id
    else:
        safe_action = "sha256-" + hashlib.sha256(action_id.encode()).hexdigest()[:24]
    return f"{prefix}-{safe_action}.json"


def _write_evidence(
    execution_root: Path,
    request: ActionRequest,
    prefix: str,
    payload: dict[str, Any],
) -> str:
    relative = Path(".codex") / "loop-runs" / request.run_id / _evidence_filename(
        prefix, request.action_id
    )
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fds: list[int] = [os.open(execution_root, flags)]
    try:
        for part in (".codex", "loop-runs", request.run_id):
            directory_fds.append(os.open(part, flags, dir_fd=directory_fds[-1]))
    except BaseException:
        for directory_fd in reversed(directory_fds):
            os.close(directory_fd)
        raise
    run_fd = directory_fds[-1]
    name = relative.name
    try:
        try:
            existing = os.stat(name, dir_fd=run_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and stat.S_ISLNK(existing.st_mode):
            raise OSError("evidence target is a symlink")
        temporary = f".{name}.{os.getpid()}.{threading.get_ident()}.tmp"
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=run_fd,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            fd = -1
            os.replace(temporary, name, src_dir_fd=run_fd, dst_dir_fd=run_fd)
            os.fsync(run_fd)
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(temporary, dir_fd=run_fd)
            except FileNotFoundError:
                pass
    finally:
        for directory_fd in reversed(directory_fds):
            os.close(directory_fd)
    return relative.as_posix()


def _write_interruption_evidence(
    project_root: Path,
    request: ActionRequest,
    worker_id: str,
    *,
    result: ActionResult,
    before_fingerprint: str,
    after_fingerprint: str,
) -> str:
    payload = {
        "action_id": request.action_id,
        "run_id": request.run_id,
        "worker_id": worker_id,
        "signal": _current_stop_reason() or "SIGTERM",
        "observed_at": datetime.now(UTC).isoformat(timespec="microseconds"),
        "new_leases_stopped": True,
        "result_class": ActionResultClass.RECOVERABLE_PARTIAL.value,
        "summary": "worker interrupted after bounded action",
        "artifact_paths": list(result.artifact_paths),
        "checkpoint": result.checkpoint,
        "before_fingerprint": before_fingerprint,
        "after_fingerprint": after_fingerprint,
        "lease_provenance": "worker-owned-live-lease",
    }
    return _write_evidence(project_root, request, "worker-interruption", payload)


def _read_run_state_locked(token: RunLockToken) -> dict[str, Any]:
    validate = os.open(
        "run.json",
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=token.run_fd,
    )
    try:
        with os.fdopen(validate, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        validate = -1
    finally:
        if validate >= 0:
            os.close(validate)
    if not isinstance(payload, dict):
        raise ValueError("run.json must contain an object")
    return payload


def _write_recovery_evidence(
    project_root: Path,
    request: ActionRequest,
    worker_id: str,
    error: BaseException | str,
    *,
    before_fingerprint: str = "",
    after_fingerprint: str = "",
) -> str:
    error_class = error.__class__.__name__ if isinstance(error, BaseException) else "LeaseLost"
    payload = {
        "action_id": request.action_id,
        "run_id": request.run_id,
        "worker_id": worker_id,
        "error_class": error_class,
        "summary": _redact_text(error),
        "observed_at": datetime.now(UTC).isoformat(timespec="microseconds"),
        "recoverable": True,
        "result_class": ActionResultClass.RECOVERABLE_PARTIAL.value,
        "artifact_paths": [],
        "checkpoint": "worker-completion",
        "error_provenance": "heartbeat" if "heartbeat" in str(error).lower() else "completion",
        "lease_provenance": "lease-lost-or-completion-rejected",
        "before_fingerprint": before_fingerprint,
        "after_fingerprint": after_fingerprint,
    }
    return _write_evidence(
        project_root, request, "worker-completion-failure", payload
    )


def _execution_root(project_root: Path, relative_root: str) -> Path:
    current = project_root
    if relative_root != ".":
        for part in PurePosixPath(relative_root).parts:
            current = current / part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise PermissionError("execution root may not contain symlinks")
    resolved = current.resolve()
    if resolved != project_root and project_root not in resolved.parents:
        raise PermissionError("execution root escapes project root")
    if not resolved.is_dir():
        raise PermissionError("execution root must be a directory")
    return resolved


def _validate_result_artifacts(
    execution_root: Path, result: ActionResult
) -> None:
    for value in result.artifact_paths:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value != path.as_posix():
            raise PermissionError(f"artifact path escapes execution root: {value}")
        current = execution_root
        for part in path.parts:
            current = current / part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise PermissionError(f"artifact path ownership changed: {value}")


def worker_once(project_root: Path, worker_id: str) -> WorkerResult:
    root = Path(project_root).resolve()
    if _stop_requested.is_set():
        return WorkerResult(status="stopped", summary="worker stop requested")

    with SupervisorStore.open(root) as store:
        store.migrate()
        action = store.lease_next_action(
            worker_id,
            lease_seconds=LEASE_SECONDS,
            heartbeat_stale_seconds=HEARTBEAT_STALE_SECONDS,
        )
        if action is None:
            return WorkerResult(status="idle")
        request = _request_from_record(store, action)
        execution_root = _execution_root(root, request.repo_relative_root)

        finished = threading.Event()
        lease_lost = threading.Event()
        heartbeat_errors: list[BaseException] = []
        heartbeat = threading.Thread(
            target=_heartbeat,
            args=(
                root,
                action.action_id,
                worker_id,
                finished,
                lease_lost,
                heartbeat_errors,
            ),
            name=f"loop-worker-heartbeat-{worker_id}",
            daemon=True,
        )
        heartbeat.start()
        heartbeat_stopped = False
        final_lease_checked = False

        def stop_heartbeat() -> None:
            nonlocal heartbeat_stopped
            if heartbeat_stopped:
                return
            finished.set()
            heartbeat.join()
            heartbeat_stopped = True

        def check_final_lease() -> None:
            nonlocal final_lease_checked
            if final_lease_checked or lease_lost.is_set():
                return
            final_lease_checked = True
            try:
                renewed = store.renew_lease(
                    action.action_id,
                    worker_id,
                    lease_seconds=LEASE_SECONDS,
                )
            except BaseException as exc:
                heartbeat_errors.append(exc)
                lease_lost.set()
                return
            if not renewed:
                heartbeat_errors.append(
                    RuntimeError("final action lease is no longer active")
                )
                lease_lost.set()

        interruption_evidence = ""
        recovery_evidence = ""
        before_fingerprint = ""
        after_fingerprint = ""
        outcome: WorkerResult | None = None
        try:
            with acquire_run_lock(
                execution_root,
                request.run_id,
                owner=f"worker:{worker_id}",
                blocking=True,
            ) as token:
                if lease_lost.is_set():
                    recovery_evidence = _write_recovery_evidence(
                        execution_root,
                        request,
                        worker_id,
                        heartbeat_errors[0]
                        if heartbeat_errors
                        else "action lease lost before execution",
                    )
                    outcome = WorkerResult(
                        action_id=action.action_id,
                        run_id=action.run_id,
                        status="lease_lost",
                        summary="action lease was lost before execution",
                        recovery_evidence=recovery_evidence,
                    )
                else:
                    try:
                        with ExitStack() as locks:
                            if _mutates_git(request):
                                locks.enter_context(
                                    acquire_repository_mutation_lock(
                                        root,
                                        owner=f"worker:{worker_id}:{request.action_id}",
                                    )
                                )
                            before = _read_run_state_locked(token)
                            before_fingerprint = _state_fingerprint(before)
                            if int(before.get("state_revision", 0)) != request.run_revision:
                                raise ValueError("leased action run revision is stale")
                            with legacy.bounded_run_transaction(
                                execution_root, request.run_id, before
                            ) as transaction:
                                try:
                                    result = execute_action(request, execution_root)
                                finally:
                                    stop_heartbeat()
                                _validate_result_artifacts(execution_root, result)
                                check_final_lease()
                                if lease_lost.is_set():
                                    raise BoundedFailure(
                                        "heartbeat failed before run commit",
                                        cause=heartbeat_errors[0]
                                        if heartbeat_errors
                                        else None,
                                    )
                                legacy.validate_run_payload(
                                    transaction.staged_payload
                                )
                                saved = atomic_save_run_locked(
                                    execution_root,
                                    request.run_id,
                                    transaction.staged_payload,
                                    token=token,
                                    expected_revision=request.run_revision,
                                    expected_fingerprint=before_fingerprint,
                                )
                                after_fingerprint = _state_fingerprint(saved)
                    except Exception as exc:
                        stop_heartbeat()
                        check_final_lease()
                        if not after_fingerprint:
                            after_fingerprint = before_fingerprint
                        result = classify_bounded_failure(
                            exc,
                            action_id=action.action_id,
                            execution_root=execution_root,
                        )

                    if _stop_requested.is_set():
                        interruption_evidence = _write_interruption_evidence(
                            execution_root,
                            request,
                            worker_id,
                            result=result,
                            before_fingerprint=before_fingerprint,
                            after_fingerprint=after_fingerprint,
                        )
                        result = replace(
                            result,
                            artifact_paths=tuple(
                                dict.fromkeys(
                                    (*result.artifact_paths, interruption_evidence)
                                )
                            ),
                        )

                    if lease_lost.is_set():
                        recovery_evidence = _write_recovery_evidence(
                            execution_root,
                            request,
                            worker_id,
                            heartbeat_errors[0]
                            if heartbeat_errors
                            else "action lease lost before completion",
                            before_fingerprint=before_fingerprint,
                            after_fingerprint=after_fingerprint,
                        )
                        outcome = WorkerResult(
                            action_id=action.action_id,
                            run_id=action.run_id,
                            status="lease_lost",
                            result_class=result.result_class.value,
                            summary=(
                                "heartbeat failed during execution"
                                if heartbeat_errors
                                else "action lease was lost during execution"
                            ),
                            interruption_evidence=interruption_evidence,
                            recovery_evidence=recovery_evidence,
                        )
                    else:
                        try:
                            store.complete_action(action.action_id, worker_id, result)
                        except Exception as exc:
                            recovery_evidence = _write_recovery_evidence(
                                execution_root,
                                request,
                                worker_id,
                                exc,
                                before_fingerprint=before_fingerprint,
                                after_fingerprint=after_fingerprint,
                            )
                            outcome = WorkerResult(
                                action_id=action.action_id,
                                run_id=action.run_id,
                                status="lease_lost",
                                result_class=result.result_class.value,
                                summary=str(exc),
                                interruption_evidence=interruption_evidence,
                                recovery_evidence=recovery_evidence,
                            )
                        else:
                            outcome = WorkerResult(
                                action_id=action.action_id,
                                run_id=action.run_id,
                                status=(
                                    "completed"
                                    if result.result_class
                                    is ActionResultClass.SUCCESS
                                    else "failed"
                                ),
                                result_class=result.result_class.value,
                                summary=result.summary,
                                interruption_evidence=interruption_evidence,
                            )
        finally:
            stop_heartbeat()
        if outcome is None:
            raise RuntimeError("worker action exited without a recorded outcome")
        return outcome


def _sigterm_handler(_signum: int, _frame: Any) -> None:
    request_stop("SIGTERM")


def worker_watch(project_root: Path, worker_id: str, poll_seconds: float) -> None:
    if poll_seconds <= 0:
        raise ValueError("poll_seconds must be positive")
    previous_handler = None
    if threading.current_thread() is threading.main_thread():
        previous_handler = signal.signal(signal.SIGTERM, _sigterm_handler)
    try:
        while not _stop_requested.is_set():
            result = worker_once(project_root, worker_id)
            if result.status == "stopped":
                break
            _stop_requested.wait(poll_seconds)
    finally:
        if previous_handler is not None:
            signal.signal(signal.SIGTERM, previous_handler)
