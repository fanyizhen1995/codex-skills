#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gpu_flow_common import (
    PENDING_TASK_STATUSES,
    git_worktrees,
    is_active_session,
    load_json_dir,
    load_tasks,
    lock_task_id,
    normalize_status,
    session_task_id,
    task_counts,
)


PRIORITY_SCORE = {"high": 30, "medium": 20, "low": 10}
def blocked_by(task: dict[str, Any]) -> str:
    value = task.get("blocked_by") or task.get("blockedBy") or ""
    if isinstance(value, list):
        return ",".join(str(item) for item in value if item)
    return str(value).strip()


def build_candidates(repo: Path) -> dict[str, Any]:
    tasks = load_tasks(repo)
    sessions = load_json_dir(repo / ".codex" / "session-state")
    locks = load_json_dir(repo / ".codex" / "locks")
    worktrees = git_worktrees(repo)

    active_sessions_by_task: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        task_id = session_task_id(session)
        if task_id and is_active_session(session):
            active_sessions_by_task.setdefault(task_id, []).append(session)

    locks_by_task: dict[str, list[dict[str, Any]]] = {}
    for lock in locks:
        task_id = lock_task_id(lock)
        if task_id:
            locks_by_task.setdefault(task_id, []).append(lock)

    candidates: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task.get("id") or task.get("task") or "").strip()
        status = normalize_status(task.get("status"))
        if not task_id or status in {"done", "completed", "accepted"}:
            continue

        reasons: list[str] = []
        score = PRIORITY_SCORE.get(normalize_status(task.get("priority")), 0)
        if status in PENDING_TASK_STATUSES:
            score += 20
        else:
            reasons.append(f"status:{status or 'unknown'}")

        blocker = blocked_by(task)
        if blocker:
            score -= 25
            reasons.append("blocked_by")

        if task_id in active_sessions_by_task:
            score -= 40
            reasons.append("active_session")

        if task_id in locks_by_task:
            score -= 20
            reasons.append("active_lock")

        if any(task_id in path for path in worktrees):
            score -= 8
            reasons.append("existing_worktree")

        if task.get("requires_eval") is True:
            score -= 3
            reasons.append("requires_eval")

        if task_id in active_sessions_by_task or task_id in locks_by_task:
            recommendation = "coordinate"
        elif blocker:
            recommendation = "wait"
        elif status in PENDING_TASK_STATUSES:
            recommendation = "claim"
        else:
            recommendation = "review"

        candidates.append(
            {
                "id": task_id,
                "title": str(task.get("title") or ""),
                "status": status or "unknown",
                "priority": str(task.get("priority") or ""),
                "blocked_by": blocker,
                "requires_eval": bool(task.get("requires_eval")),
                "verify": str(task.get("verify") or ""),
                "recommendation": recommendation,
                "score": score,
                "reasons": reasons,
                "active_sessions": [session.get("_path", "") for session in active_sessions_by_task.get(task_id, [])],
                "active_locks": [lock.get("_path", "") for lock in locks_by_task.get(task_id, [])],
            }
        )

    candidates.sort(key=lambda item: (item["score"], item["priority"], item["id"]), reverse=True)
    counts = task_counts(tasks)
    return {
        "repo": str(repo),
        "summary": {
            "total": len(tasks),
            "pending": sum(counts.get(key, 0) for key in ("pending", "todo", "open")),
            "done": sum(counts.get(key, 0) for key in ("done", "completed", "accepted")),
            "session_state_files": len(sessions),
            "lock_files": len(locks),
            "worktrees": len(worktrees),
        },
        "candidates": candidates,
    }


def print_text(data: dict[str, Any], limit: int) -> None:
    summary = data["summary"]
    print(f"Repo: {data['repo']}")
    print(
        "Tasks: "
        f"{summary['pending']} pending, {summary['done']} done, "
        f"{summary['session_state_files']} session-state, {summary['lock_files']} locks, "
        f"{summary['worktrees']} worktrees"
    )
    print()
    for item in data["candidates"][:limit]:
        reasons = ", ".join(item["reasons"]) if item["reasons"] else "clean"
        print(f"- {item['id']} [{item['recommendation']}] score={item['score']} priority={item['priority']} reasons={reasons}")
        if item["title"]:
            print(f"  {item['title']}")
        if item["blocked_by"]:
            print(f"  blocked_by: {item['blocked_by']}")
        if item["verify"]:
            print(f"  verify: {item['verify']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank HAMI GPU Flow tasks that are safe to claim.")
    parser.add_argument("--repo", default=".", help="Path to the HAMI repository")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    parser.add_argument("--limit", type=int, default=12, help="Text output candidate limit")
    args = parser.parse_args()

    data = build_candidates(Path(args.repo).resolve())
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_text(data, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
