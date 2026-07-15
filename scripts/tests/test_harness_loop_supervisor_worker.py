from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import os

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


def _valid_run_payload(
    root: Path,
    run_id: str,
    *,
    phase: str = "planning",
    next_action: str = "run_autonomous_planner",
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "policy": "autonomous_knowledge",
        "phase": phase,
        "next_action": next_action,
        "state_revision": 0,
        "task_id": f"{run_id}-task",
        "domain": "fixture",
        "branch": "test",
        "worktree": str(root.resolve()),
        "requirement": "bounded worker fixture",
        "constraints": [],
        "stop_conditions": ["stopped_blocked"],
        "baseline_dirty_paths": [],
        "allowed_paths": [],
        "denylist_paths": [],
        "attempts": {
            "planner": 0,
            "generator": 0,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
        },
        "limits": legacy.default_limits(),
        "last_result": "none",
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
    }


def _seed_action(
    root: Path,
    *,
    action_id: str = "action-1",
    run_id: str = "run-1",
    action_type: ActionType = ActionType.RUN_PLANNER,
    phase: str = "planning",
    next_action: str = "run_autonomous_planner",
) -> ActionRequest:
    run_dir = root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            _valid_run_payload(
                root,
                run_id,
                phase=phase,
                next_action=next_action,
            )
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
        next_action=next_action,
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


def _create_demand_parent(root: Path, run_id: str) -> dict[str, object]:
    parent = legacy.create_preflight_run(
        repo_root=root,
        mode="demand-development",
        requirement="Build bounded parent child chain",
        run_id=run_id,
        confirm=True,
    )
    parent.update(
        {
            "run_kind": "parent",
            "phase": "planning",
            "next_action": "run_parent_planner",
            "child_run_ids": [],
            "current_child_run_id": "",
            "backlog": [],
            "aggregate_acceptance": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "pending": 0,
                "user_decision_required": False,
            },
            "reader_summary": {
                "purpose": "Build bounded parent child chain",
                "current_progress": "Planning",
                "next_step": "Create first child",
                "decision_needed": "No",
            },
            "accepted_changed_paths": [],
        }
    )
    legacy.save_run(root, parent)
    return parent


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


def _write_fake_evaluator_scenario(root: Path, task_id: str) -> None:
    path = root / "docs" / "harness" / "evaluator-scenarios" / f"{task_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "must_simulate": True,
                "user_scenarios": [
                    {
                        "scenario_id": "PHASE1-WORKER",
                        "user_goal": "Exercise the bounded Phase 1 demand flow.",
                        "prerequisites": ["Temporary fixture exists."],
                        "entrypoint": "python3 -c \"print('phase1-worker')\"",
                        "steps": ["Run each bounded Worker action."],
                        "expected_outcomes": ["The fake evaluator passes."],
                        "failure_signals": ["The evaluator blocks."],
                        "cleanup": ["Temporary fixture is removed."],
                        "automation_hint": "shell",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _phase_request(
    run_id: str,
    phase: str,
    action_type: ActionType,
    *,
    action_id: str,
    driver: str = "fake",
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
        payload={"driver": driver},
    )


def _prepare_autonomous_commit_gate(
    root: Path,
    run_id: str,
    *,
    generator_driver: str = "fake",
    run_updates: dict[str, object] | None = None,
) -> dict[str, object]:
    _init_git_repo(root)
    legacy.create_preflight_run(
        repo_root=root,
        mode="autonomous-knowledge",
        requirement="Exercise bounded commit safety gates",
        run_id=run_id,
        domain="fixture",
        confirm=True,
    )
    run = legacy.load_run(root, run_id)
    run.update(
        {
            "phase": "generating",
            "next_action": "run_autonomous_generator",
            "task_id": f"{run_id}-task",
            **(run_updates or {}),
        }
    )
    legacy.save_run(root, run)
    generated = legacy._run_bounded_generator(
        root,
        _phase_request(
            run_id,
            "generating",
            ActionType.RUN_GENERATOR,
            action_id=f"{run_id}-setup-generator",
            driver=generator_driver,
        ),
    )
    evaluated = legacy._run_bounded_evaluator(
        root,
        _phase_request(
            run_id,
            "evaluating",
            ActionType.RUN_EVALUATOR,
            action_id=f"{run_id}-setup-evaluator",
        ),
    )
    hygienic = legacy._run_bounded_artifact_hygiene(
        root,
        _phase_request(
            run_id,
            "artifact_hygiene",
            ActionType.RUN_ARTIFACT_HYGIENE,
            action_id=f"{run_id}-setup-hygiene",
        ),
    )
    assert generated.result_class is ActionResultClass.SUCCESS
    assert evaluated.result_class is ActionResultClass.SUCCESS
    assert hygienic.result_class is ActionResultClass.SUCCESS
    return legacy.read_json_file(
        legacy.run_dir_for(root, run_id) / "generator-result.json"
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


@pytest.mark.parametrize(
    ("role", "action_type", "phase", "next_action", "producer", "result_name"),
    [
        (
            "planner",
            ActionType.RUN_PLANNER,
            "planning",
            "run_autonomous_planner",
            "_run_fake_autonomous_planner",
            "planner-output.json",
        ),
        (
            "generator",
            ActionType.RUN_GENERATOR,
            "generating",
            "run_autonomous_generator",
            "_write_fake_autonomous_generator_result",
            "generator-result.json",
        ),
        (
            "evaluator",
            ActionType.RUN_EVALUATOR,
            "evaluating",
            "run_autonomous_evaluator",
            "_run_fake_autonomous_evaluator",
            "evaluator-result.json",
        ),
    ],
)
def test_worker_atomically_records_real_bounded_skill_invocations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    action_type: ActionType,
    phase: str,
    next_action: str,
    producer: str,
    result_name: str,
) -> None:
    from scripts.loop_supervisor import worker

    request = _seed_action(
        tmp_path,
        action_type=action_type,
        phase=phase,
        next_action=next_action,
    )
    skill_path = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("---\nname: alpha\ndescription: Alpha skill.\n---\n", encoding="utf-8")
    original_producer = getattr(legacy, producer)
    artifact_ref = f".codex/loop-runs/run-1/{role}-skill-invocation.json"
    artifact_path = tmp_path / artifact_ref

    def structured_producer(repo_root, run, **kwargs):
        produced = original_producer(repo_root, run, **kwargs)
        result_path = tmp_path / ".codex" / "loop-runs" / "run-1" / result_name
        payload = legacy.read_json_file(result_path)
        evidence = {
            "schema_version": 1,
            "invocation_id": f"invocation-worker-{role}-alpha",
            "run_id": "run-1",
            "task_id": payload["task_id"],
            "role": role,
            "skill_path": "skills/alpha/SKILL.md",
            "status": "confirmed",
        }
        legacy.write_json_file(artifact_path, evidence)
        artifact_hash = f"sha256:{hashlib.sha256(artifact_path.read_bytes()).hexdigest()}"
        payload["skill_invocations"] = [
            {
                "invocation_id": f"invocation-worker-{role}-alpha",
                "skill_path": "skills/alpha/SKILL.md",
                "artifact_path": artifact_ref,
                "artifact_sha256": artifact_hash,
            }
        ]
        legacy.write_json_file(result_path, payload)
        return produced

    monkeypatch.setattr(legacy, producer, structured_producer)

    result = worker.worker_once(tmp_path, f"worker-skill-{role}")

    assert result.status == "completed"
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        invocation = store.fetch_all("skill_invocations")[0]
        attempt = store.fetch_all("action_attempts")[0]
    assert invocation["action_id"] == request.action_id
    assert invocation["attempt_id"] == attempt["attempt_id"]
    assert invocation["artifact_sha256"] == (
        f"sha256:{hashlib.sha256(artifact_path.read_bytes()).hexdigest()}"
    )


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


def test_phase1_demand_flow_reaches_human_merge_via_bounded_workers(
    tmp_path: Path,
) -> None:
    _write_fake_evaluator_scenario(tmp_path, "phase1-demand-task")
    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Run the bounded Phase 1 demand flow",
        run_id="phase1-demand-run",
        task_id="phase1-demand-task",
        confirm=True,
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action_ids = [
            _reconcile_and_work(
                tmp_path,
                store,
                run_id="phase1-demand-run",
                expected_action=action_type,
                worker_id=f"phase1-worker-{index}",
            )
            for index, action_type in enumerate(
                (
                    ActionType.RUN_PLANNER,
                    ActionType.RUN_GENERATOR,
                    ActionType.RUN_EVALUATOR,
                ),
                start=1,
            )
        ]

    run = legacy.load_run(tmp_path, "phase1-demand-run")
    assert len(action_ids) == len(set(action_ids)) == 3
    assert run["phase"] == "passed_waiting_human_merge"
    assert run["next_action"] == "await_human_merge_confirmation"
    run_dir = legacy.run_dir_for(tmp_path, "phase1-demand-run")
    assert (run_dir / "planner-output.json").is_file()
    assert (run_dir / "generator-result.json").is_file()
    assert (run_dir / "evaluator-result.json").is_file()


def test_demand_parent_planner_worker_creates_exactly_one_child(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.worker import worker_once

    _init_git_repo(tmp_path)
    parent = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Build bounded parent child chain",
        run_id="parent-run",
        confirm=True,
    )
    parent.update(
        {
            "run_kind": "parent",
            "phase": "planning",
            "next_action": "run_parent_planner",
            "child_run_ids": [],
            "current_child_run_id": "",
            "backlog": [],
            "aggregate_acceptance": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "pending": 0,
                "user_decision_required": False,
            },
            "reader_summary": {
                "purpose": "Build bounded parent child chain",
                "current_progress": "Planning",
                "next_step": "Create first child",
                "decision_needed": "No",
            },
            "accepted_changed_paths": [],
        }
    )
    legacy.save_run(tmp_path, parent)

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            "parent-run"
        )
    assert action is not None
    assert action.action_type is ActionType.RUN_PLANNER

    result = worker_once(tmp_path, "parent-planner-worker")

    assert result.status == "completed"
    persisted = legacy.load_run(tmp_path, "parent-run")
    assert persisted["phase"] == "child_running"
    assert persisted["next_action"] == "run_child_generator"
    assert len(persisted["child_run_ids"]) == 1
    child = legacy.load_run(tmp_path, persisted["child_run_ids"][0])
    assert child["run_kind"] == "child"
    assert child["phase"] == "generating"
    assert not (tmp_path / "generated" / "child-001.txt").exists()


def test_demand_parent_child_chain_uses_one_action_per_worker(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.worker import worker_once

    _init_git_repo(tmp_path)
    parent = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Run one bounded child",
        run_id="chain-parent",
        confirm=True,
    )
    parent.update(
        {
            "run_kind": "parent",
            "phase": "planning",
            "next_action": "run_parent_planner",
            "child_run_ids": [],
            "current_child_run_id": "",
            "backlog": [],
            "aggregate_acceptance": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "pending": 0,
                "user_decision_required": False,
            },
            "reader_summary": {
                "purpose": "Run one bounded child",
                "current_progress": "Planning",
                "next_step": "Create first child",
                "decision_needed": "No",
            },
            "accepted_changed_paths": [],
        }
    )
    legacy.save_run(tmp_path, parent)

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        reconcile_once(tmp_path, store, include_worktrees=False)
        assert worker_once(tmp_path, "chain-parent-plan").status == "completed"

        parent = legacy.load_run(tmp_path, "chain-parent")
        child_id = parent["child_run_ids"][0]
        generated = reconcile_once(tmp_path, store, include_worktrees=False)
        assert generated.action_for("chain-parent") is None
        assert generated.action_for(child_id).action_type is ActionType.RUN_GENERATOR
        assert worker_once(tmp_path, "chain-child-generate").status == "completed"

        evaluated = reconcile_once(tmp_path, store, include_worktrees=False)
        assert evaluated.action_for("chain-parent") is None
        assert evaluated.action_for(child_id).action_type is ActionType.RUN_EVALUATOR
        assert worker_once(tmp_path, "chain-child-evaluate").status == "completed"

        aggregate = reconcile_once(tmp_path, store, include_worktrees=False)
        assert aggregate.action_for(child_id) is None
        assert aggregate.action_for("chain-parent").action_type is ActionType.RUN_PLANNER
        assert worker_once(tmp_path, "chain-parent-aggregate").status == "completed"

    final = legacy.load_run(tmp_path, "chain-parent")
    assert final["phase"] == "planning"
    assert final["next_action"] == "run_parent_planner"
    assert final["aggregate_acceptance"]["passed"] == 1
    assert final["child_run_ids"] == [child_id]


@pytest.mark.parametrize("cutpoint", ["run", "planner", "all"])
def test_demand_parent_retry_completes_and_adopts_orphan_child_at_each_cutpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cutpoint: str
) -> None:
    from scripts.loop_supervisor import worker

    _init_git_repo(tmp_path)
    run_id = f"crash-parent-{cutpoint}"
    _create_demand_parent(tmp_path, run_id)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            run_id
        )
    assert action is not None
    parent_path = tmp_path / ".codex/loop-runs" / run_id / "run.json"
    parent_before = parent_path.read_bytes()
    original_create = legacy._create_child_run
    original_write = legacy.write_json_file
    child_id = f"{run_id}-child-001"
    child_dir = tmp_path / ".codex/loop-runs" / child_id

    def crash_after_child(*args: object, **kwargs: object):
        original_create(*args, **kwargs)
        raise SystemExit(17)

    def crash_after_artifact(path: Path, payload: dict[str, object]):
        written = original_write(path, payload)
        if cutpoint == "run" and path == child_dir / "run.json":
            raise SystemExit(17)
        if cutpoint == "planner" and path == child_dir / "planner-output.json":
            raise SystemExit(17)
        return written

    if cutpoint == "all":
        monkeypatch.setattr(legacy, "_create_child_run", crash_after_child)
    else:
        monkeypatch.setattr(legacy, "write_json_file", crash_after_artifact)
    with pytest.raises(SystemExit, match="17"):
        worker.worker_once(tmp_path, f"crashing-parent-worker-{cutpoint}")

    child_path = child_dir / "run.json"
    if cutpoint == "all":
        observed_child = legacy.load_run(tmp_path, child_id)
        observed_child["observed_at"] = "2026-07-15T00:00:00Z"
        legacy.save_run(tmp_path, observed_child)
    child_before = child_path.read_bytes()
    assert parent_path.read_bytes() == parent_before
    assert (child_dir / "planner-output.json").exists() is (cutpoint != "run")
    assert (child_dir / "task-contract.json").exists() is (cutpoint == "all")

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        orphan_reconcile = reconcile_once(
            tmp_path, store, include_worktrees=False
        )
        assert orphan_reconcile.action_for(child_id) is None
        store._connection.execute(
            """
            UPDATE actions
            SET status = 'pending', lease_owner = '', lease_expires_at = '',
                lease_heartbeat_at = ''
            WHERE action_id = ?
            """,
            (action.action_id,),
        )

    monkeypatch.setattr(legacy, "_create_child_run", original_create)
    monkeypatch.setattr(legacy, "write_json_file", original_write)
    retried = worker.worker_once(tmp_path, f"retry-parent-worker-{cutpoint}")

    assert retried.status == "completed"
    parent = legacy.load_run(tmp_path, run_id)
    assert parent["phase"] == "child_running"
    assert parent["current_child_run_id"] == child_id
    assert parent["child_run_ids"] == [child_id]
    assert child_path.read_bytes() == child_before
    child = legacy.load_run(tmp_path, child_id)
    parent_planner = legacy.read_json_file(
        tmp_path / ".codex/loop-runs" / run_id / "planner-output.json"
    )
    child_task = parent_planner["next_child_task"]
    planner = legacy.read_json_file(child_dir / "planner-output.json")
    contract = legacy.read_json_file(child_dir / "task-contract.json")
    assert planner == legacy._demand_child_planner_payload(child, child_task)
    assert contract == legacy._demand_child_task_contract(child, child_task)
    plan_events = [
        json.loads(line)
        for line in (child_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert sum(
        event["actor"] == "planner" and event["event_type"] == "plan"
        for event in plan_events
    ) == 1
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        converged = reconcile_once(tmp_path, store, include_worktrees=False)
        assert converged.action_for(child_id).action_type is ActionType.RUN_GENERATOR
        child_result = worker.worker_once(
            tmp_path, f"child-after-adopt-{cutpoint}"
        )
    assert child_result.status == "completed"
    assert legacy.load_run(tmp_path, child_id)["phase"] == "evaluating"


@pytest.mark.parametrize("corruption", ["malformed", "conflict"])
def test_demand_parent_retry_never_overwrites_invalid_existing_child_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    from scripts.loop_supervisor import worker

    _init_git_repo(tmp_path)
    run_id = f"artifact-parent-{corruption}"
    _create_demand_parent(tmp_path, run_id)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            run_id
        )
    original_write = legacy.write_json_file
    child_dir = tmp_path / ".codex/loop-runs" / f"{run_id}-child-001"

    def crash_after_planner(path: Path, payload: dict[str, object]):
        written = original_write(path, payload)
        if path == child_dir / "planner-output.json":
            raise SystemExit(19)
        return written

    monkeypatch.setattr(legacy, "write_json_file", crash_after_planner)
    with pytest.raises(SystemExit):
        worker.worker_once(tmp_path, f"artifact-crash-{corruption}")

    planner_path = child_dir / "planner-output.json"
    if corruption == "malformed":
        planner_path.write_text("{malformed\n", encoding="utf-8")
    else:
        planner = legacy.read_json_file(planner_path)
        planner["title"] = "conflicting child identity"
        original_write(planner_path, planner)
    artifact_before = planner_path.read_bytes()
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store._connection.execute(
            """
            UPDATE actions
            SET status = 'pending', lease_owner = '', lease_expires_at = '',
                lease_heartbeat_at = ''
            WHERE action_id = ?
            """,
            (action.action_id,),
        )
    monkeypatch.setattr(legacy, "write_json_file", original_write)

    result = worker.worker_once(tmp_path, f"artifact-retry-{corruption}")

    assert result.status == "failed"
    assert planner_path.read_bytes() == artifact_before
    assert not (child_dir / "task-contract.json").exists()


def test_demand_parent_retry_rejects_orphan_child_identity_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    _init_git_repo(tmp_path)
    _create_demand_parent(tmp_path, "identity-parent")
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            "identity-parent"
        )
    original_create = legacy._create_child_run

    def crash_after_child(*args: object, **kwargs: object):
        original_create(*args, **kwargs)
        raise SystemExit(18)

    monkeypatch.setattr(legacy, "_create_child_run", crash_after_child)
    with pytest.raises(SystemExit):
        worker.worker_once(tmp_path, "identity-crash-worker")

    child_path = tmp_path / ".codex/loop-runs/identity-parent-child-001/run.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["parent_run_id"] = "different-parent"
    child_path.write_text(json.dumps(child) + "\n", encoding="utf-8")
    tampered = child_path.read_bytes()
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store._connection.execute(
            """
            UPDATE actions
            SET status = 'pending', lease_owner = '', lease_expires_at = '',
                lease_heartbeat_at = ''
            WHERE action_id = ?
            """,
            (action.action_id,),
        )
    monkeypatch.setattr(legacy, "_create_child_run", original_create)

    result = worker.worker_once(tmp_path, "identity-retry-worker")

    assert result.status == "failed"
    assert result.result_class in {
        ActionResultClass.POLICY_BLOCK.value,
        ActionResultClass.TERMINAL_FAILURE.value,
    }
    assert child_path.read_bytes() == tampered


@pytest.mark.parametrize(
    "conflict",
    ["phase", "next_action", "attempts", "cleanup", "limits", "baseline"],
)
def test_demand_parent_retry_rejects_schema_valid_orphan_state_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conflict: str
) -> None:
    from scripts.loop_supervisor import worker

    _init_git_repo(tmp_path)
    run_id = f"state-parent-{conflict}"
    _create_demand_parent(tmp_path, run_id)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            run_id
        )
    original_create = legacy._create_child_run

    def crash_after_child(*args: object, **kwargs: object):
        original_create(*args, **kwargs)
        raise SystemExit(20)

    monkeypatch.setattr(legacy, "_create_child_run", crash_after_child)
    with pytest.raises(SystemExit):
        worker.worker_once(tmp_path, f"state-crash-{conflict}")

    child_id = f"{run_id}-child-001"
    child_path = tmp_path / ".codex/loop-runs" / child_id / "run.json"
    child = legacy.load_run(tmp_path, child_id)
    if conflict == "phase":
        child["phase"] = "cleanup"
        child["next_action"] = "run_cleanup"
    elif conflict == "next_action":
        child["next_action"] = "repair_child"
    elif conflict == "attempts":
        child["attempts"]["generator"] = 1
    elif conflict == "cleanup":
        child["cleanup"]["retained_artifacts"] = ["generated/conflict.txt"]
    elif conflict == "limits":
        child["limits"]["max_tasks_per_run"] += 1
    else:
        child["baseline_dirty_paths"] = ["generated/conflict.txt"]
    legacy.save_run(tmp_path, child)
    tampered = child_path.read_bytes()

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        orphan = reconcile_once(tmp_path, store, include_worktrees=False)
        assert orphan.action_for(child_id) is None
        store._connection.execute(
            """
            UPDATE actions
            SET status = 'pending', lease_owner = '', lease_expires_at = '',
                lease_heartbeat_at = ''
            WHERE action_id = ?
            """,
            (action.action_id,),
        )
    monkeypatch.setattr(legacy, "_create_child_run", original_create)

    result = worker.worker_once(tmp_path, f"state-retry-{conflict}")

    assert result.status == "failed"
    assert result.result_class in {
        ActionResultClass.POLICY_BLOCK.value,
        ActionResultClass.TERMINAL_FAILURE.value,
    }
    assert child_path.read_bytes() == tampered
    parent = legacy.load_run(tmp_path, run_id)
    assert parent["phase"] == "planning"
    assert parent["current_child_run_id"] == ""
    assert parent["child_run_ids"] == []
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        still_orphan = reconcile_once(tmp_path, store, include_worktrees=False)
    assert still_orphan.action_for(child_id) is None


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

    generated = legacy._run_bounded_generator(
        tmp_path,
        _phase_request(
            "autonomous-run",
            "generating",
            ActionType.RUN_GENERATOR,
            action_id="setup-generator",
        ),
    )
    evaluated = legacy._run_bounded_evaluator(
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


def test_bounded_worker_commit_fails_closed_when_git_status_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="autonomous-knowledge",
        requirement="Fail closed on unavailable Git ownership evidence",
        run_id="git-status-failure",
        domain="fixture",
        confirm=True,
    )
    run = legacy.load_run(tmp_path, "git-status-failure")
    run["phase"] = "generating"
    run["next_action"] = "run_autonomous_generator"
    run["task_id"] = "git-status-failure-task"
    legacy.save_run(tmp_path, run)
    generated = legacy._run_bounded_generator(
        tmp_path,
        _phase_request(
            "git-status-failure",
            "generating",
            ActionType.RUN_GENERATOR,
            action_id="git-status-setup-generator",
        ),
    )
    evaluated = legacy._run_bounded_evaluator(
        tmp_path,
        _phase_request(
            "git-status-failure",
            "evaluating",
            ActionType.RUN_EVALUATOR,
            action_id="git-status-setup-evaluator",
        ),
    )
    hygienic = legacy._run_bounded_artifact_hygiene(
        tmp_path,
        _phase_request(
            "git-status-failure",
            "artifact_hygiene",
            ActionType.RUN_ARTIFACT_HYGIENE,
            action_id="git-status-setup-hygiene",
        ),
    )
    assert generated.result_class is ActionResultClass.SUCCESS
    assert evaluated.result_class is ActionResultClass.SUCCESS
    assert hygienic.result_class is ActionResultClass.SUCCESS

    original_run = legacy.subprocess.run

    def fail_status(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["git", "status"]:
            return subprocess.CompletedProcess(
                args, 128, stdout="", stderr="fatal: ownership unavailable\n"
            )
        return original_run(args, **kwargs)

    monkeypatch.setattr(legacy.subprocess, "run", fail_status)
    result = legacy._run_bounded_commit(
        tmp_path,
        _phase_request(
            "git-status-failure",
            "cleanup",
            ActionType.COMMIT,
            action_id="git-status-commit",
        ),
    )

    assert result.result_class is not ActionResultClass.SUCCESS
    assert "git status failed" in result.summary


@pytest.mark.parametrize(
    ("gate", "expected_next_action", "evidence_name"),
    [
        ("denylist", "inspect_autonomous_scope", "autonomous-scope-result.json"),
        ("supply_chain", "inspect_supply_chain", "supply-chain-result.json"),
        ("required_evidence", "inspect_required_evidence", "required-evidence-result.json"),
        ("unexpected_dirty", "inspect_autonomous_dirty_paths", "dirty-paths-result.json"),
        ("baseline_dirty", "inspect_autonomous_dirty_paths", "dirty-paths-result.json"),
        ("commit_provenance", "inspect_autonomous_commit", "commit-result.json"),
        ("commit_path_provenance", "inspect_autonomous_commit", "commit-result.json"),
    ],
)
def test_bounded_worker_commit_enforces_active_safety_gates(
    tmp_path: Path,
    gate: str,
    expected_next_action: str,
    evidence_name: str,
) -> None:
    from scripts.loop_supervisor.worker import worker_once

    run_id = f"gate-{gate.replace('_', '-')}"
    generator_driver = {
        "denylist": "fake-denylist",
        "supply_chain": "fake-dependency",
    }.get(gate, "fake")
    run_updates = (
        {"required_evidence": ["trusted service availability evidence"]}
        if gate == "required_evidence"
        else None
    )
    generator_result = _prepare_autonomous_commit_gate(
        tmp_path,
        run_id,
        generator_driver=generator_driver,
        run_updates=run_updates,
    )
    changed_paths = [str(path) for path in generator_result["changed_paths"]]
    run_dir = legacy.run_dir_for(tmp_path, run_id)

    if gate == "unexpected_dirty":
        (tmp_path / "unexpected.txt").write_text("not declared\n", encoding="utf-8")
    elif gate == "baseline_dirty":
        run = legacy.load_run(tmp_path, run_id)
        run["baseline_dirty_paths"] = [f" M {changed_paths[0]}"]
        legacy.save_run(tmp_path, run)
    elif gate in {"commit_provenance", "commit_path_provenance"}:
        commit_paths = list(changed_paths)
        if gate == "commit_path_provenance":
            rogue = tmp_path / "rogue.txt"
            rogue.write_text("undeclared commit content\n", encoding="utf-8")
            commit_paths.append("rogue.txt")
        subprocess.run(
            ["git", "add", "--", *commit_paths],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "test: generator supplied commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        generator_result["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        legacy.write_json_file(run_dir / "generator-result.json", generator_result)

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            run_id
        )
    assert action is not None
    assert action.action_type is ActionType.COMMIT

    result = worker_once(tmp_path, f"worker-{gate}")

    assert result.status == "failed"
    run = legacy.load_run(tmp_path, run_id)
    assert run["phase"] == "stopped_blocked"
    assert run["next_action"] == expected_next_action
    evidence = legacy.read_json_file(run_dir / evidence_name)
    if gate == "denylist":
        assert evidence["allowed"] is False
        assert ".env" in evidence["denied_paths"]
    elif gate == "supply_chain":
        assert evidence["allowed"] is False
        assert "requirements.txt" in evidence["dependency_paths"]
    elif gate == "required_evidence":
        assert evidence["status"] == "blocked"
    elif gate == "unexpected_dirty":
        assert "unexpected.txt" in evidence["unexpected_paths"]
    elif gate == "baseline_dirty":
        assert changed_paths[0] in evidence["baseline_changed_paths"]
    elif gate == "commit_provenance":
        assert "without verified orchestrator run-state evidence" in evidence["error"]
    else:
        assert "undeclared paths: rogue.txt" in evidence["error"]


def test_bounded_worker_commit_checks_scope_before_supply_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.harness_loop_autonomous import (
        ScopeCheckResult,
        SupplyChainCheckResult,
    )
    from scripts.loop_supervisor.worker import worker_once

    run_id = "gate-order"
    _prepare_autonomous_commit_gate(
        tmp_path, run_id, generator_driver="fake-dependency"
    )
    calls: list[str] = []

    def scope(*_args: object, **_kwargs: object) -> ScopeCheckResult:
        calls.append("scope")
        return ScopeCheckResult(True, ["requirements.txt"], [], [], [])

    def supply_chain(*_args: object, **_kwargs: object) -> SupplyChainCheckResult:
        calls.append("supply_chain")
        return SupplyChainCheckResult(
            False, ["requirements.txt"], ["missing dependency evidence"]
        )

    monkeypatch.setattr(legacy, "check_autonomous_scope", scope)
    monkeypatch.setattr(legacy, "check_supply_chain", supply_chain)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
            run_id
        )
    assert action is not None
    assert action.action_type is ActionType.COMMIT

    result = worker_once(tmp_path, "worker-gate-order")

    assert result.status == "failed"
    assert calls == ["scope", "supply_chain"]
    assert legacy.load_run(tmp_path, run_id)["next_action"] == "inspect_supply_chain"


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
    reconcile_acquired = threading.Event()
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
            reconcile_acquired.set()
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
    assert not reconcile_acquired.wait(timeout=0.1)
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
    original_planner = legacy._run_planner

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
    monkeypatch.setattr(legacy, "_run_planner", observed_planner)
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
    assert not handler_entered.wait(timeout=0.1)
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
    renewed = threading.Event()
    original_renew = SupervisorStore.renew_lease

    def execute(_request: ActionRequest, _root: Path) -> ActionResult:
        entered.set()
        assert release.wait(timeout=3)
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)
    monkeypatch.setattr(worker, "HEARTBEAT_SECONDS", 0.05)

    def observed_renew(self: SupervisorStore, *args: object, **kwargs: object) -> bool:
        result = original_renew(self, *args, **kwargs)
        renewed.set()
        return result

    monkeypatch.setattr(SupervisorStore, "renew_lease", observed_renew)
    thread = threading.Thread(target=worker.worker_once, args=(tmp_path, "worker-heartbeat"))
    thread.start()
    assert entered.wait(timeout=2)

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        before = next(row for row in store.fetch_all("actions") if row["action_id"] == action.action_id)
    assert renewed.wait(timeout=2)
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

    run_path = tmp_path / ".codex" / "loop-runs" / action.run_id / "run.json"
    before = run_path.read_bytes()

    def crash(request: ActionRequest, root: Path) -> ActionResult:
        staged = legacy.load_run(root, request.run_id)
        staged["phase"] = "generating"
        staged["next_action"] = "run_autonomous_generator"
        legacy.save_run(root, staged)
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
    assert run_path.read_bytes() == before


def test_successful_worker_stages_legacy_saves_and_commits_one_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    run_path = tmp_path / ".codex" / "loop-runs" / action.run_id / "run.json"
    before_stat = run_path.stat()

    def execute(request: ActionRequest, root: Path) -> ActionResult:
        staged = legacy.load_run(root, request.run_id)
        staged["phase"] = "generating"
        legacy.save_run(root, staged)
        staged = legacy.load_run(root, request.run_id)
        staged["next_action"] = "run_autonomous_generator"
        legacy.save_run(root, staged)
        assert os.stat(run_path).st_ino == before_stat.st_ino
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)

    result = worker.worker_once(tmp_path, "transaction-worker")

    assert result.status == "completed"
    persisted = json.loads(run_path.read_text(encoding="utf-8"))
    assert persisted["phase"] == "generating"
    assert persisted["next_action"] == "run_autonomous_generator"
    assert persisted["state_revision"] == 1


def test_worker_executes_worktree_action_without_writing_main_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    worktree = tmp_path / ".worktrees" / "feature"
    run_id = "worktree-run"
    run_dir = worktree / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True)
    initial = _valid_run_payload(worktree, run_id)
    (run_dir / "run.json").write_text(json.dumps(initial) + "\n", encoding="utf-8")
    request = ActionRequest(
        action_id="worktree-action",
        run_id=run_id,
        run_revision=0,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="worktree-action-key",
        repo_relative_root=".worktrees/feature",
        next_action="run_autonomous_planner",
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.upsert_run_projection(
            {
                "run_id": run_id,
                "policy": request.policy,
                "phase": request.phase,
                "status": "active",
                "revision": 0,
            }
        )
        store.enqueue_action(request)

    def execute(action: ActionRequest, execution_root: Path) -> ActionResult:
        assert execution_root == worktree.resolve()
        run = legacy.load_run(execution_root, action.run_id)
        run["phase"] = "generating"
        run["next_action"] = "run_autonomous_generator"
        legacy.save_run(execution_root, run)
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)

    result = worker.worker_once(tmp_path, "worktree-worker")

    assert result.status == "completed"
    assert not (tmp_path / ".codex" / "loop-runs" / run_id).exists()
    persisted = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert persisted["state_revision"] == 1
    assert persisted["phase"] == "generating"


def test_heartbeat_exception_loses_lease_and_prevents_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    heartbeat_failed = threading.Event()

    def explode_heartbeat(*_args: object, **_kwargs: object) -> bool:
        heartbeat_failed.set()
        raise OSError("heartbeat transport failed")

    def execute(_request: ActionRequest, _root: Path) -> ActionResult:
        assert heartbeat_failed.wait(timeout=2)
        return _success()

    monkeypatch.setattr(SupervisorStore, "renew_lease", explode_heartbeat)
    monkeypatch.setattr(worker, "execute_action", execute)
    monkeypatch.setattr(worker, "HEARTBEAT_SECONDS", 0.01)

    result = worker.worker_once(tmp_path, "heartbeat-failure-worker")

    assert result.status == "lease_lost"
    assert "heartbeat" in result.summary
    assert result.recovery_evidence
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        assert store.get_action(action.action_id).status == "leased"
        assert store.fetch_all("action_attempts") == []


def test_heartbeat_failure_during_shutdown_prevents_commit_and_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    run_path = tmp_path / ".codex/loop-runs" / action.run_id / "run.json"
    before = run_path.read_bytes()

    def fail_when_worker_stops(
        _root: Path,
        _action_id: str,
        _worker_id: str,
        finished: threading.Event,
        lease_lost: threading.Event,
        heartbeat_errors: list[BaseException],
    ) -> None:
        assert finished.wait(timeout=2)
        heartbeat_errors.append(OSError("heartbeat failed during shutdown"))
        lease_lost.set()

    def execute(request: ActionRequest, root: Path) -> ActionResult:
        run = legacy.load_run(root, request.run_id)
        run["phase"] = "generating"
        run["next_action"] = "run_autonomous_generator"
        legacy.save_run(root, run)
        return _success()

    monkeypatch.setattr(worker, "_heartbeat", fail_when_worker_stops)
    monkeypatch.setattr(worker, "execute_action", execute)

    result = worker.worker_once(tmp_path, "shutdown-heartbeat-worker")

    assert result.status == "lease_lost"
    assert result.recovery_evidence
    assert run_path.read_bytes() == before
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        assert store.get_action(action.action_id).status == "leased"
        assert store.fetch_all("action_attempts") == []


def test_synchronous_final_lease_renew_failure_prevents_commit_and_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    run_path = tmp_path / ".codex/loop-runs" / action.run_id / "run.json"
    before = run_path.read_bytes()

    def quiet_heartbeat(
        _root: Path,
        _action_id: str,
        _worker_id: str,
        finished: threading.Event,
        _lease_lost: threading.Event,
        _heartbeat_errors: list[BaseException],
    ) -> None:
        assert finished.wait(timeout=2)

    def fail_final_renew(*_args: object, **_kwargs: object) -> bool:
        raise OSError("final lease renew failed")

    def execute(request: ActionRequest, root: Path) -> ActionResult:
        run = legacy.load_run(root, request.run_id)
        run["phase"] = "generating"
        run["next_action"] = "run_autonomous_generator"
        legacy.save_run(root, run)
        return _success()

    monkeypatch.setattr(worker, "_heartbeat", quiet_heartbeat)
    monkeypatch.setattr(worker, "execute_action", execute)
    monkeypatch.setattr(SupervisorStore, "renew_lease", fail_final_renew)

    result = worker.worker_once(tmp_path, "final-renew-worker")

    assert result.status == "lease_lost"
    assert result.recovery_evidence
    assert run_path.read_bytes() == before
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        assert store.get_action(action.action_id).status == "leased"
        assert store.fetch_all("action_attempts") == []


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError("deadline"), ActionResultClass.RETRYABLE_FAILURE),
        (subprocess.SubprocessError("child failed"), ActionResultClass.RETRYABLE_FAILURE),
        (OSError("Could not resolve host"), ActionResultClass.RETRYABLE_FAILURE),
        (PermissionError("scope denied"), ActionResultClass.POLICY_BLOCK),
        (ValueError("corrupt run state"), ActionResultClass.TERMINAL_FAILURE),
        (ValueError("invalid transport schema"), ActionResultClass.TERMINAL_FAILURE),
    ],
)
def test_bounded_failure_classifier_preserves_result_semantics(error, expected) -> None:
    from scripts.loop_supervisor.worker import classify_bounded_failure

    result = classify_bounded_failure(error, action_id="action-1")

    assert result.result_class is expected


def test_failure_classifier_reports_valid_partial_artifact(tmp_path: Path) -> None:
    from scripts.loop_supervisor.worker import BoundedFailure, classify_bounded_failure

    artifact = tmp_path / "partial.json"
    artifact.write_text("{}\n", encoding="utf-8")
    error = BoundedFailure(
        "generator timed out",
        cause=TimeoutError("deadline"),
        artifact_paths=("partial.json",),
        checkpoint="generator-output",
    )

    result = classify_bounded_failure(
        error, action_id="action-1", execution_root=tmp_path
    )

    assert result.result_class is ActionResultClass.RECOVERABLE_PARTIAL
    assert result.artifact_paths == ("partial.json",)
    assert result.checkpoint == "generator-output"


@pytest.mark.parametrize(
    "cause",
    [
        PermissionError("permission denied after partial output"),
        RuntimeError("policy violation after partial output"),
        RuntimeError("secret exposure after partial output"),
        RuntimeError("scope violation after partial output"),
        RuntimeError("symlink ownership changed after partial output"),
    ],
)
def test_policy_failure_always_precedes_recoverable_partial(
    tmp_path: Path, cause: BaseException
) -> None:
    from scripts.loop_supervisor.worker import BoundedFailure, classify_bounded_failure

    artifact = tmp_path / "partial.json"
    artifact.write_text("{}\n", encoding="utf-8")
    result = classify_bounded_failure(
        BoundedFailure(
            "partial output is not safe",
            cause=cause,
            artifact_paths=("partial.json",),
            checkpoint="generator",
        ),
        action_id="policy-partial",
        execution_root=tmp_path,
    )

    assert result.result_class is ActionResultClass.POLICY_BLOCK
    assert result.artifact_paths == ()
    assert result.checkpoint == ""


def test_orchestrator_policy_failure_precedes_valid_partial_artifact(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / ".codex/loop-runs/policy-partial"
    run_dir.mkdir(parents=True)
    legacy.write_json_file(
        run_dir / "generator-result.json",
        {
            "task_id": "task-1",
            "status": "implemented",
            "changed_paths": [],
            "commit": "",
            "verify_commands": [],
            "verify_results": [],
            "artifacts": [],
            "cleanup_required": False,
            "notes": "unsafe partial",
        },
    )
    request = ActionRequest(
        action_id="policy-partial",
        run_id="policy-partial",
        run_revision=0,
        policy="demand_development",
        phase="generating",
        action_type=ActionType.RUN_GENERATOR,
        idempotency_key="policy-partial-key",
    )

    result = legacy._bounded_failure(
        request,
        "generator",
        PermissionError("scope permission denied"),
        started_at="2026-01-01T00:00:00Z",
        repo_root=tmp_path,
    )

    assert result.result_class is ActionResultClass.POLICY_BLOCK
    assert result.artifact_paths == ()


def test_worker_and_orchestrator_use_the_same_failure_classifier() -> None:
    from scripts.loop_supervisor import worker
    from scripts.loop_supervisor.failures import classify_bounded_failure

    assert worker.classify_bounded_failure is classify_bounded_failure
    assert legacy.classify_bounded_failure is classify_bounded_failure


def test_transaction_validates_every_staged_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)

    def execute(request: ActionRequest, root: Path) -> ActionResult:
        invalid = legacy.load_run(root, request.run_id)
        invalid.pop("limits")
        with pytest.raises(ValueError, match="limits"):
            legacy.save_run(root, invalid)
        unchanged = legacy.load_run(root, request.run_id)
        assert "limits" in unchanged
        unchanged["phase"] = "generating"
        unchanged["next_action"] = "run_autonomous_generator"
        legacy.save_run(root, unchanged)
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)

    result = worker.worker_once(tmp_path, "staged-validation-worker")

    assert result.status == "completed"
    persisted = legacy.load_run(tmp_path, action.run_id)
    assert persisted["phase"] == "generating"


def test_transaction_validates_final_staged_payload_before_atomic_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    run_path = tmp_path / ".codex/loop-runs" / action.run_id / "run.json"
    before = run_path.read_bytes()

    def corrupt_staged_payload(
        _request: ActionRequest, _root: Path
    ) -> ActionResult:
        transaction = legacy._BOUNDED_RUN_TRANSACTION.get()
        assert transaction is not None
        transaction.staged_payload.pop("limits")
        return _success()

    monkeypatch.setattr(worker, "execute_action", corrupt_staged_payload)

    result = worker.worker_once(tmp_path, "final-validation-worker")

    assert result.status == "failed"
    assert result.result_class == ActionResultClass.TERMINAL_FAILURE.value
    assert run_path.read_bytes() == before


def test_bounded_primitive_timeout_with_valid_generator_result_is_recoverable_partial(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / ".codex" / "loop-runs" / "partial-run"
    run_dir.mkdir(parents=True)
    legacy.write_json_file(
        run_dir / "generator-result.json",
        {
            "task_id": "task-1",
            "status": "implemented",
            "changed_paths": [],
            "commit": "",
            "verify_commands": [],
            "verify_results": [],
            "artifacts": [],
            "cleanup_required": False,
            "notes": "partial result survived timeout",
            "skill_invocations": [],
        },
    )
    request = ActionRequest(
        action_id="partial-action",
        run_id="partial-run",
        run_revision=0,
        policy="demand_development",
        phase="generating",
        action_type=ActionType.RUN_GENERATOR,
        idempotency_key="partial-action-key",
    )

    result = legacy._bounded_failure(
        request,
        "generator",
        TimeoutError("generator timed out"),
        started_at="2026-01-01T00:00:00Z",
        repo_root=tmp_path,
    )

    assert result.result_class is ActionResultClass.RECOVERABLE_PARTIAL
    assert result.artifact_paths == (
        ".codex/loop-runs/partial-run/generator-result.json",
    )
    assert result.checkpoint == "generator"


def test_recovery_evidence_hashes_unsafe_action_id_and_rejects_symlink(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor import worker

    request = ActionRequest(
        action_id="../../unsafe action",
        run_id="safe-run",
        run_revision=0,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="unsafe-action-key",
    )
    run_dir = tmp_path / ".codex" / "loop-runs" / "safe-run"
    run_dir.mkdir(parents=True)
    evidence_name = worker._evidence_filename("worker-completion-failure", request.action_id)
    outside = tmp_path / "outside.json"
    outside.write_text("untouched\n", encoding="utf-8")
    (run_dir / evidence_name).symlink_to(outside)

    with pytest.raises(OSError):
        worker._write_recovery_evidence(
            tmp_path, request, "worker-1", RuntimeError("token=secret-value")
        )

    assert outside.read_text(encoding="utf-8") == "untouched\n"


def test_run_directory_replacement_blocks_commit_without_state_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    action = _seed_action(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / action.run_id
    original = run_dir / "run.json"
    before = original.read_bytes()
    outside = tmp_path / "outside-run"
    outside.mkdir()
    outside_run = outside / "run.json"
    outside_run.write_text('{"outside":true}\n', encoding="utf-8")
    displaced = run_dir.with_name(f"{run_dir.name}-displaced")

    def replace_directory(request: ActionRequest, root: Path) -> ActionResult:
        staged = legacy.load_run(root, request.run_id)
        staged["phase"] = "generating"
        staged["next_action"] = "run_autonomous_generator"
        legacy.save_run(root, staged)
        run_dir.rename(displaced)
        run_dir.symlink_to(outside, target_is_directory=True)
        return _success()

    monkeypatch.setattr(worker, "execute_action", replace_directory)

    result = worker.worker_once(tmp_path, "replacement-worker")

    assert result.status == "failed"
    assert result.result_class == ActionResultClass.POLICY_BLOCK.value
    assert (displaced / "run.json").read_bytes() == before
    assert outside_run.read_text(encoding="utf-8") == '{"outside":true}\n'


def test_repository_mutation_lock_serializes_different_runs(tmp_path: Path) -> None:
    with acquire_repository_mutation_lock(tmp_path, owner="worker-a") as first:
        assert first["owner"] == "worker-a"
        with pytest.raises(RunLockBusy) as raised:
            with acquire_repository_mutation_lock(tmp_path, owner="worker-b"):
                pass
    assert raised.value.run_id == "repository-mutation"
    assert raised.value.current_owner == "worker-a"


def test_repository_mutation_lock_is_shared_by_main_and_linked_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import worker

    main_action = _seed_action(tmp_path, action_id="main-action", run_id="main-run")
    worktree = tmp_path / ".worktrees/feature"
    run_id = "worktree-run"
    run_dir = worktree / ".codex/loop-runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(_valid_run_payload(worktree, run_id)) + "\n",
        encoding="utf-8",
    )
    worktree_action = ActionRequest(
        action_id="worktree-action",
        run_id=run_id,
        run_revision=0,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="worktree-action-key",
        repo_relative_root=".worktrees/feature",
        next_action="run_autonomous_planner",
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.upsert_run_projection(
            {
                "run_id": run_id,
                "policy": worktree_action.policy,
                "phase": worktree_action.phase,
                "status": "active",
                "revision": 0,
            }
        )
        store.enqueue_action(worktree_action)

    main_entered = threading.Event()
    release_main = threading.Event()
    calls: list[str] = []

    def execute(request: ActionRequest, _root: Path) -> ActionResult:
        calls.append(request.action_id)
        if request.action_id == main_action.action_id:
            main_entered.set()
            assert release_main.wait(timeout=3)
        return _success()

    monkeypatch.setattr(worker, "execute_action", execute)
    main_results: list[object] = []
    main_thread = threading.Thread(
        target=lambda: main_results.append(
            worker.worker_once(tmp_path, "main-mutation-worker")
        )
    )
    main_thread.start()
    assert main_entered.wait(timeout=2)

    worktree_result = worker.worker_once(tmp_path, "worktree-mutation-worker")
    release_main.set()
    main_thread.join(timeout=3)

    assert not main_thread.is_alive()
    assert main_results[0].status == "completed"
    assert worktree_result.status == "failed"
    assert worktree_result.result_class == ActionResultClass.RETRYABLE_FAILURE.value
    assert calls == [main_action.action_id]


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
