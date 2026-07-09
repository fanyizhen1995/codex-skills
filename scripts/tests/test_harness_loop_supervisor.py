import json
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
)
from scripts.harness_loop_supervisor_state import read_jsonl


AI_INFRA_POLICY_FILE = "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json"


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


def test_service_restart_failure_opens_user_decision(tmp_path, monkeypatch):
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

    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, restart_services=True))

    decisions = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    assert result["restart_results"][0]["status"] == "error"
    assert result["failure_summary"]["open_failure_keys"] == 1
    assert len(decisions) == 1
    decision = json.loads(decisions[0].read_text(encoding="utf-8"))
    assert decision["reason"] == "service_unrecoverable"
    assert decision["failure_key"] == "service_down:project:loop-dashboard:restart-failed"


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
