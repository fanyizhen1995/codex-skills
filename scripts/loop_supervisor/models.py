"""Strict value objects shared by Supervisor and Worker components."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from enum import StrEnum
import math
import re
from types import MappingProxyType
from pathlib import PurePosixPath
from typing import Any, Mapping

from scripts.harness_loop_contracts import ALLOWED_PHASES, normalize_policy_id, validate_run_id


def _require_string(value: object, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must be non-empty")
    return value


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, MappingABC):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("payload mappings must use string keys")
        return MappingProxyType({key: _freeze_json_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        raise ValueError("payload floats must be finite")
    raise TypeError("payload values must be JSON-safe")


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, MappingABC):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def validate_repo_relative_root(value: object) -> str:
    root = _require_string(value, "repo_relative_root")
    path = PurePosixPath(root)
    if path.is_absolute() or root != path.as_posix() or any(
        part in {"", ".."} for part in path.parts
    ):
        raise ValueError("repo_relative_root must be a normalized project-relative path")
    return root


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


class ActionOwner(StrEnum):
    WORKER = "worker"
    REVIEWER = "reviewer"
    SUPERVISOR = "supervisor"


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


class RecoveryStage(StrEnum):
    RETRY = "retry"
    ALTERNATE = "alternate"
    REVIEWER = "reviewer"


class ReviewDecision(StrEnum):
    CONTINUE = "continue"
    AUTO_REMEDIATE = "auto_remediate"
    REFOCUS = "refocus"
    STOP_RUN = "stop_run"
    ASK_USER = "ask_user"


@dataclass(frozen=True)
class ReviewEvidenceBundle:
    generated_at: str
    triggering_lineages: tuple[str, ...]
    cadence_positions: Mapping[str, int]
    evidence: Mapping[str, Any]
    evidence_hashes: Mapping[str, str]
    bundle_hash: str

    def __post_init__(self) -> None:
        _require_string(self.generated_at, "generated_at")
        lineages = tuple(self.triggering_lineages)
        if not lineages or not all(isinstance(item, str) and item for item in lineages):
            raise ValueError("triggering_lineages must contain non-empty strings")
        if len(set(lineages)) != len(lineages):
            raise ValueError("triggering_lineages must be unique")
        positions = dict(self.cadence_positions)
        if set(positions) != set(lineages) or not all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in positions.values()
        ):
            raise ValueError("cadence_positions must cover every triggering lineage")
        if not isinstance(self.evidence, MappingABC) or not self.evidence:
            raise ValueError("evidence must be a non-empty mapping")
        hashes = dict(self.evidence_hashes)
        if set(hashes) != set(self.evidence):
            raise ValueError("evidence_hashes must cover every evidence section")
        for value in (*hashes.values(), self.bundle_hash):
            if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                raise ValueError("evidence hashes must be lowercase sha256 references")
        object.__setattr__(self, "triggering_lineages", lineages)
        object.__setattr__(self, "cadence_positions", MappingProxyType(positions))
        object.__setattr__(self, "evidence", _freeze_json_value(self.evidence))
        object.__setattr__(self, "evidence_hashes", MappingProxyType(hashes))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "generated_at": self.generated_at,
            "triggering_lineages": list(self.triggering_lineages),
            "cadence_positions": dict(self.cadence_positions),
            "evidence": _thaw_json_value(self.evidence),
            "evidence_hashes": dict(self.evidence_hashes),
            "bundle_hash": self.bundle_hash,
        }


@dataclass(frozen=True)
class SupervisorReview:
    schema_version: int
    review_id: str
    scope: str
    decision: ReviewDecision
    affected_run_ids: tuple[str, ...]
    summary: str
    evidence_refs: tuple[str, ...]
    findings: tuple[Mapping[str, Any], ...]
    skill_governance: tuple[Mapping[str, Any], ...]
    next_review_after_parent_tasks: int
    reviewed_runs: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        _require_string(self.review_id, "review_id")
        if self.scope != "project":
            raise ValueError("review scope must be project")
        if not isinstance(self.decision, ReviewDecision):
            raise TypeError("decision must be a ReviewDecision")
        run_ids = tuple(self.affected_run_ids)
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("affected_run_ids must be unique")
        for run_id in run_ids:
            validate_run_id(run_id)
        _require_string(self.summary, "summary")
        refs = tuple(self.evidence_refs)
        if not refs:
            raise ValueError("evidence_refs must not be empty")
        findings = tuple(_freeze_json_value(item) for item in self.findings)
        governance = tuple(_freeze_json_value(item) for item in self.skill_governance)
        reviewed_runs = _freeze_json_value(self.reviewed_runs)
        if not isinstance(reviewed_runs, MappingABC):
            raise TypeError("reviewed_runs must be a mapping")
        if (
            not isinstance(self.next_review_after_parent_tasks, int)
            or isinstance(self.next_review_after_parent_tasks, bool)
            or self.next_review_after_parent_tasks != 2
        ):
            raise ValueError("next_review_after_parent_tasks must be 2")
        object.__setattr__(self, "affected_run_ids", run_ids)
        object.__setattr__(self, "evidence_refs", refs)
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "skill_governance", governance)
        object.__setattr__(self, "reviewed_runs", reviewed_runs)


@dataclass(frozen=True)
class ReviewerExecutionResult:
    status: str
    blocks_safe_runs: bool
    review_id: str
    review: SupervisorReview | None = None
    actions: tuple[ActionRequest, ...] = ()
    evidence_path: str = ""
    accepted_review_path: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"review_complete", "review_degraded"}:
            raise ValueError("unsupported Reviewer execution status")
        if not isinstance(self.blocks_safe_runs, bool):
            raise TypeError("blocks_safe_runs must be a bool")
        _require_string(self.review_id, "review_id")
        if self.review is not None and not isinstance(self.review, SupervisorReview):
            raise TypeError("review must be a SupervisorReview")
        actions = tuple(self.actions)
        if not all(isinstance(item, ActionRequest) for item in actions):
            raise TypeError("actions must contain ActionRequest values")
        object.__setattr__(self, "actions", actions)


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    run_id: str
    run_revision: int
    policy: str
    phase: str
    action_type: ActionType
    idempotency_key: str
    queue_owner: ActionOwner = ActionOwner.WORKER
    not_before: str = ""
    repo_relative_root: str = "."
    task_id: str = ""
    next_action: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_string(self.action_id, "action_id")
        _require_string(self.run_id, "run_id")
        validate_run_id(self.run_id)
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
        if not isinstance(self.queue_owner, ActionOwner):
            raise TypeError("queue_owner must be an ActionOwner")
        _require_string(self.not_before, "not_before", allow_empty=True)
        object.__setattr__(
            self,
            "repo_relative_root",
            validate_repo_relative_root(self.repo_relative_root),
        )
        _require_string(self.task_id, "task_id", allow_empty=True)
        _require_string(self.next_action, "next_action", allow_empty=True)
        if not isinstance(self.payload, MappingABC):
            raise TypeError("payload must be a mapping")
        object.__setattr__(self, "policy", normalize_policy_id(self.policy))
        object.__setattr__(self, "payload", _freeze_json_value(self.payload))

    def payload_for_storage(self) -> dict[str, Any]:
        """Return an independent JSON-safe payload suitable for SQLite storage."""
        return _thaw_json_value(self.payload)

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Expose queue metadata without duplicating the immutable payload."""
        return MappingProxyType(self.payload_for_storage())


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
    worker_executable: bool = True
    allowed_result_classes: frozenset[ActionResultClass] = frozenset(ActionResultClass)
    result_handling: Mapping[ActionResultClass, ResultHandling] = field(
        default_factory=lambda: DEFAULT_RESULT_HANDLING
    )
    terminal: bool = False
    user_escalation: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            raise TypeError("action_type must be an ActionType")
        for field_name in (
            "mutates_git",
            "worker_executable",
            "terminal",
            "user_escalation",
        ):
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


@dataclass(frozen=True)
class RecoveryTransitionRule:
    action_type: ActionType
    mutates_git: bool
    worker_executable: bool
    strategy: str

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            raise TypeError("action_type must be an ActionType")
        if not isinstance(self.mutates_git, bool):
            raise TypeError("mutates_git must be a bool")
        if not isinstance(self.worker_executable, bool):
            raise TypeError("worker_executable must be a bool")
        _require_string(self.strategy, "strategy")


@dataclass(frozen=True)
class ReviewApplicationRule:
    action_type: ActionType
    target_phase: str
    target_next_action: str
    target_last_result: str
    mutates_run: bool

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            raise TypeError("action_type must be an ActionType")
        if self.target_phase and self.target_phase not in ALLOWED_PHASES:
            raise ValueError("target_phase is not contract allowed")
        _require_string(self.target_next_action, "target_next_action", allow_empty=True)
        _require_string(self.target_last_result, "target_last_result", allow_empty=True)
        if not isinstance(self.mutates_run, bool):
            raise TypeError("mutates_run must be a bool")
