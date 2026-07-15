from pathlib import Path
import re


FRONTEND_ROOT = Path(__file__).resolve().parent
APP_PATH = FRONTEND_ROOT / "app.js"
INDEX_PATH = FRONTEND_ROOT / "index.html"
PAGINATION_PATH = FRONTEND_ROOT / "pagination.js"
SUPERVISOR_PATH = FRONTEND_ROOT / "supervisor.js"

APP_JS = APP_PATH.read_text(encoding="utf-8")
INDEX_HTML = INDEX_PATH.read_text(encoding="utf-8")
PAGINATION_JS = PAGINATION_PATH.read_text(encoding="utf-8")
SUPERVISOR_JS = SUPERVISOR_PATH.read_text(encoding="utf-8")
ALL_FRONTEND = "\n".join((INDEX_HTML, PAGINATION_JS, SUPERVISOR_JS, APP_JS))


def function_block(name: str) -> str:
    match = re.search(
        rf"(?:async\s+)?function\s+{re.escape(name)}\([^)]*\)\s*\{{"
        rf"(?P<body>.*?)(?=\n\s*(?:async\s+)?function\s+|\n\s*boot\(\)|\Z)",
        APP_JS,
        re.S,
    )
    assert match, f"missing function {name}"
    return match.group("body")


def test_task8_scripts_are_loaded_in_binding_order():
    pagination_index = INDEX_HTML.index('/assets/pagination.js')
    supervisor_index = INDEX_HTML.index('/assets/supervisor.js')
    app_index = INDEX_HTML.index('/assets/app.js')

    assert pagination_index < supervisor_index < app_index


def test_task8_exposes_exact_supervisor_and_run_detail_tabs():
    supervisor_tabs = re.findall(
        r'role="tab"[^>]+data-supervisor-tab="[^"]+"[^>]*>([^<]+)</button>',
        INDEX_HTML,
    )
    run_tabs = re.findall(
        r'role="tab"[^>]+data-run-tab="[^"]+"[^>]*>([^<]+)</button>',
        INDEX_HTML,
    )

    assert supervisor_tabs == ["概览", "服务", "任务恢复", "Reviewer", "决策", "Skill 治理", "配置"]
    assert run_tabs == ["概览", "子任务", "Agent 结果", "验收", "日志", "阻塞诊断", "产物"]


def test_removed_roles_are_not_public_frontend_roles():
    lowered = ALL_FRONTEND.lower()

    assert 'data-tab="auditor"' not in lowered
    assert 'data-run-tab="auditor"' not in lowered
    assert "auditor" not in lowered
    assert "orchestrator" not in lowered
    assert "auto-resume" not in lowered
    assert "auto_resume" not in lowered


def test_reusable_pager_owns_cursor_history_and_only_renders_visited_pages():
    for field in ("cursor", "visitedCursors", "pageIndex", "pageSize", "query", "sort"):
        assert field in PAGINATION_JS
    assert "[20, 50, 100]" in PAGINATION_JS
    assert "URLSearchParams" in PAGINATION_JS
    assert "sessionStorage" in PAGINATION_JS
    assert "next_cursor" in PAGINATION_JS
    assert "visitedCursors.map" in PAGINATION_JS
    assert "totalPages" not in PAGINATION_JS


def test_frontend_consumes_exact_page_envelopes_and_status_errors():
    for key in ("items", "next_cursor", "previous_cursor", "page_size", "total", "has_more"):
        assert key in ALL_FRONTEND
    assert 'payload.status === "capacity_exceeded"' in PAGINATION_JS
    assert "HTTP ${response.status}" in PAGINATION_JS
    assert not re.search(r"\.slice\(\s*0\s*,\s*\d+", ALL_FRONTEND)


def test_supervisor_tabs_use_task7_routes_and_selected_tab_loading():
    for endpoint in (
        "/api/supervisor/services",
        "/api/supervisor/actions",
        "/api/supervisor/reviews",
        "/api/supervisor/decisions",
        "/api/supervisor/skills",
    ):
        assert endpoint in SUPERVISOR_JS
    assert "loadActiveTab" in SUPERVISOR_JS
    assert "requestSequence" in SUPERVISOR_JS
    assert "Promise.all" not in SUPERVISOR_JS


def test_run_detail_collections_and_log_content_are_lazy():
    load_selected_run = function_block("loadSelectedRun")

    assert "/events" not in load_selected_run
    assert "/logs" not in load_selected_run
    assert "loadActiveRunTab" in APP_JS
    assert "expandLogDetail" in APP_JS
    assert re.search(r"/logs/\$\{encodeURIComponent\(logId\)\}", APP_JS)
    assert "log.content" not in APP_JS


def test_unavailable_data_is_labeled_without_synthetic_success():
    for label in ("不可用", "暂无数据", "未启用", "当前状态需在任务恢复页查看"):
        assert label in SUPERVISOR_JS
    assert "schema_version" in SUPERVISOR_JS
    assert "Task 7 未提供配置读取 API" in SUPERVISOR_JS


def test_run_phases_are_chinese_and_log_titles_prefer_readable_sources():
    assert "statusText(run.phase || run.status)" not in APP_JS
    assert "phaseLabel(run.phase || run.status)" in APP_JS
    assert "item.name || item.path || item.source || item.log_id" in APP_JS


def test_agent_result_statuses_use_readable_chinese_labels():
    assert "agentStatusLabel(payload.status || payload.result)" in APP_JS
    for raw, label in (("done", "完成"), ("running", "运行中"), ("waiting", "等待"), ("blocked", "阻塞")):
        assert f'{raw}: "{label}"' in APP_JS


def test_frontend_has_full_text_and_responsive_overflow_contract():
    css = (FRONTEND_ROOT / "styles.css").read_text(encoding="utf-8")

    assert "text-overflow: ellipsis" not in css
    assert "-webkit-line-clamp" not in css
    assert "overflow-wrap: anywhere" in css
    assert "overflow-x: auto" in css
    assert "@media (max-width: 560px)" in css
    for radius in re.findall(r"border-radius:\s*(\d+)px", css):
        assert int(radius) <= 6
