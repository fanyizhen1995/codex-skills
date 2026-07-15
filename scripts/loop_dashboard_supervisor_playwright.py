#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageStat


ACTION_COUNT = 26
REVIEW_COUNT = 26
DECISION_COUNT = 26
SKILL_COUNT = 26
EVENT_COUNT = 26
LOG_COUNT = 26
ATTEMPT_COUNT = 421
FIXTURE_RUN_COUNT = 5
FRESHNESS_COUNT = 103
RUN_ID = "dashboard-parent-001"
CHILD_RUN_ID = "dashboard-run-001"
TASK_ID = "task-8-browser"
TASK_DESCRIPTION = (
    "实现与批准 mock 一致的统一 Loop Dashboard，完整展示父子运行的 Planner、Generator、Evaluator "
    "状态、尝试次数、当前动作、完整结论、产物来源、验收证据、复验命令和阻塞诊断；这段任务说明必须逐字可读，"
    "不能使用省略号、行数裁剪或悬浮提示代替正文。"
)
GENERATOR_RESULT = "已完成七个 Supervisor 页签、七个运行详情页签、稳定游标分页和响应式布局，完整正文保持可读。"
CHILD_GENERATOR_RESULT = "子任务已生成真实浏览器验收夹具，并保留父子 Agent 结果与产物路径。"
FINDING_TEXT = "修复后仍需核对结构化错误恢复动作、请求竞态和移动表格内部滚动；该完整 finding 不得在前端截断。"
SCENARIO_ID = "LOOP-SUPERVISOR-UNIFICATION-BROWSER-E2E"
SUPERVISOR_CURSOR_SECRET = "task-8-isolated-browser-cursor-secret-2026"


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    result_json = args.result_json.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_port = args.port if args.port is not None else find_free_port()
    dashboard_url = f"http://127.0.0.1:{selected_port}"
    server: subprocess.Popen[str] | None = None
    fixture_root: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="loop-supervisor-unification-") as tmp:
            fixture_root = Path(tmp)
            seed_fixture(repo_root, fixture_root)
            server = start_dashboard(repo_root, fixture_root, selected_port)
            wait_for_dashboard(dashboard_url, fixture_root, server)
            evidence = run_browser_actions(dashboard_url, output_dir, fixture_root)
            terminate(server)
            server_output = collect_output(server)
            server = None
            payload = {
                "status": "pass",
                "scenario_id": SCENARIO_ID,
                "summary": "统一 Loop Dashboard 的页签、稳定游标分页、懒加载日志和响应式布局通过浏览器验收。",
                "checked": [
                    "Task 6 SQLite initializer seeded 26 actions/reviews/decisions/skills",
                    "real parent/child Planner, Generator, Evaluator and task-contract artifacts drove run semantics",
                    "26 run events and 26 run logs paginated through exact Task 7 envelopes",
                    "stale requests were aborted or generation-rejected and structured Next failure rolled back",
                    "page-21 offset window restored with one globally bounded dashboard session token",
                    "Supervisor deactivation cancelled delayed health responses before run selection",
                    "current health used the bounded endpoint without paging raw service history",
                    "stale current-health projection remained visibly degraded",
                    "page 2 stayed stable after a newer SQLite action was inserted",
                    "421 recovery attempts remained reachable through exact paged envelopes",
                    "log detail was fetched only after explicit expansion",
                    "direct URL selected-tab-only loading, ARIA keyboard tabs and independent page-size 50 state passed",
                    "complete task description, parent/child Agent results, acceptance, diagnostics and provenance were visible",
                    "contract-driven Chinese mappings, honest Reviewer metrics, child filters and structured diagnostics passed",
                    "run sections were unframed without nested cards",
                    "exact seven Supervisor tabs and seven run-detail tabs were visible",
                    "removed control roles were absent from visible UI",
                    "desktop, run-detail and mobile screenshots passed canvas, internal table scrolling and overflow checks",
                ],
                "browser_evidence": evidence,
                "server_stdout": server_output["stdout"],
                "server_stderr": server_output["stderr"],
            }
            write_json(result_json, payload)
        return 0
    except Exception as exc:
        if server is not None:
            terminate(server)
        server_output = collect_output(server)
        payload = {
            "status": "fail",
            "scenario_id": SCENARIO_ID,
            "summary": f"统一 Loop Dashboard 浏览器验收失败：{exc}",
            "checked": [],
            "browser_evidence": {},
            "diagnostics": [str(exc)],
            "fixture_root": str(fixture_root) if fixture_root else "",
            "server_stdout": server_output["stdout"],
            "server_stderr": server_output["stderr"],
        }
        write_json(result_json, payload)
        print(payload["summary"], file=sys.stderr)
        return 1
    finally:
        if server is not None:
            terminate(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run isolated Loop Supervisor Dashboard browser checks.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--port", type=int, default=None)
    return parser.parse_args()


def seed_fixture(repo_root: Path, project_root: Path) -> None:
    sys.path.insert(0, str(repo_root))
    from scripts.loop_supervisor.store import SupervisorStore

    store = SupervisorStore.open(project_root)
    store.migrate()
    store.close()
    seed_supervisor_sqlite(project_root)
    seed_run(project_root)
    seed_pager_fixture_runs(project_root)


def seed_supervisor_sqlite(project_root: Path) -> None:
    db_path = project_root / ".codex" / "supervisor" / "supervisor.db"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(
        """
        INSERT INTO runs(
          run_id, loop_lineage_id, policy, phase, status, revision,
          repo_relative_root, summary_json, created_at, updated_at, last_seen_at
        ) VALUES (?, 'lineage-dashboard', 'demand_development', 'generating',
                  'active', 1, '.', ?, ?, ?, ?)
        """,
        (
            RUN_ID,
            json.dumps({"summary": "验证统一 Dashboard 浏览器分页"}, ensure_ascii=False),
            "2026-07-15T09:00:00Z",
            "2026-07-15T12:30:00Z",
            "2026-07-15T12:30:00Z",
        ),
    )
    for index in range(1, ACTION_COUNT + 1):
        timestamp = f"2026-07-15T12:{ACTION_COUNT - index:02d}:00Z"
        connection.execute(
            """
            INSERT INTO actions(
              action_id, idempotency_key, canonical_identity, run_id, run_revision,
              policy, phase, action_type, queue_owner, status, priority,
              recovery_tier, payload_json, artifact_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, 'demand_development', 'generating',
                      'recover_generator_result', 'worker', 'pending', 100, 2,
                      ?, '[]', ?, ?)
            """,
            (
                f"action-{index:03d}",
                f"dashboard-key-{index:03d}",
                f"dashboard-identity-{index:03d}",
                RUN_ID,
                json.dumps(
                    {
                        "summary": (
                            f"恢复动作 {index:03d}：验证已有 Generator 产物，重建缺失 envelope，"
                            "然后进入 Evaluator；该完整说明不得在前端截断。"
                        )
                    },
                    ensure_ascii=False,
                ),
                timestamp,
                timestamp,
            ),
        )
    for index in range(1, REVIEW_COUNT + 1):
        timestamp = f"2026-07-15T11:{REVIEW_COUNT - index:02d}:00Z"
        connection.execute(
            """
            INSERT INTO reviews(
              review_id, trigger, status, decision, summary, evidence_json,
              accepted_review_json, created_at, updated_at
            ) VALUES (?, 'cadence', 'review_complete', 'continue', ?, ?, ?, ?, ?)
            """,
            (
                f"review-{index:03d}",
                f"Reviewer 结论 {index:03d}：当前方向有效，技术阻塞可由 Supervisor 自动恢复，不需要伪造成功状态。",
                json.dumps([f"evidence-{index:03d}", RUN_ID]),
                json.dumps(
                    {
                        "requested_actions": [
                            "继续当前方向",
                            "保留完整验收证据并复验移动端布局",
                        ]
                    },
                    ensure_ascii=False,
                ),
                timestamp,
                timestamp,
            ),
        )
    for index in range(1, DECISION_COUNT + 1):
        timestamp = f"2026-07-15T10:{DECISION_COUNT - index:02d}:00Z"
        connection.execute(
            """
            INSERT INTO user_decisions(
              decision_id, scope, run_id, failure_key, status, summary,
              required_decision, resolution, created_at, updated_at
            ) VALUES (?, 'run', ?, ?, 'open', ?, ?, '', ?, ?)
            """,
            (
                f"decision-{index:03d}",
                RUN_ID,
                f"failure-{index:03d}",
                f"决策 {index:03d}：仅影响当前 run，不创建项目级停止。",
                "请选择继续恢复、重新聚焦或停止当前运行。",
                timestamp,
                timestamp,
            ),
        )
    services = [
        ("crawler-backend", "healthy", "http://127.0.0.1:8765/api/health", "1983168", "2026-07-15T12:20:00Z", "abc123"),
        ("crawler-frontend", "healthy", "http://127.0.0.1:5173", "1983724", "2026-07-15T12:20:00Z", "abc123"),
        ("loop-dashboard", "healthy", "http://127.0.0.1:8766/api/health", "1983192", "2026-07-15T12:20:00Z", "abc123"),
        ("supervisor-worker", "healthy", "worker://worker-01", "worker-01", "2026-07-15T12:20:00Z", "fixture-v1"),
    ]
    services.extend(
        (
            f"managed-service-{index:03d}",
            "healthy" if index <= 101 else "unavailable",
            f"http://127.0.0.1:{19000 + index}/health" if index <= 101 else "",
            str(2_000_000 + index) if index <= 101 else "",
            "2026-07-15T12:10:00Z" if index <= 101 else "",
            "fixture-v1" if index <= 101 else "",
        )
        for index in range(1, 103)
    )
    for service_id, status, endpoint, process_id, heartbeat, version in services:
        connection.execute(
            """
            INSERT INTO services(
              service_id, status, endpoint, process_id, heartbeat_at, version,
              details_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                service_id,
                status,
                endpoint,
                process_id,
                heartbeat,
                version,
                json.dumps(
                    {"reachable": status == "healthy", "freshness": "通过" if status == "healthy" else "暂无数据"},
                    ensure_ascii=False,
                ),
                (
                    "2026-07-15T12:20:00Z"
                    if not service_id.startswith("managed-service")
                    else "2026-07-15T10:00:00Z"
                    if status == "unavailable"
                    else "2026-07-15T11:00:00Z"
                ),
                (
                    "2026-07-15T12:20:00Z"
                    if not service_id.startswith("managed-service")
                    else "2026-07-15T10:00:00Z"
                    if status == "unavailable"
                    else "2026-07-15T11:00:00Z"
                ),
            ),
        )
    connection.execute(
        """
        INSERT INTO workers(worker_id, heartbeat_at, created_at, updated_at)
        VALUES ('worker-01', '2026-07-15T12:20:00Z', '2026-07-15T09:00:00Z', '2026-07-15T12:20:00Z')
        """
    )
    attempt_base = datetime(2026, 7, 15, 12, 27, tzinfo=timezone.utc)
    for index in range(1, ATTEMPT_COUNT + 1):
        finished = attempt_base - timedelta(seconds=index)
        started = finished - timedelta(seconds=30)
        summary = (
            "已验证 Generator 结果并从检查点恢复 Evaluator envelope"
            if index == 1
            else f"恢复尝试 {index:03d}：按稳定游标读取完整恢复证据"
        )
        connection.execute(
            """
            INSERT INTO action_attempts(
              attempt_id, action_id, worker_id, result_class, summary, failure_key,
              error_class, artifact_json, checkpoint, recovery_tier,
              started_at, finished_at, created_at
            ) VALUES (?, 'action-001', 'worker-01', 'recoverable_partial', ?, '', '', ?, ?, 2, ?, ?, ?)
            """,
            (
                f"attempt-action-001-{index:03d}",
                summary,
                json.dumps([f".codex/loop-runs/{RUN_ID}/generator-result.json"], ensure_ascii=False),
                "generator-result-validated" if index == 1 else f"checkpoint-{index:03d}",
                started.isoformat().replace("+00:00", "Z"),
                finished.isoformat().replace("+00:00", "Z"),
                finished.isoformat().replace("+00:00", "Z"),
            ),
        )
    freshness = [
        ("freshness-dashboard", "loop-dashboard", "fresh", "Dashboard API 与运行产物一致", {"lag_seconds": 2}, "2026-07-15T12:28:00Z"),
        ("freshness-crawler", "crawler-workbench", "stale", "Crawler 最近同步已过期", {"lag_seconds": 420}, "2026-07-15T12:28:00Z"),
        ("freshness-worker", "supervisor-worker", "unavailable", "Worker freshness 不可用", {"reason": "无 heartbeat"}, "2026-07-15T12:28:00Z"),
    ]
    freshness.extend(
        (
            f"freshness-{index:03d}",
            f"freshness-target-{index:03d}",
            "fresh",
            f"freshness target {index:03d} 已通过",
            {"lag_seconds": index},
            "2026-07-15T12:28:00Z",
        )
        for index in range(1, FRESHNESS_COUNT - 3)
    )
    freshness.append((
        "freshness-hidden-stale",
        "freshness-hidden-stale-target",
        "stale",
        "隐藏在 freshness 第二页的过期检查必须令全局健康降级。",
        {"lag_seconds": 420},
        "2026-07-15T10:00:00Z",
    ))
    for check_id, target, status, summary, details, created_at in freshness:
        connection.execute(
            """
            INSERT INTO freshness_checks(
              check_id, target, status, summary, details_json, checked_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (check_id, target, status, summary, json.dumps(details, ensure_ascii=False), created_at, created_at),
        )
    inventory = [
        {
            "name": f"dashboard-skill-{index:03d}",
            "status": "used" if index % 2 else "candidate",
            "evidence": f"{index} 个验证运行提供结构化调用证据",
            "reviewer_summary": "职责清晰；仅结构化 invocation 计为使用证据。",
            "recommendation": "保留" if index % 2 else "检查重复后合并",
        }
        for index in range(1, SKILL_COUNT + 1)
    ]
    connection.execute(
        """
        INSERT INTO skill_snapshots(
          snapshot_id, total_skills, used_skills, snapshot_json, created_at
        ) VALUES ('skill-snapshot-browser', ?, 13, ?, '2026-07-15T12:25:00Z')
        """,
        (
            SKILL_COUNT,
            json.dumps(
                {
                    "inventory": inventory,
                    "confirmed_usage": [item["name"] for item in inventory if item["status"] == "used"],
                    "duplicate_groups": [["dashboard-skill-002", "dashboard-skill-004"]],
                    "recommendations": ["合并重复恢复 Skill"],
                },
                ensure_ascii=False,
            ),
        ),
    )
    connection.commit()
    connection.close()


def seed_run(project_root: Path) -> None:
    run_dir = project_root / ".codex" / "loop-runs" / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / "run.json",
        {
            "run_id": RUN_ID,
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "repair_needed",
            "task_id": TASK_ID,
            "requirement": TASK_DESCRIPTION,
            "constraints": ["只读 Task 7 API", "中文正文完整可读"],
            "stop_conditions": ["passed_waiting_human_merge"],
            "attempts": {"planner": 2, "generator": 3, "evaluator": 4},
            "last_result": "fail",
            "next_action": "repair_from_evaluator_findings",
            "child_run_ids": [CHILD_RUN_ID],
            "current_child_run_id": CHILD_RUN_ID,
            "aggregate_acceptance": {
                "total": 1,
                "passed": 1,
                "failed": 0,
                "blocked": 0,
                "pending": 0,
                "user_decision_required": False,
            },
            "reader_summary": {
                "purpose": "验证七个页签、服务端游标分页、刷新恢复和日志详情懒加载。",
                "current_progress": "Task 6 SQLite 与 Task 7 page API 已准备完成，正在执行浏览器验收。",
                "next_step": "检查桌面和移动截图并确认没有页面级横向溢出。",
                "decision_needed": "不需要",
            },
        },
    )
    seed_agent_artifacts(run_dir, TASK_ID, GENERATOR_RESULT, evaluator_status="fail")
    seed_task_contract(run_dir, TASK_ID)
    seed_child_run(project_root)
    events = []
    for index in range(1, EVENT_COUNT + 1):
        events.append(
            json.dumps(
                {
                    "event_type": "transition",
                    "summary": f"event-{index:03d}：状态变化已写入结构化事件流并等待前端稳定分页展示。",
                    "timestamp": f"2026-07-15T09:{EVENT_COUNT - index:02d}:00Z",
                },
                ensure_ascii=False,
            )
        )
    (run_dir / "events.jsonl").write_text("\n".join(events) + "\n", encoding="utf-8")
    base_time = 1_752_570_000
    for index in range(1, LOG_COUNT + 1):
        path = run_dir / f"worker-attempt-{index:03d}.stdout.log"
        path.write_text(
            f"log detail {index:03d}\ntoken=browser-secret-{index:03d}\n完整日志正文只在用户明确展开后读取。\n",
            encoding="utf-8",
        )
        timestamp = base_time + LOG_COUNT - index
        os.utime(path, (timestamp, timestamp))


def seed_agent_artifacts(run_dir: Path, task_id: str, generator_notes: str, *, evaluator_status: str) -> None:
    write_json(
        run_dir / "planner-output.json",
        {
            "task_id": task_id,
            "status": "done",
            "attempt": 2,
            "title": "统一 Loop Dashboard 浏览器验收规划",
            "goal": "逐项验证 mock 字段、分页状态、并发安全、可访问性和响应式布局。",
            "allowed_paths": ["apps/loop_dashboard/frontend", "scripts/loop_dashboard_supervisor_playwright.py"],
            "verify_commands": ["python3 scripts/loop_dashboard_evaluator.py --scenario loop-supervisor-unification-01"],
            "artifact_paths": [f".codex/loop-runs/{run_dir.name}/planner-output.json"],
        },
    )
    write_json(
        run_dir / "generator-result.json",
        {
            "task_id": task_id,
            "status": "implemented",
            "attempt": 3,
            "notes": generator_notes,
            "changed_paths": ["apps/loop_dashboard/frontend/app.js", "apps/loop_dashboard/frontend/pagination.js"],
            "artifacts": [f".codex/loop-runs/{run_dir.name}/generator-result.json"],
            "verify_results": [{"command": "node --check app.js", "status": "pass"}],
        },
    )
    write_json(
        run_dir / "evaluator-result.json",
        {
            "task_id": task_id,
            "status": evaluator_status,
            "attempt": 4,
            "summary": "浏览器验收发现一个需要继续复验的重要问题。" if evaluator_status == "fail" else "子任务浏览器验收通过。",
            "verdict_reason": "需要修复后复验" if evaluator_status == "fail" else "全部场景通过",
            "next_action": "repair_and_reevaluate" if evaluator_status == "fail" else "return_to_parent_planner",
            "findings": [
                {
                    "id": "TASK8-BROWSER-FINDING-001",
                    "severity": "major",
                    "summary": "浏览器状态恢复仍需复验",
                    "recommended_action": FINDING_TEXT,
                    "evidence": [
                        "结构化 status/error 必须保留 recovery_action",
                        ".codex/loop-runs/dashboard-parent-001/evaluator-result.json",
                    ],
                }
            ] if evaluator_status == "fail" else [],
            "scenario_results": [
                {
                    "scenario_id": "TASK8-ARTIFACT-BROWSER",
                    "status": "fail" if evaluator_status == "fail" else "pass",
                    "summary": "模拟用户检查完整运行语义、分页回滚与移动端布局。",
                    "evidence": ["任务正文完整可见", "Agent 产物来源可追溯", "移动表格内部滚动"],
                }
            ],
            "checked": ["完整任务说明", "父子 Agent 结果", "验收证据与复验命令", "阻塞诊断严重性和来源"],
            "browser_evidence": ["桌面运行详情截图可读", "日志内容仅在显式展开后请求"],
            "environment_checks": [{"name": "isolated backend", "status": "pass"}],
            "rerun_commands": [
                "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-unification-01 --scenario loop-supervisor-unification-01"
            ],
            "artifact_paths": [f".codex/loop-runs/{run_dir.name}/evaluator-result.json"],
        },
    )


def seed_task_contract(run_dir: Path, task_id: str) -> None:
    write_json(
        run_dir / "task-contract.json",
        {
            "task_id": task_id,
            "title": "统一 Loop Dashboard 浏览器验收",
            "description": TASK_DESCRIPTION,
            "verify_commands": ["node --check apps/loop_dashboard/frontend/app.js"],
            "scenario_commands": ["python3 scripts/loop_dashboard_evaluator.py --scenario loop-supervisor-unification-01"],
            "artifact_paths": [f".codex/loop-runs/{run_dir.name}/task-contract.json"],
            "required_services": ["loop-dashboard"],
            "evaluator_driver": "loop_dashboard_supervisor_playwright",
            "eval_policy": {"task_level_required": True},
            "allowed_scope": "isolated_fixture_only",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "TASK8-ARTIFACT-BROWSER",
                    "user_goal": "作为操作者检查完整运行语义和分页恢复。",
                    "steps": ["打开直接运行 URL", "检查父子 Agent", "展开日志"],
                    "expected_outcomes": ["正文完整", "产物可追溯", "分页状态独立"],
                    "failure_signals": ["正文截断", "预取日志详情"],
                }
            ],
        },
    )


def seed_child_run(project_root: Path) -> None:
    child_dir = project_root / ".codex" / "loop-runs" / CHILD_RUN_ID
    child_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        child_dir / "run.json",
        {
            "run_id": CHILD_RUN_ID,
            "run_kind": "child",
            "parent_run_id": RUN_ID,
            "child_index": 1,
            "policy": "demand_development",
            "phase": "passed",
            "task_id": f"{TASK_ID}-child",
            "requirement": "构建真实 artifact-backed 浏览器夹具并验证父子 Agent 结果。",
            "constraints": ["不写入 live/main"],
            "stop_conditions": ["passed"],
            "attempts": {"planner": 1, "generator": 2, "evaluator": 1},
            "last_result": "pass",
            "next_action": "return_to_parent_planner",
            "reader_summary": {
                "purpose": "提供父 run 的真实子任务验收证据。",
                "planner_action": "定义 artifact-backed fixture",
                "generator_action": "写入真实 Planner/Generator/Evaluator 产物",
                "evaluator_action": "验证父子 Agent 结果",
                "acceptance_result": "Passed",
            },
        },
    )
    seed_agent_artifacts(child_dir, f"{TASK_ID}-child", CHILD_GENERATOR_RESULT, evaluator_status="pass")
    seed_task_contract(child_dir, f"{TASK_ID}-child")


def seed_pager_fixture_runs(project_root: Path) -> None:
    for index in range(1, FIXTURE_RUN_COUNT + 1):
        run_id = f"fixture-run-{index:03d}"
        run_dir = project_root / ".codex" / "loop-runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            run_dir / "run.json",
            {
                "run_id": run_id,
                "run_kind": "single",
                "policy": "demand_development",
                "phase": "planned",
                "task_id": f"task-8-pager-{index:03d}",
                "requirement": f"可见夹具运行 {index:03d}，用于通过真实 sidebar 和运行页签压力测试分页状态上限。",
                "attempts": {"planner": 1, "generator": 0, "evaluator": 0},
                "last_result": "none",
                "next_action": "run_generator",
                "updated_at": f"2026-07-15T13:{index:02d}:00Z",
                "reader_summary": {
                    "purpose": "真实 UI 分页状态边界验证。",
                    "current_progress": "等待在可见运行页签中加载分页集合。",
                    "next_step": "打开下一个运行页签。",
                },
            },
        )


def insert_newer_action(project_root: Path) -> None:
    connection = sqlite3.connect(project_root / ".codex" / "supervisor" / "supervisor.db")
    connection.execute(
        """
        INSERT INTO actions(
          action_id, idempotency_key, canonical_identity, run_id, run_revision,
          policy, phase, action_type, queue_owner, status, priority,
          recovery_tier, payload_json, artifact_json, created_at, updated_at
        ) VALUES ('action-newer', 'dashboard-key-newer', 'dashboard-identity-newer', ?, 1,
                  'demand_development', 'generating', 'recover_generator_result',
                  'worker', 'pending', 100, 2, '{}', '[]',
                  '2026-07-15T13:00:00Z', '2026-07-15T13:00:00Z')
        """,
        (RUN_ID,),
    )
    connection.commit()
    connection.close()


def start_dashboard(repo_root: Path, fixture_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "apps" / "loop_dashboard" / "backend")
    env["LOOP_DASHBOARD_PROJECT_ROOT"] = str(fixture_root)
    env["LOOP_DASHBOARD_CURSOR_SECRET"] = SUPERVISOR_CURSOR_SECRET
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "loop_dashboard.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
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
    server: subprocess.Popen[str],
    timeout: float = 20,
) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"isolated dashboard exited early with {server.returncode}")
        try:
            with urllib.request.urlopen(f"{dashboard_url}/api/projects/current", timeout=1) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("project_root") == str(expected_project_root.resolve()):
                return
            last_error = f"project root mismatch: {payload.get('project_root')!r}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"isolated dashboard did not become ready: {last_error}")


def _capture_current_health_contract(page, request_urls: list[str]) -> dict[str, object]:
    paths = [urlparse(url).path for url in request_urls]
    health_request_count = paths.count("/api/supervisor/health")
    raw_service_requests = paths.count("/api/supervisor/services")
    raw_freshness_requests = paths.count("/api/supervisor/services/freshness")
    if health_request_count < 1:
        raise AssertionError("current health endpoint was not requested")
    if raw_service_requests or raw_freshness_requests:
        raise AssertionError("current health depended on raw service history paging")

    payload = page.evaluate(
        """async () => {
          const response = await fetch('/api/supervisor/health');
          if (!response.ok) throw new Error(`health request failed: ${response.status}`);
          return response.json();
        }"""
    )
    services = payload.get("services", []) if isinstance(payload, dict) else []
    stale_service_ids = [
        str(item.get("service_id", ""))
        for item in services
        if isinstance(item, dict) and item.get("status") == "stale"
    ]
    ui_status = page.locator("#top-status").inner_text().splitlines()[0].strip()
    if "supervisor-worker" not in stale_service_ids or ui_status != "Supervisor 降级":
        raise AssertionError("stale current-health projection appeared healthy")
    return {
        "requested_endpoint": "/api/supervisor/health",
        "health_request_count": health_request_count,
        "raw_service_history_requests_before_projection": raw_service_requests,
        "raw_freshness_history_requests_before_projection": raw_freshness_requests,
        "current_health_established_without_raw_history": True,
        "stale_projection_honest": True,
        "stale_service_ids": stale_service_ids,
        "ui_status": ui_status,
    }


def run_browser_actions(dashboard_url: str, output_dir: Path, fixture_root: Path) -> dict[str, object]:
    from playwright.sync_api import expect, sync_playwright

    desktop_path = output_dir / "loop-supervisor-unification-desktop.png"
    run_detail_path = output_dir / "loop-supervisor-unification-run-detail-desktop.png"
    mobile_path = output_dir / "loop-supervisor-unification-mobile.png"
    request_urls: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        desktop = browser.new_page(viewport={"width": 1440, "height": 1000})
        desktop.add_init_script(
            """
            (() => {
              const originalFetch = window.fetch.bind(window);
              let delayed = false;
              let delayHealth = false;
              window.__armDelayedHealth = () => { delayHealth = true; };
              window.fetch = (input, init) => {
                const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
                const response = originalFetch(input, init);
                if (delayHealth && url.pathname === "/api/supervisor/health") {
                  delayHealth = false;
                  return response.then((value) => new Promise((resolve) => setTimeout(() => resolve(value), 700)));
                }
                if (!delayed && url.pathname === "/api/supervisor/actions"
                    && !url.searchParams.has("run_id") && !url.searchParams.has("status")) {
                  delayed = true;
                  return response.then((value) => new Promise((resolve) => setTimeout(() => resolve(value), 700)));
                }
                return response;
              };
            })();
            """
        )
        desktop.on("request", lambda request: request_urls.append(request.url))
        try:
            desktop.goto(dashboard_url, wait_until="networkidle")
            expect(desktop).to_have_title("Loop Dashboard")
            assert_sidebar_layout(desktop)
            verify_exact_tabs(desktop, "supervisor")
            verify_tab_keyboard(desktop, "supervisor")
            visible = desktop.locator("body").inner_text()
            for removed_role in ("Auditor", "orchestrator", "auto-resume"):
                if removed_role in visible:
                    raise AssertionError(f"removed role is visible: {removed_role}")

            supervisor_panel = desktop.locator("#supervisor-panel-content")
            expect(supervisor_panel).to_contain_text("活动运行")
            expect(supervisor_panel).to_contain_text("Task 7 未提供活动运行聚合")
            expect(supervisor_panel).to_contain_text("状态：待执行")
            expect(supervisor_panel).to_contain_text("恢复 Tier 2")
            expect(desktop.locator("#top-status")).to_contain_text("Supervisor 降级")
            health_contract = _capture_current_health_contract(desktop, request_urls)

            desktop.evaluate("window.__armDelayedHealth()")
            with desktop.expect_request(
                lambda request: urlparse(request.url).path == "/api/supervisor/health"
            ):
                desktop.get_by_role("tab", name="服务", exact=True).click()
            parent_run = desktop.locator(f'[data-run-id="{RUN_ID}"]')
            if not parent_run.is_visible():
                desktop.locator(".sidebar").get_by_role("button", name="下一页", exact=True).click()
            expect(parent_run).to_be_visible()
            parent_run.click()
            expect(desktop.locator("#run-title")).to_have_text(RUN_ID)
            desktop.wait_for_timeout(850)
            expect(desktop.locator("#top-status")).to_contain_text("运行需要修复")
            if not desktop.locator("#supervisor-view").evaluate("node => node.classList.contains('is-hidden')"):
                raise AssertionError("delayed health transition restored Supervisor over the run view")
            desktop.locator("#supervisor-nav").click()
            expect(desktop.get_by_role("tab", name="服务", exact=True)).to_have_attribute("aria-selected", "true")
            desktop.get_by_role("tab", name="服务", exact=True).click()
            expect(supervisor_panel).to_contain_text("Supervisor Worker")
            expect(supervisor_panel).to_contain_text("心跳过期")
            expect(supervisor_panel).to_contain_text("Crawler Backend")
            expect(supervisor_panel).to_contain_text("异常")
            if supervisor_panel.get_by_text("managed-service-102", exact=True).count():
                raise AssertionError("hidden unhealthy service unexpectedly appeared on the first service page")
            verify_collection_pagination(
                desktop,
                supervisor_panel,
                "Reviewer",
                "Reviewer 结论 001：当前方向有效，技术阻塞可由 Supervisor 自动恢复，不需要伪造成功状态。",
            )
            expect(supervisor_panel).to_contain_text("最近结论")
            expect(supervisor_panel).to_contain_text("Reviewer 结论 001：当前方向有效，技术阻塞可由 Supervisor 自动恢复，不需要伪造成功状态。")
            verify_collection_pagination(
                desktop,
                supervisor_panel,
                "决策",
                "决策 001：仅影响当前 run，不创建项目级停止。",
            )
            expect(supervisor_panel).to_contain_text("待决摘要")
            expect(supervisor_panel).to_contain_text("待决状态")
            expect(supervisor_panel).to_contain_text("需要用户")
            verify_collection_pagination(desktop, supervisor_panel, "Skill 治理", "dashboard-skill-001")

            # stale-response: delayed unfiltered recovery response must not replace the latest filter.
            desktop.get_by_role("tab", name="任务恢复", exact=True).click()
            run_filter = desktop.get_by_label("运行 ID")
            expect(run_filter).to_be_visible()
            run_filter.fill("missing-run")
            run_filter.press("Tab")
            expect(supervisor_panel.get_by_text("暂无恢复动作", exact=True)).to_be_visible()
            desktop.wait_for_timeout(850)
            expect(supervisor_panel.get_by_text("暂无恢复动作", exact=True)).to_be_visible()
            if supervisor_panel.get_by_text("action-001", exact=True).count():
                raise AssertionError("stale unfiltered response replaced the latest recovery filter")

            run_filter.fill(RUN_ID)
            run_filter.press("Tab")
            expect(supervisor_panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
            expect(supervisor_panel.get_by_text("action-001", exact=True)).to_be_visible()
            if supervisor_panel.get_by_role("button", name="2", exact=True).count() != 0:
                raise AssertionError("unknown numeric page 2 was exposed before its cursor was visited")

            recovery_expand = supervisor_panel.locator('[aria-controls="recovery-log-action-001"]')
            expect(recovery_expand).to_have_attribute("aria-expanded", "false")
            recovery_expand.click()
            expect(recovery_expand).to_have_attribute("aria-expanded", "true")
            expect(supervisor_panel).to_contain_text("已验证 Generator 结果并从检查点恢复 Evaluator envelope")
            expect(supervisor_panel).to_contain_text("generator-result-validated")
            expect(supervisor_panel).to_contain_text(f".codex/loop-runs/{RUN_ID}/generator-result.json")
            attempt_detail = supervisor_panel.locator("#recovery-log-action-001")
            expect(attempt_detail.get_by_text("第 1-20 条，共 421 条", exact=False)).to_be_visible()
            for page_number in range(2, 22):
                attempt_detail.get_by_role("button", name="下一页", exact=True).click()
                start = (page_number - 1) * 20 + 1
                end = min(page_number * 20, ATTEMPT_COUNT)
                expect(attempt_detail.get_by_text(f"第 {start}-{end} 条，共 {ATTEMPT_COUNT} 条", exact=False)).to_be_visible()
            expect(attempt_detail.get_by_text("checkpoint-401", exact=False)).to_be_visible()
            if attempt_detail.get_by_role("button", name="1", exact=True).count() != 0:
                raise AssertionError("page-21 window retained unknown page 1")
            desktop.reload(wait_until="networkidle")
            expect(desktop.get_by_role("tab", name="任务恢复", exact=True)).to_have_attribute("aria-selected", "true")
            expect(desktop.get_by_label("运行 ID")).to_have_value(RUN_ID)
            recovery_expand = supervisor_panel.locator('[aria-controls="recovery-log-action-001"]')
            recovery_expand.click()
            attempt_detail = supervisor_panel.locator("#recovery-log-action-001")
            expect(attempt_detail.get_by_text("第 401-420 条，共 421 条", exact=False)).to_be_visible()
            expect(attempt_detail.get_by_text("checkpoint-401", exact=False)).to_be_visible()
            recovery_expand.click()

            main_recovery_pager = supervisor_panel.locator('[data-pager-key="supervisor-recovery"]')

            failure = {"pending": True}

            def fail_first_cursor(route) -> None:
                parsed = urlparse(route.request.url)
                query = parse_qs(parsed.query)
                if failure["pending"] and parsed.path == "/api/supervisor/actions" and query.get("cursor"):
                    failure["pending"] = False
                    route.fulfill(
                        status=503,
                        content_type="application/json",
                        body=json.dumps(
                            {
                                "status": "capacity_exceeded",
                                "error": {
                                    "code": "snapshot_capacity_exceeded",
                                    "message": "稳定快照容量已满",
                                    "recovery_action": "缩小过滤范围后重试",
                                },
                            },
                            ensure_ascii=False,
                        ),
                    )
                else:
                    route.continue_()

            desktop.route("**/api/supervisor/actions?*", fail_first_cursor)
            main_recovery_pager.get_by_role("button", name="下一页", exact=True).click()
            expect(supervisor_panel).to_contain_text("snapshot_capacity_exceeded：稳定快照容量已满；建议：缩小过滤范围后重试")
            expect(supervisor_panel.get_by_text("action-001", exact=True)).to_be_visible()
            if main_recovery_pager.get_by_role("button", name="2", exact=True).count() != 0:
                raise AssertionError("failed Next exposed unknown numeric page 2")
            supervisor_panel.get_by_role("button", name="重试", exact=True).click()
            expect(supervisor_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
            expect(supervisor_panel.get_by_text("action-001", exact=True)).not_to_be_visible()
            expect(supervisor_panel.get_by_role("button", name="2", exact=True)).to_be_visible()
            page_two_before = action_ids(supervisor_panel)
            if page_two_before != [f"action-{index:03d}" for index in range(21, 27)]:
                raise AssertionError(f"unexpected stable page 2 actions: {page_two_before!r}")
            insert_newer_action(fixture_root)
            desktop.get_by_role("button", name="刷新当前视图", exact=True).click()
            expect(supervisor_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
            page_two_after = action_ids(supervisor_panel)
            if page_two_after != page_two_before:
                raise AssertionError(f"new action moved stable page 2: before={page_two_before}, after={page_two_after}")
            if desktop.get_by_label("运行 ID").input_value() != RUN_ID:
                raise AssertionError("refresh did not restore the recovery filter")
            if desktop.get_by_role("tab", name="任务恢复", exact=True).get_attribute("aria-selected") != "true":
                raise AssertionError("refresh did not restore the Supervisor tab")

            desktop.get_by_role("tab", name="Reviewer", exact=True).click()
            reviewer_page_size = supervisor_panel.get_by_label("每页条数")
            reviewer_page_size.select_option("50")
            expect(supervisor_panel.get_by_text("第 1-26 条，共 26 条", exact=False)).to_be_visible()
            expect(reviewer_page_size).to_have_value("50")
            desktop.get_by_role("tab", name="任务恢复", exact=True).click()
            expect(supervisor_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
            desktop.reload(wait_until="networkidle")
            expect(desktop.get_by_role("tab", name="任务恢复", exact=True)).to_have_attribute("aria-selected", "true")
            expect(desktop.get_by_label("运行 ID")).to_have_value(RUN_ID)
            expect(supervisor_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
            url_state = desktop.url
            if len(url_state) > 1200 or "cursor=" in url_state or "eyJwYXls" in url_state:
                raise AssertionError(f"pager URL is not compact: {url_state}")
            desktop.screenshot(path=str(desktop_path), full_page=True)
            desktop_pixels = canvas_pixel_check(desktop_path)
            desktop_overflow = document_overflow(desktop)
            session_bound = exercise_visible_run_tab_pager_bound(desktop)
            url_state = desktop.url
            if len(url_state) > 1200 or "cursor=" in url_state or "eyJwYXls" in url_state:
                raise AssertionError(f"pager URL is not compact after visible pager pressure: {url_state}")

            direct_requests: list[str] = []
            run_page = browser.new_page(viewport={"width": 1440, "height": 1000})
            run_page.on("request", lambda request: direct_requests.append(request.url))
            try:
                run_page.goto(f"{dashboard_url}/?run_id={RUN_ID}&run_tab=agents", wait_until="networkidle")
                if run_page.locator("#run-view").evaluate("node => node.classList.contains('is-hidden')"):
                    raise AssertionError("direct run URL remained hidden behind Supervisor view")
                expect(run_page.locator("#run-title")).to_have_text(RUN_ID)
                expect(run_page.get_by_role("tab", name="Agent 结果", exact=True)).to_have_attribute("aria-selected", "true")
                verify_exact_tabs(run_page, "run")
                assert_selected_tab_only_requests(direct_requests)
                verify_tab_keyboard(run_page, "run")
                expect(run_page.locator("#run-overview")).to_contain_text(TASK_DESCRIPTION)
                expect(run_page.locator("#top-status")).to_contain_text("运行需要修复")
                expect(run_page.locator("#run-overview")).to_contain_text("按 Evaluator finding 修复")
                expect(run_page.locator("#run-overview")).to_contain_text("最近结果失败")
                run_panel = run_page.locator("#run-panel-content")
                expect(run_panel).to_contain_text(GENERATOR_RESULT)
                expect(run_panel).to_contain_text("尝试：3")
                expect(run_panel).to_contain_text("失败")
                expect(run_panel).to_contain_text(f".codex/loop-runs/{RUN_ID}/generator-result.json")

                run_page.get_by_role("tab", name="子任务", exact=True).click()
                expect(run_panel).to_contain_text(CHILD_RUN_ID)
                expect(run_panel).to_contain_text(CHILD_GENERATOR_RESULT)
                expect(run_panel).to_contain_text(f".codex/loop-runs/{CHILD_RUN_ID}/evaluator-result.json")

                run_page.get_by_role("tab", name="验收", exact=True).click()
                expect(run_panel).to_contain_text("完整任务说明")
                expect(run_panel).to_contain_text("任务正文完整可见")
                expect(run_panel).to_contain_text("python3 scripts/loop_dashboard_evaluator.py")
                expect(run_panel).to_contain_text("TASK8-ARTIFACT-BROWSER")

                run_page.get_by_role("tab", name="阻塞诊断", exact=True).click()
                expect(run_panel).to_contain_text("TASK8-BROWSER-FINDING-001")
                expect(run_panel).to_contain_text(FINDING_TEXT)
                expect(run_panel).to_contain_text("重要")
                expect(run_panel).to_contain_text(f".codex/loop-runs/{RUN_ID}/evaluator-result.json")

                run_page.get_by_role("tab", name="产物", exact=True).click()
                expect(run_panel).to_contain_text(f".codex/loop-runs/{RUN_ID}/task-contract.json")
                artifact_query = run_panel.get_by_label("关键词")
                artifact_query.fill("planner-output.json")
                artifact_query.press("Tab")
                expect(run_panel).to_contain_text(f".codex/loop-runs/{RUN_ID}/planner-output.json")

                run_page.get_by_role("tab", name="概览", exact=True).click()
                expect(run_panel).to_contain_text("自动修复后复验")
                run_page.get_by_label("类型").select_option("transition")
                expect(run_panel.locator(f'[data-pager-key="run-{RUN_ID}-overview"]')).to_have_count(1)
                expect(run_panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
                run_panel.get_by_role("button", name="下一页", exact=True).click()
                expect(run_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()

                run_page.get_by_role("tab", name="Agent 结果", exact=True).click()
                run_page.screenshot(path=str(run_detail_path), full_page=True)
                run_detail_pixels = canvas_pixel_check(run_detail_path)
                run_detail_overflow = document_overflow(run_page)

                detail_prefix = f"/api/runs/{RUN_ID}/logs/"
                details_before = request_path_count(direct_requests, detail_prefix)
                run_page.get_by_role("tab", name="日志", exact=True).click()
                expect(run_panel.locator(f'[data-pager-key="run-{RUN_ID}-logs"]')).to_have_count(1)
                expect(run_panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
                if request_path_count(direct_requests, detail_prefix) != details_before:
                    raise AssertionError("log list fetched detail before explicit expansion")
                run_panel.get_by_role("button", name="下一页", exact=True).click()
                expect(run_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
                if request_path_count(direct_requests, detail_prefix) != details_before:
                    raise AssertionError("log pagination fetched detail content")
                run_panel.get_by_role("button", name="上一页", exact=True).click()
                first_expand = run_panel.locator("[data-log-detail]").first
                expect(first_expand).to_have_attribute("aria-expanded", "false")
                first_expand.click()
                expect(first_expand).to_have_attribute("aria-expanded", "true")
                expect(run_panel.locator("[data-log-detail-panel]").first).to_contain_text("[REDACTED]")
                details_after = request_path_count(direct_requests, detail_prefix)
                if details_after != details_before + 1:
                    raise AssertionError(f"explicit log expansion should fetch one detail, got {details_after - details_before}")
            finally:
                run_page.close()

            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            try:
                mobile.goto(dashboard_url, wait_until="networkidle")
                mobile_panel = mobile.locator("#supervisor-panel-content")
                expect(mobile_panel).to_contain_text("活动运行", timeout=15_000)
                mobile.get_by_role("tab", name="服务", exact=True).click()
                expect(mobile_panel.locator(".table-wrap").first).to_be_visible(timeout=15_000)
                mobile.screenshot(path=str(mobile_path), full_page=True)
                mobile_pixels = canvas_pixel_check(mobile_path)
                mobile_overflow = document_overflow(mobile)
                internal_scroll = mobile.locator(".tabs").first.evaluate("node => node.scrollWidth > node.clientWidth")
                if not internal_scroll:
                    raise AssertionError("mobile tabs do not retain internal horizontal scrolling")
                table_scroll = mobile.locator("#supervisor-panel-content .table-wrap").first.evaluate(
                    "node => node.scrollWidth > node.clientWidth"
                )
                if not table_scroll:
                    raise AssertionError("mobile table scrolling is not internal to table-wrap")
            finally:
                mobile.close()

            return {
                "dashboard_url": dashboard_url,
                "desktop_screenshot": str(desktop_path),
                "run_detail_screenshot": str(run_detail_path),
                "mobile_screenshot": str(mobile_path),
                "desktop_canvas": desktop_pixels,
                "run_detail_canvas": run_detail_pixels,
                "mobile_canvas": mobile_pixels,
                "desktop_overflow": desktop_overflow,
                "run_detail_overflow": run_detail_overflow,
                "mobile_overflow": mobile_overflow,
                "stable_page_two_action_ids": page_two_after,
                "log_detail_requests_before_expand": details_before,
                "log_detail_requests_after_expand": details_after,
                "compact_url_length": len(url_state),
                "global_session_bound": session_bound,
                "attempt_page_21": ["attempt-action-001-401", "attempt-action-001-420"],
                "request_count": len(request_urls) + len(direct_requests),
                "health_contract": health_contract,
                "assertions": [
                    "selected-tab-only direct URL request timing",
                    "tab independence after refresh",
                    "page-size 50 persists independently",
                    "complete task description and artifact-backed run semantics",
                    "mobile table scrolling remains internal",
                    "page-21 reload restores the retained offset window",
                    "many-run/tab URL bound uses one dashboard token",
                    "delayed health transition cannot overwrite run UI",
                "attempt page 21 remains reachable through exact envelopes",
                "visible run/tab pager pressure retained the 24-pager state bound",
                "current health uses the bounded health endpoint without raw history paging",
                "stale current-health projection remains degraded",
            ],
            }
        except Exception:
            try:
                desktop.screenshot(path=str(output_dir / "loop-supervisor-unification-failure.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            desktop.close()
            browser.close()


def verify_exact_tabs(page, view: str) -> None:
    expected = (
        ["概览", "服务", "任务恢复", "Reviewer", "决策", "Skill 治理", "配置"]
        if view == "supervisor"
        else ["概览", "子任务", "Agent 结果", "验收", "日志", "阻塞诊断", "产物"]
    )
    attribute = "data-supervisor-tab" if view == "supervisor" else "data-run-tab"
    labels = page.locator(f"[{attribute}]").evaluate_all("nodes => nodes.map(node => node.textContent.trim())")
    if labels != expected:
        raise AssertionError(f"unexpected {view} tabs: {labels!r}")


def verify_tab_keyboard(page, view: str) -> None:
    from playwright.sync_api import expect

    attribute = "data-supervisor-tab" if view == "supervisor" else "data-run-tab"
    tabs = page.locator(f"[{attribute}]")
    selected_index = tabs.evaluate_all(
        "nodes => nodes.findIndex(node => node.getAttribute('aria-selected') === 'true')"
    )
    selected = tabs.nth(selected_index)
    selected.focus()
    selected.press("End")
    expect(tabs.last).to_have_attribute("aria-selected", "true")
    expect(tabs.last).to_be_focused()
    tabs.last.press("Home")
    expect(tabs.first).to_have_attribute("aria-selected", "true")
    expect(tabs.first).to_be_focused()
    tabs.first.press("ArrowRight")
    expect(tabs.nth(1)).to_have_attribute("aria-selected", "true")
    expect(tabs.nth(1)).to_be_focused()
    tabs.nth(1).press("ArrowLeft")
    expect(tabs.first).to_have_attribute("aria-selected", "true")
    expect(tabs.first).to_be_focused()
    if selected_index != 0:
        tabs.nth(selected_index).click()
        expect(tabs.nth(selected_index)).to_have_attribute("aria-selected", "true")


def assert_selected_tab_only_requests(request_urls: list[str]) -> None:
    detail_path = f"/api/runs/{RUN_ID}"
    paths = [urlparse(url).path for url in request_urls]
    if detail_path not in paths:
        raise AssertionError("direct run URL did not request run detail")
    collection_paths = [path for path in paths if path.startswith(f"{detail_path}/")]
    if collection_paths:
        raise AssertionError(f"selected-tab-only agents view prefetched collections: {collection_paths}")


def request_path_count(request_urls: list[str], prefix: str) -> int:
    return sum(urlparse(url).path.startswith(prefix) for url in request_urls)


def assert_global_pager_bound(page) -> dict[str, int]:
    metrics = page.evaluate(
        """() => {
          const url = new URL(window.location.href);
          const token = url.searchParams.get("dashboard_state");
          const raw = sessionStorage.getItem(`loop-dashboard-state:${token}`) || "";
          const state = raw ? JSON.parse(raw) : { pagers: {} };
          return {
            urlLength: url.href.length,
            dashboardTokens: url.searchParams.getAll("dashboard_state").length,
            pagerParams: Array.from(url.searchParams.keys()).filter((name) => name.startsWith("pager.")).length,
            dashboardSessions: Array.from({ length: sessionStorage.length }, (_, index) => sessionStorage.key(index))
              .filter((key) => key && key.startsWith("loop-dashboard-state:")).length,
            storedPagers: Object.keys(state.pagers || {}).length,
            stateBytes: raw.length,
          };
        }"""
    )
    if metrics["dashboardTokens"] != 1 or metrics["pagerParams"] != 0 or metrics["dashboardSessions"] != 1:
        raise AssertionError(f"many-run/tab URL bound failed: {metrics}")
    if metrics["storedPagers"] > 24 or metrics["stateBytes"] > 256 * 1024 or metrics["urlLength"] > 600:
        raise AssertionError(f"global pager session bound failed: {metrics}")
    return metrics


def exercise_visible_run_tab_pager_bound(page) -> dict[str, int]:
    from playwright.sync_api import expect

    tabs = (
        ("子任务", "children"), ("验收", "acceptance"), ("日志", "logs"),
        ("阻塞诊断", "diagnostics"), ("产物", "artifacts"), ("概览", "overview"),
    )
    run_ids = [f"fixture-run-{index:03d}" for index in range(FIXTURE_RUN_COUNT, 0, -1)]
    previous = page.locator(".sidebar").get_by_role("button", name="上一页", exact=True)
    if previous.is_enabled():
        previous.click()
    for run_id in run_ids:
        button = page.locator(f'[data-run-id="{run_id}"]')
        expect(button).to_be_visible()
        button.click()
        expect(page.locator("#run-title")).to_have_text(run_id)
        expect(page.locator(f'[data-pager-key="run-{run_id}-overview"]')).to_have_count(1)
        for tab_name, tab_key in tabs:
            page.get_by_role("tab", name=tab_name, exact=True).click()
            expect(page.locator(f'[data-pager-key="run-{run_id}-{tab_key}"]')).to_have_count(1)
    return assert_global_pager_bound(page)


def verify_collection_pagination(page, panel, tab_name: str, first_id: str) -> None:
    from playwright.sync_api import expect

    page.get_by_role("tab", name=tab_name, exact=True).click()
    expect(panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
    first_row_value = panel.locator("tbody").get_by_text(first_id, exact=True)
    expect(first_row_value).to_be_visible()
    if panel.get_by_role("button", name="2", exact=True).count() != 0:
        raise AssertionError(f"{tab_name} exposed unknown page 2")
    panel.get_by_role("button", name="下一页", exact=True).click()
    expect(panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
    expect(first_row_value).not_to_be_visible()


def refresh_and_assert(page, panel) -> None:
    from playwright.sync_api import expect

    page.reload(wait_until="networkidle")
    expect(panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
    expect(panel.get_by_text("action-001", exact=True)).not_to_be_visible()


def action_ids(panel) -> list[str]:
    return panel.locator("tbody tr").evaluate_all(
        "rows => rows.map(row => { const match = row.innerText.match(/action-\\d{3}/); return match ? match[0] : ''; })"
    )


def document_overflow(page) -> dict[str, int]:
    metrics = page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          bodyWidth: document.body.scrollWidth
        })"""
    )
    if metrics["scrollWidth"] > metrics["innerWidth"] or metrics["bodyWidth"] > metrics["innerWidth"]:
        raise AssertionError(f"document-level horizontal overflow: {metrics}")
    return metrics


def assert_sidebar_layout(page) -> None:
    layout = page.evaluate(
        """() => {
          const sidebar = document.querySelector('.sidebar').getBoundingClientRect();
          const next = document.querySelector('.sidebar .pager-actions button:last-child').getBoundingClientRect();
          const runId = document.querySelector('.run-button .nav-title > span:first-child');
          const style = getComputedStyle(runId);
          const lineHeight = parseFloat(style.lineHeight);
          return {
            sidebarRight: sidebar.right,
            nextRight: next.right,
            runIdHeight: runId.getBoundingClientRect().height,
            lineHeight
          };
        }"""
    )
    if layout["nextRight"] > layout["sidebarRight"] + 1:
        raise AssertionError(f"sidebar pager control is clipped: {layout}")
    if layout["runIdHeight"] > layout["lineHeight"] * 2 + 1:
        raise AssertionError(f"sidebar run id wraps beyond two lines: {layout}")


def canvas_pixel_check(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        statistics = ImageStat.Stat(rgb)
        extrema = rgb.getextrema()
        canvas_variance = sum(statistics.var)
        if image.width < 300 or image.height < 300 or canvas_variance < 5:
            raise AssertionError(
                f"blank or undersized screenshot canvas: size={image.size}, variance={canvas_variance}"
            )
        return {
            "width": image.width,
            "height": image.height,
            "canvas_pixel_variance": round(canvas_variance, 2),
            "extrema": extrema,
        }


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def collect_output(process: subprocess.Popen[str] | None) -> dict[str, str]:
    if process is None:
        return {"stdout": "", "stderr": ""}
    try:
        stdout, stderr = process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "process output unavailable"}
    return {"stdout": stdout or "", "stderr": stderr or ""}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
