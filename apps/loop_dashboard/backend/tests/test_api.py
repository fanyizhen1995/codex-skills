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
