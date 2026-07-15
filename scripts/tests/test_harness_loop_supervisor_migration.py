from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.loop_supervisor import cli as supervisor_cli
from scripts.loop_supervisor import migration as migration_module
from scripts.loop_supervisor.migration import (
    MigrationValidationError,
    cleanup_legacy_runtime,
    inventory_runtime,
    migrate_jsonl,
    shadow_compare,
)
from scripts.loop_supervisor.reconciler import reconcile_once
from scripts.loop_supervisor.store import SupervisorStore
from scripts.harness_loop_runtime_lock import acquire_repository_mutation_lock


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
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
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
    subprocess.run(
        ["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True
    )
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


def test_archived_decision_inherits_opened_at_from_matching_open_source_row(
    tmp_path: Path,
) -> None:
    open_row = {
        "schema_version": 1,
        "decision_id": "legacy-decision",
        "failure_key": "unsupported_state:run-1:run-state:unsupported-state",
        "affected_runs": ["run-1"],
        "status": "open",
        "summary": "legacy gate",
        "required_user_decision": "Inspect the run.",
        "opened_at": "2026-07-09T15:03:26Z",
    }
    archived_row = {
        "schema_version": 1,
        "decision_id": "legacy-decision",
        "failure_key": open_row["failure_key"],
        "affected_runs": ["run-1"],
        "summary": "legacy gate",
        "archived_at": "2026-07-09T15:25:28Z",
    }
    _write_jsonl(
        tmp_path / ".codex/supervisor/user-decisions.jsonl", [open_row]
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/archived-user-decisions.jsonl",
        [archived_row],
    )
    store = _open_store(tmp_path)
    try:
        report = migrate_jsonl(tmp_path, store, dry_run=False)
        decisions = store.fetch_all("user_decisions")
    finally:
        store.close()

    assert report.valid_rows == 2
    assert report.corrupt_rows == 0
    assert report.archived_decisions == 1
    assert decisions[0]["status"] == "closed"
    assert decisions[0]["created_at"] == "2026-07-09T15:03:26.000000+00:00"
    assert decisions[0]["closed_at"] == "2026-07-09T15:25:28.000000+00:00"


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
        removed = cleanup_legacy_runtime(
            tmp_path, migration, comparison, store=store
        )
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


def test_archived_compatibility_requires_exact_migrated_run_state(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "archived-exact-state",
        parent_counter=0,
        completed=[],
        phase="stopped_blocked",
        next_action="inspect_blocked_diagnostics",
    )
    failure_key = (
        "unsupported_state:archived-exact-state:run-state:unsupported-state"
    )
    archived = {
        "schema_version": 1,
        "decision_id": "archived-exact-state-decision",
        "failure_key": failure_key,
        "affected_runs": ["archived-exact-state"],
        "status": "archived",
        "summary": "obsolete stopped run",
        "required_user_decision": "Inspect the run state.",
        "opened_at": "2026-07-14T00:00:00Z",
        "archived_at": "2026-07-14T01:00:00Z",
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
            | {"run_id": "archived-exact-state"}
        ],
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/archived-user-decisions.jsonl", [archived]
    )
    store = _open_store(tmp_path)
    try:
        migrate_jsonl(tmp_path, store, dry_run=False)
        run_path = tmp_path / ".codex/loop-runs/archived-exact-state/run.json"
        changed = json.loads(run_path.read_text(encoding="utf-8"))
        changed["state_revision"] = 2
        changed["constraints"] = ["state changed after archival"]
        run_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")

        result = reconcile_once(tmp_path, store, include_worktrees=False)
    finally:
        store.close()

    assert len(result.open_user_decisions) == 1
    assert result.open_user_decisions[0]["scope"] == "run"


def test_archived_compatibility_never_suppresses_global_safety(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "archived-global-safety",
        parent_counter=0,
        completed=[],
        phase="stopped_blocked",
        next_action="inspect_blocked_diagnostics",
    )
    failure_key = (
        "unsupported_state:archived-global-safety:run-state:unsupported-state"
    )
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
            | {"run_id": "archived-global-safety"}
        ],
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/archived-user-decisions.jsonl",
        [
            {
                "schema_version": 1,
                "decision_id": "archived-global-safety-decision",
                "failure_key": failure_key,
                "affected_runs": ["archived-global-safety"],
                "status": "archived",
                "summary": "obsolete stopped run",
                "required_user_decision": "Inspect the run state.",
                "opened_at": "2026-07-14T00:00:00Z",
                "archived_at": "2026-07-14T01:00:00Z",
            }
        ],
    )
    store = _open_store(tmp_path)
    try:
        migrate_jsonl(tmp_path, store, dry_run=False)
        run_path = tmp_path / ".codex/loop-runs/archived-global-safety/run.json"
        changed = json.loads(run_path.read_text(encoding="utf-8"))
        changed["state_revision"] = 2
        changed["unsafe_secret_detected"] = True
        run_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")

        result = reconcile_once(tmp_path, store, include_worktrees=False)
    finally:
        store.close()

    assert len(result.open_user_decisions) == 1
    assert result.open_user_decisions[0]["scope"] == "global"
    assert "secret_exposure" in result.open_user_decisions[0]["failure_key"]


def test_migration_validation_rejects_inexact_failure_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl", [_decision(1)]
    )
    original = migration_module._import_failures

    def import_with_wrong_count(store: SupervisorStore, failures: object) -> None:
        original(store, failures)  # type: ignore[arg-type]
        store._connection.execute(
            "UPDATE failures SET occurrence_count = occurrence_count + 1"
        )

    monkeypatch.setattr(migration_module, "_import_failures", import_with_wrong_count)
    store = _open_store(tmp_path)
    try:
        with pytest.raises(MigrationValidationError):
            migrate_jsonl(tmp_path, store, dry_run=False)
    finally:
        store.close()


def test_migration_validation_rejects_changed_transition_timestamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl", [_decision(1)]
    )
    original = migration_module._import_transitions

    def import_with_wrong_timestamp(
        store: SupervisorStore, transitions: object
    ) -> None:
        original(store, transitions)  # type: ignore[arg-type]
        store._connection.execute(
            "UPDATE transitions SET created_at = '2099-01-01T00:00:00.000000+00:00'"
        )

    monkeypatch.setattr(
        migration_module, "_import_transitions", import_with_wrong_timestamp
    )
    store = _open_store(tmp_path)
    try:
        with pytest.raises(MigrationValidationError):
            migrate_jsonl(tmp_path, store, dry_run=False)
    finally:
        store.close()


def test_migration_validation_rejects_changed_run_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_run(
        tmp_path,
        "projection-run",
        parent_counter=2,
        completed=["parent-1", "parent-2"],
    )
    original = migration_module._import_run_projections

    def import_with_wrong_projection(
        store: SupervisorStore,
        root: Path,
        records: object,
        lineage_by_run: object,
    ) -> None:
        original(
            store,
            root,
            records,  # type: ignore[arg-type]
            lineage_by_run,  # type: ignore[arg-type]
        )
        store._connection.execute(
            "UPDATE runs SET phase = 'planning' WHERE run_id = 'projection-run'"
        )

    monkeypatch.setattr(
        migration_module, "_import_run_projections", import_with_wrong_projection
    )
    store = _open_store(tmp_path)
    try:
        with pytest.raises(MigrationValidationError):
            migrate_jsonl(tmp_path, store, dry_run=False)
    finally:
        store.close()


def test_migration_validation_rejects_extra_cadence_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_run(
        tmp_path,
        "cadence-run",
        parent_counter=2,
        completed=["parent-1", "parent-2"],
    )
    original = migration_module._import_cadence

    def import_with_extra_cadence(
        store: SupervisorStore, cadence_positions: object
    ) -> None:
        original(store, cadence_positions)  # type: ignore[arg-type]
        store._connection.execute(
            """
            INSERT INTO review_cadence(
              lineage_id, reviewed_position, reserved_position, reservation_id, updated_at
            ) VALUES ('unexpected-lineage', 2, 2, '', '2026-07-14T00:00:00.000000+00:00')
            """
        )

    monkeypatch.setattr(migration_module, "_import_cadence", import_with_extra_cadence)
    store = _open_store(tmp_path)
    try:
        with pytest.raises(MigrationValidationError):
            migrate_jsonl(tmp_path, store, dry_run=False)
    finally:
        store.close()


def test_migration_imports_exact_service_projection_and_source_timestamp(
    tmp_path: Path,
) -> None:
    supervisor = tmp_path / ".codex/supervisor"
    supervisor.mkdir(parents=True)
    (supervisor / "service-health.json").write_text(
        json.dumps(
            {
                "crawler-backend": {
                    "status": "healthy",
                    "endpoint": "http://127.0.0.1:8765/api/health",
                    "process_id": 123,
                    "heartbeat_at": "2026-07-14T03:04:05Z",
                    "version": "fixture-head",
                    "reachable": True,
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    store = _open_store(tmp_path)
    try:
        report = migrate_jsonl(tmp_path, store, dry_run=False)
        services = store.fetch_all("services")
    finally:
        store.close()

    assert report.service_rows == 1
    assert services == [
        {
            "service_id": "crawler-backend",
            "status": "healthy",
            "endpoint": "http://127.0.0.1:8765/api/health",
            "process_id": 123,
            "heartbeat_at": "2026-07-14T03:04:05.000000+00:00",
            "version": "fixture-head",
            "details_json": '{"reachable":true}',
            "created_at": "2026-07-14T03:04:05.000000+00:00",
            "updated_at": "2026-07-14T03:04:05.000000+00:00",
        }
    ]


@pytest.mark.parametrize("symlink_kind", ["supervisor", "run"])
def test_cleanup_rejects_symlinked_ancestors_without_touching_external_paths(
    tmp_path: Path, symlink_kind: str
) -> None:
    store = _open_store(tmp_path)
    migration = migrate_jsonl(tmp_path, store, dry_run=False)
    comparison = shadow_compare(tmp_path, store)

    external = tmp_path.parent / f"{tmp_path.name}-external-{symlink_kind}"
    if symlink_kind == "supervisor":
        supervisor = tmp_path / ".codex/supervisor"
        shutil.rmtree(supervisor)
        external.mkdir()
        protected = external / "run-decisions.jsonl"
        protected.write_text("external evidence\n", encoding="utf-8")
        supervisor.symlink_to(external, target_is_directory=True)
    else:
        run_dir = tmp_path / ".codex/loop-runs/run-1"
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        external.mkdir()
        audit_dir = external / "audit-reports"
        audit_dir.mkdir()
        protected = audit_dir / "report.json"
        protected.write_text("external evidence\n", encoding="utf-8")
        run_dir.symlink_to(external, target_is_directory=True)

    try:
        with pytest.raises(MigrationValidationError, match="symlink"):
            cleanup_legacy_runtime(
                tmp_path, migration, comparison, store=store
            )
    finally:
        store.close()

    assert protected.read_text(encoding="utf-8") == "external evidence\n"


def test_shadow_compare_rejects_run_gate_becoming_global_safety_gate(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "scope-divergence",
        parent_counter=0,
        completed=[],
        phase="stopped_blocked",
        next_action="inspect_blocked_diagnostics",
    )
    run_path = tmp_path / ".codex/loop-runs/scope-divergence/run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["unsafe_secret_detected"] = True
    run_path.write_text(json.dumps(run) + "\n", encoding="utf-8")
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl",
        [
            _decision(
                1,
                classification="needs_user_decision",
                action="request_user_decision",
                reason="unsupported_state",
            )
            | {"run_id": "scope-divergence", "scope": "run"}
        ],
    )
    store = _open_store(tmp_path)
    try:
        report = shadow_compare(tmp_path, store)
    finally:
        store.close()

    assert report.unsafe_divergence == 1
    assert not report.passed


def test_shadow_compare_rejects_changed_user_decision_reason(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "reason-divergence",
        parent_counter=0,
        completed=[],
        phase="preflight",
        next_action="await_preflight_confirmation",
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl",
        [
            _decision(
                1,
                phase="preflight",
                next_action="await_preflight_confirmation",
                classification="needs_user_decision",
                action="request_user_decision",
                reason="permission_expansion",
            )
            | {"run_id": "reason-divergence", "scope": "run"}
        ],
    )
    store = _open_store(tmp_path)
    try:
        report = shadow_compare(tmp_path, store)
    finally:
        store.close()

    assert report.unsafe_divergence == 1
    assert not report.passed


def test_shadow_compare_rejects_active_observe_masking_continuation(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "action-divergence",
        parent_counter=2,
        completed=["parent-1", "parent-2"],
        phase="stopped_budget",
        next_action="none",
    )
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl",
        [
            _decision(
                1,
                phase="stopped_budget",
                next_action="none",
                classification="active",
                action="observe",
                reason="active_run",
            )
            | {"run_id": "action-divergence"}
        ],
    )
    store = _open_store(tmp_path)
    try:
        report = shadow_compare(tmp_path, store)
    finally:
        store.close()

    assert report.unsafe_divergence == 1
    assert not report.passed


def test_shadow_compare_uses_derived_legacy_phase_for_active_action_semantics(
    tmp_path: Path,
) -> None:
    _seed_run(
        tmp_path,
        "derived-active",
        parent_counter=0,
        completed=[],
        phase="repair_needed",
        next_action="repair_from_evaluator_findings",
    )
    run_path = tmp_path / ".codex/loop-runs/derived-active/run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["policy"] = "demand_development"
    run_path.write_text(json.dumps(run) + "\n", encoding="utf-8")
    store = _open_store(tmp_path)
    try:
        report = shadow_compare(tmp_path, store)
    finally:
        store.close()

    assert report.equivalent == 1
    assert report.unsafe_divergence == 0
    assert report.passed


@pytest.mark.parametrize(
    "command", [("migrate", "--dry-run"), ("shadow-compare",)]
)
def test_read_only_cli_commands_do_not_create_project_runtime_files(
    tmp_path: Path, command: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    subprocess.run(
        ["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True
    )
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(tmp_path).parts
    }

    assert (
        supervisor_cli.main(
            [command[0], "--project-root", str(tmp_path), *command[1:]]
        )
        == 0
    )
    capsys.readouterr()

    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(tmp_path).parts
    }
    assert after == before
    assert not (tmp_path / ".codex/supervisor").exists()


def test_migration_counts_and_quarantines_corrupt_rows_with_source_timestamps(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".codex/supervisor/run-decisions.jsonl"
    path.parent.mkdir(parents=True)
    valid = _decision(1)
    invalid_timestamp = _decision(2) | {"created_at": "not-a-timestamp"}
    nul_tailed = json.dumps(_decision(3), sort_keys=True).encode("utf-8") + b"\x00\x00\n"
    path.write_bytes(
        json.dumps(valid, sort_keys=True).encode("utf-8")
        + b"\n\n"
        + b'{"run_id":"truncated"\n'
        + nul_tailed
        + json.dumps(invalid_timestamp, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    store = _open_store(tmp_path)
    try:
        report = migrate_jsonl(tmp_path, store, dry_run=False)
        transitions = store.fetch_all("transitions")
    finally:
        store.close()

    assert report.physical_rows == 5
    assert report.valid_rows == 1
    assert report.corrupt_rows == 4
    assert report.compacted_rows == 1
    assert report.quarantine_rows == 4
    assert report.source_rows == 1
    assert transitions[0]["created_at"] == valid["created_at"]
    quarantine_path = Path(report.quarantine_path)
    assert quarantine_path.is_file()
    quarantine = [
        json.loads(line)
        for line in quarantine_path.read_text(encoding="utf-8").splitlines()
    ]
    assert {item["line_number"] for item in quarantine} == {2, 3, 4, 5}
    assert {item["reason"] for item in quarantine} == {
        "blank_row",
        "malformed_json",
        "nul_byte",
        "invalid_timestamp",
    }
    invalid_time = next(
        item for item in quarantine if item["reason"] == "invalid_timestamp"
    )
    assert invalid_time["source_timestamp"] == "not-a-timestamp"


@pytest.mark.parametrize("failing_command", ["ls-files", "status"])
def test_inventory_fails_closed_when_git_inventory_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_command: str,
) -> None:
    def failed_git(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        command = args[1]
        if command == failing_command:
            return subprocess.CompletedProcess(
                args, 128, stdout=b"", stderr=b"fatal: fixture git failure\n"
            )
        return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(migration_module.subprocess, "run", failed_git)

    with pytest.raises(MigrationValidationError, match="fixture git failure"):
        inventory_runtime(tmp_path)


def test_loop_operator_docs_remove_auto_resume_and_direct_orchestrator_execution() -> None:
    text = Path("docs/harness/planner-generator-evaluator-loop.md").read_text(
        encoding="utf-8"
    )

    assert "loop-auto-resume" not in text
    assert "harness_loop_auto_resume.py" not in text
    assert " run-demand-multi" not in text
    assert " run-autonomous" not in text
    assert "harness_loop_orchestrator.py plan" not in text
    assert "harness_loop_orchestrator.py artifact-hygiene" not in text
    assert "harness_loop_orchestrator.py cleanup" not in text


def test_rebuild_db_rejects_recent_worker_heartbeat_without_touching_database(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    store = _open_store(tmp_path)
    try:
        store.record_worker_heartbeat("worker-live")
    finally:
        store.close()
    database = tmp_path / ".codex/supervisor/supervisor.db"
    before = database.read_bytes()

    with pytest.raises(MigrationValidationError, match="heartbeat"):
        supervisor_cli._rebuild_db(tmp_path)

    assert database.read_bytes() == before


def test_rebuild_db_rejects_live_supervisor_process_without_touching_database(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    store = _open_store(tmp_path)
    try:
        timestamp = store.format_time(store.current_time())
        store._connection.execute(
            """
            INSERT INTO services(
              service_id, status, endpoint, process_id, heartbeat_at, version,
              details_json, created_at, updated_at
            ) VALUES ('loop-supervisor', 'healthy', '', ?, ?, '', '{}', ?, ?)
            """,
            (os.getpid(), timestamp, timestamp, timestamp),
        )
    finally:
        store.close()
    database = tmp_path / ".codex/supervisor/supervisor.db"
    before = database.read_bytes()

    with pytest.raises(MigrationValidationError, match="process"):
        supervisor_cli._rebuild_db(tmp_path)

    assert database.read_bytes() == before


def test_rebuild_db_rejects_held_loop_lock_without_touching_database(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    store = _open_store(tmp_path)
    store.close()
    database = tmp_path / ".codex/supervisor/supervisor.db"
    before = database.read_bytes()

    with acquire_repository_mutation_lock(tmp_path, owner="rebuild-test"):
        with pytest.raises(MigrationValidationError, match="lock"):
            supervisor_cli._rebuild_db(tmp_path)

    assert database.read_bytes() == before


def test_rebuild_db_build_failure_preserves_live_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    store = _open_store(tmp_path)
    store.close()
    database = tmp_path / ".codex/supervisor/supervisor.db"
    before = database.read_bytes()

    def fail_migration(*_args: object, **_kwargs: object) -> object:
        raise MigrationValidationError("replacement build failed")

    monkeypatch.setattr(supervisor_cli, "migrate_jsonl", fail_migration)

    with pytest.raises(MigrationValidationError, match="replacement build failed"):
        supervisor_cli._rebuild_db(tmp_path)

    assert database.is_file()
    assert database.read_bytes() == before


def test_rebuild_db_atomically_swaps_valid_replacement(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _write_jsonl(
        tmp_path / ".codex/supervisor/run-decisions.jsonl", [_decision(1)]
    )
    store = _open_store(tmp_path)
    store.close()

    result = supervisor_cli._rebuild_db(tmp_path)

    assert result["status"] == "completed"
    assert result["migration"]["validated"] is True
    assert Path(result["backup_path"], "supervisor.db").is_file()
    assert not tuple(
        (tmp_path / ".codex/supervisor").glob(".supervisor.db.rebuild-*")
    )
    with SupervisorStore.open(tmp_path) as rebuilt:
        assert rebuilt.database_integrity_ok()
        assert rebuilt.count("transitions") == 1


def test_rebuild_db_post_swap_failure_restores_live_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    store = _open_store(tmp_path)
    store.close()
    database = tmp_path / ".codex/supervisor/supervisor.db"
    before = database.read_bytes()

    def reject_replacement(_database: Path) -> None:
        raise MigrationValidationError("post-swap validation failed")

    monkeypatch.setattr(
        supervisor_cli, "_validate_replacement_database", reject_replacement
    )

    with pytest.raises(MigrationValidationError, match="post-swap validation failed"):
        supervisor_cli._rebuild_db(tmp_path)

    assert database.read_bytes() == before
    assert not tuple(
        (tmp_path / ".codex/supervisor").glob(".supervisor.db.rebuild-*")
    )
