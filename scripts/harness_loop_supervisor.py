#!/usr/bin/env python3
"""Project-level runtime supervisor for loop services and runs."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from scripts import harness_loop_auto_resume as auto_resume
    from scripts.harness_loop_supervisor_state import (
        append_jsonl,
        build_supervisor_state,
        make_failure_key,
        open_user_decision,
        read_jsonl,
        supervisor_dir,
        utc_now_iso,
    )
except ImportError:  # pragma: no cover - direct script execution from scripts/
    import harness_loop_auto_resume as auto_resume  # type: ignore[no-redef]
    from harness_loop_supervisor_state import (  # type: ignore[no-redef]
        append_jsonl,
        build_supervisor_state,
        make_failure_key,
        open_user_decision,
        read_jsonl,
        supervisor_dir,
        utc_now_iso,
    )


SUPPORTED_STOPPED_BLOCKED_NEXT_ACTIONS = {"inspect_autonomous_dirty_paths", "inspect_required_evidence"}
ACTIONABLE_PHASES = {"audit_blocked", "stopped_blocked"}
AUTONOMOUS_ACTIVE_PHASES = {"planning", "generating", "evaluating", "artifact_hygiene", "cleanup"}
DEMAND_ACTIVE_PHASES = {
    "preflight",
    "planned",
    "generating",
    "verifying",
    "evaluating",
    "repair_needed",
    "artifact_hygiene",
    "cleanup",
    "audit_pending",
    "auditing",
    "child_running",
}
ALLOWED_RESTART_SESSIONS = {
    "personal-wiki-crawler-backend": (
        "cd {project_root}/personal-wiki/apps/crawler_workbench/backend && "
        "PYTHONPATH=$PWD PW_WORKBENCH_REPO_ROOT={project_root} "
        "python3 -m uvicorn crawler_workbench.main:app --host 0.0.0.0 --port 8765"
    ),
    "personal-wiki-crawler-frontend": (
        "cd {project_root}/personal-wiki/apps/crawler_workbench/frontend && "
        "npm run dev -- --host 0.0.0.0 --port 5173"
    ),
    "loop-dashboard": (
        "cd {project_root} && PYTHONPATH=apps/loop_dashboard/backend "
        "python3 -m uvicorn loop_dashboard.main:app --host 0.0.0.0 --port 8766"
    ),
    "loop-auto-resume": (
        "cd {project_root} && python3 scripts/harness_loop_auto_resume.py "
        "--project-root {project_root} --watch --interval-seconds 30"
    ),
}
DEFAULT_SERVICES = (
    {
        "service": "crawler-backend",
        "kind": "http_and_tmux",
        "expected_endpoint": "http://127.0.0.1:8765/api/health",
        "tmux_session": "personal-wiki-crawler-backend",
        "port": 8765,
    },
    {
        "service": "crawler-frontend",
        "kind": "http_and_tmux",
        "expected_endpoint": "http://127.0.0.1:5173/",
        "tmux_session": "personal-wiki-crawler-frontend",
        "port": 5173,
    },
    {
        "service": "loop-dashboard",
        "kind": "http_and_tmux",
        "expected_endpoint": "http://127.0.0.1:8766/api/health",
        "tmux_session": "loop-dashboard",
        "port": 8766,
    },
    {
        "service": "loop-auto-resume",
        "kind": "tmux",
        "expected_endpoint": "",
        "tmux_session": "loop-auto-resume",
        "port": None,
    },
)


@dataclass(frozen=True)
class SupervisorConfig:
    project_root: Path
    mode: str = "once"
    watch_interval_seconds: int = 30
    include_worktrees: bool = True
    dry_run: bool = False
    restart_services: bool = False
    create_continuations: bool = True


@dataclass(frozen=True)
class ServiceConfig:
    service: str
    kind: str
    expected_endpoint: str = ""
    tmux_session: str = ""
    port: int | None = None
    timeout_seconds: float = 1.0


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    repo_root: Path
    run_json_path: Path
    payload: dict[str, Any]
    valid: bool = True
    error: str = ""


def run_supervisor_once(config: SupervisorConfig) -> dict[str, Any]:
    root = Path(config.project_root)
    sup_dir = supervisor_dir(root)
    sup_dir.mkdir(parents=True, exist_ok=True)
    _touch_required_streams(sup_dir)
    append_jsonl(sup_dir / "events.jsonl", _event("tick_started", "Supervisor tick started.", config))

    service_health = _check_all_services(config)
    _write_json(
        sup_dir / "service-health.json",
        {"schema_version": 1, "checked_at": utc_now_iso(), "services": service_health},
    )

    run_records = discover_run_records(root, include_worktrees=config.include_worktrees)
    decisions: list[dict[str, Any]] = []
    continuation_candidates = 0
    active = 0
    blocked = 0
    needs_user_decision = 0
    resume_needed = False

    for record in run_records:
        if not record.valid:
            append_jsonl(
                sup_dir / "events.jsonl",
                {
                    **_event("invalid_run_json", "Invalid run.json encountered.", config),
                    "run_id": record.run_id,
                    "run_json": str(record.run_json_path),
                    "error": record.error,
                },
            )
            classification = _invalid_run_classification(record)
        else:
            classification = classify_run(record)

        decision = _record_run_decision(config, record, classification)
        decisions.append(decision)
        if classification["classification"] == "continuation_candidate":
            continuation_candidates += 1
            if config.create_continuations:
                plan = plan_continuation(config, record)
                decision["continuation_plan_id"] = plan.get("plan_id")
                decision["continuation_plan_status"] = plan.get("status")
        elif classification["classification"] == "active":
            active += 1
        elif classification["classification"] in {"actionable_resume", "blocked"}:
            blocked += 1
            if classification["action"] == "resume":
                resume_needed = True
        elif classification["classification"] == "needs_user_decision":
            needs_user_decision += 1
            _open_classification_user_decision(config, record, classification)
        elif classification["classification"] == "awaiting_human_merge":
            decision["requires_human_confirmation"] = True

    auto_resume_result = _empty_auto_resume_result(root)
    if resume_needed:
        auto_resume_result = auto_resume.resume_once(
            project_root=root,
            include_worktrees=config.include_worktrees,
            planner_driver="fake" if config.dry_run else "codex-exec",
            generator_driver="fake" if config.dry_run else "codex-exec",
            evaluator_driver="fake" if config.dry_run else "codex-exec",
            max_eval_attempts=2,
            max_children=3,
            max_tasks=3,
            dry_run=config.dry_run,
        )

    restart_results = _maybe_restart_services(config, service_health)
    open_failure_keys = _count_open_user_decisions(root)
    run_summary = {
        "active": active,
        "blocked": blocked,
        "continuation_candidates": continuation_candidates,
        "needs_user_decision": needs_user_decision,
    }
    failure_summary = {"open_failure_keys": open_failure_keys}
    service_health_by_name = {item["service"]: item for item in service_health}
    last_decision = decisions[-1] if decisions else None
    state = build_supervisor_state(
        root,
        mode=config.mode,
        service_health=service_health_by_name,
        run_summary=run_summary,
        failure_summary=failure_summary,
        last_decision=last_decision,
        watch_interval_seconds=config.watch_interval_seconds,
    )
    append_jsonl(
        sup_dir / "events.jsonl",
        {
            **_event("tick_completed", "Supervisor tick completed.", config),
            "status": state["status"],
            "run_summary": run_summary,
            "service_summary": state["service_summary"],
        },
    )
    return {
        **state,
        "service_health_path": str(sup_dir / "service-health.json"),
        "run_records": len(run_records),
        "auto_resume": auto_resume_result,
        "restart_results": restart_results,
    }


def discover_run_records(project_root: Path, include_worktrees: bool = True) -> list[RunRecord]:
    root = Path(project_root)
    records: list[RunRecord] = []
    for run_json_path in _run_json_paths(root, include_worktrees=include_worktrees):
        repo_root = _repo_root_for_run_json(root, run_json_path)
        try:
            payload = _read_json(run_json_path)
            run_id = str(payload.get("run_id") or run_json_path.parent.name)
            records.append(RunRecord(run_id=run_id, repo_root=repo_root, run_json_path=run_json_path, payload=payload))
        except Exception as exc:
            records.append(
                RunRecord(
                    run_id=run_json_path.parent.name,
                    repo_root=repo_root,
                    run_json_path=run_json_path,
                    payload={},
                    valid=False,
                    error=str(exc),
                )
            )
    return records


def classify_run(run_record: RunRecord, auditor_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    if not run_record.valid:
        return _invalid_run_classification(run_record)

    run = run_record.payload
    policy = str(run.get("policy") or "")
    phase = str(run.get("phase") or "")
    next_action = str(run.get("next_action") or "")
    auditor_verdict = str((auditor_summary or {}).get("verdict") or "")
    base = {
        "run_id": run_record.run_id,
        "run_policy": policy,
        "phase": phase,
        "next_action": next_action,
        "auditor_verdict": auditor_verdict or "unavailable",
        "evidence_paths": [_relative_to_repo(run_record.repo_root, run_record.run_json_path)],
    }

    if auditor_verdict == "stop":
        return {
            **base,
            "classification": "needs_user_decision",
            "action": "request_user_decision",
            "reason": "auditor_stop",
        }
    if _has_unsafe_secret_signal(run):
        return {
            **base,
            "classification": "needs_user_decision",
            "action": "request_user_decision",
            "reason": "unsafe_secret",
        }
    if policy == "autonomous_knowledge":
        return _classify_autonomous_run(base, phase, next_action)
    if policy == "demand_development":
        return _classify_demand_run(base, phase, next_action)
    return {
        **base,
        "classification": "needs_user_decision",
        "action": "request_user_decision",
        "reason": "unsupported_state",
    }


def check_service_health(config: SupervisorConfig, service: ServiceConfig) -> dict[str, Any]:
    root = Path(config.project_root)
    now = utc_now_iso()
    errors: list[str] = []
    reachable = True
    if "http" in service.kind:
        reachable, message = _check_http_endpoint(service.expected_endpoint, service.timeout_seconds)
        if not reachable:
            errors.append(message)
    tmux_ok = True
    if "tmux" in service.kind:
        tmux_ok, message = _tmux_has_session(service.tmux_session)
        if not tmux_ok:
            errors.append(message)

    runtime_path = root / ".codex" / "service-runtime" / f"{service.service}.json"
    running_version = _check_running_version(root, service, runtime_path, reachable=reachable, tmux_ok=tmux_ok)
    if not running_version["matches_expected"]:
        errors.append(str(running_version["evidence"]))

    status = "healthy" if not errors else "degraded"
    return {
        "service": service.service,
        "kind": service.kind,
        "expected_endpoint": service.expected_endpoint,
        "tmux_session": service.tmux_session,
        "status": status,
        "reachable": reachable,
        "tmux_session_exists": tmux_ok,
        "running_version": running_version,
        "data_freshness": {"status": "not_applicable", "target_id": "", "checks": []},
        "last_checked_at": now,
        "last_restart_at": "",
        "last_error": "; ".join(_unique_strings(errors)),
    }


def plan_continuation(config: SupervisorConfig, run_record: RunRecord) -> dict[str, Any]:
    if not run_record.valid:
        raise ValueError(f"cannot plan continuation for invalid run: {run_record.run_id}")
    classification = classify_run(run_record)
    if classification.get("classification") != "continuation_candidate":
        raise ValueError(f"run is not an autonomous continuation candidate: {run_record.run_id}")

    root = Path(config.project_root)
    plans_path = supervisor_dir(root) / "continuation-plans.jsonl"
    run = run_record.payload
    parent_counter = _parent_counter(run)
    previous_commit = _previous_commit(run_record)
    idempotency_key = (
        f"autonomous_knowledge:{run.get('domain') or 'unknown'}:"
        f"{run_record.run_id}:parent-{parent_counter}:{previous_commit}"
    )
    for existing in read_jsonl(plans_path):
        if existing.get("idempotency_key") == idempotency_key and existing.get("status") in {"planned", "created"}:
            return existing

    existing_count = len(read_jsonl(plans_path)) + 1
    next_run_id = f"{run_record.run_id}-continuation-{existing_count:03d}"
    plan = {
        "schema_version": 1,
        "plan_id": f"continuation-{_safe_slug(run_record.run_id)}-{existing_count:03d}",
        "idempotency_key": idempotency_key,
        "previous_run_id": run_record.run_id,
        "next_run_id": next_run_id,
        "domain": str(run.get("domain") or ""),
        "policy_file": str(run.get("policy_file") or ""),
        "previous_phase": str(run.get("phase") or ""),
        "previous_task_id": str(run.get("task_id") or ""),
        "previous_commit": previous_commit,
        "parent_task_counter": parent_counter,
        "audit_cadence_state": {"unit": "parent_task", "interval": 2, "completed_since_last_audit": 0},
        "global_stop_result": {"status": "continue", "checked_conditions": []},
        "status": "planned" if config.create_continuations else "skipped",
        "created_run_path": _relative_to_repo(
            root,
            root / ".codex" / "loop-runs" / next_run_id / "run.json",
        ),
        "created_at": utc_now_iso(),
        "dry_run": config.dry_run,
    }
    append_jsonl(plans_path, plan)
    return plan


def restart_service(config: SupervisorConfig, tmux_session: str) -> dict[str, Any]:
    if tmux_session not in ALLOWED_RESTART_SESSIONS:
        raise ValueError(f"service restart session is not allowlisted: {tmux_session}")
    if config.dry_run:
        return {
            "session": tmux_session,
            "status": "dry_run",
            "summary": "restart skipped because supervisor is in dry-run mode",
        }
    if not config.restart_services:
        return {"session": tmux_session, "status": "skipped", "summary": "service restart disabled"}

    command = ALLOWED_RESTART_SESSIONS[tmux_session].format(project_root=Path(config.project_root))
    existing, _ = _tmux_has_session(tmux_session)
    if existing:
        return {"session": tmux_session, "status": "skipped", "summary": "tmux session already exists"}
    result = subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session, command],
        cwd=Path(config.project_root),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux restart failed for {tmux_session}: {result.stderr or result.stdout}")
    return {"session": tmux_session, "status": "started", "summary": "tmux session started from allowlist"}


def _classify_autonomous_run(base: dict[str, Any], phase: str, next_action: str) -> dict[str, Any]:
    if phase in AUTONOMOUS_ACTIVE_PHASES:
        return {**base, "classification": "actionable_resume", "action": "resume", "reason": "active_autonomous_phase"}
    if phase == "audit_blocked":
        return {**base, "classification": "actionable_resume", "action": "resume", "reason": "audit_blocked"}
    if phase == "stopped_blocked":
        if next_action in SUPPORTED_STOPPED_BLOCKED_NEXT_ACTIONS:
            return {
                **base,
                "classification": "actionable_resume",
                "action": "resume",
                "reason": "supported_stopped_blocked",
            }
        return {
            **base,
            "classification": "needs_user_decision",
            "action": "request_user_decision",
            "reason": "unsupported_state",
        }
    if phase == "stopped_budget":
        return {
            **base,
            "classification": "continuation_candidate",
            "action": "create_continuation",
            "reason": "autonomous_budget_stop",
        }
    if phase in {"stopped_no_action", "audit_passed", "committed"}:
        return {**base, "classification": "terminal", "action": "observe", "reason": "terminal_no_action"}
    return {
        **base,
        "classification": "needs_user_decision",
        "action": "request_user_decision",
        "reason": "unsupported_state",
    }


def _classify_demand_run(base: dict[str, Any], phase: str, next_action: str) -> dict[str, Any]:
    if phase in DEMAND_ACTIVE_PHASES:
        return {**base, "classification": "active", "action": "observe", "reason": "active_demand_phase"}
    if phase == "audit_blocked":
        return {**base, "classification": "actionable_resume", "action": "resume", "reason": "audit_blocked"}
    if phase == "stopped_blocked" and next_action in SUPPORTED_STOPPED_BLOCKED_NEXT_ACTIONS:
        return {
            **base,
            "classification": "actionable_resume",
            "action": "resume",
            "reason": "supported_stopped_blocked",
        }
    if phase == "passed_waiting_human_merge":
        return {
            **base,
            "classification": "awaiting_human_merge",
            "action": "await_human_merge",
            "reason": "human_merge_required",
        }
    if phase in {"stopped_no_action", "audit_passed", "committed"}:
        return {**base, "classification": "terminal", "action": "observe", "reason": "terminal_no_action"}
    return {
        **base,
        "classification": "needs_user_decision",
        "action": "request_user_decision",
        "reason": "unsupported_state",
    }


def _record_run_decision(
    config: SupervisorConfig,
    record: RunRecord,
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    decisions_path = supervisor_dir(config.project_root) / "run-decisions.jsonl"
    existing_count = len(read_jsonl(decisions_path))
    decision = {
        "schema_version": 1,
        "decision_id": f"supervisor-{existing_count + 1:06d}",
        "run_id": record.run_id,
        "repo_root": str(record.repo_root),
        "run_policy": classification.get("run_policy", ""),
        "phase": classification.get("phase", ""),
        "next_action": classification.get("next_action", ""),
        "classification": classification.get("classification", ""),
        "action": classification.get("action", ""),
        "reason": classification.get("reason", ""),
        "auditor_verdict": classification.get("auditor_verdict", "unavailable"),
        "created_at": utc_now_iso(),
        "evidence_paths": list(classification.get("evidence_paths", [])),
        "dry_run": config.dry_run,
    }
    append_jsonl(decisions_path, decision)
    return decision


def _open_classification_user_decision(
    config: SupervisorConfig,
    record: RunRecord,
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    reason = str(classification.get("reason") or "unsupported_state")
    if reason == "auditor_stop":
        failure_key = make_failure_key("auditor_stop", record.run_id, "latest-audit", "stop")
        summary = f"Auditor requested stop for run {record.run_id}."
        required = "Review the auditor stop conclusion and choose whether to stop or continue manually."
    elif reason == "unsafe_secret":
        failure_key = make_failure_key("unsafe_secret", record.run_id, "run-artifacts", "secret-signal")
        summary = f"Unsafe secret signal found for run {record.run_id}."
        required = "Inspect artifacts for secrets before any automatic continuation."
    else:
        failure_key = make_failure_key("unsupported_state", record.run_id, "run-state", reason)
        summary = f"Run {record.run_id} is in an unsupported supervisor state."
        required = "Inspect the run state and choose the next operational action."
    return open_user_decision(
        config.project_root,
        reason=reason,
        failure_key=failure_key,
        summary=summary,
        required_user_decision=required,
        affected_runs=[record.run_id],
        attempts=[],
    )


def _invalid_run_classification(record: RunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "run_policy": "invalid",
        "phase": "invalid",
        "next_action": "",
        "auditor_verdict": "unavailable",
        "classification": "needs_user_decision",
        "action": "request_user_decision",
        "reason": "unsupported_state",
        "evidence_paths": [_relative_to_repo(record.repo_root, record.run_json_path)],
    }


def _check_all_services(config: SupervisorConfig) -> list[dict[str, Any]]:
    services = [ServiceConfig(**item) for item in DEFAULT_SERVICES]
    return [check_service_health(config, service) for service in services]


def _check_running_version(
    project_root: Path,
    service: ServiceConfig,
    runtime_path: Path,
    *,
    reachable: bool,
    tmux_ok: bool,
) -> dict[str, Any]:
    rel_path = _relative_to_repo(project_root, runtime_path)
    if not runtime_path.exists():
        return {
            "git_head": "",
            "origin_main": "",
            "matches_expected": False,
            "freshness": "unavailable",
            "runtime_metadata_path": rel_path,
            "evidence": "runtime metadata missing; version freshness unavailable",
        }

    errors: list[str] = []
    try:
        metadata = _read_json(runtime_path)
    except Exception as exc:
        return {
            "git_head": "",
            "origin_main": "",
            "matches_expected": False,
            "freshness": "unavailable",
            "runtime_metadata_path": rel_path,
            "evidence": f"runtime metadata invalid: {exc}",
        }

    git_head = str(metadata.get("git_head") or "")
    origin_main = str(metadata.get("origin_main") or "")
    if service.port is not None and metadata.get("port") != service.port:
        errors.append(f"runtime port mismatch: expected {service.port}, got {metadata.get('port')}")
    if service.tmux_session and metadata.get("tmux_session") != service.tmux_session:
        errors.append(
            f"runtime tmux session mismatch: expected {service.tmux_session}, got {metadata.get('tmux_session')}"
        )
    cwd_path = Path(str(metadata.get("cwd") or project_root))
    if not _is_under(cwd_path, project_root):
        errors.append(f"runtime cwd is outside project root: {cwd_path}")
    pid = metadata.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        errors.append("runtime pid missing or invalid")
    elif not _pid_exists(pid):
        errors.append(f"runtime pid is not running: {pid}")
    expected_head = ""
    try:
        expected_head = _git_head(cwd_path)
    except RuntimeError as exc:
        errors.append(str(exc))
    if expected_head and git_head != expected_head:
        errors.append(f"git head mismatch: runtime {git_head or 'missing'} != expected {expected_head}")
    if not reachable:
        errors.append("endpoint is not reachable")
    if not tmux_ok:
        errors.append("tmux session is missing")

    matches_expected = not errors
    return {
        "git_head": git_head,
        "origin_main": origin_main,
        "matches_expected": matches_expected,
        "freshness": "fresh" if matches_expected else "stale",
        "runtime_metadata_path": rel_path,
        "evidence": "runtime metadata matches expected version" if matches_expected else "; ".join(errors),
    }


def _maybe_restart_services(config: SupervisorConfig, service_health: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if config.dry_run or not config.restart_services:
        return []
    results: list[dict[str, Any]] = []
    for service in service_health:
        if service.get("status") == "healthy":
            continue
        session = str(service.get("tmux_session") or "")
        if not session:
            continue
        try:
            results.append(restart_service(config, session))
        except Exception as exc:
            service_name = str(service.get("service") or session)
            failure_key = make_failure_key("service_down", "project", service_name, "restart_failed")
            result = {
                "session": session,
                "service": service_name,
                "status": "error",
                "error": str(exc),
                "failure_key": failure_key,
            }
            open_user_decision(
                config.project_root,
                reason="service_unrecoverable",
                failure_key=failure_key,
                summary=f"Automatic restart failed for service {service_name}: {exc}",
                required_user_decision="Inspect the service manually and decide whether automatic restart should resume.",
                affected_runs=[],
                attempts=[result],
            )
            results.append(result)
    return results


def _run_json_paths(project_root: Path, *, include_worktrees: bool) -> list[Path]:
    paths = sorted((project_root / ".codex" / "loop-runs").glob("*/run.json"))
    if include_worktrees:
        worktrees_root = project_root / ".worktrees"
        if worktrees_root.exists():
            for worktree in sorted(worktrees_root.iterdir()):
                if worktree.is_dir() and not worktree.is_symlink():
                    paths.extend(sorted((worktree / ".codex" / "loop-runs").glob("*/run.json")))
    return paths


def _repo_root_for_run_json(project_root: Path, run_json_path: Path) -> Path:
    parts = run_json_path.resolve().parts
    for index in range(len(parts) - 2):
        if parts[index] == ".codex" and parts[index + 1] == "loop-runs":
            return Path(*parts[:index])
    return project_root


def _check_http_endpoint(endpoint: str, timeout_seconds: float) -> tuple[bool, str]:
    if not endpoint:
        return False, "endpoint not configured"
    try:
        request = Request(endpoint, method="GET")
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - local configured health URL.
            status = int(getattr(response, "status", 200))
        if status >= 400:
            return False, f"endpoint returned HTTP {status}: {endpoint}"
        return True, "endpoint reachable"
    except HTTPError as exc:
        return False, f"endpoint returned HTTP {exc.code}: {endpoint}"
    except (OSError, URLError) as exc:
        return False, f"endpoint unreachable: {endpoint}: {exc}"


def _tmux_has_session(session: str) -> tuple[bool, str]:
    if not session:
        return False, "tmux session not configured"
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except FileNotFoundError:
        return False, "tmux command unavailable"
    except subprocess.TimeoutExpired:
        return False, f"tmux has-session timed out for {session}"
    if result.returncode == 0:
        return True, "tmux session exists"
    return False, f"tmux session missing: {session}: {result.stderr or result.stdout}".strip()


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _git_head(cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(cwd),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git command failed: git executable not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("git command failed: git rev-parse HEAD timed out") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"git command failed: git rev-parse HEAD: {detail}")
    return result.stdout.strip()


def _previous_commit(record: RunRecord) -> str:
    run = record.payload
    for key in ("commit", "git_head", "head"):
        value = run.get(key)
        if isinstance(value, str) and value:
            return value
    try:
        return _git_head(record.repo_root)
    except RuntimeError as exc:
        return f"unknown-{_safe_slug(str(exc))}"


def _parent_counter(run: Mapping[str, Any]) -> int:
    candidates = [run.get("parent_task_counter"), run.get("task_id"), run.get("run_id")]
    for candidate in candidates:
        if isinstance(candidate, int) and candidate >= 0:
            return candidate
        if isinstance(candidate, str):
            match = re.search(r"parent-(\d+)", candidate)
            if match:
                return int(match.group(1))
    return 0


def _has_unsafe_secret_signal(run: Mapping[str, Any]) -> bool:
    for key in ("unsafe_secret_detected", "secret_detected"):
        if run.get(key) is True:
            return True
    signals = run.get("supervisor_signals")
    if isinstance(signals, Mapping):
        return bool(signals.get("unsafe_secret"))
    return False


def _count_open_user_decisions(project_root: Path) -> int:
    decisions_dir = supervisor_dir(project_root) / "needs-user-decisions"
    if not decisions_dir.exists():
        return 0
    count = 0
    for path in decisions_dir.glob("*.json"):
        try:
            payload = _read_json(path)
        except Exception:
            continue
        if payload.get("status") == "open":
            count += 1
    return count


def _event(event: str, summary: str, config: SupervisorConfig) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event": event,
        "created_at": utc_now_iso(),
        "project_root": str(config.project_root),
        "mode": config.mode,
        "dry_run": config.dry_run,
        "summary": summary,
    }


def _empty_auto_resume_result(project_root: Path) -> dict[str, Any]:
    return {
        "project_root": str(project_root),
        "candidate_count": 0,
        "resumed_count": 0,
        "dry_run_count": 0,
        "error_count": 0,
        "resumed": [],
        "errors": [],
    }


def _touch_required_streams(supervisor_root: Path) -> None:
    supervisor_root.mkdir(parents=True, exist_ok=True)
    for name in ("events.jsonl", "run-decisions.jsonl", "continuation-plans.jsonl", "recovery-attempts.jsonl"):
        (supervisor_root / name).touch(exist_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")


def _relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(repo_root).resolve()))
    except ValueError:
        return str(path)


def _is_under(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "unknown"


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), indent=2, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Loop Supervisor once or in watch mode.")
    parser.add_argument("--project-root", default=".")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--max-ticks", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-include-worktrees", action="store_true")
    parser.add_argument("--restart-services", action="store_true")
    parser.add_argument("--no-create-continuations", action="store_true")
    args = parser.parse_args(argv)

    config = SupervisorConfig(
        project_root=Path(args.project_root),
        mode="watch" if args.watch else "once",
        watch_interval_seconds=args.interval_seconds,
        include_worktrees=not args.no_include_worktrees,
        dry_run=args.dry_run,
        restart_services=args.restart_services,
        create_continuations=not args.no_create_continuations,
    )
    tick = 0
    while True:
        tick += 1
        result = run_supervisor_once(config)
        _print_json(result)
        if not args.watch or (args.max_ticks and tick >= args.max_ticks):
            return 0
        time.sleep(max(args.interval_seconds, 1))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
