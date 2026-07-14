"""Shared contracts for the unified loop supervisor."""

from .models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionStatus,
    ActionType,
    ReviewDecision,
    TransitionRule,
)
from .registry import transition_for, validate_registry_coverage

__all__ = [
    "ActionRequest",
    "ActionResult",
    "ActionResultClass",
    "ActionStatus",
    "ActionType",
    "ReviewDecision",
    "TransitionRule",
    "transition_for",
    "validate_registry_coverage",
]
