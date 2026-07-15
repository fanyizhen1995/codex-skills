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

from .models import (
    ActionResultClass,
    ActionType,
    RecoveryStage,
    RecoveryTransitionRule,
    ReviewApplicationRule,
    ReviewDecision,
    ResultHandling,
    TransitionRule,
)


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
    "audit_pending": TransitionRule(ActionType.NO_OP, False, worker_executable=False),
    "auditing": TransitionRule(ActionType.NO_OP, False, worker_executable=False),
    "audit_blocked": TransitionRule(ActionType.NO_OP, False, worker_executable=False),
    "child_running": TransitionRule(ActionType.RUN_PLANNER, True),
}

_TERMINAL_RULE = TransitionRule(
    ActionType.NO_OP,
    False,
    worker_executable=False,
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
        ("autonomous_knowledge", "cleanup", "commit_autonomous_changes"): TransitionRule(ActionType.COMMIT, True),
        ("autonomous_knowledge", "cleanup", "run_cleanup"): TransitionRule(ActionType.CLEANUP, False),
        ("autonomous_knowledge", "committed", "push_autonomous_commit"): TransitionRule(ActionType.PUSH, True),
        ("autonomous_knowledge", "stopped_blocked", "inspect_autonomous_generator"): TransitionRule(
            ActionType.RECOVER_GENERATOR_RESULT,
            True,
            user_escalation=False,
        ),
        ("autonomous_knowledge", "stopped_blocked", "inspect_autonomous_dirty_paths"): TransitionRule(
            ActionType.RECOVER_GENERATOR_RESULT,
            True,
            user_escalation=False,
        ),
        ("autonomous_knowledge", "stopped_blocked", "inspect_required_evidence"): TransitionRule(
            ActionType.RECOVER_GENERATOR_RESULT,
            True,
            user_escalation=False,
        ),
        ("autonomous_knowledge", "stopped_blocked", "inspect_autonomous_commit"): TransitionRule(
            ActionType.RECOVER_GENERATOR_RESULT,
            True,
            user_escalation=False,
        ),
        ("autonomous_knowledge", "stopped_blocked", "retry_autonomous_push"): TransitionRule(
            ActionType.RECOVER_GENERATOR_RESULT,
            True,
            user_escalation=False,
        ),
        ("demand_development", "planned", "run_planner"): TransitionRule(ActionType.RUN_PLANNER, True),
        ("demand_development", "planned", "run_generator"): TransitionRule(ActionType.RUN_GENERATOR, True),
        ("demand_development", "evaluating", "run_evaluator"): TransitionRule(ActionType.RUN_EVALUATOR, False),
    }
)
REGISTRY: Mapping[tuple[str, str, object], TransitionRule] = MappingProxyType(dict(_registry))

_REVIEW_DECISION_RULES: Mapping[ReviewDecision, TransitionRule] = MappingProxyType(
    {
        ReviewDecision.CONTINUE: TransitionRule(
            ActionType.NO_OP,
            False,
            worker_executable=False,
        ),
        ReviewDecision.AUTO_REMEDIATE: TransitionRule(
            ActionType.RUN_ALTERNATE_RECOVERY,
            False,
            worker_executable=False,
        ),
        ReviewDecision.REFOCUS: TransitionRule(
            ActionType.REFOCUS_RUN,
            False,
            worker_executable=False,
        ),
        ReviewDecision.STOP_RUN: TransitionRule(
            ActionType.STOP_RUN,
            False,
            worker_executable=False,
        ),
        ReviewDecision.ASK_USER: TransitionRule(
            ActionType.ASK_USER,
            False,
            worker_executable=False,
            user_escalation=True,
        ),
    }
)

_REVIEW_SCHEDULE_RULE = TransitionRule(
    ActionType.RUN_REVIEWER,
    False,
    worker_executable=False,
)

_SERVICE_RESTART_RULE = TransitionRule(
    ActionType.RESTART_SERVICE,
    False,
    worker_executable=False,
)


def transition_for(policy: str, phase: str, next_action: str) -> TransitionRule:
    """Return the explicit rule for one normalized run state."""
    normalized_policy = normalize_policy_id(policy)
    rule = REGISTRY.get((normalized_policy, phase, next_action))
    if rule is None:
        rule = REGISTRY.get((normalized_policy, phase, ANY_NEXT_ACTION))
    if rule is None:
        raise ValueError(f"no supervisor transition for {normalized_policy}:{phase}:{next_action}")
    return rule


def review_transition_for(decision: ReviewDecision) -> TransitionRule:
    """Return the registry-owned action rule for a validated Reviewer decision."""
    if not isinstance(decision, ReviewDecision):
        raise TypeError("decision must be a ReviewDecision")
    return _REVIEW_DECISION_RULES[decision]


def review_application_for(
    decision: ReviewDecision,
    *,
    policy: str,
    run_kind: str,
) -> ReviewApplicationRule:
    """Resolve one validated review decision to its registry-owned target state."""
    transition = review_transition_for(decision)
    if decision is ReviewDecision.CONTINUE:
        return ReviewApplicationRule(transition.action_type, "", "", "", False)
    if decision is ReviewDecision.ASK_USER:
        return ReviewApplicationRule(transition.action_type, "", "", "", False)
    if decision is ReviewDecision.STOP_RUN:
        return ReviewApplicationRule(
            transition.action_type,
            "stopped_by_reviewer",
            "none",
            "blocked",
            True,
        )
    if run_kind == "child":
        raise ValueError("Reviewer refocus and remediation require a parent or single run")
    if policy == "autonomous_knowledge":
        phase, next_action = "planning", "run_autonomous_planner"
    elif run_kind == "parent":
        phase, next_action = "planning", "run_parent_planner"
    else:
        phase, next_action = "planned", "run_planner"
    return ReviewApplicationRule(
        transition.action_type,
        phase,
        next_action,
        "none",
        True,
    )


def reviewer_schedule_transition() -> TransitionRule:
    """Return the registry-owned project-global Reviewer scheduling rule."""
    return _REVIEW_SCHEDULE_RULE


def service_restart_transition() -> TransitionRule:
    """Return the registry-owned project service restart rule."""
    return _SERVICE_RESTART_RULE


def worker_executable_action_types() -> frozenset[ActionType]:
    """Return normal and recovery actions owned by the Worker registry contract."""
    normal = {
        rule.action_type
        for rule in REGISTRY.values()
        if not rule.terminal and not rule.user_escalation and rule.worker_executable
    }
    return frozenset(normal | {ActionType.RUN_ALTERNATE_RECOVERY})


def recovery_transition_for(
    policy: str,
    phase: str,
    next_action: str,
    stage: RecoveryStage,
) -> RecoveryTransitionRule:
    """Return the single registry-owned transition for a recovery stage."""
    if not isinstance(stage, RecoveryStage):
        raise TypeError("stage must be a RecoveryStage")
    source = transition_for(policy, phase, next_action)
    if source.terminal or source.user_escalation:
        raise ValueError("terminal and user-gated transitions cannot enter recovery")
    if stage is RecoveryStage.RETRY:
        return RecoveryTransitionRule(
            action_type=source.action_type,
            mutates_git=source.mutates_git,
            worker_executable=True,
            strategy="retry_same_action",
        )
    if stage is RecoveryStage.ALTERNATE:
        if source.action_type is ActionType.RUN_GENERATOR:
            return RecoveryTransitionRule(
                action_type=ActionType.RECOVER_GENERATOR_RESULT,
                mutates_git=True,
                worker_executable=True,
                strategy="reconstruct_result_envelope",
            )
        return RecoveryTransitionRule(
            action_type=ActionType.RUN_ALTERNATE_RECOVERY,
            mutates_git=False,
            worker_executable=True,
            strategy="replan_excluding_failed_approach",
        )
    return RecoveryTransitionRule(
        action_type=ActionType.RUN_REVIEWER,
        mutates_git=False,
        worker_executable=False,
        strategy="review_recovery_exhaustion",
    )


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

    missing_terminal_wildcards = [
        f"{policy}:{phase}"
        for policy in sorted(ALLOWED_POLICIES)
        for phase in sorted(SUPERVISOR_TERMINAL_PHASES)
        if (policy, phase, ANY_NEXT_ACTION) not in active_registry
    ]
    if missing_terminal_wildcards:
        raise ValueError(
            f"registry lacks terminal wildcard rules: {', '.join(missing_terminal_wildcards)}"
        )

    canonical_terminal_handling = {ActionResultClass.SUCCESS: ResultHandling.NO_OP}
    invalid_terminal_rules = [
        f"{policy}:{phase}:{next_action}"
        for (policy, phase, next_action), rule in active_registry.items()
        if phase in SUPERVISOR_TERMINAL_PHASES
        and not (
            rule.terminal is True
            and rule.action_type is ActionType.NO_OP
            and rule.mutates_git is False
            and rule.allowed_result_classes == frozenset({ActionResultClass.SUCCESS})
            and rule.result_handling == canonical_terminal_handling
            and rule.user_escalation is False
        )
    ]
    if invalid_terminal_rules:
        raise ValueError(f"registry has non-canonical terminal rules: {', '.join(invalid_terminal_rules)}")
