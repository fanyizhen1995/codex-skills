"""Cross-process ownership lock for one harness loop run."""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


_RUN_LOCK_TOKEN_GUARD = object()


class RunLockBusy(RuntimeError):
    def __init__(self, run_id: str, current_owner: str = "") -> None:
        self.run_id = run_id
        self.current_owner = current_owner
        detail = f" by {current_owner}" if current_owner else ""
        super().__init__(f"run {run_id} is already locked{detail}")


class RunLockToken(dict[str, object]):
    """Proof that the caller currently owns one repository-local run lock."""

    def __init__(
        self,
        *,
        repo_root: Path,
        run_id: str,
        owner: str,
        pid: int,
        handle: object,
        runs_fd: int | None,
        run_fd: int | None,
    ) -> None:
        super().__init__(lock_id=run_id, run_id=run_id, owner=owner, pid=pid)
        self._repo_root = repo_root
        self._run_id = run_id
        self._handle = handle
        self._runs_fd = runs_fd
        self._run_fd = run_fd
        if run_fd is None:
            self._run_directory_identity = None
        else:
            opened = os.fstat(run_fd)
            self._run_directory_identity = (opened.st_dev, opened.st_ino)
        self._guard = _RUN_LOCK_TOKEN_GUARD
        self._active = True

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @property
    def run_directory_identity(self) -> tuple[int, int] | None:
        return self._run_directory_identity

    @property
    def runs_fd(self) -> int:
        if self._runs_fd is None:
            raise ValueError("run lock token has no bound runs directory")
        return self._runs_fd

    @property
    def run_fd(self) -> int:
        if self._run_fd is None:
            raise ValueError("run lock token has no bound run directory")
        return self._run_fd


def run_lock_path(repo_root: Path, run_id: str) -> Path:
    _validate_run_id(run_id)
    return Path(repo_root) / ".codex" / "loop-locks" / f"{run_id}.lock"


def repository_mutation_lock_path(repo_root: Path) -> Path:
    return Path(repo_root) / ".codex" / "loop-locks" / "repository-mutation.lock"


@contextmanager
def acquire_run_lock(
    repo_root: Path,
    run_id: str,
    *,
    owner: str,
    blocking: bool = False,
) -> Iterator[RunLockToken]:
    root = Path(repo_root).resolve()
    with _acquire_lock(
        run_lock_path(root, run_id),
        lock_id=run_id,
        owner=owner,
        blocking=blocking,
        run_root=root,
    ) as token:
        if not isinstance(token, RunLockToken):
            raise TypeError("run lock did not produce a token")
        yield token


@contextmanager
def acquire_repository_mutation_lock(
    repo_root: Path, *, owner: str
) -> Iterator[dict[str, object]]:
    with _acquire_lock(
        repository_mutation_lock_path(repo_root),
        lock_id="repository-mutation",
        owner=owner,
        blocking=False,
        run_root=None,
    ) as metadata:
        yield metadata


@contextmanager
def _acquire_lock(
    path: Path,
    *,
    lock_id: str,
    owner: str,
    blocking: bool,
    run_root: Path | None,
) -> Iterator[dict[str, object] | RunLockToken]:
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("lock owner must be a non-empty string")
    path = path.absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        handle = os.fdopen(fd, "a+", encoding="utf-8")
    except BaseException:
        os.close(fd)
        raise
    try:
        handle.seek(0)
        existing = _read_metadata(handle.read())
        try:
            flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            fcntl.flock(handle.fileno(), flags)
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
        token = (
            RunLockToken(
                repo_root=run_root,
                run_id=lock_id,
                owner=owner.strip(),
                pid=os.getpid(),
                handle=handle,
                **_open_run_directory_binding(run_root, lock_id),
            )
            if run_root is not None
            else metadata
        )
        try:
            yield token
        finally:
            primary_exception = sys.exc_info()[0] is not None
            if isinstance(token, RunLockToken):
                token._active = False
                for directory_fd in (token._run_fd, token._runs_fd):
                    if directory_fd is not None:
                        os.close(directory_fd)
                token._run_fd = None
                token._runs_fd = None
            cleanup_error: BaseException | None = None
            try:
                handle.seek(0)
                handle.truncate()
                handle.flush()
            except BaseException as exc:
                cleanup_error = exc
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            if cleanup_error is not None and not primary_exception:
                raise cleanup_error
    finally:
        if not handle.closed:
            handle.close()


def validate_run_lock_token(
    token: object, repo_root: Path, run_id: str
) -> RunLockToken:
    root = Path(repo_root).resolve()
    if (
        not isinstance(token, RunLockToken)
        or token._guard is not _RUN_LOCK_TOKEN_GUARD
        or not token._active
        or token._repo_root != root
        or token._run_id != run_id
        or getattr(token._handle, "closed", True)
    ):
        raise ValueError("an active run lock token for this repository and run is required")
    if token._run_fd is not None:
        opened = os.fstat(token._run_fd)
        current = os.stat(
            run_id,
            dir_fd=token.runs_fd,
            follow_symlinks=False,
        )
        if not stat.S_ISDIR(current.st_mode) or (
            current.st_dev,
            current.st_ino,
        ) != (opened.st_dev, opened.st_ino):
            raise ValueError(f"run directory ownership changed: {run_id}")
    return token


def _open_run_directory_binding(
    root: Path | None, run_id: str
) -> dict[str, int | None]:
    if root is None:
        return {"runs_fd": None, "run_fd": None}
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    runs_path = root / ".codex" / "loop-runs"
    try:
        runs_fd = os.open(runs_path, flags)
    except FileNotFoundError:
        return {"runs_fd": None, "run_fd": None}
    try:
        run_fd = os.open(run_id, flags, dir_fd=runs_fd)
    except BaseException:
        os.close(runs_fd)
        raise
    return {"runs_fd": runs_fd, "run_fd": run_fd}


def _read_metadata(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise ValueError("run_id must contain only letters, digits, dot, underscore, or hyphen")
