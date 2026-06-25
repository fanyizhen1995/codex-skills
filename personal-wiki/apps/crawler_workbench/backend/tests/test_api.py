from __future__ import annotations

from datetime import UTC, datetime, timedelta
import threading

import pytest
from fastapi.testclient import TestClient

from crawler_workbench.db import migrate, open_db
from crawler_workbench.main import create_app
from crawler_workbench.scheduler import Scheduler
from crawler_workbench.settings import Settings


def _insert_source_profile(db, source_id: str, schedule: str, auth_state: str = "ready", enabled: int = 1, next_run_at=None):
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, auth_state, topic, enabled, next_run_at
        )
        values (?, ?, 'web', 'ai_infra', 'https://example.com', 'trusted', ?, 0, 0, ?, 'topic', ?, ?)
        """,
        (source_id, source_id, schedule, auth_state, enabled, next_run_at),
    )


def test_domains_endpoint_lists_domain_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    (settings.wiki_root / "domains" / "ai_infra").mkdir(parents=True)
    (settings.wiki_root / "domains" / "python").mkdir()
    (settings.wiki_root / "WIKI.md").write_text("# Wiki\n", encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/domains")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "ai_infra", "name": "ai_infra"},
        {"id": "python", "name": "python"},
    ]


def test_settings_endpoint_reports_runtime_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state", bind_host="127.0.0.1", bind_port=9876)

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["bind_host"] == "127.0.0.1"
    assert data["bind_port"] == 9876
    assert data["authenticated"] is False
    assert "No login" in data["warning"]
    assert data["wiki_root"] == str(settings.wiki_root)
    assert data["database_path"] == str(settings.database_path)


@pytest.mark.asyncio
async def test_scheduler_run_once_runs_due_ready_sources_and_updates_next_run_at(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    now = datetime.now(UTC).replace(tzinfo=None)
    due_past = (now - timedelta(hours=1)).isoformat(timespec="seconds")
    future = (now + timedelta(hours=1)).isoformat(timespec="seconds")

    with open_db(settings.database_path) as db:
        migrate(db)
        for source_id, schedule, auth_state, enabled, next_run_at in [
            ("hourly-due", "hourly", "ready", 1, None),
            ("daily-due", "daily", "ready", 1, due_past),
            ("weekly-not-due", "weekly", "ready", 1, future),
            ("manual-source", "manual", "ready", 1, None),
            ("needs-auth", "hourly", "needs_auth_config", 1, None),
            ("disabled-source", "hourly", "ready", 0, None),
        ]:
            _insert_source_profile(db, source_id, schedule, auth_state, enabled, next_run_at)
        db.commit()

    called: list[str] = []

    def fake_run_source_once(received_settings, db, source_id):
        assert received_settings is settings
        called.append(source_id)
        return {"fetch_run_id": len(called), "fetched_count": 0, "changed_count": 0, "skipped_count": 0}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 2
    assert called == ["daily-due", "hourly-due"]
    with open_db(settings.database_path) as db:
        rows = {
            row["id"]: row["next_run_at"]
            for row in db.execute("select id, next_run_at from source_profiles order by id")
        }

    assert datetime.fromisoformat(rows["hourly-due"]) > now
    assert datetime.fromisoformat(rows["daily-due"]) > now + timedelta(hours=23)
    assert rows["weekly-not-due"] == future
    assert rows["manual-source"] is None
    assert rows["needs-auth"] is None
    assert rows["disabled-source"] is None


@pytest.mark.asyncio
async def test_scheduler_continues_after_source_failure_and_advances_all_due_sources(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    now = datetime.now(UTC).replace(tzinfo=None)

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "first-due", "hourly")
        _insert_source_profile(db, "second-due", "daily")
        db.commit()

    called: list[str] = []

    def fake_run_source_once(received_settings, db, source_id):
        assert received_settings is settings
        called.append(source_id)
        if source_id == "first-due":
            raise RuntimeError("fetch failed")
        return {"fetch_run_id": len(called), "fetched_count": 0, "changed_count": 0, "skipped_count": 0}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 2
    assert called == ["first-due", "second-due"]
    with open_db(settings.database_path) as db:
        rows = {
            row["id"]: row["next_run_at"]
            for row in db.execute("select id, next_run_at from source_profiles order by id")
        }

    assert datetime.fromisoformat(rows["first-due"]) > now
    assert datetime.fromisoformat(rows["second-due"]) > now + timedelta(hours=23)


@pytest.mark.asyncio
async def test_scheduler_ignores_unknown_schedule(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "typo-schedule", "daliy")
        db.commit()

    called: list[str] = []

    def fake_run_source_once(received_settings, db, source_id):
        called.append(source_id)
        return {"fetch_run_id": len(called), "fetched_count": 0, "changed_count": 0, "skipped_count": 0}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 0
    assert called == []
    with open_db(settings.database_path) as db:
        row = db.execute("select next_run_at from source_profiles where id = 'typo-schedule'").fetchone()
    assert row["next_run_at"] is None


@pytest.mark.asyncio
async def test_scheduler_run_once_executes_sync_work_off_event_loop_thread(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    event_loop_thread_id = threading.get_ident()
    worker_thread_ids: list[int] = []

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "hourly-due", "hourly")
        db.commit()

    def fake_run_source_once(received_settings, db, source_id):
        worker_thread_ids.append(threading.get_ident())
        return {"fetch_run_id": 1, "fetched_count": 0, "changed_count": 0, "skipped_count": 0}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 1
    assert worker_thread_ids
    assert all(thread_id != event_loop_thread_id for thread_id in worker_thread_ids)
