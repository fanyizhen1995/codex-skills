"""Strict value objects shared by Supervisor and Worker components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class ActionType(StrEnum):
    NO_OP = "no_op"
    RUN_PLANNER = "run_planner"
    RUN_GENERATOR = "run_generator"
    RUN_EVALUATOR = "run_evaluator"
    RUN_EVIDENCE_GATE = "run_evidence_gate"
    RUN_ARTIFACT_HYGIENE = "run_artifact_hygiene"
    COMMIT = "commit"
    PUSH = "push"
    CLEANUP = "cleanup"
    CREATE_CONTINUATION = "create_continuation"
    RESTART_SERVICE = "restart_service"
    RECOVER_PARTIAL_ARTIFACT = "recover_partial_artifact"
    RECOVER_GENERATOR_RESULT = "recover_generator_result"
    RUN_ALTERNATE_RECOVERY = "run_alternate_recovery"
    RUN_REVIEWER = "run_reviewer"
    REFOCUS_RUN = "refocus_run"
    STOP_RUN = "stop_run"
    ASK_USER = "ask_user"


class ActionStatus(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionResultClass(StrEnum):
    SUCCESS = "success"
    RETRYABLE_FAILURE = "retryable_failure"
    RECOVERABLE_PARTIAL = "recoverable_partial"
    POLICY_BLOCK = "policy_block"
    TERMINAL_FAILURE = "terminal_failure"


class ResultHandling(StrEnum):
    ADVANCE = "advance"
    CLASSIFIED_RETRY = "classified_retry"
    ARTIFACT_RECOVERY = "artifact_recovery"
    SAFETY_DECISION = "safety_decision"
    REVIEWER_OR_USER = "reviewer_or_user"
    NO_OP = "no_op"
    STOP = "stop"


class ReviewDecision(StrEnum):
    CONTINUE = "continue"
    AUTO_REMEDIATE = "auto_remediate"
    REFOCUS = "refocus"
    STOP_RUN = "stop_run"
    ASK_USER = "ask_user"


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    run_id: str
    policy: str
    phase: str
    action_type: ActionType
    idempotency_key: str
    task_id: str = ""
    next_action: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    result_class: ActionResultClass
    summary: str
    failure_key: str = ""
    error_class: str = ""
    artifact_paths: tuple[str, ...] = ()
    checkpoint: str = ""
    started_at: str = ""
    finished_at: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.result_class, ActionResultClass):
            raise TypeError("result_class must be an ActionResultClass")
        if self.result_class is not ActionResultClass.SUCCESS and not self.failure_key:
            raise ValueError("non-success ActionResult requires failure_key")


DEFAULT_RESULT_HANDLING: Mapping[ActionResultClass, ResultHandling] = MappingProxyType(
    {
        ActionResultClass.SUCCESS: ResultHandling.ADVANCE,
        ActionResultClass.RETRYABLE_FAILURE: ResultHandling.CLASSIFIED_RETRY,
        ActionResultClass.RECOVERABLE_PARTIAL: ResultHandling.ARTIFACT_RECOVERY,
        ActionResultClass.POLICY_BLOCK: ResultHandling.SAFETY_DECISION,
        ActionResultClass.TERMINAL_FAILURE: ResultHandling.REVIEWER_OR_USER,
    }
)


@dataclass(frozen=True)
class TransitionRule:
    action_type: ActionType
    mutates_git: bool
    allowed_result_classes: frozenset[ActionResultClass] = frozenset(ActionResultClass)
    result_handling: Mapping[ActionResultClass, ResultHandling] = field(
        default_factory=lambda: DEFAULT_RESULT_HANDLING
    )
    terminal: bool = False
    user_escalation: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            raise TypeError("action_type must be an ActionType")
        if not self.allowed_result_classes or not all(
            isinstance(result_class, ActionResultClass) for result_class in self.allowed_result_classes
        ):
            raise TypeError("allowed_result_classes must contain ActionResultClass values")
        if set(self.result_handling) != set(self.allowed_result_classes):
            raise ValueError("result_handling must cover exactly the allowed result classes")
        if not all(isinstance(handling, ResultHandling) for handling in self.result_handling.values()):
            raise TypeError("result_handling must contain ResultHandling values")
        if self.terminal:
            if self.action_type not in {ActionType.NO_OP, ActionType.STOP_RUN}:
                raise ValueError("terminal TransitionRule must use a no-op or stop action")
            terminal_handlings = {ResultHandling.NO_OP, ResultHandling.STOP}
            if not set(self.result_handling.values()) <= terminal_handlings:
                raise ValueError("terminal TransitionRule must use no-op or stop handling")
