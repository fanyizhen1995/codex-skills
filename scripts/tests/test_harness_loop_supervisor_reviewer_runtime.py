from __future__ import annotations

from datetime import datetime, timezone
import time

import pytest

from scripts.loop_supervisor.models import ActionOwner, ActionRequest, ActionType
from scripts.loop_supervisor.reviewer_runtime import ActionLeaseGuard
from scripts.loop_supervisor.store import LeaseError, SupervisorStore


NOW = datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)


def leased_supervisor_action(tmp_path):
    store = SupervisorStore.open(tmp_path)
    store.migrate()
    store.upsert_run_projection(
        {
            "run_id": "run-1",
            "revision": 1,
            "loop_lineage_id": "lineage-a",
            "parent_run_id": "",
            "policy": "autonomous_knowledge",
            "phase": "planning",
            "status": "actionable",
            "summary": "{}",
            "artifact_refs": [],
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
