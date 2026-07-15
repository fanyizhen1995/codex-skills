#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from urllib.parse import urlparse

from PIL import Image, ImageStat


ACTION_COUNT = 26
REVIEW_COUNT = 26
DECISION_COUNT = 26
SKILL_COUNT = 26
EVENT_COUNT = 26
LOG_COUNT = 26
RUN_ID = "dashboard-run-001"
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
                    "26 run events and 26 run logs paginated through Task 7 envelopes",
                    "only visited numeric pages were exposed and refresh restored cursor history",
                    "page 2 stayed stable after a newer SQLite action was inserted",
                    "log detail was fetched only after explicit expansion",
                    "exact seven Supervisor tabs and seven run-detail tabs were visible",
                    "removed control roles were absent from visible UI",
                    "desktop 1440x1000 and mobile 390x844 screenshots passed canvas and overflow checks",
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
            ) VALUES (?, 'cadence', 'review_complete', 'continue', ?, ?, '{}', ?, ?)
            """,
            (
                f"review-{index:03d}",
                f"Reviewer 结论 {index:03d}：当前方向有效，技术阻塞可由 Supervisor 自动恢复，不需要伪造成功状态。",
                json.dumps([f"evidence-{index:03d}", RUN_ID]),
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
        ("supervisor-worker", "unavailable", "", "", "", ""),
    ]
    for service_id, status, endpoint, process_id, heartbeat, version in services:
        connection.execute(
            """
            INSERT INTO services(
              service_id, status, endpoint, process_id, heartbeat_at, version,
              details_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '2026-07-15T12:20:00Z', '2026-07-15T12:20:00Z')
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
            ),
        )
    connection.execute(
        """
        INSERT INTO workers(worker_id, heartbeat_at, created_at, updated_at)
        VALUES ('worker-01', '2026-07-15T12:20:00Z', '2026-07-15T09:00:00Z', '2026-07-15T12:20:00Z')
        """
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
            "run_kind": "single",
            "policy": "demand_development",
            "phase": "generating",
            "task_id": "task-8-browser",
            "requirement": "实现与批准 mock 一致的统一 Loop Dashboard，并完整展示较长任务说明、Agent 结果和 Evaluator finding。",
            "next_action": "run_generator",
            "updated_at": "2026-07-15T12:30:00Z",
            "reader_summary": {
                "purpose": "验证七个页签、服务端游标分页、刷新恢复和日志详情懒加载。",
                "current_progress": "Task 6 SQLite 与 Task 7 page API 已准备完成，正在执行浏览器验收。",
                "next_step": "检查桌面和移动截图并确认没有页面级横向溢出。",
                "decision_needed": "不需要",
            },
            "agents": {
                "planner": {"status": "done", "action": "明确 mock 页面字段与 API 来源", "summary": "规划覆盖全部七个 Supervisor 和运行详情页签。"},
                "generator": {"status": "running", "action": "实现分页与响应式布局", "summary": "保留完整中文正文，不使用省略号或行数截断。"},
                "evaluator": {"status": "waiting", "action": "运行 Playwright", "summary": "将验证分页稳定性、日志懒加载、角色移除和截图像素。"},
            },
            "children": [],
            "acceptance_summary": {
                "scenarios": [
                    {
                        "scenario_id": "TASK8-BROWSER",
                        "status": "pending",
                        "summary": "模拟用户浏览所有页签并检查桌面与移动布局。",
                    }
                ]
            },
            "blocked_diagnostics": [],
        },
    )
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


def run_browser_actions(dashboard_url: str, output_dir: Path, fixture_root: Path) -> dict[str, object]:
    from playwright.sync_api import expect, sync_playwright

    desktop_path = output_dir / "loop-supervisor-unification-desktop.png"
    mobile_path = output_dir / "loop-supervisor-unification-mobile.png"
    request_paths: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        desktop = browser.new_page(viewport={"width": 1440, "height": 1000})
        desktop.on("request", lambda request: request_paths.append(urlparse(request.url).path))
        try:
            desktop.goto(dashboard_url, wait_until="networkidle")
            expect(desktop).to_have_title("Loop Dashboard")
            assert_sidebar_layout(desktop)
            verify_exact_tabs(desktop, "supervisor")
            visible = desktop.locator("body").inner_text()
            for removed_role in ("Auditor", "orchestrator", "auto-resume"):
                if removed_role in visible:
                    raise AssertionError(f"removed role is visible: {removed_role}")

            supervisor_panel = desktop.locator("#supervisor-panel-content")
            for tab_name in ("概览", "服务", "Reviewer", "决策", "Skill 治理", "配置"):
                desktop.get_by_role("tab", name=tab_name, exact=True).click()
                expect(desktop.get_by_role("tab", name=tab_name, exact=True)).to_have_attribute("aria-selected", "true")
            verify_collection_pagination(
                desktop,
                supervisor_panel,
                "Reviewer",
                "Reviewer 结论 001：当前方向有效，技术阻塞可由 Supervisor 自动恢复，不需要伪造成功状态。",
            )
            verify_collection_pagination(
                desktop,
                supervisor_panel,
                "决策",
                "决策 001：仅影响当前 run，不创建项目级停止。",
            )
            verify_collection_pagination(desktop, supervisor_panel, "Skill 治理", "dashboard-skill-001")

            desktop.get_by_role("tab", name="任务恢复", exact=True).click()
            expect(supervisor_panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
            expect(supervisor_panel.get_by_text("action-001", exact=True)).to_be_visible()
            if supervisor_panel.get_by_role("button", name="2", exact=True).count() != 0:
                raise AssertionError("unknown numeric page 2 was exposed before its cursor was visited")
            run_filter = supervisor_panel.get_by_label("运行 ID")
            run_filter.fill(RUN_ID)
            run_filter.press("Tab")
            expect(supervisor_panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
            supervisor_panel.get_by_role("button", name="下一页", exact=True).click()
            expect(supervisor_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
            expect(supervisor_panel.get_by_text("action-001", exact=True)).not_to_be_visible()
            expect(supervisor_panel.get_by_role("button", name="2", exact=True)).to_be_visible()
            page_two_before = action_ids(supervisor_panel)
            if page_two_before != [f"action-{index:03d}" for index in range(21, 27)]:
                raise AssertionError(f"unexpected stable page 2 actions: {page_two_before!r}")
            insert_newer_action(fixture_root)
            refresh_and_assert(desktop, supervisor_panel)
            page_two_after = action_ids(supervisor_panel)
            if page_two_after != page_two_before:
                raise AssertionError(f"new action moved stable page 2: before={page_two_before}, after={page_two_after}")
            if desktop.get_by_label("运行 ID").input_value() != RUN_ID:
                raise AssertionError("refresh did not restore the recovery filter")
            if desktop.get_by_role("tab", name="任务恢复", exact=True).get_attribute("aria-selected") != "true":
                raise AssertionError("refresh did not restore the Supervisor tab")
            desktop.screenshot(path=str(desktop_path), full_page=True)
            desktop_pixels = canvas_pixel_check(desktop_path)
            desktop_overflow = document_overflow(desktop)

            desktop.locator(f'[data-run-id="{RUN_ID}"]').click()
            expect(desktop.locator("#run-title")).to_have_text(RUN_ID)
            verify_exact_tabs(desktop, "run")
            run_panel = desktop.locator("#run-panel-content")
            desktop.get_by_label("类型").select_option("transition")
            expect(run_panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
            run_panel.get_by_role("button", name="下一页", exact=True).click()
            expect(run_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
            for tab_name in ("子任务", "Agent 结果", "验收", "阻塞诊断", "产物"):
                desktop.get_by_role("tab", name=tab_name, exact=True).click()
                expect(desktop.get_by_role("tab", name=tab_name, exact=True)).to_have_attribute("aria-selected", "true")

            detail_prefix = f"/api/runs/{RUN_ID}/logs/"
            details_before = sum(path.startswith(detail_prefix) for path in request_paths)
            desktop.get_by_role("tab", name="日志", exact=True).click()
            expect(run_panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
            if sum(path.startswith(detail_prefix) for path in request_paths) != details_before:
                raise AssertionError("log list fetched detail before explicit expansion")
            run_panel.get_by_role("button", name="下一页", exact=True).click()
            expect(run_panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
            if sum(path.startswith(detail_prefix) for path in request_paths) != details_before:
                raise AssertionError("log pagination fetched detail content")
            run_panel.get_by_role("button", name="上一页", exact=True).click()
            first_expand = run_panel.locator("[data-log-detail]").first
            first_expand.click()
            expect(run_panel.locator("[data-log-detail-panel]").first).to_contain_text("[REDACTED]")
            details_after = sum(path.startswith(detail_prefix) for path in request_paths)
            if details_after != details_before + 1:
                raise AssertionError(f"explicit log expansion should fetch one detail, got {details_after - details_before}")

            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            try:
                mobile.goto(dashboard_url, wait_until="networkidle")
                mobile.screenshot(path=str(mobile_path), full_page=True)
                mobile_pixels = canvas_pixel_check(mobile_path)
                mobile_overflow = document_overflow(mobile)
                internal_scroll = mobile.locator(".tabs").first.evaluate("node => node.scrollWidth > node.clientWidth")
                if not internal_scroll:
                    raise AssertionError("mobile tabs do not retain internal horizontal scrolling")
            finally:
                mobile.close()

            return {
                "dashboard_url": dashboard_url,
                "desktop_screenshot": str(desktop_path),
                "mobile_screenshot": str(mobile_path),
                "desktop_canvas": desktop_pixels,
                "mobile_canvas": mobile_pixels,
                "desktop_overflow": desktop_overflow,
                "mobile_overflow": mobile_overflow,
                "stable_page_two_action_ids": page_two_after,
                "log_detail_requests_before_expand": details_before,
                "log_detail_requests_after_expand": details_after,
                "request_count": len(request_paths),
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


def verify_collection_pagination(page, panel, tab_name: str, first_id: str) -> None:
    from playwright.sync_api import expect

    page.get_by_role("tab", name=tab_name, exact=True).click()
    expect(panel.get_by_text("第 1-20 条，共 26 条", exact=False)).to_be_visible()
    expect(panel.get_by_text(first_id, exact=True)).to_be_visible()
    if panel.get_by_role("button", name="2", exact=True).count() != 0:
        raise AssertionError(f"{tab_name} exposed unknown page 2")
    panel.get_by_role("button", name="下一页", exact=True).click()
    expect(panel.get_by_text("第 21-26 条，共 26 条", exact=False)).to_be_visible()
    expect(panel.get_by_text(first_id, exact=True)).not_to_be_visible()


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
