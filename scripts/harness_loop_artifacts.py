#!/usr/bin/env python3
import os
import signal
import subprocess
import time
from pathlib import Path

try:
    from scripts.harness_loop_contracts import (
        validate_scenario_command_result_payload,
        write_json_file,
    )
except ModuleNotFoundError:  # pragma: no cover
    from harness_loop_contracts import (  # type: ignore[no-redef]
        validate_scenario_command_result_payload,
        write_json_file,
    )


def run_scenario_commands(
    repo_root: Path,
    run_dir: Path,
    commands: list[str],
    timeout_seconds: int,
) -> Path:
    evidence_dir = run_dir / "scenario-commands"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, command in enumerate(commands, start=1):
        stdout_path = evidence_dir / f"command-{index}.stdout.log"
        stderr_path = evidence_dir / f"command-{index}.stderr.log"
        started = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=repo_root,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            exit_code = process.returncode
            status = "pass" if exit_code == 0 else "fail"
        except subprocess.TimeoutExpired:
            _kill_process_group(process)
            stdout, stderr = process.communicate()
            exit_code = 124
            status = "timeout"

        stdout = _decode_timeout_stream(stdout)
        stderr = _decode_timeout_stream(stderr)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        payload = {
            "command": command,
            "cwd": str(repo_root),
            "exit_code": exit_code,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "duration_seconds": int(time.monotonic() - started),
            "status": status,
        }
        validate_scenario_command_result_payload(payload)
        results.append(payload)

    manifest = {
        "status": "pass" if all(result["status"] == "pass" for result in results) else "fail",
        "results": results,
    }
    return write_json_file(run_dir / "scenario-command-results.json", manifest)


def _kill_process_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        try:
            process.kill()
        except OSError:
            pass


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
