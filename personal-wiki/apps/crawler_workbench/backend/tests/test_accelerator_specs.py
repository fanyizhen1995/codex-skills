import json

from crawler_workbench.db import migrate, open_db
from crawler_workbench.fetch_service import run_source_once
from crawler_workbench.fetchers.base import FetchResult
from crawler_workbench.main import create_app
from crawler_workbench.profiles import mirror_profiles
from crawler_workbench.settings import Settings


class StaticFetcher:
    def __init__(self, results):
        self.results = results

    def fetch(self, profile):
        return self.results


def test_schema_migration_adds_accelerator_spec_tables(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        tables = {row["name"] for row in db.execute("select name from sqlite_master where type = 'table'")}

    assert {"accelerator_skus", "accelerator_observations", "accelerator_resolved_specs"} <= tables


def test_extracts_power_and_form_factor_from_official_raw_capture(tmp_path):
    from crawler_workbench.accelerator_specs import extract_observations_from_text

    raw_path = tmp_path / "capture.md"
    raw_path.write_text(
        "# 壁砺 166L\n\n壁砺 166L 产品形态为冷板式液冷 OAM 模组 峰值功耗 600W。",
        encoding="utf-8",
    )

    observations = extract_observations_from_text(
        profile={
            "id": "compute-accelerators-biren-166l",
            "name": "Biren 166L accelerator specs",
            "url": "https://www.birentech.com/product/hardware/166l/",
            "source_rank": "S1",
            "accelerator_scope": ["ai_asic"],
            "vendor_hint": "biren",
            "auto_resolve": False,
        },
        raw_item={
            "id": 7,
            "raw_path": str(raw_path),
            "canonical_url": "https://www.birentech.com/product/hardware/166l/",
        },
        text=raw_path.read_text(encoding="utf-8"),
    )

    assert {(item.field, item.value, item.unit) for item in observations} >= {
        ("tdp", 600, "W"),
        ("form_factor", "冷板式液冷 OAM 模组", "none"),
    }


def test_extracts_clear_memory_network_and_host_interface_fields(tmp_path):
    from crawler_workbench.accelerator_specs import extract_observations_from_text

    text = """
    GPU memory 216GB HBM3e with memory bandwidth 4.8TB/s.
    Network bandwidth 400Gb/s.
    Host interface PCIe Gen5 x16.
    Four QSFP ports are available for deployment flexibility.
    """
    observations = extract_observations_from_text(
        profile={
            "id": "compute-accelerators-example-x1",
            "source_rank": "S1",
            "accelerator_scope": ["gpu"],
            "vendor_hint": "example",
            "auto_resolve": False,
            "extract_mode": "specs_candidate",
        },
        raw_item={"id": 8, "raw_path": str(tmp_path / "capture.md"), "canonical_url": "https://example.com/x1"},
        text=text,
    )

    assert {(item.field, item.value, item.unit) for item in observations} >= {
        ("memory_capacity", 216, "GB"),
        ("memory_bandwidth", 4.8, "TB/s"),
        ("network_bandwidth", 400, "Gb/s"),
        ("host_interface", "PCIe Gen5 x16", "none"),
    }
    assert not any(item.field == "network_bandwidth" and "QSFP" in item.evidence_text for item in observations)


def test_does_not_classify_ambiguous_throughput_as_memory_bandwidth(tmp_path):
    from crawler_workbench.accelerator_specs import extract_observations_from_text

    observations = extract_observations_from_text(
        profile={
            "id": "compute-accelerators-example-x1",
            "source_rank": "S1",
            "accelerator_scope": ["gpu"],
            "vendor_hint": "example",
        },
        raw_item={"id": 8, "raw_path": str(tmp_path / "capture.md"), "canonical_url": "https://example.com/x1"},
        text="Each accelerator supports aggregate throughput of 4.8TB/s across fabric links.",
    )

    assert observations == []


def test_does_not_classify_generic_chinese_bandwidth_as_memory_bandwidth(tmp_path):
    from crawler_workbench.accelerator_specs import extract_observations_from_text

    observations = extract_observations_from_text(
        profile={
            "id": "compute-accelerators-example-x1",
            "source_rank": "S1",
            "accelerator_scope": ["gpu"],
            "vendor_hint": "example",
        },
        raw_item={"id": 8, "raw_path": str(tmp_path / "capture.md"), "canonical_url": "https://example.com/x1"},
        text="芯片间互联带宽 4.8TB/s，适用于多卡扩展。",
    )

    assert not any(item.field == "memory_bandwidth" for item in observations)


def test_upsert_ignores_non_specs_candidate_profiles(tmp_path):
    from crawler_workbench.accelerator_specs import upsert_extracted_specs_for_raw_item

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-example-x1/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("TDP 600W", encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(
            db,
            source_id="compute-accelerators-example-x1",
            config={
                "source_rank": "S1",
                "accelerator_scope": ["gpu"],
                "extract_mode": "snapshot_only",
                "vendor_hint": "example",
                "auto_resolve": False,
            },
        )
        raw_item_id = _insert_raw_item(db, "compute-accelerators-example-x1", raw_path)

        counts = upsert_extracted_specs_for_raw_item(settings, db, raw_item_id)
        observation_count = db.execute("select count(*) as count from accelerator_observations").fetchone()["count"]

    assert counts == {"skus": 0, "observations": 0, "resolved": 0}
    assert observation_count == 0


def test_upsert_extracted_specs_preserves_observation_provenance_and_resolves_s1(tmp_path):
    from crawler_workbench.accelerator_specs import upsert_extracted_specs_for_raw_item

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("# Biren\n\n峰值功耗 600W。", encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(
            db,
            source_id="compute-accelerators-biren-166l",
            config={
                "source_rank": "S1",
                "accelerator_scope": ["ai_asic"],
                "extract_mode": "specs_candidate",
                "vendor_hint": "biren",
                "auto_resolve": False,
            },
        )
        raw_item_id = _insert_raw_item(db, "compute-accelerators-biren-166l", raw_path)

        counts = upsert_extracted_specs_for_raw_item(settings, db, raw_item_id)

        observation = db.execute(
            """
            select id, sku_id, raw_item_id, raw_path, source_profile_id, source_rank, field, value_text, unit,
                   evidence_text, confidence
            from accelerator_observations
            """
        ).fetchone()
        resolved = db.execute(
            """
            select sku_id, field, value_text, unit, source_observation_id
            from accelerator_resolved_specs
            """
        ).fetchone()

    assert counts == {"skus": 1, "observations": 1, "resolved": 1}
    assert dict(observation) | {"confidence_is_positive": observation["confidence"] > 0} == {
        "id": observation["id"],
        "sku_id": "biren-166l",
        "raw_item_id": raw_item_id,
        "raw_path": str(raw_path),
        "source_profile_id": "compute-accelerators-biren-166l",
        "source_rank": "S1",
        "field": "tdp",
        "value_text": "600",
        "unit": "W",
        "evidence_text": "峰值功耗 600W",
        "confidence": observation["confidence"],
        "confidence_is_positive": True,
    }
    assert dict(resolved) == {
        "sku_id": "biren-166l",
        "field": "tdp",
        "value_text": "600",
        "unit": "W",
        "source_observation_id": observation["id"],
    }


def test_s5_observations_do_not_auto_resolve(tmp_path):
    from crawler_workbench.accelerator_specs import upsert_extracted_specs_for_raw_item

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-example-x1/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("memory 256GB HBM3e", encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(
            db,
            source_id="compute-accelerators-example-x1",
            config={
                "source_rank": "S5",
                "accelerator_scope": ["gpu"],
                "extract_mode": "specs_candidate",
                "vendor_hint": "example",
                "auto_resolve": False,
            },
        )
        raw_item_id = _insert_raw_item(db, "compute-accelerators-example-x1", raw_path)

        counts = upsert_extracted_specs_for_raw_item(settings, db, raw_item_id)
        resolved_count = db.execute("select count(*) as count from accelerator_resolved_specs").fetchone()["count"]

    assert counts == {"skus": 1, "observations": 1, "resolved": 0}
    assert resolved_count == 0


def test_conflicting_values_are_not_auto_resolved(tmp_path):
    from crawler_workbench.accelerator_specs import upsert_extracted_specs_for_raw_item

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-example-x1/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("TDP 600W. 峰值功耗 650W。", encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(
            db,
            source_id="compute-accelerators-example-x1",
            config={
                "source_rank": "S1",
                "accelerator_scope": ["gpu"],
                "extract_mode": "specs_candidate",
                "vendor_hint": "example",
                "auto_resolve": False,
            },
        )
        raw_item_id = _insert_raw_item(db, "compute-accelerators-example-x1", raw_path)

        counts = upsert_extracted_specs_for_raw_item(settings, db, raw_item_id)

    assert counts == {"skus": 1, "observations": 2, "resolved": 0}


def test_extract_all_raw_items_and_list_specs(tmp_path):
    from crawler_workbench.accelerator_specs import extract_specs_for_all_raw_items, list_accelerator_specs

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("TDP 600W. PCIe Gen5 x16.", encoding="utf-8")

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(
            db,
            source_id="compute-accelerators-biren-166l",
            config={
                "source_rank": "S1",
                "accelerator_scope": ["ai_asic"],
                "extract_mode": "specs_candidate",
                "vendor_hint": "biren",
                "auto_resolve": False,
            },
        )
        _insert_raw_item(db, "compute-accelerators-biren-166l", raw_path)

        counts = extract_specs_for_all_raw_items(settings, db)
        specs = list_accelerator_specs(db)

    assert counts == {"skus": 1, "observations": 2, "resolved": 2}
    assert len(specs) == 1
    sku = specs[0]
    assert sku | {"observations": [], "resolved_specs": []} == {
        "sku_id": "biren-166l",
        "vendor": "biren",
        "model_name": "166l",
        "normalized_model": "166L",
        "scope": "ai_asic",
        "source_profile_id": "compute-accelerators-biren-166l",
        "source_url": "https://example.com/compute-accelerators-biren-166l",
        "raw_item_id": 1,
        "raw_path": str(raw_path),
        "observations": [],
        "resolved_specs": [],
    }
    observations_by_field = {item["field"]: item for item in sku["observations"]}
    resolved_by_field = {item["field"]: item for item in sku["resolved_specs"]}
    host_observation_id = observations_by_field["host_interface"]["id"]
    tdp_observation_id = observations_by_field["tdp"]["id"]
    assert observations_by_field == {
        "host_interface": {
            "field": "host_interface",
            "id": host_observation_id,
            "value_text": "PCIe Gen5 x16",
            "value_number": None,
            "unit": "none",
            "source_profile_id": "compute-accelerators-biren-166l",
            "source_rank": "S1",
            "raw_item_id": 1,
            "raw_path": str(raw_path),
            "evidence_text": "PCIe Gen5 x16",
            "confidence": 0.9,
        },
        "tdp": {
            "field": "tdp",
            "id": tdp_observation_id,
            "value_text": "600",
            "value_number": 600,
            "unit": "W",
            "source_profile_id": "compute-accelerators-biren-166l",
            "source_rank": "S1",
            "raw_item_id": 1,
            "raw_path": str(raw_path),
            "evidence_text": "TDP 600W",
            "confidence": 0.9,
        },
    }
    assert {
        field: {key: value for key, value in item.items() if key != "source_observation_id"}
        for field, item in resolved_by_field.items()
    } == {
        "host_interface": {
            "field": "host_interface",
            "value_text": "PCIe Gen5 x16",
            "value_number": None,
            "unit": "none",
            "resolved_by": "rule",
            "confidence": "0.9",
            "conflict_status": "clean",
        },
        "tdp": {
            "field": "tdp",
            "value_text": "600",
            "value_number": 600,
            "unit": "W",
            "resolved_by": "rule",
            "confidence": "0.9",
            "conflict_status": "clean",
        },
    }
    assert resolved_by_field["host_interface"]["source_observation_id"] == host_observation_id
    assert resolved_by_field["tdp"]["source_observation_id"] == tdp_observation_id


def test_run_source_once_extracts_specs_after_writing_specs_candidate_raw_item(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    result = FetchResult(
        canonical_url="https://example.com/compute-accelerators-biren-166l",
        title="Biren 166L",
        content="峰值功耗 600W。",
        content_type="text/markdown",
    )

    with open_db(settings.database_path) as db:
        migrate(db)
        mirror_profiles(
            db,
            [
                _source_profile(
                    "compute-accelerators-biren-166l",
                    {
                        "source_rank": "S1",
                        "accelerator_scope": ["ai_asic"],
                        "extract_mode": "specs_candidate",
                        "vendor_hint": "biren",
                    },
                )
            ],
        )

        summary = run_source_once(settings, db, "compute-accelerators-biren-166l", fetcher=StaticFetcher([result]))
        observation = db.execute(
            """
            select accelerator_observations.field, accelerator_observations.value_text
            from accelerator_observations
            join raw_items on raw_items.id = accelerator_observations.raw_item_id
            where raw_items.fetch_run_id = ?
            """,
            (summary["fetch_run_id"],),
        ).fetchone()

    assert summary["changed_count"] == 1
    assert dict(observation) == {"field": "tdp", "value_text": "600"}


def test_accelerator_specs_api_lists_records(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    from fastapi.testclient import TestClient
    from crawler_workbench.accelerator_specs import upsert_extracted_specs_for_raw_item

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("TDP 600W.", encoding="utf-8")
    app = create_app(settings)

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(
            db,
            source_id="compute-accelerators-biren-166l",
            config={
                "source_rank": "S1",
                "accelerator_scope": ["ai_asic"],
                "extract_mode": "specs_candidate",
                "vendor_hint": "biren",
            },
        )
        raw_item_id = _insert_raw_item(db, "compute-accelerators-biren-166l", raw_path)
        upsert_extracted_specs_for_raw_item(settings, db, raw_item_id)
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/accelerator-specs")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["sku_id"] == "biren-166l"
    assert data[0]["observations"][0]["source_profile_id"] == "compute-accelerators-biren-166l"
    assert data[0]["resolved_specs"][0]["field"] == "tdp"


def test_accelerator_specs_extract_api_backfills_existing_raw_items(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    from fastapi.testclient import TestClient

    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("TDP 600W.", encoding="utf-8")
    app = create_app(settings)

    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_source_profile(
            db,
            source_id="compute-accelerators-biren-166l",
            config={
                "source_rank": "S1",
                "accelerator_scope": ["ai_asic"],
                "extract_mode": "specs_candidate",
                "vendor_hint": "biren",
            },
        )
        _insert_raw_item(db, "compute-accelerators-biren-166l", raw_path)
        db.commit()

    with TestClient(app) as client:
        response = client.post("/api/accelerator-specs/extract")

    assert response.status_code == 200
    assert response.json() == {"skus": 1, "observations": 1, "resolved": 1}
    with open_db(settings.database_path) as db:
        resolved_count = db.execute("select count(*) as count from accelerator_resolved_specs").fetchone()["count"]
    assert resolved_count == 1


def _source_profile(source_id: str, config: dict):
    return {
        "id": source_id,
        "name": f"{source_id} specs",
        "type": "web",
        "target_domain": "ai_infra",
        "url": f"https://example.com/{source_id}",
        "trust_level": "trusted",
        "schedule": "manual",
        "auto_ingest": False,
        "auth_required": False,
        "run_policy": "once",
        "topic": f"{source_id} specs",
        "auto_resolve": False,
        **config,
    }


def _insert_source_profile(db, source_id, config):
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, run_policy, auth_state, config_json, topic, enabled
        )
        values (?, ?, 'web', 'ai_infra', ?, 'trusted', 'manual', 0, 0, 'once', 'ready', ?, ?, 1)
        """,
        (
            source_id,
            f"{source_id} specs",
            f"https://example.com/{source_id}",
            json.dumps(config, ensure_ascii=False, sort_keys=True),
            f"{source_id} specs",
        ),
    )


def _insert_raw_item(db, source_id, raw_path):
    return db.execute(
        """
        insert into raw_items (
          source_id, target_domain, canonical_url, raw_path, title, content_hash, content_bytes, metadata_json
        )
        values (?, 'ai_infra', ?, ?, 'Spec', 'hash', 10, '{}')
        """,
        (source_id, f"https://example.com/{source_id}", str(raw_path)),
    ).lastrowid
