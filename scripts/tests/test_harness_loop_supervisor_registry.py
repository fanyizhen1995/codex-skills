from scripts.harness_loop_contracts import ALLOWED_PHASES
from scripts.loop_supervisor.models import ActionType
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


def test_nonterminal_allowed_phases_are_represented_in_registry():
    terminal_phases = {"passed", "stopped_no_action", "audit_passed"}
    covered_phases = {phase for _, phase, _ in REGISTRY}

    assert ALLOWED_PHASES - terminal_phases <= covered_phases
