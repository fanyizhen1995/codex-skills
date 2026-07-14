"""The single table-driven phase transition registry."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from scripts.harness_loop_contracts import (
    ALLOWED_PHASES,
    ALLOWED_POLICIES,
    SUPERVISOR_TERMINAL_PHASES,
    normalize_policy_id,
)

from .models import ActionResultClass, ActionType, ResultHandling, TransitionRule


ANY_NEXT_ACTION = object()

_DEFAULT_RULES = {
    "preflight": TransitionRule(ActionType.ASK_USER, False, user_escalation=True),
    "planned": TransitionRule(ActionType.RUN_GENERATOR, True),
    "generating": TransitionRule(ActionType.RUN_GENERATOR, True),
    "verifying": TransitionRule(ActionType.RUN_EVIDENCE_GATE, False),
    "evaluating": TransitionRule(ActionType.RUN_EVALUATOR, False),
    "repair_needed": TransitionRule(ActionType.RUN_GENERATOR, True),
    "artifact_hygiene": TransitionRule(ActionType.RUN_ARTIFACT_HYGIENE, False),
    "cleanup": TransitionRule(ActionType.CLEANUP, False),
    "passed_waiting_human_merge": TransitionRule(ActionType.ASK_USER, False, user_escalation=True),
    "planning": TransitionRule(ActionType.RUN_PLANNER, True),
    "committed": TransitionRule(ActionType.PUSH, True),
    "stopped_budget": TransitionRule(ActionType.CREATE_CONTINUATION, False),
    "stopped_blocked": TransitionRule(ActionType.ASK_USER, False, user_escalation=True),
    "audit_pending": TransitionRule(ActionType.RUN_REVIEWER, False),
    "auditing": TransitionRule(ActionType.RUN_REVIEWER, False),
    "audit_blocked": TransitionRule(ActionType.RUN_ALTERNATE_RECOVERY, True),
    "child_running": TransitionRule(ActionType.RUN_PLANNER, True),
}

_TERMINAL_RULE = TransitionRule(
    ActionType.NO_OP,
    False,
    allowed_result_classes=frozenset({ActionResultClass.SUCCESS}),
    result_handling={ActionResultClass.SUCCESS: ResultHandling.NO_OP},
    terminal=True,
)

_registry: dict[tuple[str, str, object], TransitionRule] = {
    (policy, phase, ANY_NEXT_ACTION): rule
    for policy in ALLOWED_POLICIES
    for phase, rule in _DEFAULT_RULES.items()
}
_registry.update(
    {
        (policy, phase, ANY_NEXT_ACTION): _TERMINAL_RULE
        for policy in ALLOWED_POLICIES
        for phase in SUPERVISOR_TERMINAL_PHASES
    }
)
_registry.update(
    {
        ("autonomous_knowledge", "planning", "run_autonomous_planner"): TransitionRule(ActionType.RUN_PLANNER, True),
        ("autonomous_knowledge", "generating", "run_autonomous_generator"): TransitionRule(ActionType.RUN_GENERATOR, True),
        ("autonomous_knowledge", "evaluating", "run_autonomous_evaluator"): TransitionRule(ActionType.RUN_EVALUATOR, False),
        ("autonomous_knowledge", "stopped_blocked", "inspect_autonomous_generator"): TransitionRule(
            ActionType.RECOVER_GENERATOR_RESULT,
            True,
            user_escalation=False,
        ),
        ("demand_development", "planned", "run_generator"): TransitionRule(ActionType.RUN_GENERATOR, True),
        ("demand_development", "evaluating", "run_evaluator"): TransitionRule(ActionType.RUN_EVALUATOR, False),
    }
)
REGISTRY: Mapping[tuple[str, str, object], TransitionRule] = MappingProxyType(dict(_registry))


def transition_for(policy: str, phase: str, next_action: str) -> TransitionRule:
    """Return the explicit rule for one normalized run state."""
    normalized_policy = normalize_policy_id(policy)
    rule = REGISTRY.get((normalized_policy, phase, next_action))
    if rule is None:
        rule = REGISTRY.get((normalized_policy, phase, ANY_NEXT_ACTION))
    if rule is None:
        raise ValueError(f"no supervisor transition for {normalized_policy}:{phase}:{next_action}")
    return rule


def validate_registry_coverage(
    registry: Mapping[tuple[str, str, object], TransitionRule] | None = None,
) -> None:
    """Reject registry drift from the run schema before Supervisor starts."""
    active_registry = REGISTRY if registry is None else registry
    invalid_terminal_phases = SUPERVISOR_TERMINAL_PHASES - ALLOWED_PHASES
    if invalid_terminal_phases:
        raise ValueError(f"terminal phases are not contract allowed: {sorted(invalid_terminal_phases)}")

    invalid_entries = [
        (policy, phase)
        for policy, phase, _ in active_registry
        if policy not in ALLOWED_POLICIES or phase not in ALLOWED_PHASES
    ]
    if invalid_entries:
        raise ValueError(f"registry contains unsupported policy or phase: {invalid_entries}")

    missing = [
        f"{policy}:{phase}"
        for policy in sorted(ALLOWED_POLICIES)
        for phase in sorted(ALLOWED_PHASES)
        if not any(
            entry_policy == policy and entry_phase == phase
            for entry_policy, entry_phase, _ in active_registry
        )
    ]
    if missing:
        raise ValueError(f"registry lacks behavior for allowed phases: {', '.join(missing)}")

    invalid_terminal_rules = [
        f"{policy}:{phase}:{next_action}"
        for (policy, phase, next_action), rule in active_registry.items()
        if phase in SUPERVISOR_TERMINAL_PHASES and not rule.terminal
    ]
    if invalid_terminal_rules:
        raise ValueError(f"registry lacks terminal behavior for allowed phases: {', '.join(invalid_terminal_rules)}")
