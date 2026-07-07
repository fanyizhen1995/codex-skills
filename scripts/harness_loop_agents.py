#!/usr/bin/env python3
import json
import os
import re
import signal
import subprocess
import time
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
