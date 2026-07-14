from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import scripts.harness_loop_orchestrator as orchestrator_module
from scripts.harness_loop_agents import build_codex_exec_command
from scripts.harness_loop_auditor import write_rule_based_audit_report
from scripts.harness_loop_orchestrator import (
    _autonomous_planner_prompt,
    _run_audit_boundary,
    _set_audit_blocked,
    run_auditor,
)
from scripts.loop_supervisor import reviewer as reviewer_module
from scripts.loop_supervisor.executor import ACTION_HANDLERS
from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
    ReviewDecision,
)
from scripts.loop_supervisor.reconciler import _state_fingerprint
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
from scripts.loop_supervisor.store import LeaseError, SupervisorStore


NOW = datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)


class MutableClock:
    def __init__(self, value: datetime = NOW) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def migrated_store(tmp_path: Path, clock: MutableClock | None = None) -> SupervisorStore:
    store = SupervisorStore.open(tmp_path, clock=clock)
    store.migrate()
    return store


def record_parent_completion(
    store: SupervisorStore,
    lineage_id: str,
    *,
    run_id: str,
    parent: int,
    previous_run_id: str = "",
) -> None:
    run_dir = store.project_root / ".codex" / "loop-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "state_revision": 1,
        "policy": "autonomous_knowledge",
        "phase": "stopped_budget",
        "run_kind": "single",
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
    }
    run_path = run_dir / "run.json"
    run_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    store.upsert_run_projection(
        {
            "run_id": run_id,
            "revision": 1,
            "loop_lineage_id": lineage_id,
            "parent_run_id": previous_run_id,
            "policy": "autonomous_knowledge",
            "phase": "stopped_budget",
            "status": "actionable",
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


def test_legacy_auditor_production_entrypoints_are_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    legacy_run = {
        "run_id": "legacy-run",
        "policy": "autonomous_knowledge",
        "run_kind": "single",
        "phase": "planning",
    }
    monkeypatch.setattr(orchestrator_module, "load_run", lambda *_args: legacy_run)

    with pytest.raises(RuntimeError, match="disabled.*Supervisor Reviewer"):
        write_rule_based_audit_report(tmp_path, legacy_run)
    with pytest.raises(RuntimeError, match="disabled.*Supervisor Reviewer"):
        run_auditor(tmp_path, "legacy-run", driver="fake")

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


def test_queued_degraded_review_releases_cadence_without_advancing(
    tmp_path: Path,
) -> None:
    clock = MutableClock(NOW)
    store = migrated_store(tmp_path, clock)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]
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
    assert cadence["reservation_id"] == ""
    assert review_due_lineages(store, now=clock.value) == ["lineage-a"]
    assert schedule_due_reviews(store, now=clock.value)[0].action_id == request.action_id


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


def test_multi_target_review_rejects_stale_revision_before_any_mutation(
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

    with pytest.raises(ValueError, match="reviewed revision"):
        apply_review_decision(store, review)

    untouched = json.loads(
        (tmp_path / ".codex" / "loop-runs" / "run-1" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert untouched["phase"] == "stopped_budget"
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
