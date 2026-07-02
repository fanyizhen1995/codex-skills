import json
from pathlib import Path
from typing import Any, Mapping


POLICY_ALIASES = {
    "demand-development": "demand_development",
    "demand_development": "demand_development",
    "autonomous-knowledge": "autonomous_knowledge",
    "autonomous_knowledge": "autonomous_knowledge",
}

ALLOWED_POLICIES = frozenset(POLICY_ALIASES.values())
ALLOWED_PHASES = frozenset(
    {
        "preflight",
        "planned",
        "generating",
        "verifying",
        "evaluating",
        "repair_needed",
        "artifact_hygiene",
        "cleanup",
        "passed_waiting_human_merge",
        "planning",
        "committed",
        "stopped_no_action",
        "stopped_budget",
        "stopped_blocked",
    }
)
ALLOWED_TASK_KINDS = frozenset(
    {
        "registered_task",
        "candidate_task",
        "task_contract_only",
        "autonomous_implementation_task",
    }
)
ALLOWED_GENERATOR_STATUSES = frozenset({"implemented", "repaired", "blocked", "failed"})
ALLOWED_AGENT_ROLES = frozenset({"planner", "generator", "evaluator"})
REQUIRED_RUN_ATTEMPT_KEYS = frozenset(
    {"planner", "generator", "evaluator", "artifact_hygiene", "cleanup"}
)
ALLOWED_AGENT_STATUSES = frozenset(
    {"pass", "fail", "blocked", "timeout", "invalid_json"}
)
ALLOWED_LAST_RESULTS = frozenset({"pass", "fail", "blocked", "none"})


def normalize_policy_id(policy: str) -> str:
    if not isinstance(policy, str):
        raise ValueError("policy must be a string")
    try:
        return POLICY_ALIASES[policy]
    except KeyError as exc:
        raise ValueError(f"unknown policy: {policy}") from exc


def default_limits() -> dict[str, int]:
    return {
        "max_tasks_per_run": 3,
        "max_generator_attempts_per_task": 2,
        "max_eval_attempts_per_task": 3,
        "max_wall_time_minutes": 60,
        "max_no_action_rounds": 1,
        "agent_timeout_minutes": 30,
        "cleanup_retention_days": 7,
    }


def run_dir_for(repo_root: Path, run_id: str) -> Path:
    return Path(repo_root) / ".codex" / "loop-runs" / run_id


def read_json_file(path: Path | str) -> dict[str, Any]:
    json_path = Path(path)
    with json_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def write_json_file(path: Path | str, payload: Mapping[str, Any]) -> Path:
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return json_path


def validate_run_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "run payload")
    _require_keys(
        payload,
        {
            "run_id",
            "policy",
            "phase",
            "task_id",
            "domain",
            "branch",
            "worktree",
            "baseline_dirty_paths",
            "allowed_paths",
            "denylist_paths",
            "attempts",
            "limits",
            "last_result",
            "next_action",
            "attempt_history",
            "cleanup",
        },
        "run payload",
    )
    _require_string(payload, "run_id")
    normalize_policy_id(payload["policy"])
    _require_enum(payload, "phase", ALLOWED_PHASES)
    for key in ("task_id", "domain", "branch", "worktree", "last_result", "next_action"):
        _require_string(payload, key)
    _require_enum(payload, "last_result", ALLOWED_LAST_RESULTS)
    for key in ("baseline_dirty_paths", "allowed_paths", "denylist_paths", "attempt_history"):
        _require_list(payload, key)
    attempts = _require_object(payload["attempts"], "attempts")
    _require_object(payload["limits"], "limits")
    for key in REQUIRED_RUN_ATTEMPT_KEYS:
        _require_int(attempts, key)
    cleanup = _require_object(payload["cleanup"], "cleanup")
    for key in ("worktrees_removed", "processes_stopped", "retained_artifacts"):
        _require_list(cleanup, key)


def validate_planner_output_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "planner output payload")
    _require_keys(
        payload,
        {
            "task_id",
            "policy",
            "task_kind",
            "title",
            "goal",
            "non_goals",
            "allowed_paths",
            "denylist_paths",
            "verify_commands",
            "evaluator_scenarios_path",
            "stop_conditions",
            "next_planning_hint",
        },
        "planner output payload",
    )
    normalize_policy_id(payload["policy"])
    _require_enum(payload, "task_kind", ALLOWED_TASK_KINDS)
    for key in ("task_id", "title", "goal", "evaluator_scenarios_path", "next_planning_hint"):
        _require_string(payload, key)
    for key in ("non_goals", "allowed_paths", "denylist_paths", "verify_commands", "stop_conditions"):
        _require_list(payload, key)


def validate_generator_result_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "generator result payload")
    _require_keys(
        payload,
        {
            "task_id",
            "status",
            "changed_paths",
            "commit",
            "verify_commands",
            "verify_results",
            "artifacts",
            "cleanup_required",
            "notes",
        },
        "generator result payload",
    )
    _require_string(payload, "task_id")
    _require_enum(payload, "status", ALLOWED_GENERATOR_STATUSES)
    for key in ("changed_paths", "verify_commands", "verify_results", "artifacts"):
        _require_list(payload, key)
    for key in ("commit", "notes"):
        _require_string(payload, key)
    _require_bool(payload, "cleanup_required")


def validate_agent_attempt_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "agent attempt payload")
    _require_keys(
        payload,
        {
            "run_id",
            "role",
            "attempt",
            "started_at",
            "finished_at",
            "exit_code",
            "status",
            "prompt_path",
            "stdout_path",
            "stderr_path",
            "output_json_path",
            "diff_patch_path",
            "verify_log_paths",
        },
        "agent attempt payload",
    )
    _require_string(payload, "run_id")
    _require_enum(payload, "role", ALLOWED_AGENT_ROLES)
    _require_int(payload, "attempt")
    if payload["attempt"] < 1:
        raise ValueError("attempt must be >= 1")
    _require_int(payload, "exit_code")
    _require_enum(payload, "status", ALLOWED_AGENT_STATUSES)
    for key in (
        "started_at",
        "finished_at",
        "prompt_path",
        "stdout_path",
        "stderr_path",
        "output_json_path",
        "diff_patch_path",
    ):
        _require_string(payload, key)
    _require_list(payload, "verify_log_paths")


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_keys(payload: dict[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - payload.keys())
    if missing:
        raise ValueError(f"{label} missing required keys: {', '.join(missing)}")


def _require_string(payload: dict[str, Any], key: str) -> None:
    if key not in payload or not isinstance(payload[key], str):
        raise ValueError(f"{key} must be a string")


def _require_list(payload: dict[str, Any], key: str) -> None:
    if key not in payload or not isinstance(payload[key], list):
        raise ValueError(f"{key} must be a list")


def _require_bool(payload: dict[str, Any], key: str) -> None:
    if key not in payload or not isinstance(payload[key], bool):
        raise ValueError(f"{key} must be a bool")


def _require_int(payload: dict[str, Any], key: str) -> None:
    if key not in payload or not isinstance(payload[key], int) or isinstance(payload[key], bool):
        raise ValueError(f"{key} must be an int")


def _require_enum(payload: dict[str, Any], key: str, allowed: frozenset[str]) -> None:
    _require_string(payload, key)
    if payload[key] not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
