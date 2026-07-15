#!/usr/bin/env python3
"""Compatibility CLI wrapper for the unified SQLite Loop Supervisor."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping


if __package__ in {None, ""}:  # Keep ``python scripts/...`` compatible.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.harness_loop_supervisor_state import build_supervisor_state
from scripts.loop_supervisor.reconciler import reconcile_once
from scripts.loop_supervisor.store import SupervisorStore


@dataclass(frozen=True)
class SupervisorConfig:
    project_root: Path
    mode: str = "once"
    watch_interval_seconds: int = 30
    include_worktrees: bool = True
    dry_run: bool = False


def run_supervisor_once(config: SupervisorConfig) -> dict[str, Any]:
    """Open the SQLite store and run one bounded reconciliation tick."""
    root = Path(config.project_root).resolve()
    with SupervisorStore.open(root) as store:
        store.migrate()
        reconciled = reconcile_once(
            root,
            store,
            shadow=config.dry_run,
            include_worktrees=config.include_worktrees,
        )
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


def _print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), indent=2, ensure_ascii=False, sort_keys=True))


def _watch_error_state(config: SupervisorConfig, error: Exception) -> dict[str, Any]:
    summary = " ".join(str(error).split())[:500]
    error_payload = {"class": type(error).__name__, "summary": summary}
    fallback: dict[str, Any] = {
        "schema_version": 1,
        "project_root": str(config.project_root),
        "mode": "watch",
        "status": "error",
        "error": error_payload,
    }
    try:
        state = build_supervisor_state(
            config.project_root,
            mode="watch",
            service_health={},
            run_summary={
                "active": 0,
                "blocked": 0,
                "continuation_candidates": 0,
                "needs_user_decision": 0,
            },
            failure_summary={"open_failure_keys": 1},
            last_decision=None,
            watch_interval_seconds=config.watch_interval_seconds,
        )
        state.update({"status": "error", "error": error_payload})
        state_path = (
            config.project_root / ".codex" / "supervisor" / "supervisor-state.json"
        )
        with state_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return state
    except Exception as status_error:
        fallback["record_error"] = {
            "class": type(status_error).__name__,
            "summary": " ".join(str(status_error).split())[:200],
        }
        return fallback


def main(argv: list[str] | None = None) -> int:
    print(
        "deprecated: use python3 -m scripts.loop_supervisor.cli watch|once",
        file=sys.stderr,
    )
    parser = argparse.ArgumentParser(
        description="Run the SQLite Loop Supervisor once or in watch mode."
    )
    parser.add_argument("--project-root", default=".")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch", action="store_true")
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
    args = parser.parse_args(argv)

    config = SupervisorConfig(
        project_root=Path(args.project_root),
        mode="watch" if args.watch else "once",
        watch_interval_seconds=args.interval_seconds,
        include_worktrees=args.include_worktrees,
        dry_run=args.dry_run,
    )
    tick = 0
    while True:
        tick += 1
        try:
            state = run_supervisor_once(config)
        except Exception as error:
            if not args.watch:
                raise
            state = _watch_error_state(config, error)
        _print_json(state)
        if not args.watch or (args.max_ticks and tick >= args.max_ticks):
            return 0
        time.sleep(max(args.interval_seconds, 1))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
