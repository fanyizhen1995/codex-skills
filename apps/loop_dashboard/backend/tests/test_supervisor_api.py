from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from loop_dashboard.main import create_app
from loop_dashboard.supervisor_store import SupervisorDashboardStore
from scripts.loop_supervisor.store import SCHEMA_VERSION, SupervisorStore


PAGE_KEYS = {
    "items",
    "next_cursor",
    "previous_cursor",
    "page_size",
    "total",
    "has_more",
}


def _open_seeded_database(project_root: Path) -> sqlite3.Connection:
    store = SupervisorStore.open(project_root)
    store.migrate()
    store.close()
    connection = sqlite3.connect(project_root / ".codex" / "supervisor" / "supervisor.db")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _seed_supervisor_database(project_root: Path, action_count: int = 25) -> sqlite3.Connection:
    connection = _open_seeded_database(project_root)
    connection.execute(
        """
        INSERT INTO runs(
          run_id, loop_lineage_id, policy, phase, status, revision,
          created_at, updated_at, last_seen_at
        ) VALUES ('run-1', 'lineage-1', 'demand_development', 'generating',
                  'active', 1, '2026-07-15T00:00:00Z',
                  '2026-07-15T00:00:00Z', '2026-07-15T00:00:00Z')
        """
    )
    for index in range(action_count):
        timestamp = f"2026-07-15T00:{index:02d}:00Z"
        connection.execute(
            """
            INSERT INTO actions(
              action_id, idempotency_key, canonical_identity, run_id,
              run_revision, action_type, status, payload_json,
              created_at, updated_at
            ) VALUES (?, ?, ?, 'run-1', 1, 'run_generator', ?, ?, ?, ?)
            """,
            (
                f"action-{index:03d}",
                f"key-{index:03d}",
                f"identity-{index:03d}",
                "pending" if index % 2 else "complete",
                json.dumps({"note": "token=action-secret"}),
                timestamp,
                timestamp,
            ),
        )
    connection.execute(
        """
        INSERT INTO action_attempts(
          attempt_id, action_id, worker_id, result_class, summary,
          artifact_json, started_at, finished_at, created_at
        ) VALUES ('attempt-1', 'action-000', 'worker-1', 'success', 'done',
                  '[]', '2026-07-15T00:00:00Z', '2026-07-15T00:01:00Z',
                  '2026-07-15T00:01:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO transitions(
          transition_id, run_id, from_revision, to_revision, from_phase,
          to_phase, action_id, created_at
        ) VALUES ('transition-1', 'run-1', 0, 1, 'planned', 'generating',
                  'action-000', '2026-07-15T00:02:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO reviews(
          review_id, trigger, status, decision, summary, created_at, updated_at
        ) VALUES ('review-1', 'cadence', 'review_complete', 'continue', 'continue',
                  '2026-07-15T00:03:00Z', '2026-07-15T00:03:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO review_findings(
          finding_id, review_id, finding_key, status, severity, summary,
          first_seen_at, last_seen_at, created_at, updated_at
        ) VALUES ('finding-1', 'review-1', 'finding-key-1', 'open', 'major',
                  'fix it', '2026-07-15T00:03:00Z', '2026-07-15T00:03:00Z',
                  '2026-07-15T00:03:00Z', '2026-07-15T00:03:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO user_decisions(
          decision_id, scope, run_id, status, summary, created_at, updated_at
        ) VALUES ('decision-1', 'run', 'run-1', 'open', 'choose',
                  '2026-07-15T00:04:00Z', '2026-07-15T00:04:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO services(
          service_id, status, endpoint, details_json, created_at, updated_at
        ) VALUES ('loop-dashboard', 'healthy', 'http://127.0.0.1:8766',
                  '{"reachable": true}', '2026-07-15T00:05:00Z',
                  '2026-07-15T00:05:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO freshness_checks(
          check_id, target, status, summary, details_json, checked_at, created_at
        ) VALUES ('freshness-1', 'wiki', 'fresh', 'indexed', '{}',
                  '2026-07-15T00:06:00Z', '2026-07-15T00:06:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO skill_snapshots(
          snapshot_id, total_skills, used_skills, snapshot_json, created_at
        ) VALUES ('snapshot-1', 2, 1, ?, '2026-07-15T00:07:00Z')
        """,
        (
            json.dumps(
                {
                    "inventory": [
                        {"name": "skill-a", "status": "used"},
                        {"name": "skill-b", "status": "candidate"},
                    ],
                    "confirmed_usage": ["skill-a"],
                    "duplicate_groups": [],
                    "recommendations": [],
                }
            ),
        ),
    )
    connection.commit()
    return connection


def _assert_page(payload: dict, *, total: int | None = None) -> None:
    assert PAGE_KEYS <= payload.keys()
    if total is not None:
        assert payload["total"] == total


def test_supervisor_routes_are_sqlite_backed_and_paginated(tmp_path: Path) -> None:
    connection = _seed_supervisor_database(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))

    summary = client.get("/api/supervisor").json()
    assert summary["status"] == "available"
    assert summary["counts"]["actions"] == 25

    routes = {
        "/api/supervisor/services": 1,
        "/api/supervisor/services/freshness": 1,
        "/api/supervisor/actions": 25,
        "/api/supervisor/actions/action-000/attempts": 1,
        "/api/supervisor/transitions": 1,
        "/api/supervisor/reviews": 1,
        "/api/supervisor/reviews/review-1/findings": 1,
        "/api/supervisor/decisions": 1,
        "/api/supervisor/skills": 1,
        "/api/supervisor/skills/snapshot-1/rows": 2,
        "/api/supervisor/recovery": 1,
    }
    for route, total in routes.items():
        response = client.get(route)
        assert response.status_code == 200, route
        payload = response.json()
        _assert_page(payload, total=total)
        assert payload["status"] == "available"

    serialized_action = json.dumps(
        client.get("/api/supervisor/actions?page_size=20").json(),
        ensure_ascii=False,
    )
    skill_snapshot = client.get("/api/supervisor/skills").json()["items"][0]
    assert "snapshot" not in skill_snapshot
    assert skill_snapshot["skill_row_count"] == 2
    assert "action-secret" not in serialized_action
    assert "[REDACTED]" in serialized_action
    assert client.get("/api/supervisor/auditor").status_code == 404
    connection.close()


def test_sqlite_cursor_is_stable_under_backdated_inserts(tmp_path: Path) -> None:
    connection = _seed_supervisor_database(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))

    first = client.get("/api/supervisor/actions?page_size=20").json()
    first_ids = {item["action_id"] for item in first["items"]}
    connection.execute(
        """
        INSERT INTO actions(
          action_id, idempotency_key, canonical_identity, run_id,
          run_revision, action_type, status, created_at, updated_at
        ) VALUES ('action-inserted', 'key-inserted', 'identity-inserted',
                  'run-1', 1, 'run_generator', 'pending',
                  '2026-07-15T00:03:30Z', '2026-07-15T00:03:30Z')
        """
    )
    connection.commit()

    second = client.get(
        "/api/supervisor/actions",
        params={"page_size": "20", "cursor": first["next_cursor"]},
    ).json()
    assert first_ids.isdisjoint(item["action_id"] for item in second["items"])
    assert "action-inserted" not in {item["action_id"] for item in second["items"]}
    assert second["total"] == 25
    connection.close()


def test_invalid_cursor_filter_and_page_size_are_400(tmp_path: Path) -> None:
    connection = _seed_supervisor_database(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))

    assert client.get("/api/supervisor/actions?cursor=bad").status_code == 400
    assert client.get("/api/supervisor/actions?cursor=").status_code == 400
    assert client.get("/api/supervisor/actions?page_size=21").status_code == 400
    assert client.get("/api/supervisor/actions?unknown=value").status_code == 400
    assert client.get("/api/supervisor/actions?status=").status_code == 400
    assert client.get("/api/supervisor/recovery?recovery_tier=nope").status_code == 400

    first = client.get("/api/supervisor/actions").json()
    mismatch = client.get(
        "/api/supervisor/actions",
        params={"status": "complete", "cursor": first["next_cursor"]},
    )
    assert mismatch.status_code == 400
    connection.close()


def test_missing_sqlite_is_honestly_unavailable_without_jsonl_fallback(tmp_path: Path) -> None:
    supervisor_dir = tmp_path / ".codex" / "supervisor"
    supervisor_dir.mkdir(parents=True)
    (supervisor_dir / "run-decisions.jsonl").write_text(
        '{"decision_id":"legacy-success"}\n', encoding="utf-8"
    )
    client = TestClient(create_app(project_root=tmp_path))

    summary = client.get("/api/supervisor").json()
    page = client.get("/api/supervisor/decisions").json()

    assert summary["status"] == "unavailable"
    assert summary["diagnostics"]
    assert page["status"] == "unavailable"
    assert page["items"] == []
    assert "legacy-success" not in json.dumps(page)


def test_incompatible_sqlite_schema_is_reported_without_migration(tmp_path: Path) -> None:
    db_path = tmp_path / ".codex" / "supervisor" / "supervisor.db"
    db_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE actions(action_id TEXT PRIMARY KEY)")
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION - 1}")
    connection.commit()
    connection.close()
    before = db_path.read_bytes()
    client = TestClient(create_app(project_root=tmp_path))

    summary = client.get("/api/supervisor").json()
    page = client.get("/api/supervisor/actions").json()

    assert summary["status"] == "schema_incompatible"
    assert page["status"] == "schema_incompatible"
    assert page["items"] == []
    assert db_path.read_bytes() == before


def test_missing_contract_column_is_schema_incompatible(tmp_path: Path) -> None:
    connection = _open_seeded_database(tmp_path)
    connection.execute("ALTER TABLE actions DROP COLUMN payload_json")
    connection.commit()
    connection.close()
    client = TestClient(create_app(project_root=tmp_path))

    page = client.get("/api/supervisor/actions").json()

    assert page["status"] == "schema_incompatible"
    assert "payload_json" in page["diagnostics"][0]["message"]


def test_missing_membership_trigger_is_schema_incompatible(tmp_path: Path) -> None:
    connection = _open_seeded_database(tmp_path)
    connection.execute("DROP TRIGGER row_sequence_actions_insert")
    connection.commit()
    connection.close()
    client = TestClient(create_app(project_root=tmp_path))

    page = client.get("/api/supervisor/actions").json()

    assert page["status"] == "schema_incompatible"
    assert "row_sequence_actions_insert" in page["diagnostics"][0]["message"]


def test_supervisor_connection_is_uri_read_only_and_query_only(tmp_path: Path) -> None:
    writer = _seed_supervisor_database(tmp_path)
    writer.close()
    store = SupervisorDashboardStore(tmp_path)

    connection = store._connect()
    try:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM actions")
    finally:
        connection.close()


def test_action_attempt_log_is_bound_to_its_run_attempt_and_fixed_stream(
    tmp_path: Path,
) -> None:
    connection = _seed_supervisor_database(tmp_path)
    run_dir = tmp_path / ".codex" / "loop-runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "policy": "demand_development",
                "phase": "generating",
                "task_id": "run-1",
                "requirement": "attempt logs",
                "attempts": {},
                "last_result": "none",
                "next_action": "run_generator",
            }
        ),
        encoding="utf-8",
    )
    log_path = run_dir / "generator-attempt-1.stdout.log"
    log_path.write_text("attempt output\n", encoding="utf-8")
    relative_log_path = str(log_path.relative_to(tmp_path))
    connection.execute(
        "UPDATE action_attempts SET artifact_json = ? WHERE attempt_id = 'attempt-1'",
        (json.dumps([relative_log_path]),),
    )
    connection.commit()
    client = TestClient(create_app(project_root=tmp_path))

    page = client.get("/api/runs/run-1/logs").json()
    attempt_log = next(
        item for item in page["items"] if item["attempt_id"] == "attempt-1"
    )
    detail = client.get(f"/api/runs/run-1/logs/{attempt_log['log_id']}")

    assert attempt_log["stream"] == "stdout"
    assert detail.status_code == 200
    assert detail.json()["content"] == "attempt output\n"
    assert client.get(f"/api/runs/other/logs/{attempt_log['log_id']}").status_code == 404
    with pytest.raises(ValueError, match="stdout or stderr"):
        client.app.state.supervisor_store.attempt_log_path(
            "run-1", "attempt-1", "../../secret"
        )
    connection.close()
