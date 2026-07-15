"""Historical audit payload fixtures for pre-Supervisor regression data."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def fake_audit_report(
    *,
    run_id: str,
    audit_id: str,
    signals: Mapping[str, Any],
    signal_artifact_path: str,
    signal_artifact_sha256: str,
    cadence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary = signals.get("summary") if isinstance(signals.get("summary"), Mapping) else {}
    repeated = int(summary.get("same_evaluator_finding_count") or 0)
    must_fix = repeated >= 2
    findings = (
        [
            {
                "finding_id": f"{audit_id}-repeat-001",
                "severity": "must_fix",
                "status": "open",
                "title": "Repeated evaluator finding",
                "summary": "The same evaluator finding repeated across multiple loop steps.",
                "required_planner_action": "create_remediation_child",
            }
        ]
        if must_fix
        else []
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "audit_id": audit_id,
        "created_at": "2026-07-08T00:00:00Z",
        "created_by": "historical-test-fixture",
        "verdict": "must_fix" if must_fix else "pass",
        "deterministic_signals": {
            "artifact_path": signal_artifact_path,
            "artifact_sha256": signal_artifact_sha256,
            "summary": dict(summary),
            "git_head_sha": str((signals.get("git") or {}).get("head_sha") or ""),
        },
        "cadence": dict(cadence or {"unit": "boundary", "current_interval": 1, "steps_since_last_audit": 1}),
        "direction_control": {
            "action": "refocus" if must_fix else "continue",
            "reason": "historical fixture",
            "recommended_next_focus": "",
        },
        "finding_lifecycle": {"open_findings": findings, "closed_findings": []},
    }
