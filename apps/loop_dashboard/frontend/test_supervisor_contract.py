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
    for field in ("cursor", "visitedCursors", "pageIndex", "pageSize", "query"):
        assert field in PAGINATION_JS
    assert "[20, 50, 100]" in PAGINATION_JS
    assert "URLSearchParams" in PAGINATION_JS
    assert "sessionStorage" in PAGINATION_JS
    assert "next_cursor" in PAGINATION_JS
    assert "visitedCursors.map" in PAGINATION_JS
    assert "totalPages" not in PAGINATION_JS


def test_pager_uses_compact_bounded_session_tokens_and_fixed_ordering():
    assert "MAX_VISITED_PAGES" in PAGINATION_JS
    assert "MAX_STATE_BYTES" in PAGINATION_JS
    assert "stateToken" in PAGINATION_JS
    assert "loop-pager-state:" in PAGINATION_JS
    assert 'this.param("history")' not in PAGINATION_JS
    assert 'this.param("sort")' not in PAGINATION_JS
    assert "fixedSort" in PAGINATION_JS


def test_pager_aborts_stale_requests_and_rolls_back_failed_transitions():
    for contract in ("AbortController", "requestGeneration", "rollbackState", "isAbortError", "retryLastRequest"):
        assert contract in PAGINATION_JS
    assert "if (this.loading) return" not in PAGINATION_JS
    assert "this.abortController.abort()" in PAGINATION_JS


def test_structured_errors_preserve_code_message_and_recovery_action():
    for contract in ("DashboardError", "recovery_action", "recoveryAction", "httpStatus"):
        assert contract in PAGINATION_JS
        assert contract in APP_JS
    assert PAGINATION_JS.index("structuredError(payload, response.status)") < PAGINATION_JS.index("!response.ok")
    assert APP_JS.index("payload.status && payload.error") < APP_JS.index("!response.ok")


def test_frontend_consumes_exact_page_envelopes_and_status_errors():
    for key in ("items", "next_cursor", "previous_cursor", "page_size", "total", "has_more"):
        assert key in ALL_FRONTEND
    assert "error.code || payload.status" in PAGINATION_JS
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


def test_supervisor_mock_regions_use_real_sources_and_honest_health():
    for endpoint in (
        "/api/supervisor/services/freshness",
        "/api/supervisor/decision-required",
        "/api/supervisor/actions/${encodeURIComponent(actionId)}/attempts",
    ):
        assert endpoint in SUPERVISOR_JS
    for label in ("活动运行", "待执行动作", "最近 Reviewer", "需要用户", "数据可读", "健康状态不可用"):
        assert label in SUPERVISOR_JS
    assert 'setHealth(true, "Supervisor 正常")' not in SUPERVISOR_JS


def test_run_detail_collections_and_log_content_are_lazy():
    load_selected_run = function_block("loadSelectedRun")

    assert "/events" not in load_selected_run
    assert "/logs" not in load_selected_run
    assert "loadActiveRunTab" in APP_JS
    assert "expandLogDetail" in APP_JS
    assert re.search(r"/logs/\$\{encodeURIComponent\(logId\)\}", APP_JS)
    assert "log.content" not in APP_JS


def test_run_detail_maps_exact_task7_fields_and_parent_child_agents():
    for field in (
        "task_description", "task_summary", "decision_summary", "last_result",
        "attempt", "artifact_paths", "checked", "evidence", "rerun_commands",
        "severity", "source", "label", "updated_at",
    ):
        assert field in APP_JS
    assert "renderDecisionSummary" in APP_JS
    assert "renderAgentPayload" in APP_JS
    assert "renderAcceptanceEvidence" in APP_JS
    assert "renderChildAgents" in APP_JS


def test_task_description_is_preferred_over_backend_list_summary_everywhere():
    assert "run.task_description || run.task_summary" in APP_JS
    assert "detail.task_description || detail.task_summary" in APP_JS
    assert "run.task_summary || run.task_description" not in APP_JS
    assert "detail.task_summary || detail.task_description" not in APP_JS


def test_unavailable_data_is_labeled_without_synthetic_success():
    for label in ("不可用", "暂无数据", "未启用", "任务恢复页提供完整记录"):
        assert label in SUPERVISOR_JS
    assert "schema_version" in SUPERVISOR_JS
    assert "Task 7 未提供配置读取 API" in SUPERVISOR_JS


def test_run_phases_are_chinese_and_log_titles_prefer_readable_sources():
    assert "statusText(run.phase || run.status)" not in APP_JS
    assert "phaseLabel(run.phase)" in APP_JS
    assert "item.source || item.log_id" in APP_JS


def test_agent_result_statuses_use_readable_chinese_labels():
    assert "agentStatusLabel(payload.status)" in APP_JS
    for raw, label in (
        ("done", "完成"),
        ("implemented", "已实现"),
        ("running", "运行中"),
        ("waiting", "等待"),
        ("blocked", "阻塞"),
    ):
        assert f'{raw}: "{label}"' in APP_JS


def test_domain_status_mappings_are_separate_and_exhaustive():
    for function_name in (
        "phaseLabel", "phaseTone", "agentStatusLabel", "acceptanceLabel",
        "acceptanceTone", "reviewDecisionLabel", "serviceHealthLabel",
        "serviceHealthTone", "severityLabel", "severityTone",
    ):
        assert f"function {function_name}" in ALL_FRONTEND
    for raw in ("pass", "passed", "ready", "missing", "terminal", "critical", "major", "minor"):
        assert f"{raw}:" in ALL_FRONTEND


def test_real_run_result_and_recovery_action_values_are_chinese():
    for mapping in (
        'fail: "失败"',
        'repair_from_evaluator_findings: "按 Evaluator finding 修复"',
        'repair_and_reevaluate: "修复后重新验收"',
        'return_to_parent_planner: "返回父 Planner"',
        'run_child_generator: "运行子任务 Generator"',
    ):
        assert mapping in APP_JS
    assert 'return labels[value] || "结果不可用"' in APP_JS
    assert 'if (!value) return "暂无动作"' in APP_JS
    assert 'node("span", `status-chip ${phaseTone(detail.phase)}`, `运行${phaseLabel(detail.phase)}`)' in APP_JS


def test_direct_url_sync_refresh_and_canonical_tabs_are_explicit():
    restore = function_block("restoreViewState")
    boot = function_block("boot")
    assert "canonicalizeViewUrl" in restore
    assert "syncView()" in boot
    assert "syncRunTabs()" in boot
    assert "refreshActiveView" in APP_JS
    assert "refresh-button" in INDEX_HTML
    assert "refresh()" in PAGINATION_JS
    assert "canonicalizeActiveTab" in SUPERVISOR_JS


def test_tabs_and_log_expansion_have_full_aria_contracts():
    for prefix in ("supervisor", "run"):
        assert f'id="{prefix}-tab-overview"' in INDEX_HTML
        assert f'aria-controls="{prefix}-panel-content"' in INDEX_HTML
    assert 'tabindex="0"' in INDEX_HTML
    assert 'tabindex="-1"' in INDEX_HTML
    for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
        assert key in ALL_FRONTEND
    assert "aria-labelledby" in INDEX_HTML
    assert 'setAttribute("aria-expanded"' in APP_JS
    assert 'setAttribute("aria-controls"' in APP_JS


def test_frontend_has_full_text_and_responsive_overflow_contract():
    css = (FRONTEND_ROOT / "styles.css").read_text(encoding="utf-8")

    assert "text-overflow: ellipsis" not in css
    assert "-webkit-line-clamp" not in css
    assert "overflow-wrap: anywhere" in css
    assert "overflow-x: auto" in css
    assert "@media (max-width: 560px)" in css
    for radius in re.findall(r"border-radius:\s*(\d+)px", css):
        assert int(radius) <= 6
