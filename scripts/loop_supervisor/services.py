"""Bounded service observation, restart planning, and restart execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import socket
import stat
from subprocess import DEVNULL, PIPE, Popen as _Popen, TimeoutExpired, run as _run
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from .failures import redact_bounded_text
from .models import ActionOwner, ActionRequest, ActionResult, ActionResultClass, ActionType
from .store import SupervisorStore


HTTP_TIMEOUT_SECONDS = 2.0
SERVICE_CADENCE_SECONDS = 30
FRESHNESS_CADENCE_SECONDS = 300
WORKER_HEARTBEAT_STALE_SECONDS = 60
MAX_RESPONSE_BYTES = 64 * 1024
RESTART_TIMEOUT_SECONDS = 10.0
RESTART_VERIFY_ATTEMPTS = 5
RESTART_VERIFY_INTERVAL_SECONDS = 0.2
RUNTIME_HEARTBEAT_SECONDS = 5.0

_SERVICE_TARGETS = (
    ("crawler-backend", "http://127.0.0.1:8765/api/health"),
    ("crawler-frontend", "http://127.0.0.1:5173/"),
    ("loop-dashboard", "http://127.0.0.1:8766/api/health"),
)
_FRESHNESS_TARGETS = (
    ("wiki", "http://127.0.0.1:8765/api/wiki/metrics"),
    ("search", "http://127.0.0.1:8765/api/search?q=supervisor"),
    ("dashboard", "http://127.0.0.1:8766/api/supervisor"),
)
_SERVICE_SESSIONS = {
    "crawler-backend": "personal-wiki-crawler-backend",
    "crawler-frontend": "personal-wiki-crawler-frontend",
    "loop-dashboard": "loop-dashboard",
    "loop-supervisor": "loop-supervisor",
    "supervisor-worker": "loop-supervisor-worker",
}
_SERVICE_FRESHNESS_TARGETS = {
    "crawler-backend": ("wiki", "search"),
    "crawler-frontend": (),
    "loop-dashboard": ("dashboard",),
    "loop-supervisor": (),
    "supervisor-worker": (),
}


@dataclass(frozen=True)
class ManagedService:
    service_id: str
    session_name: str
    endpoint: str
    command_template: str


_MANAGED_SERVICES = {
    "crawler-backend": ManagedService(
        service_id="crawler-backend",
        session_name="personal-wiki-crawler-backend",
        endpoint="http://127.0.0.1:8765/api/health",
        command_template=(
            "cd {project_root}/personal-wiki/apps/crawler_workbench/backend && "
            "PYTHONPATH=$PWD PW_WORKBENCH_REPO_ROOT={project_root} "
            "python3 -m uvicorn crawler_workbench.main:app --host 0.0.0.0 --port 8765"
        ),
    ),
    "crawler-frontend": ManagedService(
        service_id="crawler-frontend",
        session_name="personal-wiki-crawler-frontend",
        endpoint="http://127.0.0.1:5173/",
        command_template=(
            "cd {project_root}/personal-wiki/apps/crawler_workbench/frontend && "
            "if ! command -v npm >/dev/null 2>&1 && [ -s \"$HOME/.nvm/nvm.sh\" ]; "
            "then . \"$HOME/.nvm/nvm.sh\"; fi && "
            "npm run dev -- --host 0.0.0.0 --port 5173"
        ),
    ),
    "loop-dashboard": ManagedService(
        service_id="loop-dashboard",
        session_name="loop-dashboard",
        endpoint="http://127.0.0.1:8766/api/health",
        command_template=(
            "cd {project_root} && PYTHONPATH=apps/loop_dashboard/backend "
            "python3 -m uvicorn loop_dashboard.main:app --host 0.0.0.0 --port 8766"
        ),
    ),
    "supervisor-worker": ManagedService(
        service_id="supervisor-worker",
        session_name="loop-supervisor-worker",
        endpoint="",
        command_template=(
            "cd {project_root} && python3 -m scripts.loop_supervisor.cli worker "
            "--project-root {project_root} --worker-id \"$LOOP_SUPERVISOR_WORKER_ID\""
        ),
    ),
}
_SERVICE_CODE_PATHS = {
    "crawler-backend": (
        "personal-wiki/apps/crawler_workbench/backend/crawler_workbench",
        "personal-wiki/apps/crawler_workbench/backend/pyproject.toml",
    ),
    "crawler-frontend": (
        "personal-wiki/apps/crawler_workbench/frontend/src",
        "personal-wiki/apps/crawler_workbench/frontend/package.json",
        "personal-wiki/apps/crawler_workbench/frontend/vite.config.ts",
    ),
    "loop-dashboard": (
        "apps/loop_dashboard/backend/loop_dashboard",
        "apps/loop_dashboard/frontend/app.js",
        "apps/loop_dashboard/frontend/index.html",
        "apps/loop_dashboard/frontend/styles.css",
    ),
    "loop-supervisor": (
        "scripts/loop_supervisor",
        "scripts/harness_loop_contracts.py",
        "scripts/harness_loop_runtime_lock.py",
    ),
    "supervisor-worker": (
        "scripts/loop_supervisor",
        "scripts/harness_ai_infra_evidence.py",
        "scripts/harness_loop_agents.py",
        "scripts/harness_loop_artifacts.py",
        "scripts/harness_loop_autonomous.py",
        "scripts/harness_loop_contracts.py",
        "scripts/harness_loop_governance.py",
        "scripts/harness_loop_legacy_readers.py",
        "scripts/harness_loop_orchestrator.py",
        "scripts/harness_loop_runtime_lock.py",
    ),
}


def validate_service_keeper_action(action: Mapping[str, Any]) -> str:
    """Return the allowlisted service for one canonical restart action row."""
    if not isinstance(action, Mapping):
        raise TypeError("Service Keeper action must be a mapping")
    expected_identity = {
        "action_type": ActionType.RESTART_SERVICE.value,
        "queue_owner": ActionOwner.SUPERVISOR.value,
        "run_id": "service-keeper",
        "run_revision": 0,
        "policy": "autonomous_knowledge",
        "phase": "repair_needed",
        "repo_relative_root": ".",
        "next_action": ActionType.RESTART_SERVICE.value,
    }
    if any(action.get(key) != value for key, value in expected_identity.items()):
        raise ValueError("Service Keeper action identity is not canonical")
    try:
        payload = json.loads(str(action.get("payload_json") or "{}"))
    except json.JSONDecodeError as exc:
        raise ValueError("Service Keeper action payload is malformed") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Service Keeper action payload must be an object")
    if not set(payload).issubset(
        {"service_id", "outage_id", "observed_state_fingerprint"}
    ):
        raise ValueError("Service Keeper action payload has unknown fields")
    service_id = payload.get("service_id")
    outage_id = payload.get("outage_id")
    if not isinstance(service_id, str) or service_id not in _MANAGED_SERVICES:
        raise ValueError("Service Keeper service is not allowlisted")
    if not isinstance(outage_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", outage_id
    ):
        raise ValueError("Service Keeper outage identity is invalid")
    observed_fingerprint = payload.get("observed_state_fingerprint")
    if observed_fingerprint is not None and (
        not isinstance(observed_fingerprint, str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", observed_fingerprint)
    ):
        raise ValueError("Service Keeper observed fingerprint is invalid")
    expected_key = f"service-restart:{service_id}:{outage_id}"
    if action.get("idempotency_key") != expected_key:
        raise ValueError("Service Keeper idempotency key is not canonical")
    return service_id


@dataclass(frozen=True)
class ProbeResult:
    status: str
    summary: str
    details: Mapping[str, Any]
    payload: Any = None


HttpProbe = Callable[[str, float], Mapping[str, Any]]
ProcessProbe = Callable[[str, float], Mapping[str, Any]]


def observe_runtime_health(
    project_root: Path,
    store: SupervisorStore,
    *,
    http_probe: HttpProbe | None = None,
    process_probe: ProcessProbe | None = None,
    process_id: int | None = None,
    version: str | None = None,
    runtime_mode: str = "watch",
    timeout_seconds: float = HTTP_TIMEOUT_SECONDS,
    service_cadence_seconds: int = SERVICE_CADENCE_SECONDS,
    freshness_cadence_seconds: int = FRESHNESS_CADENCE_SECONDS,
    worker_stale_seconds: int = WORKER_HEARTBEAT_STALE_SECONDS,
) -> dict[str, Any]:
    """Probe trusted local endpoints and project meaningful service state.

    This path only queues idempotent restart actions. The Supervisor-owned Service
    Keeper executes them separately; neither path sends credentials or stores bodies.
    """
    root = Path(project_root).resolve()
    if store.project_root != root:
        raise ValueError("store project root does not match service observation root")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if worker_stale_seconds <= 0:
        raise ValueError("worker_stale_seconds must be positive")
    if runtime_mode not in {"once", "watch"}:
        raise ValueError("runtime_mode must be once or watch")
    probe = http_probe or _http_probe
    local_probe = process_probe or _tmux_process_probe
    runtime_pid = os.getpid() if process_id is None else process_id
    if not isinstance(runtime_pid, int) or isinstance(runtime_pid, bool) or runtime_pid <= 0:
        raise ValueError("process_id must be a positive int")
    if version is not None and (not isinstance(version, str) or not version):
        raise ValueError("version must be a non-empty string")

    probe_results = _probe_targets(probe, timeout_seconds)
    process_results = _probe_process_targets(local_probe, timeout_seconds)
    freshness_results = {
        target: _freshness_contract(target, probe_results[endpoint])
        for target, endpoint in _FRESHNESS_TARGETS
    }
    writes = {"services": 0, "freshness_checks": 0}
    for service_id, endpoint in _SERVICE_TARGETS:
        observation = probe_results[endpoint]
        process = process_results[_SERVICE_SESSIONS[service_id]]
        freshness_targets = _SERVICE_FRESHNESS_TARGETS[service_id]
        freshness = _combined_freshness(freshness_targets, freshness_results)
        version_state = _running_version_state(root, service_id, process, version)
        status = _endpoint_service_status(observation, process)
        if status == "healthy" and not (
            version_state["heartbeat_verified"]
            and version_state["version_verified"]
        ):
            status = "degraded"
        writes["services"] += store.upsert_service_observation(
            service_id=service_id,
            status=status,
            endpoint=endpoint,
            process_id=_positive_process_id(process.get("process_id")),
            heartbeat_at=str(version_state["heartbeat_at"] or "") or None,
            version=str(version_state["running_version"]),
            details={
                "reachable": observation.status == "healthy",
                "endpoint_verified": observation.status == "healthy",
                "pid_verified": (
                    process.get("session_exists") is True
                    and process.get("process_alive") is True
                    and _positive_process_id(process.get("process_id")) is not None
                ),
                "heartbeat_verified": version_state["heartbeat_verified"],
                **_process_details(process),
                **version_state,
                "freshness": freshness,
                "freshness_targets": list(freshness_targets),
                **_safe_details(observation.details),
            },
            cadence_seconds=service_cadence_seconds,
        )

    supervisor_process = process_results[_SERVICE_SESSIONS["loop-supervisor"]]
    supervisor_watch_status = _process_service_status(supervisor_process)
    supervisor_version = _running_version_state(
        root, "loop-supervisor", supervisor_process, version
    )
    if (
        supervisor_watch_status == "healthy"
        and not (
            supervisor_version["heartbeat_verified"]
            and supervisor_version["version_verified"]
        )
    ):
        supervisor_watch_status = "degraded"
    writes["services"] += store.upsert_service_observation(
        service_id="loop-supervisor",
        status=supervisor_watch_status if runtime_mode == "watch" else "unavailable",
        process_id=runtime_pid if runtime_mode == "watch" else None,
        heartbeat_at=str(supervisor_version["heartbeat_at"] or "") or None,
        version=str(supervisor_version["running_version"]),
        details={
            "role": "supervisor",
            "runtime_mode": runtime_mode,
            "process_scope": "long_running" if runtime_mode == "watch" else "one_shot",
            "process_alive": True if runtime_mode == "watch" else None,
            "freshness": "not_applicable",
            **_process_details(supervisor_process),
            **supervisor_version,
        },
        cadence_seconds=service_cadence_seconds,
    )

    worker_count, alive_worker_ids, workers, worker_heartbeat = _worker_state(
        store, worker_stale_seconds
    )
    worker_process = process_results[_SERVICE_SESSIONS["supervisor-worker"]]
    worker_version = _running_version_state(
        root, "supervisor-worker", worker_process, version
    )
    if not worker_count:
        worker_status = "offline"
    elif not alive_worker_ids:
        worker_status = "stale"
    elif (
        _process_service_status(worker_process) == "healthy"
        and worker_version["heartbeat_verified"]
        and worker_version["version_verified"]
    ):
        worker_status = "healthy"
    else:
        worker_status = "degraded"
    writes["services"] += store.upsert_service_observation(
        service_id="supervisor-worker",
        status=worker_status,
        process_id=_positive_process_id(worker_process.get("process_id")),
        heartbeat_at=worker_heartbeat,
        version=str(worker_version["running_version"]),
        details={
            "worker_count": worker_count,
            "alive_worker_ids": alive_worker_ids,
            "workers": workers,
            "freshness": "not_applicable",
            **_process_details(worker_process),
            **worker_version,
        },
        cadence_seconds=service_cadence_seconds,
    )

    for target, endpoint in _FRESHNESS_TARGETS:
        observation = probe_results[endpoint]
        freshness_status, freshness_summary = freshness_results[target]
        writes["freshness_checks"] += store.record_freshness_observation(
            target=target,
            status=freshness_status,
            summary=redact_bounded_text(freshness_summary),
            details={"endpoint": endpoint, **_safe_details(observation.details)},
            cadence_seconds=freshness_cadence_seconds,
        )
    restart_actions = _enqueue_service_restart_actions(root, store)
    return {
        "writes": writes,
        "runtime_mode": runtime_mode,
        "restart_actions": restart_actions,
    }


def _enqueue_service_restart_actions(
    project_root: Path, store: SupervisorStore
) -> list[str]:
    if store.project_root != project_root:
        raise ValueError("store project root does not match service restart root")
    existing_actions = {
        str(row["idempotency_key"]): row
        for row in store.fetch_all("actions")
        if row["action_type"] == ActionType.RESTART_SERVICE.value
    }
    queued: list[str] = []
    for observation in sorted(
        store.fetch_all("services"), key=lambda row: str(row["service_id"])
    ):
        service_id = str(observation["service_id"])
        if service_id not in _MANAGED_SERVICES:
            continue
        if observation["status"] == "healthy":
            for action in existing_actions.values():
                try:
                    payload = json.loads(str(action.get("payload_json") or "{}"))
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, Mapping):
                    continue
                outage_id = str(payload.get("outage_id") or "")
                if payload.get("service_id") == service_id and outage_id:
                    store.cancel_pending_service_restarts(
                        service_id, outage_id=outage_id
                    )
            continue
        try:
            details = json.loads(str(observation.get("details_json") or "{}"))
        except json.JSONDecodeError:
            details = {}
        if not isinstance(details, Mapping):
            details = {}
        outage_id = str(details.get("outage_id") or "")
        if not outage_id:
            raise RuntimeError(f"unhealthy service lacks outage identity: {service_id}")
        state = {
            "service_id": service_id,
            "status": str(observation.get("status") or ""),
            "endpoint": str(observation.get("endpoint") or ""),
            "pid_present": _positive_process_id(observation.get("process_id"))
            is not None,
            "endpoint_verified": details.get("endpoint_verified") is True,
            "tmux_session_exists": details.get("tmux_session_exists"),
            "process_alive": details.get("process_alive"),
            "heartbeat_verified": details.get("heartbeat_verified") is True,
            "running_version": str(details.get("running_version") or ""),
            "expected_version": str(details.get("expected_version") or ""),
            "version_verified": details.get("version_verified") is True,
            "error_class": str(details.get("error_class") or ""),
        }
        digest = hashlib.sha256(
            json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        idempotency_key = f"service-restart:{service_id}:{outage_id}"
        operation_digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        request = ActionRequest(
            action_id=f"service-restart-{operation_digest[:24]}",
            run_id="service-keeper",
            run_revision=0,
            policy="autonomous_knowledge",
            phase="repair_needed",
            action_type=ActionType.RESTART_SERVICE,
            idempotency_key=idempotency_key,
            queue_owner=ActionOwner.SUPERVISOR,
            repo_relative_root=".",
            task_id=f"service:{service_id}:{outage_id}",
            next_action=ActionType.RESTART_SERVICE.value,
            payload={
                "service_id": service_id,
                "outage_id": outage_id,
                "observed_state_fingerprint": f"sha256:{digest}",
            },
        )
        existing = existing_actions.get(idempotency_key)
        if existing is not None:
            if str(existing["status"]) == "pending":
                if existing.get("not_before") and not request.not_before:
                    request = replace(
                        request, not_before=str(existing["not_before"])
                    )
                store.update_pending_action(request)
            elif str(existing["status"]) == "failed":
                store.rearm_retryable_service_restart(
                    str(existing["action_id"]),
                    service_id=service_id,
                    backoff_seconds=SERVICE_CADENCE_SECONDS,
                )
            elif str(existing["status"]) == "cancelled":
                store.rearm_current_cancelled_service_restart(
                    str(existing["action_id"]),
                    service_id=service_id,
                    outage_id=outage_id,
                )
            queued.append(str(existing["action_id"]))
            continue
        action = store.enqueue_action(request, priority=10)
        existing_actions[idempotency_key] = {
            "action_id": action.action_id,
            "status": action.status,
        }
        queued.append(action.action_id)
    return queued


def run_service_keeper_once(
    project_root: Path,
    store: SupervisorStore,
    *,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Execute pending restarts through one bounded Supervisor-owned path."""
    root = Path(project_root).resolve()
    if store.project_root != root:
        raise ValueError("store project root does not match Service Keeper root")
    owner = owner_id or f"supervisor-service-keeper-{os.getpid()}"
    report: dict[str, Any] = {
        "claimed": 0,
        "completed": 0,
        "failed": 0,
        "action_ids": [],
    }
    current_outages: dict[str, str] = {}
    for service in store.fetch_all("services"):
        if service["status"] == "healthy":
            continue
        try:
            details = json.loads(str(service.get("details_json") or "{}"))
        except json.JSONDecodeError:
            continue
        if isinstance(details, Mapping) and details.get("outage_id"):
            current_outages[str(service["service_id"])] = str(details["outage_id"])
    candidates = sorted(
        (
            row
            for row in store.fetch_all("actions")
            if row["action_type"] == ActionType.RESTART_SERVICE.value
            and row["queue_owner"] == ActionOwner.SUPERVISOR.value
            and row["status"] in {"pending", "leased", "running"}
        ),
        key=lambda row: (str(row["created_at"]), str(row["action_id"])),
    )
    for row in candidates:
        try:
            payload = json.loads(str(row.get("payload_json") or "{}"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue
        service_id = str(payload.get("service_id") or "")
        outage_id = str(payload.get("outage_id") or "")
        current_outage_id = current_outages.get(service_id, "")
        if current_outage_id and outage_id != current_outage_id:
            if store.cancel_stale_service_restart(
                str(row["action_id"]),
                service_id=service_id,
                outage_id=outage_id,
                current_outage_id=current_outage_id,
            ):
                return report
    for row in candidates:
        try:
            payload = json.loads(str(row.get("payload_json") or "{}"))
        except json.JSONDecodeError:
            payload = {}
        service_id = str(payload.get("service_id") or "") if isinstance(payload, Mapping) else ""
        outage_id = str(payload.get("outage_id") or "") if isinstance(payload, Mapping) else ""
        current_outage_id = current_outages.get(service_id, "")
        if current_outage_id and outage_id != current_outage_id:
            if store.cancel_stale_service_restart(
                str(row["action_id"]),
                service_id=service_id,
                outage_id=outage_id,
                current_outage_id=current_outage_id,
            ):
                break
            continue
        claimed = store.claim_service_restart_action(
            str(row["action_id"]),
            owner,
            service_id=service_id,
            outage_id=outage_id,
            lease_seconds=max(120, int(RESTART_TIMEOUT_SECONDS * 4)),
        )
        if claimed is None:
            continue
        store.cancel_pending_service_restarts(service_id, outage_id=outage_id)
        report["claimed"] += 1
        report["action_ids"].append(claimed.action_id)
        if service_id not in _MANAGED_SERVICES:
            result = ActionResult(
                result_class=ActionResultClass.TERMINAL_FAILURE,
                summary="managed service is not allowlisted",
                failure_key=f"service-restart:{service_id or 'missing'}",
                error_class="service_not_allowlisted",
                checkpoint="service-restart:rejected",
            )
        else:
            try:
                result = restart_managed_service(root, service_id)
            except Exception:
                result = ActionResult(
                    result_class=ActionResultClass.RETRYABLE_FAILURE,
                    summary=f"managed service {service_id} restart raised an exception",
                    failure_key=f"service-restart:{service_id}",
                    error_class="service_restart_exception",
                    checkpoint="service-restart:exception",
                )
        store.complete_action(claimed.action_id, owner, result)
        if result.result_class is ActionResultClass.SUCCESS:
            report["completed"] += 1
        else:
            report["failed"] += 1
    return report


def restart_managed_service(project_root: Path, service_id: str) -> ActionResult:
    root = Path(project_root).resolve()
    service = _MANAGED_SERVICES.get(service_id)
    if service is None:
        raise ValueError(f"managed service is not allowlisted: {service_id}")

    current_process = _run_process_probe(
        _tmux_process_probe, service.session_name, HTTP_TIMEOUT_SECONDS
    )
    current_endpoint = (
        _run_probe(_http_probe, service.endpoint, HTTP_TIMEOUT_SECONDS)
        if service.endpoint
        else ProbeResult("healthy", "not applicable", {})
    )
    current_version = _running_version_state(
        root, service_id, current_process, None
    )
    old_process_id = _positive_process_id(current_process.get("process_id"))
    current_pid_verified = (
        current_process.get("session_exists") is True
        and current_process.get("process_alive") is True
        and old_process_id is not None
    )
    current_heartbeat_verified = bool(current_version["heartbeat_verified"])
    if not service.endpoint:
        database = root / ".codex" / "supervisor" / "supervisor.db"
        current_heartbeat_verified = False
        if database.is_file():
            with SupervisorStore.open(root) as store:
                store.migrate()
                _count, alive, _workers, _latest = _worker_state(
                    store, WORKER_HEARTBEAT_STALE_SECONDS
                )
            current_heartbeat_verified = bool(alive) and bool(
                current_version["heartbeat_verified"]
            )
    if (
        current_endpoint.status == "healthy"
        and current_pid_verified
        and current_heartbeat_verified
        and current_version["version_verified"]
    ):
        runtime_path = (
            root / ".codex" / "service-runtime" / f"{service_id}.json"
        )
        return ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary=f"managed service {service_id} recovered before restart",
            artifact_paths=(runtime_path.relative_to(root).as_posix(),),
            checkpoint="service-restart:already-healthy",
        )
    if current_process["session_exists"] is True:
        stopped = _run_tmux_command(
            ("kill-session", "-t", service.session_name),
            root,
            RESTART_TIMEOUT_SECONDS,
        )
        failure = _tmux_failure(service_id, "terminate", stopped)
        if failure is not None:
            return failure

    command = _managed_runtime_command(root, service)
    started = _run_tmux_command(
        ("new-session", "-d", "-s", service.session_name, command),
        root,
        RESTART_TIMEOUT_SECONDS,
    )
    failure = _tmux_failure(service_id, "start", started)
    if failure is not None:
        return failure

    last_summary = "replacement did not become verifiably healthy"
    for attempt in range(RESTART_VERIFY_ATTEMPTS):
        process = _run_process_probe(
            _tmux_process_probe, service.session_name, HTTP_TIMEOUT_SECONDS
        )
        endpoint = (
            _run_probe(_http_probe, service.endpoint, HTTP_TIMEOUT_SECONDS)
            if service.endpoint
            else ProbeResult("healthy", "not applicable", {})
        )
        process_id = _positive_process_id(process.get("process_id"))
        pid_verified = (
            process.get("session_exists") is True
            and process.get("process_alive") is True
            and process_id is not None
        )
        replacement_pid_verified = pid_verified and (
            old_process_id is None or process_id != old_process_id
        )
        endpoint_verified = endpoint.status == "healthy"
        version_state = _running_version_state(root, service_id, process, None)
        heartbeat_at = str(version_state["heartbeat_at"] or "")
        heartbeat_verified = bool(version_state["heartbeat_verified"])
        if not service.endpoint:
            with SupervisorStore.open(root) as store:
                store.migrate()
                _count, alive, _workers, latest = _worker_state(
                    store, WORKER_HEARTBEAT_STALE_SECONDS
                )
            heartbeat_verified = bool(alive) and heartbeat_verified
            heartbeat_at = latest or ""
        runtime_path = root / ".codex" / "service-runtime" / f"{service_id}.json"

        if (
            endpoint_verified
            and replacement_pid_verified
            and heartbeat_verified
            and version_state["version_verified"]
            and runtime_path.is_file()
        ):
            with SupervisorStore.open(root) as store:
                store.migrate()
                store.upsert_service_observation(
                    service_id=service_id,
                    status="healthy",
                    endpoint=service.endpoint,
                    process_id=process_id,
                    heartbeat_at=heartbeat_at,
                    version=str(version_state["running_version"]),
                    details={
                        "tmux_session": service.session_name,
                        "tmux_session_exists": True,
                        "process_alive": True,
                        "endpoint_verified": True,
                        "pid_verified": True,
                        "heartbeat_verified": True,
                        **version_state,
                        "restart_verified": True,
                    },
                    cadence_seconds=SERVICE_CADENCE_SECONDS,
                )
            artifact = runtime_path.relative_to(root).as_posix()
            return ActionResult(
                result_class=ActionResultClass.SUCCESS,
                summary=f"restarted and verified managed service {service_id}",
                artifact_paths=(artifact,),
                checkpoint="service-restart:verified",
            )

        last_summary = "; ".join(
            item
            for item in (
                "endpoint not verified" if not endpoint_verified else "",
                "replacement pid not verified"
                if not replacement_pid_verified
                else "",
                "heartbeat not verified" if not heartbeat_verified else "",
                str(version_state["heartbeat_evidence"])
                if not version_state["heartbeat_verified"]
                else "",
                str(version_state["version_evidence"])
                if not version_state["version_verified"]
                else "",
            )
            if item
        )
        if attempt + 1 < RESTART_VERIFY_ATTEMPTS:
            time.sleep(RESTART_VERIFY_INTERVAL_SECONDS)

    return ActionResult(
        result_class=ActionResultClass.RETRYABLE_FAILURE,
        summary=f"managed service {service_id} restart verification failed: {last_summary}",
        failure_key=f"service-restart:{service_id}",
        error_class="service_verification_failed",
        checkpoint="service-restart:verification-failed",
    )


def _tmux_failure(
    service_id: str, operation: str, result: Mapping[str, Any]
) -> ActionResult | None:
    if result.get("returncode") == 0:
        return None
    return ActionResult(
        result_class=ActionResultClass.RETRYABLE_FAILURE,
        summary=f"managed service {service_id} {operation} failed",
        failure_key=f"service-restart:{service_id}",
        error_class=f"service_{operation}_failed",
        checkpoint=f"service-restart:{operation}-failed",
    )


def _run_tmux_command(
    arguments: tuple[str, ...], cwd: Path, timeout_seconds: float
) -> Mapping[str, Any]:
    try:
        result = _run(
            ["tmux", *arguments],
            cwd=cwd,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return {"returncode": 127, "stdout": "", "stderr": "tmux unavailable"}
    except TimeoutExpired:
        return {"returncode": 124, "stdout": "", "stderr": "tmux timed out"}
    return {
        "returncode": result.returncode,
        "stdout": redact_bounded_text(result.stdout, limit=512),
        "stderr": redact_bounded_text(result.stderr, limit=512),
    }


def _managed_runtime_command(project_root: Path, service: ManagedService) -> str:
    project_argument = shlex.quote(str(project_root))
    service_argument = shlex.quote(service.service_id)
    return (
        f"cd {project_argument} && python3 -m scripts.loop_supervisor.service_runtime "
        f"--project-root {project_argument} --service-id {service_argument}"
    )


def _start_managed_child(project_root: Path, service: ManagedService) -> Any:
    project_argument = shlex.quote(str(project_root))
    command = service.command_template.format(project_root=project_argument)
    environment = None
    if service.service_id == "loop-dashboard":
        environment = os.environ.copy()
        environment["LOOP_DASHBOARD_CURSOR_SECRET"] = _dashboard_cursor_secret(
            project_root
        )
    elif service.service_id == "supervisor-worker":
        environment = os.environ.copy()
        environment["LOOP_SUPERVISOR_WORKER_ID"] = (
            f"service-keeper-worker-{os.getpid()}"
        )
    return _Popen(
        ["bash", "-lc", command],
        cwd=project_root,
        stdin=DEVNULL,
        close_fds=True,
        env=environment,
    )


def _dashboard_cursor_secret(project_root: Path) -> str:
    root = Path(project_root).resolve()
    secret_dir = root / ".codex" / "session-state" / "loop-dashboard"
    secret_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if secret_dir.is_symlink():
        raise PermissionError("dashboard cursor secret directory is a symlink")
    try:
        secret_dir.resolve().relative_to(root)
    except ValueError as exc:
        raise PermissionError(
            "dashboard cursor secret directory escapes project root"
        ) from exc
    secret_dir.chmod(0o700)

    secret_path = secret_dir / "cursor-secret"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(secret_path, flags, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(secrets.token_urlsafe(48))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

    metadata = secret_path.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise PermissionError(
            "dashboard cursor secret file is not a private regular file"
        )
    read_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        read_flags |= os.O_NOFOLLOW
    descriptor = os.open(secret_path, read_flags)
    with os.fdopen(descriptor, "r", encoding="ascii") as stream:
        secret = stream.read().strip()
    if len(secret.encode()) < 32:
        raise ValueError("dashboard cursor secret must contain at least 32 bytes")
    return secret


def run_managed_service_runtime(
    project_root: Path,
    service_id: str,
    *,
    heartbeat_interval_seconds: float = RUNTIME_HEARTBEAT_SECONDS,
) -> int:
    """Run one fixed managed child and publish evidence from its runtime wrapper."""
    root = Path(project_root).resolve()
    service = _MANAGED_SERVICES.get(service_id)
    if service is None:
        raise ValueError(f"managed service is not allowlisted: {service_id}")
    if heartbeat_interval_seconds <= 0:
        raise ValueError("heartbeat_interval_seconds must be positive")
    project_argument = shlex.quote(str(root))
    command = service.command_template.format(project_root=project_argument)
    code_fingerprint = _service_code_fingerprint(root, service_id)
    git_head = _code_version(root)
    process_id = os.getpid()
    started_at = _utc_now()
    child = _start_managed_child(root, service)
    _publish_runtime_metadata(
        root,
        service,
        process_id=process_id,
        command=command,
        started_at=started_at,
        heartbeat_at=_utc_now(),
        code_fingerprint=code_fingerprint,
        git_head=git_head,
    )
    while child.poll() is None:
        time.sleep(heartbeat_interval_seconds)
        _publish_runtime_metadata(
            root,
            service,
            process_id=process_id,
            command=command,
            started_at=started_at,
            heartbeat_at=_utc_now(),
            code_fingerprint=code_fingerprint,
            git_head=git_head,
        )
    return int(child.wait())


def _publish_runtime_metadata(
    project_root: Path,
    service: ManagedService,
    *,
    process_id: int,
    command: str,
    started_at: str,
    heartbeat_at: str,
    code_fingerprint: str,
    git_head: str,
) -> Path:
    runtime_dir = project_root / ".codex" / "service-runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    try:
        runtime_dir.resolve().relative_to(project_root)
    except ValueError as exc:
        raise PermissionError("service runtime directory escapes project root") from exc
    runtime_path = runtime_dir / f"{service.service_id}.json"
    if runtime_path.is_symlink():
        raise PermissionError("service runtime metadata target is a symlink")
    payload = {
        "schema_version": 1,
        "service": service.service_id,
        "tmux_session": service.session_name,
        "pid": process_id,
        "cwd": str(project_root),
        "command": command,
        "endpoint": service.endpoint,
        "git_head": git_head,
        "started_at": started_at,
        "heartbeat_at": heartbeat_at,
        "code_fingerprint": code_fingerprint,
    }
    temporary = runtime_path.with_name(
        f".{runtime_path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, runtime_path)
    finally:
        temporary.unlink(missing_ok=True)
    return runtime_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _worker_state(
    store: SupervisorStore, stale_seconds: int
) -> tuple[int, list[str], list[dict[str, str]], str | None]:
    now = store.current_time()
    alive: list[str] = []
    worker_rows = store.fetch_all("workers")
    workers: list[dict[str, str]] = []
    latest_heartbeat: tuple[datetime, str] | None = None
    for worker in worker_rows:
        worker_id = str(worker["worker_id"])
        heartbeat_text = str(worker.get("heartbeat_at") or "")
        heartbeat = _parse_time(str(worker.get("heartbeat_at") or ""))
        status = "stale"
        if heartbeat is not None:
            if latest_heartbeat is None or heartbeat > latest_heartbeat[0]:
                latest_heartbeat = (heartbeat, heartbeat_text)
            if (now - heartbeat).total_seconds() <= stale_seconds:
                alive.append(worker_id)
                status = "healthy"
        workers.append(
            {
                "worker_id": worker_id,
                "heartbeat_at": heartbeat_text,
                "status": status,
            }
        )
    return (
        len(worker_rows),
        sorted(alive),
        sorted(workers, key=lambda item: item["worker_id"]),
        latest_heartbeat[1] if latest_heartbeat else None,
    )


def _probe_targets(probe: HttpProbe, timeout_seconds: float) -> dict[str, ProbeResult]:
    endpoints = tuple(endpoint for _name, endpoint in (*_SERVICE_TARGETS, *_FRESHNESS_TARGETS))
    with ThreadPoolExecutor(max_workers=len(endpoints), thread_name_prefix="supervisor-probe") as executor:
        futures = {
            endpoint: executor.submit(_run_probe, probe, endpoint, timeout_seconds)
            for endpoint in endpoints
        }
        return {endpoint: future.result() for endpoint, future in futures.items()}


def _probe_process_targets(
    probe: ProcessProbe, timeout_seconds: float
) -> dict[str, dict[str, Any]]:
    sessions = tuple(_SERVICE_SESSIONS.values())
    with ThreadPoolExecutor(
        max_workers=len(sessions), thread_name_prefix="supervisor-process-probe"
    ) as executor:
        futures = {
            session: executor.submit(_run_process_probe, probe, session, timeout_seconds)
            for session in sessions
        }
        return {session: future.result() for session, future in futures.items()}


def _run_process_probe(
    probe: ProcessProbe, session_name: str, timeout_seconds: float
) -> dict[str, Any]:
    try:
        value = probe(session_name, timeout_seconds)
    except Exception:
        value = {}
    return {
        "session_name": session_name,
        "session_exists": value.get("session_exists")
        if value.get("session_exists") in {True, False}
        else None,
        "process_id": _positive_process_id(value.get("process_id")),
        "process_alive": value.get("process_alive")
        if value.get("process_alive") in {True, False}
        else None,
        "command": redact_bounded_text(value.get("command") or "", limit=128),
    }


def _tmux_process_probe(session_name: str, timeout_seconds: float) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", session_name):
        raise ValueError("tmux session name is invalid")
    try:
        process = _Popen(
            [
                "tmux",
                "list-panes",
                "-t",
                session_name,
                "-F",
                "#{session_name}|#{pane_pid}|#{pane_dead}|#{pane_current_command}",
            ],
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            close_fds=True,
        )
        stdout, _stderr = process.communicate(timeout=timeout_seconds)
    except FileNotFoundError:
        return _unknown_process(session_name)
    except TimeoutExpired:
        process.kill()
        process.communicate()
        return _unknown_process(session_name)
    if process.returncode != 0:
        return {
            **_unknown_process(session_name),
            "session_exists": False,
            "process_alive": False,
        }
    line = stdout.splitlines()[0] if stdout.splitlines() else ""
    parts = line.split("|", 3)
    if len(parts) != 4 or parts[0] != session_name:
        return _unknown_process(session_name)
    process_id = _positive_process_id(parts[1])
    process_alive = parts[2] == "0" if parts[2] in {"0", "1"} else None
    return {
        "session_name": session_name,
        "session_exists": True,
        "process_id": process_id,
        "process_alive": process_alive,
        "command": redact_bounded_text(parts[3], limit=128),
    }


def _unknown_process(session_name: str) -> dict[str, Any]:
    return {
        "session_name": session_name,
        "session_exists": None,
        "process_id": None,
        "process_alive": None,
        "command": "",
    }


def _positive_process_id(value: object) -> int | None:
    try:
        process_id = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return process_id if process_id > 0 else None


def _process_details(process: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "tmux_session": str(process.get("session_name") or ""),
        "tmux_session_exists": process.get("session_exists")
        if process.get("session_exists") in {True, False}
        else None,
        "process_alive": process.get("process_alive")
        if process.get("process_alive") in {True, False}
        else None,
        "process_command": redact_bounded_text(
            process.get("command") or "", limit=128
        ),
    }


def _running_version_state(
    project_root: Path,
    service_id: str,
    process: Mapping[str, Any],
    override: str | None,
) -> dict[str, Any]:
    if override is not None:
        return {
            "running_version": override,
            "expected_version": override,
            "heartbeat_at": "",
            "heartbeat_verified": True,
            "heartbeat_evidence": "explicit runtime evidence",
            "version_verified": True,
            "version_evidence": "explicit runtime version",
        }

    runtime_path = (
        project_root / ".codex" / "service-runtime" / f"{service_id}.json"
    )
    running_version = ""
    heartbeat_at = ""
    identity_errors: list[str] = []
    try:
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("runtime metadata must be an object")
    except (OSError, ValueError, json.JSONDecodeError):
        payload = {}
        identity_errors.append("runtime metadata unavailable")

    if payload:
        running_version = str(payload.get("code_fingerprint") or "")
        heartbeat_at = str(payload.get("heartbeat_at") or "")
        if payload.get("service") != service_id:
            identity_errors.append("runtime service mismatch")
        if payload.get("tmux_session") != _SERVICE_SESSIONS[service_id]:
            identity_errors.append("runtime tmux session mismatch")
        if _positive_process_id(payload.get("pid")) != _positive_process_id(
            process.get("process_id")
        ):
            identity_errors.append("runtime pid mismatch")
        runtime_cwd = Path(str(payload.get("cwd") or ""))
        try:
            runtime_cwd.resolve().relative_to(project_root)
        except (OSError, ValueError):
            identity_errors.append("runtime cwd is outside project root")

    version_errors = list(identity_errors)
    heartbeat_errors = list(identity_errors)
    if payload:
        if not running_version:
            version_errors.append("runtime code fingerprint missing")
        heartbeat = _parse_time(heartbeat_at)
        if heartbeat is None:
            heartbeat_errors.append("runtime heartbeat missing")
        else:
            age_seconds = (datetime.now(timezone.utc) - heartbeat).total_seconds()
            if age_seconds < -5 or age_seconds > WORKER_HEARTBEAT_STALE_SECONDS:
                heartbeat_errors.append("runtime heartbeat stale")

    try:
        expected_version = _service_code_fingerprint(project_root, service_id)
    except (OSError, RuntimeError):
        expected_version = ""
        version_errors.append("expected code fingerprint unavailable")
    if running_version and expected_version and running_version != expected_version:
        version_errors.append("runtime code fingerprint mismatch")
    version_verified = (
        not version_errors and bool(running_version) and bool(expected_version)
    )
    heartbeat_verified = not heartbeat_errors and bool(heartbeat_at)
    return {
        "running_version": running_version,
        "expected_version": expected_version,
        "heartbeat_at": heartbeat_at,
        "heartbeat_verified": heartbeat_verified,
        "heartbeat_evidence": (
            "runtime heartbeat is current and pid-bound"
            if heartbeat_verified
            else "; ".join(dict.fromkeys(heartbeat_errors))
        ),
        "version_verified": version_verified,
        "version_evidence": (
            "runtime fingerprint matches expected code"
            if version_verified
            else "; ".join(dict.fromkeys(version_errors))
        ),
    }


def _service_code_fingerprint(project_root: Path, service_id: str) -> str:
    relative_paths = _SERVICE_CODE_PATHS.get(service_id)
    if relative_paths is None:
        raise RuntimeError(f"service code paths are not configured: {service_id}")
    files: list[Path] = []
    for relative_path in relative_paths:
        path = project_root / relative_path
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and not any(
                    part
                    in {
                        "node_modules",
                        "dist",
                        "build",
                        "__pycache__",
                        ".pytest_cache",
                    }
                    for part in candidate.parts
                )
            )
    if not files:
        raise RuntimeError(f"service code files are missing: {service_id}")
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(project_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _process_service_status(process: Mapping[str, Any]) -> str:
    if process.get("session_exists") is False or process.get("process_alive") is False:
        return "unhealthy"
    if process.get("session_exists") is True and process.get("process_alive") is True:
        return "healthy"
    return "degraded"


def _endpoint_service_status(
    observation: ProbeResult, process: Mapping[str, Any]
) -> str:
    if observation.status != "healthy":
        return "unhealthy"
    return _process_service_status(process)


def _combined_freshness(
    targets: tuple[str, ...], results: Mapping[str, tuple[str, str]]
) -> str:
    if not targets:
        return "unavailable"
    return "fresh" if all(results[target][0] == "fresh" for target in targets) else "stale"


def _run_probe(probe: HttpProbe, endpoint: str, timeout_seconds: float) -> ProbeResult:
    try:
        return _coerce_probe(probe(endpoint, timeout_seconds))
    except (TimeoutError, socket.timeout):
        return ProbeResult("unhealthy", "timeout", {"error_class": "timeout"})
    except OSError:
        return ProbeResult("unhealthy", "connection error", {"error_class": "connection_error"})
    except Exception:
        return ProbeResult("unhealthy", "probe error", {"error_class": "probe_error"})


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _coerce_probe(value: Mapping[str, Any]) -> ProbeResult:
    status = str(value.get("status") or "unhealthy")
    if status != "healthy":
        status = "unhealthy"
    summary = str(value.get("summary") or ("HTTP 200" if status == "healthy" else "probe failed"))
    details = value.get("details")
    return ProbeResult(
        status=status,
        summary=summary,
        details=details if isinstance(details, Mapping) else {},
        payload=value.get("payload"),
    )


def _freshness_contract(target: str, observation: ProbeResult) -> tuple[str, str]:
    if observation.status != "healthy":
        return "stale", observation.summary
    payload = observation.payload
    if target == "wiki":
        counts = payload.get("counts") if isinstance(payload, Mapping) else None
        sizes = payload.get("sizes") if isinstance(payload, Mapping) else None
        health = payload.get("health") if isinstance(payload, Mapping) else None
        valid = (
            isinstance(counts, Mapping)
            and isinstance(sizes, Mapping)
            and isinstance(health, Mapping)
            and all(
                isinstance(counts.get(key), int)
                and not isinstance(counts.get(key), bool)
                and int(counts[key]) >= 0
                for key in ("wiki_page_count", "raw_file_count")
            )
            and all(
                isinstance(sizes.get(key), int)
                and not isinstance(sizes.get(key), bool)
                and int(sizes[key]) >= 0
                for key in ("wiki_bytes", "raw_bytes")
            )
            and isinstance(health.get("status"), str)
            and bool(health.get("status"))
        )
        return ("fresh", observation.summary) if valid else (
            "stale",
            "wiki response contract mismatch",
        )
    if target == "search":
        required = {"domain", "path", "title", "snippet", "score"}
        valid = isinstance(payload, list) and bool(payload) and all(
            isinstance(item, Mapping) and required <= set(item) for item in payload
        )
        return ("fresh", observation.summary) if valid else (
            "stale",
            "search response contract mismatch",
        )
    if target == "dashboard":
        if not isinstance(payload, Mapping) or payload.get("status") != "available":
            return "stale", "dashboard response contract mismatch"
        diagnostics = payload.get("diagnostics")
        if not isinstance(diagnostics, list):
            return "stale", "dashboard response contract mismatch"
        if diagnostics:
            return "stale", "dashboard diagnostics present"
        return "fresh", observation.summary
    return "stale", "unknown freshness target"


def _safe_details(details: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    status_code = details.get("status_code")
    if isinstance(status_code, int) and not isinstance(status_code, bool):
        safe["status_code"] = status_code
    error_class = details.get("error_class")
    if isinstance(error_class, str) and error_class:
        safe["error_class"] = error_class
    return safe


def _http_probe(endpoint: str, timeout_seconds: float) -> Mapping[str, Any]:
    accept = (
        "text/html"
        if endpoint == _MANAGED_SERVICES["crawler-frontend"].endpoint
        else "application/json"
    )
    request = Request(endpoint, headers={"Accept": accept}, method="GET")
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            status_code = int(response.getcode())
            raw_payload = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        return {
            "status": "unhealthy",
            "summary": f"HTTP {error.code}",
            "details": {"status_code": int(error.code), "error_class": "http_error"},
        }
    except (TimeoutError, socket.timeout):
        return {
            "status": "unhealthy",
            "summary": "timeout",
            "details": {"error_class": "timeout"},
        }
    except URLError as error:
        return {
            "status": "unhealthy",
            "summary": _url_error_summary(error),
            "details": {"error_class": _url_error_class(error)},
        }
    except OSError:
        return {
            "status": "unhealthy",
            "summary": "connection error",
            "details": {"error_class": "connection_error"},
        }
    if 200 <= status_code < 300:
        payload: Any = None
        details: dict[str, Any] = {"status_code": status_code}
        if len(raw_payload) > MAX_RESPONSE_BYTES:
            details["error_class"] = "response_too_large"
        elif raw_payload:
            try:
                payload = json.loads(raw_payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                details["error_class"] = "invalid_json"
        return {
            "status": "healthy",
            "summary": f"HTTP {status_code}",
            "details": details,
            "payload": payload,
        }
    return {
        "status": "unhealthy",
        "summary": f"HTTP {status_code}",
        "details": {"status_code": status_code, "error_class": "http_status"},
    }


def _url_error_class(error: URLError) -> str:
    reason = error.reason
    if isinstance(reason, socket.gaierror):
        return "dns_error"
    if isinstance(reason, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timeout"
    return "connection_error"


def _url_error_summary(error: URLError) -> str:
    return "timeout" if _url_error_class(error) == "timeout" else "connection error"


def _code_version(project_root: Path) -> str:
    git_dir = project_root / ".git"
    try:
        if git_dir.is_file():
            pointer = git_dir.read_text(encoding="utf-8").strip()
            if not pointer.startswith("gitdir: "):
                return "unavailable"
            location = Path(pointer.removeprefix("gitdir: ").strip())
            git_dir = location if location.is_absolute() else (project_root / location)
        head = (git_dir / "HEAD").read_text(encoding="ascii").strip()
        if head.startswith("ref: "):
            reference = head.removeprefix("ref: ").strip()
            if not reference.startswith("refs/") or ".." in Path(reference).parts:
                return "unavailable"
            head = (git_dir / reference).read_text(encoding="ascii").strip()
    except OSError:
        return "unavailable"
    return head[:12] if re.fullmatch(r"[0-9a-f]{40}", head) else "unavailable"
