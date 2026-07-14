"""Dispatch one Supervisor action to exactly one bounded phase primitive."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping

import scripts.harness_loop_orchestrator as legacy

from .models import ActionRequest, ActionResult, ActionResultClass, ActionType
from .recovery import inspect_partial_artifacts, reconstruct_result_envelope
from .registry import worker_executable_action_types


ActionHandler = Callable[[Path, ActionRequest], ActionResult]


def executable_action_types() -> set[ActionType]:
    return set(worker_executable_action_types())


BOUNDED_PRIMITIVE_NAMES: Mapping[ActionType, str] = {
    ActionType.RUN_PLANNER: "run_bounded_planner",
    ActionType.RUN_GENERATOR: "run_bounded_generator",
    ActionType.RUN_EVALUATOR: "run_bounded_evaluator",
    ActionType.RUN_EVIDENCE_GATE: "run_bounded_evidence_gate",
    ActionType.RUN_ARTIFACT_HYGIENE: "run_bounded_artifact_hygiene",
    ActionType.COMMIT: "run_bounded_commit",
    ActionType.PUSH: "run_bounded_push",
    ActionType.CLEANUP: "run_bounded_cleanup",
    ActionType.CREATE_CONTINUATION: "run_bounded_continuation",
    ActionType.RECOVER_GENERATOR_RESULT: "run_bounded_generator_recovery",
    ActionType.RUN_ALTERNATE_RECOVERY: "run_bounded_alternate_recovery",
}


def _call_primitive(name: str, repo_root: Path, request: ActionRequest) -> ActionResult:
    primitive = getattr(legacy, name)
    result = primitive(Path(repo_root).resolve(), request)
    if not isinstance(result, ActionResult):
        raise TypeError(f"bounded primitive {name} did not return ActionResult")
    return result


def _run_planner(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_planner", repo_root, request)


def _run_generator(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_generator", repo_root, request)


def _run_evaluator(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_evaluator", repo_root, request)


def _run_evidence_gate(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_evidence_gate", repo_root, request)


def _run_artifact_hygiene(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_artifact_hygiene", repo_root, request)


def _commit(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_commit", repo_root, request)


def _push(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_push", repo_root, request)


def _cleanup(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_cleanup", repo_root, request)


def _create_continuation(repo_root: Path, request: ActionRequest) -> ActionResult:
    return _call_primitive("run_bounded_continuation", repo_root, request)


def _recover_generator_result(repo_root: Path, request: ActionRequest) -> ActionResult:
    if not request.payload.get("recovery_failure_key"):
        return _call_primitive("run_bounded_generator_recovery", repo_root, request)
    run = legacy.load_run(repo_root, request.run_id)
    assessment = inspect_partial_artifacts(repo_root, run, ActionType.RUN_GENERATOR)
    failure_key = str(request.payload.get("recovery_failure_key") or "")
    if assessment.status != "recoverable":
        result_class = (
            ActionResultClass.POLICY_BLOCK
            if assessment.status == "unsafe"
            else ActionResultClass.TERMINAL_FAILURE
        )
        if assessment.status == "unsafe":
            run[assessment.safety_signal or "user_decision_required"] = True
            legacy.save_run(repo_root, run)
        return ActionResult(
            result_class=result_class,
            summary="; ".join(assessment.missing_checks),
            failure_key=failure_key or f"recovery:{request.run_id}:partial",
            error_class=f"partial_artifact_{assessment.status}",
        )
    path = reconstruct_result_envelope(repo_root, assessment)
    run["phase"] = "evaluating"
    run["next_action"] = "run_autonomous_evaluator"
    run["last_result"] = "none"
    legacy.save_run(repo_root, run)
    return ActionResult(
        result_class=ActionResultClass.SUCCESS,
        summary="reconstructed Generator result; independent Evaluator required",
        artifact_paths=(path.resolve().relative_to(repo_root.resolve()).as_posix(),),
        checkpoint="generator-recovery:evaluator-required",
    )


def _run_alternate_recovery(repo_root: Path, request: ActionRequest) -> ActionResult:
    failure_key = str(request.payload.get("recovery_failure_key") or "")
    if not failure_key:
        return _call_primitive("run_bounded_alternate_recovery", repo_root, request)
    run = legacy.load_run(repo_root, request.run_id)
    directives = run.setdefault("recovery_directives", [])
    if not isinstance(directives, list):
        return ActionResult(
            result_class=ActionResultClass.TERMINAL_FAILURE,
            summary="run recovery_directives is not a list",
            failure_key=failure_key,
            error_class="invalid_recovery_state",
        )
    directive = {
        "failure_key": failure_key,
        "source_action_id": str(request.payload.get("source_action_id") or ""),
        "source_action_type": str(
            request.payload.get("recovery_for_action_type") or ""
        ),
        "strategy": str(request.payload.get("recovery_strategy") or ""),
        "excluded_approach": failure_key,
    }
    if directive not in directives:
        directives.append(directive)
    if request.policy == "autonomous_knowledge":
        run["phase"] = "planning"
        run["next_action"] = "run_autonomous_planner"
    elif run.get("run_kind") == "parent":
        run["phase"] = "planning"
        run["next_action"] = "run_parent_planner"
    elif run.get("run_kind") == "child":
        run["phase"] = "repair_needed"
        run["next_action"] = "run_generator"
    else:
        run["phase"] = "planned"
        run["next_action"] = "run_planner"
    run["last_result"] = "none"
    legacy.save_run(repo_root, run)
    return ActionResult(
        result_class=ActionResultClass.SUCCESS,
        summary="recorded bounded replan excluding the failed approach",
        checkpoint="alternate-recovery:replan",
    )


ACTION_HANDLERS: Mapping[ActionType, ActionHandler] = {
    ActionType.RUN_PLANNER: _run_planner,
    ActionType.RUN_GENERATOR: _run_generator,
    ActionType.RUN_EVALUATOR: _run_evaluator,
    ActionType.RUN_EVIDENCE_GATE: _run_evidence_gate,
    ActionType.RUN_ARTIFACT_HYGIENE: _run_artifact_hygiene,
    ActionType.COMMIT: _commit,
    ActionType.PUSH: _push,
    ActionType.CLEANUP: _cleanup,
    ActionType.CREATE_CONTINUATION: _create_continuation,
    ActionType.RECOVER_GENERATOR_RESULT: _recover_generator_result,
    ActionType.RUN_ALTERNATE_RECOVERY: _run_alternate_recovery,
}


if set(ACTION_HANDLERS) != executable_action_types():
    missing = executable_action_types() - set(ACTION_HANDLERS)
    extra = set(ACTION_HANDLERS) - executable_action_types()
    raise RuntimeError(
        f"bounded handler coverage mismatch; missing={sorted(missing)} extra={sorted(extra)}"
    )


def execute_action(request: ActionRequest, repo_root: Path) -> ActionResult:
    if not isinstance(request, ActionRequest):
        raise TypeError("request must be an ActionRequest")
    handler = ACTION_HANDLERS.get(request.action_type)
    if handler is None:
        raise ValueError(f"action type is not executable: {request.action_type.value}")
    return handler(Path(repo_root).resolve(), request)
