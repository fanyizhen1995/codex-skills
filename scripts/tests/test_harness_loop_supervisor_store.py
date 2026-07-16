from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

import pytest

from scripts.harness_loop_runtime_lock import acquire_run_lock
from scripts.loop_supervisor.models import (
    ActionOwner,
    ActionRequest,
    ActionResult,
    ActionResultClass,
    ActionType,
    SkillInvocationEvidence,
)
from scripts.loop_supervisor.store import CursorError, LeaseError, SupervisorStore


class FakeClock:
    def __init__(self, value: datetime | None = None) -> None:
        self.value = value or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


class ObservableClock(FakeClock):
    def __init__(self, value: datetime | None = None) -> None:
        super().__init__(value)
        self.observed: threading.Event | None = None

    def now(self) -> datetime:
        if self.observed is not None:
            self.observed.set()
        return super().now()

    def observe(self) -> threading.Event:
        self.observed = threading.Event()
        return self.observed


class CommitFailOnceConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.fail_commit = True
        self.rollback_calls = 0

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def commit(self) -> None:
        if self.fail_commit:
            self.fail_commit = False
            raise sqlite3.OperationalError("injected commit failure")
        self.connection.commit()

    def rollback(self) -> None:
        self.rollback_calls += 1
        self.connection.rollback()


def migrated_store(
    tmp_path: Path, *, clock: FakeClock | None = None
) -> SupervisorStore:
    store = SupervisorStore.open(tmp_path, clock=clock)
    store.migrate()
    return store


def legacy_finding_store(
    tmp_path: Path, *, version: int, invalid_timestamp: bool = False
) -> SupervisorStore:
    db_path = tmp_path / ".codex" / "supervisor" / "supervisor.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(
        f"""
        PRAGMA user_version={version};
        CREATE TABLE reviews (
          review_id TEXT PRIMARY KEY,
          trigger TEXT NOT NULL,
          status TEXT NOT NULL,
          decision TEXT NOT NULL DEFAULT '',
          summary TEXT NOT NULL DEFAULT '',
          evidence_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE review_findings (
          finding_id TEXT PRIMARY KEY,
          review_id TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
          finding_key TEXT NOT NULL,
          status TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          remediation_action_id TEXT NOT NULL DEFAULT '',
          occurrence_count INTEGER NOT NULL DEFAULT 1,
          first_seen_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(finding_key, status)
        );
        INSERT INTO reviews(
          review_id, trigger, status, decision, summary, created_at, updated_at
        ) VALUES (
          'review-legacy', 'cadence', 'completed', 'continue', 'legacy',
          '2025-12-31T21:00:00', '2025-12-31T21:30:00'
        );
        """
    )
    open_last_seen = (
        "invalid-time" if invalid_timestamp else "2026-01-01T01:30:00+02:00"
    )
    connection.executemany(
        """
        INSERT INTO review_findings(
          finding_id, review_id, finding_key, status, summary, occurrence_count,
          first_seen_at, last_seen_at, created_at, updated_at
        ) VALUES (?, 'review-legacy', 'legacy-key', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                "finding-open",
                "open",
                "lexically-later-but-utc-earlier",
                2,
                "2025-12-31T22:00:00",
                open_last_seen,
                "2025-12-31T22:00:00",
                open_last_seen,
            ),
            (
                "finding-closed",
                "closed",
                "utc-latest",
                1,
                "2025-12-31T23:00:00Z",
                "2025-12-31T23:45:00Z",
                "2025-12-31T23:40:00Z",
                "2025-12-31T23:45:00Z",
            ),
        ),
    )
    connection.commit()
    connection.close()
    return SupervisorStore.open(tmp_path)


def action_request(
    run_id: str,
    *,
    revision: int,
    action_id: str = "action-1",
    payload: dict[str, object] | None = None,
    phase: str = "planning",
    action_type: ActionType = ActionType.RUN_PLANNER,
    task_id: str = "",
    policy: str = "autonomous_knowledge",
    idempotency_key: str | None = None,
) -> ActionRequest:
    return ActionRequest(
        action_id=action_id,
        run_id=run_id,
        run_revision=revision,
        policy=policy,
        phase=phase,
        action_type=action_type,
        idempotency_key=idempotency_key
        or f"{run_id}:{revision}:{phase}:{action_type.value}:{task_id}",
        task_id=task_id,
        payload=payload or {},
    )


def project_run(
    store: SupervisorStore,
    run_id: str,
    *,
    revision: int,
    phase: str = "planning",
    state_fingerprint: str = "",
) -> None:
    store.upsert_run_projection(
        {
            "run_id": run_id,
            "revision": revision,
            "policy": "autonomous_knowledge",
            "phase": phase,
            "state_fingerprint": state_fingerprint,
        }
    )


def test_migrate_creates_required_tables_and_connection_pragmas(tmp_path):
    store = SupervisorStore.open(tmp_path)
    store.migrate()

    assert set(store.table_names()) >= {
        "runs",
        "actions",
        "action_idempotency_aliases",
        "action_attempts",
        "transitions",
        "failures",
        "reviews",
        "review_findings",
        "review_reservations",
        "review_cadence",
        "review_safety_gates",
        "review_applications",
        "review_application_targets",
        "user_decisions",
        "services",
        "workers",
        "freshness_checks",
        "skill_snapshots",
        "skill_invocations",
        "aggregates",
        "schema_migrations",
        "row_sequences",
    }
    assert store.pragma("journal_mode").lower() == "wal"
    assert store.pragma("foreign_keys") == 1
    assert store.pragma("busy_timeout") == 5000
    assert store.pragma("user_version") == 15
    assert "state_fingerprint" in {
        row["name"] for row in store._connection.execute("PRAGMA table_info(runs)")
    }
    assert "deferred_position" in {
        row["name"]
        for row in store._connection.execute("PRAGMA table_info(review_cadence)")
    }


def test_deterministic_skill_snapshot_id_is_immutable(tmp_path: Path) -> None:
    store = migrated_store(tmp_path)
    snapshot = {
        "inventory": [
            {
                "name": "alpha",
                "path": "skills/alpha/SKILL.md",
                "description": "Validate loop evidence.",
                "normalized_purpose": "validate loop evidence",
            }
        ],
        "confirmed_usage": [],
        "duplicate_groups": [],
        "reviewer_recommendations": [],
    }

    first = store.record_skill_snapshot(
        snapshot,
        snapshot_id="skill-snapshot-review-immutable",
    )
    replayed = store.record_skill_snapshot(
        snapshot,
        snapshot_id="skill-snapshot-review-immutable",
    )
    changed = json.loads(json.dumps(snapshot))
    changed["inventory"][0]["description"] = "Mutated evidence."

    with pytest.raises(ValueError, match="skill snapshot identity changed"):
        store.record_skill_snapshot(
            changed,
            snapshot_id="skill-snapshot-review-immutable",
        )

    assert replayed == first
    stored = store.fetch_all("skill_snapshots")
    assert len(stored) == 1
    assert json.loads(stored[0]["snapshot_json"]) == snapshot


def test_migrate_adds_state_fingerprint_to_v7_run_projection(tmp_path):
    db_path = tmp_path / ".codex" / "supervisor" / "supervisor.db"
    db_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        PRAGMA user_version=7;
        CREATE TABLE runs (
          run_id TEXT PRIMARY KEY,
          loop_lineage_id TEXT NOT NULL DEFAULT '',
          parent_run_id TEXT NOT NULL DEFAULT '',
          policy TEXT NOT NULL DEFAULT '',
          phase TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT '',
          revision INTEGER NOT NULL CHECK (revision >= 0),
          summary_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL
        );
        INSERT INTO runs(
          run_id, policy, phase, revision, created_at, updated_at, last_seen_at
        ) VALUES (
          'legacy-run', 'autonomous_knowledge', 'planning', 4,
          '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z',
          '2026-01-01T00:00:00Z'
        );
        """
    )
    connection.commit()
    connection.close()

    store = SupervisorStore.open(tmp_path)
    store.migrate()

    assert store.pragma("user_version") == 15
    assert store.get_run("legacy-run")["state_fingerprint"] == ""


def test_migrate_v14_adds_deferred_review_cadence_without_losing_positions(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".codex" / "supervisor" / "supervisor.db"
    db_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        PRAGMA user_version=14;
        CREATE TABLE review_cadence (
          lineage_id TEXT PRIMARY KEY,
          reviewed_position INTEGER NOT NULL DEFAULT 0,
          reserved_position INTEGER NOT NULL DEFAULT 0,
          reservation_id TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL
        );
        INSERT INTO review_cadence(
          lineage_id, reviewed_position, reserved_position,
          reservation_id, updated_at
        ) VALUES (
          'lineage-a', 22, 24, 'reservation-24',
          '2026-07-16T00:00:00.000000Z'
        );
        """
    )
    connection.commit()
    connection.close()

    store = SupervisorStore.open(tmp_path)
    store.migrate()

    cadence = store.review_cadence_positions()["lineage-a"]
    assert cadence["reviewed_position"] == 22
    assert cadence["deferred_position"] == 0
    assert cadence["reserved_position"] == 24
    assert cadence["reservation_id"] == "reservation-24"
    assert store.pragma("user_version") == 15


def test_migrate_is_idempotent_and_preserves_existing_rows(tmp_path):
    store = migrated_store(tmp_path)
    store.enqueue_action(action_request("run-1", revision=0))

    store.migrate()

    assert store.count("actions") == 1
    assert store.count("schema_migrations") == 1


def test_migrate_adds_latest_freshness_index_to_existing_database(tmp_path):
    database = tmp_path / ".codex" / "supervisor" / "supervisor.db"
    database.parent.mkdir(parents=True)
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE freshness_checks (
          check_id TEXT PRIMARY KEY,
          target TEXT NOT NULL,
          status TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          details_json TEXT NOT NULL DEFAULT '{}',
          checked_at TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO freshness_checks(
          check_id, target, status, checked_at, created_at
        ) VALUES ('legacy-check', 'wiki', 'fresh',
                  '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
        """
    )
    connection.commit()
    connection.close()

    with SupervisorStore.open(tmp_path) as store:
        store.migrate()
        index = store._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
            ("freshness_checks_target_latest_idx",),
        ).fetchone()
        preserved = store.fetch_all("freshness_checks")

    assert index is not None
    assert "(target, checked_at DESC, check_id DESC)" in str(index["sql"])
    assert [row["check_id"] for row in preserved] == ["legacy-check"]


def test_migrate_backfills_legacy_reviewer_actions_to_reviewer_owner(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    request = ActionRequest(
        action_id="legacy-reviewer-action",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_REVIEWER,
        idempotency_key="legacy-reviewer-action",
        queue_owner=ActionOwner.REVIEWER,
    )
    store.enqueue_action(request)
    store._connection.execute(
        "UPDATE actions SET queue_owner = 'worker' WHERE action_id = ?",
        (request.action_id,),
    )
    store._connection.commit()
    store.close()

    reopened = SupervisorStore.open(tmp_path)
    reopened.migrate()

    assert reopened.get_action(request.action_id).queue_owner == ActionOwner.REVIEWER.value


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


def test_enqueue_deduplicates_same_canonical_identity_with_different_external_key(
    tmp_path,
):
    store = migrated_store(tmp_path)
    first = store.enqueue_action(
        action_request("run-1", revision=3, idempotency_key="external-key-one")
    )

    second = store.enqueue_action(
        action_request(
            "run-1",
            revision=3,
            action_id="action-2",
            idempotency_key="external-key-two",
        )
    )

    assert second.action_id == first.action_id
    assert store.count("actions") == 1


def test_canonical_dedupe_persists_new_idempotency_key_as_unique_alias(tmp_path):
    store = migrated_store(tmp_path)
    first = store.enqueue_action(
        action_request("run-1", revision=1, idempotency_key="K1")
    )
    duplicate = store.enqueue_action(
        action_request("run-1", revision=1, action_id="action-2", idempotency_key="K2")
    )
    assert duplicate.action_id == first.action_id

    with pytest.raises(ValueError, match="idempotency identity conflict"):
        store.enqueue_action(
            action_request(
                "run-2", revision=1, action_id="action-3", idempotency_key="K2"
            )
        )

    aliases = store.fetch_all("action_idempotency_aliases")
    assert {row["idempotency_key"] for row in aliases} == {"K1", "K2"}
    assert {row["action_id"] for row in aliases} == {first.action_id}
    assert store.count("actions") == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"run_id": "run-2"},
        {"revision": 4},
        {"phase": "generating"},
        {"action_type": ActionType.RUN_GENERATOR},
        {"task_id": "task-2"},
        {"policy": "demand_development"},
    ],
)
def test_enqueue_rejects_idempotency_key_collision_with_different_identity(
    tmp_path, overrides
):
    store = migrated_store(tmp_path)
    store.enqueue_action(
        action_request(
            "run-1",
            revision=3,
            task_id="task-1",
            idempotency_key="shared-key",
        )
    )
    incoming = {
        "run_id": "run-1",
        "revision": 3,
        "action_id": "action-2",
        "task_id": "task-1",
        "idempotency_key": "shared-key",
    }
    incoming.update(overrides)

    with pytest.raises(ValueError, match="idempotency identity conflict"):
        store.enqueue_action(action_request(**incoming))

    stored = store.get_action("action-1")
    assert stored.run_id == "run-1"
    assert stored.run_revision == 3
    assert stored.phase == "planning"
    assert stored.action_type == "run_planner"


@pytest.mark.parametrize(
    "payload",
    [
        {"stdout": "full command output"},
        {"nested": {"stderr": "full error output"}},
        {"result": {"raw_logs": ["line one", "line two"]}},
        {"captured_stdout": "full command output"},
        {"nested": {"process_stderr": "full error output"}},
        {"result": {"worker_stdout_excerpt": "many log lines"}},
    ],
)
def test_enqueue_rejects_recursive_inline_log_body_keys(tmp_path, payload):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="log body"):
        store.enqueue_action(action_request("run-1", revision=1, payload=payload))


def test_enqueue_rejects_oversized_payload_but_allows_log_path_references(tmp_path):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="payload"):
        store.enqueue_action(
            action_request("run-1", revision=1, payload={"blob": "x" * 70_000})
        )

    stored = store.enqueue_action(
        action_request(
            "run-1",
            revision=2,
            action_id="action-2",
            payload={
                "stdout_path": ".codex/loop-runs/run-1/stdout.log",
                "stderr_path": ".codex/loop-runs/run-1/stderr.log",
                "captured_stdout_ref": "artifacts/stdout.log",
            },
        )
    )
    assert stored.payload["stdout_path"].endswith("stdout.log")


@pytest.mark.parametrize(
    ("checkpoint", "error"),
    [
        (123, TypeError),
        ("line-one\nline-two", ValueError),
        ("x" * 513, ValueError),
        ("captured stdout body", ValueError),
    ],
)
def test_complete_action_rejects_unsafe_checkpoint(tmp_path, checkpoint, error):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)

    with pytest.raises(error, match="checkpoint"):
        store.complete_action(
            action.action_id,
            "worker-a",
            ActionResult(
                result_class=ActionResultClass.SUCCESS,
                summary="done",
                checkpoint=checkpoint,
            ),
        )

    assert store.count("action_attempts") == 0


def test_complete_action_accepts_safe_single_line_checkpoint_reference(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)

    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="done",
            checkpoint="planner:step-2",
        ),
    )

    assert store.fetch_all("action_attempts")[0]["checkpoint"] == "planner:step-2"


@pytest.mark.parametrize(
    "artifact_path",
    [
        "/tmp/result.json",
        "../result.json",
        "artifacts/../../result.json",
        "C:\\temp\\result.json",
    ],
)
def test_enqueue_rejects_unsafe_artifact_references(tmp_path, artifact_path):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="artifact"):
        store.enqueue_action(
            action_request("run-1", revision=1), artifact_paths=(artifact_path,)
        )


def test_enqueue_rejects_artifact_reference_through_symlink(tmp_path):
    store = migrated_store(tmp_path)
    (tmp_path / "real-artifacts").mkdir()
    (tmp_path / "linked-artifacts").symlink_to(tmp_path / "real-artifacts")

    with pytest.raises(ValueError, match="symlink"):
        store.enqueue_action(
            action_request("run-1", revision=1),
            artifact_paths=("linked-artifacts/result.json",),
        )


def test_enqueue_validates_explicit_artifact_refs_inside_payload(tmp_path):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="artifact"):
        store.enqueue_action(
            action_request(
                "run-1",
                revision=1,
                payload={"artifact_refs": ["../outside/result.json"]},
            )
        )


def test_store_rejects_oversized_summary(tmp_path):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="summary"):
        store.record_failure("failure-1", summary="x" * 4097)
    with pytest.raises(ValueError, match="encoded bytes"):
        store.record_failure("failure-2", summary="\u4e2d" * 3000)


def test_concurrent_begin_immediate_lease_has_one_winner(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    store.enqueue_action(action_request("run-1", revision=1))
    store.close()
    barrier = threading.Barrier(3)
    results: list[str | None] = []

    def claim(worker_id: str) -> None:
        worker_store = SupervisorStore.open(tmp_path)
        barrier.wait()
        leased = worker_store.lease_next_action(
            worker_id, lease_seconds=120, heartbeat_stale_seconds=60
        )
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


def test_shared_store_connection_serializes_two_thread_writes(tmp_path):
    store = migrated_store(tmp_path)
    barrier = threading.Barrier(3)
    errors: list[BaseException] = []

    def write_failures() -> None:
        barrier.wait()
        for _ in range(100):
            try:
                store.record_failure("shared-failure", summary="same observation")
            except BaseException as exc:
                errors.append(exc)

    threads = [threading.Thread(target=write_failures) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)

    assert not any(thread.is_alive() for thread in threads)
    assert errors == []
    assert store.fetch_all("failures")[0]["occurrence_count"] == 200


def test_update_failure_resolution_does_not_increment_occurrence_count(tmp_path):
    store = migrated_store(tmp_path)
    store.record_failure("episode-1", resolution='{"status":"open"}')

    updated = store.update_failure_resolution(
        "episode-1", '{"status":"closed"}'
    )

    assert updated["resolution"] == '{"status":"closed"}'
    assert updated["occurrence_count"] == 1


def test_requeue_failed_action_only_reopens_failed_row(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120)
    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(
            result_class=ActionResultClass.RETRYABLE_FAILURE,
            summary="retry",
            failure_key="retry:run-1",
        ),
    )

    assert store.requeue_failed_action(action.action_id, recovery_tier=1) is True
    assert store.get_action(action.action_id).status == "pending"
    assert store.requeue_failed_action(action.action_id, recovery_tier=1) is False


def test_commit_failure_rolls_back_and_connection_remains_usable(tmp_path):
    store = migrated_store(tmp_path)
    wrapped = CommitFailOnceConnection(store._connection)
    store._connection = wrapped

    with pytest.raises(sqlite3.OperationalError, match="injected commit failure"):
        store.record_failure("failed-commit", summary="must roll back")

    assert wrapped.rollback_calls == 1
    store.record_failure("after-rollback", summary="connection recovered")
    assert store.count("failures") == 1
    assert store.fetch_all("failures")[0]["failure_key"] == "after-rollback"


def test_renewed_heartbeat_prevents_expiry_reclaim_until_new_deadline(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    assert (
        store.lease_next_action(
            "worker-a", lease_seconds=120, heartbeat_stale_seconds=60
        ).action_id
        == action.action_id
    )

    clock.advance(seconds=100)
    assert store.renew_lease(action.action_id, "worker-a", lease_seconds=120)
    clock.advance(seconds=21)
    assert (
        store.lease_next_action(
            "worker-b", lease_seconds=120, heartbeat_stale_seconds=60
        )
        is None
    )

    clock.advance(seconds=100)
    assert (
        store.lease_next_action(
            "worker-b", lease_seconds=120, heartbeat_stale_seconds=60
        ).action_id
        == action.action_id
    )
    assert (
        store.lease_next_action(
            "worker-c", lease_seconds=120, heartbeat_stale_seconds=60
        )
        is None
    )


def test_expired_lease_can_be_reclaimed_once(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    assert (
        store.lease_next_action(
            "worker-a", lease_seconds=120, heartbeat_stale_seconds=60
        ).action_id
        == action.action_id
    )


def test_reviewer_lease_prioritizes_persisted_application_recovery(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-without-outbox", revision=1)
    project_run(store, "run-with-outbox", revision=1)

    def reviewer_request(action_id: str, run_id: str) -> ActionRequest:
        return ActionRequest(
            action_id=action_id,
            run_id=run_id,
            run_revision=1,
            policy="autonomous_knowledge",
            phase="planning",
            action_type=ActionType.RUN_REVIEWER,
            idempotency_key=action_id,
            queue_owner=ActionOwner.REVIEWER,
            task_id=f"review:{run_id}",
        )

    without_outbox = store.enqueue_action(
        reviewer_request("reviewer-without-outbox", "run-without-outbox")
    )
    store.record_review(
        review_id="review-without-outbox",
        trigger="project_global",
        status="review_applying",
        decision="auto_remediate",
        accepted_review={"review_id": "review-without-outbox"},
        source_action_id=without_outbox.action_id,
    )
    clock.advance(seconds=1)
    with_outbox = store.enqueue_action(
        reviewer_request("reviewer-with-outbox", "run-with-outbox")
    )
    store.record_review(
        review_id="review-with-outbox",
        trigger="project_global",
        status="review_applying",
        decision="auto_remediate",
        accepted_review={"review_id": "review-with-outbox"},
        source_action_id=with_outbox.action_id,
    )
    target_action = ActionRequest(
        action_id="review-application-target",
        run_id="run-with-outbox",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_ALTERNATE_RECOVERY,
        idempotency_key="review-application-target",
        queue_owner=ActionOwner.SUPERVISOR,
        task_id="review:review-with-outbox:run-with-outbox",
        next_action="auto_remediate",
    )
    store.prepare_review_application(
        review_id="review-with-outbox",
        decision="auto_remediate",
        targets=[
            (
                target_action,
                {
                    "expected_revision": 1,
                    "expected_fingerprint": "fingerprint-before",
                    "expected_post_write_fingerprint": "fingerprint-after",
                    "source_phase": "planning",
                    "target_phase": "planning",
                    "target_next_action": "run_autonomous_planner",
                    "target_last_result": "none",
                },
            )
        ],
    )

    leased = store.lease_next_action(
        "reviewer-recovery",
        lease_seconds=120,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
        allowed_queue_owners={ActionOwner.REVIEWER.value},
    )

    assert leased is not None
    assert leased.action_id == with_outbox.action_id


def test_lease_next_action_uses_compatible_default_heartbeat_threshold(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))

    leased = store.lease_next_action("worker-a", lease_seconds=120)

    assert leased.action_id == action.action_id


def test_open_global_decision_blocks_all_leases_until_resolved(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    decision = store.open_user_decision(
        scope="global",
        failure_key="safety:secret",
        summary="confirmed secret exposure",
    )

    assert store.lease_next_action("worker-a", lease_seconds=120) is None

    store.close_user_decision(decision["decision_id"], resolution="secret removed")
    assert (
        store.lease_next_action("worker-a", lease_seconds=120).action_id
        == action.action_id
    )


def test_open_run_decision_blocks_only_matching_run_lease(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "blocked-run", revision=1)
    project_run(store, "safe-run", revision=1)
    blocked = store.enqueue_action(
        action_request("blocked-run", revision=1, action_id="blocked-action")
    )
    safe = store.enqueue_action(
        action_request("safe-run", revision=1, action_id="safe-action")
    )
    store.open_user_decision(
        scope="run",
        run_id="blocked-run",
        failure_key="run:approval",
        summary="run approval required",
    )

    assert (
        store.lease_next_action("worker-a", lease_seconds=120).action_id
        == safe.action_id
    )
    assert store.lease_next_action("worker-b", lease_seconds=120) is None
    assert store.get_action(blocked.action_id).status == "pending"


def test_decision_opened_after_lease_blocks_completion_transaction(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120)
    store.open_user_decision(
        scope="run",
        run_id="run-1",
        failure_key="run:late-gate",
        summary="decision opened after lease",
    )

    with pytest.raises(RuntimeError, match="open user decision"):
        store.complete_action(
            action.action_id,
            "worker-a",
            ActionResult(
                result_class=ActionResultClass.SUCCESS, summary="must not commit"
            ),
        )

    assert store.count("action_attempts") == 0
    assert store.get_action(action.action_id).status == "leased"


def test_queued_lease_computes_deadline_after_store_lock_is_acquired(tmp_path):
    clock = ObservableClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    observed = clock.observe()
    result: list[object] = []
    started = threading.Event()

    def lease() -> None:
        started.set()
        try:
            result.append(store.lease_next_action("worker-a", lease_seconds=120))
        except BaseException as exc:
            result.append(exc)

    store._lock.acquire()
    thread = threading.Thread(target=lease)
    try:
        thread.start()
        assert started.wait(timeout=1)
        observed_while_queued = observed.wait(timeout=0.2)
        clock.advance(seconds=100)
    finally:
        store._lock.release()
    thread.join(timeout=5)

    assert observed_while_queued is False
    assert not thread.is_alive()
    assert result[0].action_id == action.action_id
    assert result[0].lease_expires_at == "2026-01-01T00:03:40.000000Z"


def test_queued_renew_computes_deadline_after_store_lock_is_acquired(tmp_path):
    clock = ObservableClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120)
    observed = clock.observe()
    result: list[object] = []
    started = threading.Event()

    def renew() -> None:
        started.set()
        try:
            result.append(
                store.renew_lease(action.action_id, "worker-a", lease_seconds=120)
            )
        except BaseException as exc:
            result.append(exc)

    store._lock.acquire()
    thread = threading.Thread(target=renew)
    try:
        thread.start()
        assert started.wait(timeout=1)
        observed_while_queued = observed.wait(timeout=0.2)
        clock.advance(seconds=100)
    finally:
        store._lock.release()
    thread.join(timeout=5)

    assert observed_while_queued is False
    assert result == [True]
    assert store.get_action(action.action_id).lease_expires_at == (
        "2026-01-01T00:03:40.000000Z"
    )


def test_queued_completion_rejects_lease_that_expires_while_waiting_for_lock(
    tmp_path,
):
    clock = ObservableClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=30)
    observed = clock.observe()
    result: list[object] = []
    started = threading.Event()

    def complete() -> None:
        started.set()
        try:
            result.append(
                store.complete_action(
                    action.action_id,
                    "worker-a",
                    ActionResult(
                        result_class=ActionResultClass.SUCCESS,
                        summary="must expire",
                        finished_at="2026-01-01T00:00:10+00:00",
                    ),
                )
            )
        except BaseException as exc:
            result.append(exc)

    store._lock.acquire()
    thread = threading.Thread(target=complete)
    try:
        thread.start()
        assert started.wait(timeout=1)
        observed_while_queued = observed.wait(timeout=0.2)
        clock.advance(seconds=31)
    finally:
        store._lock.release()
    thread.join(timeout=5)

    assert observed_while_queued is False
    assert len(result) == 1
    assert isinstance(result[0], RuntimeError)
    assert "live lease" in str(result[0])
    assert store.count("action_attempts") == 0
    assert store.get_action(action.action_id).status == "leased"


def test_queued_unexpired_completion_uses_lock_time_for_finished_at_fallback(
    tmp_path,
):
    clock = ObservableClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120)
    observed = clock.observe()
    result: list[object] = []
    started = threading.Event()

    def complete() -> None:
        started.set()
        try:
            result.append(
                store.complete_action(
                    action.action_id,
                    "worker-a",
                    ActionResult(
                        result_class=ActionResultClass.SUCCESS,
                        summary="complete after queue",
                    ),
                )
            )
        except BaseException as exc:
            result.append(exc)

    store._lock.acquire()
    thread = threading.Thread(target=complete)
    try:
        thread.start()
        assert started.wait(timeout=1)
        observed_while_queued = observed.wait(timeout=0.2)
        clock.advance(seconds=10)
    finally:
        store._lock.release()
    thread.join(timeout=5)

    assert observed_while_queued is False
    assert len(result) == 1
    assert result[0].finished_at == "2026-01-01T00:00:10.000000Z"
    assert store.count("action_attempts") == 1
    assert store.get_action(action.action_id).status == "completed"


def test_worker_heartbeat_upsert_never_moves_backwards(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, 0, 1, 40, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    first = store.record_worker_heartbeat("worker-a")
    clock.value = datetime(2026, 1, 1, 0, 0, 50, tzinfo=timezone.utc)

    second = store.record_worker_heartbeat("worker-a")

    assert second["heartbeat_at"] == first["heartbeat_at"]
    assert second["updated_at"] == first["updated_at"]


def test_touch_worker_updates_one_current_row_without_appending_history(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)

    first = store.touch_worker("idle-worker")
    clock.advance(seconds=2)
    second = store.touch_worker("idle-worker")
    workers = store.fetch_all("workers")

    assert len(workers) == 1
    assert workers[0] == second
    assert second["heartbeat_at"] == "2026-01-01T00:00:02.000000Z"
    assert second["created_at"] == first["created_at"]
    assert second["updated_at"] != first["updated_at"]


def test_service_observation_preserves_missing_heartbeat_as_empty(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)

    store.upsert_service_observation(
        service_id="loop-dashboard",
        status="unhealthy",
        endpoint="http://127.0.0.1:8766/api/health",
        process_id=None,
        details={"endpoint_verified": False},
    )

    row = store.fetch_all("services")[0]
    assert row["heartbeat_at"] == ""


def test_service_restart_claim_is_atomic_and_does_not_create_worker_heartbeat(
    tmp_path,
):
    store = migrated_store(tmp_path)
    store.upsert_service_observation(
        service_id="loop-dashboard",
        status="unhealthy",
        details={"endpoint_verified": False},
    )
    outage_id = json.loads(store.fetch_all("services")[0]["details_json"])[
        "outage_id"
    ]
    request = ActionRequest(
        action_id="service-restart-loop-dashboard-outage-1",
        run_id="service-keeper",
        run_revision=0,
        policy="autonomous_knowledge",
        phase="repair_needed",
        action_type=ActionType.RESTART_SERVICE,
        idempotency_key=f"service-restart:loop-dashboard:{outage_id}",
        queue_owner=ActionOwner.SUPERVISOR,
        repo_relative_root=".",
        task_id=f"service:loop-dashboard:{outage_id}",
        next_action=ActionType.RESTART_SERVICE.value,
        payload={"service_id": "loop-dashboard", "outage_id": outage_id},
    )
    store.enqueue_action(request)

    first = store.claim_service_restart_action(
        request.action_id,
        "supervisor-a",
        service_id="loop-dashboard",
        outage_id=outage_id,
        lease_seconds=120,
    )
    second = store.claim_service_restart_action(
        request.action_id,
        "supervisor-b",
        service_id="loop-dashboard",
        outage_id=outage_id,
        lease_seconds=120,
    )

    assert first is not None
    assert second is None
    assert store.fetch_all("workers") == []


def test_service_restart_claim_cancels_action_when_current_outage_changed(tmp_path):
    store = migrated_store(tmp_path)
    store.upsert_service_observation(
        service_id="loop-dashboard",
        status="unhealthy",
        details={"endpoint_verified": False},
    )
    first_service = store.fetch_all("services")[0]
    outage_a = json.loads(first_service["details_json"])["outage_id"]
    action_a = ActionRequest(
        action_id="service-restart-loop-dashboard-outage-a",
        run_id="service-keeper",
        run_revision=0,
        policy="autonomous_knowledge",
        phase="repair_needed",
        action_type=ActionType.RESTART_SERVICE,
        idempotency_key=f"service-restart:loop-dashboard:{outage_a}",
        queue_owner=ActionOwner.SUPERVISOR,
        repo_relative_root=".",
        task_id=f"service:loop-dashboard:{outage_a}",
        next_action=ActionType.RESTART_SERVICE.value,
        payload={"service_id": "loop-dashboard", "outage_id": outage_a},
    )
    store.enqueue_action(action_a)

    store.upsert_service_observation(
        service_id="loop-dashboard",
        status="healthy",
        details={"endpoint_verified": True},
    )
    store.upsert_service_observation(
        service_id="loop-dashboard",
        status="unhealthy",
        details={"endpoint_verified": False},
    )
    current_service = store.fetch_all("services")[0]
    outage_b = json.loads(current_service["details_json"])["outage_id"]
    action_b = ActionRequest(
        action_id="service-restart-loop-dashboard-outage-b",
        run_id="service-keeper",
        run_revision=0,
        policy="autonomous_knowledge",
        phase="repair_needed",
        action_type=ActionType.RESTART_SERVICE,
        idempotency_key=f"service-restart:loop-dashboard:{outage_b}",
        queue_owner=ActionOwner.SUPERVISOR,
        repo_relative_root=".",
        task_id=f"service:loop-dashboard:{outage_b}",
        next_action=ActionType.RESTART_SERVICE.value,
        payload={"service_id": "loop-dashboard", "outage_id": outage_b},
    )
    store.enqueue_action(action_b)

    claimed = store.claim_service_restart_action(
        action_a.action_id,
        "supervisor-after-race",
        service_id="loop-dashboard",
        outage_id=outage_a,
        lease_seconds=120,
    )

    assert claimed is None
    assert store.get_action(action_a.action_id).status == "cancelled"
    assert store.get_action(action_b.action_id).status == "pending"
    assert store.fetch_all("action_attempts") == []


def test_generic_worker_lease_cannot_claim_supervisor_service_restart(tmp_path):
    store = migrated_store(tmp_path)
    request = ActionRequest(
        action_id="service-restart-loop-dashboard-outage-1",
        run_id="service-keeper",
        run_revision=0,
        policy="autonomous_knowledge",
        phase="repair_needed",
        action_type=ActionType.RESTART_SERVICE,
        idempotency_key="service-restart:loop-dashboard:outage-1",
        queue_owner=ActionOwner.SUPERVISOR,
        repo_relative_root=".",
        task_id="service:loop-dashboard",
        next_action=ActionType.RESTART_SERVICE.value,
        payload={"service_id": "loop-dashboard", "outage_id": "outage-1"},
    )
    store.enqueue_action(request)

    leased = store.lease_next_action(
        "worker-a",
        lease_seconds=120,
        allowed_action_types={ActionType.RESTART_SERVICE.value},
        allowed_queue_owners={ActionOwner.SUPERVISOR.value},
    )

    assert leased is None
    assert store.get_action(request.action_id).status == "pending"


def test_same_worker_cannot_reclaim_expired_lease_while_its_heartbeat_is_fresh(
    tmp_path,
):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=30, heartbeat_stale_seconds=60)

    clock.advance(seconds=31)
    assert (
        store.lease_next_action(
            "worker-a", lease_seconds=30, heartbeat_stale_seconds=60
        )
        is None
    )
    clock.advance(seconds=61)
    assert (
        store.lease_next_action(
            "worker-a", lease_seconds=30, heartbeat_stale_seconds=60
        ).action_id
        == action.action_id
    )

    clock.advance(seconds=121)

    assert (
        store.lease_next_action(
            "worker-b", lease_seconds=120, heartbeat_stale_seconds=60
        ).action_id
        == action.action_id
    )
    assert (
        store.lease_next_action(
            "worker-c", lease_seconds=120, heartbeat_stale_seconds=60
        )
        is None
    )


def test_live_worker_heartbeat_prevents_reclaim_after_action_deadline(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=30, heartbeat_stale_seconds=60)

    clock.advance(seconds=31)
    store.record_worker_heartbeat("worker-a")

    assert (
        store.lease_next_action(
            "worker-b", lease_seconds=30, heartbeat_stale_seconds=60
        )
        is None
    )
    clock.advance(seconds=61)
    assert (
        store.lease_next_action(
            "worker-b", lease_seconds=30, heartbeat_stale_seconds=60
        ).action_id
        == action.action_id
    )


def test_complete_action_records_attempt_and_status_in_one_transaction(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)

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
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
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


def test_complete_action_rolls_back_forged_skill_invocation_with_attempt(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    artifact = tmp_path / ".codex" / "loop-runs" / "run-1" / "planner-result.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"status":"pass"}\n', encoding="utf-8")
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: alpha\n---\n", encoding="utf-8")
    artifact_ref = artifact.relative_to(tmp_path).as_posix()
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)

    with pytest.raises(ValueError, match="hash does not match"):
        store.complete_action(
            action.action_id,
            "worker-a",
            ActionResult(
                result_class=ActionResultClass.SUCCESS,
                summary="forged invocation",
                artifact_paths=(artifact_ref,),
                skill_invocations=(
                    SkillInvocationEvidence(
                        invocation_id="invocation-forged",
                        skill_path="skills/alpha/SKILL.md",
                        artifact_path=artifact_ref,
                        artifact_sha256=f"sha256:{'0' * 64}",
                    ),
                ),
            ),
        )

    assert store.count("action_attempts") == 0
    assert store.count("skill_invocations") == 0
    assert store.get_action(action.action_id).status == "leased"


def test_complete_action_rejects_lease_after_run_revision_advances(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=4)
    action = store.enqueue_action(action_request("run-1", revision=4))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
    project_run(store, "run-1", revision=5, phase="generating")

    with pytest.raises(RuntimeError, match="current run revision"):
        store.complete_action(
            action.action_id,
            "worker-a",
            ActionResult(result_class=ActionResultClass.SUCCESS, summary="stale"),
        )

    assert store.count("action_attempts") == 0
    assert store.get_action(action.action_id).status == "leased"


def test_complete_action_rejects_current_revision_with_wrong_run_phase(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=4)
    action = store.enqueue_action(action_request("run-1", revision=4))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
    store._connection.execute(
        "UPDATE runs SET phase = 'generating' WHERE run_id = 'run-1'"
    )

    with pytest.raises(RuntimeError, match="current run revision and phase"):
        store.complete_action(
            action.action_id,
            "worker-a",
            ActionResult(result_class=ActionResultClass.SUCCESS, summary="stale"),
        )

    assert store.count("action_attempts") == 0


def test_pending_action_for_current_revision_but_wrong_phase_is_never_leased(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=4, phase="generating")
    store.enqueue_action(action_request("run-1", revision=4, phase="planning"))

    assert (
        store.lease_next_action(
            "worker-a", lease_seconds=120, heartbeat_stale_seconds=60
        )
        is None
    )


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


def test_run_projection_rejects_stale_revision_without_overwriting_current(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=5)

    with pytest.raises(ValueError, match="stale"):
        project_run(store, "run-1", revision=4)

    assert store.get_run("run-1")["revision"] == 5
    assert store.count("transitions") == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("policy", "demand_development"),
        ("phase", "generating"),
        ("status", "blocked"),
        ("summary", "changed summary"),
        ("loop_lineage_id", "lineage-2"),
        ("parent_run_id", "parent-2"),
        ("artifact_refs", ["artifacts/other.json"]),
    ],
)
def test_same_revision_projection_rejects_any_non_observation_change(
    tmp_path, field, value
):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    original_projection = {
        "run_id": "run-1",
        "revision": 5,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "status": "running",
        "summary": "stable summary",
        "loop_lineage_id": "lineage-1",
        "parent_run_id": "parent-1",
        "artifact_refs": ["artifacts/run.json"],
    }
    store.upsert_run_projection(original_projection)
    original = store.get_run("run-1")
    changed = dict(original_projection)
    changed[field] = value
    clock.advance(seconds=30)

    with pytest.raises(ValueError, match="same-revision run projection conflict"):
        store.upsert_run_projection(changed)

    assert store.get_run("run-1") == original


def test_same_revision_projection_rejects_state_fingerprint_change(tmp_path):
    store = migrated_store(tmp_path)
    projection = {
        "run_id": "run-1",
        "revision": 5,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "state_fingerprint": "sha256:first",
    }
    store.upsert_run_projection(projection)

    with pytest.raises(ValueError, match="same-revision run projection conflict"):
        store.upsert_run_projection(
            {**projection, "state_fingerprint": "sha256:changed"}
        )

    store.upsert_run_projection(
        {
            **projection,
            "revision": 6,
            "phase": "generating",
            "state_fingerprint": "sha256:changed",
        }
    )
    assert store.get_run("run-1")["state_fingerprint"] == "sha256:changed"


def test_identical_same_revision_projection_updates_only_last_seen(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    projection = {
        "run_id": "run-1",
        "revision": 5,
        "policy": "autonomous_knowledge",
        "phase": "planning",
        "status": "running",
        "summary": "stable summary",
        "loop_lineage_id": "lineage-1",
        "parent_run_id": "parent-1",
        "artifact_refs": ["artifacts/run.json"],
    }
    store.upsert_run_projection(projection)
    original = store.get_run("run-1")
    clock.advance(seconds=30)

    refreshed = store.upsert_run_projection(projection)

    assert refreshed["last_seen_at"] > original["last_seen_at"]
    assert {
        key: value for key, value in refreshed.items() if key != "last_seen_at"
    } == {key: value for key, value in original.items() if key != "last_seen_at"}


def test_pending_action_for_old_run_revision_is_never_leased(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=4)
    old = store.enqueue_action(action_request("run-1", revision=4))
    project_run(store, "run-1", revision=5, phase="generating")

    assert store.get_action(old.action_id).status == "cancelled"
    assert (
        store.lease_next_action(
            "worker-a", lease_seconds=120, heartbeat_stale_seconds=60
        )
        is None
    )


def test_run_revision_advance_does_not_cancel_leased_action(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=4)
    action = store.enqueue_action(action_request("run-1", revision=4))
    leased = store.lease_next_action(
        "worker-a", lease_seconds=120, heartbeat_stale_seconds=60
    )
    assert leased is not None

    project_run(store, "run-1", revision=5, phase="generating")

    assert store.get_action(action.action_id).status == "leased"


@pytest.mark.parametrize("leased_status", ["leased", "running"])
def test_revision_advance_fences_leased_recovery_reviewer(
    tmp_path, leased_status
):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=4)
    request = ActionRequest(
        action_id=f"recovery-reviewer-{leased_status}",
        run_id="run-1",
        run_revision=4,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_REVIEWER,
        idempotency_key=f"recovery:reviewer-{leased_status}",
        queue_owner=ActionOwner.REVIEWER,
    )
    store.enqueue_action(request)
    leased = store.lease_next_action(
        "reviewer-a",
        lease_seconds=120,
        heartbeat_stale_seconds=60,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
        allowed_queue_owners={ActionOwner.REVIEWER.value},
    )
    assert leased is not None and leased.action_id == request.action_id
    if leased_status == "running":
        store._connection.execute(
            "UPDATE actions SET status = 'running' WHERE action_id = ?",
            (request.action_id,),
        )
        store._connection.commit()

    project_run(store, "run-1", revision=5, phase="generating")

    assert store.get_action(request.action_id).status == "cancelled"
    assert store.renew_lease(request.action_id, "reviewer-a", lease_seconds=120) is False
    with pytest.raises(LeaseError, match="live lease"):
        store.complete_action(
            request.action_id,
            "reviewer-a",
            ActionResult(result_class=ActionResultClass.SUCCESS, summary="obsolete"),
        )
    assert not any(
        row["action_id"] == request.action_id
        for row in store.fetch_all("action_attempts")
    )


def test_revision_advance_does_not_fence_leased_cadence_reviewer(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=4)
    request = ActionRequest(
        action_id="cadence-reviewer",
        run_id="run-1",
        run_revision=4,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_REVIEWER,
        idempotency_key="review:cadence",
        queue_owner=ActionOwner.REVIEWER,
    )
    store.enqueue_action(request)
    leased = store.lease_next_action(
        "reviewer-cadence",
        lease_seconds=120,
        heartbeat_stale_seconds=60,
        allowed_action_types={ActionType.RUN_REVIEWER.value},
        allowed_queue_owners={ActionOwner.REVIEWER.value},
    )
    assert leased is not None and leased.action_id == request.action_id

    project_run(store, "run-1", revision=5, phase="generating")

    assert store.get_action(request.action_id).status == "leased"
    assert store.renew_lease(
        request.action_id, "reviewer-cadence", lease_seconds=120
    )
    attempt = store.complete_action(
        request.action_id,
        "reviewer-cadence",
        ActionResult(result_class=ActionResultClass.SUCCESS, summary="cadence complete"),
    )
    assert attempt.action_id == request.action_id
    assert store.get_action(request.action_id).status == "completed"


def test_completed_action_reopens_when_run_has_not_advanced_and_preserves_evidence(
    tmp_path,
):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1, state_fingerprint="fingerprint-1")
    request = action_request(
        "run-1", revision=1, payload={"input_ref": "artifacts/planner-input.json"}
    )
    action = store.enqueue_action(request, artifact_paths=("artifacts/request.json",))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="done",
            artifact_paths=("artifacts/planner-result.json",),
        ),
    )

    with acquire_run_lock(
        tmp_path, "run-1", owner="test:reopen", blocking=True
    ) as token:
        reopened = store.enqueue_action(
            action_request("run-1", revision=1),
            expected_run_fingerprint="fingerprint-1",
            run_lock_token=token,
        )

    assert reopened.status == "pending"
    assert reopened.payload == {"input_ref": "artifacts/planner-input.json"}
    assert reopened.artifacts == ["artifacts/planner-result.json"]


def test_completed_action_does_not_reopen_without_locked_snapshot(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1, state_fingerprint="fingerprint-1")
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(result_class=ActionResultClass.SUCCESS, summary="done"),
    )

    duplicate = store.enqueue_action(action_request("run-1", revision=1))

    assert duplicate.status == "completed"


def test_completed_action_reopen_rejects_incoming_identity_impersonation(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    request = action_request("run-1", revision=1, idempotency_key="stable-external-key")
    action = store.enqueue_action(request)
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(result_class=ActionResultClass.SUCCESS, summary="done"),
    )

    with pytest.raises(ValueError, match="idempotency identity conflict"):
        store.enqueue_action(
            action_request(
                "run-1",
                revision=1,
                action_id="action-2",
                phase="generating",
                idempotency_key="stable-external-key",
            )
        )

    stored = store.get_action(action.action_id)
    assert stored.status == "completed"
    assert stored.phase == "planning"


def test_completed_action_does_not_reopen_after_run_advances(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(result_class=ActionResultClass.SUCCESS, summary="done"),
    )
    project_run(store, "run-1", revision=2, phase="generating")

    duplicate = store.enqueue_action(action_request("run-1", revision=1))

    assert duplicate.status == "completed"


def test_identical_open_user_decision_replay_does_not_write(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    first = store.open_user_decision(
        scope="run",
        run_id="run-1",
        failure_key="permission:push",
        summary="approval needed",
        required_decision="approve push",
    )

    clock.advance(seconds=30)
    identical = store.open_user_decision(
        scope="run",
        run_id="run-1",
        failure_key="permission:push",
        summary="approval needed",
        required_decision="approve push",
    )
    assert identical["updated_at"] == first["updated_at"]

    clock.advance(seconds=30)
    changed = store.open_user_decision(
        scope="run",
        run_id="run-1",
        failure_key="permission:push",
        summary="approval still needed",
        required_decision="approve push",
    )
    assert changed["updated_at"] > identical["updated_at"]
    assert store.count("user_decisions") == 1


def test_close_user_decision_compare_and_swap_preserves_newer_open_update(tmp_path):
    clock = FakeClock()
    store = migrated_store(tmp_path, clock=clock)
    observed = store.open_user_decision(
        scope="global",
        failure_key="secret:global",
        summary="initial observation",
    )
    clock.advance(seconds=1)
    newer = store.open_user_decision(
        scope="global",
        failure_key="secret:global",
        summary="newer observation",
    )

    closed = store.close_user_decision(
        observed["decision_id"],
        resolution="stale close",
        expected_updated_at=observed["updated_at"],
    )

    assert closed is None
    current = store.fetch_all("user_decisions")[0]
    assert current["status"] == "open"
    assert current["summary"] == newer["summary"]


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


def test_external_iso_timestamps_normalize_to_fixed_utc_and_sort_correctly(tmp_path):
    store = migrated_store(tmp_path)
    first = store.record_transition(
        run_id="run-1",
        from_revision=0,
        to_revision=1,
        created_at="2026-01-01T01:00:00+01:00",
    )
    second = store.record_transition(
        run_id="run-2",
        from_revision=0,
        to_revision=1,
        created_at="2026-01-01T00:00:00.5Z",
    )

    assert first["created_at"] == "2026-01-01T00:00:00.000000Z"
    assert second["created_at"] == "2026-01-01T00:00:00.500000Z"
    page = store.list_page("transitions", resource="/api/transitions", page_size=20)
    assert [item["run_id"] for item in page["items"]] == ["run-2", "run-1"]


@pytest.mark.parametrize(
    "timestamp",
    ["not-a-timestamp", "2026-01-01", "2026-01-01T00:00:00"],
)
def test_external_timestamp_rejects_invalid_or_timezone_naive_strings(
    tmp_path, timestamp
):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="timestamp"):
        store.record_transition(
            run_id="run-1",
            from_revision=0,
            to_revision=1,
            created_at=timestamp,
        )


def test_action_result_times_normalize_to_fixed_utc(tmp_path):
    store = migrated_store(tmp_path)
    project_run(store, "run-1", revision=1)
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)

    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="done",
            started_at="2026-01-01T08:00:00+08:00",
            finished_at="2026-01-01T00:00:01.5Z",
        ),
    )

    attempt = store.fetch_all("action_attempts")[0]
    assert attempt["started_at"] == "2026-01-01T00:00:00.000000Z"
    assert attempt["finished_at"] == "2026-01-01T00:00:01.500000Z"


@pytest.mark.parametrize("page_size", [20, 50, 100])
def test_list_page_accepts_documented_page_sizes(tmp_path, page_size):
    store = migrated_store(tmp_path)
    _seed_transitions(store, page_size + 1)

    page = store.list_page(
        "transitions", resource="/api/transitions", page_size=page_size
    )

    assert len(page["items"]) == page_size
    assert page["page_size"] == page_size
    assert page["has_more"] is True
    assert page["next_cursor"]


def test_list_page_rejects_unsupported_page_size(tmp_path):
    store = migrated_store(tmp_path)

    with pytest.raises(ValueError, match="page_size"):
        store.list_page("transitions", resource="/api/transitions", page_size=25)


def test_cursor_rejects_tampering_and_filter_mismatch(tmp_path):
    store = migrated_store(tmp_path)
    _seed_transitions(store, 21)
    page = store.list_page(
        "transitions",
        resource="/api/transitions",
        page_size=20,
        filters={"run_id": "run-1"},
    )
    envelope = json.loads(base64.urlsafe_b64decode(page["next_cursor"] + "=="))
    envelope["payload"]["boundary"]["primary_key"] = "transition-tampered"
    tampered = (
        base64.urlsafe_b64encode(
            json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode()
        )
        .decode()
        .rstrip("=")
    )

    with pytest.raises(CursorError, match="cursor"):
        store.list_page(
            "transitions",
            resource="/api/transitions",
            page_size=20,
            cursor=tampered,
            filters={"run_id": "run-1"},
        )
    with pytest.raises(CursorError, match="filter"):
        store.list_page(
            "transitions",
            resource="/api/transitions",
            page_size=20,
            cursor=page["next_cursor"],
            filters={"run_id": "run-2"},
        )
    with pytest.raises(CursorError, match="resource"):
        store.list_page(
            "transitions",
            resource="/api/runs/run-1/transitions",
            page_size=20,
            cursor=page["next_cursor"],
            filters={"run_id": "run-1"},
        )

    payload = json.loads(base64.urlsafe_b64decode(page["next_cursor"] + "=="))[
        "payload"
    ]
    assert payload["resource"] == "/api/transitions"
    assert (
        payload["snapshot"]["sort_timestamp"],
        payload["snapshot"]["primary_key"],
    ) >= (
        payload["boundary"]["sort_timestamp"],
        payload["boundary"]["primary_key"],
    )
    assert payload["filter_fingerprint"]
    assert isinstance(payload["snapshot_sequence"], int)
    assert payload["snapshot_total"] == 21


def test_cursor_boundary_is_stable_when_newer_row_is_inserted(tmp_path):
    store = migrated_store(tmp_path)
    _seed_transitions(store, 25)
    first = store.list_page("transitions", resource="/api/transitions", page_size=20)
    first_ids = {item["transition_id"] for item in first["items"]}

    store.record_transition(
        run_id="new-run",
        from_revision=0,
        to_revision=1,
        from_phase="planning",
        to_phase="generating",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    store.record_transition(
        run_id="backdated-run",
        from_revision=0,
        to_revision=1,
        from_phase="planning",
        to_phase="generating",
        created_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    second = store.list_page(
        "transitions",
        resource="/api/transitions",
        page_size=20,
        cursor=first["next_cursor"],
    )
    second_ids = {item["transition_id"] for item in second["items"]}

    assert len(second["items"]) == 5
    assert first_ids.isdisjoint(second_ids)
    assert all(item["run_id"] != "new-run" for item in second["items"])
    assert all(item["run_id"] != "backdated-run" for item in second["items"])
    assert second["previous_cursor"]
    assert first["total"] == second["total"] == 25

    previous = store.list_page(
        "transitions",
        resource="/api/transitions",
        page_size=20,
        cursor=second["previous_cursor"],
    )
    assert previous["total"] == 25
    assert {item["transition_id"] for item in previous["items"]} == first_ids
    assert all(item["run_id"] != "new-run" for item in previous["items"])
    assert all(item["run_id"] != "backdated-run" for item in previous["items"])


def test_cursor_sequence_does_not_reuse_deleted_max_membership(tmp_path):
    store = migrated_store(tmp_path)
    _seed_transitions(store, 25)
    first = store.list_page("transitions", resource="/api/transitions", page_size=20)
    deleted = store._connection.execute(
        "SELECT transition_id FROM transitions ORDER BY rowid DESC LIMIT 1"
    ).fetchone()[0]
    store._connection.execute(
        "DELETE FROM transitions WHERE transition_id = ?", (deleted,)
    )
    store.record_transition(
        run_id="backdated-after-delete",
        from_revision=0,
        to_revision=1,
        from_phase="planning",
        to_phase="generating",
        created_at=datetime(2025, 12, 30, tzinfo=timezone.utc),
    )

    second = store.list_page(
        "transitions",
        resource="/api/transitions",
        page_size=20,
        cursor=first["next_cursor"],
    )

    assert len(second["items"]) == 5
    assert second["total"] == 25
    assert all(item["run_id"] != "backdated-after-delete" for item in second["items"])
    previous = store.list_page(
        "transitions",
        resource="/api/transitions",
        page_size=20,
        cursor=second["previous_cursor"],
    )
    assert previous["total"] == 25
    assert all(item["run_id"] != "backdated-after-delete" for item in previous["items"])


def test_retention_aggregates_rows_older_than_90_days_before_deleting(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    old_action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
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

    assert result == {
        "action_attempts": 1,
        "review_findings": 0,
        "reviews": 1,
        "transitions": 1,
    }
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


def test_retention_compacts_freshness_history_but_keeps_latest_per_target(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    for target in ("wiki", "search", "dashboard"):
        for index, status in enumerate(("stale", "fresh", "stale"), start=1):
            store.record_freshness_observation(
                target=target,
                status=status,
                summary=f"{target}-{index}",
            )
            clock.advance(seconds=1)
    clock.advance(days=91)

    result = store.compact_retention(retention_days=90)

    assert result["freshness_checks"] == 6
    remaining = store.fetch_all("freshness_checks")
    assert len(remaining) == 3
    assert {row["target"] for row in remaining} == {"wiki", "search", "dashboard"}
    assert {row["summary"] for row in remaining} == {
        "wiki-3",
        "search-3",
        "dashboard-3",
    }
    assert sum(
        row["count"]
        for row in store.fetch_all("aggregates")
        if row["aggregate_kind"] == "freshness_checks"
    ) == 6


def test_retention_aggregates_and_deletes_skill_invocations_before_attempts(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    artifact = tmp_path / ".codex" / "loop-runs" / "run-1" / "planner-result.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"status":"pass"}\n', encoding="utf-8")
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: alpha\n---\n", encoding="utf-8")
    artifact_ref = artifact.relative_to(tmp_path).as_posix()
    artifact_hash = f"sha256:{hashlib.sha256(artifact.read_bytes()).hexdigest()}"
    action = store.enqueue_action(action_request("run-1", revision=1))
    store.lease_next_action("worker-a", lease_seconds=120, heartbeat_stale_seconds=60)
    store.complete_action(
        action.action_id,
        "worker-a",
        ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="skill-backed success",
            artifact_paths=(artifact_ref,),
            skill_invocations=(
                SkillInvocationEvidence(
                    invocation_id="invocation-retention",
                    skill_path="skills/alpha/SKILL.md",
                    artifact_path=artifact_ref,
                    artifact_sha256=artifact_hash,
                ),
            ),
        ),
    )
    clock.advance(days=91)

    store.compact_retention(retention_days=90)

    assert store.count("skill_invocations") == 0
    assert store.count("action_attempts") == 0
    assert sum(
        row["count"]
        for row in store.fetch_all("aggregates")
        if row["aggregate_kind"] == "skill_invocations"
        and row["aggregate_key"] == "skills/alpha/SKILL.md"
    ) == 1


def test_retention_preserves_incomplete_review_application_and_applied_attempt(
    tmp_path,
):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    requests = []
    targets = []
    for run_id in ("run-1", "run-2"):
        project_run(store, run_id, revision=1)
        request = ActionRequest(
            action_id=f"review-action-{run_id}",
            run_id=run_id,
            run_revision=1,
            policy="autonomous_knowledge",
            phase="planning",
            action_type=ActionType.REFOCUS_RUN,
            idempotency_key=f"review-action-{run_id}",
            queue_owner=ActionOwner.SUPERVISOR,
        )
        requests.append(request)
        targets.append(
            (
                request,
                {
                    "expected_revision": 1,
                    "expected_fingerprint": f"fingerprint-{run_id}",
                    "source_phase": "planning",
                    "target_phase": "planning",
                    "target_next_action": "run_autonomous_planner",
                    "target_last_result": "none",
                },
            )
        )
    store.record_review(
        review_id="review-incomplete-retention",
        trigger="cadence",
        status="review_applying",
        decision="refocus",
        summary="application in progress",
    )
    store.prepare_review_application(
        review_id="review-incomplete-retention",
        decision="refocus",
        targets=targets,
    )
    owner = "supervisor-review-application-retention"
    claimed = store.claim_pending_action(
        requests[0].action_id,
        owner,
        lease_seconds=120,
        expected_queue_owner=ActionOwner.SUPERVISOR,
    )
    assert claimed is not None
    store.complete_review_application_target(
        review_id="review-incomplete-retention",
        run_id=requests[0].run_id,
        action_id=requests[0].action_id,
        owner_id=owner,
        result=ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="first target applied",
        ),
        applied_revision=2,
    )
    clock.advance(days=91)

    result = store.compact_retention(retention_days=90)

    assert result["reviews"] == 0
    assert store.count("reviews") == 1
    assert store.count("review_applications") == 1
    assert store.count("review_application_targets") == 2
    assert store.count("actions") == 2
    assert store.count("action_attempts") == 1
    assert store.fetch_all("review_applications")[0]["status"] == "applying"


def test_retention_compacts_superseded_review_application(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    target = ActionRequest(
        action_id="review-target-superseded-retention",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.REFOCUS_RUN,
        idempotency_key="review-target-superseded-retention",
        queue_owner=ActionOwner.SUPERVISOR,
    )
    store.record_review(
        review_id="review-superseded-retention",
        trigger="cadence",
        status="review_applying",
        decision="refocus",
        summary="stale target",
    )
    store.prepare_review_application(
        review_id="review-superseded-retention",
        decision="refocus",
        targets=[
            (
                target,
                {
                    "expected_revision": 1,
                    "expected_fingerprint": f"sha256:{'a' * 64}",
                    "source_phase": "planning",
                    "target_phase": "planning",
                    "target_next_action": "run_autonomous_planner",
                    "target_last_result": "none",
                },
            )
        ],
    )
    store.supersede_review_application(
        "review-superseded-retention",
        reason="target advanced before application",
    )
    clock.advance(days=91)

    result = store.compact_retention(retention_days=90)

    assert result["reviews"] == 1
    assert store.count("reviews") == 0
    assert store.count("review_applications") == 0
    assert store.count("review_application_targets") == 0


def test_retention_preserves_completed_review_while_source_action_is_nonterminal(
    tmp_path,
):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    project_run(store, "run-1", revision=1)
    source = ActionRequest(
        action_id="reviewer-source-retention",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.RUN_REVIEWER,
        idempotency_key="reviewer-source-retention",
        queue_owner=ActionOwner.REVIEWER,
    )
    store.enqueue_action(source)
    target = ActionRequest(
        action_id="review-target-retention",
        run_id="run-1",
        run_revision=1,
        policy="autonomous_knowledge",
        phase="planning",
        action_type=ActionType.REFOCUS_RUN,
        idempotency_key="review-target-retention",
        queue_owner=ActionOwner.SUPERVISOR,
    )
    store.record_review(
        review_id="review-source-retention",
        trigger="cadence",
        status="review_applying",
        decision="refocus",
        summary="outbox applying",
        source_action_id=source.action_id,
    )
    store.prepare_review_application(
        review_id="review-source-retention",
        decision="refocus",
        targets=[
            (
                target,
                {
                    "expected_revision": 1,
                    "expected_fingerprint": f"sha256:{'a' * 64}",
                    "source_phase": "planning",
                    "target_phase": "planning",
                    "target_next_action": "run_autonomous_planner",
                    "target_last_result": "none",
                },
            )
        ],
    )
    owner = "supervisor-review-application-retention-source"
    assert store.claim_pending_action(
        target.action_id,
        owner,
        lease_seconds=120,
        expected_queue_owner=ActionOwner.SUPERVISOR,
    ) is not None
    store.complete_review_application_target(
        review_id="review-source-retention",
        run_id="run-1",
        action_id=target.action_id,
        owner_id=owner,
        result=ActionResult(
            result_class=ActionResultClass.SUCCESS,
            summary="outbox target complete",
        ),
        applied_revision=2,
    )
    assert store.fetch_all("review_applications")[0]["status"] == "completed"
    assert store.fetch_all("reviews")[0]["status"] == "review_complete"
    assert store.get_action(source.action_id).status == "pending"
    clock.advance(days=91)

    result = store.compact_retention(retention_days=90)

    assert result["reviews"] == 0
    assert store.count("reviews") == 1
    assert store.count("review_applications") == 1
    assert store.count("review_application_targets") == 1


def test_retention_preserves_reviews_with_active_findings_and_compacts_terminal_ones(
    tmp_path,
):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    active_statuses = {"open"}
    terminal_statuses = {"closed", "accepted_risk"}
    for status in sorted(active_statuses | terminal_statuses):
        finding_id = f"finding-{status}"
        store.record_review(
            review_id=f"review-{status}",
            trigger="cadence",
            status="completed",
            decision="continue",
            summary=f"review {status}",
            findings=(
                {
                    "finding_id": finding_id,
                    "finding_key": f"key-{status}",
                    "status": "open",
                    "summary": "finding open",
                    "evidence_refs": [f"sha256:{'a' * 64}"],
                },
            ),
        )
        if status in terminal_statuses:
            store.record_review(
                review_id=f"review-{status}",
                trigger="cadence",
                status="completed",
                decision="continue",
                summary=f"review {status}",
                findings=(
                    {
                        "finding_id": finding_id,
                        "finding_key": f"key-{status}",
                        "status": status,
                        "summary": f"finding {status}",
                        "closure_evidence_refs": (
                            [f"sha256:{'b' * 64}"] if status == "closed" else []
                        ),
                    },
                ),
            )
    clock.advance(days=91)

    result = store.compact_retention(retention_days=90)

    assert result["reviews"] == 2
    assert result["review_findings"] == 2
    assert {row["review_id"] for row in store.fetch_all("reviews")} == {
        f"review-{status}" for status in active_statuses
    }
    assert {
        row["status"] for row in store.fetch_all("review_findings")
    } == active_statuses
    aggregates = store.fetch_all("aggregates")
    assert (
        sum(
            row["count"]
            for row in aggregates
            if row["aggregate_kind"] == "review_findings"
        )
        == 4
    )


def test_retention_preserves_recent_terminal_finding_and_its_old_review(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    store.record_review(
        review_id="review-with-recent-finding",
        trigger="cadence",
        status="completed",
        decision="continue",
        summary="initial review",
        findings=(
            {
                "finding_id": "finding-recent",
                "finding_key": "key-recent",
                "status": "open",
                "summary": "risk under review",
            },
        ),
    )
    clock.advance(days=90)
    store.record_review(
        review_id="review-with-recent-finding",
        trigger="cadence",
        status="completed",
        decision="continue",
        summary="risk accepted",
        findings=(
            {
                "finding_id": "finding-recent",
                "finding_key": "key-recent",
                "status": "accepted_risk",
                "summary": "recent decision evidence",
            },
        ),
    )
    clock.advance(days=2)

    result = store.compact_retention(retention_days=90)

    assert result["reviews"] == 0
    assert result["review_findings"] == 0
    assert store.count("reviews") == 1
    assert store.count("review_findings") == 1


def test_review_finding_status_transitions_update_one_stable_row(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    for index, status in enumerate(("open", "open", "closed"), start=1):
        store.record_review(
            review_id="review-lifecycle",
            trigger="cadence",
            status="completed",
            decision="continue",
            summary="finding lifecycle",
            findings=(
                {
                    "finding_id": "finding-version-1",
                    "finding_key": "stable-finding-key",
                    "status": status,
                    "summary": f"finding is {status}",
                    "evidence_refs": [f"sha256:{'a' * 64}"],
                    "closure_evidence_refs": (
                        [f"sha256:{'b' * 64}"] if status == "closed" else []
                    ),
                },
            ),
        )
        clock.advance(seconds=10)

    findings = store.fetch_all("review_findings")
    assert len(findings) == 1
    assert findings[0]["finding_id"] == "finding-version-1"
    assert findings[0]["finding_key"] == "stable-finding-key"
    assert findings[0]["status"] == "closed"
    assert findings[0]["occurrence_count"] == 3
    assert findings[0]["first_seen_at"] == "2026-01-01T00:00:00.000000Z"
    assert findings[0]["last_seen_at"] == "2026-01-01T00:00:20.000000Z"


def test_retention_aggregates_finding_occurrence_count_not_row_count(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    for status in ("open", "open", "closed"):
        store.record_review(
            review_id="review-occurrences",
            trigger="cadence",
            status="completed",
            decision="continue",
            summary="finding occurrences",
            findings=(
                {
                    "finding_id": "finding-repeated",
                    "finding_key": "repeated-finding",
                    "status": status,
                    "summary": status,
                    "evidence_refs": [f"sha256:{'a' * 64}"],
                    "closure_evidence_refs": (
                        [f"sha256:{'b' * 64}"] if status == "closed" else []
                    ),
                },
            ),
        )
        clock.advance(seconds=1)
    clock.advance(days=91)

    store.compact_retention(retention_days=90)

    aggregates = store.fetch_all("aggregates")
    assert (
        sum(
            row["count"]
            for row in aggregates
            if row["aggregate_kind"] == "review_findings"
            and row["aggregate_key"] == "closed"
        )
        == 3
    )


def test_retention_uses_finding_last_seen_for_recent_terminal_transition(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    store = migrated_store(tmp_path, clock=clock)
    store.record_review(
        review_id="review-recent-lifecycle",
        trigger="cadence",
        status="completed",
        decision="continue",
        summary="open finding",
        findings=(
            {
                "finding_id": "finding-recent-lifecycle",
                "finding_key": "recent-lifecycle",
                "status": "open",
                "summary": "open",
            },
        ),
    )
    clock.advance(days=91)
    store.record_review(
        review_id="review-recent-lifecycle",
        trigger="cadence",
        status="completed",
        decision="continue",
        summary="closed today",
        findings=(
            {
                "finding_id": "finding-recent-lifecycle",
                "finding_key": "recent-lifecycle",
                "status": "closed",
                "summary": "closed",
                "closure_evidence_refs": [f"sha256:{'b' * 64}"],
            },
        ),
    )
    clock.advance(days=2)

    result = store.compact_retention(retention_days=90)

    assert result["review_findings"] == 0
    assert result["reviews"] == 0
    assert store.count("review_findings") == 1
    assert store.count("reviews") == 1


def test_migrate_v3_collapses_duplicate_finding_status_rows_by_finding_key(tmp_path):
    store = migrated_store(tmp_path)
    store.record_review(
        review_id="review-migration",
        trigger="cadence",
        status="completed",
        decision="continue",
        summary="migration fixture",
    )
    store._connection.execute("DROP TABLE review_findings")
    store._connection.execute(
        """
        CREATE TABLE review_findings (
          finding_id TEXT PRIMARY KEY,
          review_id TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
          finding_key TEXT NOT NULL,
          status TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          remediation_action_id TEXT NOT NULL DEFAULT '',
          occurrence_count INTEGER NOT NULL DEFAULT 1,
          first_seen_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(finding_key, status)
        )
        """
    )
    store._connection.executemany(
        """
        INSERT INTO review_findings(
          finding_id, review_id, finding_key, status, summary, occurrence_count,
          first_seen_at, last_seen_at, created_at, updated_at
        ) VALUES (?, 'review-migration', 'stable-key', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                "finding-open",
                "open",
                "old",
                2,
                "2026-01-01T00:00:00.000000Z",
                "2026-01-02T00:00:00.000000Z",
                "2026-01-01T00:00:00.000000Z",
                "2026-01-02T00:00:00.000000Z",
            ),
            (
                "finding-closed",
                "closed",
                "latest",
                1,
                "2026-01-01T00:00:00.000000Z",
                "2026-01-03T00:00:00.000000Z",
                "2026-01-03T00:00:00.000000Z",
                "2026-01-03T00:00:00.000000Z",
            ),
        ),
    )
    store._connection.execute("PRAGMA user_version=3")

    store.migrate()

    findings = store.fetch_all("review_findings")
    assert len(findings) == 1
    assert findings[0]["finding_id"] == "finding-closed"
    assert findings[0]["status"] == "closed"
    assert findings[0]["summary"] == "latest"
    assert findings[0]["occurrence_count"] == 3
    assert findings[0]["first_seen_at"] == "2026-01-01T00:00:00.000000Z"
    assert store.pragma("user_version") == 15


@pytest.mark.parametrize("legacy_version", [3, 4, 5])
def test_legacy_migration_normalizes_timestamps_before_finding_collapse(
    tmp_path, legacy_version
):
    store = legacy_finding_store(tmp_path, version=legacy_version)

    store.migrate()

    findings = store.fetch_all("review_findings")
    assert len(findings) == 1
    assert findings[0]["finding_id"] == "finding-closed"
    assert findings[0]["summary"] == "utc-latest"
    assert findings[0]["occurrence_count"] == 3
    assert findings[0]["first_seen_at"] == "2025-12-31T22:00:00.000000Z"
    assert findings[0]["last_seen_at"] == "2025-12-31T23:45:00.000000Z"
    review = store.fetch_all("reviews")[0]
    assert review["created_at"] == "2025-12-31T21:00:00.000000Z"
    policy = store._connection.execute(
        "SELECT value FROM store_metadata WHERE key = 'legacy_naive_timestamp_policy'"
    ).fetchone()[0]
    assert policy == "assume_utc"
    assert store.pragma("user_version") == 15


def test_invalid_legacy_timestamp_rolls_back_schema_version_and_data(tmp_path):
    store = legacy_finding_store(tmp_path, version=5, invalid_timestamp=True)
    original_tables = store.table_names()
    original_rows = store.fetch_all("review_findings")
    original_schema = store._connection.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'review_findings'"
    ).fetchone()[0]

    with pytest.raises(ValueError, match="legacy timestamp.*review_findings"):
        store.migrate()

    assert store.pragma("user_version") == 5
    assert store.table_names() == original_tables
    assert store.fetch_all("review_findings") == original_rows
    current_schema = store._connection.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'review_findings'"
    ).fetchone()[0]
    assert current_schema == original_schema


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
