"""Shared contracts for the unified loop supervisor."""

from .models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionStatus,
    ActionType,
    ResultHandling,
    ReviewDecision,
    ReviewEvidenceBundle,
    ReviewerExecutionResult,
    SupervisorReview,
    TransitionRule,
)
from .registry import transition_for, validate_registry_coverage

__all__ = [
    "ActionRequest",
    "ActionResult",
    "ActionResultClass",
    "ActionStatus",
    "ActionType",
    "ResultHandling",
    "ReviewDecision",
    "ReviewEvidenceBundle",
    "ReviewerExecutionResult",
    "SupervisorReview",
    "TransitionRule",
    "transition_for",
    "validate_registry_coverage",
]
