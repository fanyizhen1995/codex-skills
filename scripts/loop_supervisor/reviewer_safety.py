"""Fresh deterministic safety gates for Reviewer degradation policy."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
from typing import Any, Mapping
from uuid import uuid4

from scripts.harness_loop_agents import validate_owned_regular_file

from .safety_signals import detected_global_safety_signals
from .store import LeaseError, SupervisorStore


@dataclass(frozen=True)
class ReviewSafetyGate:
    gate_id: str
    passed: bool
    checked_at: str
    checks: Mapping[str, Any]


def evaluate_review_safety_gate(store: SupervisorStore) -> ReviewSafetyGate:
    """Evaluate and persist the shared deterministic gates immediately before review."""
    checks = current_review_safety_checks(store)
    passed = bool(checks["database_integrity"]) and bool(
        checks["no_open_global_decisions"]
    ) and bool(checks["no_fresh_global_safety_signals"])
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


def current_review_safety_checks(store: SupervisorStore) -> dict[str, Any]:
    """Read the canonical global safety state without persisting a gate row."""
    open_global = [
        str(row["decision_id"])
        for row in store.fetch_all("user_decisions")
        if row.get("status") == "open" and row.get("scope") == "global"
    ]
    fresh_signals = _fresh_global_safety_signals(store)
    checks = {
        "database_integrity": store.database_integrity_ok(),
        "open_global_decision_ids": sorted(open_global),
        "no_open_global_decisions": not open_global,
        "fresh_global_safety_signals": fresh_signals,
        "no_fresh_global_safety_signals": not fresh_signals,
    }
    return checks


def require_review_safety_clear(store: SupervisorStore) -> None:
    """Reject Reviewer renewal or side effects while any global gate is unsafe."""
    checks = current_review_safety_checks(store)
    if not checks["database_integrity"]:
        raise LeaseError("Reviewer safety gate blocked by database integrity failure")
    if not checks["no_open_global_decisions"]:
        raise LeaseError("Reviewer safety gate blocked by an open global decision")
    if not checks["no_fresh_global_safety_signals"]:
        raise LeaseError("Reviewer safety gate blocked by a canonical global signal")


def _fresh_global_safety_signals(store: SupervisorStore) -> list[dict[str, str]]:
    detected: set[tuple[str, str]] = set()
    for row in store.fetch_all("runs"):
        run_id = str(row.get("run_id") or "")
        try:
            summary = json.loads(str(row.get("summary_json") or "{}"))
        except json.JSONDecodeError:
            detected.add((run_id, "repo_corruption"))
            continue
        refs = summary.get("artifact_refs", []) if isinstance(summary, Mapping) else []
        run_ref = next(
            (
                value
                for value in refs
                if isinstance(value, str)
                and value.endswith(f"/.codex/loop-runs/{run_id}/run.json")
            ),
            "",
        )
        if not run_ref:
            run_ref = next(
                (
                    value
                    for value in refs
                    if isinstance(value, str)
                    and value == f".codex/loop-runs/{run_id}/run.json"
                ),
                "",
            )
        if not run_ref:
            continue
        try:
            path = store.project_root.joinpath(*PurePosixPath(run_ref).parts)
            owned = validate_owned_regular_file(
                store.project_root,
                path,
                "Reviewer safety run state",
            )
            payload = json.loads(owned.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("run state must be an object")
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            detected.add((run_id, "repo_corruption"))
            continue
        detected.update(
            (run_id, signal) for signal in detected_global_safety_signals(payload)
        )
    return [
        {"run_id": run_id, "signal": signal}
        for run_id, signal in sorted(detected)
    ]
