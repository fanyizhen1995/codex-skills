#!/usr/bin/env python3
"""Resume loop runs that are blocked on orchestrator-actionable phases."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.harness_loop_contracts import read_json_file
    from scripts.harness_loop_orchestrator import run_autonomous, run_demand_multi
    from scripts.harness_loop_runtime_lock import RunLockBusy
except ImportError:  # pragma: no cover - script execution from scripts/
    from harness_loop_contracts import read_json_file  # type: ignore[no-redef]
    from harness_loop_orchestrator import run_autonomous, run_demand_multi  # type: ignore[no-redef]
    from harness_loop_runtime_lock import RunLockBusy  # type: ignore[no-redef]


ACTIONABLE_PHASES = {"audit_blocked", "stopped_blocked"}
ACTIONABLE_STOPPED_BLOCKED_NEXT_ACTIONS = {
    "inspect_autonomous_dirty_paths",
    "inspect_required_evidence",
    "retry_autonomous_push",
}
ACTIONABLE_AUTONOMOUS_RUNNING_PHASES = {"planning", "generating", "evaluating", "artifact_hygiene", "cleanup"}


def _run_json_paths(project_root: Path, *, include_worktrees: bool) -> Iterable[Path]:
    yield from sorted((project_root / ".codex" / "loop-runs").glob("*/run.json"))
    if include_worktrees:
        worktrees_root = project_root / ".worktrees"
        if worktrees_root.exists():
            for worktree in sorted(worktrees_root.iterdir()):
                if worktree.is_dir() and not worktree.is_symlink():
                    yield from sorted((worktree / ".codex" / "loop-runs").glob("*/run.json"))


def repo_root_for_run_json(project_root: Path, run_json_path: Path) -> Path:
    parts = run_json_path.resolve().parts
    for index in range(len(parts) - 2):
        if parts[index] == ".codex" and parts[index + 1] == "loop-runs":
            return Path(*parts[:index])
    return project_root


def discover_actionable_runs(project_root: Path, *, include_worktrees: bool = True) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for run_json in _run_json_paths(project_root, include_worktrees=include_worktrees):
        try:
            run = read_json_file(run_json)
        except Exception as exc:
            candidates.append(
                {
                    "run_id": run_json.parent.name,
                    "repo_root": str(repo_root_for_run_json(project_root, run_json)),
                    "run_json": str(run_json),
                    "status": "invalid",
                    "error": str(exc),
                }
            )
            continue
        policy = str(run.get("policy") or "")
        if policy not in {"demand_development", "autonomous_knowledge"}:
            continue
        phase = str(run.get("phase") or "")
        next_action = str(run.get("next_action") or "")
        is_actionable_phase = phase in ACTIONABLE_PHASES or (
            policy == "autonomous_knowledge" and phase in ACTIONABLE_AUTONOMOUS_RUNNING_PHASES
        )
        if not is_actionable_phase:
            continue
        if phase == "stopped_blocked" and next_action not in ACTIONABLE_STOPPED_BLOCKED_NEXT_ACTIONS:
            continue
        candidates.append(
            {
                "run_id": str(run.get("run_id") or run_json.parent.name),
                "repo_root": str(repo_root_for_run_json(project_root, run_json)),
                "run_json": str(run_json),
                "policy": policy,
                "phase": phase,
                "next_action": next_action,
            }
        )
    return candidates


def resume_candidate(
    candidate: dict[str, Any],
    *,
    planner_driver: str,
    generator_driver: str,
    evaluator_driver: str,
    max_eval_attempts: int,
    max_children: int,
    max_tasks: int,
) -> dict[str, Any]:
    repo_root = Path(str(candidate["repo_root"]))
    run_id = str(candidate["run_id"])
    policy = str(candidate.get("policy") or "")
    if policy == "demand_development":
        status = run_demand_multi(
            repo_root=repo_root,
            run_id=run_id,
            planner_driver=planner_driver,
            generator_driver=generator_driver,
            evaluator_driver=evaluator_driver,
            max_eval_attempts=max_eval_attempts,
            max_children=max_children,
        )
    elif policy == "autonomous_knowledge":
        status = run_autonomous(
            repo_root,
            run_id,
            planner_driver=planner_driver,
            generator_driver=generator_driver,
            evaluator_driver=evaluator_driver,
            max_eval_attempts=max_eval_attempts,
            max_tasks=max_tasks,
        )
    else:
        raise ValueError(f"unsupported policy for auto resume: {policy}")
    return {
        **candidate,
        "status": "resumed",
        "result_phase": status.get("phase"),
        "result_next_action": status.get("next_action"),
    }


def resume_once(
    *,
    project_root: Path,
    include_worktrees: bool = True,
    planner_driver: str = "codex-exec",
    generator_driver: str = "codex-exec",
    evaluator_driver: str = "codex-exec",
    max_eval_attempts: int = 2,
    max_children: int = 3,
    max_tasks: int = 1,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = project_root.resolve()
    candidates = discover_actionable_runs(root, include_worktrees=include_worktrees)
    resumed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    locked: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("status") == "invalid":
            errors.append(candidate)
            continue
        if dry_run:
            resumed.append({**candidate, "status": "dry_run"})
            continue
        try:
            resumed.append(
                resume_candidate(
                    candidate,
                    planner_driver=planner_driver,
                    generator_driver=generator_driver,
                    evaluator_driver=evaluator_driver,
                    max_eval_attempts=max_eval_attempts,
                    max_children=max_children,
                    max_tasks=max_tasks,
                )
            )
        except RunLockBusy as exc:
            locked.append(
                {
                    **candidate,
                    "status": "locked_by_other_executor",
                    "current_owner": exc.current_owner,
                }
            )
        except Exception as exc:
            errors.append({**candidate, "status": "error", "error": str(exc)})
    return {
        "project_root": str(root),
        "candidate_count": len(candidates),
        "resumed_count": len([item for item in resumed if item.get("status") == "resumed"]),
        "dry_run_count": len([item for item in resumed if item.get("status") == "dry_run"]),
        "locked_count": len(locked),
        "error_count": len(errors),
        "resumed": resumed,
        "locked": locked,
        "errors": errors,
    }


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-resume orchestrator-actionable loop runs.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--include-worktrees", action="store_true")
    parser.add_argument("--no-include-worktrees", action="store_true")
    parser.add_argument("--planner-driver", default="codex-exec", choices=["fake", "fake-blocked", "fake-failed", "codex-exec"])
    parser.add_argument(
        "--generator-driver",
        default="codex-exec",
        choices=[
            "fake",
            "fake-fail-child-2-once",
            "fake-dirty-path",
            "fake-timeout",
            "fake-invalid-json",
            "fake-missing-artifact",
            "fake-stop-after-child-1",
            "codex-exec",
        ],
    )
    parser.add_argument("--evaluator-driver", default="codex-exec", choices=["fake", "codex-exec"])
    parser.add_argument("--max-eval-attempts", type=int, default=2)
    parser.add_argument("--max-children", type=int, default=3)
    parser.add_argument("--max-tasks", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)

    include_worktrees = args.include_worktrees or not args.no_include_worktrees
    while True:
        result = resume_once(
            project_root=Path(args.project_root),
            include_worktrees=include_worktrees,
            planner_driver=args.planner_driver,
            generator_driver=args.generator_driver,
            evaluator_driver=args.evaluator_driver,
            max_eval_attempts=args.max_eval_attempts,
            max_children=args.max_children,
            max_tasks=args.max_tasks,
            dry_run=args.dry_run,
        )
        _print_json(result)
        if not args.watch:
            return 1 if result["error_count"] else 0
        time.sleep(max(args.interval_seconds, 1.0))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
