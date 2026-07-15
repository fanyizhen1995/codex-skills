"""Read-only compatibility for retained pre-Supervisor audit artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.harness_loop_contracts import (
    read_json_file,
    run_dir_for,
    validate_audit_report_payload,
)


def latest_audit_report(repo_root: Path | str, run_id: str) -> dict[str, Any] | None:
    path = latest_audit_report_path(repo_root, run_id)
    if path is None:
        return None
    payload = read_json_file(path)
    validate_audit_report_payload(payload)
    return payload


def latest_audit_report_path(repo_root: Path | str, run_id: str) -> Path | None:
    audit_dir = run_dir_for(Path(repo_root), run_id) / "audit-reports"
    if not audit_dir.is_dir() or audit_dir.is_symlink():
        return None
    candidates = [
        path
        for path in audit_dir.glob("audit-*.json")
        if path.is_file() and not path.is_symlink()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (_audit_number(path), path.stat().st_mtime_ns))


def open_must_fix_findings(
    report: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(report, Mapping):
        return []
    lifecycle = report.get("finding_lifecycle")
    if not isinstance(lifecycle, Mapping):
        return []
    findings = lifecycle.get("open_findings")
    if not isinstance(findings, list):
        return []
    return [
        dict(finding)
        for finding in findings
        if isinstance(finding, Mapping)
        and str(finding.get("status", "open")) == "open"
        and str(finding.get("severity", "")) == "must_fix"
    ]


def _audit_number(path: Path) -> int:
    try:
        return int(path.stem.removeprefix("audit-"))
    except ValueError:
        return 0
