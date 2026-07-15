"""Canonical command line interface for the unified Loop Supervisor."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
from typing import Any, Mapping
from uuid import uuid4

from scripts.harness_loop_supervisor import (
    SupervisorConfig,
    _watch_error_state,
    run_supervisor_once,
)
from scripts.harness_loop_runtime_lock import (
    RunLockBusy,
    acquire_repository_mutation_lock,
    acquire_runtime_database_maintenance_lock,
)

from .migration import (
    MigrationValidationError,
    cleanup_legacy_runtime,
    migrate_jsonl,
    shadow_compare,
)
from .reconciler import _project_reconcile_lock
from .store import SupervisorStore
from .worker import clear_stop_request, worker_watch


_UNSET = object()


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
        store_factory = _in_memory_store if args.dry_run else SupervisorStore.open
        with store_factory(root) as store:
            store.migrate()
            report = migrate_jsonl(root, store, dry_run=args.dry_run)
            payload = report.as_dict()
            if args.cleanup_legacy:
                comparison = shadow_compare(root, store)
                payload["shadow_comparison"] = comparison.as_dict()
                payload["removed_paths"] = list(
                    cleanup_legacy_runtime(root, report, comparison, store=store)
                )
        _print_json(payload)
        return 0
    if args.command == "shadow-compare":
        with _in_memory_store(root) as store:
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


def _in_memory_store(root: Path) -> SupervisorStore:
    connection = sqlite3.connect(
        ":memory:", isolation_level=None, check_same_thread=False
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    return SupervisorStore(Path(root).resolve(), connection, None)


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
    try:
        with acquire_runtime_database_maintenance_lock(
            root, owner=f"supervisor-db-rebuild:{os.getpid()}"
        ), _project_reconcile_lock(root), acquire_repository_mutation_lock(
            root, owner=f"supervisor-db-rebuild:{os.getpid()}"
        ):
            return _rebuild_db_locked(root)
    except RunLockBusy as exc:
        raise MigrationValidationError(
            f"rebuild requires quiescence; runtime lock is held: {exc}"
        ) from exc


def _rebuild_db_locked(root: Path) -> dict[str, Any]:
    _assert_rebuild_quiescent(root)
    supervisor = root / ".codex" / "supervisor"
    if supervisor.is_symlink():
        raise MigrationValidationError("Supervisor runtime directory is a symlink")
    supervisor.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = root.parent / f".{root.name}-supervisor-snapshots" / f"db-rebuild-{stamp}"
    replacement = supervisor / f".supervisor.db.rebuild-{uuid4().hex}"
    database = supervisor / "supervisor.db"
    database_names = ("supervisor.db", "supervisor.db-wal", "supervisor.db-shm")
    rollback_database = backup / "rollback-supervisor.db"
    backed_up: list[str] = []
    swapped = False
    report = None
    try:
        with _store_at(root, replacement) as store:
            store.migrate()
            report = migrate_jsonl(root, store, dry_run=False)
            if not report.validated or not store.database_integrity_ok():
                raise MigrationValidationError("replacement database validation failed")
            store._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            store._connection.execute("PRAGMA journal_mode=DELETE")

        live_database_present = database.exists()
        if database.is_symlink() or (
            live_database_present and not database.is_file()
        ):
            raise MigrationValidationError(f"live database path is unsafe: {database}")
        if not live_database_present and any(
            (supervisor / name).exists() for name in database_names[1:]
        ):
            raise MigrationValidationError(
                "live database is missing but orphaned SQLite sidecars remain"
            )
        if live_database_present:
            _assert_no_live_wal_read_snapshot(database)
        backup.mkdir(parents=True, exist_ok=False)
        for name in database_names:
            source = supervisor / name
            if source.is_symlink():
                raise MigrationValidationError(f"database path is a symlink: {source}")
            if source.is_file():
                shutil.copy2(source, backup / name)
                backed_up.append(name)
        if live_database_present:
            _checkpoint_and_validate_live_database(database)
            _copy_standalone_database(database, rollback_database)
        os.replace(replacement, database)
        swapped = True
        _validate_replacement_database(database)
    except BaseException:
        if rollback_database.is_file():
            restore = supervisor / f".supervisor.db.rollback-{uuid4().hex}"
            _copy_standalone_database(rollback_database, restore)
            os.replace(restore, database)
        elif swapped:
            database.unlink(missing_ok=True)
        raise
    finally:
        for suffix in ("", "-wal", "-shm"):
            Path(str(replacement) + suffix).unlink(missing_ok=True)

    if report is None:
        raise AssertionError("replacement migration report was not created")
    return {
        "status": "completed",
        "backup_path": backup.as_posix(),
        "backed_up_database_files": backed_up,
        "rollback_database": (
            rollback_database.as_posix() if rollback_database.is_file() else ""
        ),
        "migration": report.as_dict(),
    }


def _store_at(root: Path, database: Path) -> SupervisorStore:
    connection = sqlite3.connect(
        database, timeout=5, isolation_level=None, check_same_thread=False
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    return SupervisorStore(Path(root).resolve(), connection, None)


def _assert_supported_wal_lock_runtime(
    *,
    platform: str | None = None,
    os_name: str | None = None,
    lockf: object = _UNSET,
) -> None:
    actual_platform = sys.platform if platform is None else platform
    actual_os_name = os.name if os_name is None else os_name
    actual_lockf = getattr(fcntl, "lockf", None) if lockf is _UNSET else lockf
    if actual_platform != "linux":
        raise MigrationValidationError(
            "live database rebuild requires Linux SQLite Unix-VFS lock semantics"
        )
    if actual_os_name != "posix":
        raise MigrationValidationError(
            "live database rebuild requires a POSIX runtime"
        )
    if not callable(actual_lockf):
        raise MigrationValidationError(
            "live database rebuild requires fcntl.lockf byte-range locking"
        )


def _assert_no_live_wal_read_snapshot(database: Path) -> None:
    _assert_supported_wal_lock_runtime()
    shm = Path(str(database) + "-shm")
    if not shm.exists():
        return
    if shm.is_symlink() or not shm.is_file():
        raise MigrationValidationError(f"unsafe SQLite shared-memory path: {shm}")
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(shm, flags)
    except FileNotFoundError:
        return
    try:
        # This advisory preflight avoids mutating SHM for a known reader. The
        # SQLite checkpoint result below remains the authoritative safety gate.
        for offset in range(123, 128):
            try:
                fcntl.lockf(
                    descriptor,
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                    1,
                    offset,
                    os.SEEK_SET,
                )
            except BlockingIOError as exc:
                raise MigrationValidationError(
                    "rebuild checkpoint is busy; a live SQLite read snapshot is active"
                ) from exc
            else:
                fcntl.lockf(
                    descriptor,
                    fcntl.LOCK_UN,
                    1,
                    offset,
                    os.SEEK_SET,
                )
    finally:
        os.close(descriptor)


def _copy_standalone_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    with destination.open("rb") as handle:
        os.fsync(handle.fileno())
    _validate_standalone_database(destination)


def _validate_standalone_database(database: Path) -> None:
    if database.is_symlink() or not database.is_file():
        raise MigrationValidationError(f"standalone database is unsafe: {database}")
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
    finally:
        connection.close()
    if (
        integrity is None
        or str(integrity[0]).lower() != "ok"
        or journal_mode.lower() != "delete"
    ):
        raise MigrationValidationError(
            f"standalone database validation failed: {database}"
        )


def _checkpoint_and_validate_live_database(database: Path) -> None:
    if not database.is_file() or database.is_symlink():
        raise MigrationValidationError(f"live database is missing or unsafe: {database}")
    connection = sqlite3.connect(database, timeout=0, isolation_level=None)
    try:
        connection.execute("PRAGMA busy_timeout=0")
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        if journal_mode.lower() == "wal":
            checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            # Byte-lock probing is only an early rejection optimization. SQLite
            # owns the authoritative determination that every WAL frame is safe.
            if checkpoint is None or tuple(int(value) for value in checkpoint) != (0, 0, 0):
                raise MigrationValidationError(
                    f"rebuild checkpoint did not truncate cleanly: {checkpoint}"
                )
        elif journal_mode.lower() != "delete":
            raise MigrationValidationError(
                f"unsupported live database journal mode: {journal_mode}"
            )
        standalone_mode = str(
            connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        )
        if standalone_mode.lower() != "delete":
            raise MigrationValidationError(
                f"live database did not become standalone: {standalone_mode}"
            )
    except sqlite3.OperationalError as exc:
        raise MigrationValidationError(
            f"rebuild checkpoint is busy or failed: {exc}"
        ) from exc
    finally:
        connection.close()

    sidecars = (Path(str(database) + "-wal"), Path(str(database) + "-shm"))
    if any(path.exists() for path in sidecars):
        raise MigrationValidationError(
            "live database is not standalone after checkpoint; SQLite sidecars remain"
        )
    _validate_standalone_database(database)


def _assert_rebuild_quiescent(root: Path) -> None:
    state_path = root / ".codex" / "supervisor" / "supervisor-state.json"
    if state_path.is_symlink():
        raise MigrationValidationError(
            "rebuild requires quiescence; canonical Supervisor state is a symlink"
        )
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            heartbeat = _parse_timestamp(str(state["last_heartbeat_at"]))
        except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
            raise MigrationValidationError(
                "rebuild requires quiescence; canonical Supervisor state is unreadable"
            ) from exc
        if heartbeat >= datetime.now(timezone.utc) - timedelta(seconds=120):
            raise MigrationValidationError(
                "rebuild requires quiescence; recent canonical Supervisor heartbeat"
            )

    database = root / ".codex" / "supervisor" / "supervisor.db"
    if database.is_file() and not database.is_symlink():
        _assert_no_live_wal_read_snapshot(database)
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if "actions" in tables:
                active = connection.execute(
                    "SELECT action_id FROM actions WHERE status IN ('leased', 'running') LIMIT 1"
                ).fetchone()
                if active is not None:
                    raise MigrationValidationError(
                        f"rebuild requires quiescence; active action {active['action_id']}"
                    )
            if "workers" in tables:
                cutoff = datetime.now(timezone.utc) - timedelta(seconds=120)
                for row in connection.execute("SELECT worker_id, heartbeat_at FROM workers"):
                    heartbeat = _parse_timestamp(str(row["heartbeat_at"]))
                    if heartbeat >= cutoff:
                        raise MigrationValidationError(
                            "rebuild requires quiescence; recent Worker heartbeat "
                            f"from {row['worker_id']}"
                        )
            if "services" in tables:
                for row in connection.execute(
                    "SELECT service_id, process_id FROM services WHERE process_id IS NOT NULL"
                ):
                    service_id = str(row["service_id"])
                    if "supervisor" in service_id and _process_is_alive(int(row["process_id"])):
                        raise MigrationValidationError(
                            "rebuild requires quiescence; live Supervisor/Worker process "
                            f"{row['process_id']} ({service_id})"
                        )
        finally:
            connection.close()

    runtime_dir = root / ".codex" / "service-runtime"
    if runtime_dir.is_dir() and not runtime_dir.is_symlink():
        for path in runtime_dir.glob("*supervisor*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                process_id = int(payload.get("pid") or payload.get("process_id") or 0)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if process_id > 0 and _process_is_alive(process_id):
                raise MigrationValidationError(
                    f"rebuild requires quiescence; live process {process_id} from {path}"
                )

    lock_dir = root / ".codex" / "loop-locks"
    if lock_dir.is_dir() and not lock_dir.is_symlink():
        for path in lock_dir.glob("*.lock"):
            if path.name in {
                "repository-mutation.lock",
                "runtime-database-maintenance.lock",
            }:
                continue
            if path.is_symlink() or not path.is_file():
                raise MigrationValidationError(f"unsafe loop lock path: {path}")
            with path.open("rb") as handle:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise MigrationValidationError(
                        f"rebuild requires quiescence; held loop lock {path}"
                    ) from exc
                finally:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass


def _validate_replacement_database(database: Path) -> None:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        row = connection.execute("PRAGMA quick_check").fetchone()
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    finally:
        connection.close()
    if row is None or str(row[0]).lower() != "ok" or version <= 0:
        raise MigrationValidationError("atomic replacement database validation failed")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MigrationValidationError(f"invalid runtime heartbeat timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _process_is_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), sort_keys=True, indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
