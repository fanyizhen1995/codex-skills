import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.harness_loop_supervisor import (
    ServiceConfig,
    SupervisorConfig,
    check_service_health,
    classify_run,
    discover_run_records,
    restart_service,
    run_supervisor_once,
    write_service_runtime_metadata,
)
from scripts.harness_loop_supervisor_state import read_jsonl
from scripts.harness_loop_supervisor_state import append_jsonl, make_failure_key, open_user_decision


AI_INFRA_POLICY_FILE = "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


def seed_service_runtime(
    project_root: Path,
    service: str,
    *,
    port: int,
    git_head: str,
    tmux_session: str | None = None,
) -> Path:
    runtime_path = project_root / ".codex" / "service-runtime" / f"{service}.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "service": service,
                "tmux_session": tmux_session or service,
                "pid": 12345,
                "cwd": str(project_root),
                "command": "fake service command",
                "host": "127.0.0.1",
                "port": port,
                "repo_root": str(project_root),
                "git_head": git_head,
                "origin_main": git_head,
                "started_at": "2026-07-09T00:00:00Z",
                "config_fingerprint": "sha256:test",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return runtime_path


def seed_stopped_budget_autonomous_run(
    project_root: Path,
    run_id: str,
    *,
    parent_counter: int = 10,
    git_head: str = "abc123",
) -> Path:
    return seed_run(
        project_root,
        run_id,
        policy="autonomous_knowledge",
        phase="stopped_budget",
        next_action="none",
        last_result="pass",
        task_id=f"{run_id}-parent-{parent_counter}",
        domain="ai_infra",
        policy_file=AI_INFRA_POLICY_FILE,
        commit=git_head,
    )


def seed_audit_report(project_root: Path, run_id: str, audit_id: str, verdict: str) -> Path:
    report_path = project_root / ".codex" / "loop-runs" / run_id / "audit-reports" / f"{audit_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "audit_id": audit_id,
                "created_at": "2026-07-09T00:00:00Z",
                "created_by": "test",
                "verdict": verdict,
                "deterministic_signals": {
                    "artifact_path": f".codex/loop-runs/{run_id}/deterministic-signals.json",
                    "artifact_sha256": "a" * 64,
                    "summary": {},
                    "git_head_sha": "abc123",
                },
                "cadence": {"unit": "boundary", "current_interval": 1, "steps_since_last_audit": 1},
                "direction_control": {"action": "continue", "reason": "test verdict"},
                "finding_lifecycle": {"open_findings": [], "closed_findings": []},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return report_path


def seed_run(project_root: Path, run_id: str, **overrides: object) -> Path:
    run_dir = project_root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run = {
        "run_id": run_id,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "task_id": f"{run_id}-parent-1",
        "domain": "ai_infra",
        "branch": "main",
        "worktree": str(project_root),
        "requirement": "seeded supervisor test run",
        "constraints": [],
        "stop_conditions": ["stopped_no_action", "stopped_budget", "stopped_blocked"],
        "baseline_dirty_paths": [],
        "allowed_paths": ["personal-wiki/**"],
        "denylist_paths": [],
        "attempts": {
            "planner": 0,
            "generator": 0,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
            "auditor": 0,
        },
        "limits": {},
        "last_result": "none",
        "next_action": "run_autonomous_planner",
        "attempt_history": [],
        "cleanup": {},
        "policy_file": AI_INFRA_POLICY_FILE,
        "commit": "abc123",
    }
    run.update(overrides)
    (run_dir / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run_dir / "run.json"


def patch_service_checks(monkeypatch: pytest.MonkeyPatch, *, git_head: str = "abc123") -> None:
    monkeypatch.setattr("scripts.harness_loop_supervisor._check_http_endpoint", lambda endpoint, timeout: (True, "ok"))
    monkeypatch.setattr("scripts.harness_loop_supervisor._tmux_has_session", lambda session: (True, "exists"))
    monkeypatch.setattr("scripts.harness_loop_supervisor._pid_exists", lambda pid: True)
    monkeypatch.setattr("scripts.harness_loop_supervisor._git_head", lambda cwd: git_head)


def test_once_cli_writes_state_and_exits_zero(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/harness_loop_supervisor.py",
            "--project-root",
            str(tmp_path),
            "--once",
            "--dry-run",
            "--include-worktrees",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".codex" / "supervisor" / "supervisor-state.json").exists()


def test_watch_mode_can_stop_after_max_ticks(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/harness_loop_supervisor.py",
            "--project-root",
            str(tmp_path),
            "--watch",
            "--max-ticks",
            "1",
            "--interval-seconds",
            "1",
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    state = json.loads((tmp_path / ".codex" / "supervisor" / "supervisor-state.json").read_text(encoding="utf-8"))
    assert state["mode"] == "watch"
    assert state["last_heartbeat_at"]
    assert state["last_tick_at"]


def test_write_service_runtime_metadata_records_current_process_and_git_head(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.harness_loop_supervisor._git_head", lambda cwd: "abc123")

    metadata = write_service_runtime_metadata(
        tmp_path,
        service_name="loop-dashboard",
        command="python3 -m uvicorn loop_dashboard.main:app",
        host="127.0.0.1",
        port=8766,
        tmux_session="loop-dashboard",
        cwd=tmp_path,
    )

    runtime_path = tmp_path / ".codex" / "service-runtime" / "loop-dashboard.json"
    persisted = json.loads(runtime_path.read_text(encoding="utf-8"))
    assert metadata["service"] == "loop-dashboard"
    assert persisted["service"] == "loop-dashboard"
    assert persisted["pid"] == os.getpid()
    assert persisted["git_head"] == "abc123"
    assert persisted["origin_main"] == "abc123"
    assert persisted["runtime_metadata_path"] == ".codex/service-runtime/loop-dashboard.json"


def test_write_service_runtime_cli_writes_metadata(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.invalid"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    (tmp_path / "README.md").write_text("runtime metadata fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(
        ["git", "commit", "-m", "test fixture"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/harness_loop_supervisor.py",
            "--project-root",
            str(tmp_path),
            "--write-service-runtime",
            "loop-dashboard",
            "--service-command",
            "python3 -m uvicorn loop_dashboard.main:app",
            "--service-host",
            "127.0.0.1",
            "--service-port",
            "8766",
            "--service-tmux-session",
            "loop-dashboard",
            "--service-pid",
            str(os.getpid()),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / ".codex" / "service-runtime" / "loop-dashboard.json").read_text(encoding="utf-8"))
    assert payload["service"] == "loop-dashboard"
    assert payload["port"] == 8766


def test_run_supervisor_once_writes_required_artifacts(tmp_path, monkeypatch):
    seed_service_runtime(tmp_path, "loop-dashboard", port=8766, git_head="abc123", tmux_session="loop-dashboard")
    seed_stopped_budget_autonomous_run(tmp_path, "ai-infra-r10")
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    supervisor_root = tmp_path / ".codex" / "supervisor"
    assert result["status"] in {"healthy", "degraded"}
    assert (supervisor_root / "supervisor-state.json").exists()
    assert (supervisor_root / "service-health.json").exists()
    assert (supervisor_root / "run-decisions.jsonl").exists()
    assert (supervisor_root / "events.jsonl").exists()
    plans = read_jsonl(supervisor_root / "continuation-plans.jsonl")
    assert plans[0]["status"] == "planned"
    assert not (tmp_path / ".codex" / "loop-runs" / plans[0]["next_run_id"] / "run.json").exists()


def test_stopped_budget_autonomous_plan_is_idempotent(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "ai-infra-r10", parent_counter=14)
    patch_service_checks(monkeypatch)
    config = SupervisorConfig(project_root=tmp_path, dry_run=True)

    run_supervisor_once(config)
    second = run_supervisor_once(config)

    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    assert len(plans) == 1
    assert len({plan["idempotency_key"] for plan in plans}) == 1
    assert plans[0]["parent_task_counter"] == 14
    assert second["run_summary"]["continuation_candidates"] == 1


def test_existing_planned_continuation_is_reused_when_global_stop_opens(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "planned-before-stop", parent_counter=14)
    patch_service_checks(monkeypatch)
    config = SupervisorConfig(project_root=tmp_path, dry_run=True)

    run_supervisor_once(config)
    failure_key = make_failure_key("unsupported_state", "existing-run", "run-state", "needs-human")
    open_user_decision(
        tmp_path,
        reason="unsupported_state",
        failure_key=failure_key,
        summary="Operator decision opened after the continuation plan was already planned.",
        required_user_decision="Resolve the existing decision before continuing.",
        affected_runs=["existing-run"],
        attempts=[],
    )
    second = run_supervisor_once(config)

    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    idempotency_keys = [plan["idempotency_key"] for plan in plans]
    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    assert len(plans) == 1
    assert idempotency_keys == ["autonomous_knowledge:ai_infra:planned-before-stop:parent-14:abc123"]
    assert plans[0]["status"] == "planned"
    assert second["run_summary"]["continuation_candidates"] == 1
    assert decisions[-1]["run_id"] == "planned-before-stop"
    assert decisions[-1]["action"] == "observe"
    assert decisions[-1]["reason"] == "continuation_already_planned"


def test_restart_allowlist_rejects_unknown_session(tmp_path):
    with pytest.raises(ValueError):
        restart_service(SupervisorConfig(project_root=tmp_path), "rm-random-session")


def test_missing_service_runtime_reports_unavailable_version(tmp_path, monkeypatch):
    patch_service_checks(monkeypatch)
    service = ServiceConfig(
        service="loop-dashboard",
        kind="http_and_tmux",
        expected_endpoint="http://127.0.0.1:8766/api/health",
        tmux_session="loop-dashboard",
        port=8766,
    )

    health = check_service_health(SupervisorConfig(project_root=tmp_path), service)

    assert health["status"] == "degraded"
    assert health["running_version"]["freshness"] == "unavailable"
    assert health["running_version"]["matches_expected"] is False
    assert health["running_version"]["runtime_metadata_path"] == ".codex/service-runtime/loop-dashboard.json"
    assert "runtime metadata missing" in health["running_version"]["evidence"]


def test_missing_freshness_target_reports_explicit_missing_target(tmp_path, monkeypatch):
    patch_service_checks(monkeypatch)

    health = check_service_health(
        SupervisorConfig(project_root=tmp_path),
        ServiceConfig(
            service="crawler-backend",
            kind="http_and_tmux",
            expected_endpoint="http://127.0.0.1:8765/api/health",
            tmux_session="personal-wiki-crawler-backend",
            port=8765,
        ),
    )

    assert health["data_freshness"]["status"] == "not_applicable"
    assert health["data_freshness"]["status_label"] == "暂无 freshness target"
    assert "暂无 freshness target" in health["data_freshness"]["evidence"]


def test_service_health_attaches_target_specific_freshness_from_artifact(tmp_path, monkeypatch):
    patch_service_checks(monkeypatch)
    append_jsonl(
        tmp_path / ".codex" / "supervisor" / "freshness-targets.jsonl",
        {
            "target_id": "ai-infra-parent-14-atlas-300i-a2",
            "source_run_id": "ai-infra-expansion-continuation-20260708",
            "target_commit": "abc123",
            "domain": "ai_infra",
            "wiki_paths": ["personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-spec-catalog.md"],
            "search_terms": ["Atlas 300I A2", "64 GB"],
            "expected_frontend_text": ["Atlas 300I A2", "compute-accelerator-spec-catalog"],
            "api_checks": [
                {"kind": "crawler", "url": "http://127.0.0.1:8765/api/health", "status": "pass"},
                {"kind": "wiki-page", "url": "http://127.0.0.1:8765/api/wiki/page", "status": "pass"},
                {"kind": "search", "url": "http://127.0.0.1:8765/api/search", "status": "pass"},
            ],
            "frontend_checks": [{"page": "knowledge-workbench", "status": "pass"}],
            "status": "pass",
            "verified_at": "2026-07-09T00:00:00Z",
        },
    )

    backend = check_service_health(
        SupervisorConfig(project_root=tmp_path),
        ServiceConfig(
            service="crawler-backend",
            kind="http_and_tmux",
            expected_endpoint="http://127.0.0.1:8765/api/health",
            tmux_session="personal-wiki-crawler-backend",
            port=8765,
        ),
    )
    frontend = check_service_health(
        SupervisorConfig(project_root=tmp_path),
        ServiceConfig(
            service="crawler-frontend",
            kind="http_and_tmux",
            expected_endpoint="http://127.0.0.1:5173/",
            tmux_session="personal-wiki-crawler-frontend",
            port=5173,
        ),
    )

    assert backend["data_freshness"]["status"] == "pass"
    assert backend["data_freshness"]["target_id"] == "ai-infra-parent-14-atlas-300i-a2"
    assert backend["data_freshness"]["checks"] == ["crawler", "wiki-page", "search"]
    assert frontend["data_freshness"]["status"] == "pass"
    assert frontend["data_freshness"]["checks"] == ["frontend-visible"]


def test_malformed_freshness_target_is_reported_as_failed_not_green(tmp_path, monkeypatch):
    patch_service_checks(monkeypatch)
    targets_path = tmp_path / ".codex" / "supervisor" / "freshness-targets.jsonl"
    targets_path.parent.mkdir(parents=True, exist_ok=True)
    targets_path.write_text("{not json}\n", encoding="utf-8")

    health = check_service_health(
        SupervisorConfig(project_root=tmp_path),
        ServiceConfig(
            service="crawler-backend",
            kind="http_and_tmux",
            expected_endpoint="http://127.0.0.1:8765/api/health",
            tmux_session="personal-wiki-crawler-backend",
            port=8765,
        ),
    )

    assert health["status"] == "degraded"
    assert health["data_freshness"]["status"] == "fail"
    assert "malformed" in health["data_freshness"]["evidence"]


def test_git_command_failure_is_explicit_service_error(tmp_path, monkeypatch):
    seed_service_runtime(tmp_path, "loop-dashboard", port=8766, git_head="abc123", tmux_session="loop-dashboard")
    monkeypatch.setattr("scripts.harness_loop_supervisor._check_http_endpoint", lambda endpoint, timeout: (True, "ok"))
    monkeypatch.setattr("scripts.harness_loop_supervisor._tmux_has_session", lambda session: (True, "exists"))
    monkeypatch.setattr("scripts.harness_loop_supervisor._pid_exists", lambda pid: True)

    def fail_git_head(cwd: Path) -> str:
        raise RuntimeError("git command failed: rev-parse HEAD")

    monkeypatch.setattr("scripts.harness_loop_supervisor._git_head", fail_git_head)
    service = ServiceConfig(
        service="loop-dashboard",
        kind="http_and_tmux",
        expected_endpoint="http://127.0.0.1:8766/api/health",
        tmux_session="loop-dashboard",
        port=8766,
    )

    health = check_service_health(SupervisorConfig(project_root=tmp_path), service)

    assert health["status"] == "degraded"
    assert health["running_version"]["matches_expected"] is False
    assert "git command failed: rev-parse HEAD" in health["last_error"]
    assert "git command failed: rev-parse HEAD" in health["running_version"]["evidence"]


def test_service_restart_failures_open_user_decision_after_retry_ceiling(tmp_path, monkeypatch):
    degraded_service = {
        "service": "loop-dashboard",
        "kind": "http_and_tmux",
        "expected_endpoint": "http://127.0.0.1:8766/api/health",
        "tmux_session": "loop-dashboard",
        "status": "degraded",
        "reachable": False,
        "tmux_session_exists": False,
        "running_version": {
            "git_head": "",
            "origin_main": "",
            "matches_expected": False,
            "freshness": "unavailable",
            "runtime_metadata_path": ".codex/service-runtime/loop-dashboard.json",
            "evidence": "endpoint unreachable",
        },
        "data_freshness": {"status": "not_applicable", "target_id": "", "checks": []},
        "last_checked_at": "2026-07-09T00:00:00Z",
        "last_restart_at": "",
        "last_error": "endpoint unreachable",
    }
    monkeypatch.setattr("scripts.harness_loop_supervisor._check_all_services", lambda config: [degraded_service])

    def fail_restart(config: SupervisorConfig, tmux_session: str):
        raise RuntimeError("restart failed: tmux unavailable")

    monkeypatch.setattr("scripts.harness_loop_supervisor.restart_service", fail_restart)
    config = SupervisorConfig(project_root=tmp_path, restart_services=True)

    first = run_supervisor_once(config)
    second = run_supervisor_once(config)

    decisions_dir = tmp_path / ".codex" / "supervisor" / "needs-user-decisions"
    attempts = read_jsonl(tmp_path / ".codex" / "supervisor" / "recovery-attempts.jsonl")
    assert first["restart_results"][0]["status"] == "error"
    assert first["restart_results"][0]["recovery_attempt"]["consecutive_failure_count"] == 1
    assert second["restart_results"][0]["recovery_attempt"]["consecutive_failure_count"] == 2
    assert first["failure_summary"]["open_failure_keys"] == 0
    assert second["failure_summary"]["open_failure_keys"] == 0
    assert len(attempts) == 2
    assert not decisions_dir.exists()

    result = run_supervisor_once(config)

    decisions = sorted(decisions_dir.glob("*.json"))
    assert result["restart_results"][0]["status"] == "error"
    assert result["restart_results"][0]["recovery_attempt"]["consecutive_failure_count"] == 3
    assert result["failure_summary"]["open_failure_keys"] == 1
    assert len(decisions) == 1
    decision = json.loads(decisions[0].read_text(encoding="utf-8"))
    assert decision["reason"] == "retry_ceiling_exceeded"
    assert decision["failure_key"] == "service_down:project:loop-dashboard:restart-failed"
    assert "service_unrecoverable" in decision["attempts"][-1]["summary"]


def test_started_restart_records_failure_when_followup_health_stays_degraded(tmp_path, monkeypatch):
    degraded_service = {
        "service": "loop-dashboard",
        "kind": "http_and_tmux",
        "expected_endpoint": "http://127.0.0.1:8766/api/health",
        "tmux_session": "loop-dashboard",
        "status": "degraded",
        "reachable": False,
        "tmux_session_exists": False,
        "running_version": {
            "git_head": "",
            "origin_main": "",
            "matches_expected": False,
            "freshness": "unavailable",
            "runtime_metadata_path": ".codex/service-runtime/loop-dashboard.json",
            "evidence": "endpoint unreachable",
        },
        "data_freshness": {"status": "not_applicable", "target_id": "", "checks": []},
        "last_checked_at": "2026-07-09T00:00:00Z",
        "last_restart_at": "",
        "last_error": "endpoint unreachable",
    }
    monkeypatch.setattr("scripts.harness_loop_supervisor._check_all_services", lambda config: [degraded_service])
    monkeypatch.setattr(
        "scripts.harness_loop_supervisor.restart_service",
        lambda config, tmux_session: {
            "session": tmux_session,
            "status": "started",
            "summary": "tmux session started from allowlist",
        },
    )
    monkeypatch.setattr("scripts.harness_loop_supervisor.check_service_health", lambda config, service: degraded_service)
    config = SupervisorConfig(project_root=tmp_path, restart_services=True)

    first = run_supervisor_once(config)
    second = run_supervisor_once(config)

    attempts = read_jsonl(tmp_path / ".codex" / "supervisor" / "recovery-attempts.jsonl")
    assert first["restart_results"][0]["status"] == "started"
    assert first["restart_results"][0]["verification_status"] == "degraded"
    assert first["restart_results"][0]["recovery_attempt"]["consecutive_failure_count"] == 1
    assert second["restart_results"][0]["recovery_attempt"]["consecutive_failure_count"] == 2
    assert len(attempts) == 2


def test_dry_run_passes_dry_run_to_auto_resume(tmp_path, monkeypatch):
    seed_run(
        tmp_path,
        "audit-stuck",
        policy="autonomous_knowledge",
        phase="audit_blocked",
        next_action="create_audit_remediation_task",
        last_result="blocked",
    )
    patch_service_checks(monkeypatch)
    calls = []

    def fake_resume_once(**kwargs):
        calls.append(kwargs)
        return {
            "project_root": str(kwargs["project_root"]),
            "candidate_count": 1,
            "resumed_count": 0,
            "dry_run_count": 1,
            "error_count": 0,
            "resumed": [{"run_id": "audit-stuck", "status": "dry_run"}],
            "errors": [],
        }

    monkeypatch.setattr("scripts.harness_loop_supervisor.auto_resume.resume_once", fake_resume_once)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    assert calls
    assert calls[0]["dry_run"] is True
    assert result["auto_resume"]["dry_run_count"] == 1


def test_active_autonomous_run_counts_active_not_blocked_while_resumable(tmp_path, monkeypatch):
    seed_run(
        tmp_path,
        "planning-run",
        policy="autonomous_knowledge",
        phase="planning",
        next_action="run_autonomous_planner",
        last_result="none",
    )
    monkeypatch.setattr("scripts.harness_loop_supervisor._check_all_services", lambda config: [])
    calls = []

    def fake_resume_once(**kwargs):
        calls.append(kwargs)
        return {
            "project_root": str(kwargs["project_root"]),
            "candidate_count": 1,
            "resumed_count": 0,
            "dry_run_count": 1,
            "error_count": 0,
            "resumed": [{"run_id": "planning-run", "status": "dry_run"}],
            "errors": [],
        }

    monkeypatch.setattr("scripts.harness_loop_supervisor.auto_resume.resume_once", fake_resume_once)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    assert calls
    assert result["run_summary"]["active"] == 1
    assert result["run_summary"]["blocked"] == 0
    assert result["status"] == "healthy"


def test_demand_development_human_merge_is_not_continued(tmp_path, monkeypatch):
    seed_run(
        tmp_path,
        "human-merge",
        policy="demand_development",
        phase="passed_waiting_human_merge",
        next_action="await_human_merge_confirmation",
        last_result="pass",
        task_id="human-merge",
        domain="",
    )
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    assert plans == []
    assert result["run_summary"]["continuation_candidates"] == 0
    assert any(
        decision["run_id"] == "human-merge" and decision["action"] == "await_human_merge"
        for decision in decisions
    )


def test_discover_run_records_includes_worktree_runs(tmp_path):
    seed_run(tmp_path, "root-run")
    worktree_root = tmp_path / ".worktrees" / "child-worktree"
    seed_run(worktree_root, "worktree-run")

    records = discover_run_records(tmp_path, include_worktrees=True)

    assert [record.run_id for record in records] == ["root-run", "worktree-run"]
    assert records[1].repo_root == worktree_root


def test_unsupported_phase_opens_user_decision(tmp_path, monkeypatch):
    seed_run(tmp_path, "unknown-phase", phase="mystery", next_action="none")
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    decisions = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    assert result["run_summary"]["needs_user_decision"] == 1
    assert len(decisions) == 1
    decision = json.loads(decisions[0].read_text(encoding="utf-8"))
    assert decision["reason"] == "unsupported_state"
    assert decision["affected_runs"] == ["unknown-phase"]


def test_classify_run_marks_auditor_stop_as_user_decision(tmp_path):
    run_json = seed_stopped_budget_autonomous_run(tmp_path, "audit-stop")
    record = discover_run_records(tmp_path, include_worktrees=False)[0]

    classification = classify_run(record, auditor_summary={"verdict": "stop"})

    assert record.run_json_path == run_json
    assert classification["classification"] == "needs_user_decision"
    assert classification["action"] == "request_user_decision"
    assert classification["reason"] == "auditor_stop"


def test_run_supervisor_once_loads_latest_auditor_stop_and_blocks_continuation(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "audit-stop")
    seed_audit_report(tmp_path, "audit-stop", "audit-001", "pass")
    latest_report = seed_audit_report(tmp_path, "audit-stop", "audit-002", "stop")
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    user_decisions = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    assert result["run_summary"]["continuation_candidates"] == 0
    assert result["run_summary"]["needs_user_decision"] == 1
    assert plans == []
    assert decisions[-1]["run_id"] == "audit-stop"
    assert decisions[-1]["auditor_verdict"] == "stop"
    assert decisions[-1]["action"] == "request_user_decision"
    assert decisions[-1]["reason"] == "auditor_stop"
    assert str(latest_report.relative_to(tmp_path)) in decisions[-1]["evidence_paths"]
    assert len(user_decisions) == 1
    assert json.loads(user_decisions[0].read_text(encoding="utf-8"))["reason"] == "auditor_stop"


def test_stopped_budget_auditor_must_fix_requests_user_decision_without_continuation(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "audit-must-fix")
    seed_audit_report(tmp_path, "audit-must-fix", "audit-001", "must_fix")
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    user_decisions = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    assert result["run_summary"]["continuation_candidates"] == 0
    assert result["run_summary"]["needs_user_decision"] == 1
    assert plans == []
    assert decisions[-1]["run_id"] == "audit-must-fix"
    assert decisions[-1]["auditor_verdict"] == "must_fix"
    assert decisions[-1]["classification"] == "needs_user_decision"
    assert decisions[-1]["action"] == "request_user_decision"
    assert decisions[-1]["reason"] == "auditor_must_fix"
    assert len(user_decisions) == 1
    assert json.loads(user_decisions[0].read_text(encoding="utf-8"))["reason"] == "auditor_must_fix"


def test_stopped_budget_auditor_refocus_requests_user_decision_without_continuation(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "audit-refocus")
    seed_audit_report(tmp_path, "audit-refocus", "audit-001", "refocus")
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    assert result["run_summary"]["continuation_candidates"] == 0
    assert result["run_summary"]["needs_user_decision"] == 1
    assert plans == []
    assert decisions[-1]["run_id"] == "audit-refocus"
    assert decisions[-1]["auditor_verdict"] == "refocus"
    assert decisions[-1]["classification"] == "needs_user_decision"
    assert decisions[-1]["action"] == "request_user_decision"
    assert decisions[-1]["reason"] == "auditor_refocus"


def test_stopped_budget_auditor_should_fix_records_control_input_without_continuation(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "audit-should-fix")
    seed_audit_report(tmp_path, "audit-should-fix", "audit-001", "should_fix")
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    user_decisions_dir = tmp_path / ".codex" / "supervisor" / "needs-user-decisions"
    assert result["run_summary"]["continuation_candidates"] == 0
    assert result["run_summary"]["needs_user_decision"] == 0
    assert plans == []
    assert decisions[-1]["run_id"] == "audit-should-fix"
    assert decisions[-1]["auditor_verdict"] == "should_fix"
    assert decisions[-1]["classification"] == "auditor_control"
    assert decisions[-1]["action"] == "observe"
    assert decisions[-1]["reason"] == "auditor_should_fix"
    assert not user_decisions_dir.exists()


def test_stopped_budget_blocks_continuation_when_open_user_decision_exists(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "blocked-by-global-stop")
    failure_key = make_failure_key("unsupported_state", "existing-run", "run-state", "needs-human")
    open_user_decision(
        tmp_path,
        reason="unsupported_state",
        failure_key=failure_key,
        summary="Existing open decision blocks autonomous continuation.",
        required_user_decision="Resolve the existing decision before continuing.",
        affected_runs=["existing-run"],
        attempts=[],
    )
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    decision_files = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    assert result["status"] == "blocked"
    assert result["run_summary"]["continuation_candidates"] == 0
    assert result["run_summary"]["needs_user_decision"] == 1
    assert len(decision_files) == 1
    assert len(plans) == 1
    assert plans[0]["status"] == "blocked"
    assert plans[0]["global_stop_result"]["status"] in {"blocked", "stop"}
    assert plans[0]["global_stop_result"]["checked_conditions"][0]["condition"] == "open_user_decisions"
    assert decisions[-1]["run_id"] == "blocked-by-global-stop"
    assert decisions[-1]["action"] == "request_user_decision"
    assert decisions[-1]["reason"] == "global_stop_open_user_decision"


def test_existing_blocked_continuation_plan_becomes_planned_without_duplicate_after_global_stop_resolves(
    tmp_path, monkeypatch
):
    seed_stopped_budget_autonomous_run(tmp_path, "blocked-then-clear", parent_counter=14)
    failure_key = make_failure_key("unsupported_state", "existing-run", "run-state", "needs-human")
    decision = open_user_decision(
        tmp_path,
        reason="unsupported_state",
        failure_key=failure_key,
        summary="Existing open decision blocks autonomous continuation.",
        required_user_decision="Resolve the existing decision before continuing.",
        affected_runs=["existing-run"],
        attempts=[],
    )
    patch_service_checks(monkeypatch)
    config = SupervisorConfig(project_root=tmp_path, dry_run=True)

    first = run_supervisor_once(config)
    decision_path = tmp_path / ".codex" / "supervisor" / "needs-user-decisions" / f"{decision['decision_id']}.json"
    persisted_decision = json.loads(decision_path.read_text(encoding="utf-8"))
    persisted_decision["status"] = "closed"
    decision_path.write_text(json.dumps(persisted_decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    second = run_supervisor_once(config)

    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    idempotency_keys = [plan["idempotency_key"] for plan in plans]
    assert first["run_summary"]["needs_user_decision"] == 1
    assert second["run_summary"]["continuation_candidates"] == 1
    assert len(plans) == 1
    assert idempotency_keys == ["autonomous_knowledge:ai_infra:blocked-then-clear:parent-14:abc123"]
    assert plans[0]["status"] == "planned"
    assert plans[0]["global_stop_result"]["status"] == "continue"


def test_existing_created_continuation_plan_records_observe_decision(tmp_path, monkeypatch):
    seed_stopped_budget_autonomous_run(tmp_path, "already-created", parent_counter=14)
    plans_path = tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl"
    append_jsonl(
        plans_path,
        {
            "schema_version": 1,
            "plan_id": "continuation-already-created-001",
            "idempotency_key": "autonomous_knowledge:ai_infra:already-created:parent-14:abc123",
            "previous_run_id": "already-created",
            "next_run_id": "already-created-continuation-001",
            "domain": "ai_infra",
            "policy_file": AI_INFRA_POLICY_FILE,
            "previous_phase": "stopped_budget",
            "previous_task_id": "already-created-parent-14",
            "previous_commit": "abc123",
            "parent_task_counter": 14,
            "audit_cadence_state": {"unit": "parent_task", "interval": 2, "completed_since_last_audit": 0},
            "global_stop_result": {"status": "continue", "checked_conditions": []},
            "status": "created",
            "created_run_path": ".codex/loop-runs/already-created-continuation-001/run.json",
            "created_at": "2026-07-09T00:00:00Z",
            "dry_run": False,
        },
    )
    patch_service_checks(monkeypatch)

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))

    plans = read_jsonl(plans_path)
    decisions = read_jsonl(tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl")
    assert result["run_summary"]["continuation_candidates"] == 1
    assert len(plans) == 1
    assert decisions[-1]["run_id"] == "already-created"
    assert decisions[-1]["classification"] == "continuation_candidate"
    assert decisions[-1]["action"] == "observe"
    assert decisions[-1]["reason"] == "continuation_already_created"
