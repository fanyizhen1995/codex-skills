from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time

import pytest

from scripts.loop_supervisor.models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
)
from scripts.loop_supervisor.reconciler import ReconcileResult, _state_fingerprint
from scripts.loop_supervisor.reviewer_runtime import ActionLeaseGuard
from scripts.loop_supervisor.reviewer_safety import require_review_safety_clear
from scripts.loop_supervisor.store import LeaseError, SupervisorStore


def test_reconcile_payload_exposes_reviewer_launch_metadata() -> None:
    request = ActionRequest(
        action_id="action-review-contract",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="passed",
        action_type=ActionType.RUN_REVIEWER,
        idempotency_key="review-contract",
        queue_owner=ActionOwner.REVIEWER,
        not_before="2026-07-15T14:10:00+00:00",
    )

    payload = ReconcileResult(
        queued_actions=[request],
        open_user_decisions=[],
        run_records=[],
    ).as_dict()

    assert payload["queued_actions"][0]["queue_owner"] == "reviewer"
    assert payload["queued_actions"][0]["not_before"] == "2026-07-15T14:10:00+00:00"


def test_canonical_watch_launches_one_due_reviewer_without_waiting(
    tmp_path, monkeypatch
) -> None:
    from scripts.loop_supervisor import cli

    class RunningReviewer:
        def poll(self) -> None:
            return None

    launched: list[tuple[list[str], dict[str, object]]] = []
    maintenance_launches: list[Path] = []

    def popen(command: list[str], **kwargs: object) -> RunningReviewer:
        launched.append((command, kwargs))
        return RunningReviewer()

    payload = {
        "status": "healthy",
        "queued_actions": [
            {
                "action_id": "action-review-due",
                "run_id": "run-1",
                "run_revision": 1,
                "action_type": "run_reviewer",
                "queue_owner": "reviewer",
                "not_before": "",
                "phase": "passed",
                "task_id": "review:due",
            }
        ],
    }
    args = cli.argparse.Namespace(
        command="watch",
        interval_seconds=1,
        max_ticks=2,
        include_worktrees=False,
        dry_run=False,
    )
    monkeypatch.setattr(cli, "_reviewer_process", None)
    monkeypatch.setattr(cli, "run_supervisor_once", lambda _config: payload)
    monkeypatch.setattr(
        cli,
        "_launch_service_keeper",
        lambda root: maintenance_launches.append(root) or {"status": "launched"},
    )
    monkeypatch.setattr(cli, "_print_json", lambda _payload: None)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(cli.subprocess, "Popen", popen)

    assert cli._run_supervisor(tmp_path, args) == 0

    assert maintenance_launches == [tmp_path.resolve(), tmp_path.resolve()]
    assert len(launched) == 1
    command, kwargs = launched[0]
    assert command[:3] == [sys.executable, "-m", "scripts.loop_supervisor.reviewer"]
    assert command[command.index("--project-root") + 1] == str(tmp_path.resolve())
    assert kwargs["start_new_session"] is True
    assert "wait" not in RunningReviewer.__dict__


def test_canonical_watch_launches_preexisting_due_reviewer_from_durable_queue(
    tmp_path, monkeypatch
) -> None:
    from scripts.loop_supervisor import cli

    class RunningReviewer:
        def poll(self) -> None:
            return None

    launched: list[list[str]] = []

    def popen(command: list[str], **_kwargs: object) -> RunningReviewer:
        launched.append(command)
        return RunningReviewer()

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.upsert_run_projection(
            {
                "run_id": "run-preexisting-review",
                "revision": 4,
                "loop_lineage_id": "lineage-preexisting-review",
                "parent_run_id": "",
                "policy": "autonomous_knowledge",
                "phase": "passed",
                "status": "completed",
                "state_fingerprint": "fingerprint-preexisting-review",
                "summary": "{}",
                "artifact_refs": [],
            }
        )
        due = store.current_time() - timedelta(minutes=20)
        request = ActionRequest(
            action_id="action-review-preexisting",
            run_id="run-preexisting-review",
            run_revision=4,
            policy="autonomous_knowledge",
            phase="passed",
            action_type=ActionType.RUN_REVIEWER,
            idempotency_key="review-preexisting",
            queue_owner=ActionOwner.REVIEWER,
            not_before=(due + timedelta(minutes=10)).isoformat(),
            task_id="review:preexisting",
            next_action="supervisor_reviewer",
            payload={
                "trigger": "regular_cadence",
                "triggering_lineages": ["lineage-preexisting-review"],
                "cadence_positions": {"lineage-preexisting-review": 2},
                "reservation_id": "reservation-preexisting-review",
                "worker_executable": False,
            },
        )
        store.reserve_review_action(
            request,
            reservation_id="reservation-preexisting-review",
            lineage_positions={"lineage-preexisting-review": 2},
            due_at=due,
            not_before=due + timedelta(minutes=10),
        )

    monkeypatch.setattr(cli, "_reviewer_process", None)
    monkeypatch.setattr(cli.subprocess, "Popen", popen)

    assert cli._launch_due_reviewer(tmp_path, {"queued_actions": []}) is True
    assert len(launched) == 1


def test_canonical_watch_relaunches_reclaimable_reviewer_lease(
    tmp_path, monkeypatch
) -> None:
    from scripts.loop_supervisor import cli

    class RunningReviewer:
        def poll(self) -> None:
            return None

    launched: list[list[str]] = []

    def popen(command: list[str], **_kwargs: object) -> RunningReviewer:
        launched.append(command)
        return RunningReviewer()

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.upsert_run_projection(
            {
                "run_id": "run-reclaimable-review",
                "revision": 4,
                "loop_lineage_id": "lineage-reclaimable-review",
                "parent_run_id": "",
                "policy": "autonomous_knowledge",
                "phase": "passed",
                "status": "completed",
                "state_fingerprint": "fingerprint-reclaimable-review",
                "summary": "{}",
                "artifact_refs": [],
            }
        )
        due = store.current_time() - timedelta(minutes=20)
        request = ActionRequest(
            action_id="action-review-reclaimable",
            run_id="run-reclaimable-review",
            run_revision=4,
            policy="autonomous_knowledge",
            phase="passed",
            action_type=ActionType.RUN_REVIEWER,
            idempotency_key="review-reclaimable",
            queue_owner=ActionOwner.REVIEWER,
            not_before=(due + timedelta(minutes=10)).isoformat(),
            task_id="review:reclaimable",
            next_action="supervisor_reviewer",
            payload={
                "trigger": "regular_cadence",
                "triggering_lineages": ["lineage-reclaimable-review"],
                "cadence_positions": {"lineage-reclaimable-review": 2},
                "reservation_id": "reservation-reclaimable-review",
                "worker_executable": False,
            },
        )
        store.reserve_review_action(
            request,
            reservation_id="reservation-reclaimable-review",
            lineage_positions={"lineage-reclaimable-review": 2},
            due_at=due,
            not_before=due + timedelta(minutes=10),
        )
        leased = store.lease_next_action(
            "dead-reviewer",
            lease_seconds=60,
            allowed_action_types={ActionType.RUN_REVIEWER.value},
            allowed_queue_owners={ActionOwner.REVIEWER.value},
        )
        assert leased is not None
        store._connection.execute(
            "update actions set lease_expires_at = ? where action_id = ?",
            ("2000-01-01T00:00:00.000000Z", request.action_id),
        )
        store._connection.execute(
            "update workers set heartbeat_at = ? where worker_id = ?",
            ("2000-01-01T00:00:00.000000Z", "dead-reviewer"),
        )

    monkeypatch.setattr(cli, "_reviewer_process", None)
    monkeypatch.setattr(cli.subprocess, "Popen", popen)

    assert cli._launch_due_reviewer(tmp_path, {"queued_actions": []}) is True
    assert len(launched) == 1


def test_canonical_watch_does_not_launch_second_reviewer_after_cold_restart(
    tmp_path, monkeypatch
) -> None:
    from scripts.loop_supervisor import cli

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        due = store.current_time() - timedelta(minutes=20)
        for index in (1, 2):
            run_id = f"run-review-{index}"
            lineage_id = f"lineage-review-{index}"
            store.upsert_run_projection(
                {
                    "run_id": run_id,
                    "revision": 1,
                    "loop_lineage_id": lineage_id,
                    "parent_run_id": "",
                    "policy": "autonomous_knowledge",
                    "phase": "passed",
                    "status": "completed",
                    "state_fingerprint": f"fingerprint-review-{index}",
                    "summary": "{}",
                    "artifact_refs": [],
                }
            )
            request = ActionRequest(
                action_id=f"action-review-{index}",
                run_id=run_id,
                run_revision=1,
                policy="autonomous_knowledge",
                phase="passed",
                action_type=ActionType.RUN_REVIEWER,
                idempotency_key=f"review-{index}",
                queue_owner=ActionOwner.REVIEWER,
                task_id=f"review:{index}",
                next_action="supervisor_reviewer",
                payload={
                    "trigger": "regular_cadence",
                    "triggering_lineages": [lineage_id],
                    "cadence_positions": {lineage_id: 2},
                    "reservation_id": f"reservation-review-{index}",
                    "worker_executable": False,
                },
            )
            store.reserve_review_action(
                request,
                reservation_id=f"reservation-review-{index}",
                lineage_positions={lineage_id: 2},
                due_at=due,
                not_before=due,
            )
        leased = store.lease_next_action(
            "live-reviewer",
            lease_seconds=300,
            allowed_action_types={ActionType.RUN_REVIEWER.value},
            allowed_queue_owners={ActionOwner.REVIEWER.value},
        )
        assert leased is not None

    monkeypatch.setattr(cli, "_reviewer_process", None)
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("second Reviewer was launched"),
    )
    payload = {
        "queued_actions": [
            {
                "action_type": "run_reviewer",
                "queue_owner": "reviewer",
                "not_before": "",
            }
        ]
    }

    assert cli._launch_due_reviewer(tmp_path, payload) is False


def test_canonical_watch_does_not_launch_reviewer_while_migration_is_blocked(
    tmp_path, monkeypatch
) -> None:
    from scripts.loop_supervisor import cli

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.record_review(
            review_id="review-blocked-migration",
            trigger="migration",
            status="review_migration_blocked",
            decision="refocus",
            summary="Operator resolution is required.",
        )

    monkeypatch.setattr(cli, "_reviewer_process", None)
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("blocked migration launched Reviewer"),
    )
    payload = {
        "queued_actions": [
            {
                "action_type": "run_reviewer",
                "queue_owner": "reviewer",
                "not_before": "",
            }
        ]
    }

    assert cli._launch_due_reviewer(tmp_path, payload) is False


def test_cli_resolves_blocked_review_migration(tmp_path, monkeypatch) -> None:
    from scripts.loop_supervisor import cli

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        store.record_review(
            review_id="review-cli-blocked",
            trigger="migration",
            status="review_migration_blocked",
            decision="refocus",
            summary="Operator resolution is required.",
        )
    output: list[dict[str, object]] = []
    monkeypatch.setattr(cli, "_print_json", lambda payload: output.append(dict(payload)))

    status = cli.main(
        [
            "resolve-review-migration",
            "--project-root",
            str(tmp_path),
            "--review-id",
            "review-cli-blocked",
            "--reason",
            "Verified that the review was never applied.",
        ]
    )

    assert status == 0
    assert output == [
        {
            "review_id": "review-cli-blocked",
            "source_action_id": "",
            "retried_action_id": "",
            "status": "review_superseded",
        }
    ]


def test_canonical_watch_checks_durable_reviewer_queue_before_reconcile(
    tmp_path, monkeypatch
) -> None:
    from scripts.loop_supervisor import cli

    calls: list[str] = []

    def launch(_root: Path, payload: dict[str, object]) -> bool:
        calls.append(f"launch:{payload['queued_actions']}")
        return False

    def reconcile(_config: object) -> dict[str, object]:
        calls.append("reconcile")
        return {"status": "healthy", "queued_actions": []}

    args = cli.argparse.Namespace(
        command="watch",
        interval_seconds=1,
        max_ticks=1,
        include_worktrees=False,
        dry_run=False,
    )
    monkeypatch.setattr(cli, "_launch_due_reviewer", launch)
    monkeypatch.setattr(
        cli, "_launch_service_keeper", lambda _root: {"status": "launched"}
    )
    monkeypatch.setattr(cli, "run_supervisor_once", reconcile)
    monkeypatch.setattr(cli, "_print_json", lambda _payload: None)

    assert cli._run_supervisor(tmp_path, args) == 0
    assert calls == ["launch:[]", "reconcile", "launch:[]"]


NOW = datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)


def leased_supervisor_action(tmp_path):
    store = SupervisorStore.open(tmp_path)
    store.migrate()
    run_path = Path(tmp_path) / ".codex" / "loop-runs" / "run-1" / "run.json"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": "run-1",
        "state_revision": 1,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "run_kind": "single",
        "task_id": "runtime-test",
        "domain": "",
        "branch": "main",
        "worktree": str(tmp_path),
        "requirement": "lease guard test",
        "constraints": [],
        "stop_conditions": [],
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
        "last_result": "none",
        "next_action": "run_autonomous_planner",
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
    }
    run_path.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    store.upsert_run_projection(
        {
            "run_id": "run-1",
            "revision": 1,
            "loop_lineage_id": "lineage-a",
            "parent_run_id": "",
            "policy": "autonomous_knowledge",
            "phase": "planning",
            "status": "actionable",
            "state_fingerprint": _state_fingerprint(payload),
            "summary": "{}",
            "artifact_refs": [run_path.relative_to(tmp_path).as_posix()],
        }
    )
    request = ActionRequest(
        action_id="action-supervisor-test",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.REFOCUS_RUN,
        idempotency_key="supervisor-test",
        queue_owner=ActionOwner.SUPERVISOR,
    )
    store.enqueue_action(request)
    leased = store.claim_pending_action(
        request.action_id,
        "reviewer-test",
        lease_seconds=2,
    )
    assert leased is not None
    return store, request


def test_action_lease_guard_heartbeats_while_reviewer_work_is_blocked(
    tmp_path, monkeypatch
) -> None:
    store, request = leased_supervisor_action(tmp_path)
    renewals: list[str] = []
    original = store.renew_lease

    def observed_renew(action_id, owner_id, *, lease_seconds):
        renewals.append(action_id)
        return original(action_id, owner_id, lease_seconds=lease_seconds)

    monkeypatch.setattr(store, "renew_lease", observed_renew)

    with ActionLeaseGuard(
        store,
        action_id=request.action_id,
        owner_id="reviewer-test",
        lease_seconds=2,
        heartbeat_seconds=0.01,
    ):
        time.sleep(0.05)

    assert len(renewals) >= 2


def test_action_lease_guard_prevents_side_effect_after_lease_loss(
    tmp_path, monkeypatch
) -> None:
    store, request = leased_supervisor_action(tmp_path)
    side_effects: list[str] = []

    with ActionLeaseGuard(
        store,
        action_id=request.action_id,
        owner_id="reviewer-test",
        lease_seconds=2,
        heartbeat_seconds=60,
    ) as guard:
        monkeypatch.setattr(store, "renew_lease", lambda *_args, **_kwargs: False)
        with pytest.raises(LeaseError, match="lease lost"):
            guard.checkpoint()
        if not guard.lease_lost:
            side_effects.append("mutated")

    assert side_effects == []


def test_supervisor_orphaned_source_projection_blocks_renewal_and_completion(
    tmp_path,
) -> None:
    store, request = leased_supervisor_action(tmp_path)
    store._connection.execute("DELETE FROM runs WHERE run_id = ?", (request.run_id,))

    assert (
        store.renew_lease(request.action_id, "reviewer-test", lease_seconds=2)
        is False
    )
    with pytest.raises(LeaseError, match="authoritative run projection"):
        store.complete_action(
            request.action_id,
            "reviewer-test",
            ActionResult(
                result_class=ActionResultClass.SUCCESS,
                summary="must not complete without a source projection",
            ),
        )


def test_action_lease_guard_rejects_renewal_after_global_stop(tmp_path) -> None:
    store, request = leased_supervisor_action(tmp_path)

    with ActionLeaseGuard(
        store,
        action_id=request.action_id,
        owner_id="reviewer-test",
        lease_seconds=2,
        heartbeat_seconds=60,
        safety_checkpoint=lambda: require_review_safety_clear(store),
    ) as guard:
        store.open_user_decision(
            scope="global",
            summary="Stop project automation.",
            failure_key="global-stop:test",
            required_decision="Resolve the global stop.",
        )

        with pytest.raises(LeaseError, match="safety gate"):
            guard.checkpoint()

    assert store.get_action(request.action_id).status == "leased"


def test_supervisor_renew_lease_transactionally_rejects_global_decision(tmp_path) -> None:
    store, request = leased_supervisor_action(tmp_path)
    store.open_user_decision(
        scope="global",
        summary="Stop project automation.",
        failure_key="global-stop:transactional-renewal",
        required_decision="Resolve the global stop.",
    )

    assert not store.renew_lease(
        request.action_id,
        "reviewer-test",
        lease_seconds=2,
    )
