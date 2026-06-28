#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gpu_flow_common import (
    git_worktrees,
    is_active_session,
    load_json_dir,
    load_tasks,
    lock_task_id,
    progress_head,
    run_git,
    session_task_id,
    task_counts,
)


def build_snapshot(repo: Path) -> dict[str, Any]:
    tasks = load_tasks(repo)
    sessions = load_json_dir(repo / ".codex" / "session-state")
    locks = load_json_dir(repo / ".codex" / "locks")
    counts = task_counts(tasks)

    active_tasks = sorted({session_task_id(item) for item in sessions if is_active_session(item) and session_task_id(item)})
    locked_tasks = sorted({task for task in (lock_task_id(item) for item in locks) if task})

    return {
        "repo": str(repo),
        "git": {
            "branch": run_git(repo, ["branch", "--show-current"]),
            "head": run_git(repo, ["rev-parse", "--short", "HEAD"]),
            "status_short": run_git(repo, ["status", "--short"]),
            "recent_commits": run_git(repo, ["log", "--date=short", "--pretty=format:%h %ad %s", "-8"]),
        },
        "tasks": {
            "total": len(tasks),
            "pending": sum(counts.get(key, 0) for key in ("pending", "todo", "open")),
            "done": sum(counts.get(key, 0) for key in ("done", "completed", "accepted")),
            "by_status": counts,
        },
        "session_state": {
            "total": len(sessions),
            "active_tasks": active_tasks,
            "recent_files": [item.get("_path", "") for item in sessions[-10:]],
        },
        "locks": {
            "total": len(locks),
            "tasks": locked_tasks,
            "recent_files": [item.get("_path", "") for item in locks[-10:]],
        },
        "worktrees": {
            "total": len(git_worktrees(repo)),
            "paths": git_worktrees(repo)[:80],
        },
        "progress_head": progress_head(repo),
    }


def print_text(data: dict[str, Any]) -> None:
    git = data["git"]
    tasks = data["tasks"]
    sessions = data["session_state"]
    locks = data["locks"]
    worktrees = data["worktrees"]

    print(f"Repo: {data['repo']}")
    print(f"Git: {git['branch'] or '?'} {git['head'] or '?'}")
    if git["status_short"]:
        print("Dirty files:")
        print(git["status_short"])
    print(f"Tasks: {tasks['pending']} pending, {tasks['done']} done, {tasks['total']} total")
    print(f"Session-state: {sessions['total']} files; active tasks: {', '.join(sessions['active_tasks'][:20]) or 'none'}")
    print(f"Locks: {locks['total']} files; locked tasks: {', '.join(locks['tasks'][:20]) or 'none'}")
    print(f"Worktrees: {worktrees['total']}")
    if data["progress_head"]:
        print()
        print("Progress head:")
        print(data["progress_head"])
    if git["recent_commits"]:
        print()
        print("Recent commits:")
        print(git["recent_commits"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize HAMI GPU Flow task/worktree/session state.")
    parser.add_argument("--repo", default=".", help="Path to the HAMI repository")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    data = build_snapshot(Path(args.repo).resolve())
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_text(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
