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
        normalize_policy_id,
        read_json_file,
        run_dir_for,
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
except ModuleNotFoundError:
    from harness_loop_contracts import (  # type: ignore[no-redef]
        default_limits,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
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
            ["git", "status", "--porcelain"],
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
    constraints: list[str] | None = None,
    stop_conditions: list[str] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    policy = normalize_policy_id(mode)
    if policy != "demand_development":
        raise ValueError("Phase 1 preflight only supports demand_development policy")
    constraints = list(constraints or [])
    stop_conditions = list(stop_conditions or ["passed_waiting_human_merge"])
    phase = "planned" if confirm else "preflight"
    next_action = "run_planner" if confirm else "await_preflight_confirmation"
    baseline_dirty_paths = _baseline_dirty_paths(root)
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
        "domain": "",
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
    return save_run(root, payload)


def confirm_preflight(repo_root: Path | str, run_id: str) -> dict[str, Any]:
    payload = load_run(repo_root, run_id)
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


def _apply_evaluator_result_to_run(
    run: dict[str, Any],
    evaluator_payload: dict[str, Any],
    *,
    has_artifacts: bool = False,
) -> None:
    passed = evaluator_payload["returncode"] == 0 and evaluator_payload["status"] == "pass"
    if passed and has_artifacts:
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
    if passed and has_artifacts:
        run["next_action"] = "run_artifact_hygiene"
    elif passed:
        run["next_action"] = "await_human_merge_confirmation"
    else:
        run["next_action"] = "repair_from_evaluator_findings"


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
                _apply_evaluator_result_to_run(run, evaluator_payload)
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
            evaluator_status == "pass"
            and result.returncode == 0
            and _generator_result_has_artifacts(run_dir)
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
    result_path = run_artifact_hygiene(
        repo_root=root,
        run_dir=run_dir,
        artifact_paths=list(generator_result["artifacts"]),
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
    else:
        run["phase"] = "cleanup"
        run["next_action"] = "run_cleanup"
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
    elif args.command == "status":
        payload = status_for_run(repo_root=args.repo_root, run_id=args.run_id)
    else:
        parser.error(f"unknown command: {args.command}")
    _print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
