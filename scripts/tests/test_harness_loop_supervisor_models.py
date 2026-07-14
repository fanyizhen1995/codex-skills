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
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key="run-1:1:planning:run_planner",
    )

    assert request.action_type is ActionType.RUN_PLANNER
    with pytest.raises(AttributeError):
        request.run_id = "other"  # type: ignore[misc]


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
