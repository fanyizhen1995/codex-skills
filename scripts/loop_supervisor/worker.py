"""Independent Worker that leases and executes one bounded action at a time."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
from pathlib import Path
import signal
import threading
from typing import Any

from scripts.harness_loop_runtime_lock import (
    RunLockBusy,
    acquire_repository_mutation_lock,
    acquire_run_lock,
)

from .executor import execute_action
from .models import ActionRequest, ActionResult, ActionResultClass, ActionType
from .registry import transition_for
from .store import ActionRecord, LeaseError, SupervisorStore


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
        task_id=str(row.get("task_id") or ""),
        next_action=str(row.get("next_action") or ""),
        payload=action.payload,
    )


def _mutates_git(request: ActionRequest) -> bool:
    rule = transition_for(request.policy, request.phase, request.next_action)
    if rule.action_type is not request.action_type:
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
) -> None:
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


def _failure_result(exc: BaseException, action_id: str) -> ActionResult:
    retryable = isinstance(exc, (OSError, RunLockBusy, TimeoutError))
    result_class = (
        ActionResultClass.RETRYABLE_FAILURE
        if retryable
        else ActionResultClass.TERMINAL_FAILURE
    )
    return ActionResult(
        result_class=result_class,
        summary=str(exc) or exc.__class__.__name__,
        failure_key=f"worker:{action_id}:{exc.__class__.__name__}",
        error_class=exc.__class__.__name__,
    )


def _write_interruption_evidence(
    project_root: Path,
    request: ActionRequest,
    worker_id: str,
) -> str:
    relative = Path(".codex") / "loop-runs" / request.run_id / (
        f"worker-interruption-{request.action_id}.json"
    )
    path = project_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "action_id": request.action_id,
        "run_id": request.run_id,
        "worker_id": worker_id,
        "signal": _current_stop_reason() or "SIGTERM",
        "observed_at": datetime.now(UTC).isoformat(timespec="microseconds"),
        "new_leases_stopped": True,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return relative.as_posix()


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

        finished = threading.Event()
        lease_lost = threading.Event()
        heartbeat = threading.Thread(
            target=_heartbeat,
            args=(root, action.action_id, worker_id, finished, lease_lost),
            name=f"loop-worker-heartbeat-{worker_id}",
            daemon=True,
        )
        heartbeat.start()
        interruption_evidence = ""
        try:
            try:
                with ExitStack() as locks:
                    locks.enter_context(
                        acquire_run_lock(root, request.run_id, owner=f"worker:{worker_id}")
                    )
                    if _mutates_git(request):
                        locks.enter_context(
                            acquire_repository_mutation_lock(
                                root,
                                owner=f"worker:{worker_id}:{request.action_id}",
                            )
                        )
                    result = execute_action(request, root)
            except Exception as exc:
                result = _failure_result(exc, action.action_id)

            if _stop_requested.is_set():
                interruption_evidence = _write_interruption_evidence(
                    root, request, worker_id
                )
                result = replace(
                    result,
                    artifact_paths=tuple(
                        dict.fromkeys((*result.artifact_paths, interruption_evidence))
                    ),
                )
        finally:
            finished.set()
            heartbeat.join(timeout=max(1.0, HEARTBEAT_SECONDS + 1.0))

        if lease_lost.is_set():
            return WorkerResult(
                action_id=action.action_id,
                run_id=action.run_id,
                status="lease_lost",
                result_class=result.result_class.value,
                summary="action lease was lost during execution",
                interruption_evidence=interruption_evidence,
            )
        try:
            store.complete_action(action.action_id, worker_id, result)
        except LeaseError as exc:
            return WorkerResult(
                action_id=action.action_id,
                run_id=action.run_id,
                status="lease_lost",
                result_class=result.result_class.value,
                summary=str(exc),
                interruption_evidence=interruption_evidence,
            )
        return WorkerResult(
            action_id=action.action_id,
            run_id=action.run_id,
            status=(
                "completed"
                if result.result_class is ActionResultClass.SUCCESS
                else "failed"
            ),
            result_class=result.result_class.value,
            summary=result.summary,
            interruption_evidence=interruption_evidence,
        )


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
