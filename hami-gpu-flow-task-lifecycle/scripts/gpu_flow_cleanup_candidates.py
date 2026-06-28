#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gpu_flow_common import (
    DONE_TASK_STATUSES,
    git_worktrees,
    is_active_session,
    is_completed_session,
    load_json_dir,
    load_tasks,
    lock_task_id,
    normalize_status,
    session_task_id,
)


def task_status_by_id(tasks: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for task in tasks:
        task_id = str(task.get("id") or task.get("task") or "").strip()
        if task_id:
            result[task_id] = normalize_status(task.get("status"))
    return result


def path_task_id(path: str, known_task_ids: set[str]) -> str:
    name = Path(path).name
    if name in known_task_ids:
        return name
    matches = [task_id for task_id in known_task_ids if task_id and task_id in name]
    if not matches:
        return ""
    return sorted(matches, key=len, reverse=True)[0]


def add_candidate(candidates: list[dict[str, Any]], kind: str, item_type: str, path: str, task_id: str, reasons: list[str]) -> None:
    candidates.append(
        {
            "kind": kind,
            "type": item_type,
            "path": path,
            "task_id": task_id,
            "reasons": reasons,
        }
    )


def classify_cleanup(repo: Path) -> dict[str, Any]:
    tasks = load_tasks(repo)
    task_status = task_status_by_id(tasks)
    known_task_ids = set(task_status)
    sessions = load_json_dir(repo / ".codex" / "session-state")
    locks = load_json_dir(repo / ".codex" / "locks")
    worktrees = git_worktrees(repo)

    active_task_ids = {session_task_id(session) for session in sessions if is_active_session(session) and session_task_id(session)}
    completed_session_task_ids = {
        session_task_id(session) for session in sessions if is_completed_session(session) and session_task_id(session)
    }
    lock_task_ids = {lock_task_id(lock) for lock in locks if lock_task_id(lock)}
    done_task_ids = {task_id for task_id, status in task_status.items() if status in DONE_TASK_STATUSES}

    candidates: list[dict[str, Any]] = []

    for path in worktrees:
        task_id = path_task_id(path, known_task_ids)
        if not task_id:
            add_candidate(candidates, "unknown_manual", "worktree", path, "", ["no_matching_task"])
        elif task_id in active_task_ids:
            add_candidate(candidates, "active_keep", "worktree", path, task_id, ["active_session"])
        elif task_id in done_task_ids or task_id in completed_session_task_ids:
            add_candidate(candidates, "safe_review", "worktree", path, task_id, ["task_or_session_completed"])
        else:
            add_candidate(candidates, "unknown_manual", "worktree", path, task_id, [f"task_status:{task_status.get(task_id, 'unknown')}"])

    for session in sessions:
        task_id = session_task_id(session)
        path = str(session.get("_path") or "")
        if task_id in active_task_ids:
            add_candidate(candidates, "active_keep", "session-state", path, task_id, ["active_session"])
        elif task_id in done_task_ids or is_completed_session(session):
            add_candidate(candidates, "safe_review", "session-state", path, task_id, ["task_or_session_completed"])
        else:
            add_candidate(candidates, "unknown_manual", "session-state", path, task_id, [f"session_status:{normalize_status(session.get('status')) or 'unknown'}"])

    for lock in locks:
        task_id = lock_task_id(lock)
        path = str(lock.get("_path") or "")
        if task_id in active_task_ids:
            add_candidate(candidates, "active_keep", "lock", path, task_id, ["active_session"])
        elif task_id in done_task_ids or task_id in completed_session_task_ids:
            add_candidate(candidates, "safe_review", "lock", path, task_id, ["task_or_session_completed"])
        elif task_id in lock_task_ids:
            add_candidate(candidates, "stale_review", "lock", path, task_id, ["no_active_session"])
        else:
            add_candidate(candidates, "unknown_manual", "lock", path, task_id, ["no_matching_task"])

    order = {"active_keep": 0, "stale_review": 1, "safe_review": 2, "unknown_manual": 3}
    candidates.sort(key=lambda item: (order.get(item["kind"], 99), item["task_id"], item["type"], item["path"]))
    counts: dict[str, int] = {}
    for item in candidates:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1

    return {
        "repo": str(repo),
        "summary": {
            "tasks": len(tasks),
            "worktrees": len(worktrees),
            "session_state_files": len(sessions),
            "lock_files": len(locks),
            "by_kind": counts,
        },
        "candidates": candidates,
        "note": "Read-only report. Review manually before deleting worktrees, session-state files, or locks.",
    }


def print_text(data: dict[str, Any], limit: int) -> None:
    print(f"Repo: {data['repo']}")
    print(data["note"])
    print(f"Summary: {json.dumps(data['summary'], ensure_ascii=False)}")
    print()
    for item in data["candidates"][:limit]:
        reasons = ", ".join(item["reasons"])
        print(f"- {item['kind']} {item['type']} task={item['task_id'] or '?'} reasons={reasons}")
        print(f"  {item['path']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only cleanup candidate report for HAMI GPU Flow coordination state.")
    parser.add_argument("--repo", default=".", help="Path to the HAMI repository")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    parser.add_argument("--limit", type=int, default=80, help="Text output row limit")
    args = parser.parse_args()

    data = classify_cleanup(Path(args.repo).resolve())
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_text(data, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
