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


def test_api_returns_404_for_missing_run_and_traversal_run_id(tmp_path: Path) -> None:
    client = TestClient(create_app(project_root=tmp_path))

    missing = client.get("/api/runs/missing")
    traversal = client.get("/api/runs/%2E%2E%2Foutside")

    assert missing.status_code == 404
    assert missing.json()["detail"] == "run not found: missing"
    assert traversal.status_code == 404


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
