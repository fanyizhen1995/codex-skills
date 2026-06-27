from __future__ import annotations

from datetime import UTC, datetime, timedelta
import threading

import pytest

from crawler_workbench.db import migrate, open_db
from crawler_workbench.scheduler import Scheduler
from crawler_workbench.settings import Settings


def _insert_source_profile(
    db,
    source_id: str,
    schedule: str,
    auth_state: str = "ready",
    enabled: int = 1,
    next_run_at=None,
    run_policy: str = "scheduled",
):
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, run_policy, auth_state, topic, enabled, next_run_at
        )
        values (?, ?, 'web', 'ai_infra', 'https://example.com', 'trusted', ?, 0, 0, ?, ?, 'topic', ?, ?)
        """,
        (source_id, source_id, schedule, run_policy, auth_state, enabled, next_run_at),
    )


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
            ("monthly-due", "monthly", "ready", 1, due_past),
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

    assert ran_count == 3
    assert called == ["daily-due", "hourly-due", "monthly-due"]
    with open_db(settings.database_path) as db:
        rows = {
            row["id"]: row["next_run_at"]
            for row in db.execute("select id, next_run_at from source_profiles order by id")
        }

    assert datetime.fromisoformat(rows["hourly-due"]) > now
    assert datetime.fromisoformat(rows["daily-due"]) > now + timedelta(hours=23)
    assert datetime.fromisoformat(rows["monthly-due"]) > now + timedelta(days=27)
    assert rows["weekly-not-due"] == future
    assert rows["manual-source"] is None
    assert rows["needs-auth"] is None
    assert rows["disabled-source"] is None


@pytest.mark.asyncio
async def test_scheduler_run_once_executes_approved_ingest_tasks_after_fetch(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "daily-due", "daily")
        db.commit()

    executed_tasks: list[int] = []

    def fake_run_source_once(received_settings, db, source_id):
        assert received_settings is settings
        raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, fetch_run_id, target_domain, canonical_url, raw_path,
              title, content_hash, content_bytes, metadata_json
            )
            values (?, null, 'ai_infra', 'https://example.com/new', ?, 'New item', 'abc', 12, '{}')
            """,
            (source_id, str(settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / source_id / "new.md")),
        ).lastrowid
        db.execute(
            """
            insert into ingest_tasks (
              source_id, raw_item_id, target_domain, status, risk_level, reason
            )
            values (?, ?, 'ai_infra', 'approved', 'low', 'trusted low-risk source eligible for automatic ingest')
            """,
            (source_id, raw_item_id),
        )
        db.commit()
        return {"fetch_run_id": 1, "fetched_count": 1, "changed_count": 1, "skipped_count": 0}

    def fake_run_approved_task(received_settings, db, task_id, auto_commit_enabled):
        assert received_settings is settings
        assert auto_commit_enabled is True
        executed_tasks.append(task_id)
        db.execute("update ingest_tasks set status = 'succeeded', updated_at = current_timestamp where id = ?", (task_id,))
        db.commit()
        return {"id": task_id, "status": "succeeded"}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)
    monkeypatch.setattr("crawler_workbench.scheduler.run_approved_task", fake_run_approved_task)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 1
    assert executed_tasks == [1]
    with open_db(settings.database_path) as db:
        task = db.execute("select status from ingest_tasks where id = 1").fetchone()
    assert task["status"] == "succeeded"


@pytest.mark.asyncio
async def test_scheduler_run_once_executes_existing_approved_tasks_without_due_sources(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "manual-source", "manual")
        raw_item_id = db.execute(
            """
            insert into raw_items (
              source_id, fetch_run_id, target_domain, canonical_url, raw_path,
              title, content_hash, content_bytes, metadata_json
            )
            values ('manual-source', null, 'ai_infra', 'https://example.com/new', ?, 'New item', 'abc', 12, '{}')
            """,
            (str(settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "manual-source" / "new.md"),),
        ).lastrowid
        db.execute(
            """
            insert into ingest_tasks (
              source_id, raw_item_id, target_domain, status, risk_level, reason
            )
            values ('manual-source', ?, 'ai_infra', 'approved', 'low', 'trusted low-risk source eligible for automatic ingest')
            """,
            (raw_item_id,),
        )
        db.commit()

    executed_tasks: list[int] = []

    def fake_run_source_once(received_settings, db, source_id):
        raise AssertionError("manual source should not be fetched")

    def fake_run_approved_task(received_settings, db, task_id, auto_commit_enabled):
        executed_tasks.append(task_id)
        db.execute("update ingest_tasks set status = 'succeeded', updated_at = current_timestamp where id = ?", (task_id,))
        db.commit()
        return {"id": task_id, "status": "succeeded"}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)
    monkeypatch.setattr("crawler_workbench.scheduler.run_approved_task", fake_run_approved_task)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 0
    assert executed_tasks == [1]


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


@pytest.mark.asyncio
async def test_scheduler_skips_once_source_after_successful_evidence_capture(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "known-h200", "monthly", run_policy="once")
        db.execute(
            """
            insert into fetch_runs (source_id, status, finished_at, fetched_count, changed_count, skipped_count)
            values ('known-h200', 'succeeded', current_timestamp, 1, 1, 0)
            """
        )
        db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title, content_hash, content_bytes, metadata_json
            )
            values ('known-h200', 'ai_infra', 'https://example.com/h200', '/tmp/h200.md', 'H200', 'hash', 4, '{}')
            """
        )
        db.commit()

    called: list[str] = []

    def fake_run_source_once(received_settings, db, source_id):
        called.append(source_id)
        return {"fetch_run_id": 1, "fetched_count": 1, "changed_count": 0, "skipped_count": 1}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 0
    assert called == []


@pytest.mark.asyncio
async def test_scheduler_runs_once_source_until_successful_capture_exists(tmp_path, monkeypatch):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "new-hardware", "monthly", run_policy="once")
        db.commit()

    called: list[str] = []

    def fake_run_source_once(received_settings, db, source_id):
        called.append(source_id)
        return {"fetch_run_id": 1, "fetched_count": 1, "changed_count": 1, "skipped_count": 0}

    monkeypatch.setattr("crawler_workbench.scheduler.run_source_once", fake_run_source_once)

    ran_count = await Scheduler(settings).run_once()

    assert ran_count == 1
    assert called == ["new-hardware"]
