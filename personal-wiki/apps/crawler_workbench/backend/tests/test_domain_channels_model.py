from fastapi.testclient import TestClient

from crawler_workbench.db import migrate, open_db
from crawler_workbench.main import create_app
from crawler_workbench.profiles import initialize_profiles_from_seed
from crawler_workbench.settings import Settings


PROFILE_YAML = """
sources:
  - id: nccl-releases
    name: NCCL release notes
    type: web
    target_domain: ai_infra
    url: https://docs.nvidia.com/deeplearning/nccl/release-notes/index.html
    trust_level: trusted
    schedule: daily
    auto_ingest: true
    auth_required: false
    baseline_on_first_run: true
    topic: NCCL release history
  - id: nccl-github-closed-issues
    name: NCCL GitHub closed issues
    type: github
    target_domain: ai_infra
    url: https://api.github.com/repos/NVIDIA/nccl/issues?state=closed&sort=updated&direction=desc
    trust_level: trusted
    schedule: daily
    auto_ingest: false
    auth_required: true
    auth_method: env_token
    auth_ref: GITHUB_TOKEN
    topic: NCCL GitHub issues
  - id: nccl-arxiv
    name: NCCL arXiv papers
    type: arxiv
    target_domain: ai_infra
    url: https://export.arxiv.org/api/query?search_query=all:nccl
    trust_level: untrusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: NCCL papers
"""


def seed_domain_channels_fixture(settings: Settings) -> None:
    settings.resolved_state_dir.mkdir(parents=True)
    settings.sources_yaml_path.write_text(PROFILE_YAML, encoding="utf-8")
    with open_db(settings.database_path) as db:
        migrate(db)
        initialize_profiles_from_seed(db, settings.sources_yaml_path)


def test_schema_migration_creates_channel_tables_and_source_columns(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        tables = {row["name"] for row in db.execute("select name from sqlite_master where type = 'table'")}
        source_columns = {row["name"] for row in db.execute("pragma table_info(source_profiles)").fetchall()}

    assert "channels" in tables
    assert {"channel_id", "fetcher_type"} <= source_columns


def test_empty_database_imports_sources_yaml_once_and_assigns_channels(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    settings.resolved_state_dir.mkdir(parents=True)
    settings.sources_yaml_path.write_text(PROFILE_YAML, encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        initialize_profiles_from_seed(db, settings.sources_yaml_path)
        source = db.execute(
            "select channel_id, fetcher_type from source_profiles where id = 'nccl-releases'"
        ).fetchone()
        channel = db.execute(
            "select base_url, kind, connector from channels where id = ?",
            (source["channel_id"],),
        ).fetchone()

    assert source["fetcher_type"] == "web_page"
    assert channel["base_url"] == "https://docs.nvidia.com"
    assert channel["kind"] == "web"
    assert channel["connector"] == "generic"


def test_non_empty_database_is_not_overwritten_by_later_yaml_edits(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    settings.resolved_state_dir.mkdir(parents=True)
    settings.sources_yaml_path.write_text(PROFILE_YAML, encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        initialize_profiles_from_seed(db, settings.sources_yaml_path)

    settings.sources_yaml_path.write_text(PROFILE_YAML.replace("NCCL release notes", "Changed Name"), encoding="utf-8")

    with open_db(settings.database_path) as db:
        initialize_profiles_from_seed(db, settings.sources_yaml_path)
        row = db.execute("select name from source_profiles where id = 'nccl-releases'").fetchone()

    assert row["name"] == "NCCL release notes"


def test_source_listing_includes_channel_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    seed_domain_channels_fixture(settings)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/sources")

    assert response.status_code == 200
    payload = response.json()
    source = next(item for item in payload if item["id"] == "nccl-releases")
    assert source["channel_id"]
    assert source["fetcher_type"] == "web_page"
    assert source["channel_base_url"] == "https://docs.nvidia.com"
    assert source["channel_auth_state"] == "ready"


def test_sources_endpoint_filters_by_domain_and_channel(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    seed_domain_channels_fixture(settings)

    with open_db(settings.database_path) as db:
        github_source = db.execute(
            "select channel_id from source_profiles where id = 'nccl-github-closed-issues'"
        ).fetchone()

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get(
            "/api/sources",
            params={"domain": "ai_infra", "channel_id": github_source["channel_id"]},
        )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["nccl-github-closed-issues"]


def test_channel_listing_returns_source_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    seed_domain_channels_fixture(settings)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/channels", params={"domain": "ai_infra"})

    assert response.status_code == 200
    payload = response.json()
    assert any(
        item["base_url"] == "https://docs.nvidia.com"
        and item["source_count"] == 1
        and item["auth_state"] == "ready"
        for item in payload
    )
    github = next(item for item in payload if item["base_url"] == "https://api.github.com")
    assert github["kind"] == "api"
    assert github["connector"] == "github"
    assert github["auth_mode"] == "token"
    assert github["auth_required"] is True
