from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import threading

import pytest

import scripts.harness_loop_orchestrator as orchestrator_module
from scripts.harness_loop_agents import build_codex_exec_command
from scripts.harness_loop_orchestrator import (
    _autonomous_planner_prompt,
    _run_audit_boundary,
    _set_audit_blocked,
)
from scripts.loop_supervisor import reviewer as reviewer_module
from scripts.loop_supervisor import reviewer_outbox as reviewer_outbox_module
from scripts.loop_supervisor import reviewer_safety as reviewer_safety_module
from scripts.loop_supervisor import reconciler as reconciler_module
from scripts.loop_supervisor.executor import ACTION_HANDLERS
from scripts.loop_supervisor.models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
    ReviewDecision,
)
from scripts.loop_supervisor.reconciler import _state_fingerprint
from scripts.loop_supervisor.reconciler import reconcile_once
from scripts.loop_supervisor.reviewer import (
    ReviewerContext,
    apply_review_decision,
    build_review_evidence,
    review_due_lineages,
    run_reviewer,
    run_queued_reviewer,
    schedule_due_reviews,
    validate_review_payload,
)
from scripts.loop_supervisor.reviewer_safety import current_review_safety_checks
from scripts.loop_supervisor.store import LeaseError, SupervisorStore


NOW = datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)


class MutableClock:
    def __init__(self, value: datetime = NOW) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def migrated_store(tmp_path: Path, clock: MutableClock | None = None) -> SupervisorStore:
    store = SupervisorStore.open(tmp_path, clock=clock or MutableClock())
    store.migrate()
    return store


def test_review_projection_uses_one_fallback_lineage_for_outer_row_and_summary(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    previous = {
        "run_id": "legacy-run",
        "loop_lineage_id": "",
        "parent_run_id": "",
        "policy": "autonomous_knowledge",
        "repo_relative_root": ".",
        "summary": {
            "artifact_refs": [".codex/loop-runs/legacy-run/run.json"],
        },
    }
    payload = {
        "run_id": "legacy-run",
        "state_revision": 1,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "next_action": "run_autonomous_planner",
        "last_result": "none",
    }

    reviewer_outbox_module._project_saved_run(store, previous, payload)

    projected = store.get_run("legacy-run")
    projected_summary = json.loads(projected["summary"]["summary"])
    assert projected["loop_lineage_id"] == "legacy-run"
    assert projected_summary["loop_lineage_id"] == projected["loop_lineage_id"]


def test_review_projection_compacts_long_lived_run_summary(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    previous = {
        "run_id": "long-review-run",
        "loop_lineage_id": "long-review-lineage",
        "parent_run_id": "",
        "policy": "autonomous_knowledge",
        "repo_relative_root": ".",
        "summary": {
            "artifact_refs": [".codex/loop-runs/long-review-run/run.json"],
        },
    }
    payload = {
        "run_id": "long-review-run",
        "state_revision": 2,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "next_action": "run_autonomous_planner",
        "last_result": "none",
        "task_id": "long-review-run-task-80",
        "requirement": "Long running review projection. " * 200,
        "constraints": ["x" * 600 for _ in range(20)],
        "_autonomous_completed_task_ids": [
            f"long-review-run-task-{index}" for index in range(80)
        ],
    }

    reviewer_outbox_module._project_saved_run(store, previous, payload)

    projected_summary = json.loads(store.get_run("long-review-run")["summary"]["summary"])
    completion_compaction = projected_summary["summary_compaction"][
        "_autonomous_completed_task_ids"
    ]
    assert completion_compaction["original_items"] == 80
    assert completion_compaction["retained_items"] == 8
    assert completion_compaction["series_key"].startswith("sha256:")


def test_projection_only_reviewer_cadence_uses_compacted_completion_count() -> None:
    run_id = "projection-only-run"
    summary = {
        "task_id": "projection-only-run-task-80",
        "last_result": "pass",
        "_autonomous_completed_task_ids": [
            f"projection-only-run-task-{index}" for index in range(72, 80)
        ],
        "summary_compaction": {
            "_autonomous_completed_task_ids": {
                "original_items": 80,
                "retained_items": 8,
            }
        },
    }
    rows = [
        {
            "run_id": run_id,
            "loop_lineage_id": "projection-only-lineage",
            "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "summary": {"summary": json.dumps(summary), "artifact_refs": []},
        }
    ]

    completions = reviewer_module._semantic_parent_completions(
        rows,
        {run_id: summary},
    )

    assert len(completions["projection-only-lineage"]) == 80


def test_projection_only_reviewer_deduplicates_cumulative_compacted_snapshots() -> None:
    summary = {
        "task_id": "projection-only-run-task-80",
        "last_result": "pass",
        "_autonomous_completed_task_ids": [
            f"projection-only-run-task-{index}" for index in range(72, 80)
        ],
        "summary_compaction": {
            "_autonomous_completed_task_ids": {
                "original_items": 80,
                "retained_items": 8,
            }
        },
    }
    rows = [
        {
            "run_id": run_id,
            "loop_lineage_id": "projection-only-lineage",
            "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "summary": {"summary": json.dumps(summary), "artifact_refs": []},
        }
        for run_id in ("projection-snapshot-a", "projection-snapshot-b")
    ]

    completions = reviewer_module._semantic_parent_completions(
        rows,
        {row["run_id"]: summary for row in rows},
    )

    assert len(completions["projection-only-lineage"]) == 80


def test_projection_only_reviewer_deduplicates_growing_compacted_snapshots() -> None:
    def summary(count: int) -> dict[str, object]:
        return {
            "task_id": f"projection-only-run-task-{count}",
            "last_result": "pass",
            "_autonomous_completed_task_ids": [
                f"projection-only-run-task-{index}"
                for index in range(count - 8, count)
            ],
            "summary_compaction": {
                "_autonomous_completed_task_ids": {
                    "original_items": count,
                    "retained_items": 8,
                }
            },
        }

    summaries = {
        "projection-snapshot-80": summary(80),
        "projection-snapshot-81": summary(81),
    }
    rows = [
        {
            "run_id": run_id,
            "loop_lineage_id": "projection-only-lineage",
            "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "summary": {"summary": json.dumps(payload), "artifact_refs": []},
        }
        for run_id, payload in summaries.items()
    ]

    completions = reviewer_module._semantic_parent_completions(rows, summaries)

    assert len(completions["projection-only-lineage"]) == 81


def test_projection_only_reviewer_deduplicates_growing_nonnumeric_task_series() -> None:
    all_ids = [f"autonomous-step-{index:03x}-x" for index in range(81)]
    series_key = "sha256:" + hashlib.sha256(all_ids[0].encode("utf-8")).hexdigest()

    def summary(count: int) -> dict[str, object]:
        return {
            "task_id": all_ids[count - 1],
            "last_result": "pass",
            "_autonomous_completed_task_ids": all_ids[count - 8 : count],
            "summary_compaction": {
                "_autonomous_completed_task_ids": {
                    "original_items": count,
                    "retained_items": 8,
                    "series_key": series_key,
                }
            },
        }

    summaries = {
        "projection-snapshot-80": summary(80),
        "projection-snapshot-81": summary(81),
    }
    rows = [
        {
            "run_id": run_id,
            "loop_lineage_id": "projection-only-lineage",
            "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "summary": {"summary": json.dumps(payload), "artifact_refs": []},
        }
        for run_id, payload in summaries.items()
    ]

    completions = reviewer_module._semantic_parent_completions(rows, summaries)

    assert len(completions["projection-only-lineage"]) == 81


def test_projection_only_reviewer_keeps_distinct_compacted_task_series() -> None:
    summaries = {
        run_id: {
            "task_id": f"{series}-task-80",
            "last_result": "pass",
            "_autonomous_completed_task_ids": [
                f"{series}-task-{index}" for index in range(72, 80)
            ],
            "summary_compaction": {
                "_autonomous_completed_task_ids": {
                    "original_items": 80,
                    "retained_items": 8,
                }
            },
        }
        for run_id, series in (
            ("projection-segment-a", "continuation-a"),
            ("projection-segment-b", "continuation-b"),
        )
    }
    rows = [
        {
            "run_id": run_id,
            "loop_lineage_id": "projection-only-lineage",
            "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "summary": {"summary": json.dumps(payload), "artifact_refs": []},
        }
        for run_id, payload in summaries.items()
    ]

    completions = reviewer_module._semantic_parent_completions(rows, summaries)

    assert len(completions["projection-only-lineage"]) == 160


def test_projection_only_reviewer_counts_compacted_demand_parent_children() -> None:
    run_id = "projection-only-demand-parent"
    child_ids = [f"{run_id}-child-{index:03d}" for index in range(1, 21)]
    summary = {
        "run_kind": "parent",
        "child_run_ids": child_ids[:8],
        "aggregate_acceptance": {"passed": 20},
        "summary_compaction": {
            "child_run_ids": {
                "original_items": 20,
                "retained_items": 8,
            }
        },
    }
    rows = [
        {
            "run_id": run_id,
            "loop_lineage_id": "projection-only-demand-lineage",
            "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "summary": {"summary": json.dumps(summary), "artifact_refs": []},
        }
    ]

    completions = reviewer_module._semantic_parent_completions(
        rows,
        {run_id: summary},
    )

    assert len(completions["projection-only-demand-lineage"]) == 20


def test_projection_only_reviewer_deduplicates_repeated_demand_parent_snapshots() -> None:
    child_ids = [f"shared-child-{index:03d}" for index in range(1, 21)]
    series_key = "sha256:" + hashlib.sha256(child_ids[0].encode("utf-8")).hexdigest()
    summary = {
        "run_kind": "parent",
        "child_run_ids": child_ids[:8],
        "aggregate_acceptance": {"passed": 20},
        "summary_compaction": {
            "child_run_ids": {
                "original_items": 20,
                "retained_items": 8,
                "series_key": series_key,
            }
        },
    }
    rows = [
        {
            "run_id": run_id,
            "loop_lineage_id": "projection-only-demand-lineage",
            "created_at": NOW.isoformat(),
            "updated_at": NOW.isoformat(),
            "summary": {"summary": json.dumps(summary), "artifact_refs": []},
        }
        for run_id in ("demand-parent-snapshot-a", "demand-parent-snapshot-b")
    ]

    completions = reviewer_module._semantic_parent_completions(
        rows,
        {row["run_id"]: summary for row in rows},
    )

    assert len(completions["projection-only-demand-lineage"]) == 20


def record_parent_completion(
    store: SupervisorStore,
    lineage_id: str,
    *,
    run_id: str,
    parent: int,
    previous_run_id: str = "",
    execution_root: Path | None = None,
    project: bool = True,
) -> None:
    root = (execution_root or store.project_root).resolve()
    run_dir = root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "state_revision": 1,
        "policy": "autonomous_knowledge",
        "phase": "stopped_budget",
        "run_kind": "single",
        "domain": "",
        "branch": "main",
        "worktree": str(root),
        "loop_lineage_id": lineage_id,
        "previous_run_id": previous_run_id,
        "task_id": f"parent-{parent}",
        "parent_task_counter": parent,
        "_autonomous_completed_task_ids": [f"parent-{parent}"],
        "requirement": f"Objective for {lineage_id}",
        "constraints": ["Preserve evidence"],
        "stop_conditions": ["All acceptance checks pass"],
        "last_result": "pass",
        "next_action": "none",
        "baseline_dirty_paths": [],
        "allowed_paths": [],
        "denylist_paths": [],
        "attempts": {
            "planner": 0,
            "generator": 0,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
        },
        "limits": {},
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
    }
    run_path = run_dir / "run.json"
    run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    if not project:
        return
    store.upsert_run_projection(
        {
            "run_id": run_id,
            "revision": 1,
            "repo_relative_root": root.relative_to(store.project_root).as_posix() or ".",
            "loop_lineage_id": lineage_id,
            "parent_run_id": previous_run_id,
            "policy": "autonomous_knowledge",
            "phase": "stopped_budget",
            "status": "actionable",
            "state_fingerprint": _state_fingerprint(payload),
            "summary": json.dumps(
                {
                    "completed_semantic_parent_ids": [f"parent-{parent}"],
                    "parent_task_counter": parent,
                    "task_id": f"parent-{parent}",
                },
                sort_keys=True,
            ),
            "artifact_refs": [run_path.relative_to(store.project_root).as_posix()],
        }
    )


def refresh_run_projection(
    store: SupervisorStore,
    run_id: str,
    payload: dict[str, object],
) -> None:
    current = store.get_run(run_id)
    store.upsert_run_projection(
        {
            "run_id": run_id,
            "revision": int(payload["state_revision"]),
            "loop_lineage_id": current["loop_lineage_id"],
            "parent_run_id": current["parent_run_id"],
            "policy": payload["policy"],
            "phase": payload["phase"],
            "status": current["status"],
            "state_fingerprint": _state_fingerprint(payload),
            "summary": current["summary"]["summary"],
            "artifact_refs": current["summary"]["artifact_refs"],
        }
    )


def valid_review_payload(
    *,
    review_id: str = "review-0001",
    decision: str = "continue",
    affected_run_ids: list[str] | None = None,
    evidence_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "review_id": review_id,
        "scope": "project",
        "decision": decision,
        "affected_run_ids": affected_run_ids or [],
        "summary": "The project remains aligned with its objective.",
        "evidence_refs": evidence_refs or [f"sha256:{'a' * 64}"],
        "findings": [],
        "skill_governance": [],
        "next_review_after_parent_tasks": 2,
    }


def service_keeper_action_request(
    *,
    action_id: str = "service-restart-loop-dashboard-outage-1",
    run_id: str = "service-keeper",
    run_revision: int = 0,
    action_type: ActionType = ActionType.RESTART_SERVICE,
    idempotency_key: str = "service-restart:loop-dashboard:outage-1",
    service_id: str = "loop-dashboard",
    outage_id: str | None = "outage-1",
) -> ActionRequest:
    payload: dict[str, object] = {
        "service_id": service_id,
        "observed_state_fingerprint": f"sha256:{'b' * 64}",
    }
    if outage_id is not None:
        payload["outage_id"] = outage_id
    return ActionRequest(
        action_id=action_id,
        run_id=run_id,
        run_revision=run_revision,
        policy="autonomous_knowledge",
        phase="repair_needed",
        action_type=action_type,
        idempotency_key=idempotency_key,
        queue_owner=ActionOwner.SUPERVISOR,
        repo_relative_root=".",
        task_id=f"service:{service_id}:{outage_id or 'missing'}",
        next_action=action_type.value,
        payload=payload,
    )


def _mark_lineage_terminal(store: SupervisorStore, run_id: str, phase: str) -> None:
    run_path = store.project_root / ".codex" / "loop-runs" / run_id / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["phase"] = phase
    payload["next_action"] = "none"
    payload["state_revision"] = int(payload["state_revision"]) + 1
    run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    current = store.get_run(run_id)
    store.upsert_run_projection(
        {
            "run_id": run_id,
            "revision": int(payload["state_revision"]),
            "loop_lineage_id": current["loop_lineage_id"],
            "parent_run_id": current["parent_run_id"],
            "policy": current["policy"],
            "phase": phase,
            "status": "terminal",
            "state_fingerprint": _state_fingerprint(payload),
            "summary": current["summary"]["summary"],
            "artifact_refs": current["summary"]["artifact_refs"],
        }
    )


def _record_action_attempt(store: SupervisorStore, run_id: str, suffix: str) -> str:
    run = store.get_run(run_id)
    request = ActionRequest(
        action_id=f"action-attempt-{suffix}",
        run_id=run_id,
        run_revision=int(run["revision"]),
        policy=str(run["policy"]),
        phase=str(run["phase"]),
        action_type=ActionType.RUN_ALTERNATE_RECOVERY,
        idempotency_key=f"attempt:{suffix}",
        queue_owner=ActionOwner.SUPERVISOR,
    )
    store.enqueue_action(request)
    claimed = store.claim_pending_action(
        request.action_id,
        f"attempt-worker-{suffix}",
        lease_seconds=60,
    )
    assert claimed is not None
    store.complete_action(
        request.action_id,
        f"attempt-worker-{suffix}",
        ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary=f"Completed {suffix}.",
        ),
    )
    return request.action_id


def test_project_global_review_sees_unrelated_active_lineage_and_may_refocus_it(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(
        store,
        "lineage-a",
        run_id="run-a2",
        parent=2,
        previous_run_id="run-a1",
    )
    record_parent_completion(store, "lineage-b", run_id="run-b1", parent=1)
    record_parent_completion(store, "lineage-terminal", run_id="run-terminal", parent=1)
    _mark_lineage_terminal(store, "run-terminal", "passed")

    bundle = build_review_evidence(tmp_path, store, ["lineage-a"])
    assert {item["run_id"] for item in bundle.evidence["objective_constraints"]} == {
        "run-a1",
        "run-a2",
        "run-b1",
        "run-terminal",
    }

    def refocus_unrelated_active_run(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-b1"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_reviewer(
        ReviewerContext(
            project_root=tmp_path,
            store=store,
            triggering_lineages=("lineage-a",),
        ),
        driver=refocus_unrelated_active_run,
    )

    assert result.status == "review_complete"
    refocused = json.loads(
        (tmp_path / ".codex" / "loop-runs" / "run-b1" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert (refocused["phase"], refocused["next_action"]) == (
        "planning",
        "run_autonomous_planner",
    )


def test_project_global_review_keeps_terminal_runs_as_evidence_only(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "active-lineage", run_id="active-1", parent=1)
    record_parent_completion(
        store,
        "active-lineage",
        run_id="active-2",
        parent=2,
        previous_run_id="active-1",
    )
    record_parent_completion(
        store,
        "legacy-child-lineage",
        run_id="legacy-child",
        parent=99,
        previous_run_id="active-2",
    )
    _mark_lineage_terminal(store, "legacy-child", "passed")

    bundle = build_review_evidence(tmp_path, store, ["active-lineage"])

    assert {item["run_id"] for item in bundle.evidence["objective_constraints"]} == {
        "active-1",
        "active-2",
        "legacy-child",
    }
    assert {item["loop_lineage_id"] for item in bundle.evidence["parent_progress"]} == {
        "active-lineage",
        "legacy-child-lineage",
    }

    def terminal_child_ask_user(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="ask_user",
            affected_run_ids=["legacy-child"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("active-lineage",)),
        driver=terminal_child_ask_user,
    )

    assert result.status == "review_degraded"
    assert store.fetch_all("user_decisions") == []


def test_reviewer_evidence_includes_action_attempts_from_all_project_runs(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "active-lineage", run_id="active-run", parent=1)
    record_parent_completion(
        store,
        "related-child-lineage",
        run_id="related-child",
        parent=2,
        previous_run_id="active-run",
    )
    record_parent_completion(store, "unrelated-lineage", run_id="unrelated-run", parent=1)
    active_action = _record_action_attempt(store, "active-run", "active")
    child_action = _record_action_attempt(store, "related-child", "child")
    unrelated_action = _record_action_attempt(store, "unrelated-run", "unrelated")
    _mark_lineage_terminal(store, "related-child", "passed")
    _mark_lineage_terminal(store, "unrelated-run", "passed")

    bundle = build_review_evidence(tmp_path, store, ["active-lineage"])

    assert {
        item["action_id"] for item in bundle.evidence["failures_recoveries"]["attempts"]
    } == {active_action, child_action, unrelated_action}


def test_reviewer_evidence_bounds_recovery_detail_but_preserves_global_counts(
) -> None:
    action_ids = [f"action-bounded-{index:03d}" for index in range(55)]
    recovery_actions = [
        {
            "action_id": action_id,
            "run_id": "active-run",
            "action_type": "recover_generator_result",
            "status": "failed",
            "recovery_tier": 1,
            "created_at": f"2026-07-15T00:{index:02d}:00Z",
            "payload": {"unneeded": "x" * 1000},
        }
        for index, action_id in enumerate(action_ids)
    ]
    attempts = [
        {
            "attempt_id": f"attempt-bounded-{index:03d}",
            "action_id": action_id,
            "result_class": "success",
            "error_class": "",
            "failure_key": "",
            "summary": "bounded recovery succeeded",
            "created_at": f"2026-07-15T00:{index:02d}:00Z",
        }
        for index, action_id in enumerate(action_ids)
    ]

    evidence = reviewer_module._bounded_failure_recovery_evidence(
        [], recovery_actions, attempts
    )

    assert evidence["attempt_count"] == 55
    assert evidence["recovery_action_count"] == 55
    assert len(evidence["attempts"]) == reviewer_module.REVIEW_ATTEMPT_DETAIL_LIMIT
    assert (
        len(evidence["recovery_actions"])
        == reviewer_module.REVIEW_RECOVERY_ACTION_DETAIL_LIMIT
    )
    assert evidence["attempt_counts_by_result_class"] == {"success": 55}
    assert action_ids[-1] in {item["action_id"] for item in evidence["attempts"]}
    assert action_ids[0] not in {item["action_id"] for item in evidence["attempts"]}
    assert all("payload" not in item for item in evidence["recovery_actions"])


def test_reconcile_reviewer_scope_incident_closes_only_exact_generated_decisions(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    review_id = "review-20260715T143145Z-f634627171ed"
    targets = ("historical-a", "historical-b")
    for index, run_id in enumerate(targets, start=1):
        record_parent_completion(
            store,
            f"lineage-{index}",
            run_id=run_id,
            parent=index,
        )
    registry = store.open_user_decision(
        scope="run",
        run_id=targets[0],
        failure_key=f"reconcile:run:{targets[0]}:registry_user_gate",
        summary="Registry gate.",
        required_decision="Resolve the registry gate.",
    )
    review = validate_review_payload(
        valid_review_payload(
            review_id=review_id,
            decision="ask_user",
            affected_run_ids=list(targets),
        )
    )
    apply_review_decision(store, review)
    generated = [
        row
        for row in store.fetch_all("user_decisions")
        if row["failure_key"].startswith(f"review:{review_id}:")
    ]
    targets_by_run = {
        row["run_id"]: row for row in store.review_application_targets(review_id)
    }
    for decision in generated:
        action = store.get_action(targets_by_run[decision["run_id"]]["action_id"])
        assert action.payload["review_user_decision"] == {
            "decision_id": decision["decision_id"],
            "review_id": review_id,
            "run_id": decision["run_id"],
        }

    replaced = generated[0]
    store.close_user_decision(
        replaced["decision_id"],
        resolution="Replace with an adversarial same-key user decision.",
    )
    same_key_user = store.open_user_decision(
        scope="run",
        run_id=replaced["run_id"],
        failure_key=replaced["failure_key"],
        summary="User-created decision with a colliding failure key.",
        required_decision="Keep this manual decision open.",
    )
    source_action = store.get_action(targets_by_run[replaced["run_id"]]["action_id"])
    assert source_action.payload["review_user_decision"]["decision_id"] == replaced[
        "decision_id"
    ]
    assert source_action.payload["review_user_decision"]["decision_id"] != same_key_user[
        "decision_id"
    ]
    unrelated = store.open_user_decision(
        scope="run",
        run_id="current-run",
        failure_key="review:review-current:current-run",
        summary="Current Reviewer decision.",
        required_decision="Resolve the current decision.",
    )

    closed = store.close_reviewer_scope_incident_decisions(
        review_id=review_id,
        expected_run_ids=targets,
        resolution="Close only explicitly proven Reviewer decisions.",
    )

    assert {row["decision_id"] for row in closed} == {
        row["decision_id"] for row in generated
    }
    assert store.fetch_all("user_decisions")
    assert store._connection.execute(
        "SELECT status FROM user_decisions WHERE decision_id = ?", (registry["decision_id"],)
    ).fetchone()["status"] == "open"
    assert store._connection.execute(
        "SELECT status FROM user_decisions WHERE decision_id = ?", (unrelated["decision_id"],)
    ).fetchone()["status"] == "open"
    assert store._connection.execute(
        "SELECT status FROM user_decisions WHERE decision_id = ?",
        (same_key_user["decision_id"],),
    ).fetchone()["status"] == "open"


def test_concurrent_same_key_manual_decision_cannot_be_claimed_by_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-explicit-provenance",
            decision="ask_user",
            affected_run_ids=["run-1"],
        )
    )
    original_open = store.open_user_decision
    observed_source: dict[str, str] = {}

    def race_open(**kwargs: object) -> dict[str, object]:
        source_action_id = str(kwargs.get("source_action_id") or "")
        source_action_owner = str(kwargs.get("source_action_owner") or "")
        provenance_token = str(kwargs.get("provenance_token") or "")
        if not source_action_id or not source_action_owner or not provenance_token:
            raise AssertionError("Reviewer must pass explicit decision provenance")
        observed_source.update(
            action_id=source_action_id,
            owner=source_action_owner,
            token=provenance_token,
        )
        forged = dict(kwargs)
        forged["provenance_token"] = "guessed-token"
        with pytest.raises(ValueError, match="provenance"):
            original_open(**forged)
        manual = original_open(
            scope=str(kwargs["scope"]),
            run_id=str(kwargs["run_id"]),
            failure_key=str(kwargs["failure_key"]),
            summary="Concurrent manual decision.",
            required_decision="Keep manual ownership.",
        )
        assert manual["status"] == "open"
        return original_open(**kwargs)

    monkeypatch.setattr(store, "open_user_decision", race_open)

    with pytest.raises(ValueError, match="unproven|collides"):
        apply_review_decision(store, review)

    assert observed_source["action_id"]
    decisions = store.fetch_all("user_decisions")
    assert len(decisions) == 1
    assert decisions[0]["summary"] == "Concurrent manual decision."
    action = store.get_action(observed_source["action_id"])
    assert "review_user_decision" not in action.payload


def test_cleanup_rejects_legacy_action_provenance_without_token(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-legacy-unproven",
            decision="ask_user",
            affected_run_ids=["run-1"],
        )
    )
    apply_review_decision(store, review)
    target = store.review_application_targets(review.review_id)[0]
    action = store.get_action(target["action_id"])
    payload = dict(action.payload)
    payload.pop("decision_provenance_token")
    store._connection.execute(
        "UPDATE actions SET payload_json = ? WHERE action_id = ?",
        (json.dumps(payload, sort_keys=True), action.action_id),
    )

    with pytest.raises(ValueError, match="token|provenance"):
        store.close_reviewer_scope_incident_decisions(
            review_id=review.review_id,
            expected_run_ids=("run-1",),
            resolution="Must not close unproven legacy decisions.",
        )

    assert store.fetch_all("user_decisions")[0]["status"] == "open"


def test_review_due_every_two_semantic_parents_across_continuations(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=21)
    assert review_due_lineages(store, now=NOW) == []

    record_parent_completion(
        store,
        "lineage-a",
        run_id="run-2",
        parent=22,
        previous_run_id="run-1",
    )

    assert review_due_lineages(store, now=NOW) == ["lineage-a"]


def test_due_lineages_within_ten_minutes_coalesce_into_one_review(tmp_path: Path) -> None:
    clock = MutableClock(NOW - timedelta(minutes=1))
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    clock.value = NOW
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    record_parent_completion(store, "lineage-b", run_id="run-b1", parent=1)
    clock.value = NOW + timedelta(minutes=5)
    record_parent_completion(store, "lineage-b", run_id="run-b2", parent=2)

    requests = schedule_due_reviews(store, now=NOW + timedelta(minutes=5))

    assert len(requests) == 1
    assert requests[0].action_type is ActionType.RUN_REVIEWER
    assert requests[0].metadata["triggering_lineages"] == ["lineage-a", "lineage-b"]
    assert requests[0].metadata["not_before"] == (NOW + timedelta(minutes=10)).isoformat()
    assert requests[0].metadata["reservation_id"].startswith("review-reservation-")
    assert ActionType.RUN_REVIEWER not in ACTION_HANDLERS
    assert review_due_lineages(store, now=NOW + timedelta(minutes=5)) == []
    assert not list(tmp_path.rglob("audit-reports/audit-*.json"))


def test_review_scheduling_skips_busy_lineage_but_keeps_other_due_lineage(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "busy-lineage", run_id="busy-1", parent=1)
    record_parent_completion(
        store,
        "busy-lineage",
        run_id="busy-2",
        parent=2,
        previous_run_id="busy-1",
    )
    record_parent_completion(store, "free-lineage", run_id="free-1", parent=1)
    record_parent_completion(
        store,
        "free-lineage",
        run_id="free-2",
        parent=2,
        previous_run_id="free-1",
    )

    scheduled = schedule_due_reviews(
        store,
        now=NOW,
        busy_run_ids={"busy-2"},
    )

    assert len(scheduled) == 1
    assert scheduled[0].metadata["triggering_lineages"] == ["free-lineage"]
    assert store.count("actions") == 1

    unlocked = schedule_due_reviews(store, now=NOW, busy_run_ids=set())
    assert len(unlocked) == 1
    assert unlocked[0].metadata["triggering_lineages"] == [
        "busy-lineage",
        "free-lineage",
    ]
    store.close()


def test_busy_lineage_filter_does_not_modify_existing_reviewer_lease(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "busy-lineage", run_id="busy-1", parent=1)
    record_parent_completion(
        store,
        "busy-lineage",
        run_id="busy-2",
        parent=2,
        previous_run_id="busy-1",
    )
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)
    leased = store.lease_next_action(
        "busy-reviewer",
        lease_seconds=60,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
        allowed_queue_owners={ActionOwner.REVIEWER.value},
    )
    assert leased is not None
    before = store.get_action(request.action_id)

    assert schedule_due_reviews(
        store,
        now=clock.value,
        busy_run_ids={"busy-2"},
    ) == []
    assert store.get_action(request.action_id) == before
    store.close()


def test_legacy_auditor_production_entrypoints_are_removed(tmp_path: Path) -> None:
    assert not Path("scripts/harness_loop_auditor.py").exists()
    assert not hasattr(orchestrator_module, "_run_auditor")
    assert not list(tmp_path.rglob("audit-reports/audit-*.json"))


def test_legacy_audit_boundary_cannot_emit_report_or_audit_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    legacy_run = {
        "run_id": "legacy-run",
        "policy": "autonomous_knowledge",
        "run_kind": "single",
        "phase": "planning",
        "last_result": "pass",
        "next_action": "run_autonomous_planner",
        "_autonomous_completed_task_ids": ["parent-1"],
    }

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy Auditor producer was invoked")

    monkeypatch.setattr(orchestrator_module, "_apply_audit_gate", forbidden)

    assert _run_audit_boundary(tmp_path, legacy_run, force=True) is None
    assert legacy_run["phase"] == "planning"
    assert not list(tmp_path.rglob("audit-reports/audit-*.json"))


def test_legacy_audit_block_helper_is_disabled_before_state_mutation(
    tmp_path: Path,
) -> None:
    legacy_run = {
        "run_id": "legacy-run",
        "phase": "planning",
        "last_result": "pass",
        "next_action": "run_autonomous_planner",
    }

    with pytest.raises(RuntimeError, match="disabled.*Supervisor Reviewer"):
        _set_audit_blocked(
            tmp_path,
            legacy_run,
            [{"finding_id": "legacy-finding"}],
        )

    assert legacy_run["phase"] == "planning"


def test_later_due_lineage_coalesces_into_pending_review(tmp_path: Path) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)

    first = schedule_due_reviews(store, now=NOW)[0]

    clock.value = NOW + timedelta(minutes=5)
    record_parent_completion(store, "lineage-b", run_id="run-b1", parent=1)
    record_parent_completion(store, "lineage-b", run_id="run-b2", parent=2)
    merged = schedule_due_reviews(store, now=clock.value)

    assert len(merged) == 1
    assert merged[0].action_id == first.action_id
    assert merged[0].metadata["triggering_lineages"] == ["lineage-a", "lineage-b"]
    assert merged[0].metadata["not_before"] == (NOW + timedelta(minutes=10)).isoformat()
    assert store.get_action(first.action_id).status == "pending"
    pending = [
        row
        for row in store.fetch_all("actions")
        if row["action_type"] == ActionType.RUN_REVIEWER.value
        and row["status"] == "pending"
    ]
    assert len(pending) == 1
    assert json.loads(pending[0]["payload_json"])["triggering_lineages"] == [
        "lineage-a",
        "lineage-b",
    ]


def test_terminal_pending_lineage_coalesces_and_advances_only_after_review_completion(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "old-lineage", run_id="old-1", parent=1)
    record_parent_completion(
        store,
        "old-lineage",
        run_id="old-2",
        parent=2,
        previous_run_id="old-1",
    )
    old_request = schedule_due_reviews(store, now=clock.value)[0]

    clock.value = NOW + timedelta(minutes=5)
    _mark_lineage_terminal(store, "old-1", "passed")
    _mark_lineage_terminal(store, "old-2", "passed")
    record_parent_completion(store, "new-lineage", run_id="new-1", parent=1)
    record_parent_completion(
        store,
        "new-lineage",
        run_id="new-2",
        parent=2,
        previous_run_id="new-1",
    )

    requests = schedule_due_reviews(store, now=clock.value)

    assert len(requests) == 1
    request = requests[0]
    assert request.action_id == old_request.action_id
    assert request.metadata["triggering_lineages"] == ["new-lineage", "old-lineage"]
    assert store.get_action(old_request.action_id).status == "pending"
    cadence = store.review_cadence_positions()
    assert cadence["old-lineage"]["reviewed_position"] == 0
    assert cadence["old-lineage"]["reserved_position"] == 2
    assert cadence["new-lineage"]["reviewed_position"] == 0
    assert cadence["new-lineage"]["reserved_position"] == 2

    clock.value = NOW + timedelta(minutes=15)

    def continue_new_lineage(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_queued_reviewer(
        store,
        reviewer_id="reviewer-new-lineage-only",
        driver=continue_new_lineage,
    )

    assert result is not None and result.status == "review_complete"
    reservations = store.fetch_all("review_reservations")
    assert [row["status"] for row in reservations] == ["completed"]
    cadence = store.review_cadence_positions()
    assert cadence["old-lineage"]["reviewed_position"] == 2
    assert cadence["new-lineage"]["reviewed_position"] == 2


def test_queued_reviewer_publishes_findings_before_completing_source_action(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(
        store,
        "lineage-a",
        run_id="run-a2",
        parent=2,
        previous_run_id="run-a1",
    )
    request = schedule_due_reviews(store, now=clock.value)[0]
    clock.value = NOW + timedelta(minutes=10)

    def finding_driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(
                encoding="utf-8"
            )
        )
        evidence_refs = list(evidence["evidence_hashes"].values())
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=evidence_refs,
        )
        candidate["findings"] = [
            {
                "finding_id": "finding-queued-001",
                "finding_key": "queued-finding-publication",
                "status": "open",
                "severity": "should_fix",
                "summary": "Publish this finding before completing the action.",
                "evidence_refs": [evidence_refs[0]],
                "closure_evidence_refs": [],
                "affected_run_ids": ["run-a2"],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_queued_reviewer(
        store,
        reviewer_id="reviewer-finding-publication",
        driver=finding_driver,
    )

    assert result is not None and result.status == "review_complete"
    assert store.get_action(request.action_id).status == "completed"
    assert store.fetch_all("review_reservations")[0]["status"] == "completed"
    findings = store.fetch_all("review_findings")
    assert len(findings) == 1
    assert findings[0]["finding_key"] == "queued-finding-publication"


def test_due_lineage_outside_coalescing_window_gets_separate_reservation(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    first = schedule_due_reviews(store, now=NOW)[0]

    clock.value = NOW + timedelta(minutes=11)
    record_parent_completion(store, "lineage-b", run_id="run-b1", parent=1)
    record_parent_completion(store, "lineage-b", run_id="run-b2", parent=2)
    second = schedule_due_reviews(store, now=clock.value)[0]

    assert first.action_id != second.action_id
    assert first.metadata["triggering_lineages"] == ["lineage-a"]
    assert second.metadata["triggering_lineages"] == ["lineage-b"]
    assert second.metadata["not_before"] == (
        NOW + timedelta(minutes=21)
    ).isoformat()


def test_review_scheduling_uses_transition_registry(tmp_path: Path, monkeypatch) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    observed = []

    def observed_schedule_transition():
        observed.append(True)
        from scripts.loop_supervisor.registry import reviewer_schedule_transition

        return reviewer_schedule_transition()

    monkeypatch.setattr(
        "scripts.loop_supervisor.reviewer.reviewer_schedule_transition",
        observed_schedule_transition,
    )

    schedule_due_reviews(store, now=NOW)

    assert observed == [True]


def test_project_review_reservation_survives_representative_run_revision_change(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    current = store.get_run(request.run_id)
    store.upsert_run_projection(
        {
            "run_id": request.run_id,
            "revision": int(current["revision"]) + 1,
            "loop_lineage_id": "lineage-a",
            "parent_run_id": "run-a1",
            "policy": current["policy"],
            "phase": "planning",
            "status": "actionable",
            "summary": current["summary"]["summary"],
            "artifact_refs": current["summary"]["artifact_refs"],
        }
    )

    assert store.get_action(request.action_id).status == "pending"
    assert review_due_lineages(store, now=NOW) == []


def test_cancelled_review_reservation_releases_cadence_and_requeues(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    first = schedule_due_reviews(store, now=NOW)[0]

    store.release_review_reservation(
        str(first.metadata["reservation_id"]),
        reason="stale pending action",
    )

    assert store.get_action(first.action_id).status == "cancelled"
    assert review_due_lineages(store, now=NOW) == ["lineage-a"]
    second = schedule_due_reviews(store, now=NOW)[0]
    assert second.action_id == first.action_id
    assert store.get_action(second.action_id).status == "pending"


def test_ordinary_worker_lease_cannot_claim_reviewer_owned_action(tmp_path: Path) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    leased = store.lease_next_action(
        "ordinary-worker",
        lease_seconds=60,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
    )

    assert leased is None
    assert store.get_action(request.action_id).status == "pending"


def test_run_decision_does_not_block_project_global_reviewer_lease(tmp_path: Path) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    store.open_user_decision(
        scope="run",
        run_id=request.run_id,
        summary="Only this run needs user input.",
        failure_key="run-only:block",
        required_decision="Resolve the run-specific question.",
    )
    clock.value = NOW + timedelta(minutes=10)

    leased = store.lease_next_action(
        "reviewer-run-isolation",
        lease_seconds=60,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
        allowed_queue_owners={ActionOwner.REVIEWER.value},
    )

    assert leased is not None
    assert leased.action_id == request.action_id


def test_global_decision_blocks_project_global_reviewer_lease(tmp_path: Path) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    store.open_user_decision(
        scope="global",
        summary="Project ownership is uncertain.",
        failure_key="global:block",
        required_decision="Restore trustworthy project ownership.",
    )
    clock.value = NOW + timedelta(minutes=10)

    leased = store.lease_next_action(
        "reviewer-global-block",
        lease_seconds=60,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
        allowed_queue_owners={ActionOwner.REVIEWER.value},
    )

    assert leased is None
    assert store.get_action(request.action_id).status == "pending"


def test_review_evidence_includes_parents_reserved_for_current_review(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    schedule_due_reviews(store, now=NOW)

    bundle = build_review_evidence(tmp_path, store, ["lineage-a"])

    progress = next(
        item
        for item in bundle.evidence["parent_progress"]
        if item["loop_lineage_id"] == "lineage-a"
    )
    assert progress["reviewed_position"] == 0
    assert progress["completed_since_last_review"] == ("parent-1", "parent-2")


def test_supervisor_reviewer_codex_command_uses_read_only_sandbox() -> None:
    command = build_codex_exec_command(
        repo_root=Path("/tmp/repo"),
        output_message_path=Path("/tmp/review.message.json"),
        capabilities={"json": True, "output_last_message": True},
        sandbox_mode="read-only",
    )

    assert command[command.index("--sandbox") + 1] == "read-only"


def test_reviewer_timeout_is_degraded_and_safe_loop_continues(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)

    def fake_codex_timeout(**kwargs: object) -> dict[str, object]:
        assert kwargs["role"] == "supervisor_reviewer"
        return {"status": "timeout", "exit_code": 124}

    result = run_reviewer(
        ReviewerContext(
            project_root=tmp_path,
            store=store,
            triggering_lineages=("lineage-a",),
            deterministic_safety_gates_pass=True,
        ),
        driver=fake_codex_timeout,
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is False
    assert result.review is None
    assert store.fetch_all("reviews")[0]["status"] == "review_degraded"
    assert store.fetch_all("user_decisions") == []


def test_distinct_reviewer_process_consumes_pending_reviewer_action(tmp_path: Path) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def fake_codex_reviewer(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence_path = next(review_dir.glob("review-*-evidence.json"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_queued_reviewer(
        store,
        reviewer_id="supervisor-reviewer-test",
        driver=fake_codex_reviewer,
    )

    assert result is not None and result.status == "review_complete"
    assert store.get_action(request.action_id).status == "completed"
    attempt = store.fetch_all("action_attempts")[0]
    assert attempt["worker_id"] == "supervisor-reviewer-test"
    assert request.action_type not in ACTION_HANDLERS


def test_queued_degraded_review_defers_retry_until_next_cadence(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    record_parent_completion(store, "lineage-a", run_id="run-a3", parent=3)
    record_parent_completion(store, "lineage-a", run_id="run-a4", parent=4)
    request = schedule_due_reviews(store, now=NOW)[0]
    assert request.metadata["cadence_positions"] == {"lineage-a": 2}
    clock.value = NOW + timedelta(minutes=10)

    result = run_queued_reviewer(
        store,
        reviewer_id="supervisor-reviewer-test",
        driver=lambda **_kwargs: {"status": "timeout", "exit_code": 124},
    )

    assert result is not None and result.status == "review_degraded"
    assert result.blocks_safe_runs is False
    assert store.get_action(request.action_id).status == "cancelled"
    reservation = store.fetch_all("review_reservations")[0]
    assert reservation["status"] == "released"
    cadence = store.review_cadence_positions()["lineage-a"]
    assert cadence["reviewed_position"] == 0
    assert cadence["deferred_position"] == 4
    assert cadence["reservation_id"] == ""
    assert review_due_lineages(store, now=clock.value) == []
    assert schedule_due_reviews(store, now=clock.value) == []

    record_parent_completion(store, "lineage-a", run_id="run-a5", parent=5)
    assert review_due_lineages(store, now=clock.value) == []
    record_parent_completion(store, "lineage-a", run_id="run-a6", parent=6)

    assert review_due_lineages(store, now=clock.value) == ["lineage-a"]
    retry = schedule_due_reviews(store, now=clock.value)[0]
    assert retry.action_id != request.action_id
    assert retry.metadata["cadence_positions"] == {"lineage-a": 6}


def test_queued_review_propagates_outbox_failure_without_advancing_cadence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def fake_codex_reviewer(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence_path = next(review_dir.glob("review-*-evidence.json"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    monkeypatch.setattr(
        reviewer_module,
        "apply_review_decision",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("injected outbox failure")
        ),
    )

    with pytest.raises(RuntimeError, match="injected outbox failure"):
        run_queued_reviewer(
            store,
            reviewer_id="supervisor-reviewer-test",
            driver=fake_codex_reviewer,
        )

    assert store.get_action(request.action_id).status == "leased"
    assert store.fetch_all("review_reservations")[0]["status"] == "reserved"
    assert store.review_cadence_positions()["lineage-a"]["reviewed_position"] == 0
    assert store.fetch_all("reviews")[0]["status"] == "review_applying"


def test_queued_reviewer_resumes_persisted_outbox_after_cold_store_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    config = tmp_path / ".codex" / "supervisor" / "config.json"
    config.write_text(json.dumps({"skill_roots": ["skills"]}) + "\n", encoding="utf-8")
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: alpha\ndescription: Validate loop evidence consistently.\n---\n",
        encoding="utf-8",
    )
    for lineage, prefix in (("lineage-a", "run-a"), ("lineage-b", "run-b")):
        record_parent_completion(store, lineage, run_id=f"{prefix}1", parent=1)
        record_parent_completion(store, lineage, run_id=f"{prefix}2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def first_driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence_path = next(review_dir.glob("review-*-evidence.json"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2", "run-b2"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        payload["skill_governance"] = [
            {
                "action": "keep",
                "skill_path": "skills/alpha/SKILL.md",
                "reason": "The accepted review confirms this skill remains required.",
                "evidence_refs": [evidence["evidence_hashes"]["skill_governance"]],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    original_apply = reviewer_module.apply_review_decision
    cut = []

    def cut_after_first_write(store_arg, review, **kwargs):
        def cutpoint(stage: str, run_id: str) -> None:
            if stage == "after_file_write" and not cut:
                cut.append(run_id)
                raise RuntimeError("injected cold-restart cutpoint")

        return original_apply(
            store_arg,
            review,
            application_cutpoint=cutpoint,
            **kwargs,
        )

    monkeypatch.setattr(reviewer_module, "apply_review_decision", cut_after_first_write)
    with pytest.raises(RuntimeError, match="cold-restart cutpoint"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-before-restart",
            driver=first_driver,
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )
    monkeypatch.setattr(reviewer_module, "apply_review_decision", original_apply)

    persisted = store.fetch_all("reviews")[0]
    assert persisted["source_action_id"] == request.action_id
    assert json.loads(persisted["accepted_review_json"])["review_id"] == persisted["review_id"]
    assert not any(
        json.loads(row["snapshot_json"]).get("reviewer_recommendations")
        for row in store.fetch_all("skill_snapshots")
    )
    store.close()
    clock.value += timedelta(seconds=121)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    def forbidden_driver(**_kwargs: object) -> dict[str, object]:
        raise AssertionError("cold recovery must finish before a new LLM call")

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-after-restart",
        driver=forbidden_driver,
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_complete"
    assert reopened.get_action(request.action_id).status == "completed"
    assert reopened.fetch_all("review_applications")[0]["status"] == "completed"
    assert all(
        row["status"] == "applied"
        for row in reopened.fetch_all("review_application_targets")
    )
    recommendation_snapshots = [
        json.loads(row["snapshot_json"])
        for row in reopened.fetch_all("skill_snapshots")
        if json.loads(row["snapshot_json"]).get("reviewer_recommendations")
    ]
    assert len(recommendation_snapshots) == 1
    assert recommendation_snapshots[0]["reviewer_recommendations"][0]["skill_path"] == (
        "skills/alpha/SKILL.md"
    )


def test_queued_reviewer_cold_recovery_bounds_projection_directive_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(
        store,
        "lineage-a",
        run_id="run-a2",
        parent=2,
        project=False,
    )
    run_path = tmp_path / ".codex" / "loop-runs" / "run-a2" / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["reviewer_directives"] = [
        {
            "review_id": f"review-history-{index}",
            "decision": "auto_remediate",
            "summary": "Historic process finding. " * 45,
            "evidence_refs": [f"sha256:{str(index) * 64}"],
        }
        for index in range(4)
    ]
    run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    store.upsert_run_projection(
        {
            "run_id": "run-a2",
            "revision": 1,
            "repo_relative_root": ".",
            "loop_lineage_id": "lineage-a",
            "parent_run_id": "",
            "policy": "autonomous_knowledge",
            "phase": "stopped_budget",
            "status": "actionable",
            "state_fingerprint": _state_fingerprint(payload),
            "summary": json.dumps(
                {
                    "parent_task_counter": 2,
                    "task_id": "parent-2",
                },
                sort_keys=True,
            ),
            "artifact_refs": [run_path.relative_to(tmp_path).as_posix()],
        }
    )
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n",
            encoding="utf-8",
        )
        return {"status": "pass", "exit_code": 0}

    original_apply = reviewer_module.apply_review_decision

    def cut_after_projection(store_arg, review, **kwargs):
        def cutpoint(stage: str, _run_id: str) -> None:
            if stage == "after_file_write":
                raise RuntimeError("injected process loss after projection")

        return original_apply(
            store_arg,
            review,
            application_cutpoint=cutpoint,
            **kwargs,
        )

    monkeypatch.setattr(reviewer_module, "apply_review_decision", cut_after_projection)
    with pytest.raises(RuntimeError, match="process loss after projection"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-before-restart",
            driver=driver,
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )
    monkeypatch.setattr(reviewer_module, "apply_review_decision", original_apply)

    assert store.fetch_all("reviews")[0]["status"] == "review_applying"
    assert store.fetch_all("review_applications")[0]["status"] == "applying"
    store.close()
    clock.value += timedelta(seconds=121)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-after-restart",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("cold recovery must not invoke a new LLM")
        ),
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_complete"
    assert reopened.get_action(request.action_id).status == "completed"
    assert reopened.fetch_all("review_applications")[0]["status"] == "completed"
    projected = reopened.get_run("run-a2")
    projected_summary = json.loads(projected["summary"]["summary"])
    assert "reviewer_directives" not in projected_summary


def test_queued_continue_without_skill_evidence_finalizes_without_recommendation_snapshot(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=[evidence["evidence_hashes"]["objective_constraints"]],
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_queued_reviewer(
        store,
        reviewer_id="reviewer-evidence-subset",
        driver=driver,
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_complete"
    assert store.get_action(request.action_id).status == "completed"
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"
    assert store.review_cadence_positions()["lineage-a"]["reviewed_position"] == 2
    assert not any(
        "reviewer_recommendations" in json.loads(row["snapshot_json"])
        for row in store.fetch_all("skill_snapshots")
    )


def test_cold_continue_without_skill_evidence_finalizes_after_snapshot_cutpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=[evidence["evidence_hashes"]["objective_constraints"]],
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    original_publish = reviewer_module._publish_completed_skill_snapshot
    monkeypatch.setattr(
        reviewer_module,
        "_publish_completed_skill_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("injected pre-snapshot cold-replay cutpoint")
        ),
    )
    with pytest.raises(RuntimeError, match="pre-snapshot cold-replay cutpoint"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-before-evidence-subset-replay",
            driver=driver,
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )
    monkeypatch.setattr(
        reviewer_module,
        "_publish_completed_skill_snapshot",
        original_publish,
    )
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"
    store.close()
    clock.value += timedelta(seconds=121)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-after-evidence-subset-replay",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("cold replay must not invoke a new LLM")
        ),
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_complete"
    assert reopened.get_action(request.action_id).status == "completed"
    assert reopened.fetch_all("reviews")[0]["status"] == "review_complete"
    assert reopened.review_cadence_positions()["lineage-a"]["reviewed_position"] == 2
    assert not any(
        "reviewer_recommendations" in json.loads(row["snapshot_json"])
        for row in reopened.fetch_all("skill_snapshots")
    )


def test_nonempty_skill_governance_without_top_level_skill_hash_degrades_before_acceptance(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    config = tmp_path / ".codex" / "supervisor" / "config.json"
    config.write_text(json.dumps({"skill_roots": ["skills"]}) + "\n", encoding="utf-8")
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: alpha\ndescription: Validate loop evidence consistently.\n---\n",
        encoding="utf-8",
    )
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        objective_hash = evidence["evidence_hashes"]["objective_constraints"]
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=[objective_hash],
        )
        payload["skill_governance"] = [
            {
                "action": "keep",
                "skill_path": "skills/alpha/SKILL.md",
                "reason": "This invalid recommendation omits the Skill section hash.",
                "evidence_refs": [objective_hash],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_queued_reviewer(
        store,
        reviewer_id="reviewer-missing-top-level-skill-hash",
        driver=driver,
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_degraded"
    assert store.get_action(request.action_id).status == "cancelled"
    review_row = store.fetch_all("reviews")[0]
    assert review_row["status"] == "review_degraded"
    assert review_row["accepted_review_json"] == "{}"
    assert store.fetch_all("review_applications") == []
    assert store.fetch_all("skill_snapshots") == []
    cadence = store.review_cadence_positions()["lineage-a"]
    assert cadence["reviewed_position"] == 0
    assert cadence["reserved_position"] == 0


def test_cold_attempt_missing_per_recommendation_skill_hash_releases_cadence(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    config = tmp_path / ".codex" / "supervisor" / "config.json"
    config.write_text(json.dumps({"skill_roots": ["skills"]}) + "\n", encoding="utf-8")
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: alpha\ndescription: Validate loop evidence consistently.\n---\n",
        encoding="utf-8",
    )
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    store.close()
    clock.value = NOW + timedelta(minutes=10)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        objective_hash = evidence["evidence_hashes"]["objective_constraints"]
        skill_hash = evidence["evidence_hashes"]["skill_governance"]
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=[objective_hash, skill_hash],
        )
        payload["skill_governance"] = [
            {
                "action": "keep",
                "skill_path": "skills/alpha/SKILL.md",
                "reason": "The top level cites Skill evidence but this item does not.",
                "evidence_refs": [objective_hash],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-cold-missing-item-skill-hash",
        driver=driver,
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_degraded"
    assert reopened.get_action(request.action_id).status == "cancelled"
    review_row = reopened.fetch_all("reviews")[0]
    assert review_row["status"] == "review_degraded"
    assert review_row["accepted_review_json"] == "{}"
    assert reopened.fetch_all("review_applications") == []
    assert reopened.fetch_all("skill_snapshots") == []
    cadence = reopened.review_cadence_positions()["lineage-a"]
    assert cadence["reviewed_position"] == 0
    assert cadence["reserved_position"] == 0


def test_cold_reviewer_rejects_tampered_skill_evidence_without_overwriting_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    config = tmp_path / ".codex" / "supervisor" / "config.json"
    config.write_text(json.dumps({"skill_roots": ["skills"]}) + "\n", encoding="utf-8")
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: alpha\ndescription: Validate loop evidence consistently.\n---\n",
        encoding="utf-8",
    )
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        payload["skill_governance"] = [
            {
                "action": "keep",
                "skill_path": "skills/alpha/SKILL.md",
                "reason": "The accepted review confirms this skill remains required.",
                "evidence_refs": [evidence["evidence_hashes"]["skill_governance"]],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    monkeypatch.setattr(
        store,
        "complete_reviewer_action",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("injected crash after skill snapshot publication")
        ),
    )
    with pytest.raises(RuntimeError, match="after skill snapshot publication"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-before-snapshot-replay",
            driver=driver,
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )

    snapshot_before = dict(store.fetch_all("skill_snapshots")[0])
    review_row = store.fetch_all("reviews")[0]
    evidence_ref = json.loads(review_row["evidence_json"])[0]
    evidence_path = tmp_path.joinpath(*PurePosixPath(evidence_ref).parts)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["evidence"]["skill_governance"]["inventory"][0]["description"] = (
        "Tampered after publication."
    )
    evidence_path.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
    store.close()
    clock.value += timedelta(seconds=121)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    with pytest.raises(RuntimeError, match="skill_governance evidence hash"):
        run_queued_reviewer(
            reopened,
            reviewer_id="reviewer-after-snapshot-replay",
            driver=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("cold replay must not invoke a new LLM")
            ),
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )

    assert reopened.fetch_all("skill_snapshots") == [snapshot_before]
    assert reopened.get_action(request.action_id).status == "leased"


def test_cold_reviewer_supersedes_accepted_review_without_durable_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(
        store,
        "lineage-a",
        run_id="run-a2",
        parent=2,
        previous_run_id="run-a1",
    )
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def advancing_driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        evidence_ref = next(iter(evidence["evidence_hashes"].values()))
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        candidate["findings"] = [
            {
                "finding_id": "finding-superseded-review",
                "finding_key": "superseded-review",
                "status": "open",
                "summary": "This stale finding must never become active.",
                "severity": "must_fix",
                "evidence_refs": [evidence_ref],
                "closure_evidence_refs": [],
                "affected_run_ids": ["run-a2"],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )

        run_path = tmp_path / ".codex" / "loop-runs" / "run-a2" / "run.json"
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        payload["state_revision"] = 2
        payload["phase"] = "planning"
        payload["next_action"] = "run_autonomous_planner"
        payload["last_result"] = "none"
        run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        refresh_run_projection(store, "run-a2", payload)
        return {"status": "pass", "exit_code": 0}

    original_apply = reviewer_module.apply_review_decision
    monkeypatch.setattr(
        reviewer_module,
        "apply_review_decision",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            LeaseError("injected process loss after accepted review persistence")
        ),
    )
    with pytest.raises(LeaseError, match="process loss"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-before-restart",
            driver=advancing_driver,
            timeout_seconds=1,
            heartbeat_seconds=60,
        )
    monkeypatch.setattr(reviewer_module, "apply_review_decision", original_apply)

    review_id = str(store.fetch_all("reviews")[0]["review_id"])
    assert store.fetch_all("reviews")[0]["status"] == "review_applying"
    assert store.fetch_all("review_applications") == []
    store.close()
    clock.value += timedelta(seconds=121)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    original_supersede = reopened.supersede_review_application

    def supersede_then_lose_process(review_id: str, *, reason: str) -> None:
        original_supersede(review_id, reason=reason)
        raise RuntimeError("injected process loss after review supersession")

    monkeypatch.setattr(
        reopened,
        "supersede_review_application",
        supersede_then_lose_process,
    )
    with pytest.raises(RuntimeError, match="after review supersession"):
        run_queued_reviewer(
            reopened,
            reviewer_id="reviewer-after-first-restart",
            driver=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("accepted cold recovery must not invoke a new LLM")
            ),
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )

    assert reopened.fetch_all("reviews")[0]["status"] == "review_superseded"
    assert reopened.get_action(request.action_id).status == "leased"
    reopened.close()
    clock.value += timedelta(seconds=121)
    recovered = SupervisorStore.open(tmp_path, clock=clock)
    recovered.migrate()

    result = run_queued_reviewer(
        recovered,
        reviewer_id="reviewer-after-second-restart",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("superseded cold recovery must not invoke a new LLM")
        ),
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_degraded"
    assert result.blocks_safe_runs is False
    assert result.review_id == review_id
    assert recovered.fetch_all("reviews")[0]["status"] == "review_superseded"
    assert recovered.fetch_all("review_applications") == []
    assert recovered.fetch_all("review_application_targets") == []
    assert recovered.fetch_all("review_findings") == []
    assert recovered.fetch_all("skill_snapshots") == []
    assert recovered.get_action(request.action_id).status == "cancelled"
    assert not [
        row
        for row in recovered.fetch_all("actions")
        if row["queue_owner"] == ActionOwner.SUPERVISOR.value
        and row["status"] in {"pending", "leased", "running"}
    ]
    cadence = recovered.review_cadence_positions()["lineage-a"]
    assert cadence["reviewed_position"] == 0
    assert cadence["deferred_position"] == 2
    assert cadence["reserved_position"] == 0
    assert review_due_lineages(recovered, now=clock.value) == []
    assert schedule_due_reviews(recovered, now=clock.value) == []


def test_queued_reviewer_resumes_stop_run_outbox_after_terminal_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    for lineage, prefix in (("lineage-a", "run-a"), ("lineage-b", "run-b")):
        record_parent_completion(store, lineage, run_id=f"{prefix}1", parent=1)
        record_parent_completion(store, lineage, run_id=f"{prefix}2", parent=2)
        _mark_lineage_terminal(store, f"{prefix}1", "stopped_budget")
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def first_driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence_path = next(review_dir.glob("review-*-evidence.json"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="stop_run",
            affected_run_ids=["run-a2", "run-b2"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    original_apply = reviewer_module.apply_review_decision
    written: list[str] = []

    def crash_after_first_stop(*args: object, **kwargs: object):
        def cutpoint(stage: str, run_id: str) -> None:
            if stage == "after_file_write" and not written:
                written.append(run_id)
                raise RuntimeError("injected stop-run cold-restart cutpoint")

        return original_apply(*args, application_cutpoint=cutpoint, **kwargs)

    monkeypatch.setattr(reviewer_module, "apply_review_decision", crash_after_first_stop)
    with pytest.raises(RuntimeError, match="stop-run cold-restart cutpoint"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-before-stop-restart",
            driver=first_driver,
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )
    monkeypatch.setattr(reviewer_module, "apply_review_decision", original_apply)

    assert written == ["run-a2"]
    assert store.get_run("run-a1")["status"] == "terminal"
    assert store.get_run("run-a2")["status"] == "terminal"
    persisted_targets = {
        row["run_id"]: (
            row["expected_revision"],
            row["expected_fingerprint"],
            row["expected_post_write_fingerprint"],
        )
        for row in store.review_application_targets(
            store.fetch_all("reviews")[0]["review_id"]
        )
    }
    assert set(persisted_targets) == {"run-a2", "run-b2"}
    accepted_review = json.loads(store.fetch_all("reviews")[0]["accepted_review_json"])
    assert set(accepted_review["reviewed_runs"]) == {
        "run-a1",
        "run-a2",
        "run-b1",
        "run-b2",
    }
    store.close()
    clock.value += timedelta(seconds=121)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-after-stop-restart",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("cold outbox recovery must not invoke a new LLM")
        ),
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_complete"
    assert reopened.get_action(request.action_id).status == "completed"
    assert reopened.fetch_all("review_applications")[0]["status"] == "completed"
    targets = reopened.review_application_targets(result.review_id)
    assert {row["run_id"] for row in targets} == {"run-a2", "run-b2"}
    assert {
        row["run_id"]: (
            row["expected_revision"],
            row["expected_fingerprint"],
            row["expected_post_write_fingerprint"],
        )
        for row in targets
    } == persisted_targets
    assert all(row["status"] == "applied" for row in targets)
    assert reopened.get_run("run-b2")["status"] == "terminal"


def _seed_v10_applying_review(
    tmp_path: Path,
    *,
    accepted_artifact: bool,
    application_targets: bool = True,
    tamper_evidence: bool = False,
    changed_decision: bool = False,
    wrong_source: bool = False,
    reservation: bool = True,
    self_rehash_evidence: bool = False,
    evidence_refs: bool = True,
) -> tuple[SupervisorStore, str, str]:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    bundle = build_review_evidence(tmp_path, store, ("lineage-a",))
    bundle_payload = bundle.as_dict()
    reservation_id = "v10-review-reservation"
    source = ActionRequest(
        action_id="v10-reviewer-action",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="stopped_budget",
        action_type=ActionType.RUN_REVIEWER,
        idempotency_key="v10-reviewer-action",
        queue_owner=ActionOwner.REVIEWER,
        not_before=(store.current_time() - timedelta(minutes=10)).isoformat(),
        task_id="review:v10-reviewer-action",
        next_action="supervisor_reviewer",
        payload={
            "trigger": "regular_cadence",
            "triggering_lineages": list(bundle.triggering_lineages),
            "cadence_positions": dict(bundle.cadence_positions),
            "reservation_id": reservation_id,
            "worker_executable": False,
        },
    )
    if reservation:
        store.reserve_review_action(
            source,
            reservation_id=reservation_id,
            lineage_positions=bundle.cadence_positions,
            due_at=store.current_time() - timedelta(minutes=20),
            not_before=store.current_time() - timedelta(minutes=10),
        )
    else:
        store.enqueue_action(source)
    review_id = "review-v10-applying"
    review_dir = tmp_path / ".codex" / "supervisor" / "reviews" / review_id
    review_dir.mkdir(parents=True)
    evidence_path = review_dir / f"{review_id}-evidence.json"
    accepted_path = review_dir / f"{review_id}.json"
    if tamper_evidence:
        bundle_payload["evidence"]["objective_constraints"][0]["constraints"] = [
            "tampered after acceptance"
        ]
    if self_rehash_evidence:
        evidence_hashes = {
            name: "sha256:"
            + hashlib.sha256(
                reviewer_module._canonical_json({"section": name, "value": value})
            ).hexdigest()
            for name, value in bundle_payload["evidence"].items()
        }
        bundle_payload["evidence_hashes"] = evidence_hashes
        bundle_payload["bundle_hash"] = "sha256:" + hashlib.sha256(
            reviewer_module._canonical_json(
                {
                    "triggering_lineages": bundle_payload["triggering_lineages"],
                    "cadence_positions": bundle_payload["cadence_positions"],
                    "evidence_hashes": evidence_hashes,
                }
            )
        ).hexdigest()
    evidence_path.write_text(
        json.dumps(bundle_payload) + "\n", encoding="utf-8"
    )
    candidate = valid_review_payload(
        review_id=review_id,
        decision="refocus",
        affected_run_ids=["run-1"],
        evidence_refs=list(bundle_payload["evidence_hashes"].values()),
    )
    if changed_decision:
        candidate["decision"] = "stop_run"
    if accepted_artifact:
        accepted_path.write_text(json.dumps(candidate) + "\n", encoding="utf-8")
    gate_id = "review-gate-v10-applying"
    store.record_review_safety_gate(gate_id, status="pass", checks={"passed": True})
    store.record_review(
        review_id=review_id,
        trigger=json.dumps(
            {
                "kind": "project_global",
                "triggering_lineages": list(bundle.triggering_lineages),
                "cadence_positions": dict(bundle.cadence_positions),
                "safety_gate_id": gate_id,
            }
        ),
        status="review_applying",
        decision="refocus",
        summary=str(candidate["summary"]),
        evidence_refs=(
            [
                evidence_path.relative_to(tmp_path).as_posix(),
                accepted_path.relative_to(tmp_path).as_posix(),
            ]
            if evidence_refs
            else []
        ),
    )
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    run_payload = json.loads(run_path.read_text(encoding="utf-8"))
    expected_fingerprint = _state_fingerprint(run_payload)
    target = ActionRequest(
        action_id="v10-review-target",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="stopped_budget",
        action_type=ActionType.REFOCUS_RUN,
        idempotency_key="v10-review-target",
        queue_owner=ActionOwner.SUPERVISOR,
        payload={
            "review_id": review_id,
            "review_decision": "refocus",
            "expected_revision": 1,
            "expected_fingerprint": expected_fingerprint,
            "worker_executable": False,
        },
    )
    if application_targets:
        store.prepare_review_application(
            review_id=review_id,
            decision="refocus",
            targets=[
                (
                    target,
                    {
                        "expected_revision": 1,
                        "expected_fingerprint": expected_fingerprint,
                        "source_phase": "stopped_budget",
                        "target_phase": "planning",
                        "target_next_action": "run_autonomous_planner",
                        "target_last_result": "none",
                    },
                )
            ],
        )
    if wrong_source:
        store._connection.execute(
            "UPDATE actions SET status = 'completed' WHERE action_id = ?",
            (source.action_id,),
        )
        rogue = ActionRequest(
            action_id="v10-rogue-reviewer-action",
            run_id="run-1",
            run_revision=1,
            policy="autonomous_knowledge",
            phase="stopped_budget",
            action_type=ActionType.RUN_REVIEWER,
            idempotency_key="v10-rogue-reviewer-action",
            queue_owner=ActionOwner.REVIEWER,
            task_id="review:v10-rogue",
            next_action="supervisor_reviewer",
            payload={"triggering_lineages": ["wrong-lineage"]},
        )
        store.enqueue_action(rogue)
    store._connection.execute("ALTER TABLE reviews DROP COLUMN accepted_review_json")
    store._connection.execute("ALTER TABLE reviews DROP COLUMN source_action_id")
    store._connection.execute("PRAGMA user_version=10")
    store._connection.commit()
    store.close()
    return store, source.action_id, review_id


def test_v10_applying_review_blocks_without_immutable_anchor_before_new_llm(
    tmp_path: Path,
) -> None:
    _seed_v10_applying_review(tmp_path, accepted_artifact=True)
    reopened = SupervisorStore.open(tmp_path)
    reopened.migrate()

    def forbidden_driver(**_kwargs: object) -> dict[str, object]:
        raise AssertionError("v10 reconstruction must run before a new LLM")

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-v10-reopen",
        driver=forbidden_driver,
    )

    assert result is None
    review = reopened.fetch_all("reviews")[0]
    assert review["status"] == "review_migration_blocked"
    assert review["source_action_id"] == ""
    assert reopened.get_action("v10-reviewer-action").status == "pending"


def test_v10_self_rehashed_evidence_blocks_without_llm_reinvocation(
    tmp_path: Path,
) -> None:
    _seed_v10_applying_review(
        tmp_path,
        accepted_artifact=True,
        tamper_evidence=True,
        self_rehash_evidence=True,
    )
    reopened = SupervisorStore.open(tmp_path)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-v10-self-rehashed",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("unanchored v10 migration must not invoke an LLM")
        ),
    )

    assert result is None
    review = reopened.fetch_all("reviews")[0]
    assert review["status"] == "review_migration_blocked"
    assert review["source_action_id"] == ""
    assert reopened.get_action("v10-reviewer-action").status == "pending"


def test_v10_applying_review_without_evidence_refs_blocks_without_llm(
    tmp_path: Path,
) -> None:
    _seed_v10_applying_review(
        tmp_path,
        accepted_artifact=False,
        evidence_refs=False,
    )
    reopened = SupervisorStore.open(tmp_path)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-v10-empty-evidence",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("unanchored v10 migration must not invoke an LLM")
        ),
    )

    assert result is None
    assert reopened.fetch_all("reviews")[0]["status"] == "review_migration_blocked"


def test_v10_applying_review_without_trusted_artifact_blocks_llm_reinvocation(
    tmp_path: Path,
) -> None:
    _seed_v10_applying_review(tmp_path, accepted_artifact=False)
    reopened = SupervisorStore.open(tmp_path)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-v10-blocked",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("blocked v10 migration must not invoke an LLM")
        ),
    )

    assert result is None
    review = reopened.fetch_all("reviews")[0]
    assert review["status"] == "review_migration_blocked"
    assert review["source_action_id"] == ""
    assert reopened.get_action("v10-reviewer-action").status == "pending"


def test_v10_affected_review_without_revision_targets_blocks_llm_reinvocation(
    tmp_path: Path,
) -> None:
    _seed_v10_applying_review(
        tmp_path,
        accepted_artifact=True,
        application_targets=False,
    )
    reopened = SupervisorStore.open(tmp_path)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-v10-unbound",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("unbound v10 migration must not invoke an LLM")
        ),
    )

    assert result is None
    review = reopened.fetch_all("reviews")[0]
    assert review["status"] == "review_migration_blocked"
    assert review["source_action_id"] == ""
    assert reopened.get_action("v10-reviewer-action").status == "pending"


@pytest.mark.parametrize(
    "fixture_options",
    [
        {"tamper_evidence": True},
        {"changed_decision": True},
        {"reservation": False},
        {"wrong_source": True},
    ],
)
def test_v10_untrusted_identity_or_artifacts_block_llm_reinvocation(
    tmp_path: Path,
    fixture_options: dict[str, bool],
) -> None:
    _seed_v10_applying_review(
        tmp_path,
        accepted_artifact=True,
        **fixture_options,
    )
    reopened = SupervisorStore.open(tmp_path)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-v10-untrusted",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("untrusted v10 migration must not invoke an LLM")
        ),
    )

    assert result is None
    review = reopened.fetch_all("reviews")[0]
    assert review["status"] == "review_migration_blocked"
    if fixture_options.get("wrong_source"):
        assert review["source_action_id"] != "v10-rogue-reviewer-action"


def test_reviewer_module_exposes_distinct_once_service_path(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.loop_supervisor.reviewer",
            "--project-root",
            str(tmp_path),
            "--once",
            "--reviewer-id",
            "reviewer-cli-test",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "idle"


def test_reviewer_failure_blocks_when_deterministic_safety_gate_fails(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    store.open_user_decision(
        scope="global",
        summary="Repository ownership is uncertain.",
        failure_key="ownership:global",
        required_decision="Resolve ownership before automation continues.",
    )

    result = run_reviewer(
        ReviewerContext(
            project_root=tmp_path,
            store=store,
            triggering_lineages=("lineage-a",),
        ),
        driver=lambda **_kwargs: {"status": "timeout", "exit_code": 124},
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is True


def test_evidence_build_failure_uses_fresh_deterministic_gate(
    tmp_path: Path, monkeypatch
) -> None:
    safe_store = migrated_store(tmp_path / "safe")
    record_parent_completion(safe_store, "lineage-a", run_id="run-safe", parent=1)
    monkeypatch.setattr(
        "scripts.loop_supervisor.reviewer.build_review_evidence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("evidence unavailable")),
    )

    safe = run_reviewer(
        ReviewerContext(
            project_root=tmp_path / "safe",
            store=safe_store,
            triggering_lineages=("lineage-a",),
        )
    )

    assert safe.status == "review_degraded"
    assert safe.blocks_safe_runs is False
    safe_gate = safe_store.fetch_all("review_safety_gates")[-1]
    assert safe_gate["status"] == "pass"

    blocked_store = migrated_store(tmp_path / "blocked")
    record_parent_completion(
        blocked_store, "lineage-b", run_id="run-blocked", parent=1
    )
    blocked_store.open_user_decision(
        scope="global",
        summary="Repository ownership is uncertain.",
        failure_key="ownership:global",
        required_decision="Resolve ownership before automation continues.",
    )

    blocked = run_reviewer(
        ReviewerContext(
            project_root=tmp_path / "blocked",
            store=blocked_store,
            triggering_lineages=("lineage-b",),
            deterministic_safety_gates_pass=True,
        )
    )

    assert blocked.status == "review_degraded"
    assert blocked.blocks_safe_runs is True
    blocked_gate = blocked_store.fetch_all("review_safety_gates")[-1]
    assert blocked_gate["status"] == "fail"


@pytest.mark.parametrize(
    ("signal", "expected_signal"),
    [
        ("secret_exposure_confirmed", "secret_exposure"),
        ("repo_corruption", "repo_corruption"),
        ("permission_expansion_required", "permission_expansion_required"),
        ("irreversible_operation_required", "irreversible_operation_required"),
        ("explicit_global_stop", "explicit_global_stop"),
    ],
)
def test_reviewer_fail_open_gate_reads_fresh_owned_global_safety_signals(
    tmp_path: Path,
    signal: str,
    expected_signal: str,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload[signal] = True
    payload["state_revision"] += 1
    run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    refresh_run_projection(store, "run-1", payload)

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=lambda **_kwargs: {"status": "timeout", "exit_code": 124},
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is True
    assert store.fetch_all("user_decisions") == []
    gate = store.fetch_all("review_safety_gates")[-1]
    checks = json.loads(gate["checks_json"])
    assert checks["fresh_global_safety_signals"] == [
        {"run_id": "run-1", "signal": expected_signal}
    ]


def test_reviewer_recomputes_global_decisions_after_driver_before_fail_open(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)

    def driver(**_kwargs: object) -> dict[str, object]:
        store.open_user_decision(
            scope="global",
            summary="Stop while Reviewer is running.",
            failure_key="global-stop:in-flight",
            required_decision="Resolve the global stop.",
        )
        return {"status": "timeout", "exit_code": 124}

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=driver,
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is True
    assert [row["status"] for row in store.fetch_all("review_safety_gates")] == [
        "pass",
        "fail",
        "fail",
    ]


def test_reviewer_driver_exception_blocks_on_missing_canonical_run_state(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)

    def driver(**_kwargs: object) -> dict[str, object]:
        store._connection.execute(
            "UPDATE runs SET summary_json = ? WHERE run_id = ?",
            (json.dumps({"summary": "missing canonical state", "artifact_refs": []}), "run-1"),
        )
        raise RuntimeError("Reviewer driver crashed")

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=driver,
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is True
    gate = store.fetch_all("review_safety_gates")[-1]
    checks = json.loads(gate["checks_json"])
    assert gate["status"] == "fail"
    assert checks["fresh_global_safety_signals"] == [
        {"run_id": "run-1", "signal": "repo_corruption"}
    ]


@pytest.mark.parametrize("action_status", ["pending", "leased"])
def test_reviewer_safety_allows_canonical_projectionless_service_keeper_action(
    tmp_path: Path,
    action_status: str,
) -> None:
    store = migrated_store(tmp_path)
    store.upsert_service_observation(
        service_id="loop-dashboard",
        status="unhealthy",
        details={"endpoint_verified": False},
    )
    outage_id = json.loads(store.fetch_all("services")[0]["details_json"])[
        "outage_id"
    ]
    request = service_keeper_action_request(
        outage_id=outage_id,
        idempotency_key=f"service-restart:loop-dashboard:{outage_id}",
    )
    store.enqueue_action(request)
    if action_status == "leased":
        claimed = store.claim_service_restart_action(
            request.action_id,
            "supervisor-service-keeper-test",
            service_id="loop-dashboard",
            outage_id=outage_id,
            lease_seconds=120,
        )
        assert claimed is not None and claimed.status == "leased"

    checks = current_review_safety_checks(store)

    assert checks["fresh_global_safety_signals"] == []
    assert checks["no_fresh_global_safety_signals"] is True


@pytest.mark.parametrize(
    "action_request",
    [
        service_keeper_action_request(
            action_id="arbitrary-supervisor-action",
            run_id="projectionless-run",
            action_type=ActionType.REFOCUS_RUN,
            idempotency_key="arbitrary-supervisor-action",
        ),
        service_keeper_action_request(
            action_id="malformed-service-restart",
            outage_id=None,
        ),
        service_keeper_action_request(
            action_id="mismatched-service-restart-key",
            idempotency_key="service-restart:loop-dashboard:other-outage",
        ),
        service_keeper_action_request(
            action_id="unknown-service-restart",
            service_id="unknown-service",
            idempotency_key="service-restart:unknown-service:outage-1",
        ),
        service_keeper_action_request(
            action_id="wrong-service-keeper-revision",
            run_revision=1,
        ),
        service_keeper_action_request(
            action_id="wrong-service-keeper-action-type",
            action_type=ActionType.REFOCUS_RUN,
            idempotency_key="service-restart:loop-dashboard:outage-1",
        ),
    ],
    ids=[
        "arbitrary-supervisor-action",
        "malformed-payload",
        "mismatched-idempotency-key",
        "service-not-allowlisted",
        "wrong-pseudo-run-identity",
        "other-action-type",
    ],
)
def test_reviewer_safety_rejects_noncanonical_projectionless_supervisor_action(
    tmp_path: Path,
    action_request: ActionRequest,
) -> None:
    store = migrated_store(tmp_path)
    store.enqueue_action(action_request)

    checks = current_review_safety_checks(store)

    assert checks["fresh_global_safety_signals"] == [
        {"run_id": action_request.run_id, "signal": "repo_corruption"}
    ]
    assert checks["no_fresh_global_safety_signals"] is False


@pytest.mark.parametrize(
    "state_problem",
    [
        "malformed",
        "malformed_json",
        "missing",
        "run_id",
        "revision",
        "revision_rollback",
        "revision_jump",
        "fingerprint",
        "orphaned",
    ],
)
def test_reviewer_rejects_noncanonical_run_state_before_degraded_fail_open(
    tmp_path: Path,
    state_problem: str,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"

    def driver(**_kwargs: object) -> dict[str, object]:
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        if state_problem == "malformed":
            run_path.write_text(json.dumps({"run_id": "run-1"}) + "\n", encoding="utf-8")
        elif state_problem == "malformed_json":
            run_path.write_text("{\n", encoding="utf-8")
        elif state_problem == "missing":
            run_path.unlink()
        elif state_problem == "run_id":
            payload["run_id"] = "other-run"
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        elif state_problem == "revision":
            payload["state_revision"] = 2
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        elif state_problem == "revision_rollback":
            payload["state_revision"] = 0
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        elif state_problem == "revision_jump":
            payload["state_revision"] = 3
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        elif state_problem == "fingerprint":
            payload["requirement"] = "mutated without reconciliation"
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        else:
            orphan_path = tmp_path / "orphan" / ".codex" / "loop-runs" / "run-1" / "run.json"
            orphan_path.parent.mkdir(parents=True)
            orphan_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            store._connection.execute(
                "UPDATE runs SET summary_json = ? WHERE run_id = ?",
                (
                    json.dumps(
                        {
                            "summary": "orphaned canonical state",
                            "artifact_refs": [
                                orphan_path.relative_to(tmp_path).as_posix()
                            ],
                        }
                    ),
                    "run-1",
                ),
            )
        return {"status": "timeout", "exit_code": 124}

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=driver,
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is True
    checks = json.loads(store.fetch_all("review_safety_gates")[-1]["checks_json"])
    assert checks["fresh_global_safety_signals"] == [
        {"run_id": "run-1", "signal": "repo_corruption"}
    ]


def test_queued_reviewer_blocks_application_and_completion_for_noncanonical_state(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-a2" / "run.json"
    before = run_path.read_bytes()

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        bundle = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2"],
            evidence_refs=list(bundle["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        payload["state_revision"] = 2
        run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return {"status": "pass", "exit_code": 0}

    with pytest.raises(LeaseError, match="canonical global signal"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-canonical-state",
            driver=driver,
        )

    assert store.get_action(request.action_id).status == "leased"
    assert store.fetch_all("review_applications") == []
    assert store.fetch_all("action_attempts") == []
    assert store.fetch_all("reviews") == []
    checks = json.loads(store.fetch_all("review_safety_gates")[-1]["checks_json"])
    assert checks["fresh_global_safety_signals"] == [
        {"run_id": "run-a2", "signal": "repo_corruption"}
    ]
    assert run_path.read_bytes() != before


def test_queued_reviewer_orphaned_source_projection_never_invokes_driver(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    store._connection.execute("DELETE FROM runs WHERE run_id = ?", (request.run_id,))
    clock.value = NOW + timedelta(minutes=10)

    result = run_queued_reviewer(
        store,
        reviewer_id="reviewer-orphaned-source",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("orphaned source must block before any LLM invocation")
        ),
    )

    assert result is None
    assert store.get_action(request.action_id).status == "pending"
    assert current_review_safety_checks(store)["fresh_global_safety_signals"] == [
        {"run_id": request.run_id, "signal": "repo_corruption"}
    ]


@pytest.mark.parametrize(
    "tampered_field",
    [None, "requirement", "constraints", "allowed_paths", "policy", "last_result"],
)
def test_cold_reviewer_recovery_repairs_projection_after_file_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tampered_field: str | None,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def first_driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        bundle = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2"],
            evidence_refs=list(bundle["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    original_project = reviewer_outbox_module._project_saved_run
    monkeypatch.setattr(reviewer_outbox_module, "_project_saved_run", lambda *_args: None)
    original_apply = reviewer_module.apply_review_decision

    def cut_after_file_write(*args: object, **kwargs: object):
        def cutpoint(stage: str, _run_id: str) -> None:
            if stage == "after_file_write":
                raise RuntimeError("projection persistence cutpoint")

        return original_apply(*args, application_cutpoint=cutpoint, **kwargs)

    monkeypatch.setattr(reviewer_module, "apply_review_decision", cut_after_file_write)
    with pytest.raises(RuntimeError, match="projection persistence cutpoint"):
        run_queued_reviewer(
            store,
            reviewer_id="reviewer-before-projection-repair",
            driver=first_driver,
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )
    monkeypatch.setattr(reviewer_outbox_module, "_project_saved_run", original_project)
    monkeypatch.setattr(reviewer_module, "apply_review_decision", original_apply)

    stale = store.get_run("run-a2")
    assert stale["revision"] == 1
    saved_payload = json.loads(
        (tmp_path / ".codex" / "loop-runs" / "run-a2" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved_payload["state_revision"] == 2
    target = store.fetch_all("review_application_targets")[0]
    assert target["expected_post_write_fingerprint"] == _state_fingerprint(
        saved_payload
    )
    if tampered_field is not None:
        run_path = tmp_path / ".codex" / "loop-runs" / "run-a2" / "run.json"
        replaced = json.loads(run_path.read_text(encoding="utf-8"))
        replacements: dict[str, object] = {
            "requirement": "Tampered review objective.",
            "constraints": ["Tampered immutable constraint."],
            "allowed_paths": ["scripts/tampered.py"],
            "policy": "demand_development",
            "last_result": "pass",
        }
        replaced[tampered_field] = replacements[tampered_field]
        run_path.write_text(json.dumps(replaced) + "\n", encoding="utf-8")
    store.close()
    clock.value += timedelta(seconds=121)
    reopened = SupervisorStore.open(tmp_path, clock=clock)
    reopened.migrate()

    if tampered_field is not None:
        with pytest.raises(LeaseError, match="canonical state is corrupt"):
            run_queued_reviewer(
                reopened,
                reviewer_id="reviewer-after-projection-repair",
                driver=lambda **_kwargs: (_ for _ in ()).throw(
                    AssertionError("corrupt cold recovery must not invoke a new LLM")
                ),
                timeout_seconds=1,
                heartbeat_seconds=0.01,
            )
        assert reopened.get_run("run-a2")["revision"] == 1
        assert reopened.get_action(request.action_id).status == "leased"
    else:
        result = run_queued_reviewer(
            reopened,
            reviewer_id="reviewer-after-projection-repair",
            driver=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("cold outbox recovery must not invoke a new LLM")
            ),
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )

        assert result is not None and result.status == "review_complete"
        assert reopened.get_run("run-a2")["revision"] == 2
        assert reopened.get_action(request.action_id).status == "completed"


def test_v12_worktree_projection_migration_backfills_root_for_outbox(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / ".worktrees" / "v12-child"
    store = migrated_store(tmp_path, MutableClock(NOW))
    record_parent_completion(
        store,
        "lineage-v12",
        run_id="v12-a1",
        parent=1,
        execution_root=worktree,
        project=False,
    )
    record_parent_completion(
        store,
        "lineage-v12",
        run_id="v12-a2",
        parent=2,
        execution_root=worktree,
        project=False,
    )
    reconcile_once(tmp_path, store)
    store._connection.execute("ALTER TABLE runs DROP COLUMN repo_relative_root")
    store._connection.execute("PRAGMA user_version=12")
    store._connection.commit()
    store.close()

    reopened = SupervisorStore.open(tmp_path, clock=MutableClock(NOW))
    reopened.migrate()
    reconcile_once(tmp_path, reopened)

    assert reopened.get_run("v12-a2")["repo_relative_root"] == ".worktrees/v12-child"
    assert current_review_safety_checks(reopened)["fresh_global_safety_signals"] == []
    payload = json.loads(
        (
            worktree / ".codex" / "loop-runs" / "v12-a2" / "run.json"
        ).read_text(encoding="utf-8")
    )
    review = validate_review_payload(
        valid_review_payload(
            decision="refocus",
            affected_run_ids=["v12-a2"],
        ),
        allowed_run_ids=["v12-a2"],
        reviewed_runs={
            "v12-a2": {
                "revision": payload["state_revision"],
                "state_fingerprint": _state_fingerprint(payload),
            }
        },
    )
    actions = apply_review_decision(reopened, review)

    assert reopened.get_action(actions[0].action_id).status == "completed"


def test_v12_arbitrary_projection_prefix_remains_unregistered(
    tmp_path: Path,
) -> None:
    unregistered = tmp_path / "arbitrary" / "prefix"
    store = migrated_store(tmp_path, MutableClock(NOW))
    record_parent_completion(
        store,
        "lineage-unregistered",
        run_id="unregistered-run",
        parent=1,
        execution_root=unregistered,
    )
    store._connection.execute("ALTER TABLE runs DROP COLUMN repo_relative_root")
    store._connection.execute("PRAGMA user_version=12")
    store._connection.commit()
    store.close()

    reopened = SupervisorStore.open(tmp_path, clock=MutableClock(NOW))
    reopened.migrate()

    assert reopened.get_run("unregistered-run")["repo_relative_root"] == "."
    assert current_review_safety_checks(reopened)["fresh_global_safety_signals"] == [
        {"run_id": "unregistered-run", "signal": "repo_corruption"}
    ]


def _seed_v13_pending_review_target(
    tmp_path: Path,
    *,
    mode: str,
) -> tuple[SupervisorStore, ActionRequest]:
    store = migrated_store(tmp_path, MutableClock(NOW))
    record_parent_completion(store, "lineage-v13", run_id="v13-run", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "v13-run" / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-v13-target",
            decision="refocus",
            affected_run_ids=["v13-run"],
        ),
        allowed_run_ids=["v13-run"],
        reviewed_runs={
            "v13-run": {
                "revision": payload["state_revision"],
                "state_fingerprint": _state_fingerprint(payload),
            }
        },
    )
    source = ActionRequest(
        action_id="v13-reviewer-source",
        run_id="v13-run",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="stopped_budget",
        action_type=ActionType.RUN_REVIEWER,
        idempotency_key="v13-reviewer-source",
        queue_owner=ActionOwner.REVIEWER,
        task_id="review:v13",
        next_action="supervisor_reviewer",
        payload={"triggering_lineages": ["lineage-v13"]},
    )
    store.enqueue_action(source)
    request, target, _root, _path = reviewer_outbox_module._prepare_target(
        store,
        review,
        "v13-run",
    )
    store.record_review(
        review_id=review.review_id,
        trigger="v13-migration-fixture",
        status="review_applying",
        decision=review.decision.value,
        summary=review.summary,
        accepted_review=reviewer_module._persisted_review(review),
        source_action_id=source.action_id,
    )
    store.prepare_review_application(
        review_id=review.review_id,
        decision=review.decision.value,
        targets=[(request, target)],
    )
    if mode == "post_write":
        updated = reviewer_outbox_module._updated_payload(payload, review, target)
        updated["state_revision"] = 2
        run_path.write_text(json.dumps(updated) + "\n", encoding="utf-8")
    elif mode == "tampered":
        payload["requirement"] = "Tampered legacy pre-write state."
        run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    elif mode == "ambiguous":
        run = store.get_run("v13-run")
        summary = dict(run["summary"])
        summary["artifact_refs"] = list(summary["artifact_refs"]) * 2
        store._connection.execute(
            "UPDATE runs SET summary_json = ? WHERE run_id = ?",
            (json.dumps(summary), "v13-run"),
        )
    elif mode != "pre_write":
        raise ValueError(mode)
    store._connection.execute(
        "ALTER TABLE review_application_targets "
        "DROP COLUMN expected_post_write_fingerprint"
    )
    store._connection.execute("PRAGMA user_version=13")
    store._connection.commit()
    store.close()
    return SupervisorStore.open(tmp_path, clock=MutableClock(NOW)), source


def test_v13_prewrite_target_migration_derives_post_write_fingerprint(
    tmp_path: Path,
) -> None:
    reopened, source = _seed_v13_pending_review_target(tmp_path, mode="pre_write")
    reopened.migrate()

    target = reopened.review_application_targets("review-v13-target")[0]
    assert target["expected_post_write_fingerprint"].startswith("sha256:")
    result = run_queued_reviewer(
        reopened,
        reviewer_id="reviewer-v13-safe-migration",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("safe v13 recovery must not invoke a new LLM")
        ),
    )

    assert result is not None and result.status == "review_complete"
    assert reopened.get_action(source.action_id).status == "completed"


@pytest.mark.parametrize("mode", ["post_write", "tampered", "ambiguous"])
def test_v13_non_prewrite_target_migration_blocks_llm_reinvocation(
    tmp_path: Path,
    mode: str,
) -> None:
    reopened, _source = _seed_v13_pending_review_target(tmp_path, mode=mode)
    reopened.migrate()

    result = run_queued_reviewer(
        reopened,
        reviewer_id=f"reviewer-v13-{mode}-migration",
        driver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("blocked v13 recovery must not invoke a new LLM")
        ),
    )

    assert result is None
    assert reopened.fetch_all("reviews")[0]["status"] == "review_migration_blocked"


def test_operator_can_supersede_blocked_review_migration_without_applying_it(
    tmp_path: Path,
) -> None:
    reopened, source = _seed_v13_pending_review_target(tmp_path, mode="tampered")
    reopened.migrate()

    result = reopened.resolve_blocked_review_migration(
        "review-v13-target",
        reason="The repository changed during the runtime upgrade.",
    )

    assert result == {
        "review_id": "review-v13-target",
        "source_action_id": source.action_id,
        "retried_action_id": "",
        "status": "review_superseded",
    }
    assert reopened.has_blocked_review_migration() is False
    assert reopened.fetch_all("reviews")[0]["status"] == "review_superseded"
    assert reopened.get_action(source.action_id).status == "cancelled"
    assert {
        target["status"]
        for target in reopened.review_application_targets("review-v13-target")
    } == {"superseded"}


def test_operator_resolution_can_retry_failed_source_recovery_action(
    tmp_path: Path,
) -> None:
    reopened, reviewer_source = _seed_v13_pending_review_target(
        tmp_path, mode="tampered"
    )
    reopened.migrate()
    failed_source = ActionRequest(
        action_id="v13-failed-recovery-source",
        run_id="v13-run",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="stopped_budget",
        action_type=ActionType.RECOVER_GENERATOR_RESULT,
        idempotency_key="v13-failed-recovery-source",
        queue_owner=ActionOwner.WORKER,
        task_id="v13-task",
        next_action="inspect_autonomous_dirty_paths",
    )
    reopened.enqueue_action(failed_source)
    leased = reopened.lease_next_action(
        "worker-v13-failure",
        lease_seconds=60,
        allowed_action_types={ActionType.RECOVER_GENERATOR_RESULT.value},
    )
    assert leased is not None and leased.action_id == failed_source.action_id
    reopened.complete_action(
        failed_source.action_id,
        "worker-v13-failure",
        ActionResult(
            result_class=ActionResultClass.RETRYABLE_FAILURE,
            summary="Old runtime rejected the recoverable baseline.",
            failure_key="v13:baseline",
            error_class="RuntimeError",
        ),
    )
    reviewer_payload = reviewer_source.payload_for_storage()
    reviewer_payload.update(
        {
            "recovery_stage": "reviewer",
            "source_action_id": failed_source.action_id,
        }
    )
    reopened._connection.execute(
        "UPDATE actions SET payload_json = ? WHERE action_id = ?",
        (json.dumps(reviewer_payload), reviewer_source.action_id),
    )

    result = reopened.resolve_blocked_review_migration(
        "review-v13-target",
        reason="The deterministic gate was fixed and verified.",
        retry_source_action=True,
    )

    assert result["retried_action_id"] == failed_source.action_id
    assert reopened.get_action(reviewer_source.action_id).status == "cancelled"
    assert reopened.get_action(failed_source.action_id).status == "pending"


def test_reconciled_worktree_root_is_required_for_reviewer_outbox(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / ".worktrees" / "reviewer-child"
    store = migrated_store(tmp_path, MutableClock(NOW))
    record_parent_completion(
        store,
        "lineage-worktree",
        run_id="worktree-a1",
        parent=1,
        execution_root=worktree,
        project=False,
    )
    record_parent_completion(
        store,
        "lineage-worktree",
        run_id="worktree-a2",
        parent=2,
        execution_root=worktree,
        project=False,
    )
    reconcile_once(tmp_path, store)

    payload = json.loads(
        (
            worktree / ".codex" / "loop-runs" / "worktree-a2" / "run.json"
        ).read_text(encoding="utf-8")
    )
    assert current_review_safety_checks(store)["fresh_global_safety_signals"] == [], {
        "run": store.get_run("worktree-a2"),
        "payload": payload,
    }
    actions = apply_review_decision(
        store,
        validate_review_payload(
            valid_review_payload(
                decision="refocus",
                affected_run_ids=["worktree-a2"],
            ),
            allowed_run_ids=["worktree-a2"],
            reviewed_runs={
                "worktree-a2": {
                    "revision": payload["state_revision"],
                    "state_fingerprint": _state_fingerprint(payload),
                }
            },
        ),
    )

    assert store.get_run("worktree-a2")["repo_relative_root"] == ".worktrees/reviewer-child"
    assert store.get_action(actions[0].action_id).status == "completed"
    store._connection.execute(
        "UPDATE runs SET repo_relative_root = ? WHERE run_id = ?",
        ("arbitrary/prefix", "worktree-a2"),
    )
    assert current_review_safety_checks(store)["fresh_global_safety_signals"] == [
        {"run_id": "worktree-a2", "signal": "repo_corruption"}
    ]


@pytest.mark.parametrize(
    "signal",
    [
        "secret_exposure_confirmed",
        "repo_corruption",
        "permission_expansion_required",
        "irreversible_operation_required",
        "explicit_global_stop",
    ],
)
def test_reviewer_recomputes_each_canonical_signal_after_driver(
    tmp_path: Path,
    signal: str,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"

    def driver(**_kwargs: object) -> dict[str, object]:
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        payload[signal] = True
        payload["state_revision"] += 1
        run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        refresh_run_projection(store, "run-1", payload)
        return {"status": "timeout", "exit_code": 124}

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=driver,
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is True
    assert store.fetch_all("review_safety_gates")[-1]["status"] == "fail"


def test_inflight_global_stop_prevents_accepted_review_application(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    before = run_path.read_bytes()

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        bundle = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(
                encoding="utf-8"
            )
        )
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-1"],
            evidence_refs=list(bundle["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        store.open_user_decision(
            scope="global",
            summary="Stop before Reviewer application.",
            failure_key="global-stop:before-application",
            required_decision="Resolve the global stop.",
        )
        return {"status": "pass", "exit_code": 0}

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=driver,
    )

    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is True
    assert run_path.read_bytes() == before
    assert store.fetch_all("review_applications") == []


def test_real_reviewer_path_validates_candidate_and_records_accepted_review(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)

    def fake_codex_reviewer(**kwargs: object) -> dict[str, object]:
        assert kwargs["role"] == "supervisor_reviewer"
        prompt = Path(str(kwargs["prompt_path"])).read_text(encoding="utf-8")
        assert "read-only" in prompt
        review_dir = Path(str(kwargs["run_dir"]))
        bundle_path = next(review_dir.glob("review-*-evidence.json"))
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=list(bundle["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=fake_codex_reviewer,
    )

    assert result.status == "review_complete"
    assert result.review is not None
    assert result.review.decision is ReviewDecision.CONTINUE
    stored_review = store.fetch_all("reviews")[0]
    assert stored_review["status"] == "review_complete"
    assert len(json.loads(stored_review["evidence_json"])) == 2


def test_reviewer_prompt_embeds_exact_schema_and_valid_candidate_fixture() -> None:
    review_id = "review-prompt-schema"
    prompt = reviewer_module._review_prompt(
        review_id,
        Path(".codex/supervisor/reviews/evidence.json"),
    )
    schema = json.loads(
        prompt.split("BEGIN_REVIEW_JSON_SCHEMA\n", 1)[1].split(
            "\nEND_REVIEW_JSON_SCHEMA", 1
        )[0]
    )
    fixture = json.loads(
        prompt.split("BEGIN_REVIEW_JSON_FIXTURE\n", 1)[1].split(
            "\nEND_REVIEW_JSON_FIXTURE", 1
        )[0]
    )
    top_level_keys = {
        "schema_version",
        "review_id",
        "scope",
        "decision",
        "affected_run_ids",
        "summary",
        "evidence_refs",
        "findings",
        "skill_governance",
        "next_review_after_parent_tasks",
    }
    finding_keys = {
        "finding_id",
        "finding_key",
        "status",
        "severity",
        "summary",
        "evidence_refs",
        "closure_evidence_refs",
        "affected_run_ids",
    }
    governance_variants = schema["properties"]["skill_governance"]["items"]["oneOf"]

    assert "top-level evidence_refs must include every hash referenced by findings" in prompt
    assert "and skill_governance" in prompt
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == top_level_keys
    assert schema["properties"]["findings"]["items"]["additionalProperties"] is False
    assert set(schema["properties"]["findings"]["items"]["required"]) == finding_keys
    assert [set(item["required"]) for item in governance_variants] == [
        {"action", "skill_path", "reason", "evidence_refs"},
        {"action", "source_paths", "target_path", "reason", "evidence_refs"},
    ]
    assert all(item["additionalProperties"] is False for item in governance_variants)

    evidence_ref = f"sha256:{'a' * 64}"
    fixture["evidence_refs"] = [evidence_ref]
    review = validate_review_payload(
        fixture,
        expected_evidence_hashes=[evidence_ref],
    )

    assert review.review_id == review_id
    assert review.decision is ReviewDecision.CONTINUE


def test_real_reviewer_does_not_mark_complete_before_outbox_application(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    observed_statuses: list[str] = []
    original_apply = reviewer_module.apply_review_decision

    def fake_codex_reviewer(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        bundle_path = next(review_dir.glob("review-*-evidence.json"))
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-1"],
            evidence_refs=list(bundle["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    def observed_apply(*args: object, **kwargs: object) -> list[ActionRequest]:
        observed_statuses.append(store.fetch_all("reviews")[0]["status"])
        return original_apply(*args, **kwargs)

    monkeypatch.setattr(reviewer_module, "apply_review_decision", observed_apply)

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=fake_codex_reviewer,
    )

    assert observed_statuses == ["review_applying"]
    assert result.status == "review_complete"
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"


def test_reviewer_does_not_publish_skill_recommendations_before_durable_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    config = tmp_path / ".codex" / "supervisor" / "config.json"
    config.write_text(json.dumps({"skill_roots": ["skills"]}) + "\n", encoding="utf-8")
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: alpha\ndescription: Validate loop evidence consistently.\n---\n",
        encoding="utf-8",
    )

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        payload["skill_governance"] = [
            {
                "action": "keep",
                "skill_path": "skills/alpha/SKILL.md",
                "reason": "The review recommends retaining this skill.",
                "evidence_refs": [evidence["evidence_hashes"]["skill_governance"]],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    original_record_review = store.record_review

    def fail_before_acceptance(**kwargs: object):
        if kwargs.get("status") == "review_applying":
            raise RuntimeError("injected durable acceptance cutpoint")
        return original_record_review(**kwargs)

    monkeypatch.setattr(store, "record_review", fail_before_acceptance)

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=driver,
    )

    assert result.status == "review_degraded"
    assert store.fetch_all("reviews")[0]["status"] == "review_degraded"
    assert not any(
        json.loads(row["snapshot_json"]).get("reviewer_recommendations")
        for row in store.fetch_all("skill_snapshots")
    )


def test_prior_finding_closure_evidence_is_carried_into_next_bundle(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    accepted = tmp_path / ".codex" / "supervisor" / "reviews" / "review-old" / "review-old.json"
    accepted.parent.mkdir(parents=True, exist_ok=True)
    payload = valid_review_payload(review_id="review-old")
    payload["findings"] = [
        {
            "finding_id": "finding-old",
            "finding_key": "search-freshness",
            "status": "closed",
            "summary": "Search freshness recovered.",
            "evidence_refs": [],
            "closure_evidence_refs": [f"sha256:{'b' * 64}"],
        }
    ]
    accepted.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    store.record_review(
        review_id="review-old",
        trigger="migration",
        status="review_complete",
        decision="continue",
        summary="Closed the prior finding.",
        evidence_refs=[accepted.relative_to(tmp_path).as_posix()],
        findings=[
            {
                "finding_id": "finding-old",
                "finding_key": "search-freshness",
                "status": "closed",
                "summary": "Search freshness recovered.",
            }
        ],
    )

    bundle = build_review_evidence(tmp_path, store, ["lineage-a"])

    prior = bundle.evidence["prior_findings"]
    assert prior["findings"][0]["status"] == "closed"
    assert list(prior["closure_evidence"][0]["closure_evidence_refs"]) == [
        f"sha256:{'b' * 64}"
    ]


def test_review_payload_rejects_unknown_decisions_hashes_and_operations() -> None:
    invalid_decision = valid_review_payload()
    invalid_decision["decision"] = "global_stop"
    with pytest.raises(ValueError, match="decision"):
        validate_review_payload(invalid_decision)

    invalid_hash = valid_review_payload()
    invalid_hash["evidence_refs"] = ["not-a-hash"]
    with pytest.raises(ValueError, match="evidence"):
        validate_review_payload(invalid_hash)

    prohibited = valid_review_payload()
    prohibited["operations"] = ["git reset --hard"]
    with pytest.raises(ValueError, match="unsupported|prohibited"):
        validate_review_payload(prohibited)


def test_review_finding_closure_requires_trusted_closure_evidence() -> None:
    payload = valid_review_payload()
    payload["findings"] = [
        {
            "finding_id": "finding-1",
            "finding_key": "stale-search",
            "status": "closed",
            "severity": "must_fix",
            "summary": "Search freshness recovered.",
            "evidence_refs": [f"sha256:{'a' * 64}"],
            "closure_evidence_refs": [],
            "affected_run_ids": [],
        }
    ]

    with pytest.raises(ValueError, match="closure evidence"):
        validate_review_payload(
            payload,
            existing_findings=[
                {
                    "finding_id": "finding-1",
                    "finding_key": "stale-search",
                    "status": "open",
                    "evidence_json": "[]",
                    "closure_evidence_json": "[]",
                }
            ],
        )


def test_review_finding_lifecycle_enforces_identity_transitions_and_fresh_closure(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    evidence_a = f"sha256:{'a' * 64}"
    evidence_b = f"sha256:{'b' * 64}"
    opened_payload = valid_review_payload(
        review_id="review-findings-1",
        evidence_refs=[evidence_a],
    )
    opened_payload["findings"] = [
        {
            "finding_id": "finding-stale-search",
            "finding_key": "stale-search",
            "status": "open",
            "severity": "must_fix",
            "summary": "Search freshness is stale.",
            "evidence_refs": [evidence_a],
            "closure_evidence_refs": [],
            "affected_run_ids": ["run-1"],
        }
    ]
    opened = validate_review_payload(
        opened_payload,
        expected_evidence_hashes=[evidence_a],
        allowed_run_ids=["run-1"],
        existing_findings=[],
    )
    store.record_review(
        review_id=opened.review_id,
        trigger="project_global",
        status="review_complete",
        decision=opened.decision.value,
        findings=opened.findings,
    )

    changed_identity = json.loads(json.dumps(opened_payload))
    changed_identity["review_id"] = "review-findings-2"
    changed_identity["findings"][0]["finding_id"] = "finding-renamed"
    with pytest.raises(ValueError, match="stable identity"):
        validate_review_payload(
            changed_identity,
            expected_evidence_hashes=[evidence_a],
            allowed_run_ids=["run-1"],
            existing_findings=store.fetch_all("review_findings"),
        )

    closed_payload = json.loads(json.dumps(opened_payload))
    closed_payload["review_id"] = "review-findings-3"
    closed_payload["evidence_refs"] = [evidence_b]
    closed_payload["findings"][0]["status"] = "closed"
    closed_payload["findings"][0]["evidence_refs"] = [evidence_b]
    closed_payload["findings"][0]["closure_evidence_refs"] = [evidence_a]
    with pytest.raises(ValueError, match="fresh closure evidence"):
        validate_review_payload(
            closed_payload,
            expected_evidence_hashes=[evidence_a, evidence_b],
            allowed_run_ids=["run-1"],
            existing_findings=store.fetch_all("review_findings"),
        )

    closed_payload["findings"][0]["closure_evidence_refs"] = [evidence_b]
    closed = validate_review_payload(
        closed_payload,
        expected_evidence_hashes=[evidence_b],
        allowed_run_ids=["run-1"],
        existing_findings=store.fetch_all("review_findings"),
    )
    store.record_review(
        review_id=closed.review_id,
        trigger="project_global",
        status="review_complete",
        decision=closed.decision.value,
        findings=closed.findings,
    )

    reopened_payload = json.loads(json.dumps(opened_payload))
    reopened_payload["review_id"] = "review-findings-4"
    with pytest.raises(ValueError, match="transition"):
        validate_review_payload(
            reopened_payload,
            expected_evidence_hashes=[evidence_a],
            allowed_run_ids=["run-1"],
            existing_findings=store.fetch_all("review_findings"),
        )


def test_continue_review_may_open_finding_for_terminal_evidence_run() -> None:
    evidence_ref = f"sha256:{'a' * 64}"
    payload = valid_review_payload(evidence_refs=[evidence_ref])
    payload["findings"] = [
        {
            "finding_id": "finding-terminal-run",
            "finding_key": "terminal-run-risk",
            "status": "open",
            "severity": "observe",
            "summary": "Terminal run remains relevant project evidence.",
            "evidence_refs": [evidence_ref],
            "closure_evidence_refs": [],
            "affected_run_ids": ["run-terminal"],
        }
    ]

    review = validate_review_payload(
        payload,
        expected_evidence_hashes=[evidence_ref],
        allowed_run_ids=["run-active"],
        allowed_finding_run_ids=["run-active", "run-terminal"],
    )

    assert review.decision is ReviewDecision.CONTINUE
    assert review.findings[0]["affected_run_ids"] == ("run-terminal",)


def test_review_may_close_finding_for_terminal_evidence_run() -> None:
    old_evidence = f"sha256:{'a' * 64}"
    fresh_evidence = f"sha256:{'b' * 64}"
    payload = valid_review_payload(evidence_refs=[fresh_evidence])
    payload["findings"] = [
        {
            "finding_id": "finding-terminal-run",
            "finding_key": "terminal-run-risk",
            "status": "closed",
            "severity": "observe",
            "summary": "Terminal run risk has closure evidence.",
            "evidence_refs": [fresh_evidence],
            "closure_evidence_refs": [fresh_evidence],
            "affected_run_ids": ["run-terminal"],
        }
    ]

    review = validate_review_payload(
        payload,
        expected_evidence_hashes=[fresh_evidence],
        allowed_run_ids=["run-active"],
        allowed_finding_run_ids=["run-active", "run-terminal"],
        existing_findings=[
            {
                "finding_id": "finding-terminal-run",
                "finding_key": "terminal-run-risk",
                "status": "open",
                "evidence_json": json.dumps([old_evidence]),
                "closure_evidence_json": "[]",
            }
        ],
    )

    assert review.findings[0]["status"] == "closed"
    assert review.findings[0]["affected_run_ids"] == ("run-terminal",)


def test_review_nested_schema_rejects_unknown_runs_and_unproven_skill_actions() -> None:
    evidence_ref = f"sha256:{'a' * 64}"
    finding = valid_review_payload()
    finding["findings"] = [
        {
            "finding_id": "finding-1",
            "finding_key": "stale-search",
            "status": "open",
            "severity": "must_fix",
            "summary": "Search freshness is stale.",
            "evidence_refs": [evidence_ref],
            "closure_evidence_refs": [],
            "affected_run_ids": ["unknown-run"],
        }
    ]
    with pytest.raises(ValueError, match="unknown affected runs"):
        validate_review_payload(
            finding,
            expected_evidence_hashes=[evidence_ref],
            allowed_run_ids=["run-1"],
        )

    governance = valid_review_payload()
    governance["skill_governance"] = [
        {
            "action": "keep",
            "skill_path": "skills/alpha/SKILL.md",
            "reason": "Keep the skill.",
            "evidence_refs": [],
        }
    ]
    with pytest.raises(ValueError, match="evidence_refs must not be empty"):
        validate_review_payload(
            governance,
            expected_evidence_hashes=[evidence_ref],
            allowed_skill_paths=["skills/alpha/SKILL.md"],
        )


def test_review_refocus_and_stop_run_apply_automatically(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    record_parent_completion(store, "lineage-b", run_id="run-2", parent=1)

    refocus = validate_review_payload(
        valid_review_payload(decision="refocus", affected_run_ids=["run-1"])
    )
    refocus_actions = apply_review_decision(store, refocus)
    stop = validate_review_payload(
        valid_review_payload(
            review_id="review-0002",
            decision="stop_run",
            affected_run_ids=["run-2"],
        )
    )
    stop_actions = apply_review_decision(store, stop)

    assert refocus_actions[0].action_type is ActionType.REFOCUS_RUN
    assert stop_actions[0].action_type is ActionType.STOP_RUN
    assert {row["action_type"] for row in store.fetch_all("actions")} >= {
        ActionType.REFOCUS_RUN.value,
        ActionType.STOP_RUN.value,
    }
    refocused = json.loads(
        (tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    stopped = json.loads(
        (tmp_path / ".codex" / "loop-runs" / "run-2" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert (refocused["phase"], refocused["next_action"]) == (
        "planning",
        "run_autonomous_planner",
    )
    assert refocused["reviewer_directives"][-1]["decision"] == "refocus"
    assert (stopped["phase"], stopped["next_action"]) == ("stopped_by_reviewer", "none")
    assert all(
        row["status"] == "completed"
        for row in store.fetch_all("actions")
        if row["action_type"]
        in {ActionType.REFOCUS_RUN.value, ActionType.STOP_RUN.value}
    )


def test_multi_target_review_rejects_incoherent_revision_before_any_mutation(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    record_parent_completion(store, "lineage-b", run_id="run-2", parent=1)
    reviewed_runs = {}
    for run_id in ("run-1", "run-2"):
        path = tmp_path / ".codex" / "loop-runs" / run_id / "run.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        reviewed_runs[run_id] = {
            "revision": payload["state_revision"],
            "state_fingerprint": _state_fingerprint(payload),
        }
    review = validate_review_payload(
        valid_review_payload(
            decision="refocus",
            affected_run_ids=["run-1", "run-2"],
        ),
        allowed_run_ids=["run-1", "run-2"],
        reviewed_runs=reviewed_runs,
    )
    run_two = store.get_run("run-2")
    store.upsert_run_projection(
        {
            "run_id": "run-2",
            "revision": 2,
            "loop_lineage_id": "lineage-b",
            "parent_run_id": "",
            "policy": run_two["policy"],
            "phase": "planning",
            "status": "actionable",
            "summary": run_two["summary"]["summary"],
            "artifact_refs": run_two["summary"]["artifact_refs"],
        }
    )

    with pytest.raises(LeaseError, match="canonical state is corrupt"):
        apply_review_decision(store, review)

    untouched = json.loads(
        (tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert untouched["phase"] == "stopped_budget"
    assert store.fetch_all("review_application_targets") == []


def test_review_supersession_cancels_targets_prepared_before_run_advance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    original = json.loads(run_path.read_text(encoding="utf-8"))
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-prepared-target-superseded",
            decision="refocus",
            affected_run_ids=["run-1"],
        ),
        allowed_run_ids=["run-1"],
        reviewed_runs={
            "run-1": {
                "revision": original["state_revision"],
                "state_fingerprint": _state_fingerprint(original),
            }
        },
    )
    original_prepare = store.prepare_review_application

    def prepare_then_advance(**kwargs: object):
        actions = original_prepare(**kwargs)
        owner_id = "supervisor-review-application-review-prepared-target-superseded"
        claimed = store.claim_pending_action(
            actions[0].action_id,
            owner_id,
            lease_seconds=120,
        )
        assert claimed is not None and claimed.status == "leased"
        advanced = dict(original)
        advanced["state_revision"] = 2
        advanced["phase"] = "planning"
        advanced["next_action"] = "run_autonomous_planner"
        advanced["last_result"] = "none"
        run_path.write_text(json.dumps(advanced) + "\n", encoding="utf-8")
        refresh_run_projection(store, "run-1", advanced)
        return actions

    monkeypatch.setattr(store, "prepare_review_application", prepare_then_advance)

    with pytest.raises(
        reviewer_outbox_module.ReviewSupersededError,
        match="target advanced",
    ):
        apply_review_decision(store, review)

    assert store.fetch_all("reviews")[0]["status"] == "review_superseded"
    assert store.fetch_all("review_applications")[0]["status"] == "superseded"
    assert store.fetch_all("review_application_targets")[0]["status"] == "superseded"
    target_action = store.get_action(
        str(store.fetch_all("review_application_targets")[0]["action_id"])
    )
    assert target_action.status == "cancelled"
    persisted = json.loads(run_path.read_text(encoding="utf-8"))
    assert persisted["state_revision"] == 2
    assert "reviewer_directives" not in persisted


def test_queued_reviewer_cas_race_supersedes_and_releases_cadence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(
        store,
        "lineage-a",
        run_id="run-a2",
        parent=2,
        previous_run_id="run-a1",
    )
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    original_atomic_save = reconciler_module.atomic_save_run
    advanced = False

    def advance_at_cas(*args: object, **kwargs: object):
        nonlocal advanced
        if not advanced:
            advanced = True
            run_path = tmp_path / ".codex" / "loop-runs" / "run-a2" / "run.json"
            payload = json.loads(run_path.read_text(encoding="utf-8"))
            payload["state_revision"] = 2
            payload["phase"] = "planning"
            payload["next_action"] = "run_autonomous_planner"
            payload["last_result"] = "none"
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            refresh_run_projection(store, "run-a2", payload)
        return original_atomic_save(*args, **kwargs)

    monkeypatch.setattr(reconciler_module, "atomic_save_run", advance_at_cas)

    result = run_queued_reviewer(
        store,
        reviewer_id="reviewer-cas-race",
        driver=driver,
        timeout_seconds=1,
        heartbeat_seconds=0.01,
    )

    assert result is not None and result.status == "review_degraded"
    assert result.blocks_safe_runs is False
    assert store.fetch_all("reviews")[0]["status"] == "review_superseded"
    assert store.fetch_all("review_applications")[0]["status"] == "superseded"
    assert store.fetch_all("review_application_targets")[0]["status"] == "superseded"
    target_action_id = store.fetch_all("review_application_targets")[0]["action_id"]
    assert store.get_action(str(target_action_id)).status == "cancelled"
    assert store.get_action(request.action_id).status == "cancelled"
    cadence = store.review_cadence_positions()["lineage-a"]
    assert cadence["reviewed_position"] == 0
    assert cadence["reserved_position"] == 0


def test_queued_reviewer_waits_for_file_first_projection_to_cohere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(
        store,
        "lineage-a",
        run_id="run-a2",
        parent=2,
        previous_run_id="run-a1",
    )
    request = schedule_due_reviews(store, now=NOW)[0]
    clock.value = NOW + timedelta(minutes=10)

    def driver(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence = json.loads(
            next(review_dir.glob("review-*-evidence.json")).read_text(encoding="utf-8")
        )
        candidate = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            decision="refocus",
            affected_run_ids=["run-a2"],
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(candidate) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    original_atomic_save = reconciler_module.atomic_save_run
    original_target_run = reviewer_outbox_module._target_run
    original_get_run = store.get_run
    file_written = threading.Event()
    reviewer_read_file = threading.Event()
    foreground_read_stale_projection = threading.Event()
    heartbeat_read_file = threading.Event()
    projection_updated = threading.Event()
    reviewer_thread_id = threading.get_ident()
    writer_errors: list[BaseException] = []
    writer_thread: threading.Thread | None = None
    stale_projection_returned = False
    original_safety_json_loads = reviewer_safety_module.json.loads

    def synchronized_get_run(run_id: str):
        nonlocal stale_projection_returned
        run = original_get_run(run_id)
        if (
            run_id == "run-a2"
            and threading.get_ident() == reviewer_thread_id
            and reviewer_read_file.is_set()
            and not stale_projection_returned
        ):
            stale_projection_returned = True
            foreground_read_stale_projection.set()
            assert projection_updated.wait(2), "writer did not update the projection"
        return run

    def observe_heartbeat_file_read(value, *args, **kwargs):
        payload = original_safety_json_loads(value, *args, **kwargs)
        if (
            threading.current_thread().name.startswith("reviewer-lease-")
            and isinstance(payload, dict)
            and payload.get("run_id") == "run-a2"
            and payload.get("state_revision") == 2
        ):
            heartbeat_read_file.set()
        return payload

    def observe_file_first_state(store_arg, run):
        snapshot = original_target_run(store_arg, run)
        if (
            str(run["run_id"]) == "run-a2"
            and file_written.is_set()
            and int(snapshot[2]["state_revision"]) == 2
        ):
            reviewer_read_file.set()
        return snapshot

    def advance_file_then_projection() -> None:
        try:
            run_path = tmp_path / ".codex" / "loop-runs" / "run-a2" / "run.json"
            payload = json.loads(run_path.read_text(encoding="utf-8"))
            expected_revision = int(payload["state_revision"])
            expected_fingerprint = _state_fingerprint(payload)
            payload["phase"] = "planning"
            payload["next_action"] = "run_autonomous_planner"
            payload["last_result"] = "none"
            saved = original_atomic_save(
                tmp_path,
                "run-a2",
                payload,
                expected_revision=expected_revision,
                expected_fingerprint=expected_fingerprint,
            )
            file_written.set()
            assert foreground_read_stale_projection.wait(2), (
                "foreground Reviewer did not observe file-first state"
            )
            assert heartbeat_read_file.wait(2), (
                "Reviewer heartbeat did not observe file-first state"
            )
            refresh_run_projection(store, "run-a2", saved)
        except BaseException as exc:
            writer_errors.append(exc)
        finally:
            projection_updated.set()

    advanced = False

    def advance_at_cas(*args: object, **kwargs: object):
        nonlocal advanced, writer_thread
        if not advanced:
            advanced = True
            writer_thread = threading.Thread(target=advance_file_then_projection)
            writer_thread.start()
            assert file_written.wait(2), "competing writer did not replace run.json"
        return original_atomic_save(*args, **kwargs)

    monkeypatch.setattr(store, "get_run", synchronized_get_run)
    monkeypatch.setattr(reviewer_outbox_module, "_target_run", observe_file_first_state)
    monkeypatch.setattr(reviewer_safety_module.json, "loads", observe_heartbeat_file_read)
    monkeypatch.setattr(reconciler_module, "atomic_save_run", advance_at_cas)

    try:
        result = run_queued_reviewer(
            store,
            reviewer_id="reviewer-file-first-projection-race",
            driver=driver,
            timeout_seconds=1,
            heartbeat_seconds=0.01,
        )
    finally:
        foreground_read_stale_projection.set()
        heartbeat_read_file.set()
        if writer_thread is not None:
            writer_thread.join(timeout=2)

    assert writer_thread is not None and not writer_thread.is_alive()
    assert writer_errors == []
    assert reviewer_read_file.is_set()
    assert stale_projection_returned is True
    assert result is not None and result.status == "review_degraded"
    assert result.blocks_safe_runs is False
    assert store.fetch_all("reviews")[0]["status"] == "review_superseded"
    assert store.fetch_all("review_applications")[0]["status"] == "superseded"
    assert store.fetch_all("review_application_targets")[0]["status"] == "superseded"
    target_action_id = store.fetch_all("review_application_targets")[0]["action_id"]
    assert store.get_action(str(target_action_id)).status == "cancelled"
    assert store.get_action(request.action_id).status == "cancelled"
    cadence = store.review_cadence_positions()["lineage-a"]
    assert cadence["reviewed_position"] == 0
    assert cadence["reserved_position"] == 0


@pytest.mark.parametrize(
    "state_problem",
    [
        "same_revision",
        "unsafe_payload",
        "malformed_json",
        "projection_never_coheres",
        "revision_rollback",
        "revision_jump",
    ],
)
def test_review_cas_race_with_incoherent_or_unsafe_state_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state_problem: str,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    original_payload = json.loads(run_path.read_text(encoding="utf-8"))
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-cas-corruption",
            decision="refocus",
            affected_run_ids=["run-1"],
        ),
        allowed_run_ids=["run-1"],
        reviewed_runs={
            "run-1": {
                "revision": original_payload["state_revision"],
                "state_fingerprint": _state_fingerprint(original_payload),
            }
        },
    )
    original_atomic_save = reconciler_module.atomic_save_run
    if state_problem == "projection_never_coheres":
        monkeypatch.setattr(
            reviewer_outbox_module, "_PROJECTION_CONSISTENCY_ATTEMPTS", 3
        )
        monkeypatch.setattr(
            reviewer_outbox_module, "_PROJECTION_CONSISTENCY_RETRY_SECONDS", 0.001
        )

    def corrupt_at_cas(*args: object, **kwargs: object):
        if state_problem == "malformed_json":
            run_path.write_text("{\n", encoding="utf-8")
            return original_atomic_save(*args, **kwargs)
        if state_problem == "unsafe_payload":
            corrupted = {"run_id": "run-1"}
        else:
            corrupted = json.loads(run_path.read_text(encoding="utf-8"))
            if state_problem == "same_revision":
                corrupted["requirement"] = "Changed without revision or projection."
            elif state_problem == "revision_rollback":
                corrupted["state_revision"] = 0
            else:
                corrupted["state_revision"] = (
                    2 if state_problem == "projection_never_coheres" else 3
                )
                corrupted["phase"] = "planning"
                corrupted["next_action"] = "run_autonomous_planner"
                corrupted["last_result"] = "none"
        run_path.write_text(json.dumps(corrupted) + "\n", encoding="utf-8")
        return original_atomic_save(*args, **kwargs)

    monkeypatch.setattr(reconciler_module, "atomic_save_run", corrupt_at_cas)

    with pytest.raises(LeaseError, match="canonical state is corrupt"):
        apply_review_decision(store, review)

    assert store.fetch_all("reviews")[0]["status"] == "review_applying"
    assert store.fetch_all("review_applications")[0]["status"] == "applying"
    assert store.fetch_all("review_application_targets")[0]["status"] == "pending"
    target_action_id = store.fetch_all("review_application_targets")[0]["action_id"]
    assert store.get_action(str(target_action_id)).status == "leased"


def test_prepare_target_rereads_projection_after_file_read_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    original_payload = json.loads(run_path.read_text(encoding="utf-8"))
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-prepare-read-race",
            decision="refocus",
            affected_run_ids=["run-1"],
        ),
        allowed_run_ids=["run-1"],
        reviewed_runs={
            "run-1": {
                "revision": original_payload["state_revision"],
                "state_fingerprint": _state_fingerprint(original_payload),
            }
        },
    )
    original_target_run = reviewer_outbox_module._target_run
    advanced = False

    def advance_between_projection_and_file(store_arg, run):
        nonlocal advanced
        if not advanced:
            advanced = True
            payload = json.loads(run_path.read_text(encoding="utf-8"))
            payload["state_revision"] = 2
            payload["phase"] = "planning"
            payload["next_action"] = "run_autonomous_planner"
            payload["last_result"] = "none"
            run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            refresh_run_projection(store, "run-1", payload)
        return original_target_run(store_arg, run)

    monkeypatch.setattr(
        reviewer_outbox_module,
        "_target_run",
        advance_between_projection_and_file,
    )

    with pytest.raises(
        reviewer_outbox_module.ReviewSupersededError,
        match="target advanced",
    ):
        apply_review_decision(store, review)

    assert store.fetch_all("review_applications") == []
    assert store.fetch_all("review_application_targets") == []


def test_review_outbox_resumes_idempotently_after_file_write_cutpoint(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    record_parent_completion(store, "lineage-b", run_id="run-2", parent=1)
    reviewed_runs = {}
    for run_id in ("run-1", "run-2"):
        path = tmp_path / ".codex" / "loop-runs" / run_id / "run.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        reviewed_runs[run_id] = {
            "revision": payload["state_revision"],
            "state_fingerprint": _state_fingerprint(payload),
        }
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-outbox",
            decision="refocus",
            affected_run_ids=["run-1", "run-2"],
        ),
        allowed_run_ids=["run-1", "run-2"],
        reviewed_runs=reviewed_runs,
    )
    cut = []

    def fail_after_first_write(stage: str, run_id: str) -> None:
        if stage == "after_file_write" and not cut:
            cut.append(run_id)
            raise RuntimeError("injected outbox cutpoint")

    with pytest.raises(RuntimeError, match="cutpoint"):
        apply_review_decision(store, review, application_cutpoint=fail_after_first_write)

    first_written = json.loads(
        (tmp_path / ".codex" / "loop-runs" / cut[0] / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert first_written["state_revision"] == 2
    assert store.fetch_all("reviews")[0]["status"] == "review_applying"
    assert all(
        row["status"] == "pending"
        for row in store.fetch_all("review_application_targets")
    )
    assert (
        store.lease_next_action(
            "ordinary-worker-race",
            lease_seconds=60,
            allowed_action_types={ActionType.REFOCUS_RUN.value},
        )
        is None
    )

    actions = apply_review_decision(store, review)

    assert len(actions) == 2
    for run_id in ("run-1", "run-2"):
        payload = json.loads(
            (tmp_path / ".codex" / "loop-runs" / run_id / "run.json").read_text(
                encoding="utf-8"
            )
        )
        assert payload["state_revision"] == 2
        assert payload["reviewer_directives"][-1]["review_id"] == "review-outbox"
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"
    assert all(
        row["status"] == "applied"
        for row in store.fetch_all("review_application_targets")
    )


def test_review_outbox_lease_loss_before_file_write_prevents_mutation(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    original = run_path.read_bytes()
    payload = json.loads(original)
    review = validate_review_payload(
        valid_review_payload(decision="refocus", affected_run_ids=["run-1"]),
        allowed_run_ids=["run-1"],
        reviewed_runs={
            "run-1": {
                "revision": payload["state_revision"],
                "state_fingerprint": _state_fingerprint(payload),
            }
        },
    )
    before_file_write = False

    def lose_before_write() -> None:
        if before_file_write:
            raise LeaseError("injected outer lease loss")

    def mark_before_file_write(stage: str, _run_id: str) -> None:
        nonlocal before_file_write
        if stage == "before_file_write":
            before_file_write = True

    with pytest.raises(LeaseError, match="outer lease loss"):
        apply_review_decision(
            store,
            review,
            lease_checkpoint=lose_before_write,
            application_cutpoint=mark_before_file_write,
        )

    assert run_path.read_bytes() == original
    assert store.fetch_all("review_application_targets")[0]["status"] == "pending"
    assert store.fetch_all("reviews")[0]["status"] == "review_applying"


@pytest.mark.parametrize(
    ("decision", "affected_run_ids"),
    [("continue", []), ("refocus", ["run-1"])],
)
def test_review_outbox_lease_loss_before_persistence_has_no_side_effects(
    tmp_path: Path,
    decision: str,
    affected_run_ids: list[str],
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    review = validate_review_payload(
        valid_review_payload(
            decision=decision,
            affected_run_ids=affected_run_ids,
        )
    )

    def lease_lost() -> None:
        raise LeaseError("injected outer lease loss")

    with pytest.raises(LeaseError, match="outer lease loss"):
        apply_review_decision(store, review, lease_checkpoint=lease_lost)

    assert store.fetch_all("reviews") == []
    assert store.fetch_all("review_applications") == []
    assert store.fetch_all("review_application_targets") == []
    assert store.fetch_all("actions") == []


def test_review_outbox_lease_loss_before_database_finalization_is_resumable(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    review = validate_review_payload(
        valid_review_payload(decision="refocus", affected_run_ids=["run-1"]),
        allowed_run_ids=["run-1"],
        reviewed_runs={
            "run-1": {
                "revision": payload["state_revision"],
                "state_fingerprint": _state_fingerprint(payload),
            }
        },
    )
    file_written = False

    def mark_file_written(stage: str, _run_id: str) -> None:
        nonlocal file_written
        if stage == "after_file_write":
            file_written = True

    def lose_before_finalize() -> None:
        if file_written:
            raise LeaseError("injected outer lease loss")

    with pytest.raises(LeaseError, match="outer lease loss"):
        apply_review_decision(
            store,
            review,
            lease_checkpoint=lose_before_finalize,
            application_cutpoint=mark_file_written,
        )

    written = json.loads(run_path.read_text(encoding="utf-8"))
    assert written["state_revision"] == 2
    assert store.fetch_all("review_application_targets")[0]["status"] == "pending"
    assert store.fetch_all("reviews")[0]["status"] == "review_applying"

    apply_review_decision(store, review)

    assert json.loads(run_path.read_text(encoding="utf-8"))["state_revision"] == 2
    assert store.fetch_all("review_application_targets")[0]["status"] == "applied"
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"


def test_review_outbox_finalizes_after_applied_run_advances_again(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    review = validate_review_payload(
        valid_review_payload(decision="refocus", affected_run_ids=["run-1"]),
        allowed_run_ids=["run-1"],
        reviewed_runs={
            "run-1": {
                "revision": payload["state_revision"],
                "state_fingerprint": _state_fingerprint(payload),
            }
        },
    )
    file_written = False

    def mark_file_written(stage: str, _run_id: str) -> None:
        nonlocal file_written
        if stage == "after_file_write":
            file_written = True

    def lose_before_finalize() -> None:
        if file_written:
            raise LeaseError("injected outer lease loss")

    with pytest.raises(LeaseError, match="outer lease loss"):
        apply_review_decision(
            store,
            review,
            lease_checkpoint=lose_before_finalize,
            application_cutpoint=mark_file_written,
        )

    advanced = json.loads(run_path.read_text(encoding="utf-8"))
    advanced["state_revision"] += 1
    advanced["phase"] = "generating"
    advanced["next_action"] = "run_autonomous_generator"
    advanced["last_result"] = "none"
    run_path.write_text(json.dumps(advanced) + "\n", encoding="utf-8")
    refresh_run_projection(store, "run-1", advanced)

    apply_review_decision(store, review)

    assert json.loads(run_path.read_text(encoding="utf-8"))["state_revision"] == 3
    assert store.fetch_all("review_application_targets")[0]["status"] == "applied"
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"


def test_review_auto_remediate_is_bounded_and_continue_is_a_noop(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    remediation = validate_review_payload(
        valid_review_payload(decision="auto_remediate", affected_run_ids=["run-1"])
    )
    continued = validate_review_payload(
        valid_review_payload(review_id="review-0002", decision="continue")
    )

    actions = apply_review_decision(store, remediation)

    assert actions[0].action_type is ActionType.RUN_ALTERNATE_RECOVERY
    assert actions[0].metadata["worker_executable"] is False
    remediated = json.loads(
        (tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert (remediated["phase"], remediated["next_action"]) == (
        "planning",
        "run_autonomous_planner",
    )
    assert remediated["reviewer_directives"][-1]["decision"] == "auto_remediate"
    assert store.get_action(actions[0].action_id).status == "completed"
    assert apply_review_decision(store, continued) == []


def test_reviewer_refocus_directive_is_part_of_next_planner_contract(tmp_path: Path) -> None:
    directive = {
        "review_id": "review-0001",
        "decision": "refocus",
        "summary": "Prioritize stale search recovery.",
        "evidence_refs": [f"sha256:{'a' * 64}"],
    }
    prompt = _autonomous_planner_prompt(
        {
            "run_id": "run-1",
            "domain": "ai",
            "requirement": "Keep search fresh.",
            "parent_task_counter": 2,
            "reviewer_directives": [directive],
        },
        tmp_path / ".codex" / "loop-runs" / "run-1",
    )

    assert "Reviewer directives:" in prompt
    assert "Prioritize stale search recovery." in prompt
    assert '"decision": "refocus"' in prompt


def test_review_ask_user_opens_only_run_scoped_decision(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    review = validate_review_payload(
        valid_review_payload(decision="ask_user", affected_run_ids=["run-1"])
    )

    actions = apply_review_decision(store, review)

    assert actions[0].action_type is ActionType.ASK_USER
    decisions = store.fetch_all("user_decisions")
    assert [(item["scope"], item["run_id"]) for item in decisions] == [("run", "run-1")]


def test_review_ask_user_applies_when_run_already_has_open_decision(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    store.open_user_decision(
        scope="run",
        run_id="run-1",
        failure_key="reconcile:run:run-1:registry_user_gate",
        summary="Existing registry gate.",
        required_decision="Resolve the existing gate.",
    )
    review = validate_review_payload(
        valid_review_payload(decision="ask_user", affected_run_ids=["run-1"])
    )

    actions = apply_review_decision(store, review)

    assert store.get_action(actions[0].action_id).status == "completed"
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"
    decisions = store.fetch_all("user_decisions")
    assert len(decisions) == 2
    assert all(item["scope"] == "run" for item in decisions)


def test_superseded_interrupted_ask_user_closes_only_its_provenance_decision(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    unrelated = store.open_user_decision(
        scope="run",
        run_id="run-1",
        failure_key="unrelated:run-1",
        summary="Unrelated operator decision.",
        required_decision="Resolve independently.",
    )
    run_path = tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json"
    original = json.loads(run_path.read_text(encoding="utf-8"))
    review = validate_review_payload(
        valid_review_payload(
            review_id="review-ask-user-superseded",
            decision="ask_user",
            affected_run_ids=["run-1"],
        ),
        allowed_run_ids=["run-1"],
        reviewed_runs={
            "run-1": {
                "revision": original["state_revision"],
                "state_fingerprint": _state_fingerprint(original),
            }
        },
    )

    def crash_after_decision(stage: str, _run_id: str) -> None:
        if stage == "after_file_write":
            raise RuntimeError("crash after ask_user decision")

    with pytest.raises(RuntimeError, match="crash after ask_user"):
        apply_review_decision(
            store,
            review,
            application_cutpoint=crash_after_decision,
        )

    linked = next(
        row
        for row in store.fetch_all("user_decisions")
        if row["decision_id"] != unrelated["decision_id"]
    )
    assert linked["status"] == "open"
    advanced = dict(original)
    advanced["state_revision"] = 2
    advanced["phase"] = "planning"
    advanced["next_action"] = "run_autonomous_planner"
    advanced["last_result"] = "none"
    run_path.write_text(json.dumps(advanced) + "\n", encoding="utf-8")
    refresh_run_projection(store, "run-1", advanced)

    with pytest.raises(
        reviewer_outbox_module.ReviewSupersededError,
        match="target advanced",
    ):
        apply_review_decision(store, review)

    decisions = {
        row["decision_id"]: row for row in store.fetch_all("user_decisions")
    }
    assert decisions[linked["decision_id"]]["status"] == "closed"
    assert "superseded" in decisions[linked["decision_id"]]["resolution"].lower()
    assert decisions[unrelated["decision_id"]]["status"] == "open"
    assert decisions[unrelated["decision_id"]]["resolution"] == ""


def test_evidence_bundle_hashes_global_signals_and_uses_only_structured_skill_usage(
    tmp_path: Path,
) -> None:
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=1)
    config = tmp_path / ".codex" / "supervisor" / "config.json"
    config.write_text(json.dumps({"skill_roots": ["skills"]}) + "\n", encoding="utf-8")
    for name, description in (
        ("alpha", "Validate loop evidence consistently."),
        ("beta", "validate   loop evidence consistently"),
        ("gamma", "Publish release notes."),
    ):
        skill = tmp_path / "skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n",
            encoding="utf-8",
        )
    run_dir = tmp_path / ".codex" / "loop-runs" / "run-1"
    (run_dir / "generator-result.json").write_text(
        json.dumps(
            {
                "status": "implemented",
                "summary": "Implemented with alpha.",
                "skills_used": [
                    {
                        "name": "alpha",
                        "path": "skills/alpha/SKILL.md",
                        "status": "confirmed",
                    }
                ],
                "changed_paths": [
                    "scripts/example.py",
                    "personal-wiki/domains/ai/raw/source.md",
                    "personal-wiki/domains/ai/wiki/page.md",
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "generator-attempt-1.stdout.log").write_text(
        "beta gamma alpha\n", encoding="utf-8"
    )
    (run_dir / "notes.json").write_text(
        json.dumps({"status": "pass", "skills_used": ["beta"]}) + "\n",
        encoding="utf-8",
    )

    forged_bundle = build_review_evidence(tmp_path, store, ["lineage-a"])

    assert forged_bundle.evidence["skill_governance"]["used_skills"] == 0

    artifact_ref = ".codex/loop-runs/run-1/generator-result.json"
    request = ActionRequest(
        action_id="action-skill-invocation",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="stopped_budget",
        action_type=ActionType.RUN_GENERATOR,
        idempotency_key="skill-invocation",
    )
    store.enqueue_action(request)
    leased = store.lease_next_action("worker-skill", lease_seconds=60)
    assert leased is not None
    attempt = store.complete_action(
        request.action_id,
        "worker-skill",
        ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="recorded structured skill invocation",
            artifact_paths=(artifact_ref,),
        ),
    )
    artifact_sha256 = hashlib.sha256((tmp_path / artifact_ref).read_bytes()).hexdigest()
    store.record_skill_invocation(
        invocation_id="skill-invocation-alpha",
        action_id=request.action_id,
        attempt_id=attempt.attempt_id,
        skill_path="skills/alpha/SKILL.md",
        artifact_path=artifact_ref,
        artifact_sha256=f"sha256:{artifact_sha256}",
    )

    bundle = build_review_evidence(tmp_path, store, ["lineage-a"])

    assert {
        "objective_constraints",
        "parent_progress",
        "agent_evaluator_summaries",
        "commits_pushes",
        "domain_output_metrics",
        "failures_recoveries",
        "services_freshness",
        "user_decisions",
        "skill_governance",
        "prior_findings",
    } <= set(bundle.evidence)
    assert all(
        value.startswith("sha256:") and len(value) == 71
        for value in bundle.evidence_hashes.values()
    )
    skills = bundle.evidence["skill_governance"]
    metrics = bundle.evidence["domain_output_metrics"]
    assert metrics["raw_evidence_paths"] == 1
    assert metrics["wiki_page_paths"] == 1
    assert skills["used_skills"] == 1
    assert skills["confirmed_usage"][0]["name"] == "alpha"
    assert {item["name"] for item in skills["inventory"]} == {"alpha", "beta", "gamma"}
    assert len(skills["duplicate_groups"]) == 1
    def fake_skill_reviewer(**kwargs: object) -> dict[str, object]:
        review_dir = Path(str(kwargs["run_dir"]))
        evidence_path = next(review_dir.glob("review-*-evidence.json"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        payload = valid_review_payload(
            review_id=str(kwargs["run_id"]),
            evidence_refs=list(evidence["evidence_hashes"].values()),
        )
        payload["skill_governance"] = [
            {
                "action": "keep",
                "skill_path": "skills/alpha/SKILL.md",
                "reason": "Structured execution evidence confirms current use.",
                "evidence_refs": [evidence["evidence_hashes"]["skill_governance"]],
            }
        ]
        Path(str(kwargs["output_json_path"])).write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
        return {"status": "pass", "exit_code": 0}

    result = run_reviewer(
        ReviewerContext(tmp_path, store, ("lineage-a",)),
        driver=fake_skill_reviewer,
    )

    assert result.status == "review_complete"
    snapshots = [json.loads(row["snapshot_json"]) for row in store.fetch_all("skill_snapshots")]
    recommendation_snapshots = [
        item for item in snapshots if item.get("reviewer_recommendations")
    ]
    assert len(recommendation_snapshots) == 1
    recommendation = recommendation_snapshots[0]["reviewer_recommendations"][0]
    assert recommendation["action"] == "keep"
    assert recommendation["skill_path"] == "skills/alpha/SKILL.md"
    assert recommendation["reason"] == "Structured execution evidence confirms current use."
    assert len(recommendation["evidence_refs"]) == 1
    assert recommendation["evidence_refs"][0].startswith("sha256:")
