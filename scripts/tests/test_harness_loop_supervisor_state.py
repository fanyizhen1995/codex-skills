import json

import pytest

from scripts.harness_loop_supervisor_state import (
    RecoveryAttemptInput,
    append_jsonl,
    build_supervisor_state,
    make_failure_key,
    normalize_error_class,
    open_user_decision,
    read_jsonl,
    record_recovery_attempt,
    supervisor_dir,
    utc_now_iso,
)


def test_failure_key_normalizes_and_rejects_unknown_category():
    assert make_failure_key("service_down", "Project Root", "Crawler Backend", "Connection refused!") == (
        "service_down:project-root:crawler-backend:connection-refused"
    )
    with pytest.raises(ValueError):
        make_failure_key("other", "project", "service", "error")


def test_jsonl_helpers_append_and_skip_blank_lines(tmp_path):
    path = tmp_path / "nested" / "events.jsonl"

    append_jsonl(path, {"event": "first"})
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    append_jsonl(path, {"event": "second", "count": 2})

    assert read_jsonl(path) == [{"event": "first"}, {"event": "second", "count": 2}]


def test_supervisor_dir_uses_codex_supervisor_path(tmp_path):
    assert supervisor_dir(tmp_path) == tmp_path / ".codex" / "supervisor"


def test_utc_now_iso_uses_utc_z_suffix():
    timestamp = utc_now_iso()

    assert timestamp.endswith("Z")
    assert "+00:00" not in timestamp


def test_normalize_error_class_returns_safe_slug():
    assert normalize_error_class("Connection refused!") == "connection-refused"
    assert normalize_error_class("  HTTP_500 / Retry?  ") == "http-500-retry"
    assert normalize_error_class("") == "unknown"


def test_open_user_decision_writes_open_decision_payload(tmp_path):
    decision = open_user_decision(
        tmp_path,
        reason="too_many_failures",
        failure_key="service_down:project:crawler-backend:connection-refused",
        summary="crawler backend restart failed repeatedly",
        required_user_decision="Inspect service logs",
        affected_runs=["run-1"],
        attempts=[{"summary": "fail 1"}],
    )

    decision_files = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    decision_events = read_jsonl(tmp_path / ".codex" / "supervisor" / "user-decisions.jsonl")

    assert len(decision_files) == 1
    assert decision_files[0].name == "service_down-project-crawler-backend-connection-refused.json"
    assert json.loads(decision_files[0].read_text(encoding="utf-8")) == decision
    assert decision["status"] == "open"
    assert decision["reason"] == "too_many_failures"
    assert decision_events == [decision]


def test_recovery_attempt_counter_opens_user_decision_on_third_failure(tmp_path):
    key = make_failure_key("service_down", "project", "crawler-backend", "connection_refused")
    for index in range(3):
        attempt = record_recovery_attempt(
            tmp_path,
            RecoveryAttemptInput(
                failure_key=key,
                run_id="",
                action="restart_service",
                status="fail",
                summary=f"fail {index}",
                evidence_paths=[],
            ),
        )
    assert attempt["consecutive_failure_count"] == 3
    assert attempt["max_consecutive_failures"] == 3
    assert attempt["attempt_id"] == "recovery-000003"
    decisions = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    assert len(decisions) == 1
    decision = json.loads(decisions[0].read_text(encoding="utf-8"))
    assert decision["reason"] == "retry_ceiling_exceeded"


def test_recovery_attempt_counter_groups_by_run_id_or_project(tmp_path):
    key = make_failure_key("service_down", "project", "crawler-backend", "connection_refused")
    record_recovery_attempt(
        tmp_path,
        RecoveryAttemptInput(
            failure_key=key,
            run_id="run-1",
            action="restart_service",
            status="fail",
            summary="fail",
            evidence_paths=[],
        ),
    )
    run_two_attempt = record_recovery_attempt(
        tmp_path,
        RecoveryAttemptInput(
            failure_key=key,
            run_id="run-2",
            action="restart_service",
            status="fail",
            summary="fail in another run",
            evidence_paths=[],
        ),
    )
    run_one_attempt = record_recovery_attempt(
        tmp_path,
        RecoveryAttemptInput(
            failure_key=key,
            run_id="run-1",
            action="restart_service",
            status="fail",
            summary="same run failed again",
            evidence_paths=[],
        ),
    )

    assert run_two_attempt["consecutive_failure_count"] == 1
    assert run_one_attempt["consecutive_failure_count"] == 2
    assert not (tmp_path / ".codex" / "supervisor" / "needs-user-decisions").exists()


def test_recovery_attempt_counter_resets_on_success_for_same_run(tmp_path):
    key = make_failure_key("service_down", "project", "crawler-backend", "connection_refused")
    for status in ("fail", "pass"):
        record_recovery_attempt(
            tmp_path,
            RecoveryAttemptInput(
                failure_key=key,
                run_id="run-1",
                action="restart_service",
                status=status,
                summary=status,
                evidence_paths=[],
            ),
        )
    attempt = record_recovery_attempt(
        tmp_path,
        RecoveryAttemptInput(
            failure_key=key,
            run_id="run-1",
            action="restart_service",
            status="fail",
            summary="new failure",
            evidence_paths=[],
        ),
    )

    assert attempt["consecutive_failure_count"] == 1
    assert not (tmp_path / ".codex" / "supervisor" / "needs-user-decisions").exists()


def test_recovery_attempt_rejects_status_outside_pass_fail(tmp_path):
    with pytest.raises(ValueError):
        record_recovery_attempt(
            tmp_path,
            RecoveryAttemptInput(
                failure_key="service_down:project:crawler-backend:connection-refused",
                run_id="run-1",
                action="restart_service",
                status="blocked",
                summary="blocked is not a recovery result",
                evidence_paths=[],
            ),
        )


def test_state_writers_reject_failure_keys_with_unknown_category(tmp_path):
    with pytest.raises(ValueError):
        record_recovery_attempt(
            tmp_path,
            RecoveryAttemptInput(
                failure_key="other:project:crawler-backend:connection-refused",
                run_id="run-1",
                action="restart_service",
                status="fail",
                summary="bad category",
                evidence_paths=[],
            ),
        )

    with pytest.raises(ValueError):
        open_user_decision(
            tmp_path,
            reason="unsupported_state",
            failure_key="other:project:crawler-backend:connection-refused",
            summary="bad category",
            required_user_decision="Choose a supported category.",
            affected_runs=[],
            attempts=[],
        )


def test_build_supervisor_state_persists_current_snapshot(tmp_path):
    state = build_supervisor_state(
        tmp_path,
        mode="watch",
        service_health={"crawler_backend": {"status": "healthy"}},
        run_summary={"active": 1, "blocked": 0, "continuation_candidates": 0, "needs_user_decision": 0},
        failure_summary={"open_failure_keys": 0},
        last_decision=None,
        watch_interval_seconds=60,
    )

    state_file = tmp_path / ".codex" / "supervisor" / "supervisor-state.json"
    assert json.loads(state_file.read_text(encoding="utf-8")) == state
    assert state["schema_version"] == 1
    assert state["project_root"] == str(tmp_path)
    assert state["status"] == "healthy"
    assert state["started_at"].endswith("Z")
    assert state["last_heartbeat_at"].endswith("Z")
    assert state["last_tick_at"].endswith("Z")
    assert state["mode"] == "watch"
    assert state["watch_interval_seconds"] == 60
    assert state["service_summary"] == {"total": 1, "healthy": 1, "degraded": 0, "blocked": 0}
    assert state["failure_summary"]["max_consecutive_failures"] == 3
    assert state["last_decision"] is None
