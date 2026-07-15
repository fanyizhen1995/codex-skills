"""Shared bounded-action failure classification."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

from scripts.harness_loop_runtime_lock import RunLockBusy

from .models import ActionResult, ActionResultClass


class BoundedFailure(RuntimeError):
    def __init__(
        self,
        summary: str,
        *,
        cause: BaseException | None = None,
        artifact_paths: tuple[str, ...] = (),
        checkpoint: str = "",
    ) -> None:
        super().__init__(summary)
        self.cause = cause
        self.artifact_paths = artifact_paths
        self.checkpoint = checkpoint


def redact_bounded_text(value: object, *, limit: int = 1024) -> str:
    text = str(value).replace("\x00", "")
    text = re.sub(
        r"(?i)\b(token|secret|password|authorization)\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        text,
    )
    return text[:limit]


def _valid_partial_artifacts(
    execution_root: Path | None, paths: tuple[str, ...]
) -> tuple[str, ...]:
    if execution_root is None:
        return ()
    valid: list[str] = []
    for value in paths:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value != path.as_posix():
            continue
        current = execution_root
        try:
            for part in path.parts:
                current = current / part
                metadata = current.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    raise OSError("partial artifact path contains a symlink")
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode):
            valid.append(value)
    return tuple(valid)


def classify_bounded_failure(
    exc: BaseException,
    *,
    action_id: str,
    execution_root: Path | None = None,
    started_at: str = "",
    finished_at: str = "",
) -> ActionResult:
    source = exc.cause if isinstance(exc, BoundedFailure) and exc.cause else exc
    text = f"{exc.__class__.__name__}: {exc} {source.__class__.__name__}: {source}".lower()
    policy_markers = (
        "policy",
        "permission",
        "scope",
        "secret",
        "symlink",
        "ownership",
    )
    policy = isinstance(source, PermissionError) or any(
        marker in text for marker in policy_markers
    )
    artifacts = ()
    checkpoint = ""
    if not policy and isinstance(exc, BoundedFailure):
        artifacts = _valid_partial_artifacts(execution_root, exc.artifact_paths)
        checkpoint = exc.checkpoint if artifacts else ""

    retryable = isinstance(
        source,
        (OSError, RunLockBusy, TimeoutError, subprocess.SubprocessError),
    ) or any(
        marker in text
        for marker in (
            "index.lock",
            "could not resolve",
            "dns",
            "transport",
            "connection",
            "timed out",
            "timeout",
        )
    )
    terminal = isinstance(source, (TypeError, ValueError)) or any(
        marker in text
        for marker in ("corrupt", "unprovable", "invalid json", "run payload")
    )
    if policy:
        result_class = ActionResultClass.POLICY_BLOCK
    elif artifacts:
        result_class = ActionResultClass.RECOVERABLE_PARTIAL
    elif terminal:
        result_class = ActionResultClass.TERMINAL_FAILURE
    elif retryable:
        result_class = ActionResultClass.RETRYABLE_FAILURE
    else:
        result_class = ActionResultClass.RETRYABLE_FAILURE
    return ActionResult(
        result_class=result_class,
        summary=redact_bounded_text(str(exc) or exc.__class__.__name__),
        failure_key=(
            f"worker:{hashlib.sha256(action_id.encode()).hexdigest()[:16]}:"
            f"{source.__class__.__name__}"
        ),
        error_class=source.__class__.__name__,
        artifact_paths=artifacts,
        checkpoint=checkpoint,
        started_at=started_at,
        finished_at=finished_at,
    )
