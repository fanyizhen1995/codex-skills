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
    }
)
ALLOWED_GENERATOR_STATUSES = frozenset({"implemented", "repaired", "blocked", "failed"})
ALLOWED_EVALUATOR_STATUSES = frozenset({"pass", "fail", "blocked"})
ALLOWED_AGENT_ROLES = frozenset({"planner", "generator", "evaluator"})
REQUIRED_RUN_ATTEMPT_KEYS = frozenset(
    {"planner", "generator", "evaluator", "artifact_hygiene", "cleanup"}
)
ALLOWED_AGENT_STATUSES = frozenset(
    {"pass", "fail", "blocked", "timeout", "invalid_json"}
)
ALLOWED_LAST_RESULTS = frozenset({"pass", "fail", "blocked", "none"})
ALLOWED_SCENARIO_COMMAND_STATUSES = frozenset({"pass", "fail", "timeout"})
ALLOWED_ARTIFACT_HYGIENE_STATUSES = frozenset({"pass", "redacted", "blocked"})
REQUIRED_USER_SCENARIO_KEYS = frozenset(
    {
        "scenario_id",
        "user_goal",
        "prerequisites",
        "steps",
        "expected_outcomes",
        "failure_signals",
    }
)


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
            "requirement",
            "constraints",
            "stop_conditions",
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
    policy = normalize_policy_id(payload["policy"])
    if policy != "demand_development":
        raise ValueError("Phase 1 run payload only supports demand_development policy")
    _require_enum(payload, "phase", ALLOWED_PHASES)
    for key in ("task_id", "domain", "branch", "worktree", "requirement", "last_result", "next_action"):
        _require_string(payload, key)
    _require_enum(payload, "last_result", ALLOWED_LAST_RESULTS)
    for key in (
        "constraints",
        "stop_conditions",
        "baseline_dirty_paths",
        "allowed_paths",
        "denylist_paths",
        "attempt_history",
    ):
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
    policy = normalize_policy_id(payload["policy"])
    if policy != "demand_development":
        raise ValueError("Phase 1 planner output only supports demand_development policy")
    if payload["task_kind"] == "autonomous_implementation_task":
        raise ValueError("Phase 1 planner output rejects autonomous_implementation_task")
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


def validate_evaluator_result_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "evaluator result payload")
    _require_keys(
        payload,
        {
            "status",
            "task_id",
            "driver",
            "returncode",
            "stdout",
            "stderr",
        },
        "evaluator result payload",
    )
    _require_enum(payload, "status", ALLOWED_EVALUATOR_STATUSES)
    for key in ("task_id", "driver", "stdout", "stderr"):
        _require_string(payload, key)
    _require_int(payload, "returncode")


def validate_task_contract_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "task contract payload")
    _require_keys(
        payload,
        {
            "task_id",
            "title",
            "description",
            "verify_commands",
            "scenario_commands",
            "artifact_paths",
            "required_services",
            "evaluator_driver",
            "eval_policy",
            "allowed_scope",
            "must_simulate",
            "user_scenarios",
        },
        "task contract payload",
    )
    for key in ("task_id", "title", "description", "evaluator_driver", "allowed_scope"):
        _require_string(payload, key)
    for key in ("verify_commands", "scenario_commands", "artifact_paths", "required_services"):
        _require_string_list(payload, key)
    _require_scenario_list(payload, "user_scenarios")
    _require_object(payload["eval_policy"], "eval_policy")
    _require_bool(payload, "must_simulate")


def validate_scenario_command_result_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "scenario command result payload")
    _require_keys(
        payload,
        {
            "command",
            "cwd",
            "exit_code",
            "stdout_path",
            "stderr_path",
            "duration_seconds",
            "status",
        },
        "scenario command result payload",
    )
    for key in ("command", "cwd", "stdout_path", "stderr_path"):
        _require_string(payload, key)
    _require_int(payload, "exit_code")
    _require_int(payload, "duration_seconds")
    if payload["duration_seconds"] < 0:
        raise ValueError("duration_seconds must be >= 0")
    _require_enum(payload, "status", ALLOWED_SCENARIO_COMMAND_STATUSES)


def validate_artifact_hygiene_result_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "artifact hygiene result payload")
    _require_keys(
        payload,
        {
            "status",
            "scanned_paths",
            "redacted_paths",
            "omitted_paths",
            "manifest_path",
            "redaction_manifest_path",
            "original_hashes",
            "redaction_map",
            "findings",
        },
        "artifact hygiene result payload",
    )
    _require_enum(payload, "status", ALLOWED_ARTIFACT_HYGIENE_STATUSES)
    for key in ("scanned_paths", "redacted_paths", "omitted_paths", "redaction_map", "findings"):
        _require_list(payload, key)
    for key in ("manifest_path", "redaction_manifest_path"):
        _require_string(payload, key)
    _require_object(payload["original_hashes"], "original_hashes")


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


def _require_string_list(payload: dict[str, Any], key: str) -> None:
    _require_list(payload, key)
    for index, item in enumerate(payload[key]):
        if not isinstance(item, str):
            raise ValueError(f"{key}[{index}] must be a string")


def _require_scenario_list(payload: dict[str, Any], key: str) -> None:
    _require_list(payload, key)
    for index, scenario in enumerate(payload[key]):
        if not isinstance(scenario, dict):
            raise ValueError(f"{key}[{index}] must be an object")
        missing = sorted(REQUIRED_USER_SCENARIO_KEYS - scenario.keys())
        if missing:
            raise ValueError(f"{key}[{index}] missing required keys: {', '.join(missing)}")
        for scenario_key in ("scenario_id", "user_goal"):
            if not isinstance(scenario[scenario_key], str):
                raise ValueError(f"{key}[{index}].{scenario_key} must be a string")
        for scenario_key in ("prerequisites", "steps", "expected_outcomes", "failure_signals"):
            if not isinstance(scenario[scenario_key], list):
                raise ValueError(f"{key}[{index}].{scenario_key} must be a list")
            for item_index, item in enumerate(scenario[scenario_key]):
                if not isinstance(item, str):
                    raise ValueError(f"{key}[{index}].{scenario_key}[{item_index}] must be a string")


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
