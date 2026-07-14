#!/usr/bin/env python3
"""Compatibility CLI wrapper for the unified SQLite Loop Supervisor."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping


if __package__ in {None, ""}:  # Keep ``python scripts/...`` compatible.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.harness_loop_supervisor_state import build_supervisor_state, utc_now_iso
from scripts.loop_supervisor.reconciler import reconcile_once
from scripts.loop_supervisor.store import SupervisorStore


ALLOWED_RESTART_SESSIONS = {
    "personal-wiki-crawler-backend": (
        "cd {project_root}/personal-wiki/apps/crawler_workbench/backend && "
        "PYTHONPATH=$PWD PW_WORKBENCH_REPO_ROOT={project_root} "
        "python3 -m uvicorn crawler_workbench.main:app --host 0.0.0.0 --port 8765"
    ),
    "personal-wiki-crawler-frontend": (
        "cd {project_root}/personal-wiki/apps/crawler_workbench/frontend && "
        'if ! command -v npm >/dev/null 2>&1 && [ -s "$HOME/.nvm/nvm.sh" ]; '
        'then . "$HOME/.nvm/nvm.sh"; fi && '
        "npm run dev -- --host 0.0.0.0 --port 5173"
    ),
    "loop-dashboard": (
        "cd {project_root} && PYTHONPATH=apps/loop_dashboard/backend "
        "python3 -m uvicorn loop_dashboard.main:app --host 0.0.0.0 --port 8766"
    ),
    "loop-auto-resume": (
        "cd {project_root} && python3 scripts/harness_loop_auto_resume.py "
        "--project-root {project_root} --watch --interval-seconds 30"
    ),
}
SERVICE_CODE_PATHS = {
    "crawler-backend": (
        "personal-wiki/apps/crawler_workbench/backend/crawler_workbench",
        "personal-wiki/apps/crawler_workbench/backend/pyproject.toml",
    ),
    "crawler-frontend": (
        "personal-wiki/apps/crawler_workbench/frontend/src",
        "personal-wiki/apps/crawler_workbench/frontend/package.json",
        "personal-wiki/apps/crawler_workbench/frontend/vite.config.ts",
    ),
    "loop-dashboard": (
        "apps/loop_dashboard/backend/loop_dashboard",
        "apps/loop_dashboard/frontend/app.js",
        "apps/loop_dashboard/frontend/index.html",
        "apps/loop_dashboard/frontend/styles.css",
    ),
    "loop-auto-resume": (
        "scripts/harness_loop_auto_resume.py",
        "scripts/harness_loop_runtime_lock.py",
        "scripts/harness_loop_orchestrator.py",
        "scripts/harness_loop_contracts.py",
        "scripts/harness_loop_auditor.py",
    ),
}


@dataclass(frozen=True)
class SupervisorConfig:
    project_root: Path
    mode: str = "once"
    watch_interval_seconds: int = 30
    include_worktrees: bool = True
    dry_run: bool = False
    restart_services: bool = False
    create_continuations: bool = True


def run_supervisor_once(config: SupervisorConfig) -> dict[str, Any]:
    """Open the SQLite store and run one bounded reconciliation tick."""
    root = Path(config.project_root).resolve()
    with SupervisorStore.open(root) as store:
        store.migrate()
        reconciled = reconcile_once(root, store, shadow=config.dry_run)
        open_decisions = [
            row
            for row in store.fetch_all("user_decisions")
            if row.get("status") == "open"
        ]
        open_failures = [
            row
            for row in store.fetch_all("failures")
            if row.get("resolution") == "open"
        ]

    continuation_count = sum(
        action.action_type.value == "create_continuation"
        for action in reconciled.queued_actions
    )
    run_summary = {
        "active": len(reconciled.queued_actions) - continuation_count,
        "blocked": sum(row.get("scope") == "global" for row in open_decisions),
        "continuation_candidates": continuation_count,
        "needs_user_decision": len(open_decisions),
    }
    state = build_supervisor_state(
        root,
        mode=config.mode,
        service_health={},
        run_summary=run_summary,
        failure_summary={"open_failure_keys": len(open_failures)},
        last_decision=(
            dict(reconciled.open_user_decisions[-1])
            if reconciled.open_user_decisions
            else None
        ),
        watch_interval_seconds=config.watch_interval_seconds,
    )
    return {**state, **reconciled.as_dict(), "run_summary": run_summary}


def restart_service(config: SupervisorConfig, tmux_session: str) -> dict[str, Any]:
    """Retain the allowlisted one-shot restart compatibility command."""
    if tmux_session not in ALLOWED_RESTART_SESSIONS:
        raise ValueError(f"service restart session is not allowlisted: {tmux_session}")
    if config.dry_run:
        return {
            "session": tmux_session,
            "status": "dry_run",
            "summary": "restart skipped because supervisor is in dry-run mode",
        }
    if not config.restart_services:
        return {
            "session": tmux_session,
            "status": "skipped",
            "summary": "service restart disabled",
        }

    command = ALLOWED_RESTART_SESSIONS[tmux_session].format(
        project_root=Path(config.project_root)
    )
    existing, _ = _tmux_has_session(tmux_session)
    if existing:
        return {
            "session": tmux_session,
            "status": "skipped",
            "summary": "tmux session already exists",
        }
    result = subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session, command],
        cwd=Path(config.project_root),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"tmux restart failed for {tmux_session}: {result.stderr or result.stdout}"
        )
    return {
        "session": tmux_session,
        "status": "started",
        "summary": "tmux session started from allowlist",
    }


def write_service_runtime_metadata(
    project_root: Path,
    *,
    service_name: str,
    command: str,
    host: str,
    port: int | None,
    tmux_session: str,
    cwd: Path | None = None,
    pid: int | None = None,
) -> dict[str, Any]:
    """Retain service startup metadata used by the existing launch commands."""
    root = Path(project_root)
    service_cwd = Path(cwd) if cwd is not None else root
    runtime_path = (
        root / ".codex" / "service-runtime" / f"{_safe_slug(service_name)}.json"
    )
    git_head = _git_head(service_cwd)
    metadata = {
        "schema_version": 1,
        "service": service_name,
        "tmux_session": tmux_session,
        "pid": int(pid if pid is not None else os.getpid()),
        "cwd": str(service_cwd),
        "command": command,
        "host": host,
        "port": port,
        "repo_root": str(root),
        "git_head": git_head,
        "origin_main": git_head,
        "started_at": utc_now_iso(),
        "config_fingerprint": _service_config_fingerprint(
            service_name=service_name,
            command=command,
            host=host,
            port=port,
            tmux_session=tmux_session,
            cwd=service_cwd,
        ),
        "code_fingerprint": _service_code_fingerprint(root, service_name),
        "runtime_metadata_path": _relative_to_repo(root, runtime_path),
    }
    _write_json(runtime_path, metadata)
    return metadata


def _tmux_has_session(session: str) -> tuple[bool, str]:
    if not session:
        return False, "tmux session not configured"
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except FileNotFoundError:
        return False, "tmux command unavailable"
    except subprocess.TimeoutExpired:
        return False, f"tmux has-session timed out for {session}"
    if result.returncode == 0:
        return True, "tmux session exists"
    return False, (
        f"tmux session missing: {session}: {result.stderr or result.stdout}"
    ).strip()


def _git_head(cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(cwd),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git command failed: git executable not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("git command failed: git rev-parse HEAD timed out") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"git command failed: git rev-parse HEAD: {detail}")
    return result.stdout.strip()


def _service_code_fingerprint(project_root: Path, service_name: str) -> str:
    paths = SERVICE_CODE_PATHS.get(service_name)
    if not paths:
        raise RuntimeError(f"service code paths are not configured: {service_name}")
    files: list[Path] = []
    for relative in paths:
        path = Path(project_root) / relative
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and not any(
                    part
                    in {
                        "node_modules",
                        "dist",
                        "build",
                        "__pycache__",
                        ".pytest_cache",
                    }
                    for part in candidate.parts
                )
            )
    if not files:
        raise RuntimeError(f"service code files are missing: {service_name}")
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(str(path.relative_to(project_root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _service_config_fingerprint(
    *,
    service_name: str,
    command: str,
    host: str,
    port: int | None,
    tmux_session: str,
    cwd: Path,
) -> str:
    payload = {
        "service": service_name,
        "command": command,
        "host": host,
        "port": port,
        "tmux_session": tmux_session,
        "cwd": str(cwd),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")


def _relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "unknown"


def _print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), indent=2, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the SQLite Loop Supervisor once or in watch mode."
    )
    parser.add_argument("--project-root", default=".")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch", action="store_true")
    mode.add_argument("--write-service-runtime", metavar="SERVICE")
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--max-ticks", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--include-worktrees",
        dest="include_worktrees",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--no-include-worktrees", dest="include_worktrees", action="store_false"
    )
    parser.add_argument("--restart-services", action="store_true")
    parser.add_argument("--no-create-continuations", action="store_true")
    parser.add_argument("--service-command", default="")
    parser.add_argument("--service-host", default="127.0.0.1")
    parser.add_argument("--service-port", type=int, default=None)
    parser.add_argument("--service-tmux-session", default="")
    parser.add_argument("--service-cwd", default="")
    parser.add_argument("--service-pid", type=int, default=None)
    args = parser.parse_args(argv)

    project_root = Path(args.project_root)
    if args.write_service_runtime:
        if not args.service_command:
            parser.error("--write-service-runtime requires --service-command")
        if args.service_pid is None or args.service_pid <= 0:
            parser.error(
                "--write-service-runtime requires --service-pid for the long-running service process"
            )
        metadata = write_service_runtime_metadata(
            project_root,
            service_name=args.write_service_runtime,
            command=args.service_command,
            host=args.service_host,
            port=args.service_port,
            tmux_session=args.service_tmux_session or args.write_service_runtime,
            cwd=Path(args.service_cwd) if args.service_cwd else project_root,
            pid=args.service_pid,
        )
        _print_json(metadata)
        return 0

    config = SupervisorConfig(
        project_root=project_root,
        mode="watch" if args.watch else "once",
        watch_interval_seconds=args.interval_seconds,
        include_worktrees=args.include_worktrees,
        dry_run=args.dry_run,
        restart_services=args.restart_services,
        create_continuations=not args.no_create_continuations,
    )
    tick = 0
    while True:
        tick += 1
        _print_json(run_supervisor_once(config))
        if not args.watch or (args.max_ticks and tick >= args.max_ticks):
            return 0
        time.sleep(max(args.interval_seconds, 1))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
