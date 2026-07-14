import json
import multiprocessing
import os
import threading
import time

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
from scripts.loop_supervisor.reconciler import atomic_save_run


def test_failure_key_normalizes_and_rejects_unknown_category():
    assert make_failure_key(
        "service_down", "Project Root", "Crawler Backend", "Connection refused!"
    ) == ("service_down:project-root:crawler-backend:connection-refused")
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


def test_service_summary_counts_online_separately_from_version_health(tmp_path):
    state = build_supervisor_state(
        tmp_path,
        mode="once",
        service_health={
            "crawler-backend": {
                "status": "degraded",
                "reachable": True,
                "tmux_session_exists": True,
                "running_version": {"freshness": "stale"},
            },
            "loop-auto-resume": {
                "status": "healthy",
                "reachable": True,
                "tmux_session_exists": True,
                "running_version": {"freshness": "fresh"},
            },
        },
        run_summary={
            "active": 0,
            "blocked": 0,
            "continuation_candidates": 0,
            "needs_user_decision": 0,
        },
        failure_summary={"open_failure_keys": 0},
        last_decision=None,
        watch_interval_seconds=30,
    )

    assert state["service_summary"]["online"] == 2
    assert state["service_summary"]["healthy"] == 1
    assert state["service_summary"]["degraded"] == 1


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

    decision_files = sorted(
        (tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json")
    )
    decision_events = read_jsonl(
        tmp_path / ".codex" / "supervisor" / "user-decisions.jsonl"
    )

    assert len(decision_files) == 1
    assert (
        decision_files[0].name
        == "service_down-project-crawler-backend-connection-refused.json"
    )
    assert json.loads(decision_files[0].read_text(encoding="utf-8")) == decision
    assert decision["status"] == "open"
    assert decision["reason"] == "too_many_failures"
    assert decision_events == [decision]


def test_recovery_attempt_counter_opens_user_decision_on_third_failure(tmp_path):
    key = make_failure_key(
        "service_down", "project", "crawler-backend", "connection_refused"
    )
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
    decisions = sorted(
        (tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json")
    )
    assert len(decisions) == 1
    decision = json.loads(decisions[0].read_text(encoding="utf-8"))
    assert decision["reason"] == "retry_ceiling_exceeded"


def test_recovery_attempt_counter_groups_by_run_id_or_project(tmp_path):
    key = make_failure_key(
        "service_down", "project", "crawler-backend", "connection_refused"
    )
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
    key = make_failure_key(
        "service_down", "project", "crawler-backend", "connection_refused"
    )
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


def test_state_writers_reject_unnormalized_failure_key_segments(tmp_path):
    bad_keys = [
        "service_down:Project Root:crawler-backend:connection-refused",
        "service_down:project:crawler_backend:connection-refused",
        "service_down:project:crawler-backend:Connection Refused",
        "service_down:project:crawler-backend:connection.refused",
    ]

    for failure_key in bad_keys:
        with pytest.raises(ValueError, match="invalid failure_key"):
            record_recovery_attempt(
                tmp_path,
                RecoveryAttemptInput(
                    failure_key=failure_key,
                    run_id="run-1",
                    action="restart_service",
                    status="fail",
                    summary="bad key",
                    evidence_paths=[],
                ),
            )

        with pytest.raises(ValueError, match="invalid failure_key"):
            open_user_decision(
                tmp_path,
                reason="unsupported_state",
                failure_key=failure_key,
                summary="bad key",
                required_user_decision="Provide a normalized failure key.",
                affected_runs=[],
                attempts=[],
            )


@pytest.mark.parametrize(
    ("run_summary", "failure_summary", "message"),
    [
        (
            {"active": 0, "blocked": 0, "continuation_candidates": 0},
            {"open_failure_keys": 0},
            "run_summary.needs_user_decision",
        ),
        (
            {
                "active": 0,
                "blocked": 0,
                "continuation_candidates": 0,
                "needs_user_decision": 0,
            },
            {},
            "failure_summary.open_failure_keys",
        ),
        (
            {
                "active": 0,
                "blocked": 0,
                "continuation_candidates": 0,
                "needs_user_decision": 0,
            },
            {"open_failure_keys": "zero"},
            "failure_summary.open_failure_keys",
        ),
    ],
)
def test_build_supervisor_state_rejects_missing_or_invalid_required_summaries(
    tmp_path, run_summary, failure_summary, message
):
    with pytest.raises(ValueError, match=message):
        build_supervisor_state(
            tmp_path,
            mode="watch",
            service_health={"crawler_backend": {"status": "healthy"}},
            run_summary=run_summary,
            failure_summary=failure_summary,
            last_decision=None,
            watch_interval_seconds=60,
        )

    assert not (tmp_path / ".codex" / "supervisor" / "supervisor-state.json").exists()


def test_build_supervisor_state_persists_current_snapshot(tmp_path):
    state = build_supervisor_state(
        tmp_path,
        mode="watch",
        service_health={"crawler_backend": {"status": "healthy"}},
        run_summary={
            "active": 1,
            "blocked": 0,
            "continuation_candidates": 0,
            "needs_user_decision": 0,
        },
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
    assert state["service_summary"] == {
        "total": 1,
        "online": 0,
        "healthy": 1,
        "degraded": 0,
        "blocked": 0,
    }
    assert state["failure_summary"]["max_consecutive_failures"] == 3
    assert state["last_decision"] is None


def test_atomic_save_run_increments_revision_once_and_replaces_sibling_tempfile(
    tmp_path, monkeypatch
):
    run_dir = tmp_path / ".codex" / "loop-runs" / "atomic-run"
    run_dir.mkdir(parents=True)
    run_path = run_dir / "run.json"
    run_path.write_text(
        json.dumps(
            {
                "run_id": "atomic-run",
                "policy": "autonomous_knowledge",
                "phase": "planning",
                "state_revision": 3,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    replace_calls = []
    fsync_calls = []
    real_replace = os.replace
    real_fsync = os.fsync

    def observed_replace(source, target):
        replace_calls.append((source, target))
        return real_replace(source, target)

    def observed_fsync(fd):
        fsync_calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(
        "scripts.loop_supervisor.reconciler.os.replace", observed_replace
    )
    monkeypatch.setattr("scripts.loop_supervisor.reconciler.os.fsync", observed_fsync)

    saved = atomic_save_run(
        tmp_path,
        "atomic-run",
        {
            "run_id": "atomic-run",
            "policy": "autonomous_knowledge",
            "phase": "generating",
        },
        expected_revision=3,
    )

    assert saved["state_revision"] == 4
    assert json.loads(run_path.read_text(encoding="utf-8"))["state_revision"] == 4
    assert len(replace_calls) == 1
    assert os.fspath(replace_calls[0][1]) == os.fspath(run_path)
    assert os.path.dirname(os.fspath(replace_calls[0][0])) == os.fspath(run_dir)
    assert len(fsync_calls) == 2
    assert not list(run_dir.glob(".run.json.*.tmp"))


def test_atomic_save_run_rejects_stale_expected_revision_without_writing(tmp_path):
    run_dir = tmp_path / ".codex" / "loop-runs" / "stale-run"
    run_dir.mkdir(parents=True)
    run_path = run_dir / "run.json"
    original = {
        "run_id": "stale-run",
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "state_revision": 5,
    }
    run_path.write_text(json.dumps(original) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="stale run revision"):
        atomic_save_run(
            tmp_path,
            "stale-run",
            {**original, "phase": "generating"},
            expected_revision=4,
        )

    assert json.loads(run_path.read_text(encoding="utf-8")) == original


def test_atomic_save_run_rejects_payload_id_different_from_target_directory(tmp_path):
    run_dir = tmp_path / ".codex" / "loop-runs" / "directory-owner"
    run_dir.mkdir(parents=True)
    run_path = run_dir / "run.json"
    original = {
        "run_id": "directory-owner",
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "state_revision": 5,
    }
    run_path.write_text(json.dumps(original) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="run id.*directory"):
        atomic_save_run(
            tmp_path,
            "directory-owner",
            {**original, "run_id": "declared-other", "phase": "generating"},
            expected_revision=5,
        )

    assert json.loads(run_path.read_text(encoding="utf-8")) == original
    assert not (tmp_path / ".codex" / "loop-runs" / "declared-other").exists()


def test_atomic_save_run_serializes_thread_cas_before_revision_read(
    tmp_path, monkeypatch
):
    run_path = _seed_atomic_cas_run(tmp_path, revision=7)
    first_read = threading.Event()
    release_first = threading.Event()
    read_count = 0
    read_count_lock = threading.Lock()
    results = []
    from scripts.loop_supervisor import reconciler

    real_read = reconciler._read_json_object

    def gated_read(path):
        nonlocal read_count
        with read_count_lock:
            read_count += 1
            current = read_count
        if current == 1:
            first_read.set()
            assert release_first.wait(timeout=5)
        return real_read(path)

    monkeypatch.setattr(reconciler, "_read_json_object", gated_read)

    def write(phase):
        try:
            saved = atomic_save_run(
                tmp_path,
                "cas-run",
                {
                    "run_id": "cas-run",
                    "policy": "autonomous_knowledge",
                    "phase": phase,
                },
                expected_revision=7,
            )
            results.append(("success", saved["phase"]))
        except ValueError as exc:
            results.append(("stale", str(exc)))

    first = threading.Thread(target=write, args=("generating",))
    second = threading.Thread(target=write, args=("evaluating",))
    first.start()
    assert first_read.wait(timeout=5)
    second.start()
    try:
        time.sleep(0.2)
        assert read_count == 1
    finally:
        release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive() and not second.is_alive()
    assert sorted(status for status, _ in results) == ["stale", "success"]
    assert json.loads(run_path.read_text(encoding="utf-8"))["state_revision"] == 8


def test_atomic_save_run_serializes_process_cas_before_revision_read(
    tmp_path, monkeypatch
):
    run_path = _seed_atomic_cas_run(tmp_path, revision=11)
    context = multiprocessing.get_context("fork")
    first_read = context.Event()
    release_first = context.Event()
    read_count = context.Value("i", 0)
    results = context.Queue()
    from scripts.loop_supervisor import reconciler

    real_read = reconciler._read_json_object

    def gated_read(path):
        with read_count.get_lock():
            read_count.value += 1
            current = read_count.value
        if current == 1:
            first_read.set()
            assert release_first.wait(timeout=5)
        return real_read(path)

    monkeypatch.setattr(reconciler, "_read_json_object", gated_read)

    def write(phase):
        try:
            saved = atomic_save_run(
                tmp_path,
                "cas-run",
                {
                    "run_id": "cas-run",
                    "policy": "autonomous_knowledge",
                    "phase": phase,
                },
                expected_revision=11,
            )
            results.put(("success", saved["phase"]))
        except ValueError as exc:
            results.put(("stale", str(exc)))

    first = context.Process(target=write, args=("generating",))
    second = context.Process(target=write, args=("evaluating",))
    first.start()
    assert first_read.wait(timeout=5)
    second.start()
    try:
        time.sleep(0.2)
        assert read_count.value == 1
    finally:
        release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert first.exitcode == 0 and second.exitcode == 0
    outcomes = [results.get(timeout=2), results.get(timeout=2)]
    assert sorted(status for status, _ in outcomes) == ["stale", "success"]
    assert json.loads(run_path.read_text(encoding="utf-8"))["state_revision"] == 12


def _seed_atomic_cas_run(tmp_path, *, revision):
    run_dir = tmp_path / ".codex" / "loop-runs" / "cas-run"
    run_dir.mkdir(parents=True)
    run_path = run_dir / "run.json"
    run_path.write_text(
        json.dumps(
            {
                "run_id": "cas-run",
                "policy": "autonomous_knowledge",
                "phase": "planning",
                "state_revision": revision,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return run_path
