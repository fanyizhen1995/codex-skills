#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


ACTIVE_SESSION_STATUSES = {
    "",
    "active",
    "claimed",
    "designing",
    "implementing",
    "running",
    "testing",
    "blocked",
    "handoff",
    "in_progress",
}
COMPLETED_SESSION_STATUSES = {
    "accepted",
    "done",
    "completed",
    "merged",
    "closed",
    "squashed",
}
DONE_TASK_STATUSES = {"done", "completed", "accepted"}
PENDING_TASK_STATUSES = {"pending", "todo", "open"}


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def load_tasks(repo: Path) -> list[dict[str, Any]]:
    data = load_json(repo / "tasks.json", [])
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("tasks", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def load_json_dir(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_dir():
        return rows
    for item in sorted(path.glob("*.json")):
        data = load_json(item, {})
        if isinstance(data, dict):
            data["_path"] = str(item)
            rows.append(data)
    return rows


def task_key(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("id", "task", "title"):
            raw = value.get(key)
            if isinstance(raw, str):
                return raw
    return ""


def session_task_id(session: dict[str, Any]) -> str:
    for key in ("task", "task_id", "id"):
        value = session.get(key)
        key_value = task_key(value)
        if key_value:
            return key_value
    return ""


def lock_task_id(lock: dict[str, Any]) -> str:
    for key in ("task", "task_id", "owner_task"):
        value = lock.get(key)
        key_value = task_key(value)
        if key_value:
            return key_value
    return ""


def normalize_status(value: Any) -> str:
    return str(value or "").strip().lower()


def is_active_session(session: dict[str, Any]) -> bool:
    return normalize_status(session.get("status")) in ACTIVE_SESSION_STATUSES


def is_completed_session(session: dict[str, Any]) -> bool:
    return normalize_status(session.get("status")) in COMPLETED_SESSION_STATUSES


def run_git(repo: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def git_worktrees(repo: Path) -> list[str]:
    output = run_git(repo, ["worktree", "list", "--porcelain"])
    if output:
        return [line.split(" ", 1)[1] for line in output.splitlines() if line.startswith("worktree ")]
    fallback = repo / ".worktrees"
    if fallback.is_dir():
        return [str(path) for path in sorted(fallback.iterdir()) if path.is_dir()]
    return []


def progress_head(repo: Path, max_lines: int = 24) -> str:
    path = repo / "progress.md"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return ""
    kept: list[str] = []
    for line in lines:
        kept.append(line)
        if len(kept) >= max_lines:
            break
    return "\n".join(kept).strip()


def task_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts
