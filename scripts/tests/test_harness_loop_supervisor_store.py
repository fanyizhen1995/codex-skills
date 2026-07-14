from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import threading

import pytest

from scripts.loop_supervisor.models import (
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
)
from scripts.loop_supervisor.store import CursorError, SupervisorStore


class FakeClock:
    def __init__(self, value: datetime | None = None) -> None:
        self.value = value or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


def migrated_store(
    tmp_path: Path, *, clock: FakeClock | None = None
) -> SupervisorStore:
    store = SupervisorStore.open(tmp_path, clock=clock)
    store.migrate()
    return store


def action_request(
    run_id: str,
    *,
    revision: int,
    action_id: str = "action-1",
    payload: dict[str, object] | None = None,
) -> ActionRequest:
    return ActionRequest(
        action_id=action_id,
        run_id=run_id,
        run_revision=revision,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_PLANNER,
        idempotency_key=f"{run_id}:{revision}:planning:run_planner",
        payload=payload or {},
    )


def test_migrate_creates_required_tables_and_connection_pragmas(tmp_path):
    store = SupervisorStore.open(tmp_path)
    store.migrate()

    assert set(store.table_names()) >= {
        "runs",
        "actions",
        "action_attempts",
        "transitions",
        "failures",
        "reviews",
        "review_findings",
        "user_decisions",
        "services",
        "freshness_checks",
        "skill_snapshots",
        "aggregates",
        "schema_migrations",
    }
    assert store.pragma("journal_mode").lower() == "wal"
    assert store.pragma("foreign_keys") == 1
    assert store.pragma("busy_timeout") == 5000
    assert store.pragma("user_version") == 1


def test_migrate_is_idempotent_and_preserves_existing_rows(tmp_path):
    store = migrated_store(tmp_path)
    store.enqueue_action(action_request("run-1", revision=0))

    store.migrate()

    assert store.count("actions") == 1
    assert store.count("schema_migrations") == 1


def test_enqueue_action_is_idempotent_and_uses_storage_payload(tmp_path, monkeypatch):
    store = migrated_store(tmp_path)
    request = action_request(
        "run-1", revision=3, payload={"nested": {"items": ["one"]}}
    )
    calls = 0
    original = ActionRequest.payload_for_storage

    def storage_payload(self: ActionRequest) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return original(self)

    monkeypatch.setattr(ActionRequest, "payload_for_storage", storage_payload)
    first = store.enqueue_action(request)
    second = store.enqueue_action(request)

    assert first.action_id == second.action_id
    assert store.count("actions") == 1
    assert calls == 2
    assert first.payload == {"nested": {"items": ["one"]}}


def test_concurrent_begin_immediate_lease_has_one_winner(tmp_path):
    store = migrated_store(tmp_path)
    store.enqueue_action(action_request("run-1", revision=1))
    store.close()
    barrier = threading.Barrier(3)
    results: list[str | None] = []

    def claim(worker_id: str) -> None:
        worker_store = SupervisorStore.open(tmp_path)
        barrier.wait()
        leased = worker_store.lease_next_action(worker_id, lease_seconds=120)
        results.append(None if leased is None else leased.action_id)
        worker_store.close()

    threads = [
        threading.Thread(target=claim, args=(f"worker-{index}",)) for index in range(2)
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=5)

    assert not any(thread.is_alive() for thread in threads)
    assert sorted(result for result in results if result is not None) == ["action-1"]
    assert results.count(None) == 1


def test_renewed_heartbeat_prevents_expiry_reclaim_until_new_deadline(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    action = store.enqueue_action(action_request("run-1", revision=1))
    assert (
        store.lease_next_action("worker-a", lease_seconds=120).action_id
        == action.action_id
    )

    clock.advance(seconds=100)
    assert store.renew_lease(action.action_id, "worker-a", lease_seconds=120)
    clock.advance(seconds=21)
    assert store.lease_next_action("worker-b", lease_seconds=120) is None

    clock.advance(seconds=100)
    assert (
        store.lease_next_action("worker-b", lease_seconds=120).action_id
        == action.action_id
    )
    assert store.lease_next_action("worker-c", lease_seconds=120) is None


def test_expired_lease_can_be_reclaimed_once(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    action = store.enqueue_action(action_request("run-1", revision=1))
    assert (
        store.lease_next_action("worker-a", lease_seconds=120).action_id
        == action.action_id
    )

    clock.advance(seconds=121)

    assert (
        store.lease_next_action("worker-b", lease_seconds=120).action_id
        == action.action_id
    )
    assert store.lease_next_action("worker-c", lease_seconds=120) is None


def test_complete_action_records_attempt_and_status_in_one_transaction(tmp_path):
    store = migrated_store(tmp_path)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120)

    attempt = store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="planner completed",
            artifact_paths=(".codex/loop-runs/run-1/planner-result.json",),
        ),
    )

    assert attempt.action_id == action.action_id
    assert store.count("action_attempts") == 1
    assert store.get_action(action.action_id).status == "completed"


def test_complete_action_rolls_back_attempt_when_action_update_fails(tmp_path):
    store = migrated_store(tmp_path)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120)
    store._connection.execute(
        """
        CREATE TRIGGER reject_completion
        BEFORE UPDATE OF status ON actions
        WHEN NEW.status = 'completed'
        BEGIN
          SELECT RAISE(ABORT, 'completion rejected');
        END
        """
    )

    with pytest.raises(sqlite3.IntegrityError, match="completion rejected"):
        store.complete_action(
            action.action_id,
            "worker-a",
            ActionResult(result_class=ActionResultClass.SUCCESS, summary="done"),
        )

    assert store.count("action_attempts") == 0
    assert store.get_action(action.action_id).status == "leased"


def test_unchanged_reconcile_updates_last_seen_without_transition(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    store.upsert_run_projection(
        {
            "run_id": "run-1",
            "revision": 4,
            "policy": "autonomous_knowledge",
            "phase": "planning",
        }
    )
    original = store.get_run("run-1")

    clock.advance(seconds=30)
    store.upsert_run_projection(
        {
            "run_id": "run-1",
            "revision": 4,
            "policy": "autonomous_knowledge",
            "phase": "planning",
        }
    )

    assert store.count("transitions") == 0
    assert store.get_run("run-1")["last_seen_at"] > original["last_seen_at"]


def _seed_transitions(
    store: SupervisorStore, count: int, *, run_id: str = "run-1"
) -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        store.record_transition(
            run_id=run_id,
            from_revision=index,
            to_revision=index + 1,
            from_phase="planning",
            to_phase="generating",
            created_at=base + timedelta(seconds=index),
        )


@pytest.mark.parametrize("page_size", [20, 50, 100])
def test_list_page_accepts_documented_page_sizes(tmp_path, page_size):
    store = migrated_store(tmp_path)
    _seed_transitions(store, page_size + 1)

    page = store.list_page("transitions", page_size=page_size)

    assert len(page["items"]) == page_size
    assert page["page_size"] == page_size
    assert page["has_more"] is True
    assert page["next_cursor"]


def test_list_page_rejects_unsupported_page_size(tmp_path):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="page_size"):
        store.list_page("transitions", page_size=25)


def test_cursor_rejects_tampering_and_filter_mismatch(tmp_path):
    store = migrated_store(tmp_path)
    _seed_transitions(store, 21)
    page = store.list_page("transitions", page_size=20, filters={"run_id": "run-1"})
    envelope = json.loads(base64.urlsafe_b64decode(page["next_cursor"] + "=="))
    envelope["payload"]["primary_key"] = "transition-tampered"
    tampered = (
        base64.urlsafe_b64encode(
            json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode()
        )
        .decode()
        .rstrip("=")
    )

    with pytest.raises(CursorError, match="cursor"):
        store.list_page(
            "transitions", page_size=20, cursor=tampered, filters={"run_id": "run-1"}
        )
    with pytest.raises(CursorError, match="filter"):
        store.list_page(
            "transitions",
            page_size=20,
            cursor=page["next_cursor"],
            filters={"run_id": "run-2"},
        )


def test_cursor_boundary_is_stable_when_newer_row_is_inserted(tmp_path):
    store = migrated_store(tmp_path)
    _seed_transitions(store, 25)
    first = store.list_page("transitions", page_size=20)
    first_ids = {item["transition_id"] for item in first["items"]}

    store.record_transition(
        run_id="new-run",
        from_revision=0,
        to_revision=1,
        from_phase="planning",
        to_phase="generating",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    second = store.list_page("transitions", page_size=20, cursor=first["next_cursor"])
    second_ids = {item["transition_id"] for item in second["items"]}

    assert len(second["items"]) == 5
    assert first_ids.isdisjoint(second_ids)
    assert all(item["run_id"] != "new-run" for item in second["items"])
    assert second["previous_cursor"]


def test_retention_aggregates_rows_older_than_90_days_before_deleting(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    old_action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120)
    store.complete_action(
        old_action.action_id,
        "worker-a",
        ActionResult(
            result_class=ActionResultClass.RETRYABLE_FAILURE,
            summary="capacity",
            failure_key="capacity:planner",
        ),
    )
    store.record_transition(
        run_id="run-1",
        from_revision=0,
        to_revision=1,
        from_phase="planning",
        to_phase="generating",
    )
    store.record_review(
        review_id="review-old",
        trigger="cadence",
        status="completed",
        decision="continue",
        summary="continue",
    )
    clock.advance(days=90)
    store.record_transition(
        run_id="run-2",
        from_revision=0,
        to_revision=1,
        from_phase="planning",
        to_phase="generating",
    )
    clock.advance(seconds=1)

    result = store.compact_retention(retention_days=90)

    assert result == {"action_attempts": 1, "reviews": 1, "transitions": 1}
    assert store.count("action_attempts") == 0
    assert store.count("reviews") == 0
    assert store.count("transitions") == 1
    aggregates = store.fetch_all("aggregates")
    assert (
        sum(row["count"] for row in aggregates if row["aggregate_kind"] == "failure")
        == 1
    )
    assert {row["aggregate_kind"] for row in aggregates} >= {
        "action_attempts",
        "failure",
        "reviews",
        "transitions",
    }


def test_retention_does_not_delete_details_if_aggregation_fails(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    store.record_transition(
        run_id="run-1",
        from_revision=0,
        to_revision=1,
        from_phase="planning",
        to_phase="generating",
    )
    clock.advance(days=91)
    store._connection.execute(
        """
        CREATE TRIGGER reject_aggregate
        BEFORE INSERT ON aggregates
        BEGIN
          SELECT RAISE(ABORT, 'aggregate rejected');
        END
        """
    )

    with pytest.raises(sqlite3.IntegrityError, match="aggregate rejected"):
        store.compact_retention(retention_days=90)

    assert store.count("transitions") == 1
    assert store.count("aggregates") == 0
