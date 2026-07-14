"""Cross-process ownership lock for one harness loop run."""

from __future__ import annotations

import fcntl
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class RunLockBusy(RuntimeError):
    def __init__(self, run_id: str, current_owner: str = "") -> None:
        self.run_id = run_id
        self.current_owner = current_owner
        detail = f" by {current_owner}" if current_owner else ""
        super().__init__(f"run {run_id} is already locked{detail}")


def run_lock_path(repo_root: Path, run_id: str) -> Path:
    _validate_run_id(run_id)
    return Path(repo_root) / ".codex" / "loop-locks" / f"{run_id}.lock"


def repository_mutation_lock_path(repo_root: Path) -> Path:
    return Path(repo_root) / ".codex" / "loop-locks" / "repository-mutation.lock"


@contextmanager
def acquire_run_lock(repo_root: Path, run_id: str, *, owner: str) -> Iterator[dict[str, object]]:
    with _acquire_lock(
        run_lock_path(repo_root, run_id),
        lock_id=run_id,
        owner=owner,
    ) as metadata:
        yield metadata


@contextmanager
def acquire_repository_mutation_lock(
    repo_root: Path, *, owner: str
) -> Iterator[dict[str, object]]:
    with _acquire_lock(
        repository_mutation_lock_path(repo_root),
        lock_id="repository-mutation",
        owner=owner,
    ) as metadata:
        yield metadata


@contextmanager
def _acquire_lock(
    path: Path, *, lock_id: str, owner: str
) -> Iterator[dict[str, object]]:
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("lock owner must be a non-empty string")
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        handle.seek(0)
        existing = _read_metadata(handle.read())
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise RunLockBusy(lock_id, str(existing.get("owner") or "")) from exc
        metadata = {"lock_id": lock_id, "owner": owner.strip(), "pid": os.getpid()}
        if lock_id != "repository-mutation":
            metadata["run_id"] = lock_id
        handle.seek(0)
        handle.truncate()
        json.dump(metadata, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        try:
            yield metadata
        finally:
            handle.seek(0)
            handle.truncate()
            handle.flush()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        if not handle.closed:
            handle.close()


def _read_metadata(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise ValueError("run_id must contain only letters, digits, dot, underscore, or hyphen")
