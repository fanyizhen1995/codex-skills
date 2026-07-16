from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from scripts.harness_loop_supervisor import (
    SupervisorConfig,
    main,
    run_supervisor_once,
)
from scripts.harness_loop_orchestrator import create_preflight_run
from scripts.loop_supervisor.executor import execute_action
from scripts.loop_supervisor.models import ActionOwner, ActionType
from scripts.loop_supervisor.reconciler import (
    _state_fingerprint,
    atomic_save_run,
    atomic_save_run_locked,
    desired_action_for_run,
    discover_run_records,
    reconcile_once,
)
from scripts.harness_loop_runtime_lock import acquire_run_lock
from scripts.loop_supervisor.store import SupervisorStore


REPO_ROOT = Path(__file__).resolve().parents[2]


def seed_run(project_root: Path, run_id: str, **overrides: object) -> Path:
    run_dir = project_root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run = {
        "run_id": run_id,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "task_id": f"{run_id}-parent-1",
        "worktree": str(project_root),
        "last_result": "none",
        "next_action": "run_autonomous_planner",
        "commit": "abc123",
    }
    run.update(overrides)
    path = run_dir / "run.json"
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return path


def seed_stopped_budget_run(
    project_root: Path,
    run_id: str,
    *,
    parent_counter: int = 10,
    lineage_id: str | None = None,
    commit: str = "abc123",
) -> Path:
    return seed_run(
        project_root,
        run_id,
        phase="stopped_budget",
        next_action="none",
        last_result="pass",
        task_id=f"{run_id}-parent-{parent_counter}",
        parent_task_counter=parent_counter,
        loop_lineage_id=lineage_id or run_id,
        commit=commit,
    )


def seed_auditor_report(project_root: Path, run_id: str) -> Path:
    path = (
        project_root
        / ".codex"
        / "loop-runs"
        / run_id
        / "audit-reports"
        / "audit-999.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"run_id": run_id, "verdict": "stop"}) + "\n",
        encoding="utf-8",
    )
    return path


def migrated_store(project_root: Path) -> SupervisorStore:
    store = SupervisorStore.open(project_root)
    store.migrate()
    return store


def test_locked_atomic_save_requires_active_matching_run_lock_token(tmp_path):
    path = seed_run(tmp_path, "locked-save")
    payload = json.loads(path.read_text(encoding="utf-8"))

    with acquire_run_lock(
        tmp_path, "locked-save", owner="test:locked-save", blocking=True
    ) as token:
        saved = atomic_save_run_locked(
            tmp_path,
            "locked-save",
            payload,
            token=token,
            expected_revision=0,
            expected_fingerprint=_state_fingerprint(payload),
        )

    assert saved["state_revision"] == 1
    with pytest.raises(ValueError, match="active run lock token"):
        atomic_save_run_locked(
            tmp_path,
            "locked-save",
            saved,
            token=token,
            expected_revision=1,
            expected_fingerprint=_state_fingerprint(saved),
        )


def test_once_cli_opens_sqlite_reconciler_and_writes_bounded_state(tmp_path):
    seed_run(tmp_path, "cli-run")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/harness_loop_supervisor.py",
            "--project-root",
            str(tmp_path),
            "--once",
            "--dry-run",
            "--include-worktrees",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    supervisor = tmp_path / ".codex" / "supervisor"
    state = json.loads(
        (supervisor / "supervisor-state.json").read_text(encoding="utf-8")
    )
    assert state["mode"] == "once"
    assert state["run_summary"]["active"] == 1
    assert (supervisor / "supervisor.db").exists()
    assert not (supervisor / "run-decisions.jsonl").exists()
    assert not (supervisor / "continuation-plans.jsonl").exists()


def test_watch_cli_can_stop_after_one_reconcile_tick(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/harness_loop_supervisor.py",
            "--project-root",
            str(tmp_path),
            "--watch",
            "--max-ticks",
            "1",
            "--interval-seconds",
            "1",
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    state = json.loads(
        (tmp_path / ".codex" / "supervisor" / "supervisor-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["mode"] == "watch"
    assert state["last_tick_at"].endswith("Z")


def test_watch_reports_transient_tick_error_and_continues(
    tmp_path, monkeypatch, capsys
):
    calls = 0

    def fail_once(config):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("temporary discovery failure " + "x" * 1000)
        return {"status": "healthy", "tick": calls}

    monkeypatch.setattr(
        "scripts.harness_loop_supervisor.run_supervisor_once", fail_once
    )
    monkeypatch.setattr("scripts.harness_loop_supervisor.time.sleep", lambda _: None)

    assert (
        main(
            [
                "--project-root",
                str(tmp_path),
                "--watch",
                "--max-ticks",
                "2",
                "--interval-seconds",
                "1",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert calls == 2
    assert '"status": "error"' in output
    assert '"tick": 2' in output
    assert len(output) < 2000
    state = json.loads(
        (tmp_path / ".codex" / "supervisor" / "supervisor-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["status"] == "error"
    assert state["error"]["class"] == "OSError"


@pytest.mark.parametrize("control_error", [KeyboardInterrupt, SystemExit])
def test_watch_does_not_catch_process_control_exceptions(
    tmp_path, monkeypatch, control_error
):
    def stop(_config):
        raise control_error()

    monkeypatch.setattr("scripts.harness_loop_supervisor.run_supervisor_once", stop)

    with pytest.raises(control_error):
        main(["--project-root", str(tmp_path), "--watch"])


def test_wrapper_has_no_direct_process_or_service_restart_execution_path():
    source = (REPO_ROOT / "scripts" / "harness_loop_supervisor.py").read_text(
        encoding="utf-8"
    )

    assert "restart_service" not in source
    assert "ALLOWED_RESTART_SESSIONS" not in source
    assert "tmux" not in source
    assert "subprocess" not in source


def test_wrapper_repeated_tick_does_not_append_legacy_or_sqlite_transition(tmp_path):
    run_path = seed_run(tmp_path, "steady")
    config = SupervisorConfig(project_root=tmp_path, dry_run=True)

    run_supervisor_once(config)
    before = run_path.stat().st_mtime_ns
    run_supervisor_once(config)

    with migrated_store(tmp_path) as store:
        assert store.count("actions") == 1
        assert store.count("transitions") == 0
    assert run_path.stat().st_mtime_ns == before
    assert not (tmp_path / ".codex" / "supervisor" / "events.jsonl").exists()


def test_reconcile_generator_block_queues_recovery_without_user_decision(tmp_path):
    seed_run(
        tmp_path,
        "recover-generator",
        phase="stopped_blocked",
        next_action="inspect_autonomous_generator",
    )
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert (
        result.action_for("recover-generator").action_type
        is ActionType.RECOVER_GENERATOR_RESULT
    )
    assert result.open_user_decisions == []
    assert store.count("actions") == 1


def test_run_scoped_decision_does_not_block_independent_continuation(tmp_path):
    seed_run(tmp_path, "blocked", user_decision_required=True)
    seed_stopped_budget_run(tmp_path, "safe", lineage_id="lineage-safe")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("blocked")["scope"] == "run"
    assert result.action_for("safe").action_type is ActionType.CREATE_CONTINUATION
    assert store.count("actions") == 1


def test_reconcile_honors_existing_store_decisions_before_desired_actions(tmp_path):
    seed_run(tmp_path, "blocked")
    seed_run(tmp_path, "safe")
    store = migrated_store(tmp_path)
    store.open_user_decision(
        scope="run",
        run_id="blocked",
        failure_key="existing:run-gate",
        summary="existing run decision",
    )

    run_scoped = reconcile_once(tmp_path, store)

    assert run_scoped.action_for("blocked") is None
    assert run_scoped.action_for("safe").action_type is ActionType.RUN_PLANNER

    store.open_user_decision(
        scope="global",
        failure_key="existing:global-gate",
        summary="existing global decision",
    )
    globally_blocked = reconcile_once(tmp_path, store)

    assert globally_blocked.queued_actions == []


def test_reconcile_project_lock_serializes_entire_tick(tmp_path, monkeypatch):
    seed_run(tmp_path, "run-1")
    first_entered = threading.Event()
    release_first = threading.Event()
    discovery_calls = 0
    calls_lock = threading.Lock()
    from scripts.loop_supervisor import reconciler

    real_discover = reconciler.discover_run_candidates

    def gated_discover(root, *, include_worktrees=True):
        nonlocal discovery_calls
        with calls_lock:
            discovery_calls += 1
            current = discovery_calls
        if current == 1:
            first_entered.set()
            assert release_first.wait(timeout=5)
        return real_discover(root, include_worktrees=include_worktrees)

    monkeypatch.setattr(reconciler, "discover_run_candidates", gated_discover)
    outcomes = []

    def reconcile():
        with migrated_store(tmp_path) as store:
            outcomes.append(reconciler.reconcile_once(tmp_path, store))

    first = threading.Thread(target=reconcile)
    second = threading.Thread(target=reconcile)
    first.start()
    assert first_entered.wait(timeout=5)
    second.start()
    try:
        time.sleep(0.2)
        assert discovery_calls == 1
    finally:
        release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert len(outcomes) == 2


def test_reconcile_skips_active_run_lock_without_overwriting_its_projection(tmp_path):
    active_path = seed_run(tmp_path, "active")
    seed_run(tmp_path, "unlocked")
    store = migrated_store(tmp_path)
    initial = reconcile_once(tmp_path, store, include_worktrees=False)
    active_action = initial.action_for("active")
    assert active_action is not None
    leased = store.claim_pending_action(
        active_action.action_id,
        "active-worker",
        lease_seconds=60,
        expected_queue_owner=ActionOwner.WORKER,
    )
    assert leased is not None
    initial_projection = store.get_run("active")
    actions_before = store.count("actions")
    decisions_before = store.count("user_decisions")

    active_payload = json.loads(active_path.read_text(encoding="utf-8"))
    active_payload["state_revision"] = 1
    active_payload["last_result"] = "worker still running"
    active_path.write_text(json.dumps(active_payload) + "\n", encoding="utf-8")

    outcomes = []
    failures = []
    completed = threading.Event()

    def reconcile_while_worker_holds_lock():
        try:
            outcomes.append(reconcile_once(tmp_path, store, include_worktrees=False))
        except BaseException as error:
            failures.append(error)
        finally:
            completed.set()

    worker = threading.Thread(target=reconcile_while_worker_holds_lock)
    try:
        with acquire_run_lock(tmp_path, "active", owner="worker:active", blocking=True):
            worker.start()
            bounded = completed.wait(timeout=0.5)
            if bounded:
                skipped = outcomes[0]
                assert skipped.action_for("active") is None
                assert skipped.action_for("unlocked") is not None
                assert store.get_run("active") == initial_projection
                assert store.get_action(active_action.action_id).status == "leased"
                assert store.count("actions") == actions_before
                assert store.count("user_decisions") == decisions_before
    finally:
        worker.join(timeout=2)

    assert bounded
    assert not worker.is_alive()
    assert failures == []
    recovered = reconcile_once(tmp_path, store, include_worktrees=False)
    assert recovered.action_for("active") is not None
    assert store.get_run("active")["revision"] == 1
    assert store.count("user_decisions") == decisions_before
    store.close()


def test_reconcile_does_not_close_global_decision_updated_after_observation(
    tmp_path, monkeypatch
):
    run_path = seed_run(tmp_path, "secret-run", unsafe_secret=True)
    with migrated_store(tmp_path) as seed_store:
        reconcile_once(tmp_path, seed_store)
    cleared = json.loads(run_path.read_text(encoding="utf-8"))
    cleared.pop("unsafe_secret")
    run_path.write_text(json.dumps(cleared, indent=2) + "\n", encoding="utf-8")
    store_a = migrated_store(tmp_path)
    store_b = migrated_store(tmp_path)
    before_close = threading.Event()
    allow_close = threading.Event()
    original_close = store_a.close_user_decision

    def gated_close(decision_id, *, resolution, expected_updated_at=None):
        before_close.set()
        assert allow_close.wait(timeout=5)
        return original_close(
            decision_id,
            resolution=resolution,
            expected_updated_at=expected_updated_at,
        )

    monkeypatch.setattr(store_a, "close_user_decision", gated_close)
    outcome = []

    thread = threading.Thread(
        target=lambda: outcome.append(reconcile_once(tmp_path, store_a))
    )
    thread.start()
    assert before_close.wait(timeout=5)
    decision = store_b.fetch_all("user_decisions")[0]
    store_b.open_user_decision(
        scope="global",
        run_id="secret-run",
        failure_key=decision["failure_key"],
        summary="secret condition re-observed by another tick",
    )
    allow_close.set()
    thread.join(timeout=5)

    current = store_b.fetch_all("user_decisions")[0]
    assert not thread.is_alive()
    assert len(outcome) == 1
    assert current["status"] == "open"
    assert current["summary"] == "secret condition re-observed by another tick"


def test_secret_exposure_is_global_and_blocks_independent_continuation(tmp_path):
    seed_run(tmp_path, "secret-run", unsafe_secret=True)
    seed_stopped_budget_run(tmp_path, "otherwise-safe")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("secret-run")["scope"] == "global"
    assert result.action_for("otherwise-safe") is None
    assert store.count("actions") == 0


def test_resolved_global_decision_closes_and_no_longer_blocks_continuation(tmp_path):
    secret_path = seed_run(tmp_path, "secret-run", unsafe_secret=True)
    seed_stopped_budget_run(tmp_path, "safe")
    store = migrated_store(tmp_path)
    first = reconcile_once(tmp_path, store)
    secret = json.loads(secret_path.read_text(encoding="utf-8"))
    secret.pop("unsafe_secret")
    secret_path.write_text(json.dumps(secret, indent=2) + "\n", encoding="utf-8")

    second = reconcile_once(tmp_path, store)

    assert first.decision_for("secret-run")["scope"] == "global"
    assert second.action_for("safe").action_type is ActionType.CREATE_CONTINUATION
    decisions = store.fetch_all("user_decisions")
    assert len(decisions) == 1
    assert decisions[0]["status"] == "closed"
    assert decisions[0]["resolution"] == "reconciliation condition cleared"
    assert store.fetch_all("failures")[0]["resolution"] == "resolved"


def test_resolved_failure_reopens_when_same_global_condition_recurs(tmp_path):
    run_path = seed_run(tmp_path, "secret-run", unsafe_secret=True)
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store)
    cleared = json.loads(run_path.read_text(encoding="utf-8"))
    cleared.pop("unsafe_secret")
    run_path.write_text(json.dumps(cleared, indent=2) + "\n", encoding="utf-8")
    reconcile_once(tmp_path, store)
    recurring = json.loads(run_path.read_text(encoding="utf-8"))
    expected_fingerprint = _state_fingerprint(recurring)
    recurring["unsafe_secret"] = True
    atomic_save_run(
        tmp_path,
        "secret-run",
        recurring,
        expected_revision=1,
        expected_fingerprint=expected_fingerprint,
    )

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("secret-run")["scope"] == "global"
    assert store.fetch_all("failures")[0]["resolution"] == "open"


@pytest.mark.parametrize(
    "signal",
    [
        "repo_corruption",
        "permission_expansion_required",
        "irreversible_operation_required",
        "explicit_global_stop",
    ],
)
def test_binding_spec_global_stop_exceptions_are_global(tmp_path, signal):
    seed_run(tmp_path, "global-run", **{signal: True})
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("global-run")["scope"] == "global"


def test_continuation_is_queued_with_stable_identity_and_not_created(tmp_path):
    source_path = seed_stopped_budget_run(
        tmp_path,
        "source",
        parent_counter=14,
        lineage_id="lineage-a",
        commit="commit-abc",
    )
    store = migrated_store(tmp_path)

    first = reconcile_once(tmp_path, store)
    second = reconcile_once(tmp_path, store)

    action = first.action_for("source")
    assert action.action_type is ActionType.CREATE_CONTINUATION
    assert action.payload_for_storage()["continuation_identity"] == {
        "loop_lineage_id": "lineage-a",
        "source_run_id": "source",
        "semantic_parent": "parent-14",
        "source_commit": "commit-abc",
    }
    assert second.action_for("source").action_id == action.action_id
    assert store.count("actions") == 1
    assert sorted((tmp_path / ".codex" / "loop-runs").glob("*/run.json")) == [
        source_path
    ]


def test_legacy_continuation_uses_projected_lineage_and_preserves_reviewer_cadence(
    tmp_path,
):
    seed_run(
        tmp_path,
        "legacy-root",
        phase="stopped_budget",
        next_action="none",
        last_result="pass",
        task_id="legacy-root-parent-1",
        parent_task_counter=1,
        _autonomous_completed_task_ids=["parent-1"],
    )
    source = create_preflight_run(
        tmp_path,
        "autonomous-knowledge",
        "Continue the legacy lineage.",
        "legacy-source",
        domain="ai_infra",
        constraints=[],
        stop_conditions=["stopped_budget"],
        confirm=True,
    )
    source.update(
        {
            "phase": "stopped_budget",
            "next_action": "none",
            "last_result": "pass",
            "previous_run_id": "legacy-root",
        }
    )
    (tmp_path / ".codex" / "loop-runs" / "legacy-source" / "run.json").write_text(
        json.dumps(source, indent=2) + "\n", encoding="utf-8"
    )
    store = migrated_store(tmp_path)

    first = reconcile_once(tmp_path, store)

    action = first.action_for("legacy-source")
    assert action is not None
    assert action.action_type is ActionType.CREATE_CONTINUATION
    assert store.get_run("legacy-root")["loop_lineage_id"] == "legacy-root"
    assert store.get_run("legacy-source")["loop_lineage_id"] == "legacy-root"
    assert json.loads(store.get_run("legacy-source")["summary"]["summary"])[
        "loop_lineage_id"
    ] == "legacy-root"
    assert action.payload_for_storage()["loop_lineage_id"] == "legacy-root"
    assert action.payload_for_storage()["continuation_identity"]["loop_lineage_id"] == (
        "legacy-root"
    )

    result = execute_action(action, tmp_path)

    assert result.result_class.value == "success", result.summary
    continuation_path = next(
        path
        for path in (tmp_path / ".codex" / "loop-runs").glob("*/run.json")
        if path.parent.name not in {"legacy-root", "legacy-source"}
    )
    continuation = json.loads(continuation_path.read_text(encoding="utf-8"))
    assert continuation["loop_lineage_id"] == "legacy-root"
    continuation.update(
        {
            "phase": "stopped_budget",
            "next_action": "none",
            "last_result": "pass",
            "task_id": "legacy-continuation-parent-2",
            "parent_task_counter": 2,
            "_autonomous_completed_task_ids": ["parent-2"],
        }
    )
    continuation_path.write_text(
        json.dumps(continuation, indent=2) + "\n", encoding="utf-8"
    )

    second = reconcile_once(tmp_path, store)

    assert store.get_run(continuation["run_id"])["loop_lineage_id"] == "legacy-root"
    assert any(
        queued.action_type is ActionType.RUN_REVIEWER
        for queued in second.queued_actions
    )


def test_stopped_budget_non_leaf_does_not_queue_parallel_continuation(tmp_path):
    seed_stopped_budget_run(tmp_path, "parent", parent_counter=14)
    seed_run(tmp_path, "child", previous_run_id="parent")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert result.action_for("parent") is None
    assert result.action_for("child").action_type is ActionType.RUN_PLANNER
    assert store.count("actions") == 1


def test_busy_child_projection_still_suppresses_parent_continuation(tmp_path):
    seed_stopped_budget_run(tmp_path, "parent", parent_counter=14)
    child_path = seed_run(tmp_path, "child", previous_run_id="parent")
    child_payload = json.loads(child_path.read_text(encoding="utf-8"))
    store = migrated_store(tmp_path)
    initial = reconcile_once(tmp_path, store, include_worktrees=False)
    child_action = initial.action_for("child")
    assert initial.action_for("parent") is None
    assert child_action is not None
    leased = store.claim_pending_action(
        child_action.action_id,
        "child-worker",
        lease_seconds=60,
        expected_queue_owner=ActionOwner.WORKER,
    )
    assert leased is not None

    with acquire_run_lock(tmp_path, "child", owner="worker:child", blocking=True):
        untrusted_payload = {**child_payload, "previous_run_id": "forged-parent"}
        child_path.write_text(json.dumps(untrusted_payload) + "\n", encoding="utf-8")
        try:
            busy = reconcile_once(tmp_path, store, include_worktrees=False)

            assert busy.action_for("parent") is None
            assert busy.action_for("child") is None
            assert store.get_action(child_action.action_id).status == "leased"
            assert store.count("actions") == 1
        finally:
            child_path.write_text(json.dumps(child_payload) + "\n", encoding="utf-8")

    unlocked = reconcile_once(tmp_path, store, include_worktrees=False)
    assert unlocked.action_for("parent") is None
    assert unlocked.action_for("child").action_id == child_action.action_id
    assert store.get_action(child_action.action_id).status == "leased"
    store.close()


def test_busy_forged_lineage_does_not_pollute_legacy_grandchild_projection(tmp_path):
    seed_run(tmp_path, "root", loop_lineage_id="trusted-lineage")
    child_path = seed_run(
        tmp_path,
        "child",
        previous_run_id="root",
        loop_lineage_id="trusted-lineage",
    )
    child_payload = json.loads(child_path.read_text(encoding="utf-8"))
    grandchild_path = seed_run(
        tmp_path,
        "grandchild",
        previous_run_id="child",
        loop_lineage_id="trusted-lineage",
    )
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store, include_worktrees=False)
    grandchild_payload = json.loads(grandchild_path.read_text(encoding="utf-8"))
    grandchild_payload.pop("loop_lineage_id")
    grandchild_payload["last_result"] = "legacy state changed"
    grandchild_path.write_text(json.dumps(grandchild_payload) + "\n", encoding="utf-8")

    with acquire_run_lock(tmp_path, "child", owner="worker:child", blocking=True):
        untrusted_payload = {**child_payload, "loop_lineage_id": "forged-lineage"}
        child_path.write_text(json.dumps(untrusted_payload) + "\n", encoding="utf-8")
        try:
            reconcile_once(tmp_path, store, include_worktrees=False)

            assert store.get_run("child")["loop_lineage_id"] == "trusted-lineage"
            assert store.get_run("grandchild")["loop_lineage_id"] == "trusted-lineage"
        finally:
            child_path.write_text(json.dumps(child_payload) + "\n", encoding="utf-8")

    reconcile_once(tmp_path, store, include_worktrees=False)
    assert store.get_run("grandchild")["loop_lineage_id"] == "trusted-lineage"
    store.close()


def test_busy_forged_worktree_does_not_global_stop_unlocked_run(tmp_path):
    busy_path = seed_run(tmp_path, "busy")
    busy_payload = json.loads(busy_path.read_text(encoding="utf-8"))
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store, include_worktrees=False)
    seed_run(tmp_path, "unlocked")

    with acquire_run_lock(tmp_path, "busy", owner="worker:busy", blocking=True):
        forged = {**busy_payload, "worktree": str(tmp_path.parent / "forged-owner")}
        busy_path.write_text(json.dumps(forged) + "\n", encoding="utf-8")
        try:
            result = reconcile_once(tmp_path, store, include_worktrees=False)

            assert result.action_for("unlocked") is not None
            assert not any(
                decision.get("scope") == "global"
                for decision in result.open_user_decisions
            )
        finally:
            busy_path.write_text(json.dumps(busy_payload) + "\n", encoding="utf-8")
    store.close()


def test_busy_parent_projection_gives_legacy_child_lineage_without_review(tmp_path):
    seed_run(
        tmp_path,
        "parent",
        loop_lineage_id="trusted-lineage",
        _autonomous_completed_task_ids=["parent-1"],
    )
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store, include_worktrees=False)
    seed_run(
        tmp_path,
        "legacy-child",
        previous_run_id="parent",
        task_id="legacy-child-parent-2",
        parent_task_counter=2,
        _autonomous_completed_task_ids=["parent-2"],
    )

    with acquire_run_lock(tmp_path, "parent", owner="worker:parent", blocking=True):
        busy = reconcile_once(tmp_path, store, include_worktrees=False)

        assert store.get_run("legacy-child")["loop_lineage_id"] == "trusted-lineage"
        assert not any(
            action.action_type is ActionType.RUN_REVIEWER
            for action in busy.queued_actions
        )
        assert not any(
            row["action_type"] == ActionType.RUN_REVIEWER.value
            for row in store.fetch_all("actions")
        )

    unlocked = reconcile_once(tmp_path, store, include_worktrees=False)
    assert any(
        action.action_type is ActionType.RUN_REVIEWER
        for action in unlocked.queued_actions
    )
    store.close()


def test_due_reviewer_reservation_blocks_only_the_next_parent_planner(tmp_path):
    run_id = "review-boundary"
    seed_run(
        tmp_path,
        run_id,
        task_id=f"{run_id}-parent-3",
        parent_task_counter=2,
        semantic_parent_task_next=3,
        loop_lineage_id=run_id,
        _autonomous_completed_task_ids=["parent-1", "parent-2"],
    )
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store, include_worktrees=False)

    actions = [action for action in result.queued_actions if action.run_id == run_id]
    assert [action.action_type for action in actions] == [ActionType.RUN_REVIEWER]
    assert not any(
        row["action_type"] == ActionType.RUN_PLANNER.value
        for row in store.fetch_all("actions")
        if row["run_id"] == run_id
    )
    store.close()


def test_busy_run_record_payload_is_sanitized_in_reconcile_result(tmp_path):
    run_path = seed_run(tmp_path, "busy")
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store, include_worktrees=False)

    with acquire_run_lock(tmp_path, "busy", owner="worker:busy", blocking=True):
        run_path.write_text(
            json.dumps({**payload, "requirement": "untrusted in-flight value"}) + "\n",
            encoding="utf-8",
        )
        try:
            result = reconcile_once(tmp_path, store, include_worktrees=False)
        finally:
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    busy_record = next(record for record in result.run_records if record.run_id == "busy")
    assert busy_record.payload == {}
    store.close()


def test_reconcile_excludes_busy_runs_from_reviewer_scheduling(
    tmp_path, monkeypatch
):
    from scripts.loop_supervisor import reconciler

    seed_run(tmp_path, "busy")
    observed_busy_run_ids: list[set[str]] = []

    def capture_schedule(_store, *, now, busy_run_ids):
        assert now is not None
        observed_busy_run_ids.append(set(busy_run_ids))
        return []

    monkeypatch.setattr(reconciler, "schedule_due_reviews", capture_schedule)
    with migrated_store(tmp_path) as store:
        with acquire_run_lock(tmp_path, "busy", owner="worker:busy", blocking=True):
            reconciler.reconcile_once(tmp_path, store, include_worktrees=False)

    assert observed_busy_run_ids == [{"busy"}]


def test_legacy_run_upgrades_revision_once_when_state_changes(tmp_path):
    run_path = seed_run(tmp_path, "legacy")
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store)
    changed = json.loads(run_path.read_text(encoding="utf-8"))
    changed.update({"phase": "generating", "next_action": "run_autonomous_generator"})
    run_path.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")

    reconcile_once(tmp_path, store)
    reconcile_once(tmp_path, store)

    persisted = json.loads(run_path.read_text(encoding="utf-8"))
    assert persisted["state_revision"] == 1
    assert store.get_run("legacy")["revision"] == 1
    assert store.count("transitions") == 1


def test_explicit_same_revision_state_conflict_is_run_scoped(tmp_path):
    run_path = seed_run(tmp_path, "conflict", state_revision=2)
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store)
    changed = json.loads(run_path.read_text(encoding="utf-8"))
    changed.update({"phase": "generating", "next_action": "run_autonomous_generator"})
    run_path.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("conflict")["scope"] == "run"
    assert store.get_run("conflict")["revision"] == 2
    assert store.count("transitions") == 0


def test_same_revision_continuation_identity_change_conflicts_by_fingerprint(tmp_path):
    run_path = seed_stopped_budget_run(
        tmp_path,
        "fingerprint-run",
        parent_counter=14,
        lineage_id="lineage-a",
        commit="commit-a",
    )
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["state_revision"] = 3
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    store = migrated_store(tmp_path)
    reconcile_once(tmp_path, store)
    changed = json.loads(run_path.read_text(encoding="utf-8"))
    changed.update(
        {
            "parent_task_counter": 15,
            "git_head": "commit-b",
            "head": "commit-c",
            "previous_commit": "commit-d",
        }
    )
    run_path.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("fingerprint-run")["scope"] == "run"
    assert store.get_run("fingerprint-run")["revision"] == 3
    assert store.count("actions") == 1


def test_discovery_reads_root_and_contained_non_symlink_worktree(tmp_path):
    seed_run(tmp_path, "root-run", worktree=".")
    worktree = tmp_path / ".worktrees" / "child"
    seed_run(worktree, "worktree-run")

    records = discover_run_records(tmp_path)

    assert [record.run_id for record in records] == ["root-run", "worktree-run"]
    assert records[1].repo_root == worktree.resolve()


def test_prelock_discovery_returns_only_path_metadata(tmp_path):
    seed_run(
        tmp_path,
        "candidate",
        requirement="payload must not cross the pre-lock boundary",
        unsafe_secret=True,
    )

    records = discover_run_records(tmp_path, include_worktrees=False)

    assert len(records) == 1
    assert records[0].run_id == "candidate"
    assert records[0].payload == {}


def test_reconcile_action_carries_repo_relative_execution_root(tmp_path):
    worktree = tmp_path / ".worktrees" / "child"
    seed_run(worktree, "worktree-run")
    store = migrated_store(tmp_path)

    action = reconcile_once(tmp_path, store).action_for("worktree-run")

    assert action is not None
    assert action.repo_relative_root == ".worktrees/child"
    stored = store.get_action(action.action_id)
    assert stored.repo_relative_root == ".worktrees/child"


def test_reconcile_can_exclude_worktree_runs(tmp_path):
    seed_run(tmp_path, "root-run", worktree=".")
    worktree = tmp_path / ".worktrees" / "child"
    seed_run(worktree, "worktree-run")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store, include_worktrees=False)

    assert [record.run_id for record in result.run_records] == ["root-run"]
    assert store.get_run("root-run") is not None
    with pytest.raises(KeyError):
        store.get_run("worktree-run")


@pytest.mark.parametrize("root_valid", [True, False])
def test_duplicate_directory_run_id_invalidates_every_record(tmp_path, root_valid):
    if root_valid:
        seed_run(tmp_path, "duplicate-run")
    else:
        invalid = tmp_path / ".codex" / "loop-runs" / "duplicate-run" / "run.json"
        invalid.parent.mkdir(parents=True)
        invalid.write_text("{not-json}\n", encoding="utf-8")
    worktree = tmp_path / ".worktrees" / "child"
    seed_run(worktree, "duplicate-run")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    duplicates = [
        record
        for record in result.run_records
        if record.directory_run_id == "duplicate-run"
    ]
    assert len(duplicates) == 2
    assert all(not record.valid and record.ownership_failure for record in duplicates)
    assert all("duplicate run directory id" in record.error for record in duplicates)
    assert store.count("runs") == 0
    assert store.count("actions") == 0
    assert len(result.open_user_decisions) == 1
    assert result.open_user_decisions[0]["scope"] == "global"


def test_discovery_defers_run_file_validation_until_locked_reread(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    seed_run(outside, "outside-run")
    worktrees = tmp_path / ".worktrees"
    worktrees.mkdir()
    (worktrees / "linked").symlink_to(outside, target_is_directory=True)
    escaped_run_dir = tmp_path / ".codex" / "loop-runs" / "escaped"
    escaped_run_dir.mkdir(parents=True)
    (escaped_run_dir / "run.json").symlink_to(
        outside / ".codex" / "loop-runs" / "outside-run" / "run.json"
    )

    records = discover_run_records(tmp_path)

    assert not any(record.run_id == "outside-run" for record in records)
    assert sum(record.ownership_failure for record in records) == 1
    escaped = next(record for record in records if record.run_id == "escaped")
    assert escaped.valid is True
    assert escaped.payload == {}

    with migrated_store(tmp_path) as store:
        result = reconcile_once(tmp_path, store)

    assert any(
        record.directory_run_id == "escaped" and record.ownership_failure
        for record in result.run_records
    )
    assert any(
        decision.get("scope") == "global"
        for decision in result.open_user_decisions
    )


def test_secure_reread_rejects_run_json_symlink_swap_after_validation(
    tmp_path, monkeypatch
):
    run_path = seed_run(tmp_path, "swap-run")
    outside_path = tmp_path / "outside-run.json"
    outside_path.write_text(run_path.read_text(encoding="utf-8"), encoding="utf-8")
    from scripts.loop_supervisor import reconciler

    real_check = reconciler._require_contained_non_symlink
    swapped = False

    def swap_after_check(path, root, *, allow_missing_leaf=False):
        nonlocal swapped
        result = real_check(path, root, allow_missing_leaf=allow_missing_leaf)
        if Path(path) == run_path and not swapped:
            run_path.unlink()
            run_path.symlink_to(outside_path)
            swapped = True
        return result

    monkeypatch.setattr(reconciler, "_require_contained_non_symlink", swap_after_check)

    with migrated_store(tmp_path) as store:
        result = reconcile_once(tmp_path, store, include_worktrees=False)

    assert len(result.run_records) == 1
    assert result.run_records[0].directory_run_id == "swap-run"
    assert result.run_records[0].ownership_failure is True
    assert result.run_records[0].payload == {}
    assert result.open_user_decisions[0]["scope"] == "global"


@pytest.mark.parametrize(
    "broken_link",
    ["worktrees", "runs_root", "run_directory", "run_json"],
)
def test_broken_symlink_is_global_repository_ownership_failure(tmp_path, broken_link):
    missing = tmp_path / "missing-target"
    if broken_link == "worktrees":
        (tmp_path / ".worktrees").symlink_to(missing, target_is_directory=True)
    elif broken_link == "runs_root":
        codex = tmp_path / ".codex"
        codex.mkdir()
        (codex / "loop-runs").symlink_to(missing, target_is_directory=True)
    elif broken_link == "run_directory":
        runs_root = tmp_path / ".codex" / "loop-runs"
        runs_root.mkdir(parents=True)
        (runs_root / "broken-run").symlink_to(missing, target_is_directory=True)
    else:
        run_dir = tmp_path / ".codex" / "loop-runs" / "broken-run"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").symlink_to(missing / "run.json")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert any(record.ownership_failure for record in result.run_records)
    assert len(result.open_user_decisions) == 1
    assert result.open_user_decisions[0]["scope"] == "global"


def test_invalid_json_is_run_scoped_but_ownership_failure_is_global(tmp_path):
    invalid = tmp_path / ".codex" / "loop-runs" / "invalid" / "run.json"
    invalid.parent.mkdir(parents=True)
    invalid.write_text("{not-json}\n", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-ownership"
    seed_run(outside, "outside")
    linked = tmp_path / ".codex" / "loop-runs" / "linked" / "run.json"
    linked.parent.mkdir(parents=True)
    linked.symlink_to(outside / ".codex" / "loop-runs" / "outside" / "run.json")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("invalid")["scope"] == "run"
    assert any(decision["scope"] == "global" for decision in result.open_user_decisions)
    assert store.count("failures") == 2


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_run_json_is_invalid_and_never_projected(tmp_path, constant):
    run_path = tmp_path / ".codex" / "loop-runs" / "invalid-number" / "run.json"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(
        '{"run_id":"invalid-number","policy":"autonomous_knowledge",'
        f'"phase":"planning","next_action":"run_autonomous_planner","value":{constant}}}\n',
        encoding="utf-8",
    )
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert result.decision_for("invalid-number")["scope"] == "run"
    assert store.count("runs") == 0


@pytest.mark.parametrize("declared_run_id", ["declared-other", None])
def test_payload_run_id_must_match_run_directory_basename(tmp_path, declared_run_id):
    run_path = seed_run(tmp_path, "directory-owner")
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    if declared_run_id is None:
        payload.pop("run_id")
    else:
        payload["run_id"] = declared_run_id
    run_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert len(result.open_user_decisions) == 1
    assert result.open_user_decisions[0]["scope"] == "global"
    assert result.run_records[0].ownership_failure is True


def test_reconciler_ignores_legacy_auditor_control_files(tmp_path):
    seed_stopped_budget_run(tmp_path, "auditor-is-not-control", parent_counter=11)
    seed_auditor_report(tmp_path, "auditor-is-not-control")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    assert (
        result.action_for("auditor-is-not-control").action_type
        is ActionType.CREATE_CONTINUATION
    )
    assert result.open_user_decisions == []


def test_reconciler_migrates_legacy_audit_block_without_running_auditor(tmp_path):
    run_path = seed_run(
        tmp_path,
        "legacy-audit-blocked",
        run_kind="parent",
        phase="audit_blocked",
        next_action="create_audit_remediation_task",
        last_result="blocked",
    )
    legacy_report = seed_auditor_report(tmp_path, "legacy-audit-blocked")
    store = migrated_store(tmp_path)

    result = reconcile_once(tmp_path, store)

    migrated = json.loads(run_path.read_text(encoding="utf-8"))
    assert (migrated["phase"], migrated["next_action"]) == (
        "planning",
        "run_autonomous_planner",
    )
    assert migrated["legacy_audit_migration"]["source_phase"] == "audit_blocked"
    assert migrated["reviewer_directives"][-1]["decision"] == "auto_remediate"
    assert result.action_for("legacy-audit-blocked").action_type is ActionType.RUN_PLANNER
    assert legacy_report.exists()
    assert list(legacy_report.parent.glob("audit-*.json")) == [legacy_report]


def test_legacy_audit_migration_preserves_existing_reviewer_directives(tmp_path):
    existing = {
        "review_id": "review-old",
        "decision": "refocus",
        "summary": "Keep the prior focus correction.",
        "evidence_refs": [f"sha256:{'a' * 64}"],
    }
    run_path = seed_run(
        tmp_path,
        "legacy-audit-with-directive",
        run_kind="parent",
        phase="audit_blocked",
        next_action="create_audit_remediation_task",
        last_result="blocked",
        reviewer_directives=[existing],
    )
    store = migrated_store(tmp_path)

    reconcile_once(tmp_path, store)

    migrated = json.loads(run_path.read_text(encoding="utf-8"))
    assert migrated["reviewer_directives"][0] == existing
    assert migrated["reviewer_directives"][1]["review_id"] == "legacy-audit-migration"


def test_desired_action_always_uses_transition_registry(tmp_path, monkeypatch):
    calls = []

    def observed_transition(policy, phase, next_action):
        calls.append((policy, phase, next_action))
        from scripts.loop_supervisor.registry import transition_for

        return transition_for(policy, phase, next_action)

    monkeypatch.setattr(
        "scripts.loop_supervisor.reconciler.transition_for", observed_transition
    )
    run = {
        "run_id": "registry-run",
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "next_action": "run_autonomous_planner",
    }

    action = desired_action_for_run(run)

    assert action.action_type is ActionType.RUN_PLANNER
    assert calls == [("autonomous_knowledge", "planning", "run_autonomous_planner")]
