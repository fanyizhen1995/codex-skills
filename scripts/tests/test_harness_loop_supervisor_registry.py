import pytest

from scripts.harness_loop_contracts import ALLOWED_PHASES, ALLOWED_POLICIES, SUPERVISOR_TERMINAL_PHASES
from scripts.loop_supervisor.models import ActionResultClass, ActionType, ResultHandling
from scripts.loop_supervisor.registry import ANY_NEXT_ACTION, REGISTRY, transition_for, validate_registry_coverage


def test_every_allowed_parent_phase_has_registry_behavior():
    validate_registry_coverage()


def test_generator_inspection_maps_to_recovery_not_user_decision():
    rule = transition_for("autonomous_knowledge", "stopped_blocked", "inspect_autonomous_generator")

    assert rule.action_type is ActionType.RECOVER_GENERATOR_RESULT
    assert rule.user_escalation is False


def test_wildcard_next_actions_are_explicit_registry_entries():
    assert any(next_action is ANY_NEXT_ACTION for _, _, next_action in REGISTRY)
    assert transition_for("demand_development", "generating", "run_generator").action_type is ActionType.RUN_GENERATOR


def test_every_allowed_phase_is_represented_in_registry():
    covered_phases = {phase for _, phase, _ in REGISTRY}

    assert ALLOWED_PHASES <= covered_phases


def test_terminal_phases_have_explicit_noop_terminal_rules():
    for policy in ALLOWED_POLICIES:
        for phase in SUPERVISOR_TERMINAL_PHASES:
            rule = REGISTRY[(policy, phase, ANY_NEXT_ACTION)]

            assert rule.terminal is True
            assert rule.action_type is ActionType.NO_OP
            assert rule.allowed_result_classes == frozenset({ActionResultClass.SUCCESS})
            assert rule.result_handling == {ActionResultClass.SUCCESS: ResultHandling.NO_OP}


def test_registry_is_read_only():
    with pytest.raises(TypeError):
        REGISTRY[("autonomous_knowledge", "planning", "unexpected")] = transition_for(
            "autonomous_knowledge", "planning", "run_autonomous_planner"
        )


def test_coverage_rejects_nonterminal_exact_override_for_terminal_phase():
    invalid_registry = dict(REGISTRY)
    invalid_registry[("autonomous_knowledge", "passed", "unexpected")] = transition_for(
        "autonomous_knowledge", "planning", "run_autonomous_planner"
    )

    with pytest.raises(ValueError, match="terminal"):
        validate_registry_coverage(invalid_registry)
