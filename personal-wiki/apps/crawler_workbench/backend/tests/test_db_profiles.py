import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
import pytest

from crawler_workbench.db import connect, migrate, open_db, transaction
from crawler_workbench.main import create_app
from crawler_workbench.profiles import load_profiles_from_yaml, mirror_profiles
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
    topic: NCCL release history
  - id: private-github
    name: Private GitHub issues
    type: github
    target_domain: ai_infra
    url: https://api.github.com/repos/example/private/issues
    trust_level: untrusted
    schedule: manual
    auto_ingest: false
    auth_required: true
    auth_method: env_token
    auth_ref: GITHUB_TOKEN
    topic: private issue audit
"""


def test_schema_migration_creates_profile_tables(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        tables = {
            row["name"]
            for row in db.execute("select name from sqlite_master where type = 'table'")
        }
    assert "source_profiles" in tables
    assert "source_auth_refs" in tables
    assert "fetch_runs" in tables
    assert "wiki_search_fts" in tables


def test_schema_migration_adds_baseline_column_to_existing_profile_table(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        db.execute(
            """
            create table source_profiles (
              id text primary key,
              name text not null,
              type text not null,
              target_domain text not null,
              url text not null,
              trust_level text not null,
              schedule text not null,
              auto_ingest integer not null default 0,
              auth_required integer not null default 0,
              auth_state text not null default 'ready',
              auth_method text,
              auth_ref text,
              topic text not null,
              enabled integer not null default 1,
              last_run_at text,
              next_run_at text,
              created_at text not null default current_timestamp,
              updated_at text not null default current_timestamp
            )
            """
        )
        db.commit()

        migrate(db)
        columns = {row["name"] for row in db.execute("pragma table_info(source_profiles)").fetchall()}

    assert "baseline_on_first_run" in columns
    assert "config_json" in columns


def test_open_db_closes_connection(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        db.execute("select 1")

    try:
        db.execute("select 1")
    except sqlite3.ProgrammingError as error:
        assert "closed" in str(error)
    else:
        raise AssertionError("open_db did not close the SQLite connection")


def test_yaml_profiles_mirror_to_sqlite(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(PROFILE_YAML, encoding="utf-8")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        profiles = load_profiles_from_yaml(yaml_path)
        with transaction(db):
            mirror_profiles(db, profiles)
        rows = db.execute("select id, type, auth_state from source_profiles order by id").fetchall()
    assert [row["id"] for row in rows] == ["nccl-releases", "private-github"]
    assert rows[0]["auth_state"] == "ready"
    assert rows[1]["auth_state"] == "needs_auth_config"


def test_yaml_profile_extra_config_is_persisted_for_fetchers(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: nccl-blog
    name: NCCL blog
    type: rss
    target_domain: ai_infra
    url: https://developer.nvidia.com/blog/tag/nccl/feed/
    trust_level: trusted
    schedule: weekly
    auto_ingest: true
    auth_required: false
    topic: NCCL blog
    fetch_article_body: true
    include_keywords:
      - NCCL
      - GPUDirect
""",
        encoding="utf-8",
    )
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        row = db.execute("select config_json from source_profiles where id = 'nccl-blog'").fetchone()

    assert row["config_json"] == '{"fetch_article_body": true, "include_keywords": ["NCCL", "GPUDirect"]}'


@pytest.mark.parametrize("key", ["auto_ingest", "auth_required", "enabled"])
def test_yaml_profile_boolean_fields_must_be_bool(tmp_path, key):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        f"""
sources:
  - id: bad-bool-source
    name: Bad boolean source
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: daily
    auto_ingest: true
    auth_required: false
    topic: bad boolean audit
    {key}: "false"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=f"profile bad-bool-source key {key} must be a boolean"):
        load_profiles_from_yaml(yaml_path)


def test_duplicate_yaml_source_ids_raise_value_error(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: duplicate-source
    name: First source
    type: web
    target_domain: ai_infra
    url: https://example.com/first
    trust_level: trusted
    schedule: daily
    auto_ingest: true
    auth_required: false
    topic: first duplicate
  - id: duplicate-source
    name: Second source
    type: web
    target_domain: ai_infra
    url: https://example.com/second
    trust_level: trusted
    schedule: daily
    auto_ingest: false
    auth_required: false
    topic: second duplicate
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate source id: duplicate-source"):
        load_profiles_from_yaml(yaml_path)


def test_yaml_profile_target_domain_must_be_single_segment(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: bad-domain-source
    name: Bad domain source
    type: web
    target_domain: team/ai
    url: https://example.com
    trust_level: trusted
    schedule: daily
    auto_ingest: true
    auth_required: false
    topic: bad domain audit
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid domain"):
        load_profiles_from_yaml(yaml_path)


def test_mirror_profiles_validates_boolean_fields_for_direct_calls(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    profile = load_profiles_from_yaml(tmp_path / "missing.yaml")
    assert profile == []

    bad_profile = {
        "id": "direct-bad-bool",
        "name": "Direct bad boolean",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://example.com",
        "trust_level": "trusted",
        "schedule": "daily",
        "auto_ingest": "false",
        "auth_required": False,
        "topic": "direct boolean validation",
    }
    with open_db(settings.database_path) as db:
        migrate(db)
        with pytest.raises(ValueError, match="profile direct-bad-bool key auto_ingest must be a boolean"):
            mirror_profiles(db, [bad_profile])


def test_mirror_profiles_validates_target_domain_for_direct_calls(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    bad_profile = {
        "id": "direct-bad-domain",
        "name": "Direct bad domain",
        "type": "web",
        "target_domain": "../ai",
        "url": "https://example.com",
        "trust_level": "trusted",
        "schedule": "daily",
        "auto_ingest": True,
        "auth_required": False,
        "topic": "direct domain validation",
    }
    with open_db(settings.database_path) as db:
        migrate(db)
        with pytest.raises(ValueError, match="Invalid domain"):
            mirror_profiles(db, [bad_profile])


def test_sources_endpoint_projects_safe_fields_and_booleans(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    settings.resolved_state_dir.mkdir(parents=True)
    settings.sources_yaml_path.write_text(PROFILE_YAML, encoding="utf-8")

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/sources")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["auto_ingest"] is True
    assert data[0]["auth_required"] is False
    assert data[0]["baseline_on_first_run"] is False
    assert data[0]["enabled"] is True
    assert "auth_method" not in data[1]
    assert "auth_ref" not in data[1]
    assert set(data[0]) == {
        "id",
        "name",
        "type",
        "target_domain",
        "url",
        "trust_level",
        "schedule",
        "auto_ingest",
        "auth_required",
        "baseline_on_first_run",
        "auth_state",
        "topic",
        "enabled",
        "last_run_at",
        "last_run_status",
    }


def test_removed_yaml_profiles_are_disabled(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(PROFILE_YAML, encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))

        yaml_path.write_text(
            """
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
    topic: NCCL release history
""",
            encoding="utf-8",
        )
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        rows = {
            row["id"]: row["enabled"]
            for row in db.execute("select id, enabled from source_profiles order by id")
        }

    assert rows == {"nccl-releases": 1, "private-github": 0}


def test_auth_state_is_preserved_until_auth_ref_changes(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(PROFILE_YAML, encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        db.execute("update source_profiles set auth_state = 'auth_failed' where id = 'private-github'")
        db.commit()

        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        unchanged = db.execute(
            "select auth_state from source_profiles where id = 'private-github'"
        ).fetchone()

        yaml_path.write_text(PROFILE_YAML.replace("GITHUB_TOKEN", "NEW_GITHUB_TOKEN"), encoding="utf-8")
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        changed = db.execute(
            "select auth_state, auth_ref from source_profiles where id = 'private-github'"
        ).fetchone()

    assert unchanged["auth_state"] == "auth_failed"
    assert changed["auth_state"] == "needs_auth_config"
    assert changed["auth_ref"] == "NEW_GITHUB_TOKEN"


def test_mirror_profiles_uses_caller_owned_transaction(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(PROFILE_YAML, encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        try:
            with transaction(db):
                mirror_profiles(db, load_profiles_from_yaml(yaml_path))
                raise RuntimeError("rollback")
        except RuntimeError:
            pass

        count = db.execute("select count(*) as count from source_profiles").fetchone()["count"]

    assert count == 0


def test_importing_main_does_not_create_default_database(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("crawler_workbench.main", None)

    module = importlib.import_module("crawler_workbench.main")
    importlib.reload(module)

    assert not (tmp_path / ".personal-wiki-workbench" / "workbench.sqlite3").exists()
