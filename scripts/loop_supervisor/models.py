"""Strict value objects shared by Supervisor and Worker components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class ActionType(StrEnum):
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
        if self.result_class is not ActionResultClass.SUCCESS and not self.failure_key:
            raise ValueError("non-success ActionResult requires failure_key")


@dataclass(frozen=True)
class TransitionRule:
    action_type: ActionType
    mutates_git: bool
    allowed_result_classes: frozenset[ActionResultClass] = frozenset(ActionResultClass)
    recovery_policy: str = "classified_retry"
    terminal: bool = False
    user_escalation: bool = False
