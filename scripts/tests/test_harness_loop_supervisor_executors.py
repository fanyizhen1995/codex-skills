from __future__ import annotations

import hashlib
import inspect
import shutil
import threading
from pathlib import Path

import pytest

import scripts.harness_loop_orchestrator as legacy
from scripts.loop_supervisor.models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
)


def _request(action_type: ActionType) -> ActionRequest:
    payload = (
        {"service_id": "loop-dashboard"}
        if action_type is ActionType.RESTART_SERVICE
        else {"driver": "fake"}
    )
    return ActionRequest(
        action_id=f"action-{action_type.value}",
        run_id="run-1",
        run_revision=0,
        policy="demand_development",
        phase="planning",
        action_type=action_type,
        idempotency_key=f"key-{action_type.value}",
        queue_owner=(
            ActionOwner.SUPERVISOR
            if action_type is ActionType.RESTART_SERVICE
            else ActionOwner.WORKER
        ),
        payload=payload,
    )


def _continuation_request(
    repo_root: Path,
    *,
    source_run_id: str = "source-run",
    continuation_run_id: str = "continuation-run",
    requirement: str = "Continue the trusted lineage",
    repo_relative_root: str = ".",
) -> ActionRequest:
    source = legacy.create_preflight_run(
        repo_root=repo_root,
        mode="autonomous-knowledge",
        requirement=requirement,
        run_id=source_run_id,
        domain="ai_infra",
        constraints=["preserve provenance"],
        stop_conditions=["stopped_budget"],
        confirm=True,
    )
    source.update(
        {
            "phase": "stopped_budget",
            "last_result": "pass",
            "next_action": "none",
            "loop_lineage_id": "lineage-a",
            "commit": "commit-abc",
        }
    )
    legacy.save_run(repo_root, source)
    return ActionRequest(
        action_id="action-create-continuation",
        run_id=source_run_id,
        run_revision=0,
        policy="autonomous_knowledge",
        phase="stopped_budget",
        action_type=ActionType.CREATE_CONTINUATION,
        idempotency_key="continuation-lineage-a-parent-14-commit-abc",
        repo_relative_root=repo_relative_root,
        payload={
            "loop_lineage_id": "lineage-a",
            "continuation_run_id": continuation_run_id,
            "continuation_identity": {
                "loop_lineage_id": "lineage-a",
                "source_run_id": source_run_id,
                "semantic_parent": "parent-14",
                "source_commit": "commit-abc",
            },
        },
    )


class _SimulatedContinuationHardCrash(BaseException):
    pass


def _seed_hard_crash_pending_continuation(
    repo_root: Path,
    request: ActionRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    from scripts.loop_supervisor.executor import execute_action

    def crash_after_publish(actual: str, _stage_dir: Path) -> None:
        if actual == "before_run_promotion":
            raise _SimulatedContinuationHardCrash

    with monkeypatch.context() as crash:
        crash.setattr(
            legacy,
            "_continuation_publish_cutpoint",
            crash_after_publish,
        )
        with pytest.raises(_SimulatedContinuationHardCrash):
            execute_action(request, repo_root)
    target_dir = legacy.run_dir_for(repo_root, "continuation-run")
    staging_root = repo_root / ".codex" / "loop-staging"
    sidecar = next(staging_root.glob("continuation-run-*.owner.json"))
    assert (target_dir / "preflight.md").is_file()
    assert (target_dir / "run.pending").is_file()
    assert not (target_dir / "run.json").exists()
    return target_dir, sidecar


def _seed_incomplete_continuation(
    repo_root: Path,
    *,
    source_run_id: str = "source-run",
    continuation_run_id: str = "continuation-run",
) -> dict[str, object]:
    source = legacy.load_run(repo_root, source_run_id)
    return legacy.create_preflight_run(
        repo_root=repo_root,
        mode=source["policy"],
        requirement=source["requirement"],
        run_id=continuation_run_id,
        domain=source["domain"],
        constraints=list(source["constraints"]),
        stop_conditions=list(source["stop_conditions"]),
        confirm=True,
    )


def test_handler_table_exactly_covers_registry_executable_actions() -> None:
    from scripts.loop_supervisor.executor import ACTION_HANDLERS, executable_action_types
    from scripts.loop_supervisor.registry import worker_executable_action_types

    expected = set(worker_executable_action_types())

    assert executable_action_types() == expected
    assert set(ACTION_HANDLERS) == expected
    assert len(set(ACTION_HANDLERS.values())) == len(ACTION_HANDLERS)
    assert ACTION_HANDLERS[ActionType.COMMIT]


def test_each_handler_is_bounded_and_returns_action_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import executor

    calls: list[str] = []

    def fake_primitive(repo_root: Path, request: ActionRequest) -> ActionResult:
        assert repo_root == tmp_path
        calls.append(request.action_type.value)
        return ActionResult(ActionResultClass.SUCCESS, request.action_type.value)

    for primitive_name in executor.BOUNDED_PRIMITIVE_NAMES.values():
        monkeypatch.setattr(legacy, primitive_name, fake_primitive)

    assert not hasattr(legacy, "_run_loop")
    assert not hasattr(legacy, "_run_autonomous")
    assert not hasattr(legacy, "_run_demand_multi")

    for action_type, handler in executor.ACTION_HANDLERS.items():
        result = handler(tmp_path, _request(action_type))
        assert isinstance(result, ActionResult)

    assert calls == [action_type.value for action_type in executor.ACTION_HANDLERS]


def test_dispatcher_rejects_non_executable_action(tmp_path: Path) -> None:
    from scripts.loop_supervisor.executor import execute_action

    with pytest.raises(ValueError, match="not executable"):
        execute_action(_request(ActionType.ASK_USER), tmp_path)


def test_demand_generator_can_repair_failed_evaluator_result(tmp_path: Path) -> None:
    run = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Repair the failed evaluator result",
        run_id="repair-run",
        confirm=True,
    )
    legacy._run_planner(tmp_path, run["run_id"], driver="fake")
    run = legacy.load_run(tmp_path, run["run_id"])
    run["phase"] = "repair_needed"
    run["next_action"] = "repair_from_evaluator_findings"
    run["attempts"]["generator"] = 1
    legacy.save_run(tmp_path, run)
    request = ActionRequest(
        action_id="action-repair-generator",
        run_id=run["run_id"],
        run_revision=0,
        policy="demand_development",
        phase="repair_needed",
        action_type=ActionType.RUN_GENERATOR,
        idempotency_key="repair-generator",
        task_id=run["task_id"],
        next_action="repair_from_evaluator_findings",
        payload={"driver": "fake"},
    )

    result = legacy._run_bounded_generator(tmp_path, request)

    repaired = legacy.load_run(tmp_path, run["run_id"])
    assert result.result_class is ActionResultClass.SUCCESS
    assert repaired["phase"] == "evaluating"
    assert repaired["next_action"] == "run_evaluator"
    assert repaired["attempts"]["generator"] == 2


def test_codex_evaluator_bootstraps_missing_loop_session_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Evaluate a Supervisor-owned loop run",
        run_id="evaluator-session-run",
        confirm=True,
    )
    legacy._run_planner(tmp_path, run["run_id"], driver="fake")
    legacy._run_generator(tmp_path, run["run_id"], driver="fake")
    run = legacy.load_run(tmp_path, run["run_id"])
    session_dir = tmp_path / ".codex" / "session-state"
    assert not session_dir.exists()

    def evaluator_pass(command: list[str], **_kwargs: object) -> object:
        if command[0] == "git":
            raise legacy.subprocess.CalledProcessError(128, command)
        assert "run-task-auto-gate" in command
        sessions = list(session_dir.glob("*.json"))
        assert len(sessions) == 1
        session = legacy.read_json_file(sessions[0])
        assert session["task"] == run["task_id"]
        assert Path(session["worktree"]).resolve() == tmp_path.resolve()
        assert session["branch"] == run["branch"]
        bundle = (
            tmp_path
            / ".codex"
            / "evaluations"
            / "tasks"
            / run["task_id"]
            / "20260716T000000Z-attempt-1"
        )
        bundle.mkdir(parents=True)
        legacy.write_json_file(
            bundle / "result.json",
            {
                "status": "pass",
                "gate": "task",
                "task_id": run["task_id"],
                "attempt": 1,
                "findings": [],
                "rerun_commands": [],
                "next_action": "proceed_to_user_acceptance",
            },
        )
        return legacy.subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(legacy.subprocess, "run", evaluator_pass)
    request = ActionRequest(
        action_id="action-evaluate-loop-run",
        run_id=run["run_id"],
        run_revision=0,
        policy="demand_development",
        phase="evaluating",
        action_type=ActionType.RUN_EVALUATOR,
        idempotency_key="evaluate-loop-run",
        task_id=run["task_id"],
        next_action="run_evaluator",
        payload={"driver": "codex-exec", "max_attempts": 1},
    )

    result = legacy._run_bounded_evaluator(tmp_path, request)

    assert result.result_class is ActionResultClass.SUCCESS
    assert (
        legacy.load_run(tmp_path, run["run_id"])["phase"]
        == "passed_waiting_human_merge"
    )


def test_codex_evaluator_propagates_blocked_bundle_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Evaluate an evidence-backed Supervisor run",
        run_id="blocked-evaluator-run",
        task_id="blocked-evaluator-task",
        confirm=True,
    )
    legacy._run_planner(tmp_path, run["run_id"], driver="fake")
    legacy._run_generator(tmp_path, run["run_id"], driver="fake")

    def evaluator_blocked(command: list[str], **_kwargs: object) -> object:
        if command[0] == "git":
            raise legacy.subprocess.CalledProcessError(128, command)
        assert "run-task-auto-gate" in command
        bundle = (
            tmp_path
            / ".codex"
            / "evaluations"
            / "tasks"
            / run["task_id"]
            / "20260716T172922Z-attempt-1"
        )
        bundle.mkdir(parents=True)
        legacy.write_json_file(
            bundle / "result.json",
            {
                "status": "blocked",
                "gate": "task",
                "task_id": run["task_id"],
                "final_bundle_id": "",
                "attempt": 1,
                "summary": "required browser evidence is missing",
                "findings": [
                    {
                        "id": "F-001",
                        "severity": "blocker",
                        "category": "missing_evidence",
                        "evidence": ["artifacts.json#scenario_outputs"],
                        "recommended_action": "run the browser evaluator",
                    }
                ],
                "scenario_results": [],
                "rerun_commands": ["python3 scripts/browser_evaluator.py"],
                "environment_checks": [],
                "verdict_reason": "scenario evidence is absent",
                "next_action": "request_missing_evidence",
            },
        )
        return legacy.subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    monkeypatch.setattr(legacy.subprocess, "run", evaluator_blocked)
    request = ActionRequest(
        action_id="action-blocked-evaluator",
        run_id=run["run_id"],
        run_revision=0,
        policy="demand_development",
        phase="evaluating",
        action_type=ActionType.RUN_EVALUATOR,
        idempotency_key="blocked-evaluator",
        task_id=run["task_id"],
        next_action="run_evaluator",
        payload={"driver": "codex-exec", "max_attempts": 1},
    )

    result = legacy._run_bounded_evaluator(tmp_path, request)

    evaluator_result = legacy.read_json_file(
        legacy.run_dir_for(tmp_path, run["run_id"]) / "evaluator-result.json"
    )
    updated = legacy.load_run(tmp_path, run["run_id"])
    assert result.result_class is ActionResultClass.SUCCESS
    assert evaluator_result["status"] == "blocked"
    assert evaluator_result["findings"][0]["id"] == "F-001"
    assert evaluator_result["rerun_commands"] == ["python3 scripts/browser_evaluator.py"]
    assert evaluator_result["next_action"] == "request_missing_evidence"
    assert updated["phase"] == "repair_needed"
    assert updated["next_action"] == "request_missing_evidence"


def test_codex_evaluator_without_result_bundle_is_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Retry an evaluator infrastructure failure",
        run_id="missing-evaluator-result-run",
        task_id="missing-evaluator-result-task",
        confirm=True,
    )
    legacy._run_planner(tmp_path, run["run_id"], driver="fake")
    legacy._run_generator(tmp_path, run["run_id"], driver="fake")
    monkeypatch.setattr(
        legacy.subprocess,
        "run",
        lambda command, **_kwargs: legacy.subprocess.CompletedProcess(
            command, 1, stdout="", stderr=""
        ),
    )
    request = ActionRequest(
        action_id="action-missing-evaluator-result",
        run_id=run["run_id"],
        run_revision=0,
        policy="demand_development",
        phase="evaluating",
        action_type=ActionType.RUN_EVALUATOR,
        idempotency_key="missing-evaluator-result",
        task_id=run["task_id"],
        next_action="run_evaluator",
        payload={"driver": "codex-exec", "max_attempts": 1},
    )

    result = legacy._run_bounded_evaluator(tmp_path, request)

    assert result.result_class is ActionResultClass.RETRYABLE_FAILURE
    assert "without a result bundle" in result.summary
    assert legacy.load_run(tmp_path, run["run_id"])["phase"] == "evaluating"
    assert not (
        legacy.run_dir_for(tmp_path, run["run_id"]) / "evaluator-result.json"
    ).exists()


def test_codex_evaluator_does_not_reuse_stale_success_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Require fresh evaluator evidence",
        run_id="stale-evaluator-success-run",
        task_id="stale-evaluator-success-task",
        confirm=True,
    )
    legacy._run_planner(tmp_path, run["run_id"], driver="fake")
    legacy._run_generator(tmp_path, run["run_id"], driver="fake")
    stale_bundle = (
        tmp_path
        / ".codex"
        / "evaluations"
        / "tasks"
        / run["task_id"]
        / "20260715T000000Z-attempt-1"
    )
    stale_bundle.mkdir(parents=True)
    legacy.write_json_file(
        stale_bundle / "result.json",
        {
            "status": "pass",
            "gate": "task",
            "task_id": run["task_id"],
            "attempt": 1,
            "findings": [],
            "rerun_commands": [],
            "next_action": "proceed_to_user_acceptance",
        },
    )

    def evaluator_noop(command: list[str], **_kwargs: object) -> object:
        if command[0] == "git":
            raise legacy.subprocess.CalledProcessError(128, command)
        return legacy.subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(legacy.subprocess, "run", evaluator_noop)
    request = ActionRequest(
        action_id="action-stale-evaluator-success",
        run_id=run["run_id"],
        run_revision=0,
        policy="demand_development",
        phase="evaluating",
        action_type=ActionType.RUN_EVALUATOR,
        idempotency_key="stale-evaluator-success",
        task_id=run["task_id"],
        next_action="run_evaluator",
        payload={"driver": "codex-exec", "max_attempts": 1},
    )

    result = legacy._run_bounded_evaluator(tmp_path, request)

    assert result.result_class is ActionResultClass.RETRYABLE_FAILURE
    assert "without a result bundle" in result.summary
    assert legacy.load_run(tmp_path, run["run_id"])["phase"] == "evaluating"


def test_codex_evaluator_prefers_fresh_real_bundle_over_old_fake_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="demand-development",
        requirement="Use the current codex evaluator result",
        run_id="mixed-evaluator-bundles-run",
        task_id="mixed-evaluator-bundles-task",
        confirm=True,
    )
    legacy._run_planner(tmp_path, run["run_id"], driver="fake")
    legacy._run_generator(tmp_path, run["run_id"], driver="fake")
    task_root = tmp_path / ".codex" / "evaluations" / "tasks" / run["task_id"]
    fake_bundle = task_root / "fake-attempt-9"
    fake_bundle.mkdir(parents=True)
    legacy.write_json_file(
        fake_bundle / "result.json",
        {
            "status": "pass",
            "gate": "task",
            "task_id": run["task_id"],
            "attempt": 9,
            "findings": [],
            "rerun_commands": [],
            "next_action": "proceed_to_user_acceptance",
        },
    )

    def evaluator_blocked(command: list[str], **_kwargs: object) -> object:
        if command[0] == "git":
            raise legacy.subprocess.CalledProcessError(128, command)
        real_bundle = task_root / "20260716T172922Z-attempt-1"
        real_bundle.mkdir(parents=True)
        legacy.write_json_file(
            real_bundle / "result.json",
            {
                "status": "blocked",
                "gate": "task",
                "task_id": run["task_id"],
                "attempt": 1,
                "findings": [{"id": "REAL-001"}],
                "rerun_commands": ["python3 scripts/real_evaluator.py"],
                "next_action": "request_missing_evidence",
            },
        )
        return legacy.subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    monkeypatch.setattr(legacy.subprocess, "run", evaluator_blocked)
    request = ActionRequest(
        action_id="action-mixed-evaluator-bundles",
        run_id=run["run_id"],
        run_revision=0,
        policy="demand_development",
        phase="evaluating",
        action_type=ActionType.RUN_EVALUATOR,
        idempotency_key="mixed-evaluator-bundles",
        task_id=run["task_id"],
        next_action="run_evaluator",
        payload={"driver": "codex-exec", "max_attempts": 1},
    )

    result = legacy._run_bounded_evaluator(tmp_path, request)

    evaluator_result = legacy.read_json_file(
        legacy.run_dir_for(tmp_path, run["run_id"]) / "evaluator-result.json"
    )
    assert result.result_class is ActionResultClass.SUCCESS
    assert evaluator_result["status"] == "blocked"
    assert evaluator_result["findings"] == [{"id": "REAL-001"}]
    assert evaluator_result["attempt"] == 1


def test_service_keeper_rejects_non_allowlisted_service_before_process_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor import services

    monkeypatch.setattr(
        services,
        "_run_tmux_command",
        lambda *_args: pytest.fail("non-allowlisted service reached process control"),
    )

    with pytest.raises(ValueError, match="not allowlisted"):
        services.restart_managed_service(tmp_path, "unknown-service")


def test_continuation_retry_repairs_preflight_after_provenance_save_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import reconciler
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    original_atomic_save_run = reconciler.atomic_save_run

    def crash_before_provenance_save(
        repo_root: Path,
        run_id: str,
        payload: dict[str, object],
        **kwargs: object,
    ) -> dict[str, object]:
        if run_id == "continuation-run" and "loop_lineage_id" in payload:
            raise OSError("simulated crash before continuation provenance save")
        return original_atomic_save_run(repo_root, run_id, payload, **kwargs)

    with monkeypatch.context() as crash:
        crash.setattr(reconciler, "atomic_save_run", crash_before_provenance_save)
        interrupted = execute_action(request, tmp_path)

    assert interrupted.result_class is ActionResultClass.RETRYABLE_FAILURE
    incomplete = legacy.load_run(tmp_path, "continuation-run")
    assert "loop_lineage_id" not in incomplete
    assert "previous_run_id" not in incomplete
    assert "parent_run_id" not in incomplete
    assert "previous_commit" not in incomplete

    repaired = execute_action(request, tmp_path)

    assert repaired.result_class is ActionResultClass.SUCCESS
    continuation = legacy.load_run(tmp_path, "continuation-run")
    assert continuation["loop_lineage_id"] == "lineage-a"
    assert continuation["previous_run_id"] == "source-run"
    assert continuation["parent_run_id"] == "source-run"
    assert continuation["previous_commit"] == "commit-abc"

    target = legacy.run_dir_for(tmp_path, "continuation-run") / "run.json"
    repaired_bytes = target.read_bytes()
    replayed = execute_action(request, tmp_path)
    assert replayed.result_class is ActionResultClass.SUCCESS
    assert target.read_bytes() == repaired_bytes


@pytest.mark.parametrize("cutpoint", ["after_preflight", "partial_run_json"])
def test_continuation_initial_publication_retries_after_staging_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cutpoint: str,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)

    def crash_at(actual: str, _stage_dir: Path) -> None:
        if actual == cutpoint:
            raise OSError(f"simulated continuation publication crash: {cutpoint}")

    with monkeypatch.context() as crash:
        crash.setattr(
            legacy,
            "_continuation_publish_cutpoint",
            crash_at,
            raising=False,
        )
        interrupted = execute_action(request, tmp_path)

    target_dir = legacy.run_dir_for(tmp_path, "continuation-run")
    assert interrupted.result_class is ActionResultClass.RETRYABLE_FAILURE
    assert not target_dir.exists()

    staging_root = tmp_path / ".codex" / "loop-staging"
    owned_sidecars = list(staging_root.glob("continuation-run-*.owner.json"))
    assert len(owned_sidecars) == 1
    owned_stage = staging_root / owned_sidecars[0].name.removesuffix(".owner.json")
    assert (owned_stage / "preflight.md").is_file()
    if cutpoint == "after_preflight":
        assert not (owned_stage / "run.pending").exists()
    else:
        assert (owned_stage / "run.pending").is_file()
        with pytest.raises(ValueError):
            legacy.read_json_file(owned_stage / "run.pending")
    unrelated_dir = staging_root / "continuation-run-unrelated"
    unrelated_dir.mkdir()
    unrelated_file = unrelated_dir / "keep.txt"
    unrelated_file.write_text("unrelated staging content\n", encoding="utf-8")
    unrelated_sidecar = staging_root / "continuation-run-unrelated.owner.json"
    unrelated_sidecar.write_text('{"owner":"someone-else"}\n', encoding="utf-8")

    retried = execute_action(request, tmp_path)

    assert retried.result_class is ActionResultClass.SUCCESS
    continuation = legacy.load_run(tmp_path, "continuation-run")
    assert continuation["state_revision"] == 1
    assert continuation["loop_lineage_id"] == "lineage-a"
    assert (target_dir / "preflight.md").is_file()
    assert owned_sidecars[0].is_file()
    assert owned_stage.is_dir()
    assert unrelated_file.read_text(encoding="utf-8") == "unrelated staging content\n"
    assert unrelated_sidecar.read_text(encoding="utf-8") == '{"owner":"someone-else"}\n'


def test_continuation_retry_rejects_replaced_owned_staging_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)

    def crash_after_preflight(actual: str, _stage_dir: Path) -> None:
        if actual == "after_preflight":
            raise OSError("simulated continuation publication crash")

    with monkeypatch.context() as crash:
        crash.setattr(
            legacy,
            "_continuation_publish_cutpoint",
            crash_after_preflight,
        )
        interrupted = execute_action(request, tmp_path)
    assert interrupted.result_class is ActionResultClass.RETRYABLE_FAILURE

    staging_root = tmp_path / ".codex" / "loop-staging"
    sidecar = next(staging_root.glob("continuation-run-*.owner.json"))
    sidecar_bytes = sidecar.read_bytes()
    stage_dir = staging_root / sidecar.name.removesuffix(".owner.json")
    (stage_dir / "preflight.md").unlink()
    stage_dir.rmdir()
    stage_dir.mkdir()
    replacement = stage_dir / "replacement.txt"
    replacement.write_text("unrelated replacement content\n", encoding="utf-8")

    retried = execute_action(request, tmp_path)

    assert retried.result_class is not ActionResultClass.SUCCESS
    assert "staging directory" in retried.summary
    assert "identity" in retried.summary or "content" in retried.summary
    assert replacement.read_text(encoding="utf-8") == "unrelated replacement content\n"
    assert sidecar.read_bytes() == sidecar_bytes
    assert not legacy.run_dir_for(tmp_path, "continuation-run").exists()


def test_continuation_publication_rejects_staging_replaced_after_final_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    replacement_path: Path | None = None

    def replace_before_publish(actual: str, stage_dir: Path) -> None:
        nonlocal replacement_path
        if actual != "before_publish":
            return
        owned_stage = stage_dir.with_name(f"{stage_dir.name}-displaced")
        stage_dir.rename(owned_stage)
        shutil.copytree(owned_stage, stage_dir)
        replacement_path = stage_dir
        (stage_dir / "foreign.txt").write_text(
            "unowned publication content\n", encoding="utf-8"
        )

    monkeypatch.setattr(
        legacy,
        "_continuation_publish_cutpoint",
        replace_before_publish,
    )

    result = execute_action(request, tmp_path)

    target_dir = legacy.run_dir_for(tmp_path, "continuation-run")
    assert result.result_class is not ActionResultClass.SUCCESS
    assert "staging directory" in result.summary
    assert replacement_path is not None
    assert (replacement_path / "foreign.txt").read_text(encoding="utf-8") == (
        "unowned publication content\n"
    )
    assert not target_dir.exists()


def test_continuation_publication_never_promotes_source_replaced_at_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    replacement_created = False

    def replace_at_rename(actual: str, stage_dir: Path) -> None:
        nonlocal replacement_created
        if actual != "before_stage_rename":
            return
        owned_stage = stage_dir.with_name(f"{stage_dir.name}-rename-displaced")
        stage_dir.rename(owned_stage)
        shutil.copytree(owned_stage, stage_dir)
        (stage_dir / "foreign.txt").write_text(
            "unowned rename-boundary content\n", encoding="utf-8"
        )
        replacement_created = True

    monkeypatch.setattr(
        legacy,
        "_continuation_publish_cutpoint",
        replace_at_rename,
    )

    result = execute_action(request, tmp_path)

    target_dir = legacy.run_dir_for(tmp_path, "continuation-run")
    assert replacement_created
    assert result.result_class is not ActionResultClass.SUCCESS
    assert "identity" in result.summary
    assert (target_dir / "foreign.txt").read_text(encoding="utf-8") == (
        "unowned rename-boundary content\n"
    )
    assert (target_dir / "run.pending").is_file()
    assert not (target_dir / "run.json").exists()


def test_continuation_publication_preserves_destination_created_at_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    target_dir = legacy.run_dir_for(tmp_path, "continuation-run")
    foreign_identity: tuple[int, int] | None = None

    def create_destination_at_rename(actual: str, _stage_dir: Path) -> None:
        nonlocal foreign_identity
        if actual != "before_stage_rename":
            return
        target_dir.mkdir()
        target_stat = target_dir.stat(follow_symlinks=False)
        foreign_identity = (target_stat.st_dev, target_stat.st_ino)

    monkeypatch.setattr(
        legacy,
        "_continuation_publish_cutpoint",
        create_destination_at_rename,
    )

    result = execute_action(request, tmp_path)

    assert foreign_identity is not None
    assert result.result_class is ActionResultClass.POLICY_BLOCK
    target_stat = target_dir.stat(follow_symlinks=False)
    assert (target_stat.st_dev, target_stat.st_ino) == foreign_identity
    assert list(target_dir.iterdir()) == []
    assert not (target_dir / "run.json").exists()


def test_continuation_cleanup_never_rmdirs_replacement_at_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)

    def crash_after_preflight(actual: str, _stage_dir: Path) -> None:
        if actual == "after_preflight":
            raise OSError("simulated continuation publication crash")

    with monkeypatch.context() as crash:
        crash.setattr(
            legacy,
            "_continuation_publish_cutpoint",
            crash_after_preflight,
        )
        interrupted = execute_action(request, tmp_path)
    assert interrupted.result_class is ActionResultClass.RETRYABLE_FAILURE

    staging_root = tmp_path / ".codex" / "loop-staging"
    sidecar = next(staging_root.glob("continuation-run-*.owner.json"))
    stage_dir = staging_root / sidecar.name.removesuffix(".owner.json")
    replacement: Path | None = None

    def replace_before_rmdir(actual: str, actual_stage: Path) -> None:
        nonlocal replacement
        if actual != "before_cleanup_rmdir":
            return
        displaced = actual_stage.with_name(f"{actual_stage.name}-cleanup-displaced")
        actual_stage.rename(displaced)
        actual_stage.mkdir()
        replacement = actual_stage

    monkeypatch.setattr(
        legacy,
        "_continuation_cleanup_cutpoint",
        replace_before_rmdir,
        raising=False,
    )

    retried = execute_action(request, tmp_path)

    assert replacement is not None
    assert retried.result_class is not ActionResultClass.SUCCESS
    assert replacement.is_dir()
    assert sidecar.is_file()
    assert not legacy.run_dir_for(tmp_path, "continuation-run").exists()


def test_continuation_publication_recovers_crash_before_run_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)

    def crash_before_promotion(actual: str, _stage_dir: Path) -> None:
        if actual == "before_run_promotion":
            raise OSError("simulated crash before continuation discovery")

    with monkeypatch.context() as crash:
        crash.setattr(
            legacy,
            "_continuation_publish_cutpoint",
            crash_before_promotion,
        )
        interrupted = execute_action(request, tmp_path)

    target_dir = legacy.run_dir_for(tmp_path, "continuation-run")
    assert interrupted.result_class is ActionResultClass.RETRYABLE_FAILURE
    assert not target_dir.exists()
    staging_root = tmp_path / ".codex" / "loop-staging"
    sidecar = next(staging_root.glob("continuation-run-*.owner.json"))
    hidden_stage = staging_root / sidecar.name.removesuffix(".owner.json")
    assert (hidden_stage / "preflight.md").is_file()
    assert (hidden_stage / "run.pending").is_file()

    retried = execute_action(request, tmp_path)

    assert retried.result_class is ActionResultClass.SUCCESS
    assert (target_dir / "run.json").is_file()
    assert not (target_dir / "run.pending").exists()
    continuation = legacy.load_run(tmp_path, "continuation-run")
    assert continuation["state_revision"] == 1
    assert continuation["loop_lineage_id"] == "lineage-a"


@pytest.mark.parametrize("use_worktree", [False, True], ids=["main", "worktree"])
def test_continuation_pending_publication_is_hidden_from_reconcile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_worktree: bool,
) -> None:
    from scripts.loop_supervisor import reconciler
    from scripts.loop_supervisor.executor import execute_action
    from scripts.loop_supervisor.store import SupervisorStore

    execution_root = tmp_path
    repo_relative_root = "."
    if use_worktree:
        execution_root = tmp_path / ".worktrees" / "child"
        execution_root.mkdir(parents=True)
        repo_relative_root = ".worktrees/child"
    request = _continuation_request(
        execution_root,
        repo_relative_root=repo_relative_root,
    )
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()

    pending_visible = threading.Event()
    release_promotion = threading.Event()
    discovery_entered = threading.Event()
    reconcile_started = threading.Event()
    publisher_results: list[ActionResult] = []
    reconcile_results: list[object] = []
    thread_errors: list[BaseException] = []
    failure_rows: list[dict[str, object]] = []
    decision_rows: list[dict[str, object]] = []
    real_discover = reconciler.discover_run_candidates

    def block_before_promotion(actual: str, _stage_dir: Path) -> None:
        if actual != "before_run_promotion":
            return
        pending_visible.set()
        if not release_promotion.wait(timeout=5):
            raise TimeoutError("timed out waiting to release continuation promotion")

    def observe_discovery(root: Path, *, include_worktrees: bool = True):
        discovery_entered.set()
        return real_discover(root, include_worktrees=include_worktrees)

    monkeypatch.setattr(
        legacy,
        "_continuation_publish_cutpoint",
        block_before_promotion,
    )
    monkeypatch.setattr(reconciler, "discover_run_candidates", observe_discovery)

    def publish() -> None:
        try:
            publisher_results.append(execute_action(request, execution_root))
        except BaseException as exc:
            thread_errors.append(exc)

    def reconcile() -> None:
        try:
            with SupervisorStore.open(tmp_path) as store:
                reconcile_started.set()
                result = reconciler.reconcile_once(
                    tmp_path, store, include_worktrees=True
                )
                reconcile_results.append(result)
                failure_rows.extend(
                    row
                    for row in store.fetch_all("failures")
                    if row.get("run_id") == "continuation-run"
                )
                decision_rows.extend(
                    row
                    for row in store.fetch_all("user_decisions")
                    if row.get("run_id") == "continuation-run"
                )
        except BaseException as exc:
            thread_errors.append(exc)

    publisher = threading.Thread(target=publish)
    reconciler_thread = threading.Thread(target=reconcile)
    publisher.start()
    assert pending_visible.wait(timeout=5)
    reconciler_thread.start()
    assert reconcile_started.wait(timeout=5)
    try:
        observed_before_promotion = discovery_entered.wait(timeout=0.5)
    finally:
        release_promotion.set()
    publisher.join(timeout=5)
    reconciler_thread.join(timeout=5)

    assert not publisher.is_alive()
    assert not reconciler_thread.is_alive()
    assert not observed_before_promotion
    assert thread_errors == []
    assert publisher_results[0].result_class is ActionResultClass.SUCCESS
    assert len(reconcile_results) == 1
    assert failure_rows == []
    assert decision_rows == []


def test_reconcile_skips_exact_hard_crash_pending_then_retry_promotes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.loop_supervisor.executor import execute_action
    from scripts.loop_supervisor.reconciler import reconcile_once
    from scripts.loop_supervisor.store import SupervisorStore

    request = _continuation_request(tmp_path)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        reconcile_once(tmp_path, store, include_worktrees=False)
        store.enqueue_action(request)
    target_dir, sidecar = _seed_hard_crash_pending_continuation(
        tmp_path, request, monkeypatch
    )
    owner = legacy.read_json_file(sidecar)
    target_stat = target_dir.stat(follow_symlinks=False)
    assert (owner["stage_device"], owner["stage_inode"]) == (
        target_stat.st_dev,
        target_stat.st_ino,
    )

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        pending = reconcile_once(tmp_path, store, include_worktrees=False)
        pending_failures = [
            row
            for row in store.fetch_all("failures")
            if row.get("run_id") == "continuation-run"
        ]
        pending_decisions = [
            row
            for row in store.fetch_all("user_decisions")
            if row.get("run_id") == "continuation-run"
        ]

        retried = execute_action(request, tmp_path)
        reconciled = reconcile_once(tmp_path, store, include_worktrees=False)

        assert pending.action_for("continuation-run") is None
        assert pending.decision_for("continuation-run") is None
        assert pending_failures == []
        assert pending_decisions == []
        assert retried.result_class is ActionResultClass.SUCCESS
        assert not (target_dir / "run.pending").exists()
        assert (target_dir / "run.json").is_file()
        assert reconciled.decision_for("continuation-run") is None
        assert store.get_run("continuation-run")["revision"] == 1


@pytest.mark.parametrize(
    "tamper",
    [
        "malformed_sidecar",
        "stale_hash",
        "foreign_inode",
        "missing_sidecar",
        "expired",
        "extra_member",
        "wrong_run_id",
    ],
)
def test_reconcile_rejects_untrusted_pending_continuation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    from scripts.loop_supervisor.executor import execute_action
    from scripts.loop_supervisor.reconciler import reconcile_once
    from scripts.loop_supervisor.store import SupervisorStore

    request = _continuation_request(tmp_path)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        reconcile_once(tmp_path, store, include_worktrees=False)
        store.enqueue_action(request)
    target_dir, sidecar = _seed_hard_crash_pending_continuation(
        tmp_path, request, monkeypatch
    )
    pending_path = target_dir / "run.pending"
    if tamper == "malformed_sidecar":
        sidecar.write_text("{not-json\n", encoding="utf-8")
    elif tamper == "stale_hash":
        pending_path.write_bytes(pending_path.read_bytes() + b" ")
    elif tamper == "foreign_inode":
        displaced = target_dir.with_name("continuation-run-displaced")
        target_dir.rename(displaced)
        shutil.copytree(displaced, target_dir)
    elif tamper == "missing_sidecar":
        sidecar.unlink()
    elif tamper == "expired":
        owner = legacy.read_json_file(sidecar)
        owner["created_at"] = "2000-01-01T00:00:00Z"
        legacy.write_json_file(sidecar, owner)
    elif tamper == "extra_member":
        (target_dir / "foreign.txt").write_text("foreign\n", encoding="utf-8")
    elif tamper == "wrong_run_id":
        pending = legacy.read_json_file(pending_path)
        pending["run_id"] = "other-run"
        legacy.write_json_file(pending_path, pending)
        owner = legacy.read_json_file(sidecar)
        owner["run_sha256"] = (
            "sha256:" + hashlib.sha256(pending_path.read_bytes()).hexdigest()
        )
        legacy.write_json_file(sidecar, owner)
    else:
        raise AssertionError(f"unhandled tamper case: {tamper}")

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        result = reconcile_once(tmp_path, store, include_worktrees=False)
        failures = [
            row
            for row in store.fetch_all("failures")
            if row.get("run_id") == "continuation-run"
        ]
    retried = execute_action(request, tmp_path)

    assert result.decision_for("continuation-run") is not None
    assert failures
    assert retried.result_class is not ActionResultClass.SUCCESS
    assert not (target_dir / "run.json").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phase", "not-a-contract-phase"),
        ("requirement", "forged continuation requirement"),
    ],
)
def test_reconcile_rejects_semantically_modified_pending_with_rehashed_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    from scripts.loop_supervisor.executor import execute_action
    from scripts.loop_supervisor.reconciler import reconcile_once
    from scripts.loop_supervisor.store import SupervisorStore

    request = _continuation_request(tmp_path)
    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        reconcile_once(tmp_path, store, include_worktrees=False)
        store.enqueue_action(request)
    target_dir, sidecar = _seed_hard_crash_pending_continuation(
        tmp_path, request, monkeypatch
    )
    pending_path = target_dir / "run.pending"
    pending = legacy.read_json_file(pending_path)
    pending[field] = value
    legacy.write_json_file(pending_path, pending)
    pending_bytes = pending_path.read_bytes()
    partial_size = max(1, len(pending_bytes) // 2)
    owner = legacy.read_json_file(sidecar)
    owner["run_sha256"] = "sha256:" + hashlib.sha256(pending_bytes).hexdigest()
    owner["partial_run_sha256"] = (
        "sha256:" + hashlib.sha256(pending_bytes[:partial_size]).hexdigest()
    )
    legacy.write_json_file(sidecar, owner)

    with SupervisorStore.open(tmp_path) as store:
        result = reconcile_once(tmp_path, store, include_worktrees=False)
        failures = [
            row
            for row in store.fetch_all("failures")
            if row.get("run_id") == "continuation-run"
        ]
    retried = execute_action(request, tmp_path)

    assert result.decision_for("continuation-run") is not None
    assert failures
    assert retried.result_class is not ActionResultClass.SUCCESS
    assert not (target_dir / "run.json").exists()


def test_continuation_revision_zero_repair_reconciles_after_projection(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.executor import execute_action
    from scripts.loop_supervisor.reconciler import reconcile_once
    from scripts.loop_supervisor.store import SupervisorStore

    request = _continuation_request(tmp_path)
    incomplete = _seed_incomplete_continuation(tmp_path)
    incomplete["state_revision"] = 0
    legacy.write_json_file(
        legacy.run_dir_for(tmp_path, "continuation-run") / "run.json",
        incomplete,
    )

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        observed = reconcile_once(tmp_path, store, include_worktrees=False)
        assert observed.decision_for("continuation-run") is None
        assert store.get_run("continuation-run")["revision"] == 0

        repaired = execute_action(request, tmp_path)
        reconciled = reconcile_once(tmp_path, store, include_worktrees=False)

        continuation = legacy.load_run(tmp_path, "continuation-run")
        assert repaired.result_class is ActionResultClass.SUCCESS
        assert continuation["state_revision"] == 1
        assert reconciled.decision_for("continuation-run") is None
        assert store.get_run("continuation-run")["revision"] == 1


def test_continuation_retry_rejects_unowned_existing_preflight(tmp_path: Path) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    legacy.create_preflight_run(
        repo_root=tmp_path,
        mode="autonomous_knowledge",
        requirement="Unrelated pre-existing run",
        run_id="continuation-run",
        domain="ai_infra",
        constraints=["preserve provenance"],
        stop_conditions=["stopped_budget"],
        confirm=True,
    )
    target = legacy.run_dir_for(tmp_path, "continuation-run") / "run.json"
    existing_bytes = target.read_bytes()

    result = execute_action(request, tmp_path)

    assert result.result_class is not ActionResultClass.SUCCESS
    assert "ownership state mismatch" in result.summary
    assert "requirement" in result.summary
    assert target.read_bytes() == existing_bytes


def test_continuation_retry_does_not_repair_altered_baseline(tmp_path: Path) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    incomplete = _seed_incomplete_continuation(tmp_path)
    incomplete["baseline_dirty_paths"] = ["?? unowned-change.txt"]
    target = legacy.run_dir_for(tmp_path, "continuation-run") / "run.json"
    legacy.write_json_file(target, incomplete)
    existing_bytes = target.read_bytes()

    result = execute_action(request, tmp_path)

    assert result.result_class is not ActionResultClass.SUCCESS
    assert "baseline_dirty_paths" in result.summary
    assert target.read_bytes() == existing_bytes


def test_continuation_retry_rejects_observation_field_on_incomplete_target(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    incomplete = _seed_incomplete_continuation(tmp_path)
    incomplete["state_revision"] = 0
    incomplete["updated_at"] = "2026-07-16T00:00:00Z"
    target = legacy.run_dir_for(tmp_path, "continuation-run") / "run.json"
    legacy.write_json_file(target, incomplete)
    existing_bytes = target.read_bytes()

    result = execute_action(request, tmp_path)

    assert result.result_class is not ActionResultClass.SUCCESS
    assert "updated_at" in result.summary
    assert target.read_bytes() == existing_bytes


def test_continuation_retry_does_not_repair_altered_preflight_document(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    _seed_incomplete_continuation(tmp_path)
    target_dir = legacy.run_dir_for(tmp_path, "continuation-run")
    target = target_dir / "run.json"
    preflight = target_dir / "preflight.md"
    preflight.write_text(
        preflight.read_text(encoding="utf-8") + "\nUntrusted appended content.\n",
        encoding="utf-8",
    )
    existing_bytes = target.read_bytes()
    existing_preflight_bytes = preflight.read_bytes()

    result = execute_action(request, tmp_path)

    assert result.result_class is not ActionResultClass.SUCCESS
    assert "preflight.md" in result.summary
    assert target.read_bytes() == existing_bytes
    assert preflight.read_bytes() == existing_preflight_bytes


def test_continuation_preflight_allows_created_at_shaped_requirement_line(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    requirement = (
        "Continue the trusted lineage.\n\n"
        "- Created At: `2026-07-01T12:34:56Z`\n\n"
        "Preserve this requirement metadata example."
    )
    request = _continuation_request(tmp_path, requirement=requirement)

    result = execute_action(request, tmp_path)

    assert result.result_class is ActionResultClass.SUCCESS
    continuation = legacy.load_run(tmp_path, "continuation-run")
    assert continuation["requirement"] == requirement
    assert continuation["state_revision"] == 1


def test_continuation_creation_does_not_overwrite_existing_target_directory(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    target_dir = legacy.run_dir_for(tmp_path, "continuation-run")
    target_dir.mkdir(parents=True)
    marker = target_dir / "preflight.md"
    marker.write_text("unowned target directory\n", encoding="utf-8")

    result = execute_action(request, tmp_path)

    assert result.result_class is not ActionResultClass.SUCCESS
    assert "target directory" in result.summary
    assert marker.read_text(encoding="utf-8") == "unowned target directory\n"
    assert not (target_dir / "run.json").exists()


def test_continuation_retry_rejects_malformed_existing_target_revision(
    tmp_path: Path,
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    created = execute_action(request, tmp_path)
    assert created.result_class is ActionResultClass.SUCCESS
    target = legacy.run_dir_for(tmp_path, "continuation-run") / "run.json"
    continuation = legacy.read_json_file(target)
    continuation["state_revision"] = "forged"
    legacy.write_json_file(target, continuation)
    existing_bytes = target.read_bytes()

    result = execute_action(request, tmp_path)

    assert result.result_class is not ActionResultClass.SUCCESS
    assert "state_revision" in result.summary
    assert target.read_bytes() == existing_bytes


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phase", "generating"),
        ("next_action", "run_autonomous_generator"),
        (
            "attempts",
            {
                "planner": 1,
                "generator": 0,
                "evaluator": 0,
                "artifact_hygiene": 0,
                "cleanup": 0,
            },
        ),
        ("limits", {**legacy.default_limits(), "max_tasks_per_run": 99}),
        ("allowed_paths", ["unowned/**"]),
        (
            "cleanup",
            {
                "worktrees_removed": [],
                "processes_stopped": [],
                "retained_artifacts": ["unowned-artifact"],
            },
        ),
    ],
)
def test_continuation_replay_rejects_mutated_completed_state(
    tmp_path: Path, field: str, value: object
) -> None:
    from scripts.loop_supervisor.executor import execute_action

    request = _continuation_request(tmp_path)
    created = execute_action(request, tmp_path)
    assert created.result_class is ActionResultClass.SUCCESS
    target = legacy.run_dir_for(tmp_path, "continuation-run") / "run.json"
    continuation = legacy.read_json_file(target)
    continuation[field] = value
    legacy.write_json_file(target, continuation)
    existing_bytes = target.read_bytes()

    replayed = execute_action(request, tmp_path)

    assert replayed.result_class is not ActionResultClass.SUCCESS
    assert field in replayed.summary
    assert target.read_bytes() == existing_bytes


def test_dirty_path_recovery_never_routes_to_partial_generator_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.loop_supervisor import executor

    request = ActionRequest(
        action_id="action-dirty-path-recovery",
        run_id="run-1",
        run_revision=69,
        policy="autonomous_knowledge",
        phase="stopped_blocked",
        action_type=ActionType.RECOVER_GENERATOR_RESULT,
        idempotency_key="dirty-path-recovery",
        next_action="inspect_autonomous_dirty_paths",
        payload={
            "recovery_failure_key": "worker:dirty-path-gate:RuntimeError",
            "recovery_for_action_type": ActionType.RUN_GENERATOR.value,
        },
    )
    calls: list[str] = []

    def bounded(_root: Path, actual: ActionRequest) -> ActionResult:
        calls.append(actual.next_action)
        return ActionResult(ActionResultClass.SUCCESS, "bounded dirty-path recovery")

    monkeypatch.setattr(legacy, "_run_bounded_generator_recovery", bounded)
    monkeypatch.setattr(
        executor,
        "inspect_partial_artifacts",
        lambda *_args, **_kwargs: pytest.fail("partial Generator inspection was used"),
    )

    result = executor._recover_generator_result(tmp_path, request)

    assert result.result_class is ActionResultClass.SUCCESS
    assert calls == ["inspect_autonomous_dirty_paths"]


def test_executor_source_does_not_drive_multi_round_entrypoints() -> None:
    from scripts.loop_supervisor import executor

    source = inspect.getsource(executor)
    assert "run_" + "autonomous(" not in source
    assert "run_" + "demand_multi(" not in source
    assert "run_" + "loop(" not in source


def test_legacy_multi_round_and_auditor_runtime_surfaces_are_removed() -> None:
    removed_files = (
        Path("scripts/harness_loop_phase2_smoke.py"),
        Path("scripts/harness_loop_phase3_smoke.py"),
        Path("scripts/harness_ai_infra_meta_loop_smoke.py"),
        Path("scripts/harness_loop_auditor.py"),
    )
    assert all(not path.exists() for path in removed_files)
    assert all(
        not hasattr(legacy, name)
        for name in ("_run_loop", "_run_autonomous", "_run_demand_multi", "_run_auditor")
    )
