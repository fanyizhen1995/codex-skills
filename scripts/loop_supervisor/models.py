"""Strict value objects shared by Supervisor and Worker components."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from scripts.harness_loop_contracts import ALLOWED_PHASES, normalize_policy_id


def _require_string(value: object, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must be non-empty")
    return value


def _freeze_value(value: Any) -> Any:
    if isinstance(value, MappingABC):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    return value


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
    run_revision: int
    policy: str
    phase: str
    action_type: ActionType
    idempotency_key: str
    task_id: str = ""
    next_action: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_string(self.action_id, "action_id")
        _require_string(self.run_id, "run_id")
        if not isinstance(self.run_revision, int) or isinstance(self.run_revision, bool):
            raise TypeError("run_revision must be an int")
        if self.run_revision < 0:
            raise ValueError("run_revision must be non-negative")
        _require_string(self.policy, "policy")
        _require_string(self.phase, "phase")
        if self.phase not in ALLOWED_PHASES:
            raise ValueError(f"phase is not contract allowed: {self.phase}")
        if not isinstance(self.action_type, ActionType):
            raise TypeError("action_type must be an ActionType")
        _require_string(self.idempotency_key, "idempotency_key")
        _require_string(self.task_id, "task_id", allow_empty=True)
        _require_string(self.next_action, "next_action", allow_empty=True)
        if not isinstance(self.payload, MappingABC):
            raise TypeError("payload must be a mapping")
        object.__setattr__(self, "policy", normalize_policy_id(self.policy))
        object.__setattr__(self, "payload", _freeze_value(self.payload))


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
        if not isinstance(self.artifact_paths, (list, tuple)):
            raise TypeError("artifact_paths must be a list or tuple of strings")
        artifact_paths = tuple(self.artifact_paths)
        if not all(isinstance(path, str) for path in artifact_paths):
            raise TypeError("artifact_paths must contain only strings")
        object.__setattr__(self, "artifact_paths", artifact_paths)


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
        for field_name in ("mutates_git", "terminal", "user_escalation"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a bool")
        try:
            allowed_result_classes = frozenset(self.allowed_result_classes)
        except TypeError as exc:
            raise TypeError("allowed_result_classes must be iterable") from exc
        if not allowed_result_classes or not all(
            isinstance(result_class, ActionResultClass) for result_class in allowed_result_classes
        ):
            raise TypeError("allowed_result_classes must contain ActionResultClass values")
        if not isinstance(self.result_handling, MappingABC):
            raise TypeError("result_handling must be a mapping")
        result_handling = dict(self.result_handling)
        if not all(isinstance(result_class, ActionResultClass) for result_class in result_handling):
            raise TypeError("result_handling must use ActionResultClass keys")
        if set(result_handling) != set(allowed_result_classes):
            raise ValueError("result_handling must cover exactly the allowed result classes")
        if not all(isinstance(handling, ResultHandling) for handling in result_handling.values()):
            raise TypeError("result_handling must contain ResultHandling values")
        if self.terminal:
            if self.action_type not in {ActionType.NO_OP, ActionType.STOP_RUN}:
                raise ValueError("terminal TransitionRule must use a no-op or stop action")
            terminal_handlings = {ResultHandling.NO_OP, ResultHandling.STOP}
            if not set(result_handling.values()) <= terminal_handlings:
                raise ValueError("terminal TransitionRule must use no-op or stop handling")
        object.__setattr__(self, "allowed_result_classes", allowed_result_classes)
        object.__setattr__(self, "result_handling", MappingProxyType(result_handling))
