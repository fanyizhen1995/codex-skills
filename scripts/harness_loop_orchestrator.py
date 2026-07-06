#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.harness_loop_contracts import (
        default_limits,
        load_loop_policy,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
        validate_run_id,
        validate_artifact_hygiene_result_payload,
        validate_evaluator_result_payload,
        validate_generator_result_payload,
        validate_planner_output_payload,
        validate_run_payload,
        validate_task_contract_payload,
        write_json_file,
    )
    from scripts.harness_loop_agents import run_codex_prompt
    from scripts.harness_loop_artifacts import run_artifact_hygiene, run_scenario_commands
    from scripts.harness_loop_autonomous import (
        check_autonomous_scope,
        check_supply_chain,
        create_default_coverage_map,
        decide_no_action,
        load_or_create_coverage_map,
        load_or_create_loop_state,
        policy_patterns_for_run,
        run_git_commit,
        validate_ai_infra_coverage_map_semantics,
        write_coverage_map,
        write_loop_state,
    )
except ModuleNotFoundError:
    from harness_loop_contracts import (  # type: ignore[no-redef]
        default_limits,
        load_loop_policy,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
        validate_run_id,
        validate_artifact_hygiene_result_payload,
        validate_evaluator_result_payload,
        validate_generator_result_payload,
        validate_planner_output_payload,
        validate_run_payload,
        validate_task_contract_payload,
        write_json_file,
    )
    from harness_loop_agents import run_codex_prompt  # type: ignore[no-redef]
    from harness_loop_artifacts import run_artifact_hygiene, run_scenario_commands  # type: ignore[no-redef]
    from harness_loop_autonomous import (  # type: ignore[no-redef]
        check_autonomous_scope,
        check_supply_chain,
        create_default_coverage_map,
        decide_no_action,
        load_or_create_coverage_map,
        load_or_create_loop_state,
        policy_patterns_for_run,
        run_git_commit,
        validate_ai_infra_coverage_map_semantics,
        write_coverage_map,
        write_loop_state,
    )


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _current_branch(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    branch = result.stdout.strip()
    return branch or "unknown"


def _baseline_dirty_paths(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _preflight_markdown(run_id: str, mode: str, requirement: str) -> str:
    return f"""# Planner Loop Preflight

- Run ID: `{run_id}`
- Mode: `{mode}`
- Created At: `{_timestamp()}`

## Requirement

{requirement}

## Fallback Questionnaire

1. 这个需求的最终用户或使用者是谁？
2. 完成后最重要的可观察结果是什么？
3. 哪些文件、目录或系统边界不能修改？
4. 哪些验证命令或手动检查必须通过？
5. 是否需要创建、更新或跳过 evaluator 场景？
6. 失败时应停止、重试，还是降级为人工确认？
7. 是否存在安全、凭据、网络或权限限制？
8. 完成后是否需要 commit、保留产物，或等待人工合并？
"""


def _task_id_for_run(run_id: str) -> str:
    return f"{run_id}-task"


def _child_run_id(parent_run_id: str, child_index: int) -> str:
    return f"{parent_run_id}-child-{child_index:03d}"


def _event_path(repo_root: Path, run_id: str) -> Path:
    return run_dir_for(repo_root, run_id) / "events.jsonl"


def append_loop_event(
    repo_root: Path,
    *,
    run_id: str,
    actor: str,
    event_type: str,
    summary: str,
    parent_run_id: str = "",
    child_id: str = "",
    details: dict[str, Any] | None = None,
    artifact_paths: list[str] | None = None,
) -> Path:
    payload = {
        "timestamp": _timestamp(),
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "child_id": child_id,
        "actor": actor,
        "event_type": event_type,
        "summary": summary,
        "details": details or {},
        "artifact_paths": artifact_paths or [],
    }
    path = _event_path(repo_root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _ensure_parent_fields(run: dict[str, Any]) -> dict[str, Any]:
    run.setdefault("run_kind", "parent")
    if run.get("run_kind") == "single":
        run["run_kind"] = "parent"
    if run.get("phase") == "planned":
        run["phase"] = "planning"
        run["next_action"] = "run_parent_planner"
    run.setdefault("child_run_ids", [])
    run.setdefault("current_child_run_id", "")
    run.setdefault("backlog", [])
    run.setdefault(
        "aggregate_acceptance",
        {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "pending": 0, "user_decision_required": False},
    )
    run.setdefault(
        "reader_summary",
        {"purpose": run.get("requirement", ""), "current_progress": "", "next_step": "", "decision_needed": "No"},
    )
    run.setdefault("accepted_changed_paths", [])
    return run


def _aggregate_pending(aggregate: dict[str, Any]) -> int:
    return max(
        0,
        int(aggregate.get("total", 0))
        - int(aggregate.get("passed", 0))
        - int(aggregate.get("failed", 0))
        - int(aggregate.get("blocked", 0)),
    )


def _dirty_paths_after_baseline(repo_root: Path, parent: dict[str, Any], child: dict[str, Any]) -> list[str]:
    baseline: set[str] = set()
    for value in parent.get("baseline_dirty_paths", []):
        if not isinstance(value, str):
            continue
        baseline.add(value)
        baseline.update(_parse_porcelain_paths(value))
    accepted = {str(path) for path in parent.get("accepted_changed_paths", [])}
    allowed = {str(path) for path in child.get("allowed_paths", [])}
    unexpected: list[str] = []
    for porcelain in _baseline_dirty_paths(repo_root):
        paths = _parse_porcelain_paths(porcelain)
        for path in paths:
            if _is_demand_internal_dirty_path(path, parent, child):
                continue
            if path in accepted:
                continue
            if porcelain in baseline or path in baseline:
                if path in allowed:
                    unexpected.append(path)
                continue
            if path in allowed:
                continue
            unexpected.append(path)
    return sorted(set(unexpected))


def _baseline_dirty_overlap(parent: dict[str, Any], candidate_paths: list[str]) -> list[str]:
    baseline = _baseline_dirty_relative_paths(parent)
    accepted = {str(path) for path in parent.get("accepted_changed_paths", [])}
    return sorted({str(path) for path in candidate_paths if str(path) in baseline and str(path) not in accepted})


def _is_demand_internal_dirty_path(path: str, parent: dict[str, Any], child: dict[str, Any]) -> bool:
    parent_run_id = str(parent["run_id"])
    child_run_ids = {str(run_id) for run_id in parent.get("child_run_ids", [])}
    child_run_ids.add(str(child["run_id"]))
    expected_paths = {
        f".codex/loop-runs/{parent_run_id}/events.jsonl",
        f".codex/loop-runs/{parent_run_id}/planner-output.json",
        f".codex/loop-runs/{parent_run_id}/preflight.md",
        f".codex/loop-runs/{parent_run_id}/run.json",
    }
    for child_run_id in child_run_ids:
        expected_paths.update(
            {
                f".codex/loop-runs/{child_run_id}/events.jsonl",
                f".codex/loop-runs/{child_run_id}/evaluator-result.json",
                f".codex/loop-runs/{child_run_id}/generator-result.json",
                f".codex/loop-runs/{child_run_id}/planner-output.json",
                f".codex/loop-runs/{child_run_id}/run.json",
                f".codex/loop-runs/{child_run_id}/task-contract.json",
            }
        )
    return path in expected_paths


def _block_parent(repo_root: Path, parent: dict[str, Any], reason: str, *, actor: str = "orchestrator") -> dict[str, str]:
    parent = _ensure_parent_fields(parent)
    aggregate = parent["aggregate_acceptance"]
    if aggregate.get("total", 0) and not aggregate.get("blocked", 0):
        aggregate["blocked"] = 1
    aggregate["pending"] = _aggregate_pending(aggregate)
    aggregate["user_decision_required"] = True
    parent["phase"] = "stopped_blocked"
    parent["last_result"] = "blocked"
    parent["next_action"] = "inspect_blocked_diagnostics"
    parent["reader_summary"]["current_progress"] = "Blocked"
    parent["reader_summary"]["next_step"] = "Inspect blocked diagnostics"
    parent["reader_summary"]["decision_needed"] = "Yes"
    save_run(repo_root, parent)
    append_loop_event(repo_root, run_id=parent["run_id"], actor=actor, event_type="blocked", summary=reason)
    return status_for_run(repo_root, parent["run_id"])


def _block_child(repo_root: Path, child: dict[str, Any], reason: str, *, actor: str = "orchestrator") -> dict[str, str]:
    child["phase"] = "stopped_blocked"
    child["last_result"] = "blocked"
    child["next_action"] = "inspect_blocked_diagnostics"
    child["reader_summary"]["evaluator_action"] = "Blocked before evaluator"
    child["reader_summary"]["acceptance_result"] = "Blocked"
    save_run(repo_root, child)
    append_loop_event(
        repo_root,
        run_id=child["run_id"],
        parent_run_id=child["parent_run_id"],
        child_id=f"child-{int(child['child_index']):03d}",
        actor=actor,
        event_type="blocked",
        summary=reason,
    )
    return status_for_run(repo_root, child["run_id"])


def _reconcile_passed_demand_children(repo_root: Path, parent: dict[str, Any]) -> tuple[dict[str, Any], str]:
    parent = _ensure_parent_fields(parent)
    accepted: set[str] = set()
    passed_count = 0
    for child_run_id in parent["child_run_ids"]:
        child = load_run(repo_root, str(child_run_id))
        if child.get("phase") != "passed":
            continue
        passed_count += 1
        try:
            generator_result = read_json_file(run_dir_for(repo_root, child["run_id"]) / "generator-result.json")
            validate_generator_result_payload(generator_result)
        except (OSError, RuntimeError, ValueError) as exc:
            reason = f"passed child artifact invalid for {child['run_id']}: {exc}"
            _block_parent(repo_root, parent, reason)
            return parent, "blocked"
        accepted.update(str(path) for path in generator_result["changed_paths"])
    parent["accepted_changed_paths"] = sorted(accepted)
    parent["aggregate_acceptance"]["passed"] = passed_count
    parent["aggregate_acceptance"]["pending"] = _aggregate_pending(parent["aggregate_acceptance"])
    return parent, "ok"


def _reconcile_demand_parent_children(repo_root: Path, parent: dict[str, Any]) -> str:
    parent, status = _reconcile_passed_demand_children(repo_root, parent)
    if status == "blocked":
        return "blocked"
    for child_run_id in parent["child_run_ids"]:
        child = load_run(repo_root, str(child_run_id))
        if child.get("phase") == "passed":
            continue
        if child.get("phase") == "stopped_blocked":
            save_run(repo_root, parent)
            _block_parent(
                repo_root,
                parent,
                f"reconcile blocked child {child['run_id']} in phase {child['phase']}",
            )
            return "blocked"

        parent["phase"] = "child_running"
        parent["current_child_run_id"] = child["run_id"]
        parent["next_action"] = str(child.get("next_action") or "inspect_child_state")
        parent["reader_summary"]["current_progress"] = f"Waiting for child {child['child_index']}"
        parent["reader_summary"]["next_step"] = parent["next_action"]
        parent["reader_summary"]["decision_needed"] = "No"
        parent["aggregate_acceptance"]["pending"] = _aggregate_pending(parent["aggregate_acceptance"])
        save_run(repo_root, parent)
        append_loop_event(
            repo_root,
            run_id=parent["run_id"],
            actor="orchestrator",
            event_type="wait",
            summary=f"reconcile current child {child['run_id']} in phase {child['phase']}",
            child_id=f"child-{int(child['child_index']):03d}",
            details={
                "child_run_id": child["run_id"],
                "child_phase": child["phase"],
                "child_next_action": child.get("next_action", ""),
            },
        )
        return "waiting"

    save_run(repo_root, parent)
    return "ready"


def _create_child_run(
    repo_root: Path,
    parent: dict[str, Any],
    child_index: int,
    child_task: dict[str, Any],
) -> dict[str, Any]:
    child_run_id = _child_run_id(parent["run_id"], child_index)
    child = {
        "run_id": child_run_id,
        "run_kind": "child",
        "parent_run_id": parent["run_id"],
        "child_index": child_index,
        "policy": "demand_development",
        "phase": "generating",
        "task_id": f"{child_run_id}-task",
        "domain": "",
        "branch": parent.get("branch", ""),
        "worktree": parent.get("worktree", ""),
        "requirement": str(child_task.get("description") or child_task.get("title") or parent.get("requirement", "")),
        "constraints": list(parent.get("constraints", [])),
        "stop_conditions": ["passed"],
        "baseline_dirty_paths": list(parent.get("baseline_dirty_paths", [])),
        "allowed_paths": list(child_task.get("allowed_paths", [])),
        "denylist_paths": list(child_task.get("denylist_paths", [])),
        "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
        "limits": dict(parent.get("limits", default_limits())),
        "last_result": "none",
        "next_action": "run_child_generator",
        "attempt_history": [],
        "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        "reader_summary": {
            "purpose": str(child_task.get("title", "")),
            "planner_action": "Parent planner selected this child",
            "generator_action": "",
            "evaluator_action": "",
            "acceptance_result": "",
        },
    }
    save_run(repo_root, child)

    planner_payload = {
        "task_id": child["task_id"],
        "policy": "demand_development",
        "task_kind": "task_contract_only",
        "title": str(child_task.get("title", "")),
        "goal": str(child_task.get("description", "")),
        "non_goals": [],
        "allowed_paths": list(child_task.get("allowed_paths", [])),
        "denylist_paths": list(child_task.get("denylist_paths", [])),
        "verify_commands": list(child_task.get("verify_commands", [])),
        "evaluator_scenarios_path": "",
        "stop_conditions": ["passed"],
        "next_planning_hint": "return to parent planner",
    }
    validate_planner_output_payload(planner_payload)
    write_json_file(run_dir_for(repo_root, child_run_id) / "planner-output.json", planner_payload)

    expected_outcomes = list(child_task.get("done_criteria", [])) or ["Child passes fake evaluator."]
    task_contract = {
        "task_id": child["task_id"],
        "title": str(child_task.get("title", "")),
        "description": str(child_task.get("description", "")),
        "verify_commands": list(child_task.get("verify_commands", [])),
        "scenario_commands": list(child_task.get("scenario_commands", [])),
        "artifact_paths": list(child_task.get("allowed_paths", [])),
        "required_services": [],
        "evaluator_driver": "harness_auto_gate",
        "eval_policy": {"task_level_required": True, "task_scope": "local_repo_and_harness"},
        "allowed_scope": "local_repo_and_harness",
        "must_simulate": True,
        "user_scenarios": [
            {
                "scenario_id": f"{child_run_id}-scenario",
                "user_goal": str(child_task.get("description", "")),
                "prerequisites": ["Parent demand multi-task run exists."],
                "steps": ["Run child generator.", "Run child evaluator."],
                "expected_outcomes": expected_outcomes,
                "failure_signals": ["Child evaluator fails.", "Changed paths leave allowed scope."],
            }
        ],
    }
    validate_task_contract_payload(task_contract)
    write_json_file(run_dir_for(repo_root, child_run_id) / "task-contract.json", task_contract)

    append_loop_event(
        repo_root,
        run_id=child_run_id,
        parent_run_id=parent["run_id"],
        child_id=str(child_task.get("child_id", "")),
        actor="planner",
        event_type="plan",
        summary=f"Planner selected child {child_index}: {child_task.get('title', '')}",
    )
    return child


def _read_requirement(run_dir: Path) -> str:
    text = (run_dir / "preflight.md").read_text(encoding="utf-8")
    marker = "## Requirement"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].split("##", 1)[0].strip()


def _planner_prompt(requirement: str, run_id: str) -> str:
    output_path = f".codex/loop-runs/{run_id}/planner-output.json"
    return "\n".join(
        [
            "Planner agent task.",
            f"Write {output_path} only.",
            "The JSON payload must satisfy scripts.harness_loop_contracts.validate_planner_output_payload.",
            "Use policy demand_development and task_kind registered_task unless the requirement explicitly says otherwise.",
            f"Run ID: {run_id}",
            f"Requirement: {requirement}",
            "",
        ]
    )


def _generator_prompt(run_id: str) -> str:
    planner_output_path = f".codex/loop-runs/{run_id}/planner-output.json"
    output_path = f".codex/loop-runs/{run_id}/generator-result.json"
    return "\n".join(
        [
            "Generator agent task.",
            f"Read {planner_output_path}.",
            f"Write {output_path}.",
            "The JSON payload must satisfy scripts.harness_loop_contracts.validate_generator_result_payload.",
            "Do not mark final completion; evaluator decides.",
            "",
        ]
    )


def _autonomous_planner_prompt(run: dict[str, Any], run_dir: Path) -> str:
    output_path = run_dir / "planner-output.json"
    state_path = f"personal-wiki/domains/{run['domain']}/loop-state.json"
    return "\n".join(
        [
            "Autonomous knowledge planner agent task.",
            f"Read {state_path} and the current repository state.",
            f"Write {output_path} only.",
            "The JSON payload must satisfy scripts.harness_loop_contracts.validate_planner_output_payload.",
            "Use policy autonomous_knowledge and task_kind autonomous_implementation_task when work is actionable.",
            "If there is no actionable work, update loop-state.json no-action evidence and do not write unrelated files.",
            f"Run ID: {run['run_id']}",
            f"Domain: {run['domain']}",
            f"Requirement: {run['requirement']}",
            "",
        ]
    )


def _autonomous_generator_prompt(run: dict[str, Any], run_dir: Path) -> str:
    planner_output_path = run_dir / "planner-output.json"
    output_path = run_dir / "generator-result.json"
    return "\n".join(
        [
            "Autonomous knowledge generator agent task.",
            f"Read {planner_output_path}.",
            f"Write {output_path}.",
            "The JSON payload must satisfy scripts.harness_loop_contracts.validate_generator_result_payload.",
            "Only modify paths allowed by planner-output.json and the autonomous policy.",
            "Run verification commands and include non-empty verify_results when dependency files change.",
            f"Run ID: {run['run_id']}",
            f"Domain: {run['domain']}",
            "",
        ]
    )


def _autonomous_evaluator_prompt(run: dict[str, Any], run_dir: Path) -> str:
    generator_result_path = run_dir / "generator-result.json"
    output_path = run_dir / "evaluator-result.json"
    return "\n".join(
        [
            "Autonomous knowledge evaluator agent task.",
            f"Read {generator_result_path}.",
            f"Write {output_path}.",
            "The JSON payload must satisfy scripts.harness_loop_contracts.validate_evaluator_result_payload.",
            "Verify changed wiki/raw/source artifacts from a user or operator perspective where applicable.",
            "Do not modify repository files other than the evaluator result.",
            f"Run ID: {run['run_id']}",
            f"Task ID: {run['task_id']}",
            f"Domain: {run['domain']}",
            "",
        ]
    )


def load_run(repo_root: Path | str, run_id: str) -> dict[str, Any]:
    payload = read_json_file(run_dir_for(Path(repo_root), run_id) / "run.json")
    validate_run_payload(payload)
    return payload


def save_run(repo_root: Path | str, payload: dict[str, Any]) -> dict[str, Any]:
    validate_run_payload(payload)
    write_json_file(run_dir_for(Path(repo_root), payload["run_id"]) / "run.json", payload)
    return payload


def create_preflight_run(
    repo_root: Path | str,
    mode: str,
    requirement: str,
    run_id: str,
    confirm: bool = False,
    task_id: str = "",
    domain: str = "",
    constraints: list[str] | None = None,
    stop_conditions: list[str] | None = None,
    policy_file: str = "",
) -> dict[str, Any]:
    root = Path(repo_root)
    validate_run_id(run_id)
    policy = normalize_policy_id(mode)
    if policy not in {"demand_development", "autonomous_knowledge"}:
        raise ValueError(f"unsupported preflight policy: {policy}")
    constraints = list(constraints or [])
    if policy == "autonomous_knowledge":
        if not domain:
            raise ValueError("autonomous_knowledge preflight requires domain")
        stop_conditions = list(stop_conditions or ["stopped_no_action", "stopped_budget", "stopped_blocked"])
        phase = "planning" if confirm else "preflight"
        next_action = "run_autonomous_planner" if confirm else "await_preflight_confirmation"
    else:
        stop_conditions = list(stop_conditions or ["passed_waiting_human_merge"])
        phase = "planned" if confirm else "preflight"
        next_action = "run_planner" if confirm else "await_preflight_confirmation"
    baseline_dirty_paths = _baseline_dirty_paths(root)
    policy_payload: dict[str, Any] | None = None
    if policy_file:
        policy_payload = load_loop_policy(root, policy_file)
        if policy_payload["policy"] != policy:
            raise ValueError("policy_file policy must match requested mode")
    run_dir = run_dir_for(root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "preflight.md").write_text(
        _preflight_markdown(run_id=run_id, mode=mode, requirement=requirement),
        encoding="utf-8",
    )
    payload = {
        "run_id": run_id,
        "policy": policy,
        "phase": phase,
        "task_id": task_id,
        "domain": domain,
        "branch": _current_branch(root),
        "worktree": str(root.resolve()),
        "requirement": requirement,
        "constraints": constraints,
        "stop_conditions": stop_conditions,
        "baseline_dirty_paths": baseline_dirty_paths,
        "allowed_paths": [],
        "denylist_paths": [],
        "attempts": {
            "planner": 0,
            "generator": 0,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
        },
        "limits": default_limits(),
        "last_result": "none",
        "next_action": next_action,
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
    }
    if policy == "autonomous_knowledge":
        payload["allowed_paths"], payload["denylist_paths"], payload["manual_confirm_paths"] = policy_patterns_for_run(
            {},
            domain=domain,
        )
    if policy_payload is not None:
        payload["allowed_paths"] = list(policy_payload["allowed_paths"])
        payload["denylist_paths"] = list(policy_payload["denylist_paths"])
        payload["manual_confirm_paths"] = list(policy_payload["manual_confirm_paths"])
        payload["required_evidence"] = list(policy_payload["required_evidence"])
        payload["limits"] = {**default_limits(), **policy_payload["limits"]}
        payload["policy_file"] = policy_file
    return save_run(root, payload)


def confirm_preflight(repo_root: Path | str, run_id: str) -> dict[str, Any]:
    payload = load_run(repo_root, run_id)
    if payload["policy"] == "autonomous_knowledge":
        payload["phase"] = "planning"
        payload["next_action"] = "run_autonomous_planner"
    else:
        payload["phase"] = "planned"
        payload["next_action"] = "run_planner"
    return save_run(repo_root, payload)


def run_planner(repo_root: Path | str, run_id: str, *, driver: str) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] != "planned":
        raise RuntimeError(f"run_planner requires phase planned; current phase is {run['phase']}")
    run_dir = run_dir_for(root, run_id)
    output_path = run_dir / "planner-output.json"
    task_id = run["task_id"] or _task_id_for_run(run_id)
    attempt = int(run["attempts"]["planner"]) + 1

    if driver == "fake":
        payload = {
            "task_id": task_id,
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": f"Loop task {run_id}",
            "goal": _read_requirement(run_dir),
            "non_goals": [],
            "allowed_paths": list(run.get("allowed_paths", [])),
            "denylist_paths": list(run.get("denylist_paths", [])),
            "verify_commands": [],
            "evaluator_scenarios_path": "",
            "stop_conditions": list(run.get("stop_conditions", ["passed_waiting_human_merge"])),
            "next_planning_hint": "",
        }
        validate_planner_output_payload(payload)
        write_json_file(output_path, payload)
    elif driver == "codex-exec":
        prompt_path = run_dir / "planner-prompt.md"
        prompt_path.write_text(
            _planner_prompt(requirement=_read_requirement(run_dir), run_id=run_id),
            encoding="utf-8",
        )
        output_path.unlink(missing_ok=True)
        attempt_payload = run_codex_prompt(
            role="planner",
            run_id=run_id,
            repo_root=root,
            run_dir=run_dir,
            prompt_path=prompt_path,
            output_json_path=output_path,
            attempt=attempt,
            timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
        )
        run["attempts"]["planner"] = attempt
        save_run(root, run)
        if not isinstance(attempt_payload, dict) or attempt_payload.get("status") != "pass":
            status = attempt_payload.get("status") if isinstance(attempt_payload, dict) else type(attempt_payload).__name__
            raise RuntimeError(f"planner codex-exec attempt failed with status {status}")
    else:
        raise ValueError(f"unsupported planner driver: {driver}")

    planner_payload = read_json_file(output_path)
    validate_planner_output_payload(planner_payload)
    run["task_id"] = planner_payload["task_id"]
    run["phase"] = "generating"
    run["next_action"] = "run_generator"
    run["attempts"]["planner"] = attempt
    save_run(root, run)
    return output_path


def run_generator(repo_root: Path | str, run_id: str, *, driver: str) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] != "generating":
        raise RuntimeError(f"run_generator requires phase generating; current phase is {run['phase']}")
    run_dir = run_dir_for(root, run_id)
    planner_output = read_json_file(run_dir / "planner-output.json")
    validate_planner_output_payload(planner_output)
    output_path = run_dir / "generator-result.json"
    attempt = int(run["attempts"]["generator"]) + 1

    if driver == "fake":
        payload = {
            "task_id": planner_output["task_id"],
            "status": "implemented",
            "changed_paths": [],
            "commit": "",
            "verify_commands": planner_output["verify_commands"],
            "verify_results": [],
            "artifacts": [],
            "cleanup_required": False,
            "notes": "fake generator completed",
        }
        validate_generator_result_payload(payload)
        write_json_file(output_path, payload)
    elif driver == "codex-exec":
        prompt_path = run_dir / "generator-prompt.md"
        prompt_path.write_text(_generator_prompt(run_id), encoding="utf-8")
        output_path.unlink(missing_ok=True)
        attempt_payload = run_codex_prompt(
            role="generator",
            run_id=run_id,
            repo_root=root,
            run_dir=run_dir,
            prompt_path=prompt_path,
            output_json_path=output_path,
            attempt=attempt,
            timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
        )
        run["attempts"]["generator"] = attempt
        save_run(root, run)
        if not isinstance(attempt_payload, dict) or attempt_payload.get("status") != "pass":
            status = attempt_payload.get("status") if isinstance(attempt_payload, dict) else type(attempt_payload).__name__
            raise RuntimeError(f"generator codex-exec attempt failed with status {status}")
        validate_generator_result_payload(read_json_file(output_path))
    else:
        raise ValueError(f"unsupported generator driver: {driver}")

    run["phase"] = "evaluating"
    run["next_action"] = "run_evaluator"
    run["attempts"]["generator"] = attempt
    save_run(root, run)
    return output_path


def _latest_fake_evaluator_result(repo_root: Path | str, task_id: str) -> Path | None:
    task_root = Path(repo_root) / ".codex" / "evaluations" / "tasks" / task_id
    result_paths = list(task_root.glob("fake-attempt-*/result.json"))
    if not result_paths:
        return None

    def attempt_number(path: Path) -> int:
        try:
            return int(path.parent.name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            return -1

    return max(result_paths, key=lambda path: (attempt_number(path), path.stat().st_mtime_ns))


def _generator_result_has_artifacts(run_dir: Path) -> bool:
    generator_result = read_json_file(run_dir / "generator-result.json")
    validate_generator_result_payload(generator_result)
    return bool(generator_result["artifacts"])


def _scenario_command_results_have_logs(run_dir: Path) -> bool:
    scenario_results_path = run_dir / "scenario-command-results.json"
    if not scenario_results_path.exists():
        return False
    scenario_results = read_json_file(scenario_results_path)
    for result in scenario_results.get("results", []):
        if not isinstance(result, dict):
            continue
        for key in ("stdout_path", "stderr_path"):
            path_value = result.get(key)
            if isinstance(path_value, str) and path_value:
                return True
    return False


def _apply_evaluator_result_to_run(
    run: dict[str, Any],
    evaluator_payload: dict[str, Any],
    *,
    has_artifacts: bool = False,
) -> None:
    passed = evaluator_payload["returncode"] == 0 and evaluator_payload["status"] == "pass"
    if has_artifacts:
        run["phase"] = "artifact_hygiene"
    elif passed:
        run["phase"] = "passed_waiting_human_merge"
    else:
        run["phase"] = "repair_needed"
    run["last_result"] = (
        "pass"
        if passed
        else "blocked"
        if evaluator_payload.get("status") == "blocked"
        else "fail"
    )
    if has_artifacts:
        run["next_action"] = "run_artifact_hygiene"
    elif passed:
        run["next_action"] = "await_human_merge_confirmation"
    else:
        run["next_action"] = "repair_from_evaluator_findings"
    if has_artifacts:
        run["_post_hygiene_phase"] = (
            "passed_waiting_human_merge" if passed else "repair_needed"
        )
    else:
        run.pop("_post_hygiene_phase", None)


def run_evaluator(
    repo_root: Path | str,
    run_id: str,
    *,
    driver: str,
    max_attempts: int,
) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] != "evaluating":
        raise RuntimeError(f"run_evaluator requires phase evaluating; current phase is {run['phase']}")
    task_id = str(run["task_id"]).strip()
    if not task_id:
        raise RuntimeError("run_evaluator requires a non-empty task_id")

    run_dir = run_dir_for(root, run_id)
    output_path = run_dir / "evaluator-result.json"
    checkout_root = Path(__file__).resolve().parents[1]
    task_contract_path = run_dir / "task-contract.json"
    scenario_command_results_path = ""
    if task_contract_path.exists():
        task_contract = read_json_file(task_contract_path)
        validate_task_contract_payload(task_contract)
        scenario_commands = list(task_contract["scenario_commands"])
        if scenario_commands:
            scenario_command_results_path = str(
                run_scenario_commands(
                    repo_root=root,
                    run_dir=run_dir,
                    commands=scenario_commands,
                    timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
                )
            )
            scenario_manifest = read_json_file(Path(scenario_command_results_path))
            if scenario_manifest.get("status") != "pass":
                evaluator_payload = {
                    "status": "fail",
                    "task_id": task_id,
                    "driver": driver,
                    "returncode": 1,
                    "stdout": f"scenario commands failed: {scenario_command_results_path}\n",
                    "stderr": "",
                    "scenario_command_results_path": scenario_command_results_path,
                }
                validate_evaluator_result_payload(evaluator_payload)
                write_json_file(output_path, evaluator_payload)
                _apply_evaluator_result_to_run(
                    run,
                    evaluator_payload,
                    has_artifacts=_scenario_command_results_have_logs(run_dir),
                )
                run["attempts"]["evaluator"] = int(run["attempts"]["evaluator"]) + 1
                save_run(root, run)
                return output_path

    if driver == "fake":
        command = [
            "python3",
            "scripts/harness_evaluator_orchestrator.py",
            "run-task-loop",
            "--driver",
            "fake",
            "--task-id",
            task_id,
            "--max-attempts",
            str(max_attempts),
            "--repo-root",
            str(root),
        ]
        if task_contract_path.exists():
            command.extend(["--task-contract", str(task_contract_path)])
    elif driver == "codex-exec":
        command = [
            "python3",
            "scripts/harness_evaluator_orchestrator.py",
            "run-task-auto-gate",
            "--driver",
            "codex-exec",
            "--task-id",
            task_id,
            "--max-attempts",
            str(max_attempts),
            "--repo-root",
            str(root),
        ]
        if task_contract_path.exists():
            command.extend(["--task-contract", str(task_contract_path)])
    else:
        raise ValueError(f"unsupported evaluator driver: {driver}")

    result = subprocess.run(
        command,
        cwd=checkout_root,
        check=False,
        capture_output=True,
        text=True,
    )
    evaluator_status = "pass" if result.returncode == 0 else "fail"
    if driver == "fake":
        latest_result = _latest_fake_evaluator_result(root, task_id)
        if latest_result:
            raw_result = read_json_file(latest_result)
            if raw_result.get("status") == "blocked":
                evaluator_status = "blocked"
    evaluator_payload = {
        "status": evaluator_status,
        "task_id": task_id,
        "driver": driver,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "scenario_command_results_path": scenario_command_results_path,
    }
    validate_evaluator_result_payload(evaluator_payload)
    write_json_file(output_path, evaluator_payload)

    _apply_evaluator_result_to_run(
        run,
        evaluator_payload,
        has_artifacts=(
            (evaluator_status == "pass" and result.returncode == 0 and _generator_result_has_artifacts(run_dir))
            or _scenario_command_results_have_logs(run_dir)
        ),
    )
    run["attempts"]["evaluator"] = int(run["attempts"]["evaluator"]) + 1
    save_run(root, run)
    return output_path


def run_artifact_hygiene_step(
    repo_root: Path | str,
    run_id: str,
    *,
    max_file_bytes: int = 5 * 1024 * 1024,
    max_total_bytes: int = 50 * 1024 * 1024,
) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] != "artifact_hygiene":
        raise RuntimeError(f"run_artifact_hygiene_step requires phase artifact_hygiene; current phase is {run['phase']}")

    run_dir = run_dir_for(root, run_id)
    generator_result = read_json_file(run_dir / "generator-result.json")
    validate_generator_result_payload(generator_result)
    artifact_paths = list(generator_result["artifacts"])
    scenario_results_path = run_dir / "scenario-command-results.json"
    if scenario_results_path.exists():
        scenario_results = read_json_file(scenario_results_path)
        for result in scenario_results.get("results", []):
            if not isinstance(result, dict):
                continue
            for key in ("stdout_path", "stderr_path"):
                path_value = result.get(key)
                if not isinstance(path_value, str):
                    continue
                try:
                    artifact_paths.append(Path(path_value).resolve().relative_to(root.resolve()).as_posix())
                except (OSError, RuntimeError, ValueError):
                    artifact_paths.append(path_value)
    result_path = run_artifact_hygiene(
        repo_root=root,
        run_dir=run_dir,
        artifact_paths=artifact_paths,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
    )
    hygiene_result = read_json_file(result_path)
    validate_artifact_hygiene_result_payload(hygiene_result)

    run["attempts"]["artifact_hygiene"] = int(run["attempts"]["artifact_hygiene"]) + 1
    if hygiene_result["status"] == "blocked":
        run["phase"] = "stopped_blocked"
        run["last_result"] = "blocked"
        run["next_action"] = "inspect_artifact_hygiene"
    elif run.get("_post_hygiene_phase") == "repair_needed":
        run["phase"] = "repair_needed"
        run["next_action"] = "repair_from_evaluator_findings"
    else:
        run["phase"] = "cleanup"
        run["next_action"] = "run_cleanup"
    run.pop("_post_hygiene_phase", None)
    save_run(root, run)
    return result_path


def run_cleanup(repo_root: Path | str, run_id: str) -> Path:
    root = Path(repo_root).resolve()
    run = load_run(root, run_id)
    if run["phase"] != "cleanup":
        raise RuntimeError(f"run_cleanup requires phase cleanup; current phase is {run['phase']}")

    allowed_worktrees_root_path = root / ".worktrees"
    removed: list[str] = []
    if allowed_worktrees_root_path.is_symlink() or not allowed_worktrees_root_path.is_dir():
        run["attempts"]["cleanup"] = int(run["attempts"]["cleanup"]) + 1
        run["phase"] = "passed_waiting_human_merge"
        run["next_action"] = "await_human_merge_confirmation"
        save_run(root, run)
        return write_json_file(
            run_dir_for(root, run_id) / "cleanup-result.json",
            {"status": "pass", "worktrees_removed": removed},
        )

    allowed_worktrees_root = allowed_worktrees_root_path.resolve()
    for path_value in list(run["cleanup"].get("retained_artifacts", [])):
        original_path_value = str(path_value)
        path = Path(path_value)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue
        if path.is_symlink():
            continue
        try:
            path.relative_to(allowed_worktrees_root_path)
            resolved_path = path.resolve()
            resolved_path.relative_to(allowed_worktrees_root)
        except (OSError, RuntimeError, ValueError):
            continue
        if resolved_path == allowed_worktrees_root:
            continue
        if resolved_path.is_dir() and not resolved_path.is_symlink():
            shutil.rmtree(resolved_path)
        else:
            resolved_path.unlink()
        removed.append(original_path_value)

    run["cleanup"]["worktrees_removed"].extend(removed)
    run["attempts"]["cleanup"] = int(run["attempts"]["cleanup"]) + 1
    run["phase"] = "passed_waiting_human_merge"
    run["next_action"] = "await_human_merge_confirmation"
    save_run(root, run)
    return write_json_file(run_dir_for(root, run_id) / "cleanup-result.json", {"status": "pass", "worktrees_removed": removed})


def run_loop(
    repo_root: Path | str,
    run_id: str,
    *,
    planner_driver: str,
    generator_driver: str,
    evaluator_driver: str,
    max_eval_attempts: int,
) -> dict[str, str]:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] == "preflight":
        raise RuntimeError("run_loop requires confirmed preflight; current phase is preflight")
    if run["phase"] == "planned":
        run_planner(root, run_id, driver=planner_driver)
        run = load_run(root, run_id)
    if run["phase"] == "generating":
        run_generator(root, run_id, driver=generator_driver)
        run = load_run(root, run_id)
    if run["phase"] == "evaluating":
        run_evaluator(
            root,
            run_id,
            driver=evaluator_driver,
            max_attempts=max_eval_attempts,
        )
        run = load_run(root, run_id)
    if run["phase"] == "artifact_hygiene":
        run_artifact_hygiene_step(root, run_id)
        run = load_run(root, run_id)
    if run["phase"] == "cleanup":
        run_cleanup(root, run_id)
        run = load_run(root, run_id)
    terminal_phases = {
        "passed_waiting_human_merge",
        "repair_needed",
        "committed",
        "stopped_no_action",
        "stopped_budget",
        "stopped_blocked",
    }
    if run["phase"] not in terminal_phases:
        raise RuntimeError(f"run_loop unsupported phase {run['phase']}")
    return status_for_run(root, run_id)


def _fake_parent_planner_payload(
    parent: dict[str, Any],
    decision: str = "next_child",
    max_children: int = 3,
) -> dict[str, Any]:
    aggregate = parent.get("aggregate_acceptance", {})
    passed = int(aggregate.get("passed", 0)) if isinstance(aggregate, dict) else 0
    base_payload: dict[str, Any] = {
        "task_id": parent.get("task_id", ""),
        "policy": "demand_development",
        "task_kind": "registered_task",
        "title": "Demand parent planner",
        "goal": parent.get("requirement", ""),
        "non_goals": [],
        "allowed_paths": [],
        "denylist_paths": [],
        "verify_commands": [],
        "evaluator_scenarios_path": "",
        "stop_conditions": ["passed_waiting_human_merge", "stopped_blocked", "stopped_budget"],
        "backlog": list(parent.get("backlog", [])),
        "next_planning_hint": "",
    }
    if decision in {"blocked", "failed"}:
        return {
            **base_payload,
            "planner_decision": decision,
            "next_child_task": {},
            "blocked_reason": f"fake planner {decision}",
            "done_criteria": [],
            "reader_summary": {
                "purpose": parent.get("requirement", ""),
                "current_progress": "Blocked",
                "next_step": "User decision required",
                "decision_needed": "Yes",
            },
            "decision_required": True,
        }
    if decision == "parent_done" or passed >= max_children:
        return {
            **base_payload,
            "planner_decision": "parent_done",
            "next_child_task": {},
            "blocked_reason": "",
            "done_criteria": ["all fake children passed"],
            "reader_summary": {
                "purpose": parent.get("requirement", ""),
                "current_progress": f"{passed} children passed",
                "next_step": "Await human merge",
                "decision_needed": "No",
            },
            "decision_required": False,
        }

    next_index = passed + 1
    return {
        **base_payload,
        "planner_decision": "next_child",
        "next_child_task": {
            "child_id": f"child-{next_index:03d}",
            "title": f"Fake child {next_index}",
            "description": f"Implement fake child {next_index}",
            "allowed_paths": [f"generated/child-{next_index:03d}.txt"],
            "denylist_paths": [".env"],
            "verify_commands": [],
            "scenario_commands": [],
            "done_criteria": [f"child {next_index} passes fake evaluator"],
        },
        "blocked_reason": "",
        "done_criteria": [],
        "reader_summary": {
            "purpose": parent.get("requirement", ""),
            "current_progress": f"{passed} children passed",
            "next_step": "Run next child",
            "decision_needed": "No",
        },
        "decision_required": False,
    }


def _run_fake_demand_child(
    repo_root: Path,
    parent: dict[str, Any],
    child: dict[str, Any],
    *,
    generator_driver: str,
    max_eval_attempts: int,
) -> None:
    child_run_dir = run_dir_for(repo_root, child["run_id"])
    child_index = int(child["child_index"])
    generated_path = f"generated/child-{child_index:03d}.txt"
    target = repo_root / generated_path
    if generator_driver in {"fake-timeout", "fake-invalid-json", "fake-missing-artifact"}:
        reason = {
            "fake-timeout": "generator timeout",
            "fake-invalid-json": "generator invalid_json",
            "fake-missing-artifact": "generator missing artifact",
        }[generator_driver]
        parent = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
        _block_child(repo_root, child, reason, actor="generator")
        _block_parent(repo_root, parent, reason, actor="generator")
        return

    parent_for_dirty = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
    planned_paths = sorted(set([generated_path] + [str(path) for path in child.get("allowed_paths", [])]))
    baseline_overlap = _baseline_dirty_overlap(parent_for_dirty, planned_paths)
    if baseline_overlap:
        reason = f"baseline dirty path overlaps child allowed paths: {', '.join(baseline_overlap)}"
        _block_child(repo_root, child, reason)
        _block_parent(repo_root, parent_for_dirty, reason)
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"child {child_index}\n", encoding="utf-8")
    if generator_driver == "fake-dirty-path":
        (repo_root / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
    generator_payload = {
        "task_id": child["task_id"],
        "status": "implemented",
        "changed_paths": [generated_path],
        "commit": "",
        "verify_commands": [],
        "verify_results": [{"command": "fake", "status": "pass"}],
        "artifacts": [generated_path],
        "cleanup_required": False,
        "notes": "fake demand child generated",
    }
    validate_generator_result_payload(generator_payload)
    write_json_file(child_run_dir / "generator-result.json", generator_payload)
    child["attempts"]["generator"] = int(child["attempts"]["generator"]) + 1
    child["reader_summary"]["generator_action"] = f"Generated {generated_path}"
    append_loop_event(
        repo_root,
        run_id=child["run_id"],
        parent_run_id=parent["run_id"],
        child_id=f"child-{child_index:03d}",
        actor="generator",
        event_type="implement",
        summary=f"Generator wrote {generated_path}",
        artifact_paths=[generated_path],
    )

    parent_for_dirty = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
    unexpected_dirty = _dirty_paths_after_baseline(repo_root, parent_for_dirty, child)
    if unexpected_dirty:
        reason = f"unexpected dirty path: {', '.join(unexpected_dirty)}"
        _block_child(repo_root, child, reason)
        _block_parent(repo_root, parent_for_dirty, reason)
        return

    should_fail_once = (
        generator_driver == "fake-fail-child-2-once"
        and child_index == 2
        and int(child["attempts"]["evaluator"]) == 0
    )
    evaluator_payload = {
        "status": "fail" if should_fail_once else "pass",
        "task_id": child["task_id"],
        "driver": "fake",
        "returncode": 1 if should_fail_once else 0,
        "stdout": "fake evaluator fail\n" if should_fail_once else "fake evaluator pass\n",
        "stderr": "",
    }
    validate_evaluator_result_payload(evaluator_payload)
    write_json_file(child_run_dir / "evaluator-result.json", evaluator_payload)
    child["attempts"]["evaluator"] = int(child["attempts"]["evaluator"]) + 1

    if should_fail_once:
        child["phase"] = "repair_needed"
        child["last_result"] = "fail"
        child["next_action"] = "repair_child"
        child["reader_summary"]["evaluator_action"] = "Fake evaluator failed; repair required"
        child["reader_summary"]["acceptance_result"] = "Repair needed"
        save_run(repo_root, child)
        append_loop_event(
            repo_root,
            run_id=child["run_id"],
            parent_run_id=parent["run_id"],
            child_id=f"child-{child_index:03d}",
            actor="evaluator",
            event_type="evaluate",
            summary="Evaluator failed child; repair required",
        )
        if child["attempts"]["evaluator"] >= max_eval_attempts:
            parent = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
            parent["phase"] = "stopped_blocked"
            parent["last_result"] = "blocked"
            parent["next_action"] = "inspect_child_evaluator_attempts"
            parent["aggregate_acceptance"]["blocked"] = int(parent["aggregate_acceptance"]["blocked"]) + 1
            parent["aggregate_acceptance"]["pending"] = _aggregate_pending(parent["aggregate_acceptance"])
            parent["aggregate_acceptance"]["user_decision_required"] = True
            parent["reader_summary"]["current_progress"] = f"Child {child_index} evaluator failed"
            parent["reader_summary"]["next_step"] = "Inspect child evaluator attempts"
            parent["reader_summary"]["decision_needed"] = "Yes"
            save_run(repo_root, parent)
            append_loop_event(
                repo_root,
                run_id=parent["run_id"],
                actor="evaluator",
                event_type="blocked",
                summary=f"Evaluator failed child {child_index}; max attempts exhausted",
                child_id=f"child-{child_index:03d}",
                details={"child_run_id": child["run_id"], "max_eval_attempts": max_eval_attempts},
            )
            return
        append_loop_event(
            repo_root,
            run_id=child["run_id"],
            parent_run_id=parent["run_id"],
            child_id=f"child-{child_index:03d}",
            actor="generator",
            event_type="repair",
            summary="Generator repaired same child",
        )
        child["attempts"]["evaluator"] = int(child["attempts"]["evaluator"]) + 1
        evaluator_payload["status"] = "pass"
        evaluator_payload["returncode"] = 0
        evaluator_payload["stdout"] = "fake evaluator pass after repair\n"
        validate_evaluator_result_payload(evaluator_payload)
        write_json_file(child_run_dir / "evaluator-result.json", evaluator_payload)

    child["phase"] = "passed"
    child["last_result"] = "pass"
    child["next_action"] = "return_to_parent_planner"
    child["reader_summary"]["evaluator_action"] = "Fake evaluator passed"
    child["reader_summary"]["acceptance_result"] = "Passed"
    save_run(repo_root, child)
    append_loop_event(
        repo_root,
        run_id=child["run_id"],
        parent_run_id=parent["run_id"],
        child_id=f"child-{child_index:03d}",
        actor="evaluator",
        event_type="evaluate",
        summary="Evaluator passed child",
    )

    parent = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
    parent["accepted_changed_paths"] = sorted(set(parent["accepted_changed_paths"] + generator_payload["changed_paths"]))
    parent["aggregate_acceptance"]["passed"] = int(parent["aggregate_acceptance"]["passed"]) + 1
    parent["aggregate_acceptance"]["pending"] = _aggregate_pending(parent["aggregate_acceptance"])
    parent["current_child_run_id"] = child["run_id"]
    parent["phase"] = "planning"
    parent["next_action"] = "run_parent_planner"
    parent["reader_summary"]["current_progress"] = f"{parent['aggregate_acceptance']['passed']} children passed"
    parent["reader_summary"]["next_step"] = "Run parent planner"
    parent["reader_summary"]["decision_needed"] = "No"
    save_run(repo_root, parent)

    if generator_driver == "fake-stop-after-child-1" and child_index == 1:
        parent["phase"] = "child_running"
        parent["next_action"] = "resume_current_child"
        save_run(repo_root, parent)
        append_loop_event(
            repo_root,
            run_id=parent["run_id"],
            actor="orchestrator",
            event_type="decision",
            summary="resume checkpoint after child 1",
        )
        return


def run_demand_multi(
    repo_root: Path | str,
    run_id: str,
    *,
    planner_driver: str,
    generator_driver: str,
    evaluator_driver: str,
    max_eval_attempts: int,
    max_children: int,
) -> dict[str, str]:
    root = Path(repo_root)
    validate_run_id(run_id)
    run = load_run(root, run_id)
    if run.get("run_kind") == "child":
        raise RuntimeError("run_demand_multi requires a parent run_id")
    parent = _ensure_parent_fields(run)
    if parent["phase"] == "preflight":
        raise RuntimeError("run_demand_multi requires confirmed preflight")
    if parent["phase"] in {"stopped_blocked", "stopped_budget", "passed_waiting_human_merge"}:
        return status_for_run(root, run_id)
    if planner_driver not in {"fake", "fake-blocked", "fake-failed"}:
        raise ValueError("run_demand_multi initially supports fake planner drivers")
    if generator_driver not in {
        "fake",
        "fake-fail-child-2-once",
        "fake-dirty-path",
        "fake-timeout",
        "fake-invalid-json",
        "fake-missing-artifact",
        "fake-stop-after-child-1",
    }:
        raise ValueError("run_demand_multi initially supports fake generator drivers")
    if evaluator_driver != "fake":
        raise ValueError("run_demand_multi initially supports fake evaluator driver")

    while True:
        parent = _ensure_parent_fields(load_run(root, run_id))
        if parent["phase"] in {"stopped_blocked", "stopped_budget", "passed_waiting_human_merge"}:
            return status_for_run(root, run_id)
        reconcile_status = _reconcile_demand_parent_children(root, parent)
        if reconcile_status in {"waiting", "blocked"}:
            return status_for_run(root, run_id)
        parent = _ensure_parent_fields(load_run(root, run_id))
        if parent["phase"] in {"stopped_blocked", "stopped_budget", "passed_waiting_human_merge"}:
            return status_for_run(root, run_id)
        if parent["phase"] == "child_running" and parent.get("current_child_run_id"):
            current_child = load_run(root, str(parent["current_child_run_id"]))
            if current_child["phase"] != "passed":
                append_loop_event(
                    root,
                    run_id=run_id,
                    actor="orchestrator",
                    event_type="wait",
                    summary=f"Waiting for current child {current_child['run_id']} in phase {current_child['phase']}",
                    child_id=f"child-{int(current_child['child_index']):03d}",
                    details={"child_run_id": current_child["run_id"], "child_phase": current_child["phase"]},
                )
                return status_for_run(root, run_id)
            append_loop_event(
                root,
                run_id=run_id,
                actor="orchestrator",
                event_type="decision",
                summary=f"resume from passed child {current_child['run_id']}",
                child_id=f"child-{int(current_child['child_index']):03d}",
                details={"child_run_id": current_child["run_id"]},
            )
            parent, reconcile_status = _reconcile_passed_demand_children(root, parent)
            if reconcile_status == "blocked":
                return status_for_run(root, run_id)
            parent["phase"] = "planning"
            parent["next_action"] = "run_parent_planner"
            parent["reader_summary"]["current_progress"] = f"{parent['aggregate_acceptance']['passed']} children passed"
            parent["reader_summary"]["next_step"] = "Run parent planner"
            parent["reader_summary"]["decision_needed"] = "No"
            save_run(root, parent)
            continue
        if max_children < 1:
            parent["phase"] = "stopped_budget"
            parent["last_result"] = "blocked"
            parent["next_action"] = "inspect_budget_limits"
            parent["aggregate_acceptance"]["pending"] = _aggregate_pending(parent["aggregate_acceptance"])
            parent["aggregate_acceptance"]["user_decision_required"] = True
            parent["reader_summary"]["current_progress"] = "Budget exhausted"
            parent["reader_summary"]["next_step"] = "Inspect budget limits"
            parent["reader_summary"]["decision_needed"] = "Yes"
            save_run(root, parent)
            append_loop_event(
                root,
                run_id=run_id,
                actor="orchestrator",
                event_type="blocked",
                summary="max_children budget exhausted",
            )
            return status_for_run(root, run_id)

        passed = int(parent["aggregate_acceptance"]["passed"])
        if passed >= max_children:
            parent["phase"] = "passed_waiting_human_merge"
            parent["next_action"] = "await_human_merge_confirmation"
            parent["last_result"] = "pass"
            parent["aggregate_acceptance"]["total"] = max_children
            parent["aggregate_acceptance"]["pending"] = 0
            parent["reader_summary"]["current_progress"] = f"{passed} children passed"
            parent["reader_summary"]["next_step"] = "Await human merge"
            parent["reader_summary"]["decision_needed"] = "No"
            save_run(root, parent)
            append_loop_event(
                root,
                run_id=run_id,
                actor="orchestrator",
                event_type="decision",
                summary="All child tasks passed; awaiting human merge",
            )
            return status_for_run(root, run_id)

        decision = {"fake-blocked": "blocked", "fake-failed": "failed"}.get(planner_driver, "next_child")
        planner_payload = _fake_parent_planner_payload(parent, decision=decision, max_children=max_children)
        validate_planner_output_payload(planner_payload)
        write_json_file(run_dir_for(root, run_id) / "planner-output.json", planner_payload)
        parent["attempts"]["planner"] = int(parent["attempts"]["planner"]) + 1
        parent["reader_summary"] = planner_payload["reader_summary"]

        if planner_payload["planner_decision"] in {"blocked", "failed"}:
            parent["phase"] = "stopped_blocked"
            parent["last_result"] = "blocked"
            parent["next_action"] = "inspect_parent_planner_blocked"
            parent["aggregate_acceptance"]["user_decision_required"] = True
            save_run(root, parent)
            append_loop_event(
                root,
                run_id=run_id,
                actor="planner",
                event_type="blocked",
                summary=planner_payload["blocked_reason"],
            )
            return status_for_run(root, run_id)

        if planner_payload["planner_decision"] == "parent_done":
            parent["phase"] = "passed_waiting_human_merge"
            parent["next_action"] = "await_human_merge_confirmation"
            parent["last_result"] = "pass"
            parent["aggregate_acceptance"]["total"] = max_children
            parent["aggregate_acceptance"]["pending"] = 0
            save_run(root, parent)
            append_loop_event(
                root,
                run_id=run_id,
                actor="planner",
                event_type="decision",
                summary="Parent planner marked demand run done",
            )
            return status_for_run(root, run_id)

        child_index = len(parent["child_run_ids"]) + 1
        child = _create_child_run(root, parent, child_index, planner_payload["next_child_task"])
        parent["child_run_ids"].append(child["run_id"])
        parent["current_child_run_id"] = child["run_id"]
        parent["phase"] = "child_running"
        parent["next_action"] = "run_child_generator"
        parent["aggregate_acceptance"]["total"] = max_children
        parent["aggregate_acceptance"]["pending"] = _aggregate_pending(parent["aggregate_acceptance"])
        save_run(root, parent)

        _run_fake_demand_child(
            root,
            parent,
            child,
            generator_driver=generator_driver,
            max_eval_attempts=max_eval_attempts,
        )
        parent_after_child = load_run(root, run_id)
        if parent_after_child["phase"] in {"stopped_blocked", "stopped_budget"}:
            return status_for_run(root, run_id)
        if parent_after_child["phase"] == "child_running":
            return status_for_run(root, run_id)


def _stop_run(
    repo_root: Path,
    run: dict[str, Any],
    *,
    phase: str,
    next_action: str,
    last_result: str,
) -> dict[str, Any]:
    run["phase"] = phase
    run["next_action"] = next_action
    run["last_result"] = last_result
    save_run(repo_root, run)
    return status_for_run(repo_root, run["run_id"])


def _autonomous_task_id(run_id: str, task_number: int) -> str:
    return f"{run_id}-task-{task_number}"


def _coverage_map_result_path(repo_root: Path, run_id: str) -> Path:
    return run_dir_for(repo_root, run_id) / "coverage-map-result.json"


def _load_ai_infra_coverage_map(
    repo_root: Path,
    run: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if run["domain"] != "ai_infra":
        return None, None
    coverage_path = repo_root / "personal-wiki" / "domains" / run["domain"] / "coverage-map.json"
    if not coverage_path.exists():
        result = {
            "status": "blocked",
            "domain": run["domain"],
            "coverage_map_path": str(coverage_path.relative_to(repo_root)),
            "error": "coverage-map.json is missing",
        }
        write_json_file(_coverage_map_result_path(repo_root, run["run_id"]), result)
        return None, result
    try:
        payload = load_or_create_coverage_map(repo_root, run["domain"], run["requirement"])
    except ValueError as exc:
        result = {
            "status": "blocked",
            "domain": run["domain"],
            "coverage_map_path": str(coverage_path.relative_to(repo_root)),
            "error": str(exc),
        }
        write_json_file(_coverage_map_result_path(repo_root, run["run_id"]), result)
        return None, result
    try:
        validate_ai_infra_coverage_map_semantics(payload, expected_domain=run["domain"])
    except ValueError as exc:
        result = {
            "status": "blocked",
            "domain": run["domain"],
            "coverage_map_path": str(coverage_path.relative_to(repo_root)),
            "error": str(exc),
        }
        write_json_file(_coverage_map_result_path(repo_root, run["run_id"]), result)
        return None, result
    return payload, None


def _stop_for_ai_infra_coverage_map(
    repo_root: Path,
    run: dict[str, Any],
    result: dict[str, Any],
) -> bool:
    run["phase"] = "stopped_blocked"
    run["next_action"] = "inspect_ai_infra_coverage_map"
    run["last_result"] = "blocked"
    save_run(repo_root, run)
    append_loop_event(
        repo_root,
        run_id=run["run_id"],
        actor="orchestrator",
        event_type="blocked",
        summary=f"AI infra coverage map blocked autonomous no-action: {result.get('error', 'invalid coverage map')}",
        details=result,
        artifact_paths=[str(_coverage_map_result_path(repo_root, run["run_id"]).relative_to(repo_root))],
    )
    return True


def _run_fake_autonomous_planner(
    repo_root: Path,
    run: dict[str, Any],
    *,
    task_number: int,
) -> bool:
    run_dir = run_dir_for(repo_root, run["run_id"])
    domain = run["domain"]
    state = load_or_create_loop_state(repo_root, domain, run["requirement"])
    coverage_map, coverage_result = _load_ai_infra_coverage_map(repo_root, run)
    run["attempts"]["planner"] = int(run["attempts"]["planner"]) + 1
    if coverage_result is not None:
        save_run(repo_root, run)
        _stop_for_ai_infra_coverage_map(repo_root, run, coverage_result)
        return False
    decision = decide_no_action(state, coverage_map=coverage_map)

    if decision.no_action:
        state["last_planner_decision"] = "no_action"
        write_loop_state(repo_root, domain, state)
        run["phase"] = "stopped_no_action"
        run["next_action"] = "none"
        run["last_result"] = "pass"
        save_run(repo_root, run)
        return False

    task_id = _autonomous_task_id(run["run_id"], task_number)
    allowed_patterns, denied_patterns, _manual_patterns = policy_patterns_for_run(run, domain=domain)
    planner_payload = {
        "task_id": task_id,
        "policy": "autonomous_knowledge",
        "task_kind": "autonomous_implementation_task",
        "title": f"Autonomous knowledge task {task_number}",
        "goal": run["requirement"],
        "non_goals": [],
        "allowed_paths": allowed_patterns,
        "denylist_paths": denied_patterns,
        "verify_commands": [],
        "evaluator_scenarios_path": "",
        "stop_conditions": list(run.get("stop_conditions", ["stopped_no_action", "stopped_budget", "stopped_blocked"])),
        "next_planning_hint": "return to planning after commit",
    }
    validate_planner_output_payload(planner_payload)
    write_json_file(run_dir / "planner-output.json", planner_payload)
    state["last_planner_decision"] = "planned"
    write_loop_state(repo_root, domain, state)
    run["task_id"] = task_id
    run["phase"] = "generating"
    run["next_action"] = "run_autonomous_generator"
    save_run(repo_root, run)
    return True


def _stop_if_autonomous_no_action(repo_root: Path, run: dict[str, Any]) -> bool:
    domain = run["domain"]
    state = load_or_create_loop_state(repo_root, domain, run["requirement"])
    coverage_map, coverage_result = _load_ai_infra_coverage_map(repo_root, run)
    if coverage_result is not None:
        return _stop_for_ai_infra_coverage_map(repo_root, run, coverage_result)
    decision = decide_no_action(state, coverage_map=coverage_map)
    if not decision.no_action:
        return False
    state["last_planner_decision"] = "no_action"
    write_loop_state(repo_root, domain, state)
    run["attempts"]["planner"] = int(run["attempts"]["planner"]) + 1
    run["phase"] = "stopped_no_action"
    run["next_action"] = "none"
    run["last_result"] = "pass"
    save_run(repo_root, run)
    return True


def _run_codex_autonomous_planner(
    repo_root: Path,
    run: dict[str, Any],
) -> bool:
    run_dir = run_dir_for(repo_root, run["run_id"])
    output_path = run_dir / "planner-output.json"
    prompt_path = run_dir / "planner-prompt.md"
    prompt_path.write_text(_autonomous_planner_prompt(run, run_dir), encoding="utf-8")
    attempt = int(run["attempts"]["planner"]) + 1
    output_path.unlink(missing_ok=True)
    attempt_payload = run_codex_prompt(
        role="planner",
        run_id=run["run_id"],
        repo_root=repo_root,
        run_dir=run_dir,
        prompt_path=prompt_path,
        output_json_path=output_path,
        attempt=attempt,
        timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
    )
    run["attempts"]["planner"] = attempt
    save_run(repo_root, run)
    if not isinstance(attempt_payload, dict) or attempt_payload.get("status") != "pass":
        return False

    planner_payload = read_json_file(output_path)
    validate_planner_output_payload(planner_payload)
    run = load_run(repo_root, run["run_id"])
    run["task_id"] = planner_payload["task_id"]
    run["phase"] = "generating"
    run["next_action"] = "run_autonomous_generator"
    save_run(repo_root, run)
    return True


def _write_fake_autonomous_generator_result(
    repo_root: Path,
    run: dict[str, Any],
    *,
    driver: str,
    task_number: int,
) -> dict[str, Any]:
    run_dir = run_dir_for(repo_root, run["run_id"])
    domain = run["domain"]
    state = load_or_create_loop_state(repo_root, domain, run["requirement"])
    changed_paths: list[str] = []
    artifacts: list[str] = []
    verify_results: list[str] = []
    notes = "fake autonomous generator completed"

    if driver == "fake":
        raw_relative = f"personal-wiki/domains/{domain}/raw/loop-autonomous/{run['run_id']}-task-{task_number}.md"
        raw_path = repo_root / raw_relative
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(
            "\n".join(
                [
                    f"# Autonomous Raw Note {task_number}",
                    "",
                    f"- Run ID: {run['run_id']}",
                    f"- Domain: {domain}",
                    "- Source: fake autonomous generator",
                    "",
                    "Synthetic allowlisted evidence for the autonomous knowledge loop.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        state["candidate_backlog"] = []
        state["coverage_gaps"] = []
        state["known_sources"] = [
            *list(state.get("known_sources", [])),
            {
                "id": f"{run['run_id']}-task-{task_number}",
                "title": f"Autonomous raw note {task_number}",
                "source": "fake-generator",
                "status": "captured",
                "updated_at": _timestamp(),
                "evidence": [raw_relative],
            },
        ]
        state["no_action_evidence"] = [
            {
                "id": f"{run['run_id']}-scan-{task_number}",
                "title": "Autonomous scan completed",
                "source": "coverage-map",
                "status": "complete",
                "updated_at": _timestamp(),
                "evidence": ["coverage-map scan confirmed no remaining candidates"],
            }
        ]
        state["last_scan_at"] = _timestamp()
        state["last_planner_decision"] = "planned"
        write_loop_state(repo_root, domain, state)
        changed_paths = [raw_relative, f"personal-wiki/domains/{domain}/loop-state.json"]
        if domain == "ai_infra":
            coverage_map = create_default_coverage_map(domain, run["requirement"])
            coverage_map["domain_goal"] = state["domain_goal"]
            for layer_name, layer_payload in coverage_map["layers"].items():
                layer_payload["status"] = "covered"
                layer_payload["covered_pages"] = [f"wiki/{layer_name}.md"]
                layer_payload["raw_evidence"] = [raw_relative]
                layer_payload["candidate_gaps"] = []
                layer_payload["blocked_reason"] = ""
                layer_payload["last_scanned_at"] = state["last_scan_at"]
                layer_payload["notes"] = "Synthetic fake-generator coverage for autonomous smoke."
            write_coverage_map(repo_root, domain, coverage_map)
            changed_paths.append(f"personal-wiki/domains/{domain}/coverage-map.json")
        artifacts = [raw_relative]
    elif driver == "fake-denylist":
        denied_relative = ".env"
        (repo_root / denied_relative).write_text("FAKE_SECRET=redacted\n", encoding="utf-8")
        changed_paths = [denied_relative]
        notes = "fake autonomous generator wrote denylist path"
    elif driver == "fake-dependency":
        dependency_relative = "requirements.txt"
        (repo_root / dependency_relative).write_text("example-package==0.0.1\n", encoding="utf-8")
        changed_paths = [dependency_relative]
        notes = ""
    else:
        raise ValueError(f"unsupported autonomous generator driver: {driver}")

    payload = {
        "task_id": run["task_id"],
        "status": "implemented",
        "changed_paths": changed_paths,
        "commit": "",
        "verify_commands": [],
        "verify_results": verify_results,
        "artifacts": artifacts,
        "cleanup_required": False,
        "notes": notes,
    }
    validate_generator_result_payload(payload)
    write_json_file(run_dir / "generator-result.json", payload)
    run["attempts"]["generator"] = int(run["attempts"]["generator"]) + 1
    run["phase"] = "evaluating"
    run["next_action"] = "run_autonomous_evaluator"
    save_run(repo_root, run)
    return payload


def _run_codex_autonomous_generator(
    repo_root: Path,
    run: dict[str, Any],
) -> dict[str, Any] | None:
    run_dir = run_dir_for(repo_root, run["run_id"])
    output_path = run_dir / "generator-result.json"
    prompt_path = run_dir / "generator-prompt.md"
    prompt_path.write_text(_autonomous_generator_prompt(run, run_dir), encoding="utf-8")
    attempt = int(run["attempts"]["generator"]) + 1
    output_path.unlink(missing_ok=True)
    attempt_payload = run_codex_prompt(
        role="generator",
        run_id=run["run_id"],
        repo_root=repo_root,
        run_dir=run_dir,
        prompt_path=prompt_path,
        output_json_path=output_path,
        attempt=attempt,
        timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
    )
    run["attempts"]["generator"] = attempt
    _record_generator_attempt_for_task(run)
    save_run(repo_root, run)
    if not isinstance(attempt_payload, dict) or attempt_payload.get("status") != "pass":
        return None

    generator_payload = read_json_file(output_path)
    validate_generator_result_payload(generator_payload)
    run = load_run(repo_root, run["run_id"])
    run["phase"] = "evaluating"
    run["next_action"] = "run_autonomous_evaluator"
    save_run(repo_root, run)
    return generator_payload


def _generator_attempts_for_task(repo_root: Path, run: dict[str, Any]) -> int:
    del repo_root
    task_id = str(run.get("task_id", ""))
    attempts_by_task = run.get("_autonomous_generator_attempts_by_task", {})
    if not isinstance(attempts_by_task, dict):
        return 0
    value = attempts_by_task.get(task_id, 0)
    return int(value) if isinstance(value, int) else 0


def _record_generator_attempt_for_task(run: dict[str, Any]) -> None:
    task_id = str(run.get("task_id", ""))
    attempts_by_task = run.get("_autonomous_generator_attempts_by_task")
    if not isinstance(attempts_by_task, dict):
        attempts_by_task = {}
    attempts_by_task[task_id] = int(attempts_by_task.get(task_id, 0)) + 1
    run["_autonomous_generator_attempts_by_task"] = attempts_by_task


def _run_fake_autonomous_evaluator(
    repo_root: Path,
    run: dict[str, Any],
    *,
    max_attempts: int,
) -> dict[str, Any]:
    run_dir = run_dir_for(repo_root, run["run_id"])
    output_path = run_dir / "evaluator-result.json"
    task_contract_path = run_dir / "task-contract.json"
    scenario_path = repo_root / "docs" / "harness" / "evaluator-scenarios" / f"{run['task_id']}.json"
    if task_contract_path.exists() or scenario_path.exists():
        run_evaluator(repo_root, run["run_id"], driver="fake", max_attempts=max_attempts)
        return read_json_file(output_path)

    payload = {
        "status": "pass",
        "task_id": run["task_id"],
        "driver": "fake",
        "returncode": 0,
        "stdout": "fake autonomous smoke pass\n",
        "stderr": "",
    }
    validate_evaluator_result_payload(payload)
    write_json_file(output_path, payload)
    run["attempts"]["evaluator"] = int(run["attempts"]["evaluator"]) + 1
    run["phase"] = "artifact_hygiene"
    run["next_action"] = "run_artifact_hygiene"
    run["last_result"] = "pass"
    save_run(repo_root, run)
    return payload


def _run_codex_autonomous_evaluator(
    repo_root: Path,
    run: dict[str, Any],
) -> dict[str, Any] | None:
    run_dir = run_dir_for(repo_root, run["run_id"])
    output_path = run_dir / "evaluator-result.json"
    prompt_path = run_dir / "evaluator-prompt.md"
    prompt_path.write_text(_autonomous_evaluator_prompt(run, run_dir), encoding="utf-8")
    attempt = int(run["attempts"]["evaluator"]) + 1
    output_path.unlink(missing_ok=True)
    attempt_payload = run_codex_prompt(
        role="evaluator",
        run_id=run["run_id"],
        repo_root=repo_root,
        run_dir=run_dir,
        prompt_path=prompt_path,
        output_json_path=output_path,
        attempt=attempt,
        timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
    )
    run["attempts"]["evaluator"] = attempt
    save_run(repo_root, run)
    if not isinstance(attempt_payload, dict) or attempt_payload.get("status") != "pass":
        return None

    evaluator_payload = read_json_file(output_path)
    validate_evaluator_result_payload(evaluator_payload)
    run = load_run(repo_root, run["run_id"])
    run["phase"] = "artifact_hygiene"
    run["next_action"] = "run_artifact_hygiene"
    run["last_result"] = (
        "pass"
        if evaluator_payload["status"] == "pass" and evaluator_payload["returncode"] == 0
        else "blocked"
        if evaluator_payload["status"] == "blocked"
        else "fail"
    )
    save_run(repo_root, run)
    return evaluator_payload


def _run_wiki_validate(repo_root: Path, domain: str, run_dir: Path) -> bool:
    cli_path = repo_root / "personal-wiki" / "tools" / "wiki_cli" / "cli.py"
    result_path = run_dir / "wiki-validate-result.json"
    if not cli_path.exists():
        write_json_file(
            result_path,
            {
                "status": "skipped",
                "reason": "personal-wiki CLI not present",
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            },
        )
        return True
    result = subprocess.run(
        ["python3", "personal-wiki/tools/wiki_cli/cli.py", "--root", "personal-wiki", "validate", "--domain", domain],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    write_json_file(
        result_path,
        {
            "status": "pass" if result.returncode == 0 else "fail",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )
    return result.returncode == 0


def _commit_autonomous_changes(
    repo_root: Path,
    run: dict[str, Any],
    generator_result: dict[str, Any],
) -> bool:
    run_dir = run_dir_for(repo_root, run["run_id"])
    changed_paths = list(generator_result["changed_paths"])
    dirty_result = _check_autonomous_dirty_paths(repo_root, run, changed_paths)
    write_json_file(run_dir / "dirty-paths-result.json", dirty_result)
    if not dirty_result["allowed"]:
        _stop_run(repo_root, run, phase="stopped_blocked", next_action="inspect_autonomous_dirty_paths", last_result="blocked")
        return False

    dependency_allowed_paths = [
        "requirements.txt",
        "requirements-*.txt",
        "package.json",
        "package-lock.json",
        "package*.json",
    ]
    allowed_patterns, denied_patterns, manual_patterns = policy_patterns_for_run(run, domain=run["domain"])
    scope = check_autonomous_scope(
        changed_paths,
        allowed_patterns + dependency_allowed_paths,
        denied_patterns,
        manual_patterns,
    )
    write_json_file(
        run_dir / "autonomous-scope-result.json",
        {
            "allowed": scope.allowed,
            "allowed_paths": scope.allowed_paths,
            "denied_paths": scope.denied_paths,
            "manual_confirm_paths": scope.manual_confirm_paths,
            "findings": scope.findings,
        },
    )
    if not scope.allowed:
        _stop_run(repo_root, run, phase="stopped_blocked", next_action="inspect_autonomous_scope", last_result="blocked")
        return False

    supply_chain = check_supply_chain(changed_paths, generator_result["notes"], generator_result["verify_results"])
    write_json_file(
        run_dir / "supply-chain-result.json",
        {
            "allowed": supply_chain.allowed,
            "dependency_paths": supply_chain.dependency_paths,
            "findings": supply_chain.findings,
        },
    )
    if not supply_chain.allowed:
        _stop_run(repo_root, run, phase="stopped_blocked", next_action="inspect_supply_chain", last_result="blocked")
        return False

    if not _run_wiki_validate(repo_root, run["domain"], run_dir):
        _stop_run(repo_root, run, phase="stopped_blocked", next_action="inspect_wiki_validate", last_result="blocked")
        return False

    if changed_paths and not generator_result["commit"]:
        try:
            commit_sha = run_git_commit(
                repo_root,
                changed_paths,
                f"chore(wiki): autonomous knowledge update {run['run_id']}",
            )
        except Exception as exc:
            write_json_file(
                run_dir / "commit-result.json",
                {
                    "status": "blocked",
                    "commit": "",
                    "error": str(exc),
                },
            )
            _stop_run(repo_root, run, phase="stopped_blocked", next_action="inspect_autonomous_commit", last_result="blocked")
            return False
        write_json_file(
            run_dir / "commit-result.json",
            {
                "status": "pass",
                "commit": commit_sha,
                "error": "",
            },
        )
        generator_result["commit"] = commit_sha
        write_json_file(run_dir / "generator-result.json", generator_result)

    return _finish_autonomous_cleanup(repo_root, run["run_id"])


def _finish_autonomous_cleanup(repo_root: Path, run_id: str) -> bool:
    run = load_run(repo_root, run_id)
    run["phase"] = "cleanup"
    run["next_action"] = "run_cleanup"
    save_run(repo_root, run)
    run_cleanup(repo_root, run_id)
    run = load_run(repo_root, run_id)
    run["phase"] = "planning"
    run["next_action"] = "run_autonomous_planner"
    run["last_result"] = "pass"
    save_run(repo_root, run)
    return True


def _check_autonomous_dirty_paths(
    repo_root: Path,
    run: dict[str, Any],
    declared_changed_paths: list[str],
) -> dict[str, Any]:
    actual_paths = _git_dirty_paths(repo_root)
    baseline_paths = _baseline_dirty_relative_paths(run)
    declared = set(declared_changed_paths)
    declared.add(f"personal-wiki/domains/{run['domain']}/loop-state.json")
    baseline_changed_paths = sorted(path for path in declared if path in baseline_paths)
    ignored_paths = [
        path
        for path in actual_paths
        if _is_autonomous_internal_dirty_path(path, str(run["run_id"]), str(run["task_id"]))
    ]
    unexpected_paths = sorted(
        path
        for path in actual_paths
        if path not in declared
        and path not in baseline_paths
        and path not in ignored_paths
    )
    return {
        "allowed": not unexpected_paths and not baseline_changed_paths,
        "actual_paths": actual_paths,
        "declared_paths": sorted(declared),
        "baseline_paths": sorted(baseline_paths),
        "baseline_changed_paths": baseline_changed_paths,
        "ignored_paths": sorted(ignored_paths),
        "unexpected_paths": unexpected_paths,
    }


def _git_dirty_paths(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    paths: list[str] = []
    for line in result.stdout.splitlines():
        parsed_paths = _parse_porcelain_paths(line)
        paths.extend(parsed_paths)
    return sorted(set(paths))


def _baseline_dirty_relative_paths(run: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for line in run.get("baseline_dirty_paths", []):
        if not isinstance(line, str):
            continue
        paths.update(_parse_porcelain_paths(line))
    return paths


def _parse_porcelain_paths(line: str) -> list[str]:
    if not line.strip() or len(line) < 4:
        return []
    path_value = line[3:].strip()
    if " -> " in path_value:
        old_path, new_path = path_value.split(" -> ", 1)
        return [old_path.strip(), new_path.strip()]
    return [path_value]


def _is_autonomous_internal_dirty_path(path: str, run_id: str, task_id: str) -> bool:
    return (
        path.startswith(f".codex/loop-runs/{run_id}/")
        or (bool(task_id) and path.startswith(f".codex/evaluations/tasks/{task_id}/"))
    )


def run_autonomous(
    repo_root: Path | str,
    run_id: str,
    planner_driver: str,
    generator_driver: str,
    evaluator_driver: str,
    max_eval_attempts: int,
    max_tasks: int,
) -> dict[str, str]:
    root = Path(repo_root)
    validate_run_id(run_id)
    if planner_driver not in {"fake", "codex-exec"}:
        raise ValueError(f"unsupported autonomous planner driver: {planner_driver}")
    if generator_driver not in {"fake", "fake-denylist", "fake-dependency", "codex-exec"}:
        raise ValueError(f"unsupported autonomous generator driver: {generator_driver}")
    if evaluator_driver not in {"fake", "codex-exec"}:
        raise ValueError(f"unsupported autonomous evaluator driver: {evaluator_driver}")

    tasks_completed = 0
    while True:
        run = load_run(root, run_id)
        if run["policy"] != "autonomous_knowledge":
            raise RuntimeError(f"run_autonomous requires autonomous_knowledge policy; current policy is {run['policy']}")
        if run["phase"] == "preflight":
            raise RuntimeError("run_autonomous requires confirmed preflight; current phase is preflight")
        if run["phase"] in {"stopped_no_action", "stopped_budget", "stopped_blocked"}:
            return status_for_run(root, run_id)
        if run["phase"] == "planning" and tasks_completed >= max_tasks:
            return _stop_run(root, run, phase="stopped_budget", next_action="none", last_result="pass")
        if run["phase"] not in {"planning", "generating", "evaluating", "artifact_hygiene", "cleanup"}:
            raise RuntimeError(f"run_autonomous unsupported phase {run['phase']}")

        if run["phase"] == "planning":
            task_number = int(run["attempts"]["generator"]) + 1
            if planner_driver != "fake" and _stop_if_autonomous_no_action(root, run):
                return status_for_run(root, run_id)
            if planner_driver == "fake":
                planned = _run_fake_autonomous_planner(root, run, task_number=task_number)
            else:
                planned = _run_codex_autonomous_planner(root, run)
            if not planned:
                current = load_run(root, run_id)
                if current["phase"] in {"stopped_no_action", "stopped_blocked"}:
                    return status_for_run(root, run_id)
                return _stop_run(root, current, phase="stopped_blocked", next_action="inspect_autonomous_planner", last_result="blocked")
            continue

        run = load_run(root, run_id)
        if run["phase"] == "generating":
            if _generator_attempts_for_task(root, run) >= int(run["limits"]["max_generator_attempts_per_task"]):
                return _stop_run(root, run, phase="stopped_blocked", next_action="inspect_autonomous_generator", last_result="blocked")
            if generator_driver == "codex-exec":
                generator_result = _run_codex_autonomous_generator(root, run)
                if generator_result is None:
                    continue
            else:
                task_number = int(run["attempts"]["generator"]) + 1
                _write_fake_autonomous_generator_result(
                    root,
                    run,
                    driver=generator_driver,
                    task_number=task_number,
                )
            continue

        run = load_run(root, run_id)
        if run["phase"] == "evaluating":
            if evaluator_driver == "fake":
                evaluator_result = _run_fake_autonomous_evaluator(root, run, max_attempts=max_eval_attempts)
            else:
                evaluator_result = _run_codex_autonomous_evaluator(root, run)
                if evaluator_result is None:
                    return _stop_run(root, load_run(root, run_id), phase="stopped_blocked", next_action="inspect_autonomous_evaluator", last_result="blocked")
            if evaluator_result["status"] != "pass" or evaluator_result["returncode"] != 0:
                return _stop_run(root, load_run(root, run_id), phase="stopped_blocked", next_action="inspect_evaluator", last_result="blocked")
            continue

        run = load_run(root, run_id)
        if run["phase"] == "artifact_hygiene":
            run_artifact_hygiene_step(root, run_id)
            run = load_run(root, run_id)
            if run["phase"] == "stopped_blocked":
                return status_for_run(root, run_id)
            continue

        run = load_run(root, run_id)
        if run["phase"] == "cleanup":
            generator_result = read_json_file(run_dir_for(root, run_id) / "generator-result.json")
            validate_generator_result_payload(generator_result)
            if not generator_result["commit"]:
                if not _commit_autonomous_changes(root, run, generator_result):
                    return status_for_run(root, run_id)
            else:
                if not _finish_autonomous_cleanup(root, run_id):
                    return status_for_run(root, run_id)
            tasks_completed += 1


def status_for_run(repo_root: Path | str, run_id: str) -> dict[str, str]:
    payload = load_run(repo_root, run_id)
    return {
        "run_id": payload["run_id"],
        "policy": payload["policy"],
        "phase": payload["phase"],
        "next_action": payload["next_action"],
        "task_id": payload["task_id"],
    }


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage harness planner loop run state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Create a preflight run.")
    preflight.add_argument("--repo-root", default=".")
    preflight.add_argument("--mode", required=True)
    preflight.add_argument("--requirement", required=True)
    preflight.add_argument("--run-id", required=True)
    preflight.add_argument("--task-id", default="")
    preflight.add_argument("--domain", default="")
    preflight.add_argument("--policy-file", default="")
    preflight.add_argument("--constraint", action="append", default=[])
    preflight.add_argument("--stop-condition", action="append", default=[])
    preflight.add_argument("--confirm", action="store_true")

    confirm = subparsers.add_parser("confirm-preflight", help="Confirm a preflight run.")
    confirm.add_argument("--repo-root", default=".")
    confirm.add_argument("--run-id", required=True)

    plan = subparsers.add_parser("plan", help="Run the Planner step.")
    plan.add_argument("--repo-root", default=".")
    plan.add_argument("--run-id", required=True)
    plan.add_argument("--driver", choices=("fake", "codex-exec"), required=True)

    generate = subparsers.add_parser("generate", help="Run the Generator step.")
    generate.add_argument("--repo-root", default=".")
    generate.add_argument("--run-id", required=True)
    generate.add_argument("--driver", choices=("fake", "codex-exec"), required=True)

    evaluate = subparsers.add_parser("evaluate", help="Run the Evaluator step.")
    evaluate.add_argument("--repo-root", default=".")
    evaluate.add_argument("--run-id", required=True)
    evaluate.add_argument("--driver", choices=("fake", "codex-exec"), required=True)
    evaluate.add_argument("--max-attempts", type=int, default=2)

    artifact_hygiene = subparsers.add_parser("artifact-hygiene", help="Run artifact hygiene for generated artifacts.")
    artifact_hygiene.add_argument("--repo-root", default=".")
    artifact_hygiene.add_argument("--run-id", required=True)

    cleanup = subparsers.add_parser("cleanup", help="Run cleanup for retained loop artifacts.")
    cleanup.add_argument("--repo-root", default=".")
    cleanup.add_argument("--run-id", required=True)

    run = subparsers.add_parser("run", help="Run the planner/generator/evaluator loop.")
    run.add_argument("--repo-root", default=".")
    run.add_argument("--run-id", required=True)
    run.add_argument("--planner-driver", choices=("fake", "codex-exec"), required=True)
    run.add_argument("--generator-driver", choices=("fake", "codex-exec"), required=True)
    run.add_argument("--evaluator-driver", choices=("fake", "codex-exec"), required=True)
    run.add_argument("--max-eval-attempts", type=int, default=2)

    run_demand_multi_parser = subparsers.add_parser("run-demand-multi", help="Run demand-development parent/child loop.")
    run_demand_multi_parser.add_argument("--repo-root", default=".")
    run_demand_multi_parser.add_argument("--run-id", required=True)
    run_demand_multi_parser.add_argument("--planner-driver", choices=("fake", "fake-blocked", "fake-failed", "codex-exec"), required=True)
    run_demand_multi_parser.add_argument(
        "--generator-driver",
        choices=(
            "fake",
            "fake-fail-child-2-once",
            "fake-dirty-path",
            "fake-timeout",
            "fake-invalid-json",
            "fake-missing-artifact",
            "fake-stop-after-child-1",
            "codex-exec",
        ),
        required=True,
    )
    run_demand_multi_parser.add_argument("--evaluator-driver", choices=("fake", "codex-exec"), required=True)
    run_demand_multi_parser.add_argument("--max-eval-attempts", type=int, default=2)
    run_demand_multi_parser.add_argument("--max-children", type=int, default=3)

    run_autonomous_parser = subparsers.add_parser("run-autonomous", help="Run the autonomous knowledge loop.")
    run_autonomous_parser.add_argument("--repo-root", default=".")
    run_autonomous_parser.add_argument("--run-id", required=True)
    run_autonomous_parser.add_argument("--planner-driver", choices=("fake", "codex-exec"), required=True)
    run_autonomous_parser.add_argument("--generator-driver", choices=("fake", "fake-denylist", "fake-dependency", "codex-exec"), required=True)
    run_autonomous_parser.add_argument("--evaluator-driver", choices=("fake", "codex-exec"), required=True)
    run_autonomous_parser.add_argument("--max-eval-attempts", type=int, default=2)
    run_autonomous_parser.add_argument("--max-tasks", type=int, default=3)

    status = subparsers.add_parser("status", help="Print run status.")
    status.add_argument("--repo-root", default=".")
    status.add_argument("--run-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "preflight":
        payload = create_preflight_run(
            repo_root=args.repo_root,
            mode=args.mode,
            requirement=args.requirement,
            run_id=args.run_id,
            task_id=args.task_id,
            domain=args.domain,
            policy_file=args.policy_file,
            constraints=args.constraint,
            stop_conditions=args.stop_condition or None,
            confirm=args.confirm,
        )
    elif args.command == "confirm-preflight":
        payload = confirm_preflight(repo_root=args.repo_root, run_id=args.run_id)
    elif args.command == "plan":
        run_planner(repo_root=args.repo_root, run_id=args.run_id, driver=args.driver)
        payload = load_run(args.repo_root, args.run_id)
    elif args.command == "generate":
        run_generator(repo_root=args.repo_root, run_id=args.run_id, driver=args.driver)
        payload = load_run(args.repo_root, args.run_id)
    elif args.command == "evaluate":
        run_evaluator(
            repo_root=args.repo_root,
            run_id=args.run_id,
            driver=args.driver,
            max_attempts=args.max_attempts,
        )
        payload = load_run(args.repo_root, args.run_id)
    elif args.command == "artifact-hygiene":
        run_artifact_hygiene_step(repo_root=args.repo_root, run_id=args.run_id)
        payload = load_run(args.repo_root, args.run_id)
    elif args.command == "cleanup":
        run_cleanup(repo_root=args.repo_root, run_id=args.run_id)
        payload = load_run(args.repo_root, args.run_id)
    elif args.command == "run":
        payload = run_loop(
            repo_root=args.repo_root,
            run_id=args.run_id,
            planner_driver=args.planner_driver,
            generator_driver=args.generator_driver,
            evaluator_driver=args.evaluator_driver,
            max_eval_attempts=args.max_eval_attempts,
        )
    elif args.command == "run-demand-multi":
        payload = run_demand_multi(
            repo_root=args.repo_root,
            run_id=args.run_id,
            planner_driver=args.planner_driver,
            generator_driver=args.generator_driver,
            evaluator_driver=args.evaluator_driver,
            max_eval_attempts=args.max_eval_attempts,
            max_children=args.max_children,
        )
    elif args.command == "run-autonomous":
        payload = run_autonomous(
            repo_root=args.repo_root,
            run_id=args.run_id,
            planner_driver=args.planner_driver,
            generator_driver=args.generator_driver,
            evaluator_driver=args.evaluator_driver,
            max_eval_attempts=args.max_eval_attempts,
            max_tasks=args.max_tasks,
        )
    elif args.command == "status":
        payload = status_for_run(repo_root=args.repo_root, run_id=args.run_id)
    else:
        parser.error(f"unknown command: {args.command}")
    _print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
