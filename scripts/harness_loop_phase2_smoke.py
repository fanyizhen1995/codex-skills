#!/usr/bin/env python3
import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

try:
    from scripts.harness_loop_contracts import (
        read_json_file,
        run_dir_for,
        validate_generator_result_payload,
        validate_run_payload,
        validate_task_contract_payload,
        write_json_file,
    )
    from scripts.harness_loop_orchestrator import (
        _run_generator as run_generator,
        _run_loop as run_loop,
        _run_planner as run_planner,
        create_preflight_run,
    )
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from harness_loop_contracts import (  # type: ignore[no-redef]
        read_json_file,
        run_dir_for,
        validate_generator_result_payload,
        validate_run_payload,
        validate_task_contract_payload,
        write_json_file,
    )
    from harness_loop_orchestrator import (  # type: ignore[no-redef]
        _run_generator as run_generator,
        _run_loop as run_loop,
        _run_planner as run_planner,
        create_preflight_run,
    )


SMOKE_ARTIFACT = Path(".codex/tmp/phase-2-smoke-artifact.txt")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _validate_safe_id(value: str, label: str) -> None:
    if not SAFE_ID_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe slug")


def _safe_child(root: Path, child: Path, label: str) -> Path:
    resolved_root = root.resolve()
    resolved_child = child.resolve()
    try:
        resolved_child.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes {resolved_root}") from exc
    return resolved_child


def _scenario_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / "docs" / "harness" / "evaluator-scenarios" / f"{task_id}.json"


def _assert_fake_evaluator_metadata(repo_root: Path, task_id: str) -> None:
    scenario_path = _scenario_path(repo_root, task_id)
    if not scenario_path.exists():
        raise FileNotFoundError(f"fake evaluator scenario metadata missing: {scenario_path}")
    payload = read_json_file(scenario_path)
    if payload.get("task_id") != task_id:
        raise RuntimeError(f"scenario metadata task_id mismatch: {scenario_path}")
    if not payload.get("user_scenarios"):
        raise RuntimeError(f"scenario metadata has no user_scenarios: {scenario_path}")


def _clean_previous_smoke(repo_root: Path, run_id: str, task_id: str) -> None:
    loop_runs_root = repo_root / ".codex" / "loop-runs"
    run_dir = _safe_child(loop_runs_root, run_dir_for(repo_root, run_id), "run_id")
    shutil.rmtree(run_dir, ignore_errors=True)
    (repo_root / SMOKE_ARTIFACT).unlink(missing_ok=True)
    eval_tasks_root = repo_root / ".codex" / "evaluations" / "tasks"
    eval_task_dir = _safe_child(eval_tasks_root, eval_tasks_root / task_id, "task_id")
    for attempt_dir in eval_task_dir.glob("fake-attempt-*"):
        if attempt_dir.is_dir():
            shutil.rmtree(attempt_dir)


def _write_smoke_artifact(repo_root: Path) -> str:
    artifact_path = repo_root / SMOKE_ARTIFACT
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("phase 2 smoke artifact\n", encoding="utf-8")
    return SMOKE_ARTIFACT.as_posix()


def _add_generator_artifact(generator_path: Path, artifact_relative_path: str) -> None:
    generator_result = read_json_file(generator_path)
    generator_result["artifacts"] = [artifact_relative_path]
    generator_result["cleanup_required"] = True
    validate_generator_result_payload(generator_result)
    write_json_file(generator_path, generator_result)


def _write_task_contract(run_dir: Path, task_id: str, artifact_relative_path: str) -> Path:
    scenario_command = (
        "python3 -c "
        "\"from pathlib import Path; "
        f"p=Path('{artifact_relative_path}'); "
        "assert p.is_file() and p.stat().st_size > 0; "
        "print('phase2 scenario command passed')\""
    )
    payload = {
        "task_id": task_id,
        "title": "Planner generator evaluator loop Phase 2 smoke",
        "description": "Self-contained smoke for task-contract scenario command evidence, artifact hygiene, cleanup, and human merge gate.",
        "verify_commands": [],
        "scenario_commands": [scenario_command],
        "artifact_paths": [artifact_relative_path],
        "required_services": [],
        "evaluator_driver": "fake",
        "eval_policy": {
            "task_level_required": True,
            "max_task_eval_attempts": 2,
        },
        "allowed_scope": "local_repo_and_harness",
        "must_simulate": True,
        "user_scenarios": [
            {
                "scenario_id": "PGE-PHASE2-SMOKE-CONTRACT",
                "user_goal": "Run a local scenario command and preserve its evidence before artifact hygiene and cleanup.",
                "prerequisites": ["The smoke artifact exists under .codex/tmp."],
                "steps": ["Run the task-contract scenario command."],
                "expected_outcomes": ["scenario-command-results.json records a passing command."],
                "failure_signals": ["The scenario command fails or evidence is missing."],
            }
        ],
    }
    validate_task_contract_payload(payload)
    return write_json_file(run_dir / "task-contract.json", payload)


def run_phase2_smoke(repo_root: Path | str, run_id: str, task_id: str) -> dict[str, Any]:
    _validate_safe_id(run_id, "run_id")
    _validate_safe_id(task_id, "task_id")
    root = Path(repo_root).resolve()
    _assert_fake_evaluator_metadata(root, task_id)
    _clean_previous_smoke(root, run_id, task_id)

    create_preflight_run(
        repo_root=root,
        mode="demand-development",
        requirement="Evaluator scenario Phase 2 smoke",
        run_id=run_id,
        task_id=task_id,
        constraints=["Keep Phase 2 smoke artifacts under .codex."],
        stop_conditions=["passed_waiting_human_merge"],
        confirm=True,
    )
    run_planner(root, run_id, driver="fake")
    generator_path = run_generator(root, run_id, driver="fake")
    artifact_relative_path = _write_smoke_artifact(root)
    _add_generator_artifact(generator_path, artifact_relative_path)

    run_dir = run_dir_for(root, run_id)
    _write_task_contract(run_dir, task_id, artifact_relative_path)
    status = run_loop(
        root,
        run_id,
        planner_driver="fake",
        generator_driver="fake",
        evaluator_driver="fake",
        max_eval_attempts=2,
    )

    run_payload = read_json_file(run_dir / "run.json")
    validate_run_payload(run_payload)
    required_paths = {
        "scenario_command_results_path": run_dir / "scenario-command-results.json",
        "artifact_manifest_path": run_dir / "artifact-manifest.json",
        "cleanup_result_path": run_dir / "cleanup-result.json",
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    if missing:
        raise RuntimeError(f"Phase 2 smoke evidence missing: {', '.join(missing)}")
    if run_payload["phase"] != "passed_waiting_human_merge":
        raise RuntimeError(f"Phase 2 smoke ended in phase {run_payload['phase']}")
    if run_payload["next_action"] != "await_human_merge_confirmation":
        raise RuntimeError(f"Phase 2 smoke ended with next_action {run_payload['next_action']}")

    scenario_manifest = read_json_file(required_paths["scenario_command_results_path"])
    artifact_manifest = read_json_file(required_paths["artifact_manifest_path"])
    cleanup_result = read_json_file(required_paths["cleanup_result_path"])
    if scenario_manifest.get("status") != "pass":
        raise RuntimeError("Phase 2 smoke scenario command did not pass")
    if artifact_manifest.get("status") not in {"pass", "redacted"}:
        raise RuntimeError("Phase 2 smoke artifact hygiene did not pass")
    if cleanup_result.get("status") != "pass":
        raise RuntimeError("Phase 2 smoke cleanup did not pass")

    return {
        **status,
        "run_dir": str(run_dir),
        **{name: str(path) for name, path in required_paths.items()},
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Phase 2 planner loop smoke scenario.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-id", default="evaluator-scenario-phase-2")
    parser.add_argument("--task-id", default="planner-generator-evaluator-loop-phase-2-01")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_phase2_smoke(args.repo_root, args.run_id, args.task_id)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
