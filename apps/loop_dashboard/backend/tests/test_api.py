import json
from pathlib import Path

from fastapi.testclient import TestClient

from loop_dashboard import main
from loop_dashboard.main import create_app


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def seed_minimal_run(repo_root: Path) -> None:
    write_json(
        repo_root / ".codex" / "loop-runs" / "demo-run" / "run.json",
        {
            "run_id": "demo-run",
            "policy": "demand_development",
            "phase": "passed_waiting_human_merge",
            "task_id": "loop-dashboard-dev-01",
            "domain": "",
            "branch": "feat/loop-dashboard",
            "worktree": str(repo_root),
            "requirement": "展示 run 列表和详情",
            "constraints": ["只读"],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 1, "evaluator": 1, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "pass",
            "next_action": "await_human_merge_confirmation",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def seed_supervisor_artifacts(repo_root: Path) -> None:
    supervisor_dir = repo_root / ".codex" / "supervisor"
    write_json(
        supervisor_dir / "supervisor-state.json",
        {
            "schema_version": 1,
            "project_root": str(repo_root),
            "status": "healthy",
            "started_at": "2026-07-09T00:00:00Z",
            "last_heartbeat_at": "2026-07-09T00:01:00Z",
            "last_tick_at": "2026-07-09T00:01:00Z",
            "generated_at": "2026-07-09T00:01:00Z",
            "mode": "watch",
            "service_summary": {"total": 1, "healthy": 1, "degraded": 0},
            "service_health": {
                "crawler-backend": {
                    "service": "crawler-backend",
                    "status": "healthy",
                    "last_error": "",
                }
            },
            "run_summary": {"active": 1, "blocked": 0, "continuation_candidates": 1, "needs_user_decision": 1},
            "failure_summary": {"open_failure_keys": 1, "max_consecutive_failures": 3},
            "last_decision": {"decision_id": "supervisor-000001", "run_id": "demo-run"},
            "watch_interval_seconds": 60,
        },
    )
    write_json(
        supervisor_dir / "service-health.json",
        {
            "schema_version": 1,
            "checked_at": "2026-07-09T00:01:00Z",
            "services": [
                {
                    "service": "crawler-backend",
                    "kind": "http_and_tmux",
                    "status": "healthy",
                    "reachable": True,
                    "tmux_session_exists": True,
                    "last_error": "token=service-secret",
                }
            ],
        },
    )
    append_jsonl(
        supervisor_dir / "run-decisions.jsonl",
        {
            "schema_version": 1,
            "decision_id": "supervisor-000001",
            "run_id": "demo-run",
            "classification": "continuation_candidate",
            "action": "create_continuation",
            "reason": "finished_parent_task",
            "created_at": "2026-07-09T00:01:01Z",
            "evidence_paths": [".codex/loop-runs/demo-run/run.json"],
        },
    )
    append_jsonl(
        supervisor_dir / "continuation-plans.jsonl",
        {
            "schema_version": 1,
            "plan_id": "continuation-demo-run-001",
            "idempotency_key": "autonomous_knowledge:ai_infra:demo-run:parent-1:abc123",
            "previous_run_id": "demo-run",
            "next_run_id": "demo-run-continuation-001",
            "status": "planned",
            "created_at": "2026-07-09T00:01:02Z",
        },
    )
    append_jsonl(
        supervisor_dir / "recovery-attempts.jsonl",
        {
            "schema_version": 1,
            "attempt_id": "recovery-000001",
            "failure_key": "service_down:project:crawler-backend:http",
            "run_id": "",
            "action": "restart_service",
            "status": "fail",
            "summary": "token=recovery-secret",
            "consecutive_failure_count": 1,
            "recorded_at": "2026-07-09T00:01:03Z",
        },
    )
    write_json(
        supervisor_dir / "needs-user-decisions" / "service_down-project-crawler-backend-http.json",
        {
            "schema_version": 1,
            "decision_id": "service_down-project-crawler-backend-http",
            "opened_at": "2026-07-09T00:01:04Z",
            "status": "open",
            "reason": "retry_ceiling_exceeded",
            "failure_key": "service_down:project:crawler-backend:http",
            "summary": "api_key=user-decision-secret",
            "required_user_decision": "Inspect repeated recovery failure.",
            "affected_runs": [],
            "attempts": [],
        },
    )
    seed_minimal_run(repo_root)
    write_json(
        repo_root / ".codex" / "loop-runs" / "demo-run" / "audit-reports" / "audit-002.json",
        {
            "schema_version": 1,
            "run_id": "demo-run",
            "audit_id": "audit-002",
            "created_at": "2026-07-09T00:01:05Z",
            "verdict": "stop",
            "direction_control": {"action": "stop", "reason": "secret=audit-secret"},
            "finding_lifecycle": {"open_findings": [{"finding_id": "audit-002-stop", "severity": "must_fix"}]},
        },
    )
    write_json(
        repo_root / ".codex" / "loop-runs" / "loop-supervisor" / "run.json",
        {
            "run_id": "loop-supervisor",
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "loop-supervisor",
            "requirement": "Supervisor global artifacts must not be listed as a task run.",
            "attempts": {},
            "last_result": "none",
            "next_action": "observe",
        },
    )


def test_api_project_runs_detail_events_and_logs(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))

    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/projects/current").json()["project_root"] == str(tmp_path.resolve())
    runs = client.get("/api/runs").json()
    assert runs[0]["run_id"] == "demo-run"
    assert runs[0]["task_summary"] == "展示 run 列表和详情"
    assert client.get("/api/runs/demo-run").json()["phase"] == "passed_waiting_human_merge"
    assert client.get("/api/runs/demo-run/events").json()["run_id"] == "demo-run"
    assert client.get("/api/runs/demo-run/logs").json()["run_id"] == "demo-run"


def test_supervisor_api_returns_honest_missing_state(tmp_path: Path) -> None:
    client = TestClient(create_app(project_root=tmp_path))

    payload = client.get("/api/supervisor").json()

    assert payload["status"] == "unavailable"
    assert payload["state"]["status_label"] == "暂无数据"


def test_supervisor_api_reads_services_decisions_recovery_and_user_decisions(tmp_path: Path) -> None:
    seed_supervisor_artifacts(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))

    assert client.get("/api/supervisor").json()["status"] == "healthy"
    assert client.get("/api/supervisor/services").json()["services"][0]["service"] == "crawler-backend"
    assert client.get("/api/supervisor/decisions").json()["continuation_plans"][0]["idempotency_key"]
    assert client.get("/api/supervisor/recovery").json()["attempts"][0]["consecutive_failure_count"] == 1
    assert client.get("/api/supervisor/decision-required").json()["open_count"] == 1
    assert client.get("/api/supervisor/auditor").json()["audits"][0]["verdict"] == "stop"


def test_supervisor_api_redacts_artifacts_and_reports_malformed_jsonl(tmp_path: Path) -> None:
    seed_supervisor_artifacts(tmp_path)
    recovery_path = tmp_path / ".codex" / "supervisor" / "recovery-attempts.jsonl"
    with recovery_path.open("a", encoding="utf-8") as handle:
        handle.write('{"summary": "Authorization: Bearer malformed-secret"\n')
    client = TestClient(create_app(project_root=tmp_path))

    response = client.get("/api/supervisor/recovery")

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["status"] == "invalid_artifact"
    assert "token=[REDACTED]" in serialized
    assert "recovery-secret" not in serialized
    assert "malformed-secret" not in serialized


def test_run_list_excludes_supervisor_global_artifacts(tmp_path: Path) -> None:
    seed_supervisor_artifacts(tmp_path)
    runs = TestClient(create_app(project_root=tmp_path)).get("/api/runs").json()

    assert all(run["run_id"] != "loop-supervisor" for run in runs)


def test_api_events_skip_dangling_symlink_artifacts(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "dangling.log").symlink_to(run_dir / "missing-target.log")
    client = TestClient(create_app(project_root=tmp_path))

    response = client.get("/api/runs/demo-run/events")

    assert response.status_code == 200
    sources = [event["source"] for event in response.json()["events"]]
    assert any(source.endswith("run.json") for source in sources)
    assert all("dangling.log" not in source for source in sources)


def test_api_events_skip_dangling_session_symlink(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    sessions_dir = tmp_path / ".codex" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "bad.jsonl").symlink_to(sessions_dir / "missing.jsonl")
    (sessions_dir / "good.jsonl").write_text(
        json.dumps(
            {
                "run_id": "demo-run",
                "type": "agent_message",
                "agent": "planner",
                "message": "Planner API session event",
                "timestamp": "2026-07-03T00:00:00Z",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client = TestClient(create_app(project_root=tmp_path))

    response = client.get("/api/runs/demo-run/events")

    assert response.status_code == 200
    assert any("Planner API session event" in event["message"] for event in response.json()["events"])


def test_api_serves_worktree_history_run(tmp_path: Path) -> None:
    worktree_root = tmp_path / ".worktrees" / "loop-dashboard"
    seed_minimal_run(worktree_root)
    run_dir = worktree_root / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "planner-attempt-1.stdout.log").write_text("Planner history log\n", encoding="utf-8")
    client = TestClient(create_app(project_root=tmp_path))

    runs = client.get("/api/runs").json()
    detail = client.get("/api/runs/demo-run").json()
    events = client.get("/api/runs/demo-run/events").json()
    logs = client.get("/api/runs/demo-run/logs").json()

    assert runs[0]["run_id"] == "demo-run"
    assert runs[0]["source_kind"] == "worktree"
    assert detail["source_path"] == ".worktrees/loop-dashboard/.codex/loop-runs/demo-run"
    assert detail["phase"] == "passed_waiting_human_merge"
    assert events["events"]
    assert logs["logs"][0]["content"] == "Planner history log\n"


def test_api_returns_404_for_missing_run_and_traversal_run_id(tmp_path: Path) -> None:
    client = TestClient(create_app(project_root=tmp_path))

    missing = client.get("/api/runs/missing")
    traversal = client.get("/api/runs/%2E%2E%2Foutside")

    assert missing.status_code == 404
    assert missing.json()["detail"] == "run not found: missing"
    assert traversal.status_code == 404


def test_api_returns_invalid_run_detail_for_listed_malformed_and_empty_runs(tmp_path: Path) -> None:
    broken = tmp_path / ".codex" / "loop-runs" / "broken-run"
    broken.mkdir(parents=True)
    (broken / "run.json").write_text("{bad json", encoding="utf-8")
    (tmp_path / ".codex" / "loop-runs" / "empty-run").mkdir(parents=True)
    client = TestClient(create_app(project_root=tmp_path))

    runs = client.get("/api/runs").json()
    broken_detail = client.get("/api/runs/broken-run")
    empty_detail = client.get("/api/runs/empty-run")

    assert any(run["run_id"] == "broken-run" and run["phase"] == "invalid_artifact" for run in runs)
    assert any(run["run_id"] == "empty-run" and run["phase"] == "invalid_artifact" for run in runs)
    assert broken_detail.status_code == 200
    assert broken_detail.json()["phase"] == "invalid_artifact"
    assert empty_detail.status_code == 200
    assert empty_detail.json()["blocked_diagnostics"][0]["kind"] == "invalid_artifact"


def test_api_handles_non_string_run_kind(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".codex" / "loop-runs" / "weird-run" / "run.json",
        {
            "run_id": "weird-run",
            "run_kind": [],
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "weird-run-task",
            "domain": "",
            "branch": "main",
            "worktree": str(tmp_path),
            "requirement": "API should tolerate malformed run_kind",
            "constraints": [],
            "stop_conditions": ["passed"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 0, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_generator",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )
    client = TestClient(create_app(project_root=tmp_path))

    runs = client.get("/api/runs")
    detail = client.get("/api/runs/weird-run")

    assert runs.status_code == 200
    assert next(run for run in runs.json() if run["run_id"] == "weird-run")["run_kind"] == "single"
    assert detail.status_code == 200
    assert detail.json()["run_kind"] == "single"


def test_api_and_static_page_expose_auditor_and_skill_dashboard(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    write_json(
        run_dir / "audit-reports" / "audit-001.json",
        {
            "schema_version": 1,
            "run_id": "demo-run",
            "audit_id": "audit-001",
            "verdict": "must_fix",
            "deterministic_signals": {
                "summary": {
                    "unclassified_dirty_paths": 1,
                    "same_evaluator_finding_count": 2,
                }
            },
            "direction_control": {
                "action": "switch_task",
                "reason": "连续空转",
                "recommended_next_focus": "优先整改 audit finding",
            },
            "finding_lifecycle": {
                "open_findings": [
                    {
                        "finding_id": "audit-001-stagnation-001",
                        "severity": "must_fix",
                        "title": "loop 空转",
                        "summary": "coverage 无增长。",
                    }
                ]
            },
        },
    )
    skill_dir = tmp_path / "loop-helper"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: loop-helper\ndescription: Use when testing loop dashboard skill inventory.\n---\n",
        encoding="utf-8",
    )
    client = TestClient(create_app(project_root=tmp_path))

    detail = client.get("/api/runs/demo-run")
    index = client.get("/")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["audit_summary"]["verdict"] == "must_fix"
    assert payload["audit_summary"]["open_must_fix"] == 1
    assert payload["audit_summary"]["direction_action"] == "switch_task"
    assert payload["skill_inventory"]["total_project_skills"] == 1
    assert payload["skill_inventory"]["items"][0]["name"] == "loop-helper"
    assert index.status_code == 200
    assert "审计与 Skill" in index.text


def test_static_serving_prefers_vite_dist_index_and_assets(tmp_path: Path, monkeypatch) -> None:
    frontend_dir = tmp_path / "frontend"
    dist_dir = frontend_dir / "dist"
    (dist_dir / "assets").mkdir(parents=True)
    (dist_dir / "index.html").write_text('<script src="/assets/app-built.js"></script>', encoding="utf-8")
    (dist_dir / "assets" / "app-built.js").write_text("console.log('built')", encoding="utf-8")
    (frontend_dir / "index.html").write_text('<script src="/src/main.tsx"></script>', encoding="utf-8")
    monkeypatch.setattr(main, "_frontend_root", lambda: frontend_dir)

    client = TestClient(create_app(project_root=tmp_path))

    index = client.get("/")
    asset = client.get("/assets/app-built.js")

    assert index.status_code == 200
    assert "/assets/app-built.js" in index.text
    assert "/src/main.tsx" not in index.text
    assert asset.status_code == 200
    assert "built" in asset.text


def seed_parent_child_api_run(repo_root: Path) -> None:
    parent_dir = repo_root / ".codex" / "loop-runs" / "api-parent"
    write_json(
        parent_dir / "run.json",
        {
            "run_id": "api-parent",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "API parent",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_parent_planner",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["api-parent-child-001"],
            "current_child_run_id": "api-parent-child-001",
            "backlog": [],
            "aggregate_acceptance": {"total": 1, "passed": 0, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            "reader_summary": {"purpose": "API summary", "current_progress": "running", "next_step": "child", "decision_needed": "No"},
            "accepted_changed_paths": [],
        },
    )
    child_dir = repo_root / ".codex" / "loop-runs" / "api-parent-child-001"
    child_payload = json.loads((parent_dir / "run.json").read_text(encoding="utf-8"))
    child_payload.update(
        {
            "run_id": "api-parent-child-001",
            "run_kind": "child",
            "parent_run_id": "api-parent",
            "child_index": 1,
            "phase": "generating",
            "task_id": "api-parent-child-001-task",
            "requirement": "API child",
            "stop_conditions": ["passed"],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "reader_summary": {
                "purpose": "API child",
                "planner_action": "planned",
                "generator_action": "pending",
                "evaluator_action": "pending",
                "acceptance_result": "pending",
            },
        }
    )
    write_json(child_dir / "run.json", child_payload)


def test_api_returns_parent_child_fields(tmp_path: Path) -> None:
    seed_parent_child_api_run(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))

    runs = client.get("/api/runs").json()
    detail = client.get("/api/runs/api-parent").json()

    parent = next(run for run in runs if run["run_id"] == "api-parent")
    assert parent["run_kind"] == "parent"
    assert parent["children_summary"]["total"] == 1
    assert detail["reader_summary"]["purpose"] == "API summary"
    assert detail["children"][0]["run_id"] == "api-parent-child-001"
