import json
import os
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest

from loop_dashboard import main
from loop_dashboard.main import create_app
from loop_dashboard.pagination import SnapshotCapacityError
from loop_dashboard.store import LoopDashboardStore


TEST_CURSOR_SECRET = b"task-7-dashboard-test-secret-32-bytes"


def create_test_app(project_root: Path, **kwargs):
    return create_app(
        project_root=project_root,
        cursor_secret=TEST_CURSOR_SECRET,
        **kwargs,
    )


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


def test_app_requires_explicit_random_cursor_secret(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("LOOP_DASHBOARD_CURSOR_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="LOOP_DASHBOARD_CURSOR_SECRET"):
        create_app(project_root=tmp_path)
    with pytest.raises(ValueError, match="at least 32 bytes"):
        create_app(project_root=tmp_path, cursor_secret=b"short")

    app = create_app(
        project_root=tmp_path,
        cursor_secret=b"explicit-test-cursor-secret-32-bytes",
    )
    assert app.state.store is not None


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
    client = TestClient(create_test_app(project_root=tmp_path))

    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/projects/current").json()["project_root"] == str(tmp_path.resolve())
    runs = client.get("/api/runs").json()["items"]
    assert runs[0]["run_id"] == "demo-run"
    assert runs[0]["task_summary"] == "展示 run 列表和详情"
    assert client.get("/api/runs/demo-run").json()["phase"] == "passed_waiting_human_merge"
    assert client.get("/api/runs/demo-run/events").json()["page_size"] == 20
    assert client.get("/api/runs/demo-run/logs").json()["page_size"] == 20


def test_supervisor_api_returns_honest_missing_state(tmp_path: Path) -> None:
    client = TestClient(create_test_app(project_root=tmp_path))

    payload = client.get("/api/supervisor").json()

    assert payload["status"] == "unavailable"
    assert payload["counts"] == {}
    assert payload["diagnostics"]


def test_supervisor_api_does_not_fall_back_to_non_utf8_legacy_state(tmp_path: Path) -> None:
    supervisor_dir = tmp_path / ".codex" / "supervisor"
    supervisor_dir.mkdir(parents=True)
    (supervisor_dir / "supervisor-state.json").write_bytes(
        b'{"status": "healthy", "last_error": "token=state-secret", "broken": "\xff"}'
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    response = client.get("/api/supervisor")

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["status"] == "unavailable"
    assert payload["diagnostics"][0]["status"] == "unavailable"
    assert "state-secret" not in serialized


def test_supervisor_api_ignores_legacy_json_and_jsonl_artifacts(tmp_path: Path) -> None:
    seed_supervisor_artifacts(tmp_path)
    client = TestClient(create_test_app(project_root=tmp_path))

    assert client.get("/api/supervisor").json()["status"] == "unavailable"
    for route in (
        "/api/supervisor/services",
        "/api/supervisor/decisions",
        "/api/supervisor/recovery",
        "/api/supervisor/decision-required",
    ):
        payload = client.get(route).json()
        assert set(payload) == {"status", "error"}
        assert payload["status"] == "unavailable"
    assert client.get("/api/supervisor/auditor").status_code == 404


def test_supervisor_auditor_route_is_removed(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    audit_dir = tmp_path / ".codex" / "loop-runs" / "demo-run" / "audit-reports"
    write_json(
        audit_dir / "audit-001.json",
        {
            "schema_version": 1,
            "run_id": "demo-run",
            "audit_id": "audit-001",
            "created_at": "2026-07-09T00:01:05Z",
            "verdict": "pass",
        },
    )
    (audit_dir / "audit-002.json").write_text(
        '{"run_id": "demo-run", "verdict": "stop", "reason": "token=newest-audit-secret"',
        encoding="utf-8",
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    response = client.get("/api/supervisor/auditor")

    assert response.status_code == 404


def test_supervisor_api_does_not_parse_malformed_legacy_jsonl(tmp_path: Path) -> None:
    seed_supervisor_artifacts(tmp_path)
    recovery_path = tmp_path / ".codex" / "supervisor" / "recovery-attempts.jsonl"
    with recovery_path.open("a", encoding="utf-8") as handle:
        handle.write('{"summary": "Authorization: Bearer malformed-secret"\n')
    client = TestClient(create_test_app(project_root=tmp_path))

    response = client.get("/api/supervisor/recovery")

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["status"] == "unavailable"
    assert set(payload) == {"status", "error"}
    assert "recovery-secret" not in serialized
    assert "malformed-secret" not in serialized


def test_run_list_excludes_supervisor_global_artifacts(tmp_path: Path) -> None:
    seed_supervisor_artifacts(tmp_path)
    runs = TestClient(create_test_app(project_root=tmp_path)).get("/api/runs").json()["items"]

    assert all(run["run_id"] != "loop-supervisor" for run in runs)


def test_api_events_skip_dangling_symlink_artifacts(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "dangling.log").symlink_to(run_dir / "missing-target.log")
    client = TestClient(create_test_app(project_root=tmp_path))

    response = client.get("/api/runs/demo-run/events")

    assert response.status_code == 200
    sources = [event["source"] for event in response.json()["items"]]
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
    client = TestClient(create_test_app(project_root=tmp_path))

    response = client.get("/api/runs/demo-run/events")

    assert response.status_code == 200
    assert any("Planner API session event" in event["message"] for event in response.json()["items"])


def test_api_serves_worktree_history_run(tmp_path: Path) -> None:
    worktree_root = tmp_path / ".worktrees" / "loop-dashboard"
    seed_minimal_run(worktree_root)
    run_dir = worktree_root / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "planner-attempt-1.stdout.log").write_text("Planner history log\n", encoding="utf-8")
    client = TestClient(create_test_app(project_root=tmp_path))

    runs = client.get("/api/runs").json()["items"]
    detail = client.get("/api/runs/demo-run").json()
    events = client.get("/api/runs/demo-run/events").json()
    logs = client.get("/api/runs/demo-run/logs").json()

    assert runs[0]["run_id"] == "demo-run"
    assert runs[0]["source_kind"] == "worktree"
    assert detail["source_path"] == ".worktrees/loop-dashboard/.codex/loop-runs/demo-run"
    assert detail["phase"] == "passed_waiting_human_merge"
    assert events["items"]
    assert logs["items"][0]["summary"] == "Planner history log"


def test_api_returns_404_for_missing_run_and_traversal_run_id(tmp_path: Path) -> None:
    client = TestClient(create_test_app(project_root=tmp_path))

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
    client = TestClient(create_test_app(project_root=tmp_path))

    runs = client.get("/api/runs").json()["items"]
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
    client = TestClient(create_test_app(project_root=tmp_path))

    runs = client.get("/api/runs")
    detail = client.get("/api/runs/weird-run")

    assert runs.status_code == 200
    assert next(run for run in runs.json()["items"] if run["run_id"] == "weird-run")["run_kind"] == "single"
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
    client = TestClient(create_test_app(project_root=tmp_path))

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

    client = TestClient(create_test_app(project_root=tmp_path))

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
    client = TestClient(create_test_app(project_root=tmp_path))

    runs = client.get("/api/runs").json()["items"]
    detail = client.get("/api/runs/api-parent").json()

    parent = next(run for run in runs if run["run_id"] == "api-parent")
    assert parent["run_kind"] == "parent"
    assert parent["children_summary"]["total"] == 1
    assert detail["reader_summary"]["purpose"] == "API summary"
    assert detail["children"][0]["run_id"] == "api-parent-child-001"


def test_run_list_and_detail_collections_use_page_contract(tmp_path: Path) -> None:
    for index in range(25):
        run_id = f"paged-run-{index:03d}"
        write_json(
            tmp_path / ".codex" / "loop-runs" / run_id / "run.json",
            {
                "run_id": run_id,
                "policy": "demand_development",
                "phase": "generating",
                "task_id": run_id,
                "requirement": f"paged run {index}",
                "attempts": {},
                "last_result": "none",
                "next_action": "run_generator",
            },
        )
    run_dir = tmp_path / ".codex" / "loop-runs" / "paged-run-024"
    append_jsonl(
        run_dir / "events.jsonl",
        {
            "event_type": "transition",
            "summary": "entered generating",
            "timestamp": "2026-07-15T00:00:00Z",
        },
    )
    (run_dir / "generator-attempt-1.stdout.log").write_text(
        "generator output\n", encoding="utf-8"
    )
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "findings": [
                {
                    "id": "finding-1",
                    "severity": "major",
                    "recommended_action": "fix route",
                }
            ],
            "scenario_results": [
                {
                    "scenario_id": "scenario-1",
                    "status": "fail",
                    "summary": "route failed",
                }
            ],
        },
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    first = client.get("/api/runs?page_size=20").json()
    assert set(first) == {
        "items",
        "next_cursor",
        "previous_cursor",
        "page_size",
        "total",
        "has_more",
    }
    assert first["total"] == 25
    first_ids = {item["run_id"] for item in first["items"]}

    write_json(
        tmp_path / ".codex" / "loop-runs" / "paged-run-new" / "run.json",
        {
            "run_id": "paged-run-new",
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "paged-run-new",
            "requirement": "newer run",
            "attempts": {},
            "last_result": "none",
            "next_action": "run_generator",
        },
    )
    second = client.get(
        "/api/runs",
        params={"page_size": "20", "cursor": first["next_cursor"]},
    ).json()
    assert first_ids.isdisjoint(item["run_id"] for item in second["items"])
    assert second["total"] == 25

    for collection in (
        "children",
        "acceptance",
        "events",
        "logs",
        "diagnostics",
        "artifacts",
    ):
        response = client.get(f"/api/runs/paged-run-024/{collection}?page_size=20")
        assert response.status_code == 200, collection
        payload = response.json()
        assert set(payload) == {
            "items",
            "next_cursor",
            "previous_cursor",
            "page_size",
            "total",
            "has_more",
        }


def test_acceptance_duplicate_source_ids_paginate_forward_and_reverse(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "scenario_results": [
                {
                    "scenario_id": "duplicate-scenario",
                    "status": "fail",
                    "summary": "same scenario",
                    "occurrence": index,
                }
                for index in range(45)
            ],
        },
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    pages = []
    cursor = None
    while not pages or cursor:
        response = client.get(
            "/api/runs/demo-run/acceptance",
            params={"cursor": cursor} if cursor else None,
        )
        assert response.status_code == 200
        pages.append(response.json())
        cursor = pages[-1]["next_cursor"]

    assert [len(page["items"]) for page in pages] == [20, 20, 5]
    assert {item["acceptance_id"] for page in pages for item in page["items"]} == {
        "duplicate-scenario"
    }
    reverse = client.get(
        "/api/runs/demo-run/acceptance",
        params={"cursor": pages[-1]["previous_cursor"]},
    ).json()
    assert reverse["items"] == pages[-2]["items"]


def test_run_cursor_is_validated_before_lookup_and_survives_run_deletion(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "scenario_results": [
                {
                    "scenario_id": f"scenario-{index:03d}",
                    "status": "fail",
                    "summary": f"scenario {index}",
                }
                for index in range(25)
            ],
        },
    )
    client = TestClient(create_test_app(project_root=tmp_path))
    first = client.get("/api/runs/demo-run/acceptance").json()
    shutil.rmtree(run_dir)

    malformed = client.get("/api/runs/missing/acceptance?cursor=bad")
    second = client.get(
        "/api/runs/demo-run/acceptance",
        params={"cursor": first["next_cursor"]},
    )

    assert malformed.status_code == 400
    assert second.status_code == 200
    assert second.json()["total"] == 25
    assert len(second.json()["items"]) == 5


def test_log_list_omits_bodies_and_detail_is_opaque_redacted_and_bounded(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    log_path = run_dir / "generator-attempt-1.stdout.log"
    log_path.write_text("token=top-secret\n" + "界" * 30_000, encoding="utf-8")
    client = TestClient(create_test_app(project_root=tmp_path))

    logs = client.get("/api/runs/demo-run/logs?page_size=20").json()
    item = next(item for item in logs["items"] if item["stream"] == "stdout")
    assert "content" not in item
    assert "path" not in item
    assert "generator-attempt-1.stdout.log" not in item["log_id"]
    assert "/" not in item["log_id"]

    detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")
    assert detail.status_code == 200
    payload = detail.json()
    assert len(payload["content"].encode("utf-8")) <= 65_536
    assert payload["truncated"] is True
    assert payload["total_bytes"] > 65_536
    assert "top-secret" not in payload["content"]
    assert "[REDACTED]" in payload["content"]

    assert client.get(f"/api/runs/other-run/logs/{item['log_id']}").status_code == 404
    assert client.get("/api/runs/demo-run/logs/not-a-real-id").status_code == 404


def test_log_detail_revalidates_symlinks_regular_files_and_run_ownership(
    tmp_path: Path,
) -> None:
    for run_id in ("run-a", "run-b"):
        write_json(
            tmp_path / ".codex" / "loop-runs" / run_id / "run.json",
            {
                "run_id": run_id,
                "policy": "demand_development",
                "phase": "generating",
                "task_id": run_id,
                "requirement": run_id,
                "attempts": {},
                "last_result": "none",
                "next_action": "run_generator",
            },
        )
    run_a = tmp_path / ".codex" / "loop-runs" / "run-a"
    log_path = run_a / "generator-attempt-1.stderr.log"
    log_path.write_text("failure\n", encoding="utf-8")
    client = TestClient(create_test_app(project_root=tmp_path))
    item = client.get("/api/runs/run-a/logs").json()["items"][0]

    assert client.get(f"/api/runs/run-b/logs/{item['log_id']}").status_code == 404
    outside = tmp_path / "outside.log"
    outside.write_text("secret outside\n", encoding="utf-8")
    log_path.unlink()
    log_path.symlink_to(outside)
    assert client.get(f"/api/runs/run-a/logs/{item['log_id']}").status_code == 404

    log_path.unlink()
    log_path.mkdir()
    assert client.get(f"/api/runs/run-a/logs/{item['log_id']}").status_code == 404


def test_log_discovery_rejects_every_lexical_symlink_component(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    real_logs = run_dir / "real-logs"
    real_logs.mkdir()
    (real_logs / "nested.stdout.log").write_text("must stay hidden\n", encoding="utf-8")
    (run_dir / "linked-logs").symlink_to(real_logs, target_is_directory=True)
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "stdout_path": "linked-logs/nested.stdout.log",
        },
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    logs = client.get("/api/runs/demo-run/logs").json()

    assert logs["items"] == []


def test_log_list_rejects_task_root_replaced_by_cross_task_alias(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for run_id in ("task-a", "task-b"):
        write_json(
            tmp_path / ".codex" / "loop-runs" / run_id / "run.json",
            {
                "run_id": run_id,
                "policy": "demand_development",
                "phase": "generating",
                "task_id": run_id,
                "requirement": run_id,
                "attempts": {},
                "last_result": "none",
                "next_action": "run_generator",
            },
        )
    task_a = tmp_path / ".codex" / "loop-runs" / "task-a"
    task_b = tmp_path / ".codex" / "loop-runs" / "task-b"
    (task_a / "worker-attempt-1.stdout.log").write_text(
        "task-a output\n", encoding="utf-8"
    )
    (task_b / "worker-attempt-1.stdout.log").write_text(
        "cross-task-secret\n", encoding="utf-8"
    )
    app = create_test_app(project_root=tmp_path)
    original_collect = app.state.store._collect_log_handles
    swapped = False

    def racing_collect(run_id, run_dir, supervisor_store):
        nonlocal swapped
        if run_id == "task-a" and not swapped:
            swapped = True
            task_a.rename(task_a.with_name("task-a-original"))
            task_a.symlink_to(task_b, target_is_directory=True)
        return original_collect(run_id, run_dir, supervisor_store)

    monkeypatch.setattr(app.state.store, "_collect_log_handles", racing_collect)
    with TestClient(app) as client:
        response = client.get("/api/runs/task-a/logs")

    assert swapped is True
    assert "cross-task-secret" not in response.text
    if response.status_code == 200:
        assert response.json()["items"] == []
    else:
        assert response.status_code == 404


def test_log_list_traverses_lexical_task_root_without_resolving_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "worker-attempt-1.stdout.log").write_text(
        "lexical output\n", encoding="utf-8"
    )
    app = create_test_app(project_root=tmp_path)
    original_resolve = Path.resolve

    def reject_task_root_resolve(path: Path, *args, **kwargs):
        if path == run_dir or run_dir in path.parents:
            raise AssertionError("lexical task root was resolved")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", reject_task_root_resolve)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/runs/demo-run/logs")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_log_detail_traverses_lexical_task_root_without_resolving_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "worker-attempt-1.stdout.log").write_text(
        "lexical detail\n", encoding="utf-8"
    )
    app = create_test_app(project_root=tmp_path)
    with TestClient(app) as client:
        item = client.get("/api/runs/demo-run/logs").json()["items"][0]
        original_resolve = Path.resolve

        def reject_task_root_resolve(path: Path, *args, **kwargs):
            if path == run_dir or run_dir in path.parents:
                raise AssertionError("lexical task root was resolved")
            return original_resolve(path, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", reject_task_root_resolve)
        client.raise_server_exceptions = False
        response = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert response.status_code == 200
    assert response.json()["content"] == "lexical detail\n"


def test_log_list_rejects_cross_task_evaluation_alias(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "task_id": "task-a",
            "final_bundle_id": "bundle-1",
        },
    )
    tasks_dir = tmp_path / ".codex" / "evaluations" / "tasks"
    write_json(
        tasks_dir / "task-b" / "bundle-1" / "result.json",
        {"stdout": "cross-task-evaluation-secret\n"},
    )
    (tasks_dir / "task-a").symlink_to(
        tasks_dir / "task-b", target_is_directory=True
    )
    app = create_test_app(project_root=tmp_path)

    with TestClient(app) as client:
        response = client.get("/api/runs/demo-run/logs")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert "cross-task-evaluation-secret" not in response.text


def test_log_detail_rejects_cross_task_evaluation_alias_after_issue(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "task_id": "task-a",
            "final_bundle_id": "bundle-1",
        },
    )
    tasks_dir = tmp_path / ".codex" / "evaluations" / "tasks"
    task_a = tasks_dir / "task-a"
    task_b = tasks_dir / "task-b"
    write_json(
        task_a / "bundle-1" / "result.json",
        {"stdout": "owned evaluation output\n"},
    )
    write_json(
        task_b / "bundle-1" / "result.json",
        {"stdout": "replacement evaluation secret\n"},
    )
    app = create_test_app(project_root=tmp_path)
    with TestClient(app) as client:
        item = client.get("/api/runs/demo-run/logs").json()["items"][0]
        task_a.rename(tasks_dir / "task-a-original")
        task_a.symlink_to(task_b, target_is_directory=True)

        detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert detail.status_code == 404
    assert "replacement evaluation secret" not in detail.text


def test_log_detail_reads_same_leaf_descriptor_during_swap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    log_path = run_dir / "generator-attempt-1.stdout.log"
    log_path.write_text("inside\n", encoding="utf-8")
    outside = tmp_path / "outside.log"
    outside.write_text("outside-secret\n", encoding="utf-8")
    client = TestClient(create_test_app(project_root=tmp_path))
    item = client.get("/api/runs/demo-run/logs").json()["items"][0]
    original_open = __import__("os").open
    swapped = False

    def racing_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == log_path.name and kwargs.get("dir_fd") is not None and not swapped:
            swapped = True
            log_path.unlink()
            log_path.symlink_to(outside)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr("loop_dashboard.store.os.open", racing_open)

    response = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert swapped is True
    assert response.status_code == 404
    assert "outside-secret" not in response.text


def test_log_detail_reads_through_open_ancestor_descriptor_during_swap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()
    log_path = logs_dir / "nested.stdout.log"
    log_path.write_text("inside ancestor\n", encoding="utf-8")
    outside_dir = tmp_path / "outside-logs"
    outside_dir.mkdir()
    (outside_dir / log_path.name).write_text("ancestor-secret\n", encoding="utf-8")
    write_json(
        run_dir / "evaluator-result.json",
        {"status": "fail", "stdout_path": "logs/nested.stdout.log"},
    )
    client = TestClient(create_test_app(project_root=tmp_path))
    item = client.get("/api/runs/demo-run/logs").json()["items"][0]
    original_open = __import__("os").open
    swapped = False

    def racing_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == logs_dir.name and kwargs.get("dir_fd") is not None and not swapped:
            swapped = True
            logs_dir.rename(run_dir / "logs-original")
            logs_dir.symlink_to(outside_dir, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr("loop_dashboard.store.os.open", racing_open)

    response = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert swapped is True
    assert response.status_code == 404
    assert "ancestor-secret" not in response.text


def test_log_detail_does_not_follow_ancestor_swapped_during_os_open(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()
    log_path = logs_dir / "nested.stdout.log"
    log_path.write_text("anchored content\n", encoding="utf-8")
    outside_dir = tmp_path / "outside-logs"
    outside_dir.mkdir()
    (outside_dir / log_path.name).write_text("replacement-secret\n", encoding="utf-8")
    write_json(
        run_dir / "evaluator-result.json",
        {"status": "fail", "stdout_path": "logs/nested.stdout.log"},
    )
    client = TestClient(create_test_app(project_root=tmp_path))
    item = client.get("/api/runs/demo-run/logs").json()["items"][0]
    original_open = __import__("os").open
    swapped = False
    leaf_opens = 0

    def racing_os_open(path, flags, *args, **kwargs):
        nonlocal leaf_opens, swapped
        if path == log_path.name and kwargs.get("dir_fd") is not None:
            leaf_opens += 1
            if leaf_opens == 2 and not swapped:
                swapped = True
                logs_dir.rename(run_dir / "logs-original")
                logs_dir.symlink_to(outside_dir, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr("loop_dashboard.store.os.open", racing_os_open)

    response = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert swapped is True
    assert response.status_code == 200
    assert response.json()["content"] == "anchored content\n"
    assert "replacement-secret" not in response.text


def test_log_detail_traverses_from_trusted_project_descriptor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    log_path = run_dir / "generator-attempt-1.stdout.log"
    log_path.write_text("trusted content\n", encoding="utf-8")
    outside_root = tmp_path / "outside-root"
    outside_log = outside_root / "loop-runs" / "demo-run" / log_path.name
    outside_log.parent.mkdir(parents=True)
    outside_log.write_text("project-ancestor-secret\n", encoding="utf-8")
    client = TestClient(create_test_app(project_root=tmp_path))
    item = client.get("/api/runs/demo-run/logs").json()["items"][0]
    codex_dir = tmp_path / ".codex"
    original_open = __import__("os").open
    swapped = False

    def racing_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == ".codex" and kwargs.get("dir_fd") is not None and not swapped:
            swapped = True
            codex_dir.rename(tmp_path / ".codex-original")
            codex_dir.symlink_to(outside_root, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr("loop_dashboard.store.os.open", racing_open)

    response = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert swapped is True
    assert response.status_code == 404
    assert "project-ancestor-secret" not in response.text


def test_inline_log_ids_include_json_position_and_revalidate_provenance(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    evaluator_path = run_dir / "evaluator-result.json"
    write_json(
        evaluator_path,
        {
            "status": "fail",
            "commands": [
                {"stdout": "identical body\n"},
                {"stdout": "identical body\n"},
            ],
        },
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    page = client.get("/api/runs/demo-run/logs").json()
    inline_items = [item for item in page["items"] if item["stream"] == "stdout"]
    assert len(inline_items) == 2
    assert len({item["log_id"] for item in inline_items}) == 2

    write_json(evaluator_path, {"status": "fail", "commands": []})
    for item in inline_items:
        assert (
            client.get(f"/api/runs/demo-run/logs/{item['log_id']}").status_code
            == 404
        )


def test_log_detail_fails_closed_when_final_bundle_reference_changes(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    evaluator_path = run_dir / "evaluator-result.json"
    write_json(
        evaluator_path,
        {
            "status": "fail",
            "task_id": "task-a",
            "final_bundle_id": "bundle-a",
        },
    )
    task_dir = tmp_path / ".codex" / "evaluations" / "tasks" / "task-a"
    for bundle_id in ("bundle-a", "bundle-b"):
        write_json(
            task_dir / bundle_id / "result.json",
            {"stdout": "identical evaluator output\n"},
        )
    app = create_test_app(project_root=tmp_path)

    with TestClient(app) as client:
        item = client.get("/api/runs/demo-run/logs").json()["items"][0]
        write_json(
            evaluator_path,
            {
                "status": "fail",
                "task_id": "task-a",
                "final_bundle_id": "bundle-b",
            },
        )

        detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert detail.status_code == 404


def test_log_detail_fails_closed_when_scenario_reference_is_removed(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    evaluator_path = run_dir / "evaluator-result.json"
    write_json(
        evaluator_path,
        {
            "status": "fail",
            "scenario_command_results_path": "scenario-results.json",
        },
    )
    write_json(
        run_dir / "scenario-results.json",
        {"commands": [{"stdout_path": "scenario.stdout.log"}]},
    )
    (run_dir / "scenario.stdout.log").write_text(
        "scenario output\n", encoding="utf-8"
    )
    app = create_test_app(project_root=tmp_path)

    with TestClient(app) as client:
        item = client.get("/api/runs/demo-run/logs").json()["items"][0]
        write_json(evaluator_path, {"status": "fail"})

        detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert detail.status_code == 404


def test_log_detail_fails_closed_when_nested_log_path_reference_changes(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    evaluator_path = run_dir / "evaluator-result.json"
    for name in ("first.stdout.log", "second.stdout.log"):
        (run_dir / name).write_text("identical file output\n", encoding="utf-8")
    write_json(
        evaluator_path,
        {
            "status": "fail",
            "commands": [{"stdout_path": "first.stdout.log"}],
        },
    )
    app = create_test_app(project_root=tmp_path)

    with TestClient(app) as client:
        item = client.get("/api/runs/demo-run/logs").json()["items"][0]
        write_json(
            evaluator_path,
            {
                "status": "fail",
                "commands": [{"stdout_path": "second.stdout.log"}],
            },
        )

        detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert detail.status_code == 404


def test_log_detail_redacts_compound_secret_keys(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "generator-attempt-1.stdout.log").write_text(
        "\n".join(
            (
                "openaiApiKey=openai-secret",
                "apiKey: api-key-secret",
                "apikey=compact-secret",
                '"openai-api-key": "quoted secret with spaces"',
                "github_token=github-secret",
                "Authorization: Bearer bearer-secret",
            )
        ),
        encoding="utf-8",
    )
    client = TestClient(create_test_app(project_root=tmp_path))
    item = client.get("/api/runs/demo-run/logs").json()["items"][0]

    detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}").json()

    assert detail["content"].count("[REDACTED]") == 6
    for secret in (
        "openai-secret",
        "api-key-secret",
        "compact-secret",
        "quoted secret with spaces",
        "secret with spaces",
        "github-secret",
        "bearer-secret",
    ):
        assert secret not in detail["content"]


def test_issued_log_handle_survives_event_and_artifact_discovery(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "generator-attempt-1.stdout.log").write_text(
        "stable handle\n", encoding="utf-8"
    )
    client = TestClient(create_test_app(project_root=tmp_path))
    item = client.get("/api/runs/demo-run/logs").json()["items"][0]

    assert client.get("/api/runs/demo-run/events").status_code == 200
    assert client.get("/api/runs/demo-run/artifacts").status_code == 200
    detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert detail.status_code == 200
    assert detail.json()["content"] == "stable handle\n"


def test_event_classification_uses_bounded_scan_beyond_first_line(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    (run_dir / "generator-attempt-1.stdout.log").write_text(
        "x" * 500
        + "\nused skill test-driven-development\n"
        + "called tool shell\n"
        + "planner agent completed\n",
        encoding="utf-8",
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    events = client.get("/api/runs/demo-run/events").json()["items"]
    kinds = {event["kind"] for event in events}

    assert {"skill", "tool", "agent"} <= kinds


def test_run_cursor_secret_and_snapshot_are_shared_across_app_instances(
    tmp_path: Path,
) -> None:
    for index in range(25):
        run_id = f"restart-run-{index:03d}"
        write_json(
            tmp_path / ".codex" / "loop-runs" / run_id / "run.json",
            {
                "run_id": run_id,
                "policy": "demand_development",
                "phase": "generating",
                "task_id": run_id,
                "requirement": run_id,
                "attempts": {},
                "last_result": "none",
                "next_action": "run_generator",
            },
        )
    first_client = TestClient(create_test_app(project_root=tmp_path))
    first = first_client.get("/api/runs").json()
    second_client = TestClient(create_test_app(project_root=tmp_path))

    second = second_client.get(
        "/api/runs", params={"cursor": first["next_cursor"]}
    )

    assert second.status_code == 200
    assert second.json()["previous_cursor"] is not None


def test_run_cursor_resolves_snapshot_before_live_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for index in range(25):
        run_id = f"frozen-run-{index:03d}"
        write_json(
            tmp_path / ".codex" / "loop-runs" / run_id / "run.json",
            {
                "run_id": run_id,
                "policy": "demand_development",
                "phase": "generating",
                "task_id": run_id,
                "requirement": run_id,
                "attempts": {},
                "last_result": "none",
                "next_action": "run_generator",
            },
        )
    app = create_test_app(project_root=tmp_path)
    with TestClient(app) as client:
        first = client.get("/api/runs").json()

        def fail_live_scan():
            raise AssertionError("live run scan must not run for a cursor")

        monkeypatch.setattr(app.state.store, "list_runs", fail_live_scan)
        malformed = client.get("/api/runs", params={"cursor": "bad"})
        continuation = client.get(
            "/api/runs", params={"cursor": first["next_cursor"]}
        )

    assert malformed.status_code == 400
    assert continuation.status_code == 200
    assert continuation.json()["total"] == 25
    assert len(continuation.json()["items"]) == 5


def test_frozen_log_cursor_does_not_rediscover_live_collection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    for index in range(25):
        (run_dir / f"worker-attempt-{index:03d}.stdout.log").write_text(
            f"output {index}\n", encoding="utf-8"
        )
    app = create_test_app(project_root=tmp_path)
    with TestClient(app) as client:
        first = client.get("/api/runs/demo-run/logs").json()
        for index in range(30):
            (run_dir / f"newer-attempt-{index:03d}.stderr.log").write_text(
                f"new output {index}\n", encoding="utf-8"
            )

        def fail_live_discovery(*_args, **_kwargs):
            raise AssertionError("live log discovery must not run for a cursor")

        monkeypatch.setattr(
            app.state.store,
            "_collect_log_handles",
            fail_live_discovery,
        )
        continuation = client.get(
            "/api/runs/demo-run/logs",
            params={"cursor": first["next_cursor"]},
        )

    assert continuation.status_code == 200
    assert continuation.json()["total"] == 25
    assert len(continuation.json()["items"]) == 5


def test_growing_log_detail_is_capped_to_opening_size(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    log_path = run_dir / "worker-attempt-1.stdout.log"
    original = b"opening content\n"
    appended = b"appended after open\n"
    log_path.write_bytes(original)
    app = create_test_app(project_root=tmp_path)
    with TestClient(app) as client:
        item = client.get("/api/runs/demo-run/logs").json()["items"][0]
        original_read = os.read
        appended_once = False

        def append_before_read(descriptor: int, size: int) -> bytes:
            nonlocal appended_once
            if (
                not appended_once
                and os.fstat(descriptor).st_ino == log_path.stat().st_ino
            ):
                appended_once = True
                with log_path.open("ab") as stream:
                    stream.write(appended)
            return original_read(descriptor, size)

        monkeypatch.setattr("loop_dashboard.store.os.read", append_before_read)
        detail = client.get(f"/api/runs/demo-run/logs/{item['log_id']}")

    assert appended_once is True
    assert detail.status_code == 200
    assert detail.json()["content"] == original.decode()
    assert detail.json()["total_bytes"] == len(original)
    assert detail.json()["truncated"] is False


def test_event_ids_are_content_stable_not_list_indexes(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    append_jsonl(
        run_dir / "events.jsonl",
        {
            "event_type": "transition",
            "summary": "stable event",
            "timestamp": "2026-07-15T00:00:00Z",
        },
    )
    client = TestClient(create_test_app(project_root=tmp_path))

    event = next(
        item
        for item in client.get("/api/runs/demo-run/events").json()["items"]
        if item["message"] == "stable event"
    )

    assert ":" not in event["event_id"]
    assert len(event["event_id"]) == 24


def test_event_api_declares_retention_and_total_matches_exposed_snapshot(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    for index in range(1100):
        append_jsonl(
            run_dir / "events.jsonl",
            {
                "event_type": "transition",
                "summary": f"event {index}",
                "timestamp": f"2026-07-15T00:00:{index:04d}Z",
            },
        )
    client = TestClient(create_test_app(project_root=tmp_path))

    response = client.get("/api/runs/demo-run/events")
    first = response.json()
    items = list(first["items"])
    cursor = first["next_cursor"]
    while cursor:
        page = client.get(
            "/api/runs/demo-run/events",
            params={"cursor": cursor},
        ).json()
        items.extend(page["items"])
        cursor = page["next_cursor"]

    assert response.headers["X-Loop-Event-Retention"] == (
        "structured=last-1000-lines-within-1048576-bytes;"
        "sessions=last-200-matching-supported-events-scanning-last-10000-"
        "lines-from-newest-128-files-within-2097152-bytes-each-and-"
        "at-most-4096-inspected-entries;"
        "logs=newest-1000"
    )
    assert len(items) == first["total"]
    messages = {item["message"] for item in items}
    assert "event 1099" in messages
    assert "event 0" not in messages


def test_session_event_candidates_are_sorted_by_freshness_before_retention(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    sessions_dir = tmp_path / ".codex" / "sessions"
    for index in range(129):
        path = sessions_dir / f"session-{index:03d}.jsonl"
        append_jsonl(
            path,
            {
                "run_id": "other-run",
                "type": "agent_message",
                "message": f"other {index}",
            },
        )
        os.utime(path, (index + 1, index + 1))
    discovery_order = list(sessions_dir.rglob("*.jsonl"))
    newest = discovery_order[128]
    newest.write_text(
        json.dumps(
            {
                "run_id": "demo-run",
                "type": "agent_message",
                "message": "newest retained session",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    os.utime(newest, (1000, 1000))

    events = LoopDashboardStore(tmp_path).get_events("demo-run")

    assert events is not None
    assert any(item["message"] == "newest retained session" for item in events)


def test_session_event_retention_counts_only_matching_supported_events(
    tmp_path: Path,
) -> None:
    seed_minimal_run(tmp_path)
    session_path = tmp_path / ".codex" / "sessions" / "mixed.jsonl"
    for index in range(200):
        append_jsonl(
            session_path,
            {
                "run_id": "demo-run",
                "type": "agent_message",
                "message": f"matching {index}",
                "timestamp": f"2026-07-15T00:00:{index:04d}Z",
            },
        )
        append_jsonl(
            session_path,
            {
                "run_id": "other-run",
                "type": "agent_message",
                "message": f"unrelated {index}",
            },
        )
        append_jsonl(
            session_path,
            {
                "run_id": "demo-run",
                "type": "unsupported",
                "message": f"unsupported {index}",
            },
        )
    app = create_test_app(project_root=tmp_path)

    with TestClient(app) as client:
        response = client.get(
            "/api/runs/demo-run/events", params={"kind": "agent"}
        )
        first = response.json()
        items = list(first["items"])
        cursor = first["next_cursor"]
        while cursor:
            page = client.get(
                "/api/runs/demo-run/events",
                params={"kind": "agent", "cursor": cursor},
            ).json()
            items.extend(page["items"])
            cursor = page["next_cursor"]

    matching = [item for item in items if item["message"].startswith("matching ")]
    assert len(matching) == 200
    assert response.headers["X-Loop-Event-Retention"] == (
        "structured=last-1000-lines-within-1048576-bytes;"
        "sessions=last-200-matching-supported-events-scanning-last-10000-lines-"
        "from-newest-128-files-within-2097152-bytes-each-and-at-most-4096-"
        "inspected-entries;logs=newest-1000"
    )


def test_session_discovery_uses_project_descriptors_not_path_rglob(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_minimal_run(tmp_path)
    sessions_dir = tmp_path / ".codex" / "sessions"
    append_jsonl(
        sessions_dir / "nested" / "session.jsonl",
        {
            "run_id": "demo-run",
            "type": "agent_message",
            "message": "descriptor session event",
        },
    )
    original_rglob = Path.rglob

    def reject_session_rglob(path: Path, pattern: str):
        if path == sessions_dir:
            raise AssertionError("session discovery used Path.rglob")
        return original_rglob(path, pattern)

    monkeypatch.setattr(Path, "rglob", reject_session_rglob)
    store = LoopDashboardStore(tmp_path)

    events = store.get_events("demo-run")

    assert events is not None
    assert any(
        item["message"] == "descriptor session event" for item in events
    )


def test_session_discovery_overflow_is_capacity_error(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    sessions_dir = tmp_path / ".codex" / "sessions"
    sessions_dir.mkdir(parents=True)
    for index in range(3):
        (sessions_dir / f"unrelated-{index}.txt").write_text(
            "not a session\n", encoding="utf-8"
        )
    store = LoopDashboardStore(
        tmp_path,
        session_discovery_max_entries=2,
    )

    with pytest.raises(SnapshotCapacityError, match="session discovery"):
        store.get_events("demo-run")


def test_snapshot_capacity_returns_status_error_not_cursor_400(tmp_path: Path) -> None:
    seed_minimal_run(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "demo-run"
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "scenario_results": [
                {
                    "scenario_id": "large-scenario",
                    "status": "fail",
                    "summary": "x" * 500,
                }
            ],
        },
    )
    client = TestClient(
        create_test_app(
            project_root=tmp_path,
            max_snapshot_row_bytes=128,
        )
    )

    response = client.get("/api/runs/demo-run/acceptance")

    assert response.status_code == 503
    assert response.json() == {
        "status": "capacity_exceeded",
        "error": {
            "code": "snapshot_capacity_exceeded",
            "message": "snapshot row byte budget exceeded",
        },
    }
