from __future__ import annotations

import pytest

from crawler_workbench.db import migrate, open_db
from crawler_workbench.discovery import (
    accept_candidate,
    extract_accelerator_candidates,
    list_candidates,
    reject_candidate,
    upsert_candidates,
)
from crawler_workbench.fetchers.base import FetchResult
from crawler_workbench.settings import Settings


DISCOVERY_PROFILE = {
    "id": "compute-accelerator-discovery-nvidia-products",
    "name": "NVIDIA accelerator discovery",
    "type": "web",
    "target_domain": "ai_infra",
    "url": "https://www.nvidia.com/en-us/data-center/products/",
    "trust_level": "trusted",
    "schedule": "monthly",
    "auto_ingest": False,
    "auth_required": False,
    "run_policy": "scheduled",
    "topic": "NVIDIA accelerator product discovery",
    "discovery_mode": "accelerator_models",
    "extract_mode": "discovery_index",
    "vendor_hint": "nvidia",
    "accelerator_scope": ["gpu"],
}


def _insert_discovery_profile(db):
    db.execute(
        """
        insert into source_profiles (
          id, name, type, target_domain, url, trust_level, schedule,
          auto_ingest, auth_required, run_policy, auth_state, config_json, topic, enabled
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
          'scheduled',
          'ready',
          '{"discovery_mode": "accelerator_models", "extract_mode": "discovery_index", "vendor_hint": "nvidia", "accelerator_scope": ["gpu"]}',
          'NVIDIA accelerator product discovery',
          1
        )
        """
    )


def test_extract_accelerator_candidates_from_index_text():
    result = FetchResult(
        canonical_url="https://www.nvidia.com/en-us/data-center/products/",
        title="NVIDIA data center products",
        content="# NVIDIA data center products\nNVIDIA H300 GPU accelerator now available.\nLegacy H200 remains listed.",
        content_type="text/html",
        metadata={"source_url": "https://www.nvidia.com/en-us/data-center/products/"},
    )

    candidates = extract_accelerator_candidates(DISCOVERY_PROFILE, [result])

    assert [candidate.model_name for candidate in candidates] == ["H300", "H200"]
    assert candidates[0].vendor == "nvidia"
    assert candidates[0].scope == "gpu"
    assert candidates[0].source_url == "https://www.nvidia.com/en-us/data-center/products/"
    assert "H300 GPU accelerator" in candidates[0].evidence_text
    assert candidates[0].confidence >= 0.7


def test_upsert_candidates_deduplicates_and_strengthens_existing_rows(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_discovery_profile(db)
        db.commit()
        result = FetchResult(
            canonical_url="https://www.nvidia.com/en-us/data-center/products/",
            title="NVIDIA products",
            content="NVIDIA H300 GPU accelerator",
            content_type="text/html",
            metadata={"source_url": "https://www.nvidia.com/en-us/data-center/products/"},
        )
        candidates = extract_accelerator_candidates(DISCOVERY_PROFILE, [result])

        first = upsert_candidates(db, DISCOVERY_PROFILE, candidates)
        candidates[0].confidence = 0.95
        candidates[0].evidence_text = "NVIDIA H300 GPU accelerator with stronger official evidence"
        second = upsert_candidates(db, DISCOVERY_PROFILE, candidates)
        rows = list_candidates(db)

    assert first == {"created": 1, "updated": 0, "unchanged": 0}
    assert second == {"created": 0, "updated": 1, "unchanged": 0}
    assert len(rows) == 1
    assert rows[0]["model_name"] == "H300"
    assert rows[0]["confidence"] == 0.95
    assert rows[0]["status"] == "pending"


def test_reject_candidate_marks_rejected_without_creating_source(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_discovery_profile(db)
        db.commit()
        candidates = extract_accelerator_candidates(
            DISCOVERY_PROFILE,
            [
                FetchResult(
                    canonical_url="https://www.nvidia.com/en-us/data-center/products/",
                    title="NVIDIA products",
                    content="NVIDIA H300 GPU accelerator",
                    content_type="text/html",
                )
            ],
        )
        upsert_candidates(db, DISCOVERY_PROFILE, candidates)
        candidate_id = list_candidates(db)[0]["id"]

        rejected = reject_candidate(db, candidate_id)
        source = db.execute("select 1 from source_profiles where id = 'compute-accelerators-nvidia-h300'").fetchone()

    assert rejected["status"] == "rejected"
    assert source is None


def test_accept_candidate_creates_one_shot_source(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_discovery_profile(db)
        db.commit()
        candidates = extract_accelerator_candidates(
            DISCOVERY_PROFILE,
            [
                FetchResult(
                    canonical_url="https://www.nvidia.com/en-us/data-center/products/",
                    title="NVIDIA products",
                    content="NVIDIA H300 GPU accelerator",
                    content_type="text/html",
                    metadata={"source_url": "https://www.nvidia.com/en-us/data-center/products/"},
                )
            ],
        )
        upsert_candidates(db, DISCOVERY_PROFILE, candidates)
        candidate_id = list_candidates(db)[0]["id"]

        accepted = accept_candidate(
            db,
            candidate_id,
            {
                "source_id": "compute-accelerators-nvidia-h300",
                "name": "NVIDIA H300 accelerator specs",
                "url": "https://www.nvidia.com/en-us/data-center/h300/",
                "scope": ["gpu"],
                "source_rank": "S1",
            },
        )
        source = db.execute(
            "select id, schedule, run_policy, auto_ingest, config_json from source_profiles where id = ?",
            ("compute-accelerators-nvidia-h300",),
        ).fetchone()

    assert accepted["status"] == "accepted"
    assert accepted["accepted_source_id"] == "compute-accelerators-nvidia-h300"
    assert source["schedule"] == "monthly"
    assert source["run_policy"] == "once"
    assert source["auto_ingest"] == 0
    assert '"accelerator_scope": ["gpu"]' in source["config_json"]


def test_accept_candidate_rejects_unsafe_source_id(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        _insert_discovery_profile(db)
        db.commit()
        upsert_candidates(
            db,
            DISCOVERY_PROFILE,
            extract_accelerator_candidates(
                DISCOVERY_PROFILE,
                [
                    FetchResult(
                        canonical_url="https://www.nvidia.com/en-us/data-center/products/",
                        title="NVIDIA products",
                        content="NVIDIA H300 GPU accelerator",
                        content_type="text/html",
                    )
                ],
            ),
        )
        candidate_id = list_candidates(db)[0]["id"]

        with pytest.raises(ValueError, match="Invalid source id"):
            accept_candidate(
                db,
                candidate_id,
                {
                    "source_id": "../bad",
                    "name": "bad",
                    "url": "https://example.com/bad",
                    "scope": ["gpu"],
                    "source_rank": "S1",
                },
            )
