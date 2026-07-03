#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
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
CHECKED = ["run-list", "run-detail", "flow-diagram", "agent-cards", "logs", "completed-runs"]


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dashboard_url = f"http://127.0.0.1:{args.port}"
    server: subprocess.Popen[str] | None = None

    try:
        with tempfile.TemporaryDirectory(prefix="loop-dashboard-fixture-") as tmp:
            fixture_root = Path(tmp)
            seed_fixture_project(fixture_root)
            server = start_dashboard(repo_root, fixture_root, args.port)
            wait_for_health(dashboard_url, server)
            run_browser_checks(dashboard_url, output_dir)
            write_json(
                output_dir / "result.json",
                {
                    "status": "pass",
                    "scenario_id": SCENARIO_ID,
                    "checked": CHECKED,
                    "dashboard_url": dashboard_url,
                },
            )
        return 0
    except Exception as exc:
        write_json(
            output_dir / "result.json",
            {
                "status": "fail",
                "scenario_id": SCENARIO_ID,
                "error": str(exc),
                "dashboard_url": dashboard_url,
            },
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
    parser.add_argument("--port", type=int, default=8767)
    return parser.parse_args()


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
    seed_rich_evaluator_result(project_root)


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
    requirement = "实现独立本地 Loop Dashboard，监控 loop、agent、skill 和日志。"
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


def wait_for_health(dashboard_url: str, server: subprocess.Popen[str], timeout_seconds: float = 20.0) -> None:
    health_url = f"{dashboard_url}/api/health"
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if server.poll() is not None:
            stdout, stderr = server.communicate(timeout=1)
            raise RuntimeError(
                f"dashboard server exited before health check; returncode={server.returncode}; "
                f"stdout={stdout.strip()!r}; stderr={stderr.strip()!r}"
            )
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "ok":
                return
            last_error = f"unexpected health payload: {payload!r}"
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"dashboard did not become healthy at {health_url}: {last_error}")


def run_browser_checks(dashboard_url: str, output_dir: Path) -> None:
    try:
        from playwright.sync_api import expect, sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright for Python is not installed") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.goto(dashboard_url, wait_until="networkidle")
            expect(page).to_have_title("Loop 看板")
            expect(page.get_by_role("heading", name="Loop 看板")).to_be_visible()
            expect(page.get_by_test_id("run-list")).to_contain_text("active-repair-run")

            page.get_by_role("button").filter(has_text="active-repair-run").first.click()
            detail = page.get_by_test_id("run-detail")
            expect(detail).to_contain_text("实现独立本地 Loop Dashboard")
            expect(detail).to_contain_text("需要修复")

            agent_cards = page.get_by_test_id("agent-cards")
            expect(agent_cards).to_contain_text("Planner")
            expect(agent_cards).to_contain_text("Generator")
            expect(agent_cards).to_contain_text("Evaluator")

            flow = page.get_by_test_id("flow-diagram")
            expect(flow).to_contain_text("Evaluator")
            expect(flow).to_contain_text("阻塞")

            diagnostics = page.get_by_test_id("blocked-diagnostics")
            expect(diagnostics).to_contain_text("LD-001")

            page.get_by_test_id("log-kind-filter").select_option("stderr")
            log_list = page.get_by_test_id("log-list")
            expect(log_list).to_contain_text("Generator stderr")

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
            click_run_and_expect_phase(page, expect, "no-action-run", "停止：无需操作")
            click_run_and_expect_phase(page, expect, "budget-run", "停止：预算耗尽")
            click_run_and_expect_phase(page, expect, "blocked-run", "停止：阻塞")

            page.set_viewport_size({"width": 390, "height": 900})
            page.goto(dashboard_url, wait_until="networkidle")
            expect(page.get_by_role("heading", name="Loop 看板")).to_be_visible()
            overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if overflow:
                raise AssertionError("dashboard has horizontal overflow at 390px viewport width")
        except Exception:
            try:
                page.screenshot(path=str(output_dir / "failure.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            browser.close()


def click_run_and_expect_phase(page: Any, expect: Any, run_id: str, phase_text: str) -> None:
    page.get_by_role("button").filter(has_text=run_id).first.click()
    detail = page.get_by_test_id("run-detail")
    expect(detail).to_contain_text(run_id)
    expect(detail).to_contain_text(phase_text)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_with_timestamp = dict(payload)
    if "generated_at" not in payload_with_timestamp:
        payload_with_timestamp["generated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload_with_timestamp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
