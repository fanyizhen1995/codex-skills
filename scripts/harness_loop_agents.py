#!/usr/bin/env python3
import json
import hashlib
import os
import re
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.harness_loop_contracts import (
        validate_agent_attempt_payload,
        write_json_file,
    )
except ModuleNotFoundError:
    from harness_loop_contracts import (  # type: ignore[no-redef]
        validate_agent_attempt_payload,
        write_json_file,
    )


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class AgentAttemptEvidence:
    attempt: int
    status: str
    payload: Mapping[str, Any]
    path: Path
    attempt_sha256: str
    stream_sha256: Mapping[str, str]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _absolute_lexical_path(path: Path, label: str) -> Path:
    if ".." in path.parts:
        raise PermissionError(f"{label} ownership escapes its owner root")
    return path if path.is_absolute() else Path.cwd() / path


def _lexical_lstat(path: Path, label: str) -> os.stat_result | None:
    current = Path(path.anchor)
    metadata = current.lstat()
    for part in path.parts[1:]:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(metadata.st_mode):
            raise PermissionError(f"{label} ownership traverses a symlink: {current}")
    return metadata


def validate_owned_regular_file(owner_root: Path, path: Path, label: str) -> Path:
    """Validate lexical ownership before resolving a regular evidence file."""
    owner = _absolute_lexical_path(Path(owner_root), f"{label} owner root")
    owner_metadata = _lexical_lstat(owner, f"{label} owner root")
    if owner_metadata is None or not stat.S_ISDIR(owner_metadata.st_mode):
        raise PermissionError(f"{label} owner root ownership requires a real directory")

    raw_candidate = Path(path)
    candidate = _absolute_lexical_path(raw_candidate, label)
    if not raw_candidate.is_absolute():
        candidate = owner / raw_candidate
    try:
        relative = candidate.relative_to(owner)
    except ValueError as exc:
        raise PermissionError(f"{label} ownership escapes its owner root") from exc

    current = owner
    candidate_metadata = owner_metadata
    for part in relative.parts:
        if part in {"", ".."}:
            raise PermissionError(f"{label} ownership escapes its owner root")
        current = current / part
        try:
            candidate_metadata = current.lstat()
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"missing {label}: {current}") from exc
        if stat.S_ISLNK(candidate_metadata.st_mode):
            raise PermissionError(f"{label} ownership traverses a symlink: {current}")
    try:
        resolved_owner = owner.resolve(strict=True)
        current.resolve(strict=True).relative_to(resolved_owner)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PermissionError(f"{label} ownership escapes its owner root") from exc
    if not stat.S_ISREG(candidate_metadata.st_mode):
        raise PermissionError(f"{label} ownership requires a regular file")
    return current


def _owned_attempt_path(run_dir: Path, value: object, field_name: str) -> Path:
    return validate_owned_regular_file(
        run_dir,
        Path(str(value)),
        f"attempt {field_name}",
    )


def load_validated_attempt_evidence(
    run_dir: Path,
    *,
    role: str,
    expected_run_id: str,
) -> tuple[AgentAttemptEvidence, ...]:
    """Load contract-valid Agent attempts and hash their owned stream evidence."""
    owner = _absolute_lexical_path(Path(run_dir), "attempt owner root")
    owner_metadata = _lexical_lstat(owner, "attempt owner root")
    if owner_metadata is None or not stat.S_ISDIR(owner_metadata.st_mode):
        raise PermissionError("attempt owner root ownership requires a real directory")
    evidence: list[AgentAttemptEvidence] = []
    for discovered_path in sorted(owner.glob(f"{role}-attempt-*.json")):
        path = validate_owned_regular_file(owner, discovered_path, "attempt JSON")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"attempt payload must be an object: {path}")
        validate_agent_attempt_payload(payload)
        if payload["run_id"] != expected_run_id or payload["role"] != role:
            raise PermissionError("attempt payload ownership does not match run and role")
        streams = {
            name: _owned_attempt_path(owner, payload[f"{name}_path"], f"{name}_path")
            for name in ("stdout", "stderr")
        }
        evidence.append(
            AgentAttemptEvidence(
                attempt=int(payload["attempt"]),
                status=str(payload["status"]),
                payload=payload,
                path=path,
                attempt_sha256=_sha256(path),
                stream_sha256={name: _sha256(stream) for name, stream in streams.items()},
            )
        )
    return tuple(evidence)


def codex_exec_capabilities() -> dict[str, bool]:
    try:
        result = subprocess.run(
            ["codex", "exec", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return {"json": False, "output_last_message": False}
    help_text = f"{result.stdout}\n{result.stderr}"
    return {
        "json": "--json" in help_text,
        "output_last_message": "--output-last-message" in help_text,
    }


def build_codex_exec_command(
    repo_root: Path,
    output_message_path: Path,
    capabilities: Mapping[str, bool],
) -> list[str]:
    command = [
        "codex",
        "-a",
        "never",
        "exec",
        "--cd",
        str(repo_root),
        "--color",
        "never",
    ]
    if capabilities.get("json", False):
        command.append("--json")
    if capabilities.get("output_last_message", False):
        command.extend(["--output-last-message", str(output_message_path)])
    command.append("-")
    return command


def run_codex_prompt(
    role: str,
    run_id: str,
    repo_root: Path,
    run_dir: Path,
    prompt_path: Path,
    output_json_path: Path,
    attempt: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / f"{role}-attempt-{attempt}.stdout.log"
    stderr_path = run_dir / f"{role}-attempt-{attempt}.stderr.log"
    attempt_json_path = run_dir / f"{role}-attempt-{attempt}.json"
    output_message_path = run_dir / f"{role}-attempt-{attempt}.message.json"
    started_at = _timestamp()
    prompt = prompt_path.read_text(encoding="utf-8")
    command = build_codex_exec_command(
        repo_root=repo_root,
        output_message_path=output_message_path,
        capabilities=codex_exec_capabilities(),
    )

    try:
        result = subprocess.run(
            command,
            input=prompt,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
        if exit_code == 0:
            if output_json_path.exists() or _write_output_from_final_message(output_message_path, output_json_path):
                status = "pass"
            else:
                status = "invalid_json"
        else:
            status = "fail"
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_timeout_stream(exc.output)
        stderr = _decode_timeout_stream(exc.stderr)
        exit_code = 124
        _terminate_codex_attempt_processes(output_message_path)
        if output_json_path.exists() or _write_output_from_final_message(output_message_path, output_json_path):
            status = "pass"
        else:
            status = "timeout"

    finished_at = _timestamp()
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    payload = {
        "run_id": run_id,
        "role": role,
        "attempt": attempt,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "status": status,
        "prompt_path": str(prompt_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "output_json_path": str(output_json_path),
        "diff_patch_path": "",
        "verify_log_paths": [],
    }
    validate_agent_attempt_payload(payload)
    write_json_file(attempt_json_path, payload)
    return payload


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _terminate_codex_attempt_processes(output_message_path: Path) -> list[int]:
    needle = str(output_message_path).encode("utf-8")
    current_pid = os.getpid()
    terminated: list[int] = []
    proc_root = Path("/proc")
    if not proc_root.exists():
        return terminated

    for proc_path in proc_root.iterdir():
        if not proc_path.name.isdigit():
            continue
        pid = int(proc_path.name)
        if pid == current_pid:
            continue
        try:
            cmdline = (proc_path / "cmdline").read_bytes()
        except OSError:
            continue
        if needle not in cmdline:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            continue
        terminated.append(pid)

    if not terminated:
        return terminated

    time.sleep(0.2)
    for pid in terminated:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            continue
    return terminated


def _write_output_from_final_message(output_message_path: Path, output_json_path: Path) -> bool:
    payload = _load_json_object_from_final_message(output_message_path)
    if payload is None:
        return False
    write_json_file(output_json_path, payload)
    return True


def _load_json_object_from_final_message(output_message_path: Path) -> dict[str, Any] | None:
    if not output_message_path.exists():
        return None
    text = output_message_path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    for candidate in _final_message_json_candidates(text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _final_message_json_candidates(text: str) -> list[str]:
    candidates = [text]
    candidates.extend(match.group(1).strip() for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL))
    return candidates
