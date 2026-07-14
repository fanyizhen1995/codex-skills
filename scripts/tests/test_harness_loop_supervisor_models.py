import json
import math

import pytest

from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionStatus,
    ActionType,
    ResultHandling,
    ReviewDecision,
    TransitionRule,
)


def test_action_types_cover_all_supervisor_execution_categories():
    expected = {
        "RUN_PLANNER",
        "RUN_GENERATOR",
        "RUN_EVALUATOR",
        "RUN_EVIDENCE_GATE",
        "COMMIT",
        "PUSH",
        "CLEANUP",
        "CREATE_CONTINUATION",
        "RESTART_SERVICE",
        "RECOVER_PARTIAL_ARTIFACT",
        "RECOVER_GENERATOR_RESULT",
        "RUN_ALTERNATE_RECOVERY",
        "RUN_REVIEWER",
        "REFOCUS_RUN",
        "STOP_RUN",
        "ASK_USER",
    }

    assert expected <= set(ActionType.__members__)


def test_action_request_is_immutable_and_carries_transition_identity():
    request = ActionRequest(
        action_id="action-1",
        run_id="run-1",
        run_revision=1,
        policy="autonomous-knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="run-1:1:planning:run_planner",
    )

    assert request.action_type is ActionType.RUN_PLANNER
    assert request.policy == "autonomous_knowledge"
    assert request.run_revision == 1
    assert request.repo_relative_root == "."
    with pytest.raises(AttributeError):
        request.run_id = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("run_revision", True, TypeError),
        ("run_revision", -1, ValueError),
        ("phase", "not_allowed", ValueError),
        ("action_type", "run_planner", TypeError),
        ("action_id", "", ValueError),
        ("run_id", "../escape", ValueError),
        ("repo_relative_root", "../escape", ValueError),
        ("repo_relative_root", "/absolute", ValueError),
    ],
)
def test_action_request_rejects_invalid_execution_fields(field, value, error):
    kwargs = {
        "action_id": "action-1",
        "run_id": "run-1",
        "run_revision": 1,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "action_type": ActionType.RUN_PLANNER,
        "idempotency_key": "run-1:1:planning:run_planner",
    }
    kwargs[field] = value

    with pytest.raises(error):
        ActionRequest(**kwargs)


def test_action_request_accepts_safe_nested_execution_root():
    request = ActionRequest(
        action_id="action-1",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="run-1:1:planning:run_planner",
        repo_relative_root=".worktrees/feature",
    )

    assert request.repo_relative_root == ".worktrees/feature"


def test_frozen_models_snapshot_mutable_inputs_recursively():
    payload = {"nested": {"items": ["before"], "tags": ["before"]}}
    artifact_paths = ["result.json"]
    allowed_results = [ActionResultClass.SUCCESS]
    handling = {ActionResultClass.SUCCESS: ResultHandling.ADVANCE}

    request = ActionRequest(
        action_id="action-1",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="run-1:1:planning:run_planner",
        payload=payload,
    )
    result = ActionResult(
        result_class=ActionResultClass.SUCCESS,
        summary="complete",
        artifact_paths=artifact_paths,
    )
    rule = TransitionRule(
        ActionType.RUN_GENERATOR,
        True,
        allowed_result_classes=allowed_results,
        result_handling=handling,
    )

    payload["nested"]["items"].append("after")
    payload["nested"]["tags"].append("after")
    artifact_paths.append("other.json")
    allowed_results.append(ActionResultClass.TERMINAL_FAILURE)
    handling[ActionResultClass.SUCCESS] = ResultHandling.NO_OP

    assert request.payload["nested"]["items"] == ("before",)
    assert request.payload["nested"]["tags"] == ("before",)
    assert result.artifact_paths == ("result.json",)
    assert rule.allowed_result_classes == frozenset({ActionResultClass.SUCCESS})
    assert rule.result_handling[ActionResultClass.SUCCESS] is ResultHandling.ADVANCE
    with pytest.raises(TypeError):
        request.payload["nested"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        request.payload["nested"]["items"][0] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        rule.result_handling[ActionResultClass.SUCCESS] = ResultHandling.NO_OP  # type: ignore[index]


@pytest.mark.parametrize(
    "payload",
    [
        {1: "non-string-key"},
        {"bytes": bytearray(b"unsafe")},
        {"object": object()},
        {"nan": math.nan},
        {"infinity": math.inf},
        {"set": {"unsafe"}},
    ],
)
def test_action_request_rejects_non_json_safe_payload_values(payload):
    with pytest.raises((TypeError, ValueError)):
        ActionRequest(
            action_id="action-1",
            run_id="run-1",
            run_revision=1,
            policy="autonomous_knowledge",
            phase="planning",
            action_type=ActionType.RUN_PLANNER,
            idempotency_key="run-1:1:planning:run_planner",
            payload=payload,
        )


def test_action_request_payload_for_storage_returns_independent_json_safe_copy():
    payload = {"nested": {"items": ["before"], "number": 1.5, "none": None}}
    request = ActionRequest(
        action_id="action-1",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="run-1:1:planning:run_planner",
        payload=payload,
    )

    payload["nested"]["items"].append("external-change")
    stored = request.payload_for_storage()
    stored["nested"]["items"].append("storage-change")

    assert json.loads(json.dumps(stored)) == {
        "nested": {"items": ["before", "storage-change"], "number": 1.5, "none": None}
    }
    assert request.payload["nested"]["items"] == ("before",)


def test_transition_rule_requires_boolean_control_flags():
    for field in ("mutates_git", "terminal", "user_escalation"):
        kwargs = {"mutates_git": True, "terminal": False, "user_escalation": False}
        kwargs[field] = 1

        with pytest.raises(TypeError, match=field):
            TransitionRule(ActionType.RUN_GENERATOR, **kwargs)


def test_action_result_requires_failure_key_for_non_success():
    with pytest.raises(ValueError, match="failure_key"):
        ActionResult(result_class=ActionResultClass.RETRYABLE_FAILURE, summary="capacity")


def test_action_result_accepts_success_without_failure_key():
    result = ActionResult(result_class=ActionResultClass.SUCCESS, summary="complete")

    assert result.failure_key == ""


def test_action_result_rejects_string_result_class():
    with pytest.raises(TypeError, match="ActionResultClass"):
        ActionResult(result_class="success", summary="complete")  # type: ignore[arg-type]


def test_transition_rule_routes_each_result_class_to_its_own_default_handling():
    rule = TransitionRule(ActionType.RUN_GENERATOR, True)

    assert rule.result_handling[ActionResultClass.SUCCESS] is ResultHandling.ADVANCE
    assert rule.result_handling[ActionResultClass.RETRYABLE_FAILURE] is ResultHandling.CLASSIFIED_RETRY
    assert rule.result_handling[ActionResultClass.RECOVERABLE_PARTIAL] is ResultHandling.ARTIFACT_RECOVERY
    assert rule.result_handling[ActionResultClass.POLICY_BLOCK] is ResultHandling.SAFETY_DECISION
    assert rule.result_handling[ActionResultClass.TERMINAL_FAILURE] is ResultHandling.REVIEWER_OR_USER
    assert len(set(rule.result_handling.values())) == len(ActionResultClass)


def test_status_and_reviewer_decision_use_closed_enums():
    assert ActionStatus.PENDING.value == "pending"
    assert ReviewDecision.ASK_USER.value == "ask_user"
