from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from scripts.loop_supervisor.models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
)
from scripts.loop_supervisor.reconciler import reconcile_once
from scripts.loop_supervisor.store import SupervisorStore
from scripts.harness_loop_contracts import (
    default_limits,
    read_json_file,
    validate_generator_result_payload,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 15, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


def migrated_store(tmp_path: Path, clock: FakeClock | None = None) -> SupervisorStore:
    store = SupervisorStore.open(tmp_path, clock=clock)
    store.migrate()
    return store


def episode_failures(store: SupervisorStore) -> list[dict[str, object]]:
    return [
        row
        for row in store.fetch_all("failures")
        if json.loads(row["resolution"]).get("kind") == "episode"
    ]


def recovery_run() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "loop_lineage_id": "lineage-1",
        "task_id": "task-1",
        "policy": "autonomous_knowledge",
        "phase": "generating",
        "next_action": "run_autonomous_generator",
        "state_revision": 4,
    }


def failed_result(attempt: int, *, action_type: ActionType = ActionType.RUN_GENERATOR) -> dict[str, object]:
    return {
        "attempt_id": f"attempt-{attempt}",
        "action_id": "action-generator",
        "action_type": action_type.value,
        "result_class": "retryable_failure",
        "error_class": "RuntimeError",
        "summary": "Selected model is at capacity",
    }


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Selected model is at capacity", "model_capacity"),
        ("stream disconnected before completion", "sse_disconnect"),
        ("Temporary failure in name resolution", "dns_failure"),
        ("fatal: Unable to create '.git/index.lock'", "git_lock"),
    ],
)
def test_classify_retryable_errors(message: str, expected: str) -> None:
    from scripts.loop_supervisor.recovery import classify_attempt_failure

    classification = classify_attempt_failure({"stderr": message})

    assert classification.error_class == expected
    assert classification.retryable is True


def test_three_failures_then_one_alternate_without_user_decision(tmp_path: Path) -> None:
    from scripts.loop_supervisor.recovery import plan_recovery

    clock = FakeClock()
    store = migrated_store(tmp_path, clock)
    plans = [
        plan_recovery(store, recovery_run(), failed_result(attempt), jitter=lambda: 0.0)
        for attempt in range(1, 4)
    ]

    assert [plan.tier for plan in plans] == [1, 1, 2]
    assert [plan.action_type for plan in plans] == [
        ActionType.RUN_GENERATOR,
        ActionType.RUN_GENERATOR,
        ActionType.RECOVER_GENERATOR_RESULT,
    ]
    assert plans[-1].strategy == "reconstruct_result_envelope"
    assert plans[-1].episode_number == 1
    assert all(
        value in plans[-1].failure_key
        for value in (
            "lineage-1",
            "run-1",
            "task-1",
            "run_generator",
            "model_capacity",
        )
    )
    assert store.fetch_all("user_decisions") == []

    failures = episode_failures(store)
    assert len(failures) == 1
    assert failures[0]["occurrence_count"] == 3
    state = json.loads(failures[0]["resolution"])
    assert state["alternate_used"] is True
    assert state["episode_attempts"] == 3


def test_alternating_error_classes_share_one_action_recovery_episode(tmp_path: Path) -> None:
    from scripts.loop_supervisor.recovery import plan_recovery

    store = migrated_store(tmp_path)
    results = [
        {**failed_result(1), "summary": "Selected model is at capacity"},
        {
            **failed_result(2),
            "error_class": "OSError",
            "summary": "Temporary failure in name resolution",
        },
        {**failed_result(3), "summary": "Selected model is at capacity"},
    ]

    plans = [
        plan_recovery(store, recovery_run(), result, jitter=lambda: 0.0)
        for result in results
    ]

    assert [plan.tier for plan in plans] == [1, 1, 2]
    assert len({plan.failure_key for plan in plans}) == 1
    rows = store.fetch_all("failures")
    episode_rows = [
        row for row in rows if json.loads(row["resolution"]).get("kind") == "episode"
    ]
    class_rows = {
        row["error_class"]: row
        for row in rows
        if json.loads(row["resolution"]).get("kind") == "class_lifetime"
    }
    assert episode_rows[0]["occurrence_count"] == 3
    assert class_rows["model_capacity"]["occurrence_count"] == 2
    assert class_rows["dns_failure"]["occurrence_count"] == 1


def test_recoverable_partial_skips_retry_and_plans_recovery_action(tmp_path: Path) -> None:
    from scripts.loop_supervisor.recovery import plan_recovery

    store = migrated_store(tmp_path)
    result = failed_result(1)
    result["result_class"] = ActionResultClass.RECOVERABLE_PARTIAL.value

    plan = plan_recovery(store, recovery_run(), result, jitter=lambda: 0.0)

    assert plan.tier == 2
    assert plan.action_type is ActionType.RECOVER_GENERATOR_RESULT
    assert plan.strategy == "reconstruct_result_envelope"
    assert store.fetch_all("user_decisions") == []


def test_recovery_plan_uses_registry_owned_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.loop_supervisor.recovery as recovery
    from scripts.loop_supervisor.models import RecoveryTransitionRule

    observed: list[tuple[str, str, str, object]] = []

    def registry_transition(policy: str, phase: str, next_action: str, stage: object):
        observed.append((policy, phase, next_action, stage))
        return RecoveryTransitionRule(
            action_type=ActionType.REFOCUS_RUN,
            mutates_git=False,
            worker_executable=True,
            strategy="registry-test-strategy",
        )

    monkeypatch.setattr(recovery, "recovery_transition_for", registry_transition)
    store = migrated_store(tmp_path)
    result = failed_result(1)
    result["result_class"] = ActionResultClass.RECOVERABLE_PARTIAL.value

    plan = recovery.plan_recovery(store, recovery_run(), result, jitter=lambda: 0.0)

    assert observed
    assert plan.action_type is ActionType.REFOCUS_RUN
    assert plan.strategy == "registry-test-strategy"


def test_worker_rejects_recovery_override_without_registry_stage() -> None:
    from scripts.loop_supervisor.worker import _mutates_git

    request = ActionRequest(
        action_id="action-unsafe-override",
        run_id="run-1",
        run_revision=0,
        policy="autonomous_knowledge",
        phase="generating",
        action_type=ActionType.RECOVER_GENERATOR_RESULT,
        idempotency_key="unsafe-override",
        next_action="run_autonomous_generator",
        payload={
            "recovery_failure_key": "recovery:forged",
            "recovery_for_action_type": ActionType.RUN_GENERATOR.value,
        },
    )

    with pytest.raises(ValueError, match="registry"):
        _mutates_git(request)


def test_alternate_is_planned_once_then_reviewer_consumes_exhaustion(tmp_path: Path) -> None:
    from scripts.loop_supervisor.recovery import plan_recovery

    store = migrated_store(tmp_path)
    for attempt in range(1, 4):
        alternate = plan_recovery(store, recovery_run(), failed_result(attempt), jitter=lambda: 0.0)

    repeated = plan_recovery(store, recovery_run(), failed_result(3), jitter=lambda: 0.0)
    alternate_failure = {
        "attempt_id": "alternate-attempt-1",
        "action_id": "recover-generator",
        "action_type": ActionType.RECOVER_GENERATOR_RESULT.value,
        "result_class": "terminal_failure",
        "error_class": "partial_artifact_unprovable",
        "summary": "partial artifact recovery could not be proven",
        "recovery_failure_key": alternate.failure_key,
    }
    reviewer = plan_recovery(store, recovery_run(), alternate_failure, jitter=lambda: 0.0)

    assert repeated == alternate
    assert reviewer.tier == 3
    assert reviewer.action_type is ActionType.RUN_REVIEWER
    assert reviewer.strategy == "review_recovery_exhaustion"
    assert store.fetch_all("user_decisions") == []


def test_success_closes_episode_and_recurrence_starts_new_episode(tmp_path: Path) -> None:
    from scripts.loop_supervisor.recovery import plan_recovery

    store = migrated_store(tmp_path)
    first = plan_recovery(store, recovery_run(), failed_result(1), jitter=lambda: 0.0)
    closed = plan_recovery(
        store,
        recovery_run(),
        {
            "attempt_id": "attempt-success",
            "action_id": "action-generator",
            "action_type": ActionType.RUN_GENERATOR.value,
            "result_class": "success",
            "error_class": "",
            "summary": "generator completed",
        },
        jitter=lambda: 0.0,
    )
    recurrence = plan_recovery(store, recovery_run(), failed_result(2), jitter=lambda: 0.0)

    assert first.episode_number == 1
    assert closed.tier == 0
    assert recurrence.episode_number == 2
    failure = episode_failures(store)[0]
    assert failure["occurrence_count"] == 2
    state = json.loads(failure["resolution"])
    assert state["status"] == "open"
    assert state["episode_number"] == 2
    assert state["lifetime_count"] == 2


PARENT22_RUN_ID = "parent-22-structural-fixture"
PARENT22_TASK_ID = "parent-22-task"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "test: baseline"], cwd=root, check=True)


def seed_parent22_partial_fixture(root: Path) -> dict[str, object]:
    _init_git_repo(root)
    run_dir = root / ".codex" / "loop-runs" / PARENT22_RUN_ID
    run_dir.mkdir(parents=True)
    changed_path = "knowledge/parent-22.md"
    changed_file = root / changed_path
    changed_file.parent.mkdir(parents=True)
    changed_file.write_text("# Parent 22 fixture\n\nRecovered evidence.\n", encoding="utf-8")
    run = {
        "run_id": PARENT22_RUN_ID,
        "loop_lineage_id": "ai-infra-lineage",
        "policy": "autonomous_knowledge",
        "phase": "generating",
        "task_id": PARENT22_TASK_ID,
        "domain": "ai_infra",
        "branch": "fixture",
        "worktree": str(root.resolve()),
        "requirement": "Recover the parent-22 structural fixture",
        "constraints": [],
        "stop_conditions": ["secret exposure"],
        "baseline_dirty_paths": [],
        "allowed_paths": ["knowledge/**"],
        "denylist_paths": [".env", ".codex/secrets/**"],
        "manual_confirm_paths": [],
        "required_evidence": ["gap proof"],
        "attempts": {
            "planner": 1,
            "generator": 4,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
        },
        "limits": default_limits(),
        "last_result": "fail",
        "next_action": "run_autonomous_generator",
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
        "state_revision": 3,
    }
    _write_json(run_dir / "run.json", run)
    _write_json(
        run_dir / "planner-output.json",
        {
            "task_id": PARENT22_TASK_ID,
            "policy": "autonomous_knowledge",
            "task_kind": "autonomous_implementation_task",
            "title": "Parent 22 fixture",
            "goal": "Produce one scoped knowledge page",
            "non_goals": [],
            "allowed_paths": ["knowledge/**"],
            "denylist_paths": [".env", ".codex/secrets/**"],
            "verify_commands": ["python3 -m pytest -q fixture"],
            "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/fixture.json",
            "stop_conditions": ["secret exposure"],
            "next_planning_hint": "Evaluate independently",
        },
    )
    for attempt in (3, 4):
        stdout_path = run_dir / f"generator-attempt-{attempt}.stdout.log"
        stderr_path = run_dir / f"generator-attempt-{attempt}.stderr.log"
        stdout_path.write_text("bounded partial output\n", encoding="utf-8")
        stderr_path.write_text("operation timed out\n", encoding="utf-8")
        _write_json(
            run_dir / f"generator-attempt-{attempt}.json",
            {
                "run_id": PARENT22_RUN_ID,
                "role": "generator",
                "attempt": attempt,
                "started_at": f"2026-07-15T00:0{attempt}:00Z",
                "finished_at": f"2026-07-15T00:0{attempt}:30Z",
                "exit_code": 124,
                "status": "timeout",
                "prompt_path": str(run_dir / "generator-prompt.md"),
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "output_json_path": str(run_dir / "generator-result.json"),
                "diff_patch_path": "",
                "verify_log_paths": [],
            },
        )
    verify_dir = run_dir / "scenario-commands"
    verify_dir.mkdir()
    verify_stdout = verify_dir / "command-1.stdout.log"
    verify_stderr = verify_dir / "command-1.stderr.log"
    verify_stdout.write_text("1 passed\n", encoding="utf-8")
    verify_stderr.write_text("", encoding="utf-8")
    _write_json(
        run_dir / "scenario-command-results.json",
        {
            "status": "pass",
            "results": [
                {
                    "command": "python3 -m pytest -q fixture",
                    "cwd": str(root.resolve()),
                    "exit_code": 0,
                    "stdout_path": str(verify_stdout),
                    "stderr_path": str(verify_stderr),
                    "duration_seconds": 1,
                    "status": "pass",
                }
            ],
        },
    )
    gap_path = run_dir / "gap-proofs" / f"{PARENT22_TASK_ID}.json"
    _write_json(
        gap_path,
        {
            "task_id": PARENT22_TASK_ID,
            "layer": "runtime",
            "candidate": {
                "title": "Parent 22 fixture",
                "source_type": "paper",
                "identity_key": "fixture:parent-22",
            },
            "local_checks": {
                "raw_manifest_scan": "not present",
                "wiki_search": "not present",
                "domain_index_scan": "not present",
            },
            "gap_reason": "No existing fixture page",
            "planned_outputs": [changed_path],
        },
    )
    _write_json(
        run_dir / "required-evidence-manifest.json",
        {
            "run_id": PARENT22_RUN_ID,
            "task_id": PARENT22_TASK_ID,
            "generated_at": "2026-07-15T00:05:00Z",
            "items": [
                {
                    "evidence_id": "gap-proof",
                    "task_id": PARENT22_TASK_ID,
                    "status": "pass",
                    "summary": "gap proof",
                    "artifacts": [f"gap-proofs/{PARENT22_TASK_ID}.json"],
                }
            ],
        },
    )
    _write_json(
        run_dir / "dirty-paths-result.json",
        {
            "allowed": True,
            "actual_paths": [changed_path],
            "declared_paths": [changed_path],
            "baseline_paths": [],
            "baseline_changed_paths": [],
            "ignored_paths": [],
            "unexpected_paths": [],
        },
    )
    _write_json(
        run_dir / "autonomous-scope-result.json",
        {
            "allowed": True,
            "allowed_paths": [changed_path],
            "denied_paths": [],
            "manual_confirm_paths": [],
            "findings": [],
        },
    )
    _write_json(
        run_dir / "artifact-manifest.json",
        {
            "status": "pass",
            "scanned_paths": [changed_path],
            "redacted_paths": [],
            "omitted_paths": [],
            "manifest_path": str(run_dir / "artifact-manifest.json"),
            "redaction_manifest_path": str(run_dir / "redaction-manifest.json"),
            "original_hashes": {
                changed_path: hashlib.sha256(changed_file.read_bytes()).hexdigest()
            },
            "redaction_map": [],
            "findings": [],
        },
    )
    _write_json(run_dir / "redaction-manifest.json", {"redactions": []})
    return run


def test_parent22_timeout_artifacts_reconstruct_generator_result_then_evaluate(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.recovery import (
        inspect_partial_artifacts,
        reconstruct_result_envelope,
    )

    run = seed_parent22_partial_fixture(tmp_path)

    assessment = inspect_partial_artifacts(tmp_path, run, ActionType.RUN_GENERATOR)
    path = reconstruct_result_envelope(tmp_path, assessment)
    payload = read_json_file(path)

    assert assessment.status == "recoverable"
    assert assessment.recovered_attempts == (3, 4)
    assert payload["recovery"]["recovered_from_attempts"] == [3, 4]
    assert set(payload["recovery"]["attempt_stream_hashes"]["3"]) == {"stdout", "stderr"}
    assert payload["recovery"]["artifact_hashes"]["knowledge/parent-22.md"]
    assert "generator_contract" in payload["recovery"]["checks"]
    assert payload["status"] == "implemented"
    assert payload["changed_paths"] == ["knowledge/parent-22.md"]
    validate_generator_result_payload(payload)


@pytest.mark.parametrize(
    ("mutation", "expected_status", "expected_check"),
    [
        ("missing_verification", "missing_work", "verification_manifest"),
        ("undeclared_path", "unsafe", "declared_paths"),
        ("baseline_overlap", "unsafe", "baseline_ownership"),
        ("scope_violation", "unsafe", "path_scope"),
        ("artifact_hash_changed", "unsafe", "secret_scope_manifest"),
        ("missing_gap_proof", "missing_work", "required_evidence"),
        ("missing_freshness", "missing_work", "freshness_evidence"),
        ("primary_manifest_symlink", "unsafe", "verification_manifest"),
        ("scenario_commands_owner_symlink", "unsafe", "verification_manifest"),
        ("verification_log_outside_run", "unsafe", "verification_manifest"),
    ],
)
def test_partial_artifacts_require_proof_not_existence(
    tmp_path: Path,
    mutation: str,
    expected_status: str,
    expected_check: str,
) -> None:
    from scripts.loop_supervisor.recovery import inspect_partial_artifacts

    run = seed_parent22_partial_fixture(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / PARENT22_RUN_ID
    changed_path = tmp_path / "knowledge" / "parent-22.md"
    if mutation == "missing_verification":
        (run_dir / "scenario-command-results.json").unlink()
    elif mutation == "undeclared_path":
        dirty = read_json_file(run_dir / "dirty-paths-result.json")
        dirty["actual_paths"].append("knowledge/undeclared.md")
        _write_json(run_dir / "dirty-paths-result.json", dirty)
    elif mutation == "baseline_overlap":
        run["baseline_dirty_paths"] = ["?? knowledge/parent-22.md"]
    elif mutation == "scope_violation":
        run["allowed_paths"] = ["other/**"]
    elif mutation == "artifact_hash_changed":
        changed_path.write_text("api_key=fixture-secret\n", encoding="utf-8")
        hygiene = read_json_file(run_dir / "artifact-manifest.json")
        hygiene["original_hashes"]["knowledge/parent-22.md"] = hashlib.sha256(
            changed_path.read_bytes()
        ).hexdigest()
        _write_json(run_dir / "artifact-manifest.json", hygiene)
    elif mutation == "missing_gap_proof":
        (run_dir / "gap-proofs" / f"{PARENT22_TASK_ID}.json").unlink()
    elif mutation == "missing_freshness":
        run["required_evidence"] = ["crawler workbench freshness evidence"]
    elif mutation == "primary_manifest_symlink":
        manifest = run_dir / "scenario-command-results.json"
        outside = tmp_path / "unrelated-verification-manifest.json"
        manifest.replace(outside)
        manifest.symlink_to(outside)
    elif mutation == "scenario_commands_owner_symlink":
        commands = run_dir / "scenario-commands"
        outside = tmp_path / "external-scenario-commands"
        commands.replace(outside)
        commands.symlink_to(outside, target_is_directory=True)
        manifest = read_json_file(run_dir / "scenario-command-results.json")
        manifest["results"][0]["stdout_path"] = str(
            (outside / "command-1.stdout.log").resolve()
        )
        manifest["results"][0]["stderr_path"] = str(
            (outside / "command-1.stderr.log").resolve()
        )
        _write_json(run_dir / "scenario-command-results.json", manifest)
    elif mutation == "verification_log_outside_run":
        manifest = read_json_file(run_dir / "scenario-command-results.json")
        manifest["results"][0]["stdout_path"] = str(tmp_path / "README.md")
        _write_json(run_dir / "scenario-command-results.json", manifest)

    assessment = inspect_partial_artifacts(tmp_path, run, ActionType.RUN_GENERATOR)

    assert assessment.status == expected_status
    assert any(expected_check in check for check in assessment.missing_checks)


def _complete_retryable_action(store: SupervisorStore, action_id: str, worker_id: str) -> None:
    leased = store.lease_next_action(
        worker_id,
        lease_seconds=120,
        heartbeat_stale_seconds=60,
    )
    assert leased is not None
    assert leased.action_id == action_id
    store.complete_action(
        action_id,
        worker_id,
        ActionResult(
            result_class=ActionResultClass.RETRYABLE_FAILURE,
            summary="Selected model is at capacity",
            failure_key=f"worker:{action_id}:capacity",
            error_class="model_capacity",
        ),
    )


def _complete_recoverable_partial_action(
    store: SupervisorStore, action_id: str, worker_id: str
) -> None:
    leased = store.lease_next_action(
        worker_id,
        lease_seconds=120,
        heartbeat_stale_seconds=60,
    )
    assert leased is not None and leased.action_id == action_id
    store.complete_action(
        action_id,
        worker_id,
        ActionResult(
            result_class=ActionResultClass.RECOVERABLE_PARTIAL,
            summary="Generator timed out after writing partial artifacts",
            failure_key=f"worker:{action_id}:partial",
            error_class="TimeoutError",
        ),
    )


def test_reconciler_retries_with_backoff_then_recovers_parent22_and_evaluates(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.worker import worker_once

    seed_parent22_partial_fixture(tmp_path)
    clock = FakeClock()
    store = migrated_store(tmp_path, clock)

    first = reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID)
    assert first is not None
    assert first.action_type is ActionType.RUN_GENERATOR

    _complete_retryable_action(store, first.action_id, "worker-1")
    before_backoff = reconcile_once(tmp_path, store, include_worktrees=False)
    assert before_backoff.action_for(PARENT22_RUN_ID) is None
    clock.advance(seconds=60)
    retry_one = reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID)
    assert retry_one is not None
    assert retry_one.action_id == first.action_id
    assert retry_one.action_type is ActionType.RUN_GENERATOR

    _complete_retryable_action(store, first.action_id, "worker-2")
    assert reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID) is None
    clock.advance(seconds=119)
    assert reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID) is None
    clock.advance(seconds=1)
    retry_two = reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID)
    assert retry_two is not None
    assert retry_two.action_id == first.action_id

    _complete_retryable_action(store, first.action_id, "worker-3")
    alternate = reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID)
    assert alternate is not None
    assert alternate.action_type is ActionType.RECOVER_GENERATOR_RESULT
    assert alternate.payload["recovery_for_action_type"] == ActionType.RUN_GENERATOR.value
    assert alternate.payload["recovery_failure_key"]
    assert store.fetch_all("user_decisions") == []

    recovered = worker_once(tmp_path, "worker-recovery")
    assert recovered.status == "completed"
    assert recovered.action_id == alternate.action_id
    saved = read_json_file(tmp_path / ".codex" / "loop-runs" / PARENT22_RUN_ID / "run.json")
    assert saved["phase"] == "evaluating"
    assert saved["next_action"] == "run_autonomous_evaluator"
    assert read_json_file(
        tmp_path / ".codex" / "loop-runs" / PARENT22_RUN_ID / "generator-result.json"
    )["recovery"]["next_required_action"] == ActionType.RUN_EVALUATOR.value

    evaluator = reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID)
    assert evaluator is not None
    assert evaluator.action_type is ActionType.RUN_EVALUATOR
    assert not any(
        row["status"] == "pending" and row["action_type"] in {ActionType.COMMIT.value, ActionType.PUSH.value}
        for row in store.fetch_all("actions")
    )
    failure = episode_failures(store)[0]
    assert json.loads(failure["resolution"])["status"] == "closed"
    assert failure["occurrence_count"] == 3


def test_unsafe_secret_partial_opens_global_decision_not_reviewer(tmp_path: Path) -> None:
    from scripts.loop_supervisor.worker import worker_once

    seed_parent22_partial_fixture(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / PARENT22_RUN_ID
    changed_path = tmp_path / "knowledge" / "parent-22.md"
    changed_path.write_text("api_key=fixture-secret\n", encoding="utf-8")
    hygiene = read_json_file(run_dir / "artifact-manifest.json")
    hygiene["original_hashes"]["knowledge/parent-22.md"] = hashlib.sha256(
        changed_path.read_bytes()
    ).hexdigest()
    _write_json(run_dir / "artifact-manifest.json", hygiene)
    store = migrated_store(tmp_path)
    source = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
        PARENT22_RUN_ID
    )
    assert source is not None
    _complete_recoverable_partial_action(store, source.action_id, "worker-source")
    recovery = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
        PARENT22_RUN_ID
    )
    assert recovery is not None
    assert recovery.action_type is ActionType.RECOVER_GENERATOR_RESULT

    result = worker_once(tmp_path, "worker-recovery")

    assert result.result_class == ActionResultClass.POLICY_BLOCK.value
    saved = read_json_file(run_dir / "run.json")
    assert saved["secret_exposure_confirmed"] is True
    reconciled = reconcile_once(tmp_path, store, include_worktrees=False)
    assert reconciled.action_for(PARENT22_RUN_ID) is None
    decision = reconciled.decision_for(PARENT22_RUN_ID)
    assert decision is not None
    assert decision["scope"] == "global"
    assert decision["failure_key"].endswith(":secret_exposure")
    assert not any(
        row["action_type"] == ActionType.RUN_REVIEWER.value
        for row in store.fetch_all("actions")
    )


def test_non_generator_alternate_performs_registry_declared_bounded_replan(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.worker import _mutates_git, worker_once

    run = seed_parent22_partial_fixture(tmp_path)
    run["phase"] = "planning"
    run["next_action"] = "run_autonomous_planner"
    run["last_result"] = "fail"
    run_dir = tmp_path / ".codex" / "loop-runs" / PARENT22_RUN_ID
    _write_json(run_dir / "run.json", run)
    store = migrated_store(tmp_path)
    source = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
        PARENT22_RUN_ID
    )
    assert source is not None and source.action_type is ActionType.RUN_PLANNER
    _complete_recoverable_partial_action(store, source.action_id, "worker-source")
    alternate = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
        PARENT22_RUN_ID
    )

    assert alternate is not None
    assert alternate.action_type is ActionType.RUN_ALTERNATE_RECOVERY
    assert _mutates_git(alternate) is False
    result = worker_once(tmp_path, "worker-alternate")

    assert result.status == "completed"
    saved = read_json_file(run_dir / "run.json")
    assert saved["phase"] == "planning"
    assert saved["next_action"] == "run_autonomous_planner"
    directive = saved["recovery_directives"][-1]
    assert directive["strategy"] == "replan_excluding_failed_approach"
    assert directive["failure_key"] == alternate.payload["recovery_failure_key"]
    assert directive["source_action_type"] == ActionType.RUN_PLANNER.value
    next_action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(
        PARENT22_RUN_ID
    )
    assert next_action is not None
    assert next_action.action_type is ActionType.RUN_PLANNER


def test_failed_alternate_queues_reviewer_once_without_user_decision(tmp_path: Path) -> None:
    from scripts.loop_supervisor.executor import ACTION_HANDLERS
    from scripts.loop_supervisor.reviewer import run_queued_reviewer
    from scripts.loop_supervisor.worker import worker_once

    seed_parent22_partial_fixture(tmp_path)
    clock = FakeClock()
    store = migrated_store(tmp_path, clock)
    action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID)
    assert action is not None
    for attempt, delay in ((1, 60), (2, 120), (3, 0)):
        _complete_retryable_action(store, action.action_id, f"worker-{attempt}")
        result = reconcile_once(tmp_path, store, include_worktrees=False)
        if delay:
            assert result.action_for(PARENT22_RUN_ID) is None
            clock.advance(seconds=delay)
            action = reconcile_once(tmp_path, store, include_worktrees=False).action_for(PARENT22_RUN_ID)
            assert action is not None
    alternate = result.action_for(PARENT22_RUN_ID)
    assert alternate is not None
    leased = store.lease_next_action(
        "worker-alternate",
        lease_seconds=120,
        heartbeat_stale_seconds=60,
    )
    assert leased is not None and leased.action_id == alternate.action_id
    store.complete_action(
        alternate.action_id,
        "worker-alternate",
        ActionResult(
            result_class=ActionResultClass.TERMINAL_FAILURE,
            summary="partial artifact recovery could not be proven",
            failure_key="worker:alternate:unprovable",
            error_class="partial_artifact_unprovable",
        ),
    )

    reviewer = reconcile_once(tmp_path, store, include_worktrees=False)
    reviewer_action = reviewer.action_for(PARENT22_RUN_ID)
    assert reviewer_action is not None
    assert reviewer_action.action_type is ActionType.RUN_REVIEWER
    assert reviewer_action.queue_owner is ActionOwner.REVIEWER
    repeated = reconcile_once(tmp_path, store, include_worktrees=False)
    assert repeated.action_for(PARENT22_RUN_ID).action_id == reviewer_action.action_id
    assert len(
        [row for row in store.fetch_all("actions") if row["action_type"] == ActionType.RUN_REVIEWER.value]
    ) == 1
    assert store.fetch_all("user_decisions") == []
    assert ActionType.RUN_REVIEWER not in ACTION_HANDLERS

    worker_result = worker_once(tmp_path, "task-5-worker")

    assert worker_result.status == "idle"
    reviewer_row = store.get_action(reviewer_action.action_id)
    assert reviewer_row.status == "pending"
    assert reviewer_row.queue_owner == ActionOwner.REVIEWER.value
    assert not any(
        row["action_id"] == reviewer_action.action_id
        for row in store.fetch_all("action_attempts")
    )

    reviewer_result = run_queued_reviewer(
        store,
        reviewer_id="task-5-reviewer",
        driver=lambda **_kwargs: {"status": "timeout", "exit_code": 124},
    )

    assert reviewer_result is not None
    assert store.get_action(reviewer_action.action_id).status in {"completed", "failed"}
    reviewer_attempt = next(
        row
        for row in store.fetch_all("action_attempts")
        if row["action_id"] == reviewer_action.action_id
    )
    assert reviewer_attempt["worker_id"] == "task-5-reviewer"
