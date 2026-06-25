from __future__ import annotations

from pathlib import Path
import subprocess


def git_dirty_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return _parse_porcelain_z(result.stdout)


def paths_owned_by_task(paths: set[str], owned_prefixes: list[str]) -> bool:
    return all(any(path.startswith(prefix) for prefix in owned_prefixes) for path in paths)


def auto_commit(repo_root: Path, paths: list[str], message: str) -> str:
    staged = _staged_paths(repo_root)
    if staged:
        raise ValueError("staged changes already exist")

    requested_paths = set(paths)
    stageable_paths = _stageable_paths(repo_root, requested_paths)
    if not stageable_paths:
        raise ValueError("no staged changes")

    try:
        subprocess.run(["git", "add", "--", *stageable_paths], cwd=repo_root, check=True, capture_output=True, text=True)
        staged_after_add = _staged_paths(repo_root)
        if not staged_after_add:
            raise ValueError("no staged changes")
        if not staged_after_add.issubset(requested_paths):
            raise ValueError("staged changes include files outside requested paths")

        commit = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if commit.returncode != 0:
            raise RuntimeError(f"git commit failed: {commit.stdout}{commit.stderr}")
    except Exception:
        _unstage_paths(repo_root, stageable_paths)
        raise
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _stageable_paths(repo_root: Path, paths: set[str]) -> list[str]:
    deleted_paths = _deleted_paths(repo_root)
    stageable: list[str] = []
    for path in sorted(paths):
        candidate = repo_root / path
        if candidate.is_file() or path in deleted_paths:
            stageable.append(path)
    return stageable


def _parse_porcelain_z(output: bytes) -> set[str]:
    paths: set[str] = set()
    entries = output.split(b"\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        if not entry:
            index += 1
            continue

        status = entry[:2].decode("ascii", errors="replace")
        path = entry[3:].decode("utf-8", errors="surrogateescape")
        if path:
            paths.add(path)
        index += 1

        if "R" in status or "C" in status:
            if index < len(entries) and entries[index]:
                paths.add(entries[index].decode("utf-8", errors="surrogateescape"))
            index += 1

    return paths


def _staged_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return {
        path.decode("utf-8", errors="surrogateescape")
        for path in result.stdout.split(b"\0")
        if path
    }


def _deleted_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=D", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return {
        path.decode("utf-8", errors="surrogateescape")
        for path in result.stdout.split(b"\0")
        if path
    }


def _unstage_paths(repo_root: Path, paths: list[str]) -> None:
    subprocess.run(
        ["git", "reset", "-q", "--", *paths],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
