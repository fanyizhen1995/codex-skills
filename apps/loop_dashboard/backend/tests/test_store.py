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
    assert "apps/loop_dashboard/backend/loop_dashboard/store.py" in active["agents"]["generator"]["artifact_paths"]
    assert active["agents"]["evaluator"]["status"] == "fail"
    assert active["blocked_diagnostics"][0]["kind"] == "evaluator_finding"
    assert active["constraints"] == ["只读后端", "中文 UI"]
    assert active["stop_conditions"] == ["passed_waiting_human_merge"]
    assert active["attempts"]["generator"] == 1
    assert active["flow_nodes"][0]["label"] == "Preflight"
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
    assert any(event["kind"] == "log" and event["source"].endswith("planner-attempt-1.stdout.log") for event in events)
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


def test_scenario_result_and_log_paths_accept_absolute_repo_relative_and_run_relative_paths(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "paths-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "paths-run"
    nested_dir = run_dir / "scenario-commands"
    nested_dir.mkdir(parents=True)
    (nested_dir / "stdout.log").write_text("api_key=run-relative-secret\n", encoding="utf-8")
    (nested_dir / "stderr.log").write_text("token=repo-relative-secret\n", encoding="utf-8")
    (nested_dir / "absolute.log").write_text("Authorization: Bearer absolute-secret\n", encoding="utf-8")
    write_json(
        nested_dir / "scenario-results.json",
        {
            "commands": [
                {
                    "command": "pytest",
                    "stdout_path": "scenario-commands/stdout.log",
                    "stderr_path": ".codex/loop-runs/paths-run/scenario-commands/stderr.log",
                },
                {
                    "command": "pytest -q",
                    "stdout_path": str(nested_dir / "absolute.log"),
                },
            ]
        },
    )
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["scenario_command_results_path"] = ".codex/loop-runs/paths-run/scenario-commands/scenario-results.json"
    write_json(run_dir / "evaluator-result.json", evaluator_result)

    store = LoopDashboardStore(tmp_path)
    logs = store.get_logs("paths-run")
    detail = store.get_run("paths-run")

    sources = {log["source"] for log in logs}
    assert ".codex/loop-runs/paths-run/scenario-commands/stdout.log" in sources
    assert ".codex/loop-runs/paths-run/scenario-commands/stderr.log" in sources
    assert ".codex/loop-runs/paths-run/scenario-commands/absolute.log" in sources
    joined = "\n".join(log["content"] for log in logs)
    assert "api_key=[REDACTED]" in joined
    assert "token=[REDACTED]" in joined
    assert "Authorization: Bearer [REDACTED]" in joined
    assert "run-relative-secret" not in joined
    assert "repo-relative-secret" not in joined
    assert "absolute-secret" not in joined
    assert ".codex/loop-runs/paths-run/scenario-commands/scenario-results.json" in detail["artifact_paths"]
    assert ".codex/loop-runs/paths-run/scenario-commands/stdout.log" in detail["artifact_paths"]


def test_scenario_result_and_log_paths_ignore_absolute_paths_outside_project_root(tmp_path: Path) -> None:
    outside_dir = tmp_path.parent / f"{tmp_path.name}-outside"
    outside_dir.mkdir()
    outside_result = outside_dir / "scenario-results.json"
    outside_log = outside_dir / "stdout.log"
    write_json(outside_result, {"commands": [{"stdout": "outside result leaked"}]})
    outside_log.write_text("outside absolute log leaked\n", encoding="utf-8")
    seed_run(
        tmp_path,
        "outside-paths-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "outside-paths-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["scenario_command_results_path"] = str(outside_result)
    evaluator_result["scenario_results"] = [{"stdout_path": str(outside_log)}]
    write_json(run_dir / "evaluator-result.json", evaluator_result)
    try:
        logs = LoopDashboardStore(tmp_path).get_logs("outside-paths-run")
    finally:
        outside_result.unlink(missing_ok=True)
        outside_log.unlink(missing_ok=True)
        outside_dir.rmdir()

    joined = "\n".join(log["content"] for log in logs)
    sources = {log["source"] for log in logs}
    assert "outside result leaked" not in joined
    assert "outside absolute log leaked" not in joined
    assert all(str(outside_dir) not in source for source in sources)


def test_scenario_result_and_log_paths_do_not_overread_unrelated_project_files(tmp_path: Path) -> None:
    secret_file = tmp_path / "private-notes.md"
    secret_file.write_text("private in-repo secret should not be exposed\n", encoding="utf-8")
    seed_run(
        tmp_path,
        "overread-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "overread-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["scenario_command_results_path"] = "private-notes.md"
    evaluator_result["scenario_results"] = [{"stdout_path": "private-notes.md"}]
    write_json(run_dir / "evaluator-result.json", evaluator_result)

    logs = LoopDashboardStore(tmp_path).get_logs("overread-run")

    joined = "\n".join(log["content"] for log in logs)
    sources = {log["source"] for log in logs}
    assert "private in-repo secret should not be exposed" not in joined
    assert "private-notes.md" not in sources


def test_malformed_evaluator_attempt_falls_back_to_run_attempts_and_logs(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "malformed-attempt-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "malformed-attempt-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["attempt"] = "n/a"
    write_json(run_dir / "evaluator-result.json", evaluator_result)
    (run_dir / "evaluator-attempt-4.stderr.log").write_text("evaluator attempt log\n", encoding="utf-8")

    detail = LoopDashboardStore(tmp_path).get_run("malformed-attempt-run")

    assert detail["agents"]["evaluator"]["attempt"] == 1

    evaluator_result["attempt"] = {}
    run_data = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    run_data["attempts"]["evaluator"] = "n/a"
    write_json(run_dir / "run.json", run_data)
    write_json(run_dir / "evaluator-result.json", evaluator_result)

    detail = LoopDashboardStore(tmp_path).get_run("malformed-attempt-run")

    assert detail["agents"]["evaluator"]["attempt"] == 4


def test_symlinked_log_and_rich_evaluator_result_outside_project_root_are_not_exposed(tmp_path: Path) -> None:
    outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-rich"
    outside_dir.mkdir()
    outside_log = outside_dir / "planner-attempt-9.stdout.log"
    outside_result = outside_dir / "result.json"
    outside_log.write_text("outside symlink log leaked\n", encoding="utf-8")
    write_json(
        outside_result,
        {
            "status": "fail",
            "stdout": "token=outside-rich-result",
            "findings": [{"id": "OUTSIDE", "recommended_action": "outside finding"}],
        },
    )
    seed_run(
        tmp_path,
        "symlink-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "symlink-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["final_bundle_id"] = "bundle-outside"
    write_json(run_dir / "evaluator-result.json", evaluator_result)
    task_dir = tmp_path / ".codex" / "evaluations" / "tasks" / "loop-dashboard-dev-01"
    task_dir.mkdir(parents=True)
    (task_dir / "bundle-outside").symlink_to(outside_dir, target_is_directory=True)
    (run_dir / "planner-attempt-9.stdout.log").symlink_to(outside_log)
    try:
        store = LoopDashboardStore(tmp_path)
        detail = store.get_run("symlink-run")
        logs = store.get_logs("symlink-run")
    finally:
        (run_dir / "planner-attempt-9.stdout.log").unlink(missing_ok=True)
        (task_dir / "bundle-outside").unlink(missing_ok=True)
        outside_log.unlink(missing_ok=True)
        outside_result.unlink(missing_ok=True)
        outside_dir.rmdir()

    joined = "\n".join(log["content"] for log in logs)
    assert "outside symlink log leaked" not in joined
    assert "outside-rich-result" not in joined
    assert all(item.get("title") != "OUTSIDE" for item in detail["blocked_diagnostics"])


def test_fixed_run_json_symlink_outside_run_dir_is_not_loaded(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "fixed-symlink-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )
    unrelated = tmp_path / "unrelated-evaluator-result.json"
    write_json(
        unrelated,
        {
            "status": "fail",
            "findings": [{"id": "LEAKED", "recommended_action": "outside run dir"}],
            "stdout": "token=outside-run-secret",
        },
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "fixed-symlink-run"
    (run_dir / "evaluator-result.json").unlink()
    (run_dir / "evaluator-result.json").symlink_to(unrelated)
    try:
        store = LoopDashboardStore(tmp_path)
        detail = store.get_run("fixed-symlink-run")
        logs = store.get_logs("fixed-symlink-run")
    finally:
        (run_dir / "evaluator-result.json").unlink(missing_ok=True)
        unrelated.unlink(missing_ok=True)

    assert all(item.get("title") != "LEAKED" for item in detail["blocked_diagnostics"])
    assert "outside-run-secret" not in "\n".join(log["content"] for log in logs)


def test_rich_evaluator_bundle_result_is_merged_into_blocked_diagnostics_and_logs(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "bundle-run",
        "repair_needed",
        last_result="blocked",
        next_action="repair_from_evaluator_findings",
        evaluator_shape="simplified",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "bundle-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["final_bundle_id"] = "bundle-b"
    write_json(run_dir / "evaluator-result.json", evaluator_result)
    write_json(
        tmp_path / ".codex" / "evaluations" / "tasks" / "loop-dashboard-dev-01" / "bundle-a" / "result.json",
        {
            "status": "fail",
            "summary": "older result",
            "findings": [
                {
                    "id": "OLD",
                    "severity": "minor",
                    "summary": "old finding",
                }
            ],
        },
    )
    write_json(
        tmp_path / ".codex" / "evaluations" / "tasks" / "loop-dashboard-dev-01" / "bundle-b" / "result.json",
        {
            "status": "fail",
            "summary": "rich bundle found blocked diagnostics",
            "stdout": "bundle stdout token=bundle-secret",
            "findings": [
                {
                    "id": "BUNDLE-001",
                    "severity": "critical",
                    "category": "spec",
                    "summary": "summary fallback",
                    "evidence": ["rich bundle evidence"],
                    "recommended_action": "include rich finding",
                }
            ],
        },
    )

    store = LoopDashboardStore(tmp_path)
    detail = store.get_run("bundle-run")
    logs = store.get_logs("bundle-run")
    events = store.get_events("bundle-run")

    diagnostic = next(item for item in detail["blocked_diagnostics"] if item["title"] == "BUNDLE-001")
    assert diagnostic["severity"] == "critical"
    assert diagnostic["message"] == "include rich finding"
    assert diagnostic["source"].endswith(".codex/evaluations/tasks/loop-dashboard-dev-01/bundle-b/result.json")
    assert all(item["title"] != "OLD" for item in detail["blocked_diagnostics"])
    assert any(log["source"] == "result.json:stdout" and "bundle-secret" not in log["content"] for log in logs)
    assert any(event["kind"] == "log" and event["source"] == "result.json:stdout" for event in events)


def test_evaluator_finding_diagnostics_are_redacted(tmp_path: Path) -> None:
    seed_run(tmp_path, "finding-secret-run", "repair_needed", last_result="fail")
    run_dir = tmp_path / ".codex" / "loop-runs" / "finding-secret-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["findings"] = [
        {
            "id": "SECRET-FINDING",
            "severity": "major",
            "recommended_action": "rotate apiKey=diagnostic-secret",
            "evidence": ["Authorization: Basic evidence-secret"],
        }
    ]
    write_json(run_dir / "evaluator-result.json", evaluator_result)

    detail = LoopDashboardStore(tmp_path).get_run("finding-secret-run")
    diagnostic = next(item for item in detail["blocked_diagnostics"] if item["title"] == "SECRET-FINDING")

    assert diagnostic["message"] == "rotate apiKey=[REDACTED]"
    assert diagnostic["evidence"] == ["Authorization: [REDACTED]"]
    assert "diagnostic-secret" not in json.dumps(diagnostic, ensure_ascii=False)
    assert "evidence-secret" not in json.dumps(diagnostic, ensure_ascii=False)


def test_flow_nodes_include_required_loop_steps_and_node_details(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "flow-run",
        "repair_needed",
        last_result="fail",
        next_action="run_generator_repair",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "flow-run"
    write_json(run_dir / "artifact-manifest.json", {"status": "pass", "artifacts": []})
    write_json(run_dir / "cleanup-result.json", {"status": "pending"})

    detail = LoopDashboardStore(tmp_path).get_run("flow-run")
    nodes = detail["flow_nodes"]

    assert [node["id"] for node in nodes] == [
        "preflight",
        "planner",
        "generator",
        "evaluator",
        "repair_needed",
        "artifact_hygiene",
        "cleanup",
        "human_merge",
    ]
    evaluator = next(node for node in nodes if node["id"] == "evaluator")
    repair = next(node for node in nodes if node["id"] == "repair_needed")
    assert evaluator["status"] == "blocked"
    assert repair["status"] == "running"
    assert evaluator["current_action"]
    assert evaluator["recent_result"]
    assert evaluator["artifact_paths"]


def test_autonomous_flow_nodes_include_commit_and_planner_loop(tmp_path: Path) -> None:
    seed_run(tmp_path, "autonomous-flow-run", "evaluating", next_action="run_evaluator")
    run_dir = tmp_path / ".codex" / "loop-runs" / "autonomous-flow-run"
    run_data = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    run_data["policy"] = "autonomous_knowledge"
    write_json(run_dir / "run.json", run_data)
    write_json(run_dir / "commit-result.json", {"status": "pass", "commit": "abc123"})

    detail = LoopDashboardStore(tmp_path).get_run("autonomous-flow-run")

    assert [node["id"] for node in detail["flow_nodes"]] == [
        "planner",
        "generator",
        "evaluator",
        "artifact_hygiene",
        "cleanup",
        "commit",
        "planner_loop",
    ]


def test_codex_session_jsonl_events_are_included_with_token_counts(tmp_path: Path) -> None:
    seed_run(tmp_path, "session-run", "repair_needed", last_result="fail")
    session_dir = tmp_path / ".codex" / "sessions"
    session_dir.mkdir(parents=True)
    session_file = session_dir / "session.jsonl"
    session_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "run_id": "session-run",
                        "type": "agent_message",
                        "agent": "planner",
                        "message": "Planner saw Authorization: Basic session-secret",
                        "timestamp": "2026-07-03T00:00:00Z",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "run_id": "session-run",
                        "type": "token_usage",
                        "agent": "generator",
                        "tokens": {"input": 11, "output": 7, "accessToken": "token-usage-secret"},
                        "timestamp": "2026-07-03T00:00:01Z",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    events = LoopDashboardStore(tmp_path).get_events("session-run")

    assert any(event["kind"] == "agent" and "Planner saw Authorization: [REDACTED]" in event["message"] for event in events)
    assert any(event["kind"] == "token" and "input=11" in event["message"] and "output=7" in event["message"] for event in events)
    assert any(event["kind"] == "token" and "accessToken=[REDACTED]" in event["message"] for event in events)
    assert all("session-secret" not in event["message"] for event in events)
    assert all("token-usage-secret" not in event["message"] for event in events)


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
