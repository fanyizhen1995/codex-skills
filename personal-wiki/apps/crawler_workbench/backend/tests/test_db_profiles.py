import importlib
import json
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
import pytest

from crawler_workbench.db import connect, migrate, open_db, transaction
from crawler_workbench.main import create_app
from crawler_workbench.profiles import load_profiles_from_yaml, mirror_profiles
from crawler_workbench.source_snapshot import (
    build_source_profile_snapshot,
    source_profile_snapshot_db_rows,
    write_source_profile_snapshot,
)
from crawler_workbench.settings import Settings
from scripts.harness_loop_governance import validate_source_profile_snapshot


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
    assert "wiki_search_index_state" in tables


def test_schema_migration_adds_search_index_source_count_to_existing_database(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        db.execute(
            """
            create table wiki_search_index_state (
              domain text primary key,
              source_mtime real not null,
              indexed_at text not null default current_timestamp
            )
            """
        )
        db.commit()

        migrate(db)
        columns = {row["name"] for row in db.execute("pragma table_info(wiki_search_index_state)").fetchall()}

    assert "source_count" in columns


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


def test_schema_migration_adds_run_policy_and_candidates_to_existing_database(tmp_path):
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
              baseline_on_first_run integer not null default 0,
              auth_state text not null default 'ready',
              auth_method text,
              auth_ref text,
              config_json text not null default '{}',
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
        profile_columns = {row["name"] for row in db.execute("pragma table_info(source_profiles)").fetchall()}
        candidate_columns = {
            row["name"] for row in db.execute("pragma table_info(accelerator_candidates)").fetchall()
        }

    assert "run_policy" in profile_columns
    assert {
        "id",
        "vendor",
        "model_name",
        "normalized_model",
        "scope",
        "source_profile_id",
        "source_url",
        "evidence_url",
        "evidence_text",
        "confidence",
        "status",
        "accepted_source_id",
    } <= candidate_columns


def test_schema_migration_recovers_legacy_dirty_baseline_failures(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        db.execute(
            """
            insert into source_profiles (
              id, name, type, target_domain, url, trust_level, schedule,
              auto_ingest, auth_required, topic
            )
            values ('src', 'Source', 'web', 'ai_infra', 'https://example.com', 'trusted', 'manual', 1, 0, 'topic')
            """
        )
        baseline_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values ('src', 'ai_infra', 'failed', 'low', 'baseline dirty paths include files outside the ingest task')
            """
        ).lastrowid
        real_failure_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values ('src', 'ai_infra', 'failed', 'low', 'validation failed')
            """
        ).lastrowid
        db.commit()

        migrate(db)

        rows = {
            row["id"]: row
            for row in db.execute(
                "select id, status, reason from ingest_tasks where id in (?, ?)",
                (baseline_task_id, real_failure_task_id),
            ).fetchall()
        }

    assert rows[baseline_task_id]["status"] == "approved"
    assert rows[baseline_task_id]["reason"] == "waiting for clean git baseline before automatic retry"
    assert rows[real_failure_task_id]["status"] == "failed"
    assert rows[real_failure_task_id]["reason"] == "validation failed"


def test_source_profile_snapshot_exports_non_sensitive_manifest_and_detects_drift(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    settings.resolved_state_dir.mkdir(parents=True)
    settings.sources_yaml_path.write_text(PROFILE_YAML, encoding="utf-8")
    with open_db(settings.database_path) as db:
        migrate(db)
        mirror_profiles(db, load_profiles_from_yaml(settings.sources_yaml_path))

        snapshot = build_source_profile_snapshot(db, domain="ai_infra", run_id="ai-infra-loop-governance-dev")
        db_rows = source_profile_snapshot_db_rows(db, domain="ai_infra")
        findings = validate_source_profile_snapshot(snapshot, db_rows)
        snapshot_path = write_source_profile_snapshot(
            settings.repo_root,
            db,
            domain="ai_infra",
            run_id="ai-infra-loop-governance-dev",
        )

        db.execute("update source_profiles set schedule = 'weekly' where id = 'private-github'")
        stale_findings = validate_source_profile_snapshot(snapshot, source_profile_snapshot_db_rows(db, domain="ai_infra"))

    assert findings == []
    assert snapshot["schema_version"] == 1
    assert snapshot["run_id"] == "ai-infra-loop-governance-dev"
    assert snapshot["record_counts"] == {"channels": 2, "sources": 2}
    serialized = json.dumps(snapshot, ensure_ascii=False)
    assert "GITHUB_TOKEN" not in serialized
    assert "auth_ref" not in serialized
    assert "auth_method" not in serialized
    assert snapshot_path == tmp_path / "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
    assert snapshot_path.exists()
    assert any("sources[1].schedule" in finding and "weekly" in finding for finding in stale_findings)


def test_schema_migration_normalizes_legacy_dirty_baseline_approved_reasons(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        db.execute(
            """
            insert into source_profiles (
              id, name, type, target_domain, url, trust_level, schedule,
              auto_ingest, auth_required, topic
            )
            values ('src', 'Source', 'web', 'ai_infra', 'https://example.com', 'trusted', 'manual', 1, 0, 'topic')
            """
        )
        task_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values ('src', 'ai_infra', 'approved', 'low', 'baseline dirty paths include files outside the ingest task')
            """
        ).lastrowid
        intermediate_task_id = db.execute(
            """
            insert into ingest_tasks (source_id, target_domain, status, risk_level, reason)
            values ('src', 'ai_infra', 'approved', 'low', 'ready to retry after dirty baseline cleanup')
            """
        ).lastrowid
        db.commit()

        migrate(db)

        rows = {
            row["id"]: row
            for row in db.execute(
                "select id, status, reason from ingest_tasks where id in (?, ?)",
                (task_id, intermediate_task_id),
            ).fetchall()
        }

    assert rows[task_id]["status"] == "approved"
    assert rows[task_id]["reason"] == "waiting for clean git baseline before automatic retry"
    assert rows[intermediate_task_id]["status"] == "approved"
    assert rows[intermediate_task_id]["reason"] == "waiting for clean git baseline before automatic retry"


def test_accelerator_candidates_are_unique_by_effective_evidence_url(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        db.execute(
            """
            insert into source_profiles (
              id, name, type, target_domain, url, trust_level, schedule,
              auto_ingest, auth_required, topic
            )
            values (
              'compute-accelerator-discovery-nvidia-products',
              'NVIDIA accelerator discovery',
              'web',
              'ai_infra',
              'https://www.nvidia.com/en-us/data-center/products/',
              'trusted',
              'monthly',
              0,
              0,
              'NVIDIA accelerator product discovery'
            )
            """
        )
        db.execute(
            """
            insert into accelerator_candidates (
              vendor, model_name, normalized_model, scope, source_profile_id,
              source_url, evidence_url, evidence_text, confidence
            )
            values (
              'nvidia',
              'H300',
              'h300',
              'gpu',
              'compute-accelerator-discovery-nvidia-products',
              'https://www.nvidia.com/en-us/data-center/products/',
              null,
              'NVIDIA H300 GPU accelerator',
              0.8
            )
            """
        )

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                insert into accelerator_candidates (
                  vendor, model_name, normalized_model, scope, source_profile_id,
                  source_url, evidence_url, evidence_text, confidence
                )
                values (
                  'nvidia',
                  'H300',
                  'h300',
                  'gpu',
                  'compute-accelerator-discovery-nvidia-products',
                  'https://www.nvidia.com/en-us/data-center/products/',
                  null,
                  'Duplicate NVIDIA H300 GPU accelerator',
                  0.7
                )
                """
            )


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


def test_yaml_profile_accepts_compute_accelerator_metadata(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: compute-accelerators-nvidia-h200
    name: NVIDIA H200 accelerator specs
    type: web
    target_domain: ai_infra
    url: https://www.nvidia.com/en-us/data-center/h200/
    trust_level: trusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: NVIDIA H200 accelerator specs
    source_rank: S1
    accelerator_scope:
      - gpu
    extract_mode: specs_candidate
    vendor_hint: nvidia
    auto_resolve: false
""",
        encoding="utf-8",
    )
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        row = db.execute(
            "select config_json from source_profiles where id = 'compute-accelerators-nvidia-h200'"
        ).fetchone()

    assert row["config_json"] == (
        '{"accelerator_scope": ["gpu"], "auto_resolve": false, '
        '"extract_mode": "specs_candidate", "source_rank": "S1", "vendor_hint": "nvidia"}'
    )


def test_yaml_profile_accepts_run_policy_and_discovery_metadata(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: compute-accelerator-discovery-nvidia-products
    name: NVIDIA accelerator discovery
    type: web
    target_domain: ai_infra
    url: https://www.nvidia.com/en-us/data-center/products/
    trust_level: trusted
    schedule: monthly
    auto_ingest: false
    auth_required: false
    topic: NVIDIA accelerator product discovery
    run_policy: scheduled
    discovery_mode: accelerator_models
    extract_mode: discovery_index
    vendor_hint: nvidia
    accelerator_scope:
      - gpu
    include_patterns:
      - H[0-9]{3}
""",
        encoding="utf-8",
    )
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        row = db.execute(
            "select run_policy, config_json from source_profiles where id = 'compute-accelerator-discovery-nvidia-products'"
        ).fetchone()

    assert row["run_policy"] == "scheduled"
    assert row["config_json"] == (
        '{"accelerator_scope": ["gpu"], "discovery_mode": "accelerator_models", '
        '"extract_mode": "discovery_index", "include_patterns": ["H[0-9]{3}"], "vendor_hint": "nvidia"}'
    )


def test_yaml_profile_defaults_run_policy_to_scheduled(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(PROFILE_YAML, encoding="utf-8")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        with transaction(db):
            mirror_profiles(db, load_profiles_from_yaml(yaml_path))
        rows = db.execute("select id, run_policy from source_profiles order by id").fetchall()

    assert {row["id"]: row["run_policy"] for row in rows} == {
        "nccl-releases": "scheduled",
        "private-github": "scheduled",
    }


def test_yaml_profile_rejects_invalid_run_policy(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: bad-run-policy
    name: Bad run policy
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: daily
    auto_ingest: false
    auth_required: false
    topic: bad run policy
    run_policy: forever
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid run_policy"):
        load_profiles_from_yaml(yaml_path)


def test_yaml_profile_rejects_discovery_profile_run_policy_once(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: compute-accelerator-discovery-once
    name: NVIDIA accelerator discovery
    type: web
    target_domain: ai_infra
    url: https://www.nvidia.com/en-us/data-center/products/
    trust_level: trusted
    schedule: monthly
    auto_ingest: false
    auth_required: false
    topic: NVIDIA accelerator product discovery
    run_policy: once
    discovery_mode: accelerator_models
    extract_mode: discovery_index
    vendor_hint: nvidia
    accelerator_scope:
      - gpu
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="discovery profiles require run_policy: scheduled"):
        load_profiles_from_yaml(yaml_path)


def test_accelerator_profiles_use_once_policy_and_discovery_profiles_are_monthly():
    import yaml

    config_path = Path(__file__).parents[2] / "config" / "sources.example.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in data["sources"]}
    accelerator_sources = [
        source
        for source in sources.values()
        if source["id"].startswith("compute-accelerators-")
        and source.get("extract_mode") == "specs_candidate"
    ]
    discovery_sources = [
        source
        for source in sources.values()
        if source.get("discovery_mode") == "accelerator_models"
    ]
    expected_discovery_ids = {
        "compute-accelerator-discovery-nvidia-products",
        "compute-accelerator-discovery-amd-instinct",
        "compute-accelerator-discovery-intel-gaudi",
        "compute-accelerator-discovery-huawei-ascend",
        "compute-accelerator-discovery-cambricon-products",
        "compute-accelerator-discovery-kunlunxin-products",
        "compute-accelerator-discovery-metax-products",
        "compute-accelerator-discovery-moore-threads-products",
        "compute-accelerator-discovery-biren-products",
        "compute-accelerator-discovery-iluvatar-products",
        "compute-accelerator-discovery-enflame-products",
        "compute-accelerator-discovery-aws-ec2-accelerators",
        "compute-accelerator-discovery-google-cloud-tpu-docs",
    }

    assert accelerator_sources
    assert expected_discovery_ids <= {source["id"] for source in discovery_sources}
    assert all(source.get("run_policy") == "once" for source in accelerator_sources)
    assert all(source["schedule"] == "monthly" for source in discovery_sources)
    assert all(source.get("run_policy") == "scheduled" for source in discovery_sources)
    assert all(source["extract_mode"] == "discovery_index" for source in discovery_sources)
    assert all(source["auto_ingest"] is False for source in discovery_sources)
    assert all(source["auth_required"] is False for source in discovery_sources)
    assert all(source.get("accelerator_scope") for source in discovery_sources)
    discovered_scopes = {
        scope
        for source in discovery_sources
        for scope in source.get("accelerator_scope", [])
    }
    assert {"gpu", "npu", "tpu", "dpu", "ipu", "fpga", "dsa", "ai_asic"} <= discovered_scopes


def test_accelerator_discovery_profiles_use_reachable_product_indexes():
    import yaml

    config_path = Path(__file__).parents[2] / "config" / "sources.example.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in data["sources"]}

    assert sources["compute-accelerator-discovery-biren-products"]["url"] == "https://www.birentech.com/"
    assert sources["compute-accelerator-discovery-enflame-products"]["url"] == "https://www.enflame-tech.com/"
    assert (
        sources["compute-accelerator-discovery-kunlunxin-products"]["url"]
        == "https://www.kunlunxin.com/wp-sitemap-posts-product-1.xml"
    )
    assert (
        sources["compute-accelerator-discovery-intel-dsa-docs"]["url"]
        == "https://www.intel.com/content/www/us/en/content-details/671116/intel-data-streaming-accelerator-architecture-specification.html"
    )
    assert (
        sources["compute-accelerators-microsoft-maia-200"]["url"]
        == "https://techcommunity.microsoft.com/blog/azureinfrastructureblog/deep-dive-into-the-maia-200-architecture/4489312"
    )


def test_yaml_profile_rejects_invalid_accelerator_scope(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: bad-accelerator-scope
    name: Bad accelerator scope
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: bad accelerator scope
    source_rank: S1
    accelerator_scope:
      - quantum
    extract_mode: specs_candidate
    auto_resolve: false
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid accelerator_scope"):
        load_profiles_from_yaml(yaml_path)


def test_yaml_profile_rejects_non_string_accelerator_scope_entries(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: bad-accelerator-scope-entry
    name: Bad accelerator scope entry
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: bad accelerator scope entry
    source_rank: S1
    accelerator_scope:
      - kind: gpu
    extract_mode: specs_candidate
    auto_resolve: false
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="accelerator_scope entries must be strings"):
        load_profiles_from_yaml(yaml_path)


def test_yaml_profile_rejects_s5_auto_resolve(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: bad-s5-auto-resolve
    name: Bad S5 auto resolve
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: untrusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: bad S5 auto resolve
    source_rank: S5
    accelerator_scope:
      - gpu
    extract_mode: specs_candidate
    auto_resolve: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="S5 profiles cannot auto_resolve"):
        load_profiles_from_yaml(yaml_path)


@pytest.mark.parametrize(
    ("extra_yaml", "message"),
    [
        ("source_rank: S6", "invalid source_rank"),
        ("extract_mode: full_extract", "invalid extract_mode"),
        ('auto_resolve: "false"', "auto_resolve must be a boolean"),
    ],
)
def test_yaml_profile_rejects_invalid_accelerator_metadata(tmp_path, extra_yaml, message):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        f"""
sources:
  - id: bad-accelerator-metadata
    name: Bad accelerator metadata
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: weekly
    auto_ingest: false
    auth_required: false
    topic: bad accelerator metadata
    source_rank: S1
    accelerator_scope:
      - gpu
    extract_mode: specs_candidate
    auto_resolve: false
    {extra_yaml}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=message):
        load_profiles_from_yaml(yaml_path)


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


def test_yaml_profile_source_id_must_be_single_segment(tmp_path):
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        """
sources:
  - id: ../bad-source
    name: Bad source id
    type: web
    target_domain: ai_infra
    url: https://example.com
    trust_level: trusted
    schedule: daily
    auto_ingest: true
    auth_required: false
    topic: bad source id audit
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid source id"):
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


def test_mirror_profiles_validates_source_id_for_direct_calls(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    bad_profile = {
        "id": "../direct-bad-source",
        "name": "Direct bad source id",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://example.com",
        "trust_level": "trusted",
        "schedule": "daily",
        "auto_ingest": True,
        "auth_required": False,
        "topic": "direct source id validation",
    }
    with open_db(settings.database_path) as db:
        migrate(db)
        with pytest.raises(ValueError, match="Invalid source id"):
            mirror_profiles(db, [bad_profile])


def test_mirror_profiles_validates_accelerator_metadata_for_direct_calls(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    bad_profile = {
        "id": "direct-bad-accelerator-metadata",
        "name": "Direct bad accelerator metadata",
        "type": "web",
        "target_domain": "ai_infra",
        "url": "https://example.com",
        "trust_level": "trusted",
        "schedule": "weekly",
        "auto_ingest": False,
        "auth_required": False,
        "topic": "direct accelerator metadata validation",
        "source_rank": "S1",
        "accelerator_scope": [{"kind": "gpu"}],
        "extract_mode": "specs_candidate",
        "auto_resolve": False,
    }
    with open_db(settings.database_path) as db:
        migrate(db)
        with pytest.raises(ValueError, match="accelerator_scope entries must be strings"):
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
    assert data[0]["run_policy"] == "scheduled"
    assert data[0]["enabled"] is True
    assert "auth_method" not in data[1]
    assert "auth_ref" not in data[1]
    assert set(data[0]) == {
        "id",
        "name",
        "type",
        "fetcher_type",
        "target_domain",
        "url",
        "channel_id",
        "channel_name",
        "channel_base_url",
        "channel_auth_state",
        "trust_level",
        "schedule",
        "auto_ingest",
        "auth_required",
        "baseline_on_first_run",
        "run_policy",
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
