import sqlite3

from fastapi.testclient import TestClient
import pytest

from crawler_workbench.db import connect, migrate
from crawler_workbench.fetchers.base import FetchResult
from crawler_workbench.fetch_service import run_source_once
from crawler_workbench.main import create_app
from crawler_workbench.policy import ingest_decision
from crawler_workbench.profiles import mirror_profiles
from crawler_workbench.settings import Settings


class StaticFetcher:
    def __init__(self, results):
        self.results = results

    def fetch(self, profile):
        return self.results


class FailingFetcher:
    def fetch(self, profile):
        raise RuntimeError("fetch exploded")


class CloseTrackingFetcher(StaticFetcher):
    def __init__(self, results):
        super().__init__(results)
        self.closed = False

    def close(self):
        self.closed = True


def profile(
    auto_ingest=True,
    trust_level="trusted",
    auth_required=False,
    enabled=True,
    baseline_on_first_run=False,
    **extra,
):
    return {
        "id": "src",
        "name": "Source",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://example.com",
        "trust_level": trust_level,
        "schedule": "manual",
        "auto_ingest": auto_ingest,
        "auth_required": auth_required,
        "baseline_on_first_run": baseline_on_first_run,
        "topic": "topic",
        "enabled": enabled,
        **extra,
    }


def write_sources_yaml(settings, enabled=True):
    settings.resolved_state_dir.mkdir(parents=True, exist_ok=True)
    settings.sources_yaml_path.write_text(
        f"""
sources:
  - id: src
    name: Source
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: manual
    auto_ingest: true
    auth_required: false
    topic: topic
    enabled: {str(enabled).lower()}
""",
        encoding="utf-8",
    )


def test_ingest_decision_blocks_untrusted_and_large():
    assert ingest_decision(profile(trust_level="untrusted"), 10).status == "pending"
    assert ingest_decision(profile(auth_required=True), 10).status == "pending"
    assert ingest_decision(profile(), 3_000_000, max_auto_ingest_bytes=2_000_000).status == "pending"
    assert ingest_decision(profile(), 10).status == "approved"


def test_run_source_once_records_raw_item_and_ingest_task(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    result = FetchResult(
        canonical_url="https://example.com/doc",
        title="Doc",
        content="hello",
        content_type="text/markdown",
        metadata={"kind": "test"},
    )
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        summary = run_source_once(settings, db, "src", fetcher=StaticFetcher([result]))
        tasks = db.execute("select status, reason from ingest_tasks").fetchall()
        raw_items = db.execute("select raw_path, content_hash from raw_items").fetchall()
    assert summary["changed_count"] == 1
    assert tasks[0]["status"] == "approved"
    assert "trusted" in tasks[0]["reason"]
    assert raw_items[0]["raw_path"].endswith(".md")


def test_run_source_once_baselines_first_run_without_raw_or_tasks(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    results = [
        FetchResult("https://example.com/one", "One", "one", "text/markdown"),
        FetchResult("https://example.com/two", "Two", "two", "text/markdown"),
    ]
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile(baseline_on_first_run=True)])
        summary = run_source_once(settings, db, "src", fetcher=StaticFetcher(results))
        raw_count = db.execute("select count(*) as count from raw_items").fetchone()["count"]
        version_rows = db.execute("select raw_item_id from content_versions order by canonical_url").fetchall()
        task_count = db.execute("select count(*) as count from ingest_tasks").fetchone()["count"]

    raw_dir = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src"
    raw_files = list(raw_dir.glob("*.md")) if raw_dir.exists() else []
    assert summary == {"fetch_run_id": 1, "fetched_count": 2, "changed_count": 0, "skipped_count": 2}
    assert raw_count == 0
    assert [row["raw_item_id"] for row in version_rows] == [None, None]
    assert task_count == 0
    assert raw_files == []


def test_run_source_once_creates_task_for_changed_content_after_baseline(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile(baseline_on_first_run=True)])
        run_source_once(
            settings,
            db,
            "src",
            fetcher=StaticFetcher([FetchResult("https://example.com/doc", "Doc", "old", "text/markdown")]),
        )
        second = run_source_once(
            settings,
            db,
            "src",
            fetcher=StaticFetcher([FetchResult("https://example.com/doc", "Doc", "new", "text/markdown")]),
        )
        task = db.execute("select status, reason from ingest_tasks").fetchone()
        raw_count = db.execute("select count(*) as count from raw_items").fetchone()["count"]

    assert second["changed_count"] == 1
    assert second["skipped_count"] == 0
    assert raw_count == 1
    assert task["status"] == "approved"
    assert "trusted" in task["reason"]


def test_run_source_once_skips_duplicate_hash(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    result = FetchResult("https://example.com/doc", "Doc", "hello", "text/markdown")
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        run_source_once(settings, db, "src", fetcher=StaticFetcher([result]))
        second = run_source_once(settings, db, "src", fetcher=StaticFetcher([result]))
    assert second["skipped_count"] == 1
    assert second["changed_count"] == 0


def test_run_source_once_cleans_raw_files_and_counts_after_insert_failure(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    results = [
        FetchResult("https://example.com/one", "One", "one", "text/markdown"),
        FetchResult("https://example.com/two", None, "two", "text/markdown"),
    ]
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        with pytest.raises(sqlite3.IntegrityError):
            run_source_once(settings, db, "src", fetcher=StaticFetcher(results))
        fetch_run = db.execute("select * from fetch_runs").fetchone()
        raw_count = db.execute("select count(*) as count from raw_items").fetchone()["count"]
        version_count = db.execute("select count(*) as count from content_versions").fetchone()["count"]
        task_count = db.execute("select count(*) as count from ingest_tasks").fetchone()["count"]

    raw_dir = settings.wiki_root / "domains" / "ai_infra" / "raw" / "crawler" / "src"
    raw_files = list(raw_dir.glob("*.md")) if raw_dir.exists() else []
    assert fetch_run["status"] == "failed"
    assert fetch_run["fetched_count"] == 2
    assert fetch_run["changed_count"] == 0
    assert fetch_run["error"]
    assert raw_count == 0
    assert version_count == 0
    assert task_count == 0
    assert raw_files == []


def test_specs_candidate_fetch_rolls_back_raw_and_specs_after_later_insert_failure(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    results = [
        FetchResult("https://example.com/one", "One", "峰值功耗 600W", "text/markdown"),
        FetchResult("https://example.com/two", None, "two", "text/markdown"),
    ]
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(
            db,
            [
                profile(
                    source_rank="S1",
                    accelerator_scope=["gpu"],
                    extract_mode="specs_candidate",
                    vendor_hint="src",
                    auto_resolve=False,
                )
            ],
        )
        with pytest.raises(sqlite3.IntegrityError):
            run_source_once(settings, db, "src", fetcher=StaticFetcher(results))
        raw_count = db.execute("select count(*) as count from raw_items").fetchone()["count"]
        sku_count = db.execute("select count(*) as count from accelerator_skus").fetchone()["count"]
        observation_count = db.execute("select count(*) as count from accelerator_observations").fetchone()["count"]
        resolved_count = db.execute("select count(*) as count from accelerator_resolved_specs").fetchone()["count"]

    assert raw_count == 0
    assert sku_count == 0
    assert observation_count == 0
    assert resolved_count == 0


def test_run_source_once_records_failed_run_when_fetcher_raises(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        with pytest.raises(RuntimeError, match="fetch exploded"):
            run_source_once(settings, db, "src", fetcher=FailingFetcher())
        fetch_run = db.execute("select status, error, fetched_count, changed_count from fetch_runs").fetchone()
    assert fetch_run["status"] == "failed"
    assert fetch_run["error"] == "fetch exploded"
    assert fetch_run["fetched_count"] == 0
    assert fetch_run["changed_count"] == 0


def test_run_source_once_does_not_close_injected_fetcher(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    fetcher = CloseTrackingFetcher([
        FetchResult("https://example.com/doc", "Doc", "hello", "text/markdown"),
    ])
    with connect(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, [profile()])
        run_source_once(settings, db, "src", fetcher=fetcher)
    assert fetcher.closed is False


def test_run_source_api_returns_404_for_missing_source(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    write_sources_yaml(settings)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/api/sources/missing/run")

    assert response.status_code == 404


def test_run_source_api_returns_409_for_disabled_source(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    write_sources_yaml(settings, enabled=False)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post("/api/sources/src/run")

    assert response.status_code == 409
