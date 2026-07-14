from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import threading
import time

import pytest

from scripts.harness_loop_runtime_lock import RunLockBusy, acquire_repository_mutation_lock
from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
)
from scripts.loop_supervisor.store import SupervisorStore
from scripts.loop_supervisor.reconciler import reconcile_once
import scripts.harness_loop_orchestrator as legacy
import scripts.loop_supervisor.reconciler as reconciler_module


def _seed_action(
    root: Path,
    *,
    action_id: str = "action-1",
    run_id: str = "run-1",
    action_type: ActionType = ActionType.RUN_PLANNER,
    phase: str = "planning",
) -> ActionRequest:
    run_dir = root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "policy": "autonomous_knowledge",
                "phase": phase,
                "next_action": "run_autonomous_planner",
                "state_revision": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    request = ActionRequest(
        action_id=action_id,
        run_id=run_id,
        run_revision=0,
        policy="autonomous_knowledge",
        phase=phase,
        action_type=action_type,
        idempotency_key=f"key-{action_id}",
        payload={"driver": "fake"},
    )
    with SupervisorStore.open(root) as store:
        store.migrate()
        store.upsert_run_projection(
            {
                "run_id": run_id,
                "policy": "autonomous_knowledge",
                "phase": phase,
                "status": "active",
                "revision": 0,
            }
        )
        store.enqueue_action(request)
    return request


def _success(summary: str = "bounded action completed") -> ActionResult:
    return ActionResult(ActionResultClass.SUCCESS, summary)


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.invalid"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"], cwd=root, check=True
    )
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "test: initial"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _phase_request(
    run_id: str, phase: str, action_type: ActionType, *, action_id: str
) -> ActionRequest:
    return ActionRequest(
        action_id=action_id,
        run_id=run_id,
        run_revision=0,
        policy="autonomous_knowledge",
        phase=phase,
        action_type=action_type,
        idempotency_key=f"key-{action_id}",
        task_id="autonomous-task-1",
        payload={"driver": "fake"},
    )


def _reconcile_and_work(
    root: Path,
    store: SupervisorStore,
    *,
    run_id: str,
    expected_action: ActionType,
    worker_id: str,
) -> str:
    from scripts.loop_supervisor.worker import worker_once

    reconciled = reconcile_once(root, store, include_worktrees=False)
    action = reconciled.action_for(run_id)
    current = legacy.load_run(root, run_id)
    assert action is not None, (
        f"expected={expected_action.value} "
        f"state={current['phase']}/{current['next_action']} "
        f"actions={[(row['action_type'], row['status']) for row in store.fetch_all('actions')]} "
        f"records={[(record.valid, record.error) for record in reconciled.run_records]} "
        f"decisions={reconciled.open_user_decisions}"
    )
    assert action.action_type is expected_action

    result = worker_once(root, worker_id)

    assert result.status == "completed"
    assert result.action_id == action.action_id
    return result.action_id


def test_worker_executes_exactly_one_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    first = _seed_action(tmp_path, action_id="action-1")
    _seed_action(tmp_path, action_id="action-2", run_id="run-2")
    calls: list[str] = []

    def execute(request: ActionRequest, _root: Path) -> ActionResult:
        calls.append(request.action_id)
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)

    result = worker.worker_once(tmp_path, "worker-1")

    assert result.action_id == first.action_id
    assert result.status == "completed"
    assert calls == [first.action_id]
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        statuses = {row["action_id"]: row["status"] for row in store.fetch_all("actions")}
    assert statuses == {"action-1": "completed", "action-2": "pending"}


def test_confirmed_demand_run_reconciles_and_worker_calls_planner_primitive(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.worker import worker_once

    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Implement one bounded task",
        run_id="demand-run",
        confirm=True,
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        reconciled = reconcile_once(tmp_path, store, include_worktrees=False)
        action = reconciled.action_for("demand-run")

    assert action is not None
    assert action.action_type is ActionType.RUN_PLANNER

    result = worker_once(tmp_path, "planner-worker")

    assert result.status == "completed"
    run = legacy.load_run(tmp_path, "demand-run")
    assert run["phase"] == "generating"
    assert run["next_action"] == "run_generator"
    assert (tmp_path / ".codex/loop-runs/demand-run/planner-output.json").is_file()
    assert not (tmp_path / ".codex/loop-runs/demand-run/generator-result.json").exists()


def test_autonomous_workers_run_hygiene_commit_push_and_cleanup_as_separate_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="autonomous-knowledge",
        requirement="Expand fixture knowledge",
        run_id="autonomous-run",
        domain="fixture",
        confirm=True,
    )
    run = legacy.load_run(tmp_path, "autonomous-run")
    run["phase"] = "generating"
    run["next_action"] = "run_autonomous_generator"
    run["task_id"] = "autonomous-task-1"
    legacy.save_run(tmp_path, run)

    generated = legacy.run_bounded_generator(
        tmp_path,
        _phase_request(
            "autonomous-run",
            "generating",
            ActionType.RUN_GENERATOR,
            action_id="setup-generator",
        ),
    )
    evaluated = legacy.run_bounded_evaluator(
        tmp_path,
        _phase_request(
            "autonomous-run",
            "evaluating",
            ActionType.RUN_EVALUATOR,
            action_id="setup-evaluator",
        ),
    )
    assert generated.result_class is ActionResultClass.SUCCESS
    assert evaluated.result_class is ActionResultClass.SUCCESS
    assert legacy.load_run(tmp_path, "autonomous-run")["phase"] == "artifact_hygiene"

    commit_calls: list[list[str]] = []
    push_calls: list[str] = []
    original_commit = legacy.run_git_commit

    def record_commit(
        repo_root: Path, changed_paths: list[str], message: str
    ) -> str:
        commit_calls.append(list(changed_paths))
        return original_commit(repo_root, changed_paths, message)

    def fake_push(
        repo_root: Path, run_payload: dict[str, object], commit_sha: str
    ) -> dict[str, object]:
        push_calls.append(commit_sha)
        result = {
            "status": "pass",
            "commit": commit_sha,
            "remote_commit": commit_sha,
            "error": "",
        }
        legacy.write_json_file(
            legacy.run_dir_for(repo_root, str(run_payload["run_id"]))
            / "push-result.json",
            result,
        )
        return result

    monkeypatch.setattr(legacy, "run_git_commit", record_commit)
    monkeypatch.setattr(legacy, "_push_autonomous_commit", fake_push)

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action_ids = [
            _reconcile_and_work(
                tmp_path,
                store,
                run_id="autonomous-run",
                expected_action=action_type,
                worker_id=f"worker-{index}",
            )
            for index, action_type in enumerate(
                (
                    ActionType.RUN_ARTIFACT_HYGIENE,
                    ActionType.COMMIT,
                    ActionType.PUSH,
                    ActionType.CLEANUP,
                ),
                start=1,
            )
        ]

    final = legacy.load_run(tmp_path, "autonomous-run")
    assert len(action_ids) == len(set(action_ids)) == 4
    assert len(commit_calls) == 1
    assert len(push_calls) == 1
    assert final["phase"] == "planning"
    assert final["next_action"] == "run_autonomous_planner"
    assert final["last_result"] == "pass"
    assert final["phase"] != "passed_waiting_human_merge"
    assert final["_autonomous_completed_task_ids"] == ["autonomous-task-1"]


def test_demand_cleanup_remains_generic_and_waits_for_human_merge(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.worker import worker_once

    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Clean demand artifacts",
        run_id="demand-cleanup",
        confirm=True,
    )
    run = legacy.load_run(tmp_path, "demand-cleanup")
    run["phase"] = "cleanup"
    run["next_action"] = "run_cleanup"
    legacy.save_run(tmp_path, run)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        reconciled = reconcile_once(tmp_path, store, include_worktrees=False)
        action = reconciled.action_for("demand-cleanup")
    assert action is not None
    assert action.action_type is ActionType.CLEANUP

    result = worker_once(tmp_path, "demand-cleanup-worker")

    assert result.status == "completed"
    final = legacy.load_run(tmp_path, "demand-cleanup")
    assert final["phase"] == "passed_waiting_human_merge"
    assert final["next_action"] == "await_human_merge_confirmation"


def test_reconciler_waits_for_worker_finalize_and_completion_under_run_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Serialize worker and reconciler",
        run_id="race-run",
        confirm=True,
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        planner = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            "race-run"
        )
    assert planner is not None

    legacy_written = threading.Event()
    release_handler = threading.Event()
    reconcile_attempted = threading.Event()
    original_acquire = reconciler_module.acquire_run_lock

    def same_revision_handler(
        request: ActionRequest, root: Path
    ) -> ActionResult:
        run = legacy.load_run(root, request.run_id)
        run["phase"] = "generating"
        run["next_action"] = "run_generator"
        run["task_id"] = "race-task"
        legacy.save_run(root, run)
        legacy_written.set()
        assert release_handler.wait(timeout=3)
        return _success("planner completed")

    @contextmanager
    def observed_reconcile_lock(*args: object, **kwargs: object):
        reconcile_attempted.set()
        with original_acquire(*args, **kwargs) as token:
            yield token

    monkeypatch.setattr(worker, "execute_action", same_revision_handler)
    monkeypatch.setattr(
        reconciler_module, "acquire_run_lock", observed_reconcile_lock
    )
    worker_result: list[object] = []
    reconcile_result: list[object] = []

    worker_thread = threading.Thread(
        target=lambda: worker_result.append(worker.worker_once(tmp_path, "race-worker"))
    )
    worker_thread.start()
    assert legacy_written.wait(timeout=2)

    def reconcile_in_thread() -> None:
        with SupervisorStore.open(tmp_path) as thread_store:
            thread_store.migrate()
            reconcile_result.append(
                reconcile_once(tmp_path, thread_store, include_worktrees=False)
            )

    reconcile_thread = threading.Thread(target=reconcile_in_thread)
    reconcile_thread.start()
    assert reconcile_attempted.wait(timeout=2)
    time.sleep(0.1)
    assert reconcile_thread.is_alive()
    assert reconcile_result == []

    release_handler.set()
    worker_thread.join(timeout=3)
    reconcile_thread.join(timeout=3)
    assert not worker_thread.is_alive()
    assert not reconcile_thread.is_alive()

    completed = worker_result[0]
    reconciled = reconcile_result[0]
    assert completed.status == "completed"
    assert completed.status != "lease_lost"
    run = legacy.load_run(tmp_path, "race-run")
    assert run["state_revision"] == 1
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        planner_row = store.get_action(planner.action_id)
        projected = store.get_run("race-run")
        pending = [
            row
            for row in store.fetch_all("actions")
            if row["run_id"] == "race-run" and row["status"] == "pending"
        ]
    assert planner_row.status == "completed"
    assert projected["revision"] == 1
    assert len(pending) == 1
    assert pending[0]["action_type"] == ActionType.RUN_GENERATOR.value
    assert reconciled.open_user_decisions == []


def test_worker_waits_when_reconciler_holds_same_run_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Reconciler owns run lock first",
        run_id="reconciler-first",
        confirm=True,
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            "reconciler-first"
        )
    assert action is not None

    reconcile_before_enqueue = threading.Event()
    release_reconciler = threading.Event()
    handler_entered = threading.Event()
    original_enqueue = SupervisorStore.enqueue_action
    original_planner = legacy.run_planner

    def blocked_enqueue(
        self: SupervisorStore, request: ActionRequest, *args: object, **kwargs: object
    ):
        if request.run_id == "reconciler-first":
            reconcile_before_enqueue.set()
            assert release_reconciler.wait(timeout=3)
        return original_enqueue(self, request, *args, **kwargs)

    def observed_planner(*args: object, **kwargs: object):
        handler_entered.set()
        return original_planner(*args, **kwargs)

    monkeypatch.setattr(SupervisorStore, "enqueue_action", blocked_enqueue)
    monkeypatch.setattr(legacy, "run_planner", observed_planner)
    reconcile_result: list[object] = []
    worker_result: list[object] = []

    def reconcile_in_thread() -> None:
        with SupervisorStore.open(tmp_path) as thread_store:
            thread_store.migrate()
            reconcile_result.append(
                reconcile_once(tmp_path, thread_store, include_worktrees=False)
            )

    reconcile_thread = threading.Thread(target=reconcile_in_thread)
    reconcile_thread.start()
    assert reconcile_before_enqueue.wait(timeout=2)
    worker_thread = threading.Thread(
        target=lambda: worker_result.append(
            worker.worker_once(tmp_path, "reconciler-first-worker")
        )
    )
    worker_thread.start()
    time.sleep(0.1)
    assert worker_thread.is_alive()
    assert not handler_entered.is_set()

    release_reconciler.set()
    reconcile_thread.join(timeout=3)
    worker_thread.join(timeout=3)
    assert not reconcile_thread.is_alive()
    assert not worker_thread.is_alive()
    assert handler_entered.is_set()
    assert worker_result[0].status == "completed"

    monkeypatch.setattr(SupervisorStore, "enqueue_action", original_enqueue)
    with SupervisorStore.open(tmp_path) as final_store:
        final_store.migrate()
        final_reconcile = reconcile_once(
            tmp_path, final_store, include_worktrees=False
        )
        file_state = legacy.load_run(tmp_path, "reconciler-first")
        projected = final_store.get_run("reconciler-first")
        old_action_status = final_store.get_action(action.action_id).status
        actions = [
            row
            for row in final_store.fetch_all("actions")
            if row["run_id"] == "reconciler-first"
        ]
        attempts = [
            row
            for row in final_store.fetch_all("action_attempts")
            if row["action_id"] == action.action_id
        ]

    assert final_reconcile.open_user_decisions == []
    assert old_action_status == "completed"
    assert file_state["state_revision"] == projected["revision"] == 1
    assert file_state["phase"] == projected["phase"] == "generating"
    pending = [row for row in actions if row["status"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["run_revision"] == 1
    assert pending[0]["action_type"] == ActionType.RUN_GENERATOR.value
    assert not any(
        row["status"] == "pending" and row["run_revision"] == 0 for row in actions
    )
    assert len(attempts) == 1


def test_worker_heartbeat_renews_worker_and_action_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    entered = threading.Event()
    release = threading.Event()

    def execute(_request: ActionRequest, _root: Path) -> ActionResult:
        entered.set()
        assert release.wait(timeout=3)
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)
    monkeypatch.setattr(worker, "HEARTBEAT_SECONDS", 0.05)
    thread = threading.Thread(target=worker.worker_once, args=(tmp_path, "worker-heartbeat"))
    thread.start()
    assert entered.wait(timeout=2)

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        before = next(row for row in store.fetch_all("actions") if row["action_id"] == action.action_id)
    time.sleep(0.15)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        after = next(row for row in store.fetch_all("actions") if row["action_id"] == action.action_id)
        heartbeat = next(row for row in store.fetch_all("workers") if row["worker_id"] == "worker-heartbeat")

    release.set()
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert after["lease_heartbeat_at"] > before["lease_heartbeat_at"]
    assert heartbeat["heartbeat_at"] == after["lease_heartbeat_at"]


def test_expired_crashed_worker_lease_is_reclaimed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        leased = store.lease_next_action("worker-crashed", lease_seconds=120)
        assert leased is not None
        stale = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(timespec="microseconds")
        store._connection.execute(
            "UPDATE actions SET lease_expires_at = ?, lease_heartbeat_at = ? WHERE action_id = ?",
            (stale, stale, action.action_id),
        )
        store._connection.execute(
            "UPDATE workers SET heartbeat_at = ? WHERE worker_id = ?",
            (stale, "worker-crashed"),
        )
    monkeypatch.setattr(worker, "execute_action", lambda _request, _root: _success("reclaimed"))

    result = worker.worker_once(tmp_path, "worker-replacement")

    assert result.status == "completed"
    assert result.action_id == action.action_id
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        attempts = store.fetch_all("action_attempts")
    assert attempts[0]["worker_id"] == "worker-replacement"


def test_process_exit_after_lease_is_not_recorded_as_action_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)

    def crash(_request: ActionRequest, _root: Path) -> ActionResult:
        raise SystemExit(9)

    monkeypatch.setattr(worker, "execute_action", crash)

    with pytest.raises(SystemExit, match="9"):
        worker.worker_once(tmp_path, "worker-crash")

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        row = next(item for item in store.fetch_all("actions") if item["action_id"] == action.action_id)
        attempts = store.fetch_all("action_attempts")
    assert row["status"] == "leased"
    assert row["lease_owner"] == "worker-crash"
    assert attempts == []


def test_repository_mutation_lock_serializes_different_runs(tmp_path: Path) -> None:
    with acquire_repository_mutation_lock(tmp_path, owner="worker-a") as first:
        assert first["owner"] == "worker-a"
        with pytest.raises(RunLockBusy) as raised:
            with acquire_repository_mutation_lock(tmp_path, owner="worker-b"):
                pass
    assert raised.value.run_id == "repository-mutation"
    assert raised.value.current_owner == "worker-a"


def test_worker_obeys_repository_lock_for_registry_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    called = False

    def execute(_request: ActionRequest, _root: Path) -> ActionResult:
        nonlocal called
        called = True
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)
    with acquire_repository_mutation_lock(tmp_path, owner="worker-a"):
        result = worker.worker_once(tmp_path, "worker-b")

    assert result.action_id == action.action_id
    assert result.status == "failed"
    assert result.result_class == ActionResultClass.RETRYABLE_FAILURE.value
    assert called is False


def test_worker_rechecks_store_guards_when_completing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)

    def execute(_request: ActionRequest, _root: Path) -> ActionResult:
        with SupervisorStore.open(tmp_path) as store:
            store.migrate()
            store.open_user_decision(
                scope="run",
                run_id=action.run_id,
                summary="operator decision required",
            )
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)

    result = worker.worker_once(tmp_path, "worker-guard")

    assert result.status == "lease_lost"
    assert result.recovery_evidence
    evidence = json.loads(
        (tmp_path / result.recovery_evidence).read_text(encoding="utf-8")
    )
    assert evidence["action_id"] == action.action_id
    assert evidence["error_class"] == "LeaseError"
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        row = next(item for item in store.fetch_all("actions") if item["action_id"] == action.action_id)
    assert row["status"] == "leased"


def test_stop_signal_preserves_interruption_evidence_and_prevents_new_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)

    def execute(_request: ActionRequest, _root: Path) -> ActionResult:
        worker.request_stop("SIGTERM")
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)
    worker.clear_stop_request()
    try:
        result = worker.worker_once(tmp_path, "worker-term")
        stopped = worker.worker_once(tmp_path, "worker-term")
    finally:
        worker.clear_stop_request()

    assert result.status == "completed"
    evidence = tmp_path / result.interruption_evidence
    assert evidence.is_file()
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["action_id"] == action.action_id
    assert payload["signal"] == "SIGTERM"
    assert stopped.status == "stopped"
