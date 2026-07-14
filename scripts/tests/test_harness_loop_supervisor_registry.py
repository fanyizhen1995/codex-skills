import pytest

from scripts.harness_loop_contracts import ALLOWED_PHASES, ALLOWED_POLICIES, SUPERVISOR_TERMINAL_PHASES
from scripts.loop_supervisor.models import ActionResultClass, ActionType, ResultHandling, TransitionRule
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


def test_demand_planned_routes_planner_and_child_generator_exactly():
    planner = transition_for("demand_development", "planned", "run_planner")
    child_generator = transition_for("demand_development", "planned", "run_generator")

    assert planner.action_type is ActionType.RUN_PLANNER
    assert planner.mutates_git is True
    assert child_generator.action_type is ActionType.RUN_GENERATOR
    assert child_generator.mutates_git is True


def test_autonomous_commit_cleanup_and_push_are_distinct_exact_actions():
    commit = transition_for(
        "autonomous_knowledge", "cleanup", "commit_autonomous_changes"
    )
    cleanup = transition_for("autonomous_knowledge", "cleanup", "run_cleanup")
    push = transition_for(
        "autonomous_knowledge", "committed", "push_autonomous_commit"
    )

    assert commit.action_type is ActionType.COMMIT
    assert commit.mutates_git is True
    assert cleanup.action_type is ActionType.CLEANUP
    assert cleanup.mutates_git is False
    assert push.action_type is ActionType.PUSH
    assert push.mutates_git is True
    assert transition_for(
        "autonomous_knowledge", "stopped_blocked", "retry_autonomous_push"
    ).action_type is not ActionType.CLEANUP


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


@pytest.mark.parametrize(
    ("next_action", "rule"),
    [
        (
            ANY_NEXT_ACTION,
            TransitionRule(
                ActionType.NO_OP,
                True,
                allowed_result_classes=frozenset({ActionResultClass.SUCCESS}),
                result_handling={ActionResultClass.SUCCESS: ResultHandling.NO_OP},
                terminal=True,
            ),
        ),
        (
            "unexpected",
            TransitionRule(
                ActionType.NO_OP,
                False,
                allowed_result_classes=frozenset({ActionResultClass.SUCCESS}),
                result_handling={ActionResultClass.SUCCESS: ResultHandling.NO_OP},
                terminal=True,
                user_escalation=True,
            ),
        ),
    ],
)
def test_coverage_rejects_noncanonical_terminal_wildcard_and_exact_entries(next_action, rule):
    invalid_registry = dict(REGISTRY)
    invalid_registry[("autonomous_knowledge", "passed", next_action)] = rule

    with pytest.raises(ValueError, match="canonical terminal"):
        validate_registry_coverage(invalid_registry)


def test_coverage_requires_canonical_terminal_wildcard_entries():
    invalid_registry = dict(REGISTRY)
    wildcard_key = ("autonomous_knowledge", "passed", ANY_NEXT_ACTION)
    invalid_registry[("autonomous_knowledge", "passed", "unexpected")] = invalid_registry.pop(wildcard_key)

    with pytest.raises(ValueError, match="terminal wildcard"):
        validate_registry_coverage(invalid_registry)
