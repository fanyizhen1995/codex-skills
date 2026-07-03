import json
from pathlib import Path

import pytest

from loop_dashboard.store import LoopDashboardStore, safe_join


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def seed_run(
    repo_root: Path,
    run_id: str,
    phase: str,
    last_result: str = "none",
    next_action: str = "run_generator",
    evaluator_shape: str = "rich",
) -> None:
    run_dir = repo_root / ".codex" / "loop-runs" / run_id
    write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "policy": "demand_development",
            "phase": phase,
            "task_id": "loop-dashboard-dev-01",
            "domain": "",
            "branch": "feat/loop-dashboard",
            "worktree": str(repo_root),
            "requirement": "实现独立本地 Loop Dashboard，监控 loop、agent、skill 和日志。",
            "constraints": ["只读后端", "中文 UI"],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 1, "evaluator": 1, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {"max_eval_attempts": 2},
            "last_result": last_result,
            "next_action": next_action,
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )
    write_json(
        run_dir / "planner-output.json",
        {
            "task_id": "loop-dashboard-dev-01",
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": "Loop 看板",
            "goal": "实现看板",
            "non_goals": [],
            "allowed_paths": ["apps/loop_dashboard"],
            "denylist_paths": [".env"],
            "verify_commands": ["python3 -m pytest -q apps/loop_dashboard/backend/tests"],
            "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json",
            "stop_conditions": ["passed_waiting_human_merge"],
            "next_planning_hint": "",
        },
    )
    write_json(
        run_dir / "generator-result.json",
        {
            "task_id": "loop-dashboard-dev-01",
            "status": "implemented",
            "changed_paths": ["apps/loop_dashboard/backend/loop_dashboard/store.py"],
            "commit": "",
            "verify_commands": ["python3 -m pytest -q apps/loop_dashboard/backend/tests"],
            "verify_results": [{"command": "pytest", "status": "pass"}],
            "artifacts": ["apps/loop_dashboard/backend/loop_dashboard/store.py"],
            "cleanup_required": False,
            "notes": "完成只读 API",
        },
    )
    if evaluator_shape == "simplified":
        write_json(
            run_dir / "evaluator-result.json",
            {
                "status": "blocked",
                "task_id": "loop-dashboard-dev-01",
                "driver": "fake",
                "returncode": 1,
                "stdout": "token=inline-secret",
                "stderr": "scenario failed",
                "scenario_command_results_path": "scenario-results.json",
            },
        )
        write_json(
            run_dir / "scenario-results.json",
            {
                "commands": [
                    {
                        "command": "pytest",
                        "returncode": 1,
                        "stdout": "api_key=from-scenario",
                        "stderr": "assertion failed",
                    }
                ]
            },
        )
    else:
        write_json(
            run_dir / "evaluator-result.json",
            {
                "status": "fail" if phase == "repair_needed" else "pass",
                "gate": "task",
                "task_id": "loop-dashboard-dev-01",
                "final_bundle_id": "",
                "attempt": 1,
                "summary": "点击日志过滤失败" if phase == "repair_needed" else "通过",
                "findings": [
                    {
                        "id": "LD-001",
                        "severity": "major",
                        "category": "frontend_click",
                        "evidence": ["logs filter did not update"],
                        "recommended_action": "修复日志过滤",
                    }
                ]
                if phase == "repair_needed"
                else [],
                "scenario_results": [],
                "rerun_commands": [],
                "environment_checks": [],
                "verdict_reason": "需要修复" if phase == "repair_needed" else "通过",
                "next_action": "repair_and_reevaluate" if phase == "repair_needed" else "proceed_to_user_acceptance",
            },
        )
    (run_dir / "planner-attempt-1.stdout.log").write_text(
        "Planner: 正在拆解需求\nAuthorization: Bearer secret-token\n",
        encoding="utf-8",
    )
    (run_dir / "generator-attempt-1.stderr.log").write_text(
        "Generator 使用 skill: test-driven-development\n",
        encoding="utf-8",
    )


def test_safe_join_rejects_path_traversal_and_absolute_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        safe_join(tmp_path, "../outside")
    with pytest.raises(ValueError):
        safe_join(tmp_path, "/tmp/outside")


def test_list_runs_summarizes_agents_completed_and_blocked_states(tmp_path: Path) -> None:
    seed_run(tmp_path, "active-run", "repair_needed", last_result="fail", next_action="run_generator_repair")
    seed_run(
        tmp_path,
        "complete-run",
        "passed_waiting_human_merge",
        last_result="pass",
        next_action="await_human_merge_confirmation",
    )

    store = LoopDashboardStore(tmp_path)
    runs = store.list_runs()

    assert [run["run_id"] for run in runs] == ["complete-run", "active-run"]
    active = next(run for run in runs if run["run_id"] == "active-run")
    assert active["task_summary"].startswith("实现独立本地 Loop Dashboard")
    assert active["project_root"] == str(tmp_path.resolve())
    assert active["agents"]["planner"]["attempt"] == 1
    assert active["agents"]["generator"]["last_result"] == "完成只读 API"
    assert active["agents"]["evaluator"]["status"] == "fail"
    assert active["blocked_diagnostics"][0]["kind"] == "evaluator_finding"
    assert next(run for run in runs if run["run_id"] == "complete-run")["completed"] is True


def test_detail_includes_flow_nodes_events_and_redacted_logs(tmp_path: Path) -> None:
    seed_run(tmp_path, "active-run", "repair_needed", last_result="fail", next_action="run_generator_repair")

    store = LoopDashboardStore(tmp_path)
    detail = store.get_run("active-run")
    events = store.get_events("active-run")
    logs = store.get_logs("active-run")

    assert detail["flow_nodes"][0]["label"] == "Preflight"
    assert any(node["status"] == "running" for node in detail["flow_nodes"])
    assert any(event["kind"] == "artifact" for event in events)
    assert any(event["kind"] == "skill" for event in events)
    assert any(log["stream"] == "stdout" for log in logs)
    joined = "\n".join(log["content"] for log in logs)
    assert "Authorization: Bearer [REDACTED]" in joined
    assert "secret-token" not in joined


def test_simplified_evaluator_result_adds_blocked_diagnostic_and_inline_logs(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "simple-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )

    store = LoopDashboardStore(tmp_path)
    detail = store.get_run("simple-run")
    logs = store.get_logs("simple-run")

    assert any(item["kind"] == "evaluator_result" for item in detail["blocked_diagnostics"])
    assert any(log["source"] == "evaluator-result.json:stdout" for log in logs)
    assert any(log["source"].endswith("scenario-results.json:stdout") for log in logs)
    joined = "\n".join(log["content"] for log in logs)
    assert "token=[REDACTED]" in joined
    assert "api_key=[REDACTED]" in joined
    assert "inline-secret" not in joined
    assert "from-scenario" not in joined


def test_missing_loop_runs_directory_returns_empty_list(tmp_path: Path) -> None:
    assert LoopDashboardStore(tmp_path).list_runs() == []


def test_invalid_run_json_is_reported_without_breaking_other_runs(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "good-run",
        "passed_waiting_human_merge",
        last_result="pass",
        next_action="await_human_merge_confirmation",
    )
    broken = tmp_path / ".codex" / "loop-runs" / "broken-run"
    broken.mkdir(parents=True)
    (broken / "run.json").write_text("{bad json", encoding="utf-8")

    runs = LoopDashboardStore(tmp_path).list_runs()

    assert any(run["run_id"] == "good-run" for run in runs)
    invalid = next(run for run in runs if run["run_id"] == "broken-run")
    assert invalid["phase"] == "invalid_artifact"
    assert invalid["health"] == "blocked"
