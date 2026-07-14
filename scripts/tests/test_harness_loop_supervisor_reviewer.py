from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.harness_loop_agents import build_codex_exec_command
from scripts.harness_loop_orchestrator import _autonomous_planner_prompt
from scripts.loop_supervisor.executor import ACTION_HANDLERS
from scripts.loop_supervisor.models import ActionType, ReviewDecision
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
from scripts.loop_supervisor.store import SupervisorStore


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
    assert ActionType.RUN_REVIEWER not in ACTION_HANDLERS
    assert review_due_lineages(store, now=NOW + timedelta(minutes=5)) == []
    assert not list(tmp_path.rglob("audit-reports/audit-*.json"))


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


def test_scheduled_review_advances_cadence_even_if_run_revision_cancels_action(
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

    assert store.get_action(request.action_id).status == "cancelled"
    assert review_due_lineages(store, now=NOW) == []


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
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-a1", parent=1)
    record_parent_completion(store, "lineage-a", run_id="run-a2", parent=2)
    request = schedule_due_reviews(store, now=NOW)[0]

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
        validate_review_payload(payload)


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
    snapshot = store.fetch_all("skill_snapshots")[0]
    assert snapshot["total_skills"] == 3
    assert snapshot["used_skills"] == 1

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
