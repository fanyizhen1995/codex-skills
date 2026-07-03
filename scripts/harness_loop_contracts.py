import json
import re
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
ALLOWED_RUN_KINDS = frozenset({"single", "parent", "child"})
PARENT_ONLY_PHASES = frozenset({"planning", "child_running", "passed_waiting_human_merge"})
CHILD_ONLY_PHASES = frozenset({"planned", "generating", "evaluating", "artifact_hygiene", "cleanup", "passed"})
SHARED_PARENT_CHILD_PHASES = frozenset({"repair_needed", "stopped_budget", "stopped_blocked"})
ALLOWED_PHASES = ALLOWED_PHASES | frozenset({"child_running", "passed"})
ALLOWED_TASK_KINDS = frozenset(
    {
        "registered_task",
        "candidate_task",
        "task_contract_only",
        "autonomous_implementation_task",
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
ALLOWED_PLANNER_DECISIONS = frozenset({"planned", "no_action", "blocked", "failed"})
ALLOWED_DEMAND_PARENT_PLANNER_DECISIONS = frozenset({"next_child", "parent_done", "blocked", "failed"})
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
REQUIRED_LOOP_STATE_ITEM_KEYS = frozenset(
    {
        "id",
        "title",
        "source",
        "status",
        "updated_at",
        "evidence",
    }
)
REQUIRED_BLOCKED_GAP_KEYS = REQUIRED_LOOP_STATE_ITEM_KEYS | frozenset({"blocked_reason"})
REQUIRED_BLOCKED_ITEM_KEYS = REQUIRED_LOOP_STATE_ITEM_KEYS | frozenset(
    {
        "blocked_reason",
        "required_human_input",
        "retry_after",
        "retry_count",
        "last_error",
        "requires_user_input",
    }
)
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not SAFE_RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be a safe slug")
    return run_id


def run_dir_for(repo_root: Path, run_id: str) -> Path:
    validate_run_id(run_id)
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


def _optional_run_kind(payload: dict[str, Any]) -> str:
    run_kind = payload.get("run_kind", "single")
    if not isinstance(run_kind, str):
        raise ValueError("run_kind must be a string")
    if run_kind not in ALLOWED_RUN_KINDS:
        raise ValueError(f"unknown run_kind: {run_kind}")
    return run_kind


def _validate_run_kind_phase(run_kind: str, phase: str) -> None:
    if run_kind == "parent" and phase not in (PARENT_ONLY_PHASES | SHARED_PARENT_CHILD_PHASES):
        raise ValueError(f"parent phase is not allowed: {phase}")
    if run_kind == "child" and phase not in (CHILD_ONLY_PHASES | SHARED_PARENT_CHILD_PHASES):
        raise ValueError(f"child phase is not allowed: {phase}")


def _require_reader_summary(payload: dict[str, Any], keys: set[str]) -> None:
    summary = _require_object(payload.get("reader_summary"), "reader_summary")
    _require_keys(summary, keys, "reader_summary")
    for key in keys:
        _require_string(summary, key)


def _validate_parent_run_payload(payload: dict[str, Any]) -> None:
    for key in ("child_run_ids", "backlog", "accepted_changed_paths"):
        _require_list(payload, key)
    _require_string(payload, "current_child_run_id")
    aggregate = _require_object(payload.get("aggregate_acceptance"), "aggregate_acceptance")
    for key in ("total", "passed", "failed", "blocked", "pending"):
        _require_int(aggregate, key)
    _require_bool(aggregate, "user_decision_required")
    _require_reader_summary(payload, {"purpose", "current_progress", "next_step", "decision_needed"})


def _validate_child_run_payload(payload: dict[str, Any]) -> None:
    _require_string(payload, "parent_run_id")
    if not payload["parent_run_id"]:
        raise ValueError("child run requires parent_run_id")
    _require_int(payload, "child_index")
    _require_reader_summary(
        payload,
        {"purpose", "planner_action", "generator_action", "evaluator_action", "acceptance_result"},
    )


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
    validate_run_id(payload["run_id"])
    normalize_policy_id(payload["policy"])
    _require_enum(payload, "phase", ALLOWED_PHASES)
    run_kind = _optional_run_kind(payload)
    _validate_run_kind_phase(run_kind, payload["phase"])
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
    if run_kind == "parent":
        _validate_parent_run_payload(payload)
    elif run_kind == "child":
        _validate_child_run_payload(payload)


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
    _require_enum(payload, "task_kind", ALLOWED_TASK_KINDS)
    if policy == "demand_development" and payload["task_kind"] == "autonomous_implementation_task":
        raise ValueError("autonomous_implementation_task requires autonomous_knowledge policy")
    for key in ("task_id", "title", "goal", "evaluator_scenarios_path", "next_planning_hint"):
        _require_string(payload, key)
    for key in ("non_goals", "allowed_paths", "denylist_paths", "verify_commands", "stop_conditions"):
        _require_list(payload, key)
    if _has_multi_task_planner_fields(payload):
        _validate_multi_task_planner_fields(payload)


def _has_multi_task_planner_fields(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in (
            "planner_decision",
            "next_child_task",
            "backlog",
            "blocked_reason",
            "done_criteria",
            "reader_summary",
            "decision_required",
        )
    )


def _validate_next_child_task(payload: dict[str, Any]) -> None:
    task = _require_object(payload, "next_child_task")
    _require_keys(
        task,
        {
            "child_id",
            "title",
            "description",
            "allowed_paths",
            "denylist_paths",
            "verify_commands",
            "scenario_commands",
            "done_criteria",
        },
        "next_child_task",
    )
    for key in ("child_id", "title", "description"):
        _require_string(task, key)
        if not task[key]:
            raise ValueError(f"next_child_task.{key} must not be empty")
    for key in ("allowed_paths", "denylist_paths", "verify_commands", "scenario_commands", "done_criteria"):
        _require_list(task, key)


def _validate_multi_task_planner_fields(payload: dict[str, Any]) -> None:
    _require_enum(payload, "planner_decision", ALLOWED_DEMAND_PARENT_PLANNER_DECISIONS)
    _require_list(payload, "backlog")
    _require_string(payload, "blocked_reason")
    _require_list(payload, "done_criteria")
    _require_reader_summary(payload, {"purpose", "current_progress", "next_step", "decision_needed"})
    _require_bool(payload, "decision_required")
    decision = payload["planner_decision"]
    next_child_task = payload.get("next_child_task")
    if decision == "next_child":
        _validate_next_child_task(next_child_task)
    else:
        if isinstance(next_child_task, dict) and next_child_task:
            raise ValueError("next_child_task must be empty unless planner_decision is next_child")
        if decision == "parent_done" and not payload["done_criteria"]:
            raise ValueError("done_criteria must not be empty for parent_done")
        if decision in {"blocked", "failed"} and not payload["blocked_reason"]:
            raise ValueError("blocked_reason must not be empty for blocked or failed")


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


def validate_loop_state_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "loop state payload")
    _require_keys(
        payload,
        {
            "policy",
            "domain",
            "domain_goal",
            "last_planner_decision",
            "last_scan_at",
            "scan_ttl_days",
            "candidate_backlog",
            "coverage_gaps",
            "known_sources",
            "blocked_items",
            "no_action_evidence",
        },
        "loop state payload",
    )
    policy = normalize_policy_id(payload["policy"])
    if policy != "autonomous_knowledge":
        raise ValueError("loop state payload only supports autonomous_knowledge policy")
    for key in ("domain", "domain_goal", "last_planner_decision", "last_scan_at"):
        _require_string(payload, key)
    _require_enum(payload, "last_planner_decision", ALLOWED_PLANNER_DECISIONS)
    _require_int(payload, "scan_ttl_days")
    if payload["scan_ttl_days"] < 1:
        raise ValueError("scan_ttl_days must be >= 1")
    for key in ("candidate_backlog", "known_sources", "no_action_evidence"):
        _require_loop_state_item_list(payload, key, REQUIRED_LOOP_STATE_ITEM_KEYS)
    _require_loop_state_item_list(payload, "coverage_gaps", REQUIRED_BLOCKED_GAP_KEYS)
    if payload["last_planner_decision"] == "no_action" and not payload["no_action_evidence"]:
        raise ValueError("no_action_evidence must not be empty for no_action decisions")
    for index, gap in enumerate(payload["coverage_gaps"]):
        if gap["status"] != "blocked":
            raise ValueError(f"coverage_gaps[{index}].status must be blocked")
        if not isinstance(gap["blocked_reason"], str):
            raise ValueError(f"coverage_gaps[{index}].blocked_reason must be a string")
    _require_loop_state_item_list(payload, "blocked_items", REQUIRED_BLOCKED_ITEM_KEYS)


def validate_loop_policy_payload(payload: dict[str, Any]) -> None:
    _require_object(payload, "loop policy payload")
    _require_keys(
        payload,
        {
            "policy",
            "auto_commit",
            "auto_merge_main",
            "allowed_paths",
            "manual_confirm_paths",
            "denylist_paths",
            "limits",
            "required_evidence",
        },
        "loop policy payload",
    )
    normalize_policy_id(payload["policy"])
    _require_bool(payload, "auto_commit")
    _require_bool(payload, "auto_merge_main")
    for key in ("allowed_paths", "manual_confirm_paths", "denylist_paths", "required_evidence"):
        _require_string_list(payload, key)
    limits = _require_object(payload["limits"], "limits")
    for key in default_limits():
        _require_int(limits, key)


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


def _require_loop_state_item_list(
    payload: dict[str, Any],
    key: str,
    required_keys: frozenset[str],
) -> None:
    _require_list(payload, key)
    for index, item in enumerate(payload[key]):
        if not isinstance(item, dict):
            raise ValueError(f"{key}[{index}] must be an object")
        missing = sorted(required_keys - item.keys())
        if missing:
            raise ValueError(f"{key}[{index}] missing required keys: {', '.join(missing)}")
        for item_key in ("id", "title", "source", "status", "updated_at"):
            if not isinstance(item[item_key], str):
                raise ValueError(f"{key}[{index}].{item_key} must be a string")
        if not isinstance(item["evidence"], list):
            raise ValueError(f"{key}[{index}].evidence must be a list")
        if key != "blocked_items" and not item["evidence"]:
            raise ValueError(f"{key}[{index}].evidence must not be empty")
        for evidence_index, evidence in enumerate(item["evidence"]):
            if not isinstance(evidence, str):
                raise ValueError(f"{key}[{index}].evidence[{evidence_index}] must be a string")
        if required_keys == REQUIRED_BLOCKED_ITEM_KEYS:
            for item_key in ("blocked_reason", "required_human_input", "retry_after", "last_error"):
                if not isinstance(item[item_key], str):
                    raise ValueError(f"{key}[{index}].{item_key} must be a string")
            if not isinstance(item["requires_user_input"], bool):
                raise ValueError(f"{key}[{index}].requires_user_input must be a bool")
            if not isinstance(item["retry_count"], int) or isinstance(item["retry_count"], bool):
                raise ValueError(f"{key}[{index}].retry_count must be an int")


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
