#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.harness_loop_contracts import (
        read_json_file,
        run_dir_for,
        validate_audit_report_payload,
        write_json_file,
    )
except ModuleNotFoundError:
    from harness_loop_contracts import (  # type: ignore[no-redef]
        read_json_file,
        run_dir_for,
        validate_audit_report_payload,
        write_json_file,
    )


CREATED_BY = "harness_loop_orchestrator"
DETERMINISTIC_SIGNALS_FILENAME = "deterministic-signals.json"


def timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compute_deterministic_signals(repo_root: Path | str, run: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(repo_root)
    run_id = str(run.get("run_id", ""))
    child_run_ids = [str(value) for value in run.get("child_run_ids", []) if str(value).strip()]
    changed_paths = _generator_changed_paths(root, run_id)
    child_changed_paths = [_generator_changed_paths(root, child_id) for child_id in child_run_ids]
    head_sha = _git_head_sha(root)
    previous_audit_head_sha = _previous_audit_head_sha(root, run_id)
    commits_since_last_audit = _commits_since_last_audit(root, head_sha, previous_audit_head_sha)
    summary = {
        "passed_children_since_last_audit": _passed_children(run),
        "autonomous_rounds_since_last_audit": _completed_autonomous_rounds(run),
        "commits_since_last_audit": commits_since_last_audit,
        "coverage_layers_changed": _covered_layer_count(root, run),
        "new_raw_files": _count_paths(changed_paths, "/raw/"),
        "new_or_updated_wiki_pages": _count_wiki_pages(changed_paths),
        "same_evaluator_finding_count": _same_evaluator_finding_count(root, child_run_ids or [run_id]),
        "same_dirty_path_count": _same_dirty_path_count(root, run_id),
        "same_identity_key_blocked_count": _same_identity_key_blocked_count(root, run),
        "same_file_modified_consecutively": _same_file_modified_consecutively(child_changed_paths),
        "unclassified_dirty_paths": len(_unclassified_dirty_paths(root, run)),
        "unpushed_commits": _unpushed_commit_count(root),
        "missing_required_evidence": _missing_required_evidence_count(root, run_id),
        "dashboard_visibility_failures": _dashboard_visibility_failure_count(root, run_id),
        "same_local_issue_rounds": _same_local_issue_rounds(root, run_id),
        "core_goal_progress_delta": _core_goal_progress_delta(run),
        "remaining_value_estimate": _remaining_value_estimate(run),
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "computed_at": timestamp(),
        "created_by": CREATED_BY,
        "summary": summary,
        "git": {
            "head_sha": head_sha,
            "previous_audit_head_sha": previous_audit_head_sha,
        },
        "progress_counters": {
            "passed_children_since_last_audit": summary["passed_children_since_last_audit"],
            "autonomous_rounds_since_last_audit": summary["autonomous_rounds_since_last_audit"],
            "commits_since_last_audit": summary["commits_since_last_audit"],
            "coverage_layers_changed": summary["coverage_layers_changed"],
            "new_raw_files": summary["new_raw_files"],
            "new_or_updated_wiki_pages": summary["new_or_updated_wiki_pages"],
        },
        "repeat_counters": {
            "same_evaluator_finding_count": summary["same_evaluator_finding_count"],
            "same_dirty_path_count": summary["same_dirty_path_count"],
            "same_identity_key_blocked_count": summary["same_identity_key_blocked_count"],
            "same_file_modified_consecutively": summary["same_file_modified_consecutively"],
        },
        "hygiene_counters": {
            "unclassified_dirty_paths": summary["unclassified_dirty_paths"],
            "unpushed_commits": summary["unpushed_commits"],
            "missing_required_evidence": summary["missing_required_evidence"],
            "dashboard_visibility_failures": summary["dashboard_visibility_failures"],
        },
        "tunnel_vision_inputs": {
            "same_local_issue_rounds": summary["same_local_issue_rounds"],
            "core_goal_progress_delta": summary["core_goal_progress_delta"],
            "remaining_value_estimate": summary["remaining_value_estimate"],
        },
    }


def write_deterministic_signals(repo_root: Path | str, run: Mapping[str, Any]) -> Path:
    root = Path(repo_root)
    payload = compute_deterministic_signals(root, run)
    return write_json_file(run_dir_for(root, str(run["run_id"])) / DETERMINISTIC_SIGNALS_FILENAME, payload)


def rule_based_audit_report(
    *,
    run_id: str,
    audit_id: str,
    signals: Mapping[str, Any],
    signal_artifact_path: str,
    signal_artifact_sha256: str,
) -> dict[str, Any]:
    summary = signals.get("summary") if isinstance(signals.get("summary"), Mapping) else {}
    repeated_evaluator = _safe_int(summary.get("same_evaluator_finding_count"))
    repeated_dirty = _safe_int(summary.get("same_dirty_path_count"))
    local_issue_rounds = _safe_int(summary.get("same_local_issue_rounds"))
    open_findings: list[dict[str, str]] = []
    verdict = "pass"
    action = "continue"
    reason = "deterministic audit signals are within thresholds"

    if repeated_evaluator >= 2:
        verdict = "must_fix"
        action = "refocus"
        reason = "same evaluator finding repeated across loop work"
        open_findings.append(
            {
                "finding_id": f"{audit_id}-repeat-001",
                "severity": "must_fix",
                "status": "open",
                "title": "Repeated evaluator finding",
                "summary": "The same evaluator finding repeated across multiple loop steps.",
                "required_planner_action": "create_remediation_child",
            }
        )
    elif repeated_dirty >= 2 or local_issue_rounds >= 2:
        verdict = "should_fix"
        action = "refocus"
        reason = "repeat hygiene or tunnel-vision signal crossed advisory threshold"
        open_findings.append(
            {
                "finding_id": f"{audit_id}-hygiene-001",
                "severity": "should_fix",
                "status": "open",
                "title": "Repeated hygiene signal",
                "summary": "Repeated hygiene or tunnel-vision signals suggest the loop should refocus.",
                "required_planner_action": "plan_followup_or_refocus",
            }
        )

    report = {
        "schema_version": 1,
        "run_id": run_id,
        "audit_id": audit_id,
        "created_at": timestamp(),
        "created_by": CREATED_BY,
        "verdict": verdict,
        "deterministic_signals": {
            "artifact_path": signal_artifact_path,
            "artifact_sha256": signal_artifact_sha256,
            "summary": dict(summary),
            "git_head_sha": _signal_git_head_sha(signals),
        },
        "cadence": {"unit": "boundary", "current_interval": 1, "steps_since_last_audit": 1},
        "direction_control": {"action": action, "reason": reason, "recommended_next_focus": ""},
        "finding_lifecycle": {"open_findings": open_findings, "closed_findings": []},
    }
    validate_audit_report_payload(report)
    return report


def write_rule_based_audit_report(repo_root: Path | str, run: Mapping[str, Any]) -> Path:
    root = Path(repo_root)
    run_id = str(run["run_id"])
    signal_path = write_deterministic_signals(root, run)
    signal_payload = read_json_file(signal_path)
    audit_id = _next_audit_id(root, run_id)
    report = rule_based_audit_report(
        run_id=run_id,
        audit_id=audit_id,
        signals=signal_payload,
        signal_artifact_path=signal_path.relative_to(root).as_posix(),
        signal_artifact_sha256=hashlib.sha256(signal_path.read_bytes()).hexdigest(),
    )
    return write_json_file(run_dir_for(root, run_id) / "audit-reports" / f"{audit_id}.json", report)


fake_audit_report = rule_based_audit_report
write_fake_audit_report = write_rule_based_audit_report


def latest_audit_report(repo_root: Path | str, run_id: str) -> dict[str, Any] | None:
    root = Path(repo_root)
    path = latest_audit_report_path(root, run_id)
    if path is None:
        return None
    payload = read_json_file(path)
    validate_audit_report_payload(payload)
    return payload


def latest_audit_report_path(repo_root: Path | str, run_id: str) -> Path | None:
    audit_dir = run_dir_for(Path(repo_root), run_id) / "audit-reports"
    if not audit_dir.is_dir():
        return None
    candidates = [path for path in audit_dir.glob("audit-*.json") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (_audit_number(path), path.stat().st_mtime_ns))


def open_must_fix_findings(report: Mapping[str, Any] | None) -> list[dict[str, Any]]:
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


def audit_report_has_open_must_fix(repo_root: Path | str, run_id: str) -> bool:
    return bool(open_must_fix_findings(latest_audit_report(repo_root, run_id)))


def _next_audit_id(repo_root: Path, run_id: str) -> str:
    latest = latest_audit_report_path(repo_root, run_id)
    number = _audit_number(latest) + 1 if latest is not None else 1
    return f"audit-{number:03d}"


def _audit_number(path: Path | None) -> int:
    if path is None:
        return 0
    stem = path.stem
    if not stem.startswith("audit-"):
        return 0
    try:
        return int(stem.split("-", 1)[1])
    except ValueError:
        return 0


def _passed_children(run: Mapping[str, Any]) -> int:
    aggregate = run.get("aggregate_acceptance")
    if isinstance(aggregate, Mapping):
        return _safe_int(aggregate.get("passed"))
    return 0


def _completed_autonomous_rounds(run: Mapping[str, Any]) -> int:
    completed = run.get("_autonomous_completed_task_ids")
    return len(completed) if isinstance(completed, list) else 0


def _git_head_sha(repo_root: Path) -> str:
    result = _run_git(repo_root, ["rev-parse", "HEAD"])
    if result is None or result.returncode != 0:
        return ""
    return result.stdout.strip()


def _previous_audit_head_sha(repo_root: Path, run_id: str) -> str:
    latest = latest_audit_report_path(repo_root, run_id)
    if latest is None:
        return ""
    try:
        payload = read_json_file(latest)
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    signals = payload.get("deterministic_signals")
    if not isinstance(signals, Mapping):
        return ""
    value = signals.get("git_head_sha")
    return str(value).strip() if value else ""


def _commits_since_last_audit(repo_root: Path, head_sha: str, previous_audit_head_sha: str) -> int:
    if not head_sha or not previous_audit_head_sha:
        return 0
    result = _run_git(repo_root, ["rev-list", "--count", f"{previous_audit_head_sha}..{head_sha}"])
    if result is None or result.returncode != 0:
        return 0
    return min(_safe_int(result.stdout.strip()), 100)


def _signal_git_head_sha(signals: Mapping[str, Any]) -> str:
    git_info = signals.get("git")
    if not isinstance(git_info, Mapping):
        return ""
    return str(git_info.get("head_sha") or "").strip()


def _covered_layer_count(repo_root: Path, run: Mapping[str, Any]) -> int:
    domain = str(run.get("domain", "")).strip()
    if not domain:
        return 0
    coverage_path = repo_root / "personal-wiki" / "domains" / domain / "coverage-map.json"
    if not coverage_path.exists():
        return 0
    try:
        coverage = read_json_file(coverage_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return 0
    layers = coverage.get("layers")
    if not isinstance(layers, Mapping):
        return 0
    return sum(1 for layer in layers.values() if isinstance(layer, Mapping) and layer.get("status") == "covered")


def _generator_changed_paths(repo_root: Path, run_id: str) -> list[str]:
    path = run_dir_for(repo_root, run_id) / "generator-result.json"
    if not path.exists():
        return []
    try:
        payload = read_json_file(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    changed_paths = payload.get("changed_paths")
    if not isinstance(changed_paths, list):
        return []
    return [str(value) for value in changed_paths if str(value).strip()]


def _count_paths(paths: Sequence[str], marker: str) -> int:
    return sum(1 for path in paths if marker in path)


def _count_wiki_pages(paths: Sequence[str]) -> int:
    return sum(1 for path in paths if path.endswith(".md") and "/wiki/" in path)


def _same_evaluator_finding_count(repo_root: Path, run_ids: Sequence[str]) -> int:
    findings: list[str] = []
    for run_id in run_ids:
        path = run_dir_for(repo_root, run_id) / "evaluator-result.json"
        if not path.exists():
            continue
        try:
            payload = read_json_file(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        structured_keys = _structured_evaluator_finding_keys(payload)
        if structured_keys:
            findings.extend(structured_keys)
            continue
        if payload.get("status") == "pass" and "finding" not in str(payload.get("stdout", "")).lower():
            continue
        text = _normalize_finding_text(str(payload.get("stdout") or payload.get("stderr") or ""))
        if text:
            findings.append(text)
    counts = Counter(findings)
    return max(counts.values(), default=0)


def _structured_evaluator_finding_keys(payload: Mapping[str, Any]) -> list[str]:
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        return []
    keys: list[str] = []
    for finding in raw_findings:
        if not isinstance(finding, Mapping):
            continue
        category = _normalize_key_part(str(finding.get("category") or ""))
        title = _normalize_key_part(str(finding.get("title") or finding.get("key") or ""))
        if category and title:
            keys.append(f"finding:{category}:{title}")
            continue
        finding_id = _normalize_key_part(str(finding.get("id") or finding.get("finding_id") or ""))
        if finding_id:
            keys.append(f"finding-id:{finding_id}")
    return keys


def _normalize_finding_text(value: str) -> str:
    text = " ".join(value.strip().lower().split())
    if not text:
        return ""
    return text[:500]


def _normalize_key_part(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _same_dirty_path_count(repo_root: Path, run_id: str) -> int:
    path = run_dir_for(repo_root, run_id) / "dirty-paths-result.json"
    if not path.exists():
        return 0
    try:
        payload = read_json_file(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return 0
    paths = payload.get("unexpected_paths")
    if not isinstance(paths, list):
        return 0
    counts = Counter(str(value) for value in paths if str(value).strip())
    return max(counts.values(), default=0)


def _same_identity_key_blocked_count(repo_root: Path, run: Mapping[str, Any]) -> int:
    domain = str(run.get("domain", "")).strip()
    if not domain:
        return 0
    path = repo_root / "personal-wiki" / "domains" / domain / "loop-state.json"
    if not path.exists():
        return 0
    try:
        state = read_json_file(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return 0
    keys: list[str] = []
    for collection_name in ("blocked_items", "coverage_gaps"):
        items = state.get(collection_name)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, Mapping):
                key = str(item.get("identity_key") or item.get("id") or "").strip()
                if key:
                    keys.append(key)
    counts = Counter(keys)
    return max(counts.values(), default=0)


def _same_file_modified_consecutively(changed_path_groups: Sequence[Sequence[str]]) -> int:
    previous: set[str] | None = None
    repeated = 0
    for group in changed_path_groups:
        current = {str(path) for path in group if str(path).strip()}
        if previous is not None and previous & current:
            repeated += 1
        previous = current
    return repeated


def _unclassified_dirty_paths(repo_root: Path, run: Mapping[str, Any]) -> list[str]:
    accepted = {str(path) for path in run.get("accepted_changed_paths", [])}
    baseline = _baseline_dirty_paths(run)
    run_id = str(run.get("run_id", ""))
    paths: list[str] = []
    for path in _git_dirty_paths(repo_root):
        if path in accepted or path in baseline:
            continue
        if path.startswith(".codex/loop-runs/"):
            continue
        paths.append(path)
    return sorted(paths)


def _git_dirty_paths(repo_root: Path) -> list[str]:
    result = _run_git(repo_root, ["status", "--porcelain", "--untracked-files=all"])
    if result is None or result.returncode != 0:
        stderr = "" if result is None else result.stderr.strip()
        raise RuntimeError(f"git status failed: {stderr or 'git command did not complete'}")
    return sorted({path for line in result.stdout.splitlines() for path in _parse_porcelain_paths(line)})


def _parse_porcelain_paths(line: str) -> list[str]:
    if len(line) < 4:
        return []
    value = line[3:].strip()
    if " -> " in value:
        old, new = value.split(" -> ", 1)
        return [old.strip(), new.strip()]
    return [value]


def _baseline_dirty_paths(run: Mapping[str, Any]) -> set[str]:
    paths: set[str] = set()
    for line in run.get("baseline_dirty_paths", []):
        if isinstance(line, str):
            paths.update(_parse_porcelain_paths(line))
    return paths


def _unpushed_commit_count(repo_root: Path) -> int:
    upstream = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream is None or upstream.returncode != 0:
        return 0
    result = _run_git(repo_root, ["rev-list", "--count", f"{upstream.stdout.strip()}..HEAD"])
    if result is None or result.returncode != 0:
        return 0
    return _safe_int(result.stdout.strip())


def _run_git(repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        process = subprocess.Popen(
            ["git", *args],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return subprocess.CompletedProcess(["git", *args], process.returncode, stdout, stderr)


def _missing_required_evidence_count(repo_root: Path, run_id: str) -> int:
    path = run_dir_for(repo_root, run_id) / "required-evidence-result.json"
    if not path.exists():
        return 0
    try:
        payload = read_json_file(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return 1
    if payload.get("status") == "pass":
        return 0
    findings = payload.get("findings")
    return len(findings) if isinstance(findings, list) else 1


def _dashboard_visibility_failure_count(repo_root: Path, run_id: str) -> int:
    root = run_dir_for(repo_root, run_id) / "trusted-live-evidence"
    if not root.is_dir():
        return 0
    failures = 0
    for path in root.glob("*.json"):
        try:
            payload = read_json_file(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if payload.get("evidence_id") == "loop-dashboard-freshness" and payload.get("status") != "pass":
            failures += 1
    return failures


def _same_local_issue_rounds(repo_root: Path, run_id: str) -> int:
    events_path = run_dir_for(repo_root, run_id) / "events.jsonl"
    if not events_path.exists():
        return 0
    issue_counts: Counter[str] = Counter()
    try:
        lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        summary = str(event.get("summary", "")).strip().lower()
        if summary:
            issue_counts[summary] += 1
    return max(issue_counts.values(), default=0)


def _core_goal_progress_delta(run: Mapping[str, Any]) -> str:
    aggregate = run.get("aggregate_acceptance")
    if isinstance(aggregate, Mapping) and _safe_int(aggregate.get("passed")) > 0:
        return "medium"
    if _completed_autonomous_rounds(run) > 0:
        return "medium"
    return "none"


def _remaining_value_estimate(run: Mapping[str, Any]) -> str:
    if str(run.get("phase", "")) in {"stopped_no_action", "passed_waiting_human_merge"}:
        return "low"
    return "medium"


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0
