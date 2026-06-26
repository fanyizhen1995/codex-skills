from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
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


def _insert_pending_task(db, settings: Settings, source_id: str = "src", url: str = "https://vllm.ai/blog/nccl") -> int:
    _insert_source_profile(db, source_id, "manual")
    raw = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / source_id / "item.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("raw", encoding="utf-8")
    raw_item_id = db.execute(
        """
        insert into raw_items (
          source_id, target_domain, canonical_url, raw_path, title,
          content_hash, content_bytes, metadata_json
        )
        values (?, 'ai_infra', ?, ?, 'Item', 'hash', 3, '{}')
        """,
        (source_id, url, str(raw)),
    ).lastrowid
    task_id = db.execute(
        """
        insert into ingest_tasks (source_id, raw_item_id, target_domain, status, risk_level, reason)
        values (?, ?, 'ai_infra', 'pending', 'manual', 'needs review')
        """,
        (source_id, raw_item_id),
    ).lastrowid
    db.commit()
    return int(task_id)


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


def test_wiki_metrics_endpoint_reports_counts_sizes_and_light_health(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    wiki_root = settings.wiki_root
    domain_root = wiki_root / "domains" / "ai_infra"
    raw_path = domain_root / "raw" / "crawler" / "src" / "item.md"
    for path, text in [
        (wiki_root / "WIKI.md", "# Wiki\n"),
        (domain_root / "wiki" / "index.md", "# Index\n"),
        (domain_root / "wiki" / "nccl.md", "# NCCL\n"),
        (raw_path, "raw evidence\n"),
        (wiki_root / "global" / "wiki" / "gpu.md", "# GPU\n"),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "src", "manual")
        db.execute(
            """
            insert into raw_items (
              source_id, target_domain, canonical_url, raw_path, title,
              content_hash, content_bytes, metadata_json
            )
            values ('src', 'ai_infra', 'https://example.com/item', ?, 'Item', 'hash', 13, '{}')
            """,
            (str(raw_path),),
        )
        db.execute(
            """
            insert into validation_runs (target_domain, status, command, output, created_at)
            values ('ai_infra', 'succeeded', 'validate --domain ai_infra', 'No validation issues', '2026-06-26 02:00:00')
            """
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/wiki/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["counts"]["domain_count"] == 1
    assert data["counts"]["wiki_page_count"] == 3
    assert data["counts"]["raw_file_count"] == 1
    assert data["counts"]["raw_item_count"] == 1
    assert data["counts"]["total_file_count"] == 5
    assert data["sizes"]["total_bytes"] == sum(path.stat().st_size for path in wiki_root.rglob("*") if path.is_file())
    assert data["sizes"]["raw_bytes"] == raw_path.stat().st_size
    assert data["health"]["status"] == "healthy"
    assert data["health"]["score"] == 100
    assert data["health"]["latest_validation_status"] == "succeeded"
    assert data["health"]["latest_validation_at"] == "2026-06-26 02:00:00"


def test_runs_endpoint_exposes_failure_reason_for_failed_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "src", "manual")
        db.execute(
            """
            insert into fetch_runs (
              source_id, status, finished_at, fetched_count, changed_count, skipped_count, error
            )
            values ('src', 'failed', current_timestamp, 0, 0, 0, 'fetch exploded')
            """
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/runs")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["source_id"] == "src"
    assert data[0]["status"] == "failed"
    assert data[0]["error"] == "fetch exploded"
    assert data[0]["failure_reason"] == "fetch exploded"
    assert data[0]["failed_count"] == 1


def test_sources_endpoint_exposes_latest_fetch_run_state(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(db, "src", "manual")
        db.execute(
            """
            insert into fetch_runs (
              source_id, status, started_at, finished_at, fetched_count, changed_count, skipped_count, error
            )
            values ('src', 'failed', '2026-06-26 01:00:00', '2026-06-26 01:00:05', 0, 0, 0, 'old failure')
            """
        )
        db.execute(
            """
            insert into fetch_runs (
              source_id, status, started_at, finished_at, fetched_count, changed_count, skipped_count, error
            )
            values ('src', 'succeeded', '2026-06-26 02:00:00', '2026-06-26 02:00:10', 1, 1, 0, null)
            """
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/sources")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == "src"
    assert data[0]["last_run_at"] == "2026-06-26 02:00:10"
    assert data[0]["last_run_status"] == "succeeded"


def test_example_sources_include_daily_ai_infra_tracking_sources():
    import yaml

    config_path = Path(__file__).parents[2] / "config" / "sources.example.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in data["sources"]}

    assert sources["nccl-release-notes"] == {
        "id": "nccl-release-notes",
        "name": "NCCL release notes",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html",
        "trust_level": "trusted",
        "schedule": "daily",
        "auto_ingest": True,
        "auth_required": False,
        "baseline_on_first_run": True,
        "topic": "NCCL release notes",
    }
    assert sources["nccl-github-closed-issues"]["url"] == "https://api.github.com/repos/NVIDIA/nccl/issues?sort=updated&direction=desc"
    assert sources["nccl-github-closed-issues"]["type"] == "github"
    assert sources["nccl-github-closed-issues"]["schedule"] == "daily"
    assert sources["nccl-github-closed-issues"]["auto_ingest"] is True
    assert sources["nccl-github-closed-issues"]["baseline_on_first_run"] is True
    assert sources["sglang-github-closed-issues-prs"]["url"] == "https://api.github.com/repos/sgl-project/sglang?sort=updated&direction=desc"
    assert sources["sglang-github-closed-issues-prs"]["type"] == "github"
    assert sources["sglang-github-closed-issues-prs"]["schedule"] == "daily"
    assert sources["sglang-github-closed-issues-prs"]["auto_ingest"] is True
    assert sources["sglang-github-closed-issues-prs"]["baseline_on_first_run"] is True
    assert sources["nccl-technical-blog"]["url"] == "https://developer.nvidia.com/blog/tag/nccl/feed/"
    assert sources["nccl-technical-blog"]["type"] == "rss"
    assert sources["nccl-technical-blog"]["schedule"] == "weekly"
    assert sources["nccl-technical-blog"]["fetch_article_body"] is True
    assert "NCCL" in sources["nccl-technical-blog"]["include_keywords"]
    assert sources["nccl-github-releases"]["url"] == "https://github.com/NVIDIA/nccl/releases.atom"
    assert sources["nccl-github-releases"]["schedule"] == "weekly"
    assert sources["nccl-arxiv-papers"]["type"] == "arxiv"
    assert sources["nccl-arxiv-papers"]["schedule"] == "weekly"


def test_trust_queue_source_endpoint_sets_manual_source_and_approves_task(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        task_id = _insert_pending_task(db, settings)

    with TestClient(app) as client:
        response = client.post(f"/api/queue/{task_id}/trust-source", json={"mode": "manual"})

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "vllm.ai"
    assert data["approved_count"] == 1
    with open_db(settings.database_path) as db:
        profile = db.execute("select schedule, auto_ingest from source_profiles where id = 'src'").fetchone()
        task = db.execute("select status from ingest_tasks where id = ?", (task_id,)).fetchone()
    assert profile["schedule"] == "manual"
    assert profile["auto_ingest"] == 1
    assert task["status"] == "approved"


def test_trust_queue_source_endpoint_sets_monthly_schedule(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
    with open_db(settings.database_path) as db:
        migrate(db)
        task_id = _insert_pending_task(db, settings)

    with TestClient(app) as client:
        response = client.post(f"/api/queue/{task_id}/trust-source", json={"mode": "scheduled", "frequency": "monthly"})

    assert response.status_code == 200
    with open_db(settings.database_path) as db:
        profile = db.execute("select schedule, auto_ingest from source_profiles where id = 'src'").fetchone()
    assert profile["schedule"] == "monthly"
    assert profile["auto_ingest"] == 1


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
