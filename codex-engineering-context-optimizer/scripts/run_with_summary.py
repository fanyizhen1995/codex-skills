#!/usr/bin/env python3
"""Run a command, save full output, and print a compact engineering summary."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


KEY_PATTERNS = [
    r"\bFAILED\b",
    r"\bFAIL\b",
    r"\bERROR\b",
    r"\bError\b",
    r"\bTraceback\b",
    r"\bAssertionError\b",
    r"\bpanic\b",
    r"\bsegmentation fault\b",
    r"\bsegfault\b",
    r"\bundefined reference\b",
    r"\bfatal:",
    r"\bException\b",
    r"\bTimeout\b",
    r"\btimeout\b",
    r"\bx509:",
    r"\bpermission denied\b",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory for the command.")
    parser.add_argument("--label", default="command", help="Short label used in artifact filenames.")
    parser.add_argument(
        "--artifact-dir",
        default=None,
        help="Directory for full logs. Defaults to <cwd>/.codex/artifacts/context-optimizer.",
    )
    parser.add_argument("--max-key-lines", type=int, default=80)
    parser.add_argument("--tail-lines", type=int, default=80)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    return parser.parse_args()


def normalize_command(command: list[str]) -> list[str]:
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("missing command; pass it after --")
    return command


def safe_label(label: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", label.strip())
    return value.strip("-") or "command"


def line_stats(text: str) -> tuple[int, int]:
    if not text:
        return 0, 0
    return len(text), text.count("\n") + (0 if text.endswith("\n") else 1)


def key_lines(text: str, limit: int) -> list[str]:
    patterns = [re.compile(p) for p in KEY_PATTERNS]
    results: list[str] = []
    for idx, line in enumerate(text.splitlines(), 1):
        if any(p.search(line) for p in patterns):
            results.append(f"{idx}: {line[:500]}")
            if len(results) >= limit:
                break
    return results


def tail(text: str, limit: int) -> list[str]:
    if limit <= 0:
        return []
    lines = text.splitlines()
    return lines[-limit:]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def main() -> int:
    args = parse_args()
    command = normalize_command(args.command)
    cwd = Path(args.cwd).expanduser().resolve()
    artifact_dir = (
        Path(args.artifact_dir).expanduser()
        if args.artifact_dir
        else cwd / ".codex" / "artifacts" / "context-optimizer"
    )

    start = time.time()
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        errors="replace",
    )
    duration_ms = int((time.time() - start) * 1000)

    command_text = shlex.join(command)
    digest = hashlib.sha256(
        f"{time.time_ns()}\0{cwd}\0{command_text}".encode("utf-8")
    ).hexdigest()[:16]
    stem = f"{time.strftime('%Y%m%d-%H%M%S')}-{safe_label(args.label)}-{digest}"
    stdout_path = artifact_dir / f"{stem}.stdout.log"
    stderr_path = artifact_dir / f"{stem}.stderr.log"
    meta_path = artifact_dir / f"{stem}.meta.txt"

    write_text(stdout_path, completed.stdout)
    write_text(stderr_path, completed.stderr)
    write_text(
        meta_path,
        "\n".join(
            [
                f"command: {command_text}",
                f"cwd: {cwd}",
                f"exit_code: {completed.returncode}",
                f"duration_ms: {duration_ms}",
                f"stdout_path: {stdout_path}",
                f"stderr_path: {stderr_path}",
            ]
        )
        + "\n",
    )

    stdout_chars, stdout_lines = line_stats(completed.stdout)
    stderr_chars, stderr_lines = line_stats(completed.stderr)
    combined = completed.stdout + "\n" + completed.stderr
    keys = key_lines(combined, args.max_key_lines)

    print("# Command Summary")
    print()
    print(f"- command: `{command_text}`")
    print(f"- cwd: `{cwd}`")
    print(f"- exit_code: `{completed.returncode}`")
    print(f"- duration_ms: `{duration_ms}`")
    print(f"- stdout: `{stdout_lines}` lines, `{stdout_chars}` chars -> `{stdout_path}`")
    print(f"- stderr: `{stderr_lines}` lines, `{stderr_chars}` chars -> `{stderr_path}`")
    print(f"- metadata: `{meta_path}`")
    print()

    if keys:
        print("## Key Lines")
        for line in keys:
            print(line)
        print()
    else:
        print("## Key Lines")
        print("No obvious failure/error lines matched the built-in patterns.")
        print()

    print("## Tail")
    print("### stdout")
    for line in tail(completed.stdout, args.tail_lines):
        print(line[:500])
    print("### stderr")
    for line in tail(completed.stderr, args.tail_lines):
        print(line[:500])

    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
