#!/usr/bin/env python3
import hashlib
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

try:
    from scripts.harness_loop_contracts import (
        validate_artifact_hygiene_result_payload,
        validate_scenario_command_result_payload,
        write_json_file,
    )
except ModuleNotFoundError:  # pragma: no cover
    from harness_loop_contracts import (  # type: ignore[no-redef]
        validate_artifact_hygiene_result_payload,
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
            second_communicate_timeout = False
        except subprocess.TimeoutExpired as exc:
            _kill_process_group(process)
            second_communicate_timeout = False
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                second_communicate_timeout = True
                _close_process_pipes(process)
                try:
                    process.kill()
                except OSError:
                    pass
                stdout = exc.output
                stderr = exc.stderr
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
            "second_communicate_timeout": second_communicate_timeout,
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


def _close_process_pipes(process: subprocess.Popen) -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(process, stream_name, None)
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            pass


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_artifact_hygiene(
    repo_root: Path,
    run_dir: Path,
    artifact_paths: list[str],
    max_file_bytes: int = 5 * 1024 * 1024,
    max_total_bytes: int = 50 * 1024 * 1024,
) -> Path:
    scanned_paths: list[str] = []
    redacted_paths: list[str] = []
    omitted_paths: list[str] = []
    original_hashes: dict[str, str] = {}
    redaction_map: list[dict[str, str]] = []
    findings: list[dict[str, str]] = []
    redactions: list[dict[str, str]] = []
    total_bytes = 0

    resolved_repo_root = repo_root.resolve()
    for relative_path in artifact_paths:
        if _is_virtual_artifact_reference(relative_path):
            continue
        artifact_path, safe_relative_path, path_error = _resolve_safe_artifact_path(
            resolved_repo_root,
            relative_path,
        )
        if path_error:
            omitted_paths.append(relative_path)
            findings.append(
                {
                    "path": relative_path,
                    "severity": "error",
                    "message": path_error,
                }
            )
            continue

        assert artifact_path is not None
        assert safe_relative_path is not None
        if not artifact_path.exists() or not artifact_path.is_file():
            omitted_paths.append(relative_path)
            findings.append(
                {
                    "path": relative_path,
                    "severity": "error",
                    "message": "artifact missing",
                }
            )
            continue

        size = artifact_path.stat().st_size
        if size > max_file_bytes:
            omitted_paths.append(relative_path)
            findings.append(
                {
                    "path": relative_path,
                    "severity": "error",
                    "message": "artifact exceeds max_file_bytes",
                }
            )
            continue
        if total_bytes + size > max_total_bytes:
            omitted_paths.append(relative_path)
            findings.append(
                {
                    "path": relative_path,
                    "severity": "error",
                    "message": "artifact exceeds max_total_bytes",
                }
            )
            continue

        original_hash = _sha256(artifact_path)
        try:
            text = artifact_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            omitted_paths.append(relative_path)
            findings.append(
                {
                    "path": relative_path,
                    "severity": "error",
                    "message": "binary artifact omitted",
                }
            )
            continue
        if "\x00" in text:
            omitted_paths.append(relative_path)
            findings.append(
                {
                    "path": relative_path,
                    "severity": "error",
                    "message": "binary artifact omitted",
                }
            )
            continue

        redacted_text, rule_ids = _redact_sensitive_text(text)
        redacted_relative = ""
        redacted_path: Path | None = None
        if rule_ids:
            redacted_relative = f"{safe_relative_path}.redacted"
            redacted_path, redacted_error = _resolve_safe_redacted_output_path(
                resolved_repo_root,
                redacted_relative,
            )
            if redacted_error:
                omitted_paths.append(safe_relative_path)
                findings.append(
                    {
                        "path": safe_relative_path,
                        "severity": "error",
                        "message": redacted_error,
                    }
                )
                continue

        total_bytes += size
        scanned_paths.append(safe_relative_path)
        original_hashes[safe_relative_path] = original_hash
        if not rule_ids:
            continue

        assert redacted_path is not None
        redacted_path.parent.mkdir(parents=True, exist_ok=True)
        redacted_path.write_text(redacted_text, encoding="utf-8")
        redacted_hash = _sha256(redacted_path)
        redacted_paths.append(redacted_relative)
        for rule_id in rule_ids:
            redaction_map.append(
                {
                    "path": safe_relative_path,
                    "rule_id": rule_id,
                    "replacement": "[REDACTED]",
                }
            )
            redactions.append(
                {
                    "path": safe_relative_path,
                    "redacted_path": redacted_relative,
                    "rule_id": rule_id,
                    "original_sha256": original_hashes[safe_relative_path],
                    "redacted_sha256": redacted_hash,
                }
            )
        findings.append(
            {
                "path": safe_relative_path,
                "severity": "warning",
                "message": "sensitive text redacted",
            }
        )

    manifest_path = run_dir / "artifact-manifest.json"
    redaction_manifest_path = run_dir / "redaction-manifest.json"
    redaction_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    redaction_manifest_path.write_text(
        json.dumps({"redactions": redactions}, indent=2) + "\n",
        encoding="utf-8",
    )
    payload = {
        "status": "blocked" if omitted_paths else "redacted" if redacted_paths else "pass",
        "scanned_paths": scanned_paths,
        "redacted_paths": redacted_paths,
        "omitted_paths": omitted_paths,
        "manifest_path": str(manifest_path),
        "redaction_manifest_path": str(redaction_manifest_path),
        "original_hashes": original_hashes,
        "redaction_map": redaction_map,
        "findings": findings,
    }
    validate_artifact_hygiene_result_payload(payload)
    return write_json_file(manifest_path, payload)


def _is_virtual_artifact_reference(path_value: str) -> bool:
    return path_value.strip().startswith("embedded:")


def _resolve_safe_artifact_path(repo_root: Path, path_value: str) -> tuple[Path | None, str | None, str]:
    requested_path = Path(path_value)
    if requested_path.is_absolute():
        return None, None, "artifact path must be relative to repo_root"
    if ".." in requested_path.parts:
        return None, None, "artifact path must not contain parent directory segments"

    try:
        artifact_path = (repo_root / requested_path).resolve()
    except (OSError, RuntimeError):
        return None, None, "artifact path could not be resolved"

    try:
        safe_relative_path = artifact_path.relative_to(repo_root).as_posix()
    except ValueError:
        return None, None, "artifact path escapes repo_root"
    return artifact_path, safe_relative_path, ""


def _resolve_safe_redacted_output_path(repo_root: Path, redacted_relative: str) -> tuple[Path | None, str]:
    redacted_path = repo_root / redacted_relative
    if redacted_path.is_symlink():
        return None, "redacted output path is a symlink"
    try:
        redacted_path.resolve().relative_to(repo_root)
    except (OSError, RuntimeError, ValueError):
        return None, "redacted output path escapes repo_root"
    return redacted_path, ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_AUTHORIZATION_RE = re.compile(r"authorization\s*:", re.IGNORECASE)
_SIMPLE_AUTHORIZATION_RE = re.compile(r"^(\s*authorization\s*:\s*).*$", re.IGNORECASE)
_TOKEN_OR_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|bearer[_-]?token|secret|password|credential)\b\s*[:=]"
)


def _redact_sensitive_text(text: str) -> tuple[str, list[str]]:
    rule_ids: list[str] = []
    output_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        newline = line[len(content) :]
        simple_authorization = _SIMPLE_AUTHORIZATION_RE.match(content)
        if simple_authorization:
            output_lines.append(simple_authorization.group(1) + "[REDACTED]" + newline)
            rule_ids.append("authorization_header")
        elif _AUTHORIZATION_RE.search(content):
            output_lines.append("[REDACTED]" + newline)
            rule_ids.append("authorization_header")
        elif _TOKEN_OR_SECRET_ASSIGNMENT_RE.search(content):
            output_lines.append("[REDACTED]" + newline)
            rule_ids.append("token_or_secret")
        else:
            output_lines.append(line)
    return "".join(output_lines), sorted(set(rule_ids))
