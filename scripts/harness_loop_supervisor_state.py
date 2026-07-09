import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


ALLOWED_FAILURE_CATEGORIES = {
    "service_down",
    "stale_version",
    "data_freshness",
    "dashboard_visibility",
    "required_evidence",
    "dirty_path",
    "audit_blocked",
    "auditor_stop",
    "continuation_duplicate",
    "unsupported_state",
    "unsafe_secret",
}
MAX_CONSECUTIVE_FAILURES = 3
ALLOWED_RECOVERY_STATUSES = {"pass", "fail"}
REQUIRED_RUN_SUMMARY_COUNTERS = ("active", "blocked", "continuation_candidates", "needs_user_decision")
REQUIRED_FAILURE_SUMMARY_COUNTERS = ("open_failure_keys",)


@dataclass(frozen=True)
class RecoveryAttemptInput:
    failure_key: str
    run_id: str
    action: str
    status: str
    summary: str
    evidence_paths: list[str]


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def supervisor_dir(project_root: Path) -> Path:
    return Path(project_root) / ".codex" / "supervisor"


def append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("JSONL payload must be a mapping")
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("a", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, sort_keys=True)
        handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    json_path = Path(path)
    if not json_path.exists():
        return []

    payloads: list[dict[str, Any]] = []
    with json_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL line {line_number} must be an object: {json_path}")
            payloads.append(payload)
    return payloads


def normalize_error_class(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "unknown"


def make_failure_key(category: str, scope_id: str, subject_id: str, error_class: str) -> str:
    normalized_category = str(category).strip()
    if normalized_category not in ALLOWED_FAILURE_CATEGORIES:
        raise ValueError(f"unknown failure category: {category}")
    return ":".join(
        [
            normalized_category,
            normalize_error_class(scope_id),
            normalize_error_class(subject_id),
            normalize_error_class(error_class),
        ]
    )


def record_recovery_attempt(project_root: Path, attempt: RecoveryAttemptInput) -> dict[str, Any]:
    _validate_failure_key(attempt.failure_key)
    if attempt.status not in ALLOWED_RECOVERY_STATUSES:
        raise ValueError(f"unknown recovery attempt status: {attempt.status}")

    root = supervisor_dir(project_root)
    attempts_path = root / "recovery-attempts.jsonl"
    existing_attempts = read_jsonl(attempts_path)
    timestamp = utc_now_iso()
    scope_key = _retry_scope_key(attempt.run_id)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "attempt_id": f"recovery-{len(existing_attempts) + 1:06d}",
        "started_at": timestamp,
        "finished_at": timestamp,
        "recorded_at": timestamp,
        "failure_key": attempt.failure_key,
        "run_id": attempt.run_id,
        "retry_scope": scope_key,
        "action": attempt.action,
        "status": attempt.status,
        "summary": attempt.summary,
        "evidence_paths": list(attempt.evidence_paths),
        "max_consecutive_failures": MAX_CONSECUTIVE_FAILURES,
    }

    consecutive_failure_count = _consecutive_failure_count(
        existing_attempts + [payload],
        attempt.failure_key,
        scope_key,
    )
    payload["consecutive_failure_count"] = consecutive_failure_count
    append_jsonl(attempts_path, payload)

    if attempt.status == "fail" and consecutive_failure_count >= MAX_CONSECUTIVE_FAILURES:
        consecutive_attempts = _trailing_attempts_for_failure_key(
            existing_attempts + [payload],
            attempt.failure_key,
            scope_key,
            consecutive_failure_count,
        )
        open_user_decision(
            project_root,
            reason="retry_ceiling_exceeded",
            failure_key=attempt.failure_key,
            summary=(
                f"Recovery action {attempt.action!r} failed "
                f"{consecutive_failure_count} consecutive times."
            ),
            required_user_decision="Inspect the repeated recovery failure and choose the next action.",
            affected_runs=_unique_non_empty_strings(item.get("run_id") for item in consecutive_attempts),
            attempts=consecutive_attempts,
        )

    return payload


def open_user_decision(
    project_root: Path,
    *,
    reason: str,
    failure_key: str,
    summary: str,
    required_user_decision: str,
    affected_runs: list[str],
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    _validate_failure_key(failure_key)
    root = supervisor_dir(project_root)
    decisions_dir = root / "needs-user-decisions"
    decision_path = decisions_dir / f"{_safe_file_stem(failure_key)}.json"
    if decision_path.exists():
        with decision_path.open("r", encoding="utf-8") as handle:
            existing = json.load(handle)
        if isinstance(existing, dict) and existing.get("status") == "open":
            return existing

    opened_at = utc_now_iso()
    decision: dict[str, Any] = {
        "schema_version": 1,
        "decision_id": _safe_file_stem(failure_key),
        "opened_at": opened_at,
        "status": "open",
        "reason": reason,
        "failure_key": failure_key,
        "summary": summary,
        "required_user_decision": required_user_decision,
        "affected_runs": list(affected_runs),
        "attempts": [dict(item) for item in attempts],
    }

    decisions_dir.mkdir(parents=True, exist_ok=True)
    with decision_path.open("w", encoding="utf-8") as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    append_jsonl(root / "user-decisions.jsonl", decision)
    return decision


def build_supervisor_state(
    project_root: Path,
    *,
    mode: str,
    service_health: dict[str, Any],
    run_summary: dict[str, Any],
    failure_summary: dict[str, Any],
    last_decision: dict[str, Any] | None,
    watch_interval_seconds: int,
) -> dict[str, Any]:
    project_root_path = Path(project_root)
    now = utc_now_iso()
    service_summary = _summarize_services(service_health)
    run_summary_payload = _validated_run_summary(run_summary)
    failure_summary_payload = _validated_failure_summary(failure_summary)
    status = _supervisor_status(service_summary, run_summary_payload, failure_summary_payload)
    started_at = _existing_started_at(supervisor_dir(project_root_path) / "supervisor-state.json") or now
    state: dict[str, Any] = {
        "schema_version": 1,
        "project_root": str(project_root_path),
        "status": status,
        "started_at": started_at,
        "last_heartbeat_at": now,
        "last_tick_at": now,
        "generated_at": now,
        "mode": mode,
        "service_summary": service_summary,
        "service_health": dict(service_health),
        "run_summary": run_summary_payload,
        "failure_summary": failure_summary_payload,
        "last_decision": dict(last_decision) if last_decision is not None else None,
        "watch_interval_seconds": watch_interval_seconds,
    }

    state_path = supervisor_dir(project_root) / "supervisor-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return state


def _consecutive_failure_count(attempts: list[dict[str, Any]], failure_key: str, retry_scope: str) -> int:
    count = 0
    for attempt in reversed(attempts):
        if attempt.get("failure_key") != failure_key:
            continue
        if _retry_scope_key(str(attempt.get("run_id", ""))) != retry_scope:
            continue
        if attempt.get("status") != "fail":
            break
        count += 1
    return count


def _trailing_attempts_for_failure_key(
    attempts: list[dict[str, Any]], failure_key: str, retry_scope: str, count: int
) -> list[dict[str, Any]]:
    if count <= 0:
        return []
    trailing: list[dict[str, Any]] = []
    for attempt in reversed(attempts):
        if attempt.get("failure_key") != failure_key:
            continue
        if _retry_scope_key(str(attempt.get("run_id", ""))) != retry_scope:
            continue
        if attempt.get("status") != "fail":
            break
        trailing.append(attempt)
        if len(trailing) == count:
            break
    return list(reversed(trailing))


def _safe_file_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    safe = re.sub(r"-+", "-", safe).strip("-")
    return safe or "unknown"


def _unique_non_empty_strings(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _retry_scope_key(run_id: str) -> str:
    return run_id or "project"


def _validate_failure_key(failure_key: str) -> None:
    parts = str(failure_key).split(":")
    if len(parts) != 4 or any(not part for part in parts):
        raise ValueError(f"invalid failure_key: {failure_key}")
    if parts[0] not in ALLOWED_FAILURE_CATEGORIES:
        raise ValueError(f"unknown failure category: {parts[0]}")
    for part in parts[1:]:
        if part != normalize_error_class(part):
            raise ValueError(f"invalid failure_key: {failure_key}")


def _validated_run_summary(run_summary: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(run_summary)
    for key in REQUIRED_RUN_SUMMARY_COUNTERS:
        payload[key] = _required_non_negative_int(payload, f"run_summary.{key}")
    return payload


def _validated_failure_summary(failure_summary: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(failure_summary)
    for key in REQUIRED_FAILURE_SUMMARY_COUNTERS:
        payload[key] = _required_non_negative_int(payload, f"failure_summary.{key}")
    if "max_consecutive_failures" in payload:
        payload["max_consecutive_failures"] = _required_non_negative_int(
            payload,
            "failure_summary.max_consecutive_failures",
        )
    else:
        payload["max_consecutive_failures"] = MAX_CONSECUTIVE_FAILURES
    return payload


def _required_non_negative_int(payload: Mapping[str, Any], field_path: str) -> int:
    key = field_path.rsplit(".", 1)[-1]
    if key not in payload:
        raise ValueError(f"missing required {field_path}")
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"invalid required {field_path}: expected non-negative integer")
    return value


def _existing_started_at(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict) and isinstance(payload.get("started_at"), str):
        return payload["started_at"]
    return None


def _summarize_services(service_health: Mapping[str, Any]) -> dict[str, int]:
    summary = {"total": len(service_health), "healthy": 0, "degraded": 0, "blocked": 0}
    for service in service_health.values():
        status = ""
        if isinstance(service, Mapping):
            status = str(service.get("status", "")).strip().lower()
        if status in {"healthy", "pass", "ok"}:
            summary["healthy"] += 1
        elif status in {"blocked", "fail", "failed", "down", "unreachable"}:
            summary["blocked"] += 1
        else:
            summary["degraded"] += 1
    return summary


def _supervisor_status(
    service_summary: Mapping[str, int],
    run_summary: Mapping[str, Any],
    failure_summary: Mapping[str, Any],
) -> str:
    if (
        int(service_summary.get("blocked", 0)) > 0
        or int(run_summary.get("needs_user_decision", 0)) > 0
        or int(failure_summary.get("open_failure_keys", 0)) > 0
    ):
        return "blocked"
    if int(service_summary.get("degraded", 0)) > 0 or int(run_summary.get("blocked", 0)) > 0:
        return "degraded"
    return "healthy"
