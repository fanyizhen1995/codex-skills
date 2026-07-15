"""Canonical command line interface for the unified Loop Supervisor."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Mapping

from scripts.harness_loop_supervisor import (
    SupervisorConfig,
    _watch_error_state,
    run_supervisor_once,
)

from .migration import cleanup_legacy_runtime, migrate_jsonl, shadow_compare
from .store import SupervisorStore
from .worker import clear_stop_request, worker_watch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the unified Loop Supervisor.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    once = subparsers.add_parser("once", help="Run one reconciliation tick.")
    _add_supervisor_arguments(once)

    watch = subparsers.add_parser("watch", help="Run reconciliation continuously.")
    _add_supervisor_arguments(watch)
    watch.add_argument("--interval-seconds", type=int, default=30)
    watch.add_argument("--max-ticks", type=int, default=0, help=argparse.SUPPRESS)

    worker = subparsers.add_parser("worker", help="Lease and execute bounded actions.")
    worker.add_argument("--project-root", default=".")
    worker.add_argument("--worker-id", default="worker-01")
    worker.add_argument("--poll-seconds", type=float, default=2.0)

    status = subparsers.add_parser("status", help="Print queue and control-store status.")
    status.add_argument("--project-root", default=".")

    health = subparsers.add_parser("health", help="Check control-store integrity and workers.")
    health.add_argument("--project-root", default=".")

    migrate = subparsers.add_parser("migrate", help="Compact retained JSONL into SQLite.")
    migrate.add_argument("--project-root", default=".")
    migrate.add_argument("--dry-run", action="store_true")
    migrate.add_argument("--cleanup-legacy", action="store_true")

    compare = subparsers.add_parser(
        "shadow-compare", help="Compare retained outcomes with registry actions."
    )
    compare.add_argument("--project-root", default=".")

    rebuild = subparsers.add_parser("rebuild-db", help="Rebuild SQLite from retained artifacts.")
    rebuild.add_argument("--project-root", default=".")
    rebuild.add_argument("--confirm", action="store_true")

    retention = subparsers.add_parser("retention", help="Compact expired operational detail.")
    retention.add_argument("--project-root", default=".")
    retention.add_argument("--retention-days", type=int, default=90)
    return parser


def _add_supervisor_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", default=".")
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    if args.command in {"once", "watch"}:
        return _run_supervisor(root, args)
    if args.command == "worker":
        clear_stop_request()
        worker_watch(root, args.worker_id, args.poll_seconds)
        return 0
    if args.command == "status":
        _print_json(_status(root))
        return 0
    if args.command == "health":
        payload = _health(root)
        _print_json(payload)
        return 0 if payload["status"] == "healthy" else 1
    if args.command == "migrate":
        if args.dry_run and args.cleanup_legacy:
            raise SystemExit("--cleanup-legacy cannot be combined with --dry-run")
        with SupervisorStore.open(root) as store:
            store.migrate()
            report = migrate_jsonl(root, store, dry_run=args.dry_run)
            payload = report.as_dict()
            if args.cleanup_legacy:
                comparison = shadow_compare(root, store)
                payload["shadow_comparison"] = comparison.as_dict()
                payload["removed_paths"] = list(
                    cleanup_legacy_runtime(root, report, comparison)
                )
        _print_json(payload)
        return 0
    if args.command == "shadow-compare":
        with SupervisorStore.open(root) as store:
            store.migrate()
            report = shadow_compare(root, store)
        _print_json(report.as_dict())
        return 0 if report.passed else 1
    if args.command == "rebuild-db":
        if not args.confirm:
            print("rebuild-db requires --confirm and stopped Supervisor processes", file=sys.stderr)
            return 2
        payload = _rebuild_db(root)
        _print_json(payload)
        return 0
    if args.command == "retention":
        with SupervisorStore.open(root) as store:
            store.migrate()
            deleted = store.compact_retention(retention_days=args.retention_days)
        _print_json({"status": "completed", "deleted": deleted})
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


def _run_supervisor(root: Path, args: argparse.Namespace) -> int:
    watching = args.command == "watch"
    interval = args.interval_seconds if watching else 30
    config = SupervisorConfig(
        project_root=root,
        mode="watch" if watching else "once",
        watch_interval_seconds=interval,
        include_worktrees=args.include_worktrees,
        dry_run=args.dry_run,
    )
    tick = 0
    while True:
        tick += 1
        try:
            payload = run_supervisor_once(config)
        except Exception as error:
            if not watching:
                raise
            payload = _watch_error_state(config, error)
        _print_json(payload)
        if not watching or (args.max_ticks and tick >= args.max_ticks):
            return 0
        time.sleep(max(interval, 1))


def _status(root: Path) -> dict[str, Any]:
    with SupervisorStore.open(root) as store:
        store.migrate()
        counts = {
            table: store.count(table)
            for table in (
                "runs",
                "actions",
                "action_attempts",
                "failures",
                "reviews",
                "user_decisions",
                "services",
            )
        }
        workers = store.fetch_all("workers")
        integrity = store.database_integrity_ok()
    return {
        "status": "healthy" if integrity else "unhealthy",
        "project_root": str(root),
        "database": str(root / ".codex/supervisor/supervisor.db"),
        "counts": counts,
        "workers": workers,
    }


def _health(root: Path) -> dict[str, Any]:
    with SupervisorStore.open(root) as store:
        store.migrate()
        integrity = store.database_integrity_ok()
        workers = store.fetch_all("workers")
        journal_mode = str(store.pragma("journal_mode"))
        foreign_keys = int(store.pragma("foreign_keys"))
    healthy = integrity and journal_mode.lower() == "wal" and foreign_keys == 1
    return {
        "status": "healthy" if healthy else "unhealthy",
        "database_integrity": integrity,
        "journal_mode": journal_mode,
        "foreign_keys": foreign_keys,
        "workers": workers,
    }


def _rebuild_db(root: Path) -> dict[str, Any]:
    supervisor = root / ".codex" / "supervisor"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = root.parent / f".{root.name}-supervisor-snapshots" / f"db-rebuild-{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    moved: list[str] = []
    for name in ("supervisor.db", "supervisor.db-wal", "supervisor.db-shm"):
        source = supervisor / name
        if source.exists() and not source.is_symlink():
            shutil.move(source, backup / name)
            moved.append(name)
    with SupervisorStore.open(root) as store:
        store.migrate()
        report = migrate_jsonl(root, store, dry_run=False)
    return {
        "status": "completed",
        "backup_path": backup.as_posix(),
        "moved_database_files": moved,
        "migration": report.as_dict(),
    }


def _print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), sort_keys=True, indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
