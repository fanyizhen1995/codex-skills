#!/usr/bin/env python3
import argparse
import json
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
        validate_run_payload,
        write_json_file,
    )
except ModuleNotFoundError:
    from harness_loop_contracts import (  # type: ignore[no-redef]
        default_limits,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
        validate_run_payload,
        write_json_file,
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
) -> dict[str, Any]:
    root = Path(repo_root)
    policy = normalize_policy_id(mode)
    phase = "planned" if confirm else "preflight"
    next_action = "run_planner" if confirm else "await_preflight_confirmation"
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
        "task_id": "",
        "domain": "",
        "branch": _current_branch(root),
        "worktree": str(root.resolve()),
        "baseline_dirty_paths": _baseline_dirty_paths(root),
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
    preflight.add_argument("--confirm", action="store_true")

    confirm = subparsers.add_parser("confirm-preflight", help="Confirm a preflight run.")
    confirm.add_argument("--repo-root", default=".")
    confirm.add_argument("--run-id", required=True)

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
            confirm=args.confirm,
        )
    elif args.command == "confirm-preflight":
        payload = confirm_preflight(repo_root=args.repo_root, run_id=args.run_id)
    elif args.command == "status":
        payload = status_for_run(repo_root=args.repo_root, run_id=args.run_id)
    else:
        parser.error(f"unknown command: {args.command}")
    _print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
