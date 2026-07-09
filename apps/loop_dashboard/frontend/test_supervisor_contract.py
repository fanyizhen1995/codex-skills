from pathlib import Path
import re


FRONTEND_ROOT = Path(__file__).resolve().parent
APP_JS = (FRONTEND_ROOT / "app.js").read_text(encoding="utf-8")
INDEX_HTML = (FRONTEND_ROOT / "index.html").read_text(encoding="utf-8")
SUPERVISOR_MOCK = (
    FRONTEND_ROOT.parent.parent.parent
    / "docs/superpowers/mockups/2026-07-09-loop-supervisor-dashboard-mock.html"
).read_text(encoding="utf-8")


def function_block(name: str) -> str:
    match = re.search(rf"function {name}\([^)]*\) \{{(?P<body>.*?)(?=\n(?:async )?function |\Z)", APP_JS, re.S)
    assert match, f"missing function {name}"
    return match.group("body")


def object_block(name: str) -> str:
    match = re.search(rf"const {name} = \{{(?P<body>.*?)\n\}};", APP_JS, re.S)
    assert match, f"missing object {name}"
    return match.group("body")


def assert_mapping(body: str, key: str, label: str) -> None:
    pattern = rf"(?:^|\n)\s*{re.escape(key)}:\s*['\"]{re.escape(label)}['\"]"
    assert re.search(pattern, body), f"missing mapping {key!r} -> {label!r}"


def test_supervisor_panel_and_endpoints_are_part_of_frontend_contract():
    assert "全局 Agent：Loop Supervisor" in INDEX_HTML
    assert 'id="supervisor-content"' in INDEX_HTML

    for endpoint in [
        "/api/supervisor",
        "/api/supervisor/services",
        "/api/supervisor/decisions",
        "/api/supervisor/recovery",
        "/api/supervisor/decision-required",
        "/api/supervisor/auditor",
    ]:
        assert endpoint in APP_JS


def test_real_supervisor_and_auditor_values_have_chinese_labels():
    audit_labels = function_block("auditVerdictLabel")
    for key, label in {
        "pass": "通过",
        "must_fix": "必须整改",
        "should_fix": "建议整改",
        "observe": "观察",
        "blocked": "审计不可用",
        "stop": "停止",
        "continue": "继续",
        "refocus": "重新聚焦",
    }.items():
        assert_mapping(audit_labels, key, label)

    classification_labels = object_block("SUPERVISOR_CLASSIFICATION_LABELS")
    for key, label in {
        "continuation_candidate": "续跑候选",
        "active": "运行中",
        "blocked": "阻塞",
        "stopped": "已停止",
        "human_gate": "等待人工",
        "unsupported": "不支持",
        "needs_user_decision": "需要用户决策",
        "actionable_resume": "可恢复",
        "awaiting_human_merge": "等待人工合并",
        "terminal": "终止",
    }.items():
        assert_mapping(classification_labels, key, label)

    action_labels = object_block("SUPERVISOR_ACTION_LABELS")
    for key, label in {
        "observe": "观察",
        "resume": "恢复运行",
        "restart_service": "重启服务",
        "create_continuation": "创建续跑",
        "request_user_decision": "请求用户决策",
        "await_human_merge": "等待人工合并",
        "continue": "继续",
        "refocus": "重新聚焦",
        "stop": "停止",
    }.items():
        assert_mapping(action_labels, key, label)


def test_unavailable_supervisor_payloads_do_not_synthesize_numeric_zeroes():
    unavailable_payload = function_block("unavailableSupervisorPayload")

    assert "watch_interval_seconds: null" in unavailable_payload
    assert "open_count: null" in unavailable_payload
    assert not re.search(
        r"\b(?:watch_interval_seconds|service_count|open_count|total_count|returned_count)\s*:\s*0\b",
        unavailable_payload,
    )


def test_open_counts_and_watch_interval_do_not_fallback_to_concrete_values():
    assert "function openCountLabel" in APP_JS
    assert "function watchIntervalLabel" in APP_JS
    assert "`${openCount} open`" not in APP_JS
    assert '`${snapshot.watch_interval_seconds}s`' not in APP_JS


def test_control_flow_requires_rich_supervisor_decision_before_available_state():
    assert "function supervisorDecisionAvailable" in APP_JS
    assert "function currentSupervisorDecision" in APP_JS
    assert "currentSupervisorDecision(bundle)" in function_block("renderSupervisorControlFlow")
    assert 'lastDecision ? lastDecision.action || "available" : "unavailable"' not in APP_JS
    assert "nonEmptyObject(snapshot.last_decision) || decisions[0] || null" not in APP_JS


def test_decision_log_visible_text_uses_translated_classification_fallback():
    decision_log = function_block("renderSupervisorDecisionLog")
    decision_detail = function_block("supervisorDecisionDetail")

    assert '"supervisor-decision-text"' in decision_log
    assert "supervisorDecisionDetail(decision)" in decision_log
    assert "decision.summary || decision.reason || decision.classification" not in decision_log

    assert "supervisorClassificationLabel(decision.classification)" in decision_detail
    assert "decision.summary || decision.reason || classification || decision.decision_id" in decision_detail


def test_supervisor_dashboard_mock_uses_chinese_visible_verdict_labels():
    raw_verdict_tokens = {"continue", "refocus", "stop", "must_fix", "should_fix"}
    raw_visible_tokens = [
        token
        for code_span in re.findall(r"`([^`]+)`", SUPERVISOR_MOCK)
        for token in re.split(r"[/,\s]+", code_span)
        if token in raw_verdict_tokens
    ]
    assert raw_visible_tokens == []
    assert ">continue<" not in SUPERVISOR_MOCK
    assert '<span class="pill good">继续</span>' in SUPERVISOR_MOCK


def test_supervisor_dashboard_mock_does_not_expose_internal_operational_labels():
    forbidden_visible_fragments = [
        "0 open",
        "stopped_budget",
        "Freshness Target",
        ">idempotency_key<",
        "idempotency_key",
        "open decisions",
        "needs-user-decisions",
        "retry_ceiling",
        "auditor_stop",
        "unsafe_secret",
        "open decision",
    ]
    for fragment in forbidden_visible_fragments:
        assert fragment not in SUPERVISOR_MOCK


def test_supervisor_frontend_user_decision_copy_does_not_show_internal_labels():
    combined = (
        function_block("renderSupervisorUserDecisions")
        + function_block("renderSupervisorContinuation")
        + function_block("renderSupervisorRecovery")
    )

    for fragment in [
        "open 决策",
        "暂无 needs-user-decisions 数据",
        "暂无 open 决策",
        "user decision",
        "failure_key：",
        "idempotency_key：",
        "已有 idempotency_key",
        "continuation",
    ]:
        assert fragment not in combined


def test_supervisor_action_and_classification_fallbacks_stay_chinese():
    action_label = function_block("supervisorActionLabel")
    classification_label = function_block("supervisorClassificationLabel")

    assert 'text(normalized, "暂无数据")' not in action_label
    assert 'text(normalized, "暂无数据")' not in classification_label
    assert '"未识别动作"' in action_label
    assert '"未识别分类"' in classification_label


def test_supervisor_service_version_renders_stale_runtime_metadata():
    version_label = function_block("serviceVersionLabel")

    assert 'version.freshness === "stale"' in version_label
    assert '"版本过期"' in version_label
    assert 'version.freshness === "unavailable"' in version_label
    assert version_label.index('version.freshness === "unavailable"') < version_label.index("version.matches_expected === false")
