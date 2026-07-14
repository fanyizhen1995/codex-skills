"""Fresh deterministic safety gates for Reviewer degradation policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import uuid4

from .store import SupervisorStore


@dataclass(frozen=True)
class ReviewSafetyGate:
    gate_id: str
    passed: bool
    checked_at: str
    checks: Mapping[str, Any]


def evaluate_review_safety_gate(store: SupervisorStore) -> ReviewSafetyGate:
    """Evaluate and persist the shared deterministic gates immediately before review."""
    open_global = [
        str(row["decision_id"])
        for row in store.fetch_all("user_decisions")
        if row.get("status") == "open" and row.get("scope") == "global"
    ]
    checks = {
        "database_integrity": store.database_integrity_ok(),
        "open_global_decision_ids": sorted(open_global),
        "no_open_global_decisions": not open_global,
    }
    passed = bool(checks["database_integrity"]) and bool(
        checks["no_open_global_decisions"]
    )
    gate_id = f"review-gate-{uuid4().hex}"
    row = store.record_review_safety_gate(
        gate_id,
        status="pass" if passed else "fail",
        checks=checks,
    )
    return ReviewSafetyGate(
        gate_id=gate_id,
        passed=passed,
        checked_at=str(row["checked_at"]),
        checks=checks,
    )
