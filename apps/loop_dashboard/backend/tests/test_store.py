import json
import os
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


def test_list_runs_includes_project_worktree_history(tmp_path: Path) -> None:
    worktree_root = tmp_path / ".worktrees" / "loop-dashboard"
    seed_run(
        worktree_root,
        "loop-dashboard-dev",
        "passed_waiting_human_merge",
        last_result="pass",
        next_action="await_human_merge_confirmation",
    )

    runs = LoopDashboardStore(tmp_path).list_runs()

    assert [run["run_id"] for run in runs] == ["loop-dashboard-dev"]
    run = runs[0]
    assert run["completed"] is True
    assert run["source_kind"] == "worktree"
    assert run["source_path"] == ".worktrees/loop-dashboard/.codex/loop-runs/loop-dashboard-dev"


def test_duplicate_run_id_prefers_newest_source(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "duplicate-run",
        "repair_needed",
        last_result="fail",
        next_action="run_generator_repair",
    )
    worktree_root = tmp_path / ".worktrees" / "loop-dashboard"
    seed_run(
        worktree_root,
        "duplicate-run",
        "passed_waiting_human_merge",
        last_result="pass",
        next_action="await_human_merge_confirmation",
    )
    current_run = tmp_path / ".codex" / "loop-runs" / "duplicate-run" / "run.json"
    worktree_run = worktree_root / ".codex" / "loop-runs" / "duplicate-run" / "run.json"
    os.utime(current_run, (1_700_000_000, 1_700_000_000))
    os.utime(worktree_run, (1_800_000_000, 1_800_000_000))

    store = LoopDashboardStore(tmp_path)
    runs = store.list_runs()
    detail = store.get_run("duplicate-run")

    assert [run["run_id"] for run in runs] == ["duplicate-run"]
    assert runs[0]["source_kind"] == "worktree"
    assert runs[0]["phase"] == "passed_waiting_human_merge"
    assert detail["source_kind"] == "worktree"
    assert detail["phase"] == "passed_waiting_human_merge"


def test_detail_keeps_full_task_description_while_list_uses_short_summary(tmp_path: Path) -> None:
    seed_run(tmp_path, "long-run", "passed_waiting_human_merge", last_result="pass", next_action="await_human_merge_confirmation")
    full_requirement = (
        "实现独立本地 Loop Dashboard，用于中文可视化监控当前项目 Planner Generator Evaluator loop、"
        "agent、skill、日志、完成态和阻塞诊断；本次还需要验证开发流程并修复流程 bug。"
    )
    run_json = tmp_path / ".codex" / "loop-runs" / "long-run" / "run.json"
    run_data = json.loads(run_json.read_text(encoding="utf-8"))
    run_data["requirement"] = full_requirement
    write_json(run_json, run_data)

    store = LoopDashboardStore(tmp_path)
    listed = store.list_runs()[0]
    detail = store.get_run("long-run")

    assert listed["task_summary"].endswith("…")
    assert listed["task_summary"] != full_requirement
    assert detail["task_description"] == full_requirement


def test_detail_includes_decision_and_acceptance_summaries_for_passed_run(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "accepted-run",
        "passed_waiting_human_merge",
        last_result="pass",
        next_action="await_human_merge_confirmation",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "accepted-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["final_bundle_id"] = "bundle-pass"
    evaluator_result["scenario_results"] = [
        {
            "scenario_id": "api-summary",
            "status": "pass",
            "summary": "API includes summaries",
        }
    ]
    evaluator_result["rerun_commands"] = ["pytest -q apps/loop_dashboard/backend/tests/test_store.py"]
    evaluator_result["environment_checks"] = [{"name": "backend pytest", "status": "pass"}]
    write_json(run_dir / "evaluator-result.json", evaluator_result)
    write_json(
        tmp_path / ".codex" / "evaluations" / "tasks" / "loop-dashboard-dev-01" / "bundle-pass" / "result.json",
        {
            "status": "pass",
            "scenario_id": "browser-acceptance",
            "checked": ["任务摘要", {"label": "验收场景"}],
            "scenario_results": [
                {
                    "scenario_id": "browser-acceptance",
                    "status": "pass",
                    "summary": "Dashboard shows human-readable acceptance",
                }
            ],
            "browser_evidence": [
                "summary panel visible",
                {"text": "Authorization: Bearer browser-secret"},
            ],
        },
    )

    detail = LoopDashboardStore(tmp_path).get_run("accepted-run")

    assert detail["decision_summary"] == {
        "requires_user_decision": True,
        "decision_label": "等待用户确认合入",
        "next_action": "await_human_merge_confirmation",
        "reason": "通过",
    }
    assert detail["acceptance_summary"]["status"] == "pass"
    assert detail["acceptance_summary"]["scenarios"] == [
        {
            "scenario_id": "browser-acceptance",
            "status": "pass",
            "summary": "Dashboard shows human-readable acceptance",
        },
        {
            "scenario_id": "api-summary",
            "status": "pass",
            "summary": "API includes summaries",
        },
    ]
    assert detail["acceptance_summary"]["checked"] == ["任务摘要", "验收场景"]
    assert "pytest -q apps/loop_dashboard/backend/tests/test_store.py" in detail["acceptance_summary"]["rerun_commands"]
    evidence = json.dumps(detail["acceptance_summary"]["evidence"], ensure_ascii=False)
    assert "summary panel visible" in evidence
    assert "backend pytest" in evidence
    assert "Authorization: Bearer [REDACTED]" in evidence
    assert "browser-secret" not in evidence


def test_detail_includes_user_decision_and_redacted_finding_evidence_for_repair_run(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "repair-summary-run",
        "repair_needed",
        last_result="fail",
        next_action="repair_from_evaluator_findings",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "repair-summary-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["findings"] = [
        {
            "id": "LD-SECRET",
            "severity": "major",
            "summary": "Log filter failed",
            "evidence": ["api_key=finding-secret", {"stdout": "token=object-secret"}],
            "recommended_action": "修复日志过滤",
        }
    ]
    evaluator_result["scenario_results"] = [
        {"scenario_id": "log-filter", "status": "fail", "summary": "Log filter did not update"}
    ]
    evaluator_result["rerun_commands"] = ["python3 scripts/loop_dashboard_evaluator.py"]
    write_json(run_dir / "evaluator-result.json", evaluator_result)

    detail = LoopDashboardStore(tmp_path).get_run("repair-summary-run")

    assert detail["decision_summary"]["requires_user_decision"] is False
    assert detail["decision_summary"]["decision_label"] == "自动修复后复验"
    assert detail["decision_summary"]["next_action"] == "repair_from_evaluator_findings"
    assert detail["decision_summary"]["reason"] == "需要修复"
    assert detail["acceptance_summary"]["status"] == "fail"
    assert detail["acceptance_summary"]["scenarios"] == [
        {"scenario_id": "log-filter", "status": "fail", "summary": "Log filter did not update"}
    ]
    evidence = json.dumps(detail["acceptance_summary"]["evidence"], ensure_ascii=False)
    assert "LD-SECRET" in evidence
    assert "修复日志过滤" in evidence
    assert "api_key=[REDACTED]" in evidence
    assert "token=[REDACTED]" in evidence
    assert "finding-secret" not in evidence
    assert "object-secret" not in evidence
    assert detail["acceptance_summary"]["rerun_commands"] == ["python3 scripts/loop_dashboard_evaluator.py"]


def test_acceptance_summary_redacts_finding_titles_and_includes_scenario_evidence(tmp_path: Path) -> None:
    seed_run(tmp_path, "redaction-run", "repair_needed", last_result="fail", next_action="run_generator_repair")
    run_dir = tmp_path / ".codex" / "loop-runs" / "redaction-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["findings"] = [
        {
            "id": "token=title-secret",
            "evidence": ["visible evidence"],
            "recommended_action": "修复验收摘要",
        }
    ]
    evaluator_result["scenario_results"] = [
        {
            "scenario_id": "scenario-evidence",
            "status": "fail",
            "summary": "Scenario evidence should be visible",
            "evidence": ["点击运行详情", "Authorization: Bearer scenario-secret"],
        }
    ]
    write_json(run_dir / "evaluator-result.json", evaluator_result)

    detail = LoopDashboardStore(tmp_path).get_run("redaction-run")
    evidence = json.dumps(detail["acceptance_summary"]["evidence"], ensure_ascii=False)

    assert "token=[REDACTED]" in evidence
    assert "title-secret" not in evidence
    assert "点击运行详情" in evidence
    assert "Authorization: Bearer [REDACTED]" in evidence
    assert "scenario-secret" not in evidence


def test_acceptance_summary_falls_back_to_scenario_contract_for_older_results(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "contract-fallback-run",
        "passed_waiting_human_merge",
        last_result="pass",
        next_action="await_human_merge_confirmation",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "contract-fallback-run"
    evaluator_result = json.loads((run_dir / "evaluator-result.json").read_text(encoding="utf-8"))
    evaluator_result["scenario_results"] = [
        {"scenario_id": "CONTRACT-SCENARIO", "status": "pass", "evidence": ["summary.md#CONTRACT-SCENARIO"]}
    ]
    evaluator_result["summary"] = ""
    evaluator_result["verdict_reason"] = ""
    write_json(run_dir / "evaluator-result.json", evaluator_result)
    write_json(
        tmp_path / "docs" / "harness" / "evaluator-scenarios" / "loop-dashboard-dev-01.json",
        {
            "task_id": "loop-dashboard-dev-01",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "CONTRACT-SCENARIO",
                    "user_goal": "作为操作者打开看板并确认任务、流程和日志都可读。",
                    "steps": ["打开看板", "点击运行", "过滤日志"],
                    "expected_outcomes": ["详情可见", "日志已脱敏"],
                    "entrypoint": "python3 scripts/loop_dashboard_evaluator.py",
                }
            ],
        },
    )

    detail = LoopDashboardStore(tmp_path).get_run("contract-fallback-run")

    assert detail["acceptance_summary"]["scenarios"] == [
        {
            "scenario_id": "CONTRACT-SCENARIO",
            "status": "pass",
            "summary": "作为操作者打开看板并确认任务、流程和日志都可读。",
        }
    ]
    assert detail["acceptance_summary"]["checked"] == ["打开看板", "点击运行", "过滤日志"]
    assert detail["acceptance_summary"]["evidence"] == [
        "CONTRACT-SCENARIO: summary.md#CONTRACT-SCENARIO",
        "详情可见",
        "日志已脱敏",
    ]
    assert detail["acceptance_summary"]["rerun_commands"] == ["python3 scripts/loop_dashboard_evaluator.py"]


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


def test_detail_exposes_governance_artifacts_and_formal_verification(tmp_path: Path) -> None:
    seed_run(tmp_path, "ai-infra-loop-governance-dev-child-004", "repair_needed", last_result="fail", next_action="repair_and_reevaluate")
    run_dir = tmp_path / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev-child-004"
    formal_dir = run_dir / "formal-verification"
    formal_dir.mkdir(parents=True)
    write_json(
        formal_dir / "formal-001.json",
        {
            "phase": "formal_suspicion_pass",
            "suspicions": [
                {
                    "id": "formal-confirmed-bug",
                    "risk": "high",
                    "result": "confirmed_bug",
                    "repair_required": True,
                    "counterexample": {
                        "artifact_path": ".codex/loop-runs/ai-infra-loop-governance-dev-child-004/counterexample-tests/formal-confirmed-bug.json",
                        "command": "pytest -q tests/test_formal.py",
                    },
                }
            ],
        },
    )
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": "fail",
            "task_id": "ai-infra-loop-governance-dev-child-004-task",
            "driver": "fake",
            "returncode": 1,
            "stdout": "formal suspicion confirmed a bug\n",
            "stderr": "",
            "next_action": "repair_and_reevaluate",
            "formal_verification": {
                "status": "fail",
                "next_action": "repair_and_reevaluate",
                "artifact_paths": [
                    ".codex/loop-runs/ai-infra-loop-governance-dev-child-004/formal-verification/formal-001.json"
                ],
                "findings": [],
                "required_counterexample_reruns": [
                    {
                        "id": "formal-confirmed-bug",
                        "command": "pytest -q tests/test_formal.py",
                        "artifact_path": ".codex/loop-runs/ai-infra-loop-governance-dev-child-004/counterexample-tests/formal-confirmed-bug.json",
                    }
                ],
            },
        },
    )
    write_json(
        run_dir / "task-contract.json",
        {
            "task_id": "ai-infra-loop-governance-dev-child-004-task",
            "title": "Formal suspicion",
            "description": "Verify formal suspicion.",
            "verify_commands": [],
            "scenario_commands": [],
            "artifact_paths": [
                "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
            ],
            "required_services": [],
            "evaluator_driver": "harness_auto_gate",
            "eval_policy": {"task_level_required": True},
            "allowed_scope": "local_repo_and_harness",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "GOV-01",
                    "user_goal": "确认治理 artifacts 在看板可见。",
                    "steps": ["打开 run detail"],
                    "expected_outcomes": ["formal verification 可见"],
                    "failure_signals": ["只看到 run.json"],
                }
            ],
        },
    )
    snapshot_path = tmp_path / "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
    write_json(snapshot_path, {"schema_version": 1, "record_counts": {"channels": 1, "sources": 1}})

    detail = LoopDashboardStore(tmp_path).get_run("ai-infra-loop-governance-dev-child-004")

    governance = detail["governance_artifacts"]
    assert governance["formal_verification"]["status"] == "fail"
    assert governance["formal_verification"]["next_action"] == "repair_and_reevaluate"
    assert governance["formal_verification_artifact_paths"] == [
        ".codex/loop-runs/ai-infra-loop-governance-dev-child-004/formal-verification/formal-001.json"
    ]
    assert governance["task_contract_artifact_paths"] == [
        "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
    ]
    assert governance["evaluator_scenarios"][0]["scenario_id"] == "GOV-01"
    assert governance["source_profile_snapshots"] == [
        "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
    ]


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


def seed_parent_child_runs(repo_root: Path) -> None:
    parent_dir = repo_root / ".codex" / "loop-runs" / "parent-run"
    write_json(
        parent_dir / "run.json",
        {
            "run_id": "parent-run",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "Parent requirement for dashboard",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 2, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_parent_planner",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["parent-run-child-002", "missing-child"],
            "current_child_run_id": "parent-run-child-002",
            "backlog": [],
            "aggregate_acceptance": {"total": 2, "passed": 1, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            "reader_summary": {"purpose": "Explain parent", "current_progress": "One child passed", "next_step": "Run child 2", "decision_needed": "No"},
            "accepted_changed_paths": ["generated/child-001.txt"],
        },
    )
    for index, phase in [(1, "passed"), (2, "generating")]:
        child_id = f"parent-run-child-{index:03d}"
        child_dir = repo_root / ".codex" / "loop-runs" / child_id
        write_json(
            child_dir / "run.json",
            {
                "run_id": child_id,
                "run_kind": "child",
                "parent_run_id": "parent-run",
                "child_index": index,
                "policy": "demand_development",
                "phase": phase,
                "task_id": f"{child_id}-task",
                "domain": "",
                "branch": "main",
                "worktree": str(repo_root),
                "requirement": f"Child {index} description with enough text to wrap cleanly",
                "constraints": [],
                "stop_conditions": ["passed"],
                "baseline_dirty_paths": [],
                "allowed_paths": [f"generated/child-{index:03d}.txt"],
                "denylist_paths": [],
                "attempts": {"planner": 1, "generator": 1, "evaluator": 1 if phase == "passed" else 0, "artifact_hygiene": 0, "cleanup": 0},
                "limits": {},
                "last_result": "pass" if phase == "passed" else "none",
                "next_action": "return_to_parent_planner" if phase == "passed" else "run_child_generator",
                "attempt_history": [],
                "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
                "reader_summary": {
                    "purpose": f"Child {index}",
                    "planner_action": "Planner picked child",
                    "generator_action": "Generator wrote file",
                    "evaluator_action": "Evaluator checked result",
                    "acceptance_result": "Passed" if phase == "passed" else "Pending",
                },
            },
        )
        (child_dir / "events.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": "2026-07-03T00:00:00Z",
                    "run_id": child_id,
                    "parent_run_id": "parent-run",
                    "child_id": f"child-{index:03d}",
                    "actor": "planner",
                    "event_type": "plan",
                    "summary": f"Planner selected child {index}",
                    "details": {},
                    "artifact_paths": [],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )


def test_parent_child_runs_are_aggregated_with_children_and_events(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    store = LoopDashboardStore(tmp_path)

    runs = store.list_runs()
    parent = next(run for run in runs if run["run_id"] == "parent-run")
    detail = store.get_run("parent-run")
    events = store.get_events("parent-run")

    assert parent["run_kind"] == "parent"
    assert parent["children_summary"]["total"] == 2
    assert parent["children_summary"]["passed"] == 1
    assert detail["reader_summary"]["purpose"] == "Explain parent"
    assert [child["run_id"] for child in detail["children"]] == ["parent-run-child-001", "parent-run-child-002"]
    assert detail["children"][0]["reader_summary"]["acceptance_result"] == "Passed"
    assert any(event["kind"] == "plan" and "Planner selected child 1" in event["message"] for event in events)
    assert any(item["kind"] == "child_artifact_missing" for item in detail["relationship_diagnostics"])


def test_parent_acceptance_summary_aggregates_child_evaluator_results(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    child_dir = tmp_path / ".codex" / "loop-runs" / "parent-run-child-001"
    write_json(
        child_dir / "evaluator-result.json",
        {
            "status": "pass",
            "task_id": "parent-run-child-001-task",
            "summary": "子任务浏览器验收通过",
            "scenario_results": [
                {
                    "scenario_id": "CHILD-UI-001",
                    "status": "pass",
                    "summary": "Evaluator 模拟用户检查子任务页面，验证功能实现完整性和设计匹配。",
                    "evidence": ["点击子任务 tab", "核对设计 mock 中的 Agent 结果和验收区域"],
                }
            ],
            "checked": ["功能实现完整性", "设计/mock 匹配"],
            "rerun_commands": ["python3 scripts/loop_dashboard_evaluator.py --child parent-run-child-001"],
        },
    )

    detail = LoopDashboardStore(tmp_path).get_run("parent-run")

    acceptance = detail["acceptance_summary"]
    assert acceptance["status"] in {"pass", "partial"}
    scenario_text = json.dumps(acceptance["scenarios"], ensure_ascii=False)
    assert "parent-run-child-001" in scenario_text
    assert "功能实现完整性和设计匹配" in scenario_text
    checked_text = json.dumps(acceptance["checked"], ensure_ascii=False)
    assert "功能实现完整性" in checked_text
    assert "设计/mock 匹配" in checked_text
    evidence_text = json.dumps(acceptance["evidence"], ensure_ascii=False)
    assert "核对设计 mock" in evidence_text
    assert "parent-run-child-001" in evidence_text
    assert acceptance["rerun_commands"] == ["python3 scripts/loop_dashboard_evaluator.py --child parent-run-child-001"]


def test_top_level_list_runs_hides_children_that_have_existing_parent(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)

    runs = LoopDashboardStore(tmp_path).list_runs()

    run_ids = [run["run_id"] for run in runs]
    assert "parent-run" in run_ids
    assert "parent-run-child-001" not in run_ids
    assert "parent-run-child-002" not in run_ids


def test_list_runs_keeps_orphan_child_top_level(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".codex" / "loop-runs" / "orphan-child" / "run.json",
        {
            "run_id": "orphan-child",
            "run_kind": "child",
            "parent_run_id": "missing-parent",
            "child_index": 1,
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "orphan-child-task",
            "domain": "",
            "branch": "main",
            "worktree": str(tmp_path),
            "requirement": "Orphan child should remain visible",
            "constraints": [],
            "stop_conditions": ["passed"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_child_generator",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )

    runs = LoopDashboardStore(tmp_path).list_runs()

    assert [run["run_id"] for run in runs] == ["orphan-child"]


def test_top_level_list_runs_hides_explicit_orphan_child_when_parent_exists(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".codex" / "loop-runs" / "parent-run" / "run.json",
        {
            "run_id": "parent-run",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(tmp_path),
            "requirement": "Parent with explicit orphan child",
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
            "child_run_ids": ["explicit-orphan-child"],
            "current_child_run_id": "explicit-orphan-child",
            "aggregate_acceptance": {"total": 1, "passed": 0, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
        },
    )
    write_json(
        tmp_path / ".codex" / "loop-runs" / "explicit-orphan-child" / "run.json",
        {
            "run_id": "explicit-orphan-child",
            "run_kind": "child",
            "child_index": 1,
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "explicit-orphan-child-task",
            "domain": "",
            "branch": "main",
            "worktree": str(tmp_path),
            "requirement": "Explicit orphan child should be hidden by parent",
            "constraints": [],
            "stop_conditions": ["passed"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_child_generator",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )

    runs = LoopDashboardStore(tmp_path).list_runs()

    assert [run["run_id"] for run in runs] == ["parent-run"]


def test_parent_child_relationship_conflicts_are_deduped_sorted_and_diagnosed(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    other_parent = tmp_path / ".codex" / "loop-runs" / "other-parent" / "run.json"
    payload = json.loads((tmp_path / ".codex" / "loop-runs" / "parent-run" / "run.json").read_text(encoding="utf-8"))
    payload["run_id"] = "other-parent"
    payload["child_run_ids"] = ["parent-run-child-001"]
    write_json(other_parent, payload)
    child_path = tmp_path / ".codex" / "loop-runs" / "parent-run-child-001" / "run.json"
    child_payload = json.loads(child_path.read_text(encoding="utf-8"))
    child_payload["parent_run_id"] = "other-parent"
    child_path.write_text(json.dumps(child_payload, indent=2), encoding="utf-8")

    detail = LoopDashboardStore(tmp_path).get_run("parent-run")

    assert [child["run_id"] for child in detail["children"]].count("parent-run-child-001") == 0
    assert any(item["kind"] == "child_parent_conflict" for item in detail["relationship_diagnostics"])


def test_top_level_list_runs_keeps_conflicting_child_visible(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".codex" / "loop-runs" / "parent-run" / "run.json",
        {
            "run_id": "parent-run",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(tmp_path),
            "requirement": "Parent with conflicting child",
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
            "child_run_ids": ["child-x"],
            "current_child_run_id": "child-x",
            "aggregate_acceptance": {"total": 1, "passed": 0, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
        },
    )
    write_json(
        tmp_path / ".codex" / "loop-runs" / "child-x" / "run.json",
        {
            "run_id": "child-x",
            "run_kind": "child",
            "parent_run_id": "missing-parent",
            "child_index": 1,
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "child-x-task",
            "domain": "",
            "branch": "main",
            "worktree": str(tmp_path),
            "requirement": "Conflicting child should remain top level",
            "constraints": [],
            "stop_conditions": ["passed"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_child_generator",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )

    store = LoopDashboardStore(tmp_path)
    detail = store.get_run("parent-run")
    runs = store.list_runs()

    assert [child["run_id"] for child in detail["children"]] == []
    assert [run["run_id"] for run in runs] == ["child-x", "parent-run"]


def test_parent_child_relationship_rejects_path_traversal(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    parent_path = tmp_path / ".codex" / "loop-runs" / "parent-run" / "run.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent["child_run_ids"].append("../outside")
    parent_path.write_text(json.dumps(parent, indent=2), encoding="utf-8")

    detail = LoopDashboardStore(tmp_path).get_run("parent-run")

    assert all(child["run_id"] != "../outside" for child in detail["children"])
    assert any(item["kind"] == "unsafe_child_reference" for item in detail["relationship_diagnostics"])


def test_parent_child_relationship_uses_newest_duplicate_child_source(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    current_child_dir = tmp_path / ".codex" / "loop-runs" / "parent-run-child-001"
    worktree_root = tmp_path / ".worktrees" / "older-source"
    worktree_child_dir = worktree_root / ".codex" / "loop-runs" / "parent-run-child-001"
    child_payload = json.loads((current_child_dir / "run.json").read_text(encoding="utf-8"))
    stale_payload = {**child_payload, "requirement": "stale duplicate child"}
    stale_payload["reader_summary"] = {"purpose": "stale child", "acceptance_result": "Stale"}
    write_json(worktree_child_dir / "run.json", stale_payload)
    (worktree_child_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-07-03T00:00:00Z",
                "run_id": "parent-run-child-001",
                "parent_run_id": "parent-run",
                "event_type": "plan",
                "summary": "stale child event",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    fresh_payload = json.loads((current_child_dir / "run.json").read_text(encoding="utf-8"))
    fresh_payload["reader_summary"] = {"purpose": "fresh child", "acceptance_result": "Fresh"}
    write_json(current_child_dir / "run.json", fresh_payload)
    (current_child_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-07-03T00:00:01Z",
                "run_id": "parent-run-child-001",
                "parent_run_id": "parent-run",
                "event_type": "plan",
                "summary": "fresh child event",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    older = 1_700_000_000
    newer = 1_800_000_000
    for path in worktree_child_dir.iterdir():
        os.utime(path, (older, older))
    for path in current_child_dir.iterdir():
        os.utime(path, (newer, newer))

    store = LoopDashboardStore(tmp_path)
    detail = store.get_run("parent-run")
    events = store.get_events("parent-run")

    child = next(item for item in detail["children"] if item["run_id"] == "parent-run-child-001")
    assert child["source_kind"] == "current"
    assert child["reader_summary"]["purpose"] == "fresh child"
    event_messages = [event["message"] for event in events if event["kind"] == "plan"]
    assert "fresh child event" in event_messages
    assert "stale child event" not in event_messages


def test_parent_child_structured_events_are_redacted(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    child_events_path = tmp_path / ".codex" / "loop-runs" / "parent-run-child-001" / "events.jsonl"
    child_events_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-07-03T00:00:02Z",
                "run_id": "parent-run-child-001",
                "parent_run_id": "parent-run",
                "event_type": "plan",
                "summary": "Planner used token=structured-secret and Authorization: Bearer child-secret",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    events = LoopDashboardStore(tmp_path).get_events("parent-run")

    messages = "\n".join(event["message"] for event in events)
    assert "token=[REDACTED]" in messages
    assert "Authorization: Bearer [REDACTED]" in messages
    assert "structured-secret" not in messages
    assert "child-secret" not in messages


def test_events_skip_dangling_symlink_artifacts(tmp_path: Path) -> None:
    seed_run(tmp_path, "dangling-events-run", "generating")
    run_dir = tmp_path / ".codex" / "loop-runs" / "dangling-events-run"
    (run_dir / "dangling.log").symlink_to(run_dir / "missing-target.log")

    events = LoopDashboardStore(tmp_path).get_events("dangling-events-run")

    assert events is not None
    assert any(event["kind"] == "artifact" and event["source"].endswith("run.json") for event in events)
    assert all("dangling.log" not in event["source"] for event in events)


def test_session_events_skip_dangling_symlink_files(tmp_path: Path) -> None:
    seed_run(tmp_path, "session-dangling-run", "generating")
    sessions_dir = tmp_path / ".codex" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "bad.jsonl").symlink_to(sessions_dir / "missing.jsonl")
    (sessions_dir / "good.jsonl").write_text(
        json.dumps(
            {
                "run_id": "session-dangling-run",
                "type": "agent_message",
                "agent": "planner",
                "message": "Planner session event",
                "timestamp": "2026-07-03T00:00:00Z",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    events = LoopDashboardStore(tmp_path).get_events("session-dangling-run")

    assert any(event["kind"] == "agent" and "Planner session event" in event["message"] for event in events)
    assert all("bad.jsonl" not in event["source"] for event in events)


def test_multi_parent_explicit_orphan_child_has_single_owner_and_diagnostic(tmp_path: Path) -> None:
    for parent_id in ("parent-b", "parent-a"):
        parent_dir = tmp_path / ".codex" / "loop-runs" / parent_id
        write_json(
            parent_dir / "run.json",
            {
                "run_id": parent_id,
                "run_kind": "parent",
                "policy": "demand_development",
                "phase": "child_running",
                "task_id": "",
                "domain": "",
                "branch": "main",
                "worktree": str(tmp_path),
                "requirement": f"{parent_id} requirement",
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
                "child_run_ids": ["shared-child"],
                "current_child_run_id": "shared-child",
                "aggregate_acceptance": {"total": 1, "passed": 0, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            },
        )
    older = 1_700_000_000
    newer = 1_800_000_000
    os.utime(tmp_path / ".codex" / "loop-runs" / "parent-a" / "run.json", (older, older))
    os.utime(tmp_path / ".codex" / "loop-runs" / "parent-b" / "run.json", (newer, newer))
    write_json(
        tmp_path / ".codex" / "loop-runs" / "shared-child" / "run.json",
        {
            "run_id": "shared-child",
            "run_kind": "child",
            "child_index": 1,
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "shared-child-task",
            "domain": "",
            "branch": "main",
            "worktree": str(tmp_path),
            "requirement": "Shared child without parent_run_id",
            "constraints": [],
            "stop_conditions": ["passed"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_child_generator",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        },
    )

    detail_a = LoopDashboardStore(tmp_path).get_run("parent-a")
    detail_b = LoopDashboardStore(tmp_path).get_run("parent-b")

    assert [child["run_id"] for child in detail_a["children"]] == []
    assert [child["run_id"] for child in detail_b["children"]] == ["shared-child"]
    assert any(item["kind"] == "child_multi_parent_conflict" for item in detail_a["relationship_diagnostics"])


def test_single_run_without_run_kind_remains_top_level(tmp_path: Path) -> None:
    seed_run(tmp_path, "single-run", "passed_waiting_human_merge", last_result="pass", next_action="await_human_merge_confirmation")

    runs = LoopDashboardStore(tmp_path).list_runs()
    detail = LoopDashboardStore(tmp_path).get_run("single-run")

    assert runs[0]["run_kind"] == "single"
    assert "children" not in detail or detail["children"] == []


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


def test_duplicate_run_id_ignores_unsafe_symlink_mtime_when_selecting_source(tmp_path: Path) -> None:
    seed_run(
        tmp_path,
        "duplicate-symlink-run",
        "passed_waiting_human_merge",
        last_result="pass",
        next_action="await_human_merge_confirmation",
    )
    worktree_root = tmp_path / ".worktrees" / "older-source"
    seed_run(
        worktree_root,
        "duplicate-symlink-run",
        "repair_needed",
        last_result="fail",
        next_action="run_generator_repair",
    )
    outside_dir = tmp_path.parent / f"{tmp_path.name}-newer-outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "newer.log"
    outside_file.write_text("outside newer mtime should not select source\n", encoding="utf-8")
    current_run = tmp_path / ".codex" / "loop-runs" / "duplicate-symlink-run" / "run.json"
    worktree_run_dir = worktree_root / ".codex" / "loop-runs" / "duplicate-symlink-run"
    worktree_run = worktree_run_dir / "run.json"
    os.utime(current_run, (1_800_000_000, 1_800_000_000))
    os.utime(worktree_run, (1_700_000_000, 1_700_000_000))
    os.utime(outside_file, (1_900_000_000, 1_900_000_000))
    (worktree_run_dir / "outside-newer.log").symlink_to(outside_file)
    try:
        store = LoopDashboardStore(tmp_path)
        runs = store.list_runs()
        detail = store.get_run("duplicate-symlink-run")
    finally:
        (worktree_run_dir / "outside-newer.log").unlink(missing_ok=True)
        outside_file.unlink(missing_ok=True)
        outside_dir.rmdir()

    assert runs[0]["source_kind"] == "current"
    assert detail["source_kind"] == "current"
    assert detail["phase"] == "passed_waiting_human_merge"


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


def test_invalid_run_json_detail_is_available_from_listed_run(tmp_path: Path) -> None:
    broken = tmp_path / ".codex" / "loop-runs" / "broken-run"
    broken.mkdir(parents=True)
    (broken / "run.json").write_text("{bad json", encoding="utf-8")

    store = LoopDashboardStore(tmp_path)
    runs = store.list_runs()
    detail = store.get_run("broken-run")

    assert any(run["run_id"] == "broken-run" and run["phase"] == "invalid_artifact" for run in runs)
    assert detail is not None
    assert detail["run_id"] == "broken-run"
    assert detail["phase"] == "invalid_artifact"
    assert detail["blocked_diagnostics"][0]["kind"] == "invalid_artifact"
    assert detail["decision_summary"]["requires_user_decision"] is True
    assert detail["decision_summary"]["decision_label"] == "需要检查无效产物"
    assert detail["decision_summary"]["next_action"] == "inspect_invalid_artifact"


def test_empty_run_directory_detail_is_available_from_listed_run(tmp_path: Path) -> None:
    (tmp_path / ".codex" / "loop-runs" / "empty-run").mkdir(parents=True)

    store = LoopDashboardStore(tmp_path)
    runs = store.list_runs()
    detail = store.get_run("empty-run")

    assert any(run["run_id"] == "empty-run" and run["phase"] == "invalid_artifact" for run in runs)
    assert detail is not None
    assert detail["run_id"] == "empty-run"
    assert detail["phase"] == "invalid_artifact"
    assert detail["blocked_diagnostics"][0]["kind"] == "invalid_artifact"
    assert detail["decision_summary"]["requires_user_decision"] is True
    assert detail["decision_summary"]["decision_label"] == "需要检查无效产物"
    assert detail["decision_summary"]["next_action"] == "inspect_invalid_artifact"


def test_weird_run_kind_falls_back_to_single_without_crashing(tmp_path: Path) -> None:
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
            "requirement": "Weird run kind should not crash",
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

    store = LoopDashboardStore(tmp_path)
    runs = store.list_runs()
    detail = store.get_run("weird-run")

    listed = next(run for run in runs if run["run_id"] == "weird-run")
    assert listed["run_kind"] == "single"
    assert detail["run_kind"] == "single"
