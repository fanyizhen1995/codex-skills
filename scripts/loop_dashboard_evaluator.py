#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCENARIO_ID = "LOOP-DASHBOARD-CLICK-SMOKE"
CHECKED = [
    "打开 Loop Dashboard 并确认标题、项目路径和运行目录可见",
    "选择运行记录并查看完整任务摘要",
    "确认页面为左侧选运行、右侧看结论的两栏结构",
    "通过 API 验证父需求、子任务顺序、旧单任务兼容和冲突诊断",
    "通过 API 验证 unsafe run_id 返回 404 且不绕过 store safe-id",
    "通过 tabs 查看概览、子任务、Agent 结果、验收、日志、阻塞诊断和产物",
    "查看流程图中的当前阶段、跳过节点和人工合并节点",
    "查看父需求概览 tab 中的多子任务进度和每个子任务状态",
    "查看父需求子任务 tab 中的完整 child 描述、agent 动作、验收结果和 artifact 路径",
    "查看 Planner、Generator、Evaluator 的状态说明",
    "查看父需求 Agent 结果 tab 中按子任务聚合的 Planner、Generator、Evaluator 说明",
    "确认 evaluator 验证功能实现完整性和设计/mock 匹配，并在验收 tab 中可见",
    "查看验收 tab 中的模拟用户验收场景",
    "查看阻塞诊断 tab 中的 evaluator finding",
    "查看父需求子任务队列、冲突父需求诊断和移动端父子布局",
    "在日志 tab 中按 Agent、日志类型和关键词过滤原始日志",
    "确认父子任务事件和日志中的敏感 token 已脱敏",
    "切换查看已完成、无需操作、预算耗尽和阻塞运行",
    "查看项目 worktree 中的已完成历史运行，并确认详情展示来源路径",
    "在 390px 移动端宽度确认页面没有横向溢出",
]


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    port = args.port if args.port is not None else find_free_port()
    dashboard_url = f"http://127.0.0.1:{port}"
    server: subprocess.Popen[str] | None = None
    fixture_root: Path | None = None

    try:
        with tempfile.TemporaryDirectory(prefix="loop-dashboard-fixture-") as tmp:
            fixture_root = Path(tmp)
            seed_fixture_project(fixture_root)
            server = start_dashboard(repo_root, fixture_root, port)
            wait_for_dashboard(dashboard_url, fixture_root, server=server)
            demand_multi_task_api = verify_demand_multi_task_api(dashboard_url)
            browser_evidence = run_browser_checks(dashboard_url, output_dir)
            terminate_process(server)
            server_output = collect_server_output(server)
            server = None
            write_json(
                output_dir / "result.json",
                {
                    "status": "pass",
                    "scenario_id": SCENARIO_ID,
                    "summary": "浏览器模拟用户完成 Loop 看板核心验收场景。",
                    "scenario_results": [
                        {
                            "scenario_id": SCENARIO_ID,
                            "status": "pass",
                            "summary": "模拟用户查看任务、流程、agent、验收摘要、诊断、日志过滤、完成运行和移动端布局。",
                            "evidence": CHECKED,
                        }
                    ],
                    "checked": CHECKED,
                    "rerun_commands": [
                        "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"
                    ],
                    "dashboard_url": dashboard_url,
                    "project_root": str(fixture_root.resolve()),
                    "demand_multi_task_api": demand_multi_task_api,
                    "browser_evidence": browser_evidence,
                    "server_stdout": server_output["stdout"],
                    "server_stderr": server_output["stderr"],
                },
            )
        return 0
    except Exception as exc:
        if server is not None:
            terminate_process(server)
        server_output = collect_server_output(server)
        write_json(
            output_dir / "result.json",
            failure_payload(exc, dashboard_url, fixture_root, server_output),
        )
        print(f"loop dashboard evaluator failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            terminate_process(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Loop Dashboard browser-click evaluator.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=None)
    return parser.parse_args()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def seed_fixture_project(project_root: Path) -> None:
    runs = [
        (
            "active-repair-run",
            "repair_needed",
            "fail",
            "run_generator_repair",
            "Evaluator 发现日志过滤缺陷，需要 Generator 修复。",
        ),
        (
            "passed-run",
            "passed_waiting_human_merge",
            "pass",
            "await_human_merge_confirmation",
            "Evaluator 通过，等待人工合并确认。",
        ),
        ("no-action-run", "stopped_no_action", "none", "none", "Planner 未发现下一步动作。"),
        ("budget-run", "stopped_budget", "budget_exhausted", "none", "循环达到预算上限。"),
        ("blocked-run", "stopped_blocked", "blocked", "none", "阻塞诊断需要人工处理。"),
    ]
    for index, (run_id, phase, last_result, next_action, summary) in enumerate(runs):
        seed_run(project_root, run_id, phase, last_result, next_action, summary, index)
    seed_run(
        project_root / ".worktrees" / "loop-dashboard",
        "loop-dashboard-dev",
        "passed_waiting_human_merge",
        "pass",
        "await_human_merge_confirmation",
        "历史 worktree 里的 Loop Dashboard 开发任务已经完成。",
        len(runs),
    )
    seed_rich_evaluator_result(project_root)
    seed_demand_multi_task_dashboard_fixture(project_root)


def seed_run(
    project_root: Path,
    run_id: str,
    phase: str,
    last_result: str,
    next_action: str,
    summary: str,
    index: int,
) -> None:
    run_dir = project_root / ".codex" / "loop-runs" / run_id
    requirement = (
        "实现独立本地 Loop Dashboard，用于中文可视化监控当前项目 Planner Generator Evaluator loop、"
        "agent、skill、日志、完成态和阻塞诊断；本次还需要验证开发流程并修复流程 bug。"
    )
    write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "policy": "demand_development",
            "phase": phase,
            "task_id": "loop-dashboard-dev-01",
            "domain": "",
            "branch": "feat/loop-dashboard",
            "worktree": str(project_root),
            "requirement": requirement,
            "constraints": ["只读后端", "中文 UI", "浏览器点击验证"],
            "stop_conditions": ["passed_waiting_human_merge", "stopped_no_action", "stopped_budget", "stopped_blocked"],
            "baseline_dirty_paths": [],
            "allowed_paths": ["apps/loop_dashboard", "scripts/loop_dashboard_evaluator.py"],
            "denylist_paths": [".env", ".codex/secrets"],
            "attempts": {
                "planner": 1 + index,
                "generator": 1 + index,
                "evaluator": 1 + index,
                "artifact_hygiene": 1 if phase.startswith("passed") else 0,
                "cleanup": 1 if phase.startswith("passed") else 0,
            },
            "limits": {"max_eval_attempts": 3, "max_tasks": 5},
            "last_result": last_result,
            "next_action": next_action,
            "attempt_history": [
                {"agent": "planner", "attempt": 1, "status": "pass"},
                {"agent": "generator", "attempt": 1, "status": "implemented"},
                {"agent": "evaluator", "attempt": 1, "status": "fail" if phase == "repair_needed" else "pass"},
            ],
            "cleanup": {
                "worktrees_removed": [],
                "processes_stopped": ["uvicorn-fixture"] if phase.startswith("passed") else [],
                "retained_artifacts": [".codex/loop-runs"],
            },
        },
    )
    write_json(
        run_dir / "planner-output.json",
        {
            "task_id": "loop-dashboard-dev-01",
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": "Loop 看板",
            "goal": requirement,
            "non_goals": ["不提供写操作"],
            "allowed_paths": ["apps/loop_dashboard", "scripts/loop_dashboard_evaluator.py"],
            "denylist_paths": [".env", ".codex/secrets"],
            "verify_commands": [
                "PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests",
                "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01",
            ],
            "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json",
            "stop_conditions": ["passed_waiting_human_merge"],
            "next_planning_hint": "保持只读监控，不引入登录态。",
        },
    )
    write_json(
        run_dir / "generator-result.json",
        {
            "task_id": "loop-dashboard-dev-01",
            "status": "implemented",
            "changed_paths": [
                "apps/loop_dashboard/backend/loop_dashboard/store.py",
                "apps/loop_dashboard/frontend/app.js",
                "scripts/loop_dashboard_evaluator.py",
            ],
            "commit": "",
            "verify_commands": ["python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v"],
            "verify_results": [{"command": "focused evaluator scenario test", "status": "pass"}],
            "artifacts": ["apps/loop_dashboard/frontend/index.html"],
            "cleanup_required": False,
            "notes": "完成只读 Loop Dashboard 和浏览器点击评估。",
        },
    )
    evaluator_status = "fail" if phase in {"repair_needed", "stopped_blocked"} else "pass"
    findings = []
    if phase == "repair_needed":
        findings = [
            {
                "id": "LD-001",
                "severity": "major",
                "category": "frontend_click",
                "evidence": ["logs filter did not update", "stderr filter was empty"],
                "recommended_action": "修复日志过滤",
            }
        ]
    elif phase == "stopped_blocked":
        findings = [
            {
                "id": "LD-BLOCKED",
                "severity": "major",
                "category": "blocked_state",
                "evidence": ["manual decision required"],
                "recommended_action": "人工解除阻塞后重试",
            }
        ]
    write_json(
        run_dir / "evaluator-result.json",
        {
            "status": evaluator_status,
            "gate": "task",
            "task_id": "loop-dashboard-dev-01",
            "final_bundle_id": "bundle-active" if phase == "repair_needed" else "",
            "attempt": 1 + index,
            "summary": summary,
            "findings": findings,
            "scenario_results": [{"scenario_id": SCENARIO_ID, "status": evaluator_status}],
            "rerun_commands": ["python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"],
            "environment_checks": [{"name": "chromium", "status": "available"}],
            "verdict_reason": summary,
            "next_action": "repair_and_reevaluate" if phase == "repair_needed" else "proceed_to_user_acceptance",
            "stdout": "Authorization: Bearer inline-token\n",
            "stderr": "Evaluator stderr: browser assertion context\n",
        },
    )
    write_json(
        run_dir / "artifact-manifest.json",
        {
            "status": "pass",
            "artifacts": [
                {"path": "apps/loop_dashboard/frontend/index.html", "kind": "frontend"},
                {"path": "scripts/loop_dashboard_evaluator.py", "kind": "evaluator"},
            ],
        },
    )
    if phase == "stopped_blocked":
        write_json(
            run_dir / "dirty-paths-result.json",
            {"status": "blocked", "diagnostics": [{"path": "apps/loop_dashboard/frontend/app.js", "reason": "manual review required"}]},
        )
    if phase.startswith("passed"):
        write_json(
            run_dir / "cleanup-result.json",
            {"status": "pass", "processes_stopped": ["uvicorn-fixture"], "worktrees_removed": []},
        )

    (run_dir / "planner-attempt-1.stdout.log").write_text(
        "Planner: 正在拆解需求\nAuthorization: Bearer planner-secret\n",
        encoding="utf-8",
    )
    (run_dir / "generator-attempt-1.stderr.log").write_text(
        "Generator stderr: 使用 skill test-driven-development\n",
        encoding="utf-8",
    )
    (run_dir / "evaluator-attempt-1.stderr.log").write_text(
        "Evaluator stderr: token=evaluator-secret\n",
        encoding="utf-8",
    )


def seed_rich_evaluator_result(project_root: Path) -> None:
    bundle_dir = project_root / ".codex" / "evaluations" / "tasks" / "loop-dashboard-dev-01" / "bundle-active"
    write_json(
        bundle_dir / "result.json",
        {
            "status": "fail",
            "scenario_id": SCENARIO_ID,
            "summary": "浏览器点击发现日志过滤问题",
            "checked": CHECKED,
            "scenario_results": [
                {
                    "scenario_id": SCENARIO_ID,
                    "status": "fail",
                    "summary": "模拟用户过滤日志时发现 stderr 过滤未按预期更新。",
                    "evidence": ["选择日志类型 stderr", "期望只显示 stderr 日志", "实际过滤结果不正确"],
                }
            ],
            "browser_evidence": [
                "已打开 Loop 看板",
                "已点击 active-repair-run",
                "已查看阻塞诊断 LD-001",
            ],
            "rerun_commands": [
                "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"
            ],
            "findings": [
                {
                    "id": "LD-001",
                    "severity": "major",
                    "category": "frontend_click",
                    "evidence": ["filter kind stderr did not update before repair"],
                    "recommended_action": "修复日志过滤",
                }
            ],
            "stdout": "Authorization: Bearer rich-secret\n",
            "stderr": "Rich evaluator stderr log line\n",
        },
    )


def seed_demand_multi_task_dashboard_fixture(repo_root: Path) -> None:
    run_root = repo_root / ".codex" / "loop-runs"
    long_requirement = (
        "验证父需求拆分后的子任务可以在 Loop Dashboard 中以中文长文本稳定展示，"
        "包括 Planner 选择、Generator 产物说明、Evaluator 模拟用户检查和验收结果；"
        "这段说明故意较长，用于覆盖移动端换行和父子关系阅读场景。"
    )
    write_json(
        run_root / "parent-run" / "run.json",
        {
            "run_id": "parent-run",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "验证父需求读者摘要和子任务队列在 Loop Dashboard 中可读。",
            "constraints": ["父需求只聚合子任务", "日志必须脱敏"],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": ["apps/loop_dashboard", "scripts/loop_dashboard_evaluator.py"],
            "denylist_paths": [".env", ".codex/secrets"],
            "attempts": {"planner": 2, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {"max_tasks": 2},
            "last_result": "none",
            "next_action": "run_child_generator",
            "attempt_history": [{"agent": "planner", "attempt": 1, "status": "pass"}],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["parent-run-child-001", "parent-run-child-002", "missing-child"],
            "current_child_run_id": "parent-run-child-002",
            "backlog": [],
            "aggregate_acceptance": {
                "total": 2,
                "passed": 1,
                "failed": 0,
                "blocked": 0,
                "pending": 1,
                "user_decision_required": False,
            },
            "reader_summary": {
                "purpose": "验证父需求读者摘要",
                "current_progress": "第一个子任务已通过，第二个子任务正在生成。",
                "next_step": "等待 parent-run-child-002 完成后汇总验收。",
                "decision_needed": "不需要",
            },
            "accepted_changed_paths": ["generated/child-001.txt"],
        },
    )
    write_json(
        run_root / "parent-run" / "evaluator-result.json",
        {
            "status": "pass",
            "gate": "task",
            "task_id": "parent-run",
            "attempt": 1,
            "summary": "父需求聚合关系可读，但保留缺失子任务诊断用于看板检查。",
            "findings": [
                {
                    "id": "child_artifact_missing",
                    "severity": "warning",
                    "category": "relationship",
                    "evidence": ["missing-child"],
                    "recommended_action": "确认缺失子任务是否仍需执行。",
                }
            ],
        },
    )
    for index, phase in [(1, "passed"), (2, "generating")]:
        child_id = f"parent-run-child-{index:03d}"
        write_json(
            run_root / child_id / "run.json",
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
                "requirement": f"{long_requirement} 子任务 {index} 还要展示自己的状态和读者摘要。",
                "constraints": ["保持只读", "展示父子关系", "移动端不能横向溢出"],
                "stop_conditions": ["passed"],
                "baseline_dirty_paths": [],
                "allowed_paths": [f"generated/child-{index:03d}.txt"],
                "denylist_paths": [".env", ".codex/secrets"],
                "attempts": {
                    "planner": 1,
                    "generator": 1 if phase == "passed" else 0,
                    "evaluator": 1 if phase == "passed" else 0,
                    "artifact_hygiene": 0,
                    "cleanup": 0,
                },
                "limits": {"max_eval_attempts": 2},
                "last_result": "pass" if phase == "passed" else "none",
                "next_action": "return_to_parent_planner" if phase == "passed" else "run_child_generator",
                "attempt_history": [
                    {"agent": "planner", "attempt": 1, "status": "pass"},
                    {"agent": "generator", "attempt": 1, "status": "implemented" if phase == "passed" else "pending"},
                ],
                "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
                "reader_summary": {
                    "purpose": f"子任务 {index} 覆盖父需求的一部分。",
                    "planner_action": "Planner 选择了这个子任务",
                    "generator_action": "Generator 正在生成实现产物" if phase == "generating" else "Generator 已生成实现产物",
                    "evaluator_action": "Evaluator 模拟用户检查",
                    "acceptance_result": "通过" if phase == "passed" else "等待验收",
                },
            },
        )
        (
            run_root / child_id / "events.jsonl"
        ).write_text(
            json.dumps(
                {
                    "timestamp": f"2026-07-03T00:00:0{index}Z",
                    "run_id": child_id,
                    "parent_run_id": "parent-run",
                    "child_id": f"child-{index:03d}",
                    "actor": "planner",
                    "event_type": "plan",
                    "summary": f"Planner selected child {index}; Authorization: Bearer secret-token",
                    "details": {},
                    "artifact_paths": [],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        if phase == "passed":
            write_json(
                run_root / child_id / "evaluator-result.json",
                {
                    "status": "pass",
                    "gate": "task",
                    "task_id": f"{child_id}-task",
                    "attempt": 1,
                    "summary": "Evaluator 已模拟用户检查子任务功能完整性和设计匹配。",
                    "scenario_results": [
                        {
                            "scenario_id": f"{child_id}-DESIGN-001",
                            "status": "pass",
                            "summary": "模拟第三方读者打开看板，核对功能实现完整性和设计/mock 匹配。",
                            "evidence": [
                                "点击父需求运行记录",
                                "切换子任务 tab",
                                "核对 Agent 结果和验收内容",
                            ],
                        }
                    ],
                    "checked": [
                        "功能实现完整性",
                        "设计/mock 匹配",
                        "父需求和子任务信息可读",
                    ],
                    "rerun_commands": [
                        "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01"
                    ],
                },
            )
    write_json(
        run_root / "legacy-single" / "run.json",
        {
            "run_id": "legacy-single",
            "policy": "demand_development",
            "phase": "passed_waiting_human_merge",
            "task_id": "legacy-single-task",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "旧格式单任务没有 run_kind，仍应作为单任务显示。",
            "constraints": [],
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
    write_json(
        run_root / "conflict-parent" / "run.json",
        {
            "run_id": "conflict-parent",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "冲突父需求引用了另一个父需求的子任务。",
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
            "child_run_ids": ["parent-run-child-001"],
            "current_child_run_id": "parent-run-child-001",
            "aggregate_acceptance": {"total": 1, "passed": 0, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            "reader_summary": {
                "purpose": "验证冲突父需求诊断",
                "current_progress": "存在多父级引用冲突。",
                "next_step": "查看阻塞诊断。",
                "decision_needed": "需要人工确认归属",
            },
        },
    )


def start_dashboard(repo_root: Path, fixture_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "apps" / "loop_dashboard" / "backend")
    env["LOOP_DASHBOARD_PROJECT_ROOT"] = str(fixture_root)
    return subprocess.Popen(
        [
            "python3",
            "-m",
            "uvicorn",
            "loop_dashboard.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for_dashboard(
    dashboard_url: str,
    expected_project_root: Path,
    server: subprocess.Popen[str] | None = None,
    timeout_seconds: float = 20.0,
) -> None:
    health_url = f"{dashboard_url}/api/health"
    project_url = f"{dashboard_url}/api/projects/current"
    expected_root = str(expected_project_root.resolve())
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if server is not None and server.poll() is not None:
            raise RuntimeError(f"dashboard server exited before readiness check; returncode={server.returncode}")
        try:
            health_payload = read_json_url(health_url)
            if health_payload.get("status") != "ok":
                last_error = f"unexpected health payload: {health_payload!r}"
                time.sleep(0.25)
                continue
            project_payload = read_json_url(project_url)
            actual_root = project_payload.get("project_root")
            if actual_root == expected_root:
                return
            raise RuntimeError(f"dashboard project root mismatch: expected {expected_root!r}, got {actual_root!r}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"dashboard did not become ready at {dashboard_url}: {last_error}")


def read_json_url(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=1) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected JSON payload from {url}: {payload!r}")
    return payload


def verify_demand_multi_task_api(base_url: str) -> dict[str, object]:
    with urllib.request.urlopen(f"{base_url}/api/runs", timeout=5) as response:
        runs = json.loads(response.read().decode("utf-8"))
    if not isinstance(runs, list):
        raise AssertionError("/api/runs should return a JSON list")
    parent = find_run_summary(runs, "parent-run")
    expect_equal(parent.get("run_kind"), "parent", "parent-run should be listed as run_kind=parent")
    expect_children_summary(parent, "parent-run list summary")
    run_ids = [run.get("run_id") for run in runs if isinstance(run, dict)]
    for child_id in ["parent-run-child-001", "parent-run-child-002"]:
        if child_id in run_ids:
            raise AssertionError(f"owned child run should not appear as a top-level run: {child_id}")
    legacy = find_run_summary(runs, "legacy-single")
    expect_equal(legacy.get("run_kind"), "single", "legacy-single should remain visible as run_kind=single")

    detail = read_json_url(f"{base_url}/api/runs/parent-run")
    children = detail.get("children")
    if not isinstance(children, list) or not children:
        raise AssertionError("parent-run detail should include child summaries")
    child_ids = [child.get("run_id") for child in children if isinstance(child, dict)]
    expect_equal(child_ids, ["parent-run-child-001", "parent-run-child-002"], "parent-run children should be sorted by child_index")
    expect_children_summary(detail, "parent-run detail summary")
    reader_summary = detail.get("reader_summary")
    if not isinstance(reader_summary, dict) or not reader_summary.get("purpose"):
        raise AssertionError("parent-run detail should include reader_summary.purpose")
    if "relationship_diagnostics" not in detail:
        raise AssertionError("parent-run detail should include relationship_diagnostics")
    events_payload = read_json_url(f"{base_url}/api/runs/parent-run/events")
    events = events_payload.get("events")
    if not isinstance(events, list):
        raise AssertionError("parent-run events endpoint should return an events list")
    if not any(isinstance(event, dict) and event.get("kind") == "plan" for event in events):
        raise AssertionError("parent-run events should include child plan events")
    if any("secret-token" in str(event) for event in events):
        raise AssertionError("parent-run events should redact fixture secret-token")

    conflict = read_json_url(f"{base_url}/api/runs/conflict-parent")
    conflict_children = conflict.get("children")
    if not isinstance(conflict_children, list):
        raise AssertionError("conflict-parent detail should include a children list")
    if any(isinstance(child, dict) and child.get("run_id") == "parent-run-child-001" for child in conflict_children):
        raise AssertionError("conflict-parent should not silently include parent-run-child-001")
    conflict_diagnostics = diagnostics_from(conflict, "relationship_diagnostics") + diagnostics_from(conflict, "blocked_diagnostics")
    conflict_kinds = {diagnostic.get("kind") for diagnostic in conflict_diagnostics if isinstance(diagnostic, dict)}
    if not conflict_kinds.intersection({"child_parent_conflict", "child_multi_parent_conflict"}):
        raise AssertionError(f"conflict-parent should expose a child conflict diagnostic, got {sorted(conflict_kinds)}")

    route_404_cases = [
        expect_route_404(
            f"{base_url}/api/runs/..%2Foutside",
            "..%2Foutside",
        )
    ]
    store_safe_id_cases = [
        expect_store_safe_id_404(f"{base_url}/api/runs/{unsafe_path}", unsafe_path)
        for unsafe_path in ["%2E%2E", "%5C..%5Coutside", "..%5Coutside"]
    ]
    return {
        "parent_children": len(children),
        "events": len(events),
        "conflict_diagnostics": sorted(str(kind) for kind in conflict_kinds),
        "route_404_cases": route_404_cases,
        "store_safe_id_cases": store_safe_id_cases,
    }


def find_run_summary(runs: list[object], run_id: str) -> dict[str, object]:
    for run in runs:
        if isinstance(run, dict) and run.get("run_id") == run_id:
            return run
    available = sorted(str(run.get("run_id")) for run in runs if isinstance(run, dict) and run.get("run_id"))
    raise AssertionError(f"/api/runs should include {run_id}; available run ids: {available}")


def expect_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def expect_children_summary(payload: dict[str, object], context: str) -> None:
    summary = payload.get("children_summary")
    if not isinstance(summary, dict):
        raise AssertionError(f"{context} should include children_summary")
    expected = {"total": 2, "passed": 1, "pending": 1}
    for key, value in expected.items():
        if summary.get(key) != value:
            raise AssertionError(f"{context} children_summary.{key} should be {value}, got {summary.get(key)!r}")


def diagnostics_from(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    diagnostics = payload.get(key)
    if not isinstance(diagnostics, list):
        raise AssertionError(f"{key} should be a list")
    return [diagnostic for diagnostic in diagnostics if isinstance(diagnostic, dict)]


def expect_route_404(url: str, case: str) -> dict[str, object]:
    try:
        urllib.request.urlopen(url, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise AssertionError(f"route-level unsafe run lookup should return 404 for {case}: got {exc.code}") from exc
        detail = read_error_detail(exc)
        if detail != "Not Found":
            raise AssertionError(
                f"route-level unsafe run lookup should be rejected by router for {case}: detail={detail!r}"
            ) from exc
        return {"case": case, "status": exc.code, "detail": detail}
    raise AssertionError(f"route-level unsafe run lookup should return 404 for {case}")


def expect_store_safe_id_404(url: str, case: str) -> dict[str, object]:
    try:
        urllib.request.urlopen(url, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise AssertionError(f"store-level unsafe run lookup should return 404 for {case}: got {exc.code}") from exc
        detail = read_error_detail(exc)
        if not isinstance(detail, str) or not detail.startswith("run not found: "):
            raise AssertionError(
                f"store-level unsafe run lookup should reach run_id handler for {case}: detail={detail!r}"
            ) from exc
        return {"case": case, "status": exc.code, "detail": detail}
    raise AssertionError(f"store-level unsafe run lookup should return 404 for {case}")


def read_error_detail(exc: urllib.error.HTTPError) -> object:
    body = exc.read().decode("utf-8")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if isinstance(payload, dict):
        return payload.get("detail")
    return payload


def run_browser_checks(dashboard_url: str, output_dir: Path) -> dict[str, Any]:
    try:
        from playwright.sync_api import expect, sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright for Python is not installed") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.goto(dashboard_url, wait_until="networkidle")
            expect(page).to_have_title("Loop Dashboard")
            expect(page.get_by_role("heading", name="Loop Dashboard")).to_be_visible()
            expect(page.get_by_test_id("project-status")).to_contain_text("项目：")
            expect(page.get_by_test_id("project-status")).to_contain_text("运行目录：")
            workbench_columns = page.locator(".workbench").evaluate(
                "el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length"
            )
            if workbench_columns != 2:
                raise AssertionError(f"dashboard should use two primary columns, got {workbench_columns}")
            expect(page.get_by_test_id("run-list")).to_contain_text("active-repair-run")
            expect(page.get_by_test_id("run-list")).to_contain_text("loop-dashboard-dev")
            expect(page.get_by_test_id("run-list")).to_contain_text("parent-run")

            page.get_by_role("button").filter(has_text="active-repair-run").first.click()
            detail = page.get_by_test_id("run-detail")
            expect(detail).to_contain_text("实现独立本地 Loop Dashboard")
            expect(detail).to_contain_text("需要修复")
            expect(detail).to_contain_text("任务摘要")
            expect(detail).to_contain_text("当前进展")
            expect(detail).to_contain_text("下一步")
            expect(detail).to_contain_text("用户决策")
            expect(detail).to_contain_text("运行信息")
            expect(detail).to_contain_text("用户决策不需要")
            expect(detail.locator(".run-summary-card")).to_have_count(1)
            expect(detail.locator(".decision-grid")).to_have_count(1)
            expect(detail.locator(".run-info-grid")).to_have_count(1)
            expect(detail.locator(".run-info-row")).to_have_count(5)
            info_columns = detail.locator(".run-info-grid").evaluate(
                "el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length"
            )
            if info_columns != 1:
                raise AssertionError(f"run info should render one field per row, got {info_columns} columns")

            tabs = page.get_by_test_id("detail-tabs")
            for tab_name in ["概览", "子任务", "Agent结果", "验收", "日志", "阻塞诊断", "产物"]:
                expect(tabs.get_by_role("tab", name=tab_name)).to_be_visible()

            click_run(page, "parent-run")
            parent_detail = page.get_by_test_id("run-detail")
            expect(parent_detail).to_contain_text("父需求读者摘要")
            expect(parent_detail).to_contain_text("子任务队列")
            expect(parent_detail).to_contain_text("验证父需求读者摘要")
            expect(parent_detail).to_contain_text("parent-run-child-001")
            expect(parent_detail).to_contain_text("parent-run-child-002")
            expect(parent_detail).to_contain_text("Planner 选择了这个子任务")
            expect(parent_detail).to_contain_text("Evaluator 模拟用户检查")
            parent_detail_excerpt = parent_detail.inner_text()[:800]
            for internal_action in [
                "run_parent_planner",
                "run_child_generator",
                "resume_current_child",
                "repair_child",
                "return_to_parent_planner",
                "child_running",
                "1 children passed",
                "Run parent planner",
                "No",
            ]:
                if internal_action in parent_detail.inner_text():
                    raise AssertionError(f"dashboard should translate internal action id: {internal_action}")
            tabs.get_by_role("tab", name="子任务").click()
            child_tab = page.get_by_test_id("tab-children")
            expect(child_tab).to_be_visible()
            expect(child_tab).to_contain_text("子任务详情")
            expect(child_tab).to_contain_text("parent-run-child-001")
            expect(child_tab).to_contain_text("parent-run-child-002")
            expect(child_tab).to_contain_text("Generator 已生成实现产物")
            expect(child_tab).to_contain_text("Evaluator 模拟用户检查")
            expect(child_tab).to_contain_text(".codex/loop-runs/parent-run-child-001/evaluator-result.json")
            tabs.get_by_role("tab", name="概览").click()
            parent_flow = page.get_by_test_id("flow-diagram")
            expect(parent_flow).to_contain_text("父需求进展")
            expect(parent_flow).to_contain_text("1 / 2 通过")
            expect(parent_flow).to_contain_text("parent-run-child-001")
            expect(parent_flow).to_contain_text("parent-run-child-002")
            expect(parent_flow).to_contain_text("Generator 已生成实现产物")
            expect(parent_flow).to_contain_text("Generator 正在生成实现产物")
            expect(parent_flow).not_to_contain_text("Repair Needed")
            tabs.get_by_role("tab", name="Agent结果").click()
            parent_agent_cards = page.get_by_test_id("agent-cards")
            expect(parent_agent_cards).to_contain_text("父需求 Agent 结果")
            expect(parent_agent_cards).to_contain_text("parent-run-child-001")
            expect(parent_agent_cards).to_contain_text("parent-run-child-002")
            expect(parent_agent_cards).to_contain_text("Planner 选择了这个子任务")
            expect(parent_agent_cards).to_contain_text("Generator 已生成实现产物")
            expect(parent_agent_cards).to_contain_text("Generator 正在生成实现产物")
            expect(parent_agent_cards).to_contain_text("Evaluator 模拟用户检查")
            tabs.get_by_role("tab", name="验收").click()
            parent_acceptance = page.get_by_test_id("tab-acceptance")
            expect(parent_acceptance).to_contain_text("验收情况")
            expect(parent_acceptance).to_contain_text("功能实现完整性")
            expect(parent_acceptance).to_contain_text("设计/mock 匹配")
            expect(parent_acceptance).to_contain_text("模拟第三方读者打开看板")
            expect(parent_acceptance).to_contain_text("parent-run-child-001")
            tabs.get_by_role("tab", name="阻塞诊断").click()
            expect(page.get_by_test_id("blocked-diagnostics")).to_contain_text("child_artifact_missing")
            tabs.get_by_role("tab", name="日志").click()
            parent_log_list = page.get_by_test_id("log-list")
            expect(parent_log_list).to_contain_text("Planner selected child 1")
            page.get_by_test_id("log-keyword-filter").fill("secret-token")
            expect(parent_log_list).to_contain_text("没有匹配的日志")
            if "secret-token" in page.content():
                raise AssertionError("dashboard rendered an unredacted fixture token")
            page.set_viewport_size({"width": 390, "height": 844})
            expect(parent_detail).to_contain_text("父需求读者摘要")
            expect(parent_detail).to_contain_text("子任务队列")
            overflow_after_parent = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if overflow_after_parent:
                raise AssertionError("parent/child dashboard has horizontal overflow at 390px viewport width")
            page.set_viewport_size({"width": 1280, "height": 900})
            page.get_by_test_id("log-keyword-filter").fill("")
            click_run(page, "conflict-parent")
            conflict_detail = page.get_by_test_id("run-detail")
            expect(conflict_detail).to_contain_text("验证冲突父需求诊断")
            expect(conflict_detail.locator(".child-queue")).to_contain_text("暂无子任务")
            expect(conflict_detail.locator(".child-queue")).not_to_contain_text("parent-run-child-001")
            tabs.get_by_role("tab", name="阻塞诊断").click()
            expect(page.get_by_test_id("blocked-diagnostics")).to_contain_text("child parent conflict")
            click_run(page, "active-repair-run")

            overview_tab = page.get_by_test_id("tab-overview")
            expect(overview_tab).to_be_visible()
            expect(page.get_by_test_id("tab-diagnostics")).not_to_be_visible()

            flow = page.get_by_test_id("flow-diagram")
            expect(flow).to_contain_text("Evaluator")
            expect(flow).to_contain_text("阻塞")
            expect(flow).to_contain_text("Artifact Hygiene")
            expect(flow).to_contain_text("Cleanup")
            expect(flow).to_contain_text(".codex/loop-runs/active-repair-run/evaluator-result.json")
            expect(flow.locator(".flow-node-header")).to_have_count(8)
            expect(flow.locator(".flow-node-body")).to_have_count(8)
            expect(flow.locator(".flow-node-long")).to_have_count(8)

            tabs.get_by_role("tab", name="Agent结果").click()
            agent_cards = page.get_by_test_id("agent-cards")
            expect(page.get_by_test_id("tab-agents")).to_be_visible()
            expect(agent_cards).to_contain_text("Planner")
            expect(agent_cards).to_contain_text("Generator")
            expect(agent_cards).to_contain_text("Evaluator")
            expect(agent_cards.locator(".agent-card-layout")).to_have_count(3)
            expect(agent_cards.locator(".agent-main")).to_have_count(3)
            expect(agent_cards.locator(".agent-long-fields")).to_have_count(3)
            expect(agent_cards).to_contain_text("apps/loop_dashboard/frontend/app.js")

            tabs.get_by_role("tab", name="验收").click()
            acceptance = page.get_by_test_id("tab-acceptance")
            expect(acceptance).to_be_visible()
            expect(acceptance).to_contain_text("验收情况")
            expect(acceptance).to_contain_text("模拟用户过滤日志时发现 stderr 过滤未按预期更新")
            expect(acceptance).to_contain_text("选择日志类型 stderr")
            expect(acceptance).to_contain_text("修复日志过滤")

            tabs.get_by_role("tab", name="阻塞诊断").click()
            diagnostics = page.get_by_test_id("blocked-diagnostics")
            expect(page.get_by_test_id("tab-diagnostics")).to_be_visible()
            expect(diagnostics).to_contain_text("LD-001")
            expect(diagnostics).to_contain_text("修复日志过滤")

            tabs.get_by_role("tab", name="产物").click()
            artifacts = page.get_by_test_id("tab-artifacts")
            expect(artifacts).to_be_visible()
            expect(artifacts).to_contain_text(".codex/loop-runs/active-repair-run/evaluator-result.json")
            expect(artifacts).to_contain_text("apps/loop_dashboard/frontend/app.js")

            tabs.get_by_role("tab", name="日志").click()
            page.get_by_test_id("agent-filter").select_option("generator")
            log_list = page.get_by_test_id("log-list")
            expect(page.get_by_test_id("tab-logs")).to_be_visible()
            expect(log_list).to_contain_text("Generator stderr")
            expect(log_list).not_to_contain_text("Planner:")

            page.get_by_test_id("log-kind-filter").select_option("stderr")
            expect(log_list).to_contain_text("Generator stderr")

            page.get_by_test_id("agent-filter").select_option("all")
            page.get_by_test_id("log-kind-filter").select_option("all")
            page.get_by_test_id("log-keyword-filter").fill("REDACTED")
            expect(log_list).to_contain_text("Authorization: Bearer [REDACTED]")
            expect(log_list).to_contain_text("token=[REDACTED]")

            page.get_by_test_id("log-kind-filter").select_option("stderr")
            page.get_by_test_id("log-keyword-filter").fill("no-such-keyword")
            expect(log_list).to_contain_text("没有匹配的日志")

            page.get_by_test_id("log-kind-filter").select_option("all")
            page.get_by_test_id("log-keyword-filter").fill("")
            click_run_and_expect_phase(page, expect, "passed-run", "通过，等待人工合并")
            expect(detail).to_contain_text(
                "实现独立本地 Loop Dashboard，用于中文可视化监控当前项目 Planner Generator Evaluator loop、"
                "agent、skill、日志、完成态和阻塞诊断；本次还需要验证开发流程并修复流程 bug。"
            )
            expect(detail).to_contain_text("等待人工合并确认")
            expect(detail).to_contain_text("用户决策")
            tabs.get_by_role("tab", name="概览").click()
            expect(flow).to_contain_text("Repair Needed")
            expect(flow).to_contain_text("跳过")
            expect(flow).to_contain_text("本次未触发")
            click_run_and_expect_phase(page, expect, "loop-dashboard-dev", "通过，等待人工合并")
            expect(detail).to_contain_text("来源")
            expect(detail).to_contain_text(".worktrees/loop-dashboard/.codex/loop-runs/loop-dashboard-dev")
            click_run_and_expect_phase(page, expect, "no-action-run", "停止：无需操作")
            click_run_and_expect_phase(page, expect, "budget-run", "停止：预算耗尽")
            click_run_and_expect_phase(page, expect, "blocked-run", "停止：阻塞")

            page.set_viewport_size({"width": 390, "height": 900})
            page.goto(dashboard_url, wait_until="networkidle")
            expect(page.get_by_role("heading", name="Loop Dashboard")).to_be_visible()
            overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if overflow:
                raise AssertionError("dashboard has horizontal overflow at 390px viewport width")
            screenshot_path = output_dir / "success.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            return {
                "screenshot": str(screenshot_path),
                "title": page.title(),
                "detail_excerpt": detail.inner_text()[:240],
                "parent_detail_excerpt": parent_detail_excerpt,
            }
        except Exception:
            try:
                page.screenshot(path=str(output_dir / "failure.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            browser.close()


def click_run_and_expect_phase(page: Any, expect: Any, run_id: str, phase_text: str) -> None:
    click_run(page, run_id)
    detail = page.get_by_test_id("run-detail")
    expect(detail).to_contain_text(run_id)
    expect(detail).to_contain_text(phase_text)


def click_run(page: Any, run_id: str) -> None:
    page.locator(f'.run-button[data-run-id="{run_id}"]').click()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_with_timestamp = dict(payload)
    if "generated_at" not in payload_with_timestamp:
        payload_with_timestamp["generated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload_with_timestamp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def failure_payload(
    exc: Exception,
    dashboard_url: str,
    fixture_root: Path | None,
    server_output: dict[str, str] | None,
) -> dict[str, Any]:
    output = server_output or {"stdout": "", "stderr": ""}
    payload: dict[str, Any] = {
        "status": "fail",
        "scenario_id": SCENARIO_ID,
        "error": str(exc),
        "dashboard_url": dashboard_url,
        "server_stdout": output["stdout"],
        "server_stderr": output["stderr"],
    }
    if fixture_root is not None:
        payload["project_root"] = str(fixture_root.resolve())
    return payload


def collect_server_output(process: subprocess.Popen[str] | None) -> dict[str, str]:
    if process is None:
        return {"stdout": "", "stderr": ""}
    stdout = ""
    stderr = ""
    if process.poll() is None:
        return {"stdout": "", "stderr": ""}
    try:
        stdout, stderr = process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
    return {"stdout": stdout or "", "stderr": stderr or ""}


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
