from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.loop_supervisor import cli as supervisor_cli
from scripts.loop_supervisor.migration import (
    MigrationValidationError,
    cleanup_legacy_runtime,
    inventory_runtime,
    migrate_jsonl,
    shadow_compare,
)
from scripts.loop_supervisor.reconciler import reconcile_once
from scripts.loop_supervisor.store import SupervisorStore


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _decision(
    index: int,
    *,
    phase: str = "stopped_blocked",
    next_action: str = "unsupported",
    classification: str = "needs_user_decision",
    action: str = "request_user_decision",
    reason: str = "unsupported_state",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "decision_id": f"supervisor-{index:06d}",
        "run_id": "run-1",
        "repo_root": "/fixture",
        "run_policy": "autonomous_knowledge",
        "phase": phase,
        "next_action": next_action,
        "classification": classification,
        "action": action,
        "reason": reason,
        "created_at": (
            datetime(2026, 7, 14, tzinfo=timezone.utc) + timedelta(seconds=index)
        ).isoformat(timespec="microseconds"),
        "evidence_paths": [".codex/loop-runs/run-1/run.json"],
        "dry_run": False,
    }


def _open_store(root: Path) -> SupervisorStore:
    store = SupervisorStore.open(root)
    store.migrate()
    return store


def _seed_run(
    root: Path,
    run_id: str,
    *,
    previous_run_id: str = "",
    parent_counter: int,
    completed: list[str],
    phase: str = "stopped_budget",
    next_action: str = "none",
) -> None:
    run_dir = root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "policy": "autonomous_knowledge",
        "phase": phase,
        "next_action": next_action,
        "last_result": "pass" if phase == "stopped_budget" else "blocked",
        "state_revision": 1,
        "run_kind": "single",
        "task_id": f"{run_id}-task-{len(completed) + 1}",
        "parent_task_counter": parent_counter,
        "semantic_parent_task_next": parent_counter + 1,
        "_autonomous_completed_task_ids": completed,
        "previous_run_id": previous_run_id,
        "requirement": "migration fixture",
        "constraints": [],
        "stop_conditions": ["stopped_budget"],
        "baseline_dirty_paths": [],
        "allowed_paths": [],
        "denylist_paths": [],
        "attempts": {},
        "limits": {},
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
    }
    (run_dir / "run.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_migration_streams_repeated_ticks_and_preserves_first_last_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [_decision(index) for index in range(1, 6330)]
    rows.append(
        _decision(
            6330,
            phase="planning",
            next_action="run_autonomous_planner",
            classification="actionable_resume",
            action="resume",
            reason="active_autonomous_phase",
        )
    )
    _write_jsonl(tmp_path / ".codex/supervisor/run-decisions.jsonl", rows)
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("migration must stream JSONL")
    ))
    store = _open_store(tmp_path)
    try:
        report = migrate_jsonl(tmp_path, store, dry_run=False)
        failure = next(
            row
            for row in store.fetch_all("failures")
            if row["failure_key"] == "unsupported_state:run-1:run-state:unsupported-state"
        )
        transitions = store.fetch_all("transitions")
    finally:
        store.close()

    assert report.source_rows == 6330
    assert report.transition_rows == 2
    assert len(transitions) == 2
    assert failure["occurrence_count"] == 6329
    assert failure["first_seen_at"] == rows[0]["created_at"]
    assert failure["last_seen_at"] == rows[-2]["created_at"]
    assert report.snapshot_path
    assert not Path(report.snapshot_path).is_relative_to(tmp_path)


def test_migration_never_deletes_legacy_files_before_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decisions_path = tmp_path / ".codex/supervisor/run-decisions.jsonl"
    _write_jsonl(decisions_path, [_decision(1)])
    monkeypatch.setattr(
        "scripts.loop_supervisor.migration.validate_migration",
        lambda *_args, **_kwargs: False,
    )
    store = _open_store(tmp_path)
    try:
        with pytest.raises(MigrationValidationError):
            migrate_jsonl(tmp_path, store, dry_run=False)
    finally:
        store.close()

    assert decisions_path.exists()


def test_inventory_preserves_parent22_crawler_raw_and_baseline_dirty_paths(
    tmp_path: Path,
) -> None:
    parent22 = Path(
        "personal-wiki/domains/ai_infra/"
        "manifest-ai-infra-expansion-continuation-20260708-parent-22-verification.json"
    )
    crawler_raw = Path(
        "personal-wiki/domains/ai_infra/raw/crawler/compute-accelerators-aws-trn2/"
        "20260712T040912332184Z-aws-amazon-com-ec2-instance-types-trn2.md"
    )
    baseline = Path("personal-wiki/domains/ai_infra/wiki/references/existing-dirty.md")
    for relative in (parent22, crawler_raw, baseline):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    _seed_run(tmp_path, "parent-22-run", parent_counter=21, completed=["parent-21"])
    run_path = tmp_path / ".codex/loop-runs/parent-22-run/run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["baseline_dirty_paths"] = [f" M {baseline.as_posix()}"]
    run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    inventory = inventory_runtime(tmp_path)

    assert parent22.as_posix() in inventory.protected_paths
    assert crawler_raw.as_posix() in inventory.protected_paths
    assert baseline.as_posix() in inventory.protected_paths


def test_migration_deduplicates_archived_decisions_and_preserves_one_open(
    tmp_path: Path,
) -> None:
    open_rows = []
    archived_rows = []
    for index in range(17):
        failure_key = f"unsupported_state:run-{index}:run-state:unsupported-state"
        row = {
            "schema_version": 1,
            "decision_id": f"decision-{index}",
            "failure_key": failure_key,
            "affected_runs": [f"run-{index}"],
            "status": "open",
            "summary": f"decision {index}",
            "required_user_decision": "Inspect the run state.",
            "opened_at": f"2026-07-14T00:00:{index:02d}Z",
        }
        open_rows.append(row)
        if index < 16:
            archived_rows.append(
                {
                    **row,
                    "status": "archived",
                    "archived_at": f"2026-07-14T01:00:{index:02d}Z",
                }
            )
    _write_jsonl(tmp_path / ".codex/supervisor/user-decisions.jsonl", open_rows)
    _write_jsonl(
        tmp_path / ".codex/supervisor/archived-user-decisions.jsonl",
        archived_rows,
    )
    store = _open_store(tmp_path)
    try:
        report = migrate_jsonl(tmp_path, store, dry_run=False)
        decisions = store.fetch_all("user_decisions")
    finally:
        store.close()

    assert report.decision_rows == 17
    assert report.archived_decisions == 16
    assert report.open_decisions == 1
    assert sum(row["status"] == "closed" for row in decisions) == 16
    assert sum(row["status"] == "open" for row in decisions) == 1


def test_migration_rebuilds_reviewer_cadence_from_semantic_parent_completions(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "lineage-root",
        parent_counter=14,
        completed=[f"lineage-root-parent-{number}" for number in range(1, 15)],
    )
    _seed_run(
        tmp_path,
        "lineage-continuation",
        previous_run_id="lineage-root",
        parent_counter=17,
        completed=[f"lineage-continuation-task-{number}" for number in range(1, 4)],
    )
    _seed_run(
        tmp_path,
        "lineage-parent-22-partial",
        previous_run_id="lineage-continuation",
        parent_counter=21,
        completed=["lineage-parent-22-partial-task-1"],
        phase="stopped_blocked",
        next_action="inspect_required_evidence",
    )
    store = _open_store(tmp_path)
    try:
        report = migrate_jsonl(tmp_path, store, dry_run=False)
        cadence = store.review_cadence_positions()
        projections = store.fetch_all("runs")
    finally:
        store.close()

    assert report.semantic_parent_completions == 18
    assert set(cadence) == {"lineage-root"}
    assert cadence["lineage-root"]["reviewed_position"] == 18
    partial = next(row for row in projections if row["run_id"] == "lineage-parent-22-partial")
    assert partial["loop_lineage_id"] == "lineage-root"


def test_shadow_compare_allows_old_user_gate_to_become_registry_recovery(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "run-1",
        parent_counter=1,
        completed=[],
        phase="stopped_blocked",
        next_action="inspect_required_evidence",
    )
    _write_jsonl(tmp_path / ".codex/supervisor/run-decisions.jsonl", [_decision(1)])
    store = _open_store(tmp_path)
    try:
        report = shadow_compare(tmp_path, store)
    finally:
        store.close()

    assert report.new_auto_recovery == 1
    assert report.new_user_intervention == 0
    assert report.unsafe_divergence == 0
    assert report.passed


def test_cleanup_requires_validated_migration_and_passing_shadow_gate(
    tmp_path: Path,
) -> None:
    decisions_path = tmp_path / ".codex/supervisor/run-decisions.jsonl"
    _write_jsonl(decisions_path, [_decision(1)])
    store = _open_store(tmp_path)
    try:
        migration = migrate_jsonl(tmp_path, store, dry_run=False)
        comparison = shadow_compare(tmp_path, store)
        removed = cleanup_legacy_runtime(tmp_path, migration, comparison)
    finally:
        store.close()

    assert decisions_path.as_posix() in removed
    assert not decisions_path.exists()


def test_supervisor_cli_exposes_only_unified_runtime_operations() -> None:
    parser = supervisor_cli.build_parser()

    for command in (
        "watch",
        "worker",
        "status",
        "health",
        "migrate",
        "shadow-compare",
        "rebuild-db",
        "retention",
    ):
        assert parser.parse_args([command]).command == command

    help_text = parser.format_help().lower()
    assert "orchestrator" not in help_text
    assert "auto-resume" not in help_text
    assert "auditor" not in help_text


def test_shadow_compare_treats_existing_human_merge_gate_as_equivalent(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "human-gate",
        parent_counter=0,
        completed=[],
        phase="passed_waiting_human_merge",
        next_action="await_human_merge_confirmation",
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl",
        [
            _decision(
                1,
                phase="passed_waiting_human_merge",
                next_action="await_human_merge_confirmation",
                classification="awaiting_human_merge",
                action="await_human_merge",
                reason="human_merge_required",
            )
            | {"run_id": "human-gate"}
        ],
    )
    store = _open_store(tmp_path)
    try:
        report = shadow_compare(tmp_path, store)
    finally:
        store.close()

    assert report.passed
    assert report.equivalent == 1


def test_shadow_compare_applies_descendant_suppression_to_old_continuations(
    tmp_path: Path,
) -> None:
    _seed_run(tmp_path, "lineage-root", parent_counter=2, completed=["parent-1", "parent-2"])
    _seed_run(
        tmp_path,
        "lineage-child",
        previous_run_id="lineage-root",
        parent_counter=3,
        completed=["lineage-child-task-1"],
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl",
        [
            _decision(
                1,
                phase="stopped_budget",
                next_action="none",
                classification="terminal",
                action="observe",
                reason="continuation_superseded_by_descendant",
            )
            | {"run_id": "lineage-root"},
            _decision(
                2,
                phase="stopped_budget",
                next_action="none",
                classification="continuation_candidate",
                action="create_continuation",
                reason="autonomous_budget_stop",
            )
            | {"run_id": "lineage-child"},
        ],
    )
    store = _open_store(tmp_path)
    try:
        report = shadow_compare(tmp_path, store)
    finally:
        store.close()

    assert report.passed
    assert report.equivalent == 2


def test_migrated_archived_decision_stays_closed_after_reconcile(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "archived-run",
        parent_counter=0,
        completed=[],
        phase="stopped_blocked",
        next_action="inspect_blocked_diagnostics",
    )
    failure_key = "unsupported_state:archived-run:run-state:unsupported-state"
    open_decision = {
        "schema_version": 1,
        "decision_id": "archived-decision",
        "failure_key": failure_key,
        "affected_runs": ["archived-run"],
        "status": "open",
        "summary": "obsolete stopped run",
        "required_user_decision": "Inspect the run state.",
        "opened_at": "2026-07-14T00:00:00Z",
    }
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl",
        [
            _decision(
                1,
                phase="stopped_blocked",
                next_action="inspect_blocked_diagnostics",
                classification="terminal",
                action="observe",
                reason="archived_user_decision",
            )
            | {"run_id": "archived-run"}
        ],
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/user-decisions.jsonl", [open_decision]
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/archived-user-decisions.jsonl",
        [
            open_decision
            | {
                "status": "archived",
                "archived_at": "2026-07-14T01:00:00Z",
            }
        ],
    )
    store = _open_store(tmp_path)
    try:
        migrate_jsonl(tmp_path, store, dry_run=False)
        reconciled = reconcile_once(tmp_path, store, include_worktrees=False)
        decisions = store.fetch_all("user_decisions")
    finally:
        store.close()

    assert reconciled.queued_actions == []
    assert reconciled.open_user_decisions == []
    assert len(decisions) == 1
    assert decisions[0]["status"] == "closed"

    run_path = tmp_path / ".codex/loop-runs/archived-run/run.json"
    changed = json.loads(run_path.read_text(encoding="utf-8"))
    changed.update(
        {
            "state_revision": 2,
            "phase": "preflight",
            "next_action": "await_preflight_confirmation",
        }
    )
    run_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")
    store = _open_store(tmp_path)
    try:
        changed_result = reconcile_once(tmp_path, store, include_worktrees=False)
    finally:
        store.close()

    assert len(changed_result.open_user_decisions) == 1
