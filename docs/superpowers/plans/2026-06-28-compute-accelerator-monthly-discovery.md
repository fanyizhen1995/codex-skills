# Compute Accelerator Monthly Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add monthly accelerator model discovery while making known model source captures one-shot after successful evidence capture.

**Architecture:** Extend source profiles with a `run_policy` field, add an accelerator candidate table/service, run discovery as a scheduled fetch post-process, and expose candidates through the existing FastAPI/React workbench. Known concrete accelerator profiles become `run_policy: once`; discovery index profiles remain monthly scheduled and only produce review candidates.

**Tech Stack:** Python 3, SQLite, FastAPI, pytest, React, TypeScript, Vite/Vitest, YAML source profiles.

---

## File Map

- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`: add persistent fields/tables.
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`: add migration columns for existing DBs.
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`: validate/store `run_policy` and discovery metadata.
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/scheduler.py`: skip completed `once` sources.
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/discovery.py`: new extraction, candidate upsert, accept/reject service.
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`: call discovery post-processing for discovery profiles.
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`: candidate endpoints and source response field.
- `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`: response/request Pydantic models.
- `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`: profile/schema tests.
- `personal-wiki/apps/crawler_workbench/backend/tests/test_scheduler.py`: split scheduler tests out of `test_api.py` and add `once` behavior.
- `personal-wiki/apps/crawler_workbench/backend/tests/test_discovery.py`: new extractor/service/API tests.
- `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`: mark known accelerator profiles one-shot and add monthly discovery profiles.
- `.personal-wiki-workbench/sources.yaml`: mirror runtime source config for local workbench.
- `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`: add `run_policy` and candidate types.
- `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`: candidate API client helpers.
- `personal-wiki/apps/crawler_workbench/frontend/src/pages/SourcesPage.tsx`: show run policy and candidate review queue.
- `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`: candidate UI/API tests.
- `docs/harness/evaluator-scenarios/compute-accelerator-monthly-discovery-01.json`: evaluator scenario.
- `tasks.json`, `progress.md`: update status/evidence after implementation.

## Task 1: Backend Profile And Schema Support

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`

- [ ] **Step 1: Write failing profile/schema tests**

Add these tests to `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`:

```python
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
```

Extend `test_sources_endpoint_projects_safe_fields_and_booleans` so the expected key set includes `"run_policy"` and assert `data[0]["run_policy"] == "scheduled"`.

- [ ] **Step 2: Run tests to verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_db_profiles.py::test_schema_migration_adds_run_policy_and_candidates_to_existing_database tests/test_db_profiles.py::test_yaml_profile_accepts_run_policy_and_discovery_metadata tests/test_db_profiles.py::test_yaml_profile_defaults_run_policy_to_scheduled tests/test_db_profiles.py::test_yaml_profile_rejects_invalid_run_policy
```

Expected: FAIL because `run_policy` and `accelerator_candidates` do not exist yet.

- [ ] **Step 3: Implement schema and profile support**

Update `schema.sql`:

```sql
  run_policy text not null default 'scheduled' check (run_policy in ('scheduled', 'once')),
```

Add it to `source_profiles` before `auth_state`.

Add:

```sql
create table if not exists accelerator_candidates (
  id integer primary key autoincrement,
  vendor text not null,
  model_name text not null,
  normalized_model text not null,
  scope text not null,
  source_profile_id text not null references source_profiles(id) on delete cascade,
  source_url text not null,
  evidence_url text,
  evidence_text text not null,
  confidence real not null,
  status text not null default 'pending' check (status in ('pending', 'accepted', 'rejected')),
  accepted_source_id text references source_profiles(id) on delete set null,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  unique(vendor, normalized_model, evidence_url)
);
```

Use `coalesce(evidence_url, source_url)` in service-level lookup because SQLite unique indexes allow multiple `null` values.

Update `db.py` migration:

```python
_ensure_column(connection, "source_profiles", "run_policy", "text not null default 'scheduled'")
```

Update `profiles.py`:

```python
PROFILE_STORAGE_KEYS = REQUIRED_PROFILE_KEYS | {
    "baseline_on_first_run",
    "enabled",
    "auth_method",
    "auth_ref",
    "run_policy",
}

RUN_POLICIES = {"scheduled", "once"}
ACCELERATOR_EXTRACT_MODES = {"specs_candidate", "snapshot_only", "manual_probe", "discovery_index"}
DISCOVERY_MODES = {"accelerator_models"}
DISCOVERY_OPTIONAL_LIST_KEYS = {"include_patterns", "exclude_patterns", "candidate_url_patterns"}
```

Add validation:

```python
def validate_run_policy(profile: dict[str, Any]) -> str:
    profile_id = profile.get("id", "<unknown>")
    run_policy = str(profile.get("run_policy", "scheduled"))
    if run_policy not in RUN_POLICIES:
        raise ValueError(f"profile {profile_id} invalid run_policy: {run_policy}")
    return run_policy
```

Call it from `load_profiles_from_yaml()` and `mirror_profiles()`.

Update accelerator validation so discovery metadata can be present:

```python
if profile.get("discovery_mode") is not None:
    if profile["discovery_mode"] not in DISCOVERY_MODES:
        raise ValueError(f"profile {profile_id} invalid discovery_mode: {profile['discovery_mode']}")
    if profile.get("extract_mode") != "discovery_index":
        raise ValueError(f"profile {profile_id} discovery profiles require extract_mode: discovery_index")
    scopes = profile.get("accelerator_scope")
    if not isinstance(scopes, list) or not scopes:
        raise ValueError(f"profile {profile_id} accelerator_scope must be a non-empty list")
    invalid_scopes = sorted(str(scope) for scope in scopes if scope not in ACCELERATOR_SCOPES)
    if invalid_scopes:
        raise ValueError(f"profile {profile_id} invalid accelerator_scope: {', '.join(invalid_scopes)}")
    for key in DISCOVERY_OPTIONAL_LIST_KEYS:
        if key in profile and (
            not isinstance(profile[key], list) or not all(isinstance(item, str) for item in profile[key])
        ):
            raise ValueError(f"profile {profile_id} {key} must be a list of strings")
    return
```

Update SQL insert/update in `mirror_profiles()` to persist `run_policy`.

Update `schemas.py`:

```python
class SourceProfileResponse(BaseModel):
    ...
    run_policy: str
```

Update `/api/sources` response in `api.py` with `run_policy=row["run_policy"]`.

- [ ] **Step 4: Run tests to verify green**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_db_profiles.py
```

Expected: all tests in `test_db_profiles.py` pass.

- [ ] **Step 5: Commit**

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py \
  personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py
git commit -m "feat(crawler): add accelerator run policy metadata"
```

## Task 2: One-Shot Scheduler Policy

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_scheduler.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/scheduler.py`

- [ ] **Step 1: Move scheduler tests into a focused module**

Move scheduler-only tests and their helpers from `test_api.py` into `test_scheduler.py`:

- `_insert_source_profile`
- tests beginning with `test_scheduler_`

Keep API endpoint tests in `test_api.py`. Adjust imports in both files.

- [ ] **Step 2: Update helper and write failing one-shot tests**

In `test_scheduler.py`, update `_insert_source_profile` to accept `run_policy="scheduled"`:

```python
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
```

Add:

```python
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
```

- [ ] **Step 3: Run tests to verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_scheduler.py::test_scheduler_skips_once_source_after_successful_evidence_capture tests/test_scheduler.py::test_scheduler_runs_once_source_until_successful_capture_exists
```

Expected: the skip test FAILS because scheduler still runs `once` sources.

- [ ] **Step 4: Implement one-shot skip**

In `scheduler.py`, select `run_policy`:

```sql
select id, schedule, next_run_at, run_policy from source_profiles
```

Filter:

```python
due_rows = [
    row
    for row in rows
    if _is_due(row["next_run_at"], now) and not _is_completed_once_source(db, row)
]
```

Add:

```python
def _is_completed_once_source(db, row) -> bool:
    if row["run_policy"] != "once":
        return False
    existing = db.execute(
        """
        select 1
        from fetch_runs
        where source_id = ?
          and status = 'succeeded'
          and (changed_count > 0 or fetched_count > 0)
        limit 1
        """,
        (row["id"],),
    ).fetchone()
    if existing is not None:
        return True
    baseline = db.execute(
        "select 1 from content_versions where source_id = ? limit 1",
        (row["id"],),
    ).fetchone()
    return baseline is not None
```

- [ ] **Step 5: Run scheduler tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_scheduler.py tests/test_api.py
```

Expected: scheduler and API tests pass.

- [ ] **Step 6: Commit**

```bash
git add personal-wiki/apps/crawler_workbench/backend/tests/test_scheduler.py \
  personal-wiki/apps/crawler_workbench/backend/tests/test_api.py \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/scheduler.py
git commit -m "feat(crawler): skip completed one-shot sources"
```

## Task 3: Discovery Candidate Service

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/discovery.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_discovery.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`

- [ ] **Step 1: Write failing extraction and persistence tests**

Create `test_discovery.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_discovery.py
```

Expected: import FAIL because `crawler_workbench.discovery` does not exist.

- [ ] **Step 3: Implement discovery service**

Create `discovery.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import sqlite3
from typing import Any

from .fetchers.base import FetchResult
from .profiles import validate_profile_source_id


MODEL_PATTERNS = [
    re.compile(r"\b(H|B|GB|MI|TPU|Trainium|Inferentia|Gaudi|Atlas|MLU|R|C|S|TG|ZK)\s?-?\d{2,4}[A-Za-z0-9-]*\b", re.I),
]


@dataclass
class AcceleratorCandidate:
    vendor: str
    model_name: str
    normalized_model: str
    scope: str
    source_url: str
    evidence_url: str | None
    evidence_text: str
    confidence: float


def extract_accelerator_candidates(profile: dict[str, Any], results: list[FetchResult]) -> list[AcceleratorCandidate]:
    if profile.get("discovery_mode") != "accelerator_models":
        return []
    vendor = str(profile.get("vendor_hint") or "").strip().lower() or "unknown"
    scope = _scope_from_profile(profile)
    candidates: dict[tuple[str, str], AcceleratorCandidate] = {}
    for result in results:
        source_url = str(result.metadata.get("source_url") or result.canonical_url)
        for match in _model_matches(result.content):
            model = _clean_model(match.group(0))
            normalized = normalize_model(model)
            evidence = _evidence_window(result.content, match.start(), match.end())
            key = (normalized, source_url)
            confidence = _confidence(evidence, profile)
            candidate = AcceleratorCandidate(
                vendor=vendor,
                model_name=model,
                normalized_model=normalized,
                scope=scope,
                source_url=source_url,
                evidence_url=source_url,
                evidence_text=evidence,
                confidence=confidence,
            )
            previous = candidates.get(key)
            if previous is None or candidate.confidence > previous.confidence:
                candidates[key] = candidate
    return list(candidates.values())


def upsert_candidates(db: sqlite3.Connection, profile: dict[str, Any], candidates: list[AcceleratorCandidate]) -> dict[str, int]:
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for candidate in candidates:
        row = db.execute(
            """
            select * from accelerator_candidates
            where vendor = ? and normalized_model = ? and coalesce(evidence_url, source_url) = ?
            """,
            (candidate.vendor, candidate.normalized_model, candidate.evidence_url or candidate.source_url),
        ).fetchone()
        if row is None:
            db.execute(
                """
                insert into accelerator_candidates (
                  vendor, model_name, normalized_model, scope, source_profile_id, source_url,
                  evidence_url, evidence_text, confidence, status
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    candidate.vendor,
                    candidate.model_name,
                    candidate.normalized_model,
                    candidate.scope,
                    profile["id"],
                    candidate.source_url,
                    candidate.evidence_url,
                    candidate.evidence_text,
                    candidate.confidence,
                ),
            )
            counts["created"] += 1
            continue
        if row["status"] == "pending" and (
            float(row["confidence"]) < candidate.confidence or row["evidence_text"] != candidate.evidence_text
        ):
            db.execute(
                """
                update accelerator_candidates
                set model_name = ?, scope = ?, source_url = ?, evidence_url = ?,
                    evidence_text = ?, confidence = ?, updated_at = current_timestamp
                where id = ?
                """,
                (
                    candidate.model_name,
                    candidate.scope,
                    candidate.source_url,
                    candidate.evidence_url,
                    candidate.evidence_text,
                    candidate.confidence,
                    row["id"],
                ),
            )
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
    db.commit()
    return counts
```

Also implement `list_candidates(db)`, `reject_candidate(db, candidate_id)`, `accept_candidate(db, candidate_id, payload)`, `normalize_model`, `_model_matches`, `_clean_model`, `_evidence_window`, `_scope_from_profile`, and `_confidence`.

Acceptance inserts into `source_profiles` directly with `run_policy='once'`, `schedule='monthly'`, `auto_ingest=0`, `auth_required=0`, `auth_state='ready'`, `trust_level='trusted'`, `type='web'`, target domain `ai_infra`, and `config_json` containing:

```python
{
    "source_rank": payload.get("source_rank", "S1"),
    "accelerator_scope": payload["scope"],
    "extract_mode": "specs_candidate",
    "vendor_hint": candidate["vendor"],
    "auto_resolve": False,
}
```

- [ ] **Step 4: Hook discovery post-processing into fetch service**

In `fetch_service.py`, after `results = runner.fetch(profile)` and before iterating content versions, add:

```python
if profile.get("discovery_mode") == "accelerator_models":
    from .discovery import extract_accelerator_candidates, upsert_candidates

    upsert_candidates(db, profile, extract_accelerator_candidates(profile, results))
```

Do not skip normal raw/content-version behavior; the existing hash logic will avoid repeated raw writes for unchanged indexes.

- [ ] **Step 5: Run tests to verify green**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_discovery.py
```

Expected: all discovery tests pass.

- [ ] **Step 6: Commit**

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench/discovery.py \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py \
  personal-wiki/apps/crawler_workbench/backend/tests/test_discovery.py
git commit -m "feat(crawler): add accelerator candidate discovery service"
```

## Task 4: Candidate API

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/tests/test_discovery.py`

- [ ] **Step 1: Write failing API tests**

Append to `test_discovery.py`:

```python
from fastapi.testclient import TestClient
from crawler_workbench.main import create_app


def test_candidates_api_lists_pending_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
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

    with TestClient(app) as client:
        response = client.get("/api/accelerator-candidates")

    assert response.status_code == 200
    assert response.json()[0]["model_name"] == "H300"
    assert response.json()[0]["status"] == "pending"


def test_candidates_api_accepts_candidate_and_creates_source(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
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

    with TestClient(app) as client:
        response = client.post(
            f"/api/accelerator-candidates/{candidate_id}/accept",
            json={
                "source_id": "compute-accelerators-nvidia-h300",
                "name": "NVIDIA H300 accelerator specs",
                "url": "https://www.nvidia.com/en-us/data-center/h300/",
                "scope": ["gpu"],
                "source_rank": "S1",
            },
        )

    assert response.status_code == 200
    assert response.json()["accepted_source_id"] == "compute-accelerators-nvidia-h300"


def test_candidates_api_rejects_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("PW_WORKBENCH_DISABLE_SCHEDULER", "1")
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    app = create_app(settings)
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

    with TestClient(app) as client:
        response = client.post(f"/api/accelerator-candidates/{candidate_id}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
```

- [ ] **Step 2: Run tests to verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_discovery.py::test_candidates_api_lists_pending_candidates tests/test_discovery.py::test_candidates_api_accepts_candidate_and_creates_source tests/test_discovery.py::test_candidates_api_rejects_candidate
```

Expected: FAIL with 404 for missing endpoints.

- [ ] **Step 3: Implement schemas and endpoints**

In `schemas.py`, add:

```python
class AcceleratorCandidateResponse(BaseModel):
    id: int
    vendor: str
    model_name: str
    normalized_model: str
    scope: str
    source_profile_id: str
    source_url: str
    evidence_url: str | None = None
    evidence_text: str
    confidence: float
    status: str
    accepted_source_id: str | None = None
    created_at: str
    updated_at: str


class AcceptAcceleratorCandidateRequest(BaseModel):
    source_id: str
    name: str
    url: str
    scope: list[str]
    source_rank: str = "S1"
```

In `api.py`, import discovery service functions and schemas. Add:

```python
@router.get("/accelerator-candidates", response_model=list[AcceleratorCandidateResponse])
def accelerator_candidates(request: Request) -> list[AcceleratorCandidateResponse]:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        return [AcceleratorCandidateResponse(**row) for row in list_candidates(db)]


@router.post("/accelerator-candidates/{candidate_id}/reject", response_model=AcceleratorCandidateResponse)
def reject_accelerator_candidate(candidate_id: int, request: Request) -> AcceleratorCandidateResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return AcceleratorCandidateResponse(**reject_candidate(db, candidate_id))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/accelerator-candidates/{candidate_id}/accept", response_model=AcceleratorCandidateResponse)
def accept_accelerator_candidate(
    candidate_id: int,
    payload: AcceptAcceleratorCandidateRequest,
    request: Request,
) -> AcceleratorCandidateResponse:
    request.app.state.initialize_database(request.app)
    with open_db(request.app.state.settings.database_path) as db:
        try:
            return AcceleratorCandidateResponse(**accept_candidate(db, candidate_id, payload.model_dump()))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 4: Run API tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_discovery.py tests/test_api.py
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py \
  personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py \
  personal-wiki/apps/crawler_workbench/backend/tests/test_discovery.py
git commit -m "feat(crawler): expose accelerator candidate review api"
```

## Task 5: Frontend Candidate Review UI

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/pages/SourcesPage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Update `App.test.tsx` imports:

```typescript
import {
  acceptAcceleratorCandidate,
  getAcceleratorCandidates,
  getQueue,
  getRuns,
  getSources,
  getWikiMetrics,
  rejectAcceleratorCandidate,
  trustQueueSource,
  validateWiki
} from "./api";
```

Add mocks:

```typescript
getAcceleratorCandidates: vi.fn().mockResolvedValue([]),
acceptAcceleratorCandidate: vi.fn().mockResolvedValue({ id: 1, status: "accepted" }),
rejectAcceleratorCandidate: vi.fn().mockResolvedValue({ id: 1, status: "rejected" }),
```

Add reset logic in `afterEach()`:

```typescript
vi.mocked(getAcceleratorCandidates).mockResolvedValue([]);
vi.mocked(acceptAcceleratorCandidate).mockResolvedValue({ id: 1, status: "accepted" });
vi.mocked(rejectAcceleratorCandidate).mockResolvedValue({ id: 1, status: "rejected" });
```

Add tests:

```typescript
it("shows source run policy and accelerator discovery candidates", async () => {
  vi.mocked(getSources).mockResolvedValue([
    {
      id: "compute-accelerators-nvidia-h200",
      name: "NVIDIA H200 accelerator specs",
      type: "web",
      target_domain: "ai_infra",
      url: "https://www.nvidia.com/en-us/data-center/h200/",
      trust_level: "trusted",
      schedule: "monthly",
      run_policy: "once",
      auto_ingest: false,
      auth_required: false,
      auth_state: "ready",
      topic: "NVIDIA H200 accelerator specifications",
      enabled: true,
      last_run_status: "succeeded"
    }
  ]);
  vi.mocked(getAcceleratorCandidates).mockResolvedValue([
    {
      id: 7,
      vendor: "nvidia",
      model_name: "H300",
      normalized_model: "h300",
      scope: "gpu",
      source_profile_id: "compute-accelerator-discovery-nvidia-products",
      source_url: "https://www.nvidia.com/en-us/data-center/products/",
      evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
      evidence_text: "NVIDIA H300 GPU accelerator now available",
      confidence: 0.85,
      status: "pending",
      created_at: "2026-06-28 01:00:00",
      updated_at: "2026-06-28 01:00:00"
    }
  ]);

  render(<App />);

  fireEvent.click(screen.getAllByText("来源订阅")[0]);

  expect(await screen.findByText("新硬件候选")).toBeInTheDocument();
  expect(screen.getByText("H300")).toBeInTheDocument();
  expect(screen.getByText(/NVIDIA H300 GPU accelerator/)).toBeInTheDocument();
  expect(screen.getByText("一次性")).toBeInTheDocument();
});


it("accepts and rejects accelerator discovery candidates", async () => {
  vi.mocked(getAcceleratorCandidates).mockResolvedValueOnce([
    {
      id: 7,
      vendor: "nvidia",
      model_name: "H300",
      normalized_model: "h300",
      scope: "gpu",
      source_profile_id: "compute-accelerator-discovery-nvidia-products",
      source_url: "https://www.nvidia.com/en-us/data-center/products/",
      evidence_url: "https://www.nvidia.com/en-us/data-center/products/",
      evidence_text: "NVIDIA H300 GPU accelerator now available",
      confidence: 0.85,
      status: "pending",
      created_at: "2026-06-28 01:00:00",
      updated_at: "2026-06-28 01:00:00"
    }
  ]).mockResolvedValueOnce([]);

  render(<App />);

  fireEvent.click(screen.getAllByText("来源订阅")[0]);
  fireEvent.click(await screen.findByRole("button", { name: "接受 H300" }));

  await waitFor(() =>
    expect(acceptAcceleratorCandidate).toHaveBeenCalledWith(7, {
      source_id: "compute-accelerators-nvidia-h300",
      name: "nvidia H300 accelerator specs",
      url: "https://www.nvidia.com/en-us/data-center/products/",
      scope: ["gpu"],
      source_rank: "S1"
    })
  );

  vi.mocked(getAcceleratorCandidates).mockResolvedValueOnce([
    {
      id: 8,
      vendor: "nvidia",
      model_name: "H301",
      normalized_model: "h301",
      scope: "gpu",
      source_profile_id: "compute-accelerator-discovery-nvidia-products",
      source_url: "https://www.nvidia.com/en-us/data-center/products/",
      evidence_text: "NVIDIA H301 GPU accelerator",
      confidence: 0.75,
      status: "pending",
      created_at: "2026-06-28 01:00:00",
      updated_at: "2026-06-28 01:00:00"
    }
  ]).mockResolvedValueOnce([]);

  fireEvent.click(screen.getByRole("button", { name: "刷新来源" }));
  fireEvent.click(await screen.findByRole("button", { name: "拒绝 H301" }));

  await waitFor(() => expect(rejectAcceleratorCandidate).toHaveBeenCalledWith(8));
});
```

- [ ] **Step 2: Run tests to verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test -- --run src/App.test.tsx
```

Expected: FAIL because candidate APIs/types/UI do not exist.

- [ ] **Step 3: Implement frontend types and API**

In `types.ts`, add `run_policy` to `SourceProfile`:

```typescript
run_policy: "scheduled" | "once" | string;
```

Add:

```typescript
export interface AcceleratorCandidate {
  id: number;
  vendor: string;
  model_name: string;
  normalized_model: string;
  scope: string;
  source_profile_id: string;
  source_url: string;
  evidence_url?: string | null;
  evidence_text: string;
  confidence: number;
  status: "pending" | "accepted" | "rejected" | string;
  accepted_source_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AcceptAcceleratorCandidatePayload {
  source_id: string;
  name: string;
  url: string;
  scope: string[];
  source_rank: string;
}
```

In `api.ts`, import the new types and add:

```typescript
export async function getAcceleratorCandidates(): Promise<AcceleratorCandidate[]> {
  return request<AcceleratorCandidate[]>("/accelerator-candidates");
}

export async function acceptAcceleratorCandidate(
  id: number,
  payload: AcceptAcceleratorCandidatePayload
): Promise<AcceleratorCandidate> {
  return request<AcceleratorCandidate>(`/accelerator-candidates/${id}/accept`, { method: "POST", body: payload });
}

export async function rejectAcceleratorCandidate(id: number): Promise<AcceleratorCandidate> {
  return request<AcceleratorCandidate>(`/accelerator-candidates/${id}/reject`, { method: "POST" });
}
```

- [ ] **Step 4: Implement candidate UI on Sources page**

In `SourcesPage.tsx`:

- load `getAcceleratorCandidates()` together with `getSources()`;
- add a refresh button labelled `刷新来源`;
- render a `work-panel` titled `新硬件候选` above source groups;
- show model/vendor/scope/confidence/evidence/source URL;
- add icon buttons with accessible labels `接受 ${candidate.model_name}` and `拒绝 ${candidate.model_name}`;
- default accept payload:

```typescript
{
  source_id: `compute-accelerators-${candidate.vendor}-${candidate.normalized_model}`.toLowerCase(),
  name: `${candidate.vendor} ${candidate.model_name} accelerator specs`,
  url: candidate.evidence_url || candidate.source_url,
  scope: [candidate.scope],
  source_rank: "S1"
}
```

Display `run_policy === "once" ? "一次性" : "定时"` in the source table near the schedule.

- [ ] **Step 5: Run frontend tests and build**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test -- --run src/App.test.tsx src/api.test.ts
npm run build
```

Expected: tests and build pass.

- [ ] **Step 6: Commit**

```bash
git add personal-wiki/apps/crawler_workbench/frontend/src/types.ts \
  personal-wiki/apps/crawler_workbench/frontend/src/api.ts \
  personal-wiki/apps/crawler_workbench/frontend/src/pages/SourcesPage.tsx \
  personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx
git commit -m "feat(crawler): add accelerator candidate review ui"
```

## Task 6: Source Configuration And Evaluator Scenario

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/config/sources.example.yaml`
- Modify: `.personal-wiki-workbench/sources.yaml`
- Create: `docs/harness/evaluator-scenarios/compute-accelerator-monthly-discovery-01.json`
- Modify: `tasks.json`
- Modify: `progress.md`

- [ ] **Step 1: Write failing config test**

Add to `test_db_profiles.py`:

```python
def test_accelerator_profiles_use_once_policy_and_discovery_profiles_are_monthly():
    import yaml

    config_path = Path(__file__).parents[2] / "config" / "sources.example.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in data["sources"]}
    accelerator_sources = [
        source for source in sources.values()
        if source["id"].startswith("compute-accelerators-") and source.get("extract_mode") == "specs_candidate"
    ]
    discovery_sources = [
        source for source in sources.values()
        if source.get("discovery_mode") == "accelerator_models"
    ]

    assert accelerator_sources
    assert discovery_sources
    assert all(source.get("run_policy") == "once" for source in accelerator_sources)
    assert all(source["schedule"] == "monthly" for source in discovery_sources)
    assert all(source.get("run_policy") == "scheduled" for source in discovery_sources)
```

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_db_profiles.py::test_accelerator_profiles_use_once_policy_and_discovery_profiles_are_monthly
```

Expected: FAIL until YAML is updated.

- [ ] **Step 2: Update source YAML**

In both `personal-wiki/apps/crawler_workbench/config/sources.example.yaml` and `.personal-wiki-workbench/sources.yaml`:

- add `run_policy: once` to all concrete `compute-accelerators-*` profiles with `extract_mode: specs_candidate`;
- keep NCCL/SGLang sources unchanged;
- add monthly discovery profiles such as:

```yaml
- id: compute-accelerator-discovery-nvidia-products
  name: NVIDIA accelerator product discovery
  type: web
  target_domain: ai_infra
  url: https://www.nvidia.com/en-us/data-center/products/
  trust_level: trusted
  schedule: monthly
  run_policy: scheduled
  auto_ingest: false
  auth_required: false
  baseline_on_first_run: false
  topic: NVIDIA accelerator product index discovery
  discovery_mode: accelerator_models
  extract_mode: discovery_index
  vendor_hint: nvidia
  accelerator_scope:
  - gpu
  include_patterns:
  - H[0-9]{3}
  - GB[0-9]{3}
```

Add a controlled initial set for NVIDIA, AMD, Intel, Huawei Ascend, Cambricon, Kunlunxin, MetaX, Moore Threads, Biren, Iluvatar, Enflame, AWS EC2 accelerators, and Google Cloud TPU docs. Disable any source that is known to return 403/captcha by setting `enabled: false`.

- [ ] **Step 3: Add evaluator scenario**

Create `docs/harness/evaluator-scenarios/compute-accelerator-monthly-discovery-01.json`:

```json
{
  "task_id": "compute-accelerator-monthly-discovery-01",
  "must_simulate": true,
  "user_scenarios": [
    {
      "scenario_id": "accelerator-monthly-discovery-user-flow",
      "user_goal": "As an ai_infra wiki maintainer, verify that known accelerator model sources are one-shot and new hardware discovery is monthly, candidate-based, and manually accepted.",
      "prerequisites": [
        "The crawler workbench backend and frontend dependencies are available.",
        "The accelerator monthly discovery implementation has been completed.",
        "The source example YAML includes known accelerator model sources and monthly discovery sources."
      ],
      "entrypoint": "bash -lc 'cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py tests/test_scheduler.py tests/test_discovery.py && cd ../frontend && npm test -- --run src/App.test.tsx src/api.test.ts && npm run build && cd /home/fyz/codex-skills && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra'",
      "steps": [
        "Run backend profile, scheduler, and discovery tests.",
        "Run frontend tests for source subscriptions and accelerator candidates.",
        "Build the frontend.",
        "Validate accelerator catalog metadata and the ai_infra wiki domain."
      ],
      "expected_outcomes": [
        "Known compute-accelerators model/spec profiles use run_policy once.",
        "Scheduler skips one-shot sources after a successful evidence capture.",
        "Monthly discovery profiles create or update accelerator candidates instead of creating formal source profiles automatically.",
        "Candidate accept creates a one-shot source; candidate reject does not create a source.",
        "The Sources page exposes run policy and pending accelerator candidates.",
        "Wiki accelerator validation and ai_infra validation pass."
      ],
      "failure_signals": [
        "A known model source remains weekly or monthly scheduled without run_policy once.",
        "A discovery source auto-creates formal source profiles without review.",
        "Candidate deduplication creates repeated rows for the same vendor/model/evidence URL.",
        "The frontend hides candidate evidence or cannot accept/reject candidates.",
        "Backend or frontend tests fail.",
        "Wiki validation fails."
      ],
      "cleanup": [
        "Remove .codex/evaluations/tasks/compute-accelerator-monthly-discovery-01/ if a clean rerun is needed."
      ],
      "automation_hint": "shell"
    }
  ]
}
```

- [ ] **Step 4: Run config/backend validation**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_db_profiles.py tests/test_scheduler.py tests/test_discovery.py
cd /home/fyz/codex-skills
python3 -m json.tool docs/harness/evaluator-scenarios/compute-accelerator-monthly-discovery-01.json >/dev/null
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators
python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```

Expected: all commands pass.

- [ ] **Step 5: Commit**

```bash
git add personal-wiki/apps/crawler_workbench/config/sources.example.yaml \
  .personal-wiki-workbench/sources.yaml \
  docs/harness/evaluator-scenarios/compute-accelerator-monthly-discovery-01.json \
  personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py
git commit -m "chore(crawler): configure monthly accelerator discovery sources"
```

## Task 7: Final Verification, Evaluator, And Progress

**Files:**
- Modify: `tasks.json`
- Modify: `progress.md`

- [ ] **Step 1: Run task verify command**

Run exactly:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py tests/test_scheduler.py tests/test_discovery.py && cd ../frontend && npm test && npm run build && cd /home/fyz/codex-skills && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```

Expected: all checks pass.

- [ ] **Step 2: Run evaluator gate**

Run:

```bash
python3 scripts/harness_evaluator_cli.py prepare-task --repo-root . --task-id compute-accelerator-monthly-discovery-01 --attempt 1
python3 scripts/harness_evaluator_orchestrator.py run-task-auto-gate --driver fake --task-id compute-accelerator-monthly-discovery-01 --repo-root . --max-attempts 1
```

Expected: a task evaluator bundle is written under `.codex/evaluations/tasks/compute-accelerator-monthly-discovery-01/` with `result.json` status `pass`.

- [ ] **Step 3: Update task status and progress**

In `tasks.json`, set:

```json
"status": "done"
```

for `compute-accelerator-monthly-discovery-01`, and update `last_updated` to `2026-06-28`.

At the top of `progress.md`, add:

```markdown
## 2026-06-28 Compute Accelerator Monthly Discovery

- Added one-shot run policy for known accelerator model/spec sources.
- Added monthly accelerator discovery profiles and candidate review flow.
- Added candidate extraction, deduplication, accept/reject APIs, and frontend candidate review controls.
- Evidence:
  - `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py tests/test_scheduler.py tests/test_discovery.py && cd ../frontend && npm test && npm run build && cd /home/fyz/codex-skills && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` -> pass
  - `.codex/evaluations/tasks/compute-accelerator-monthly-discovery-01/<timestamp>/result.json` -> pass
```

- [ ] **Step 4: Commit final bookkeeping**

```bash
git add tasks.json progress.md
git commit -m "chore: record accelerator monthly discovery completion"
```

- [ ] **Step 5: Final branch review**

Run:

```bash
git status --short
git log --oneline --max-count=8
```

Expected: only unrelated pre-existing untracked/modified files remain outside this task; task commits are visible.

