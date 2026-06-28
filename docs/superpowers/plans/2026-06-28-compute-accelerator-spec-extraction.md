# Compute Accelerator Spec Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert compute accelerator raw crawler captures into structured, source-backed SKU/spec observations and expose them in the crawler workbench.

**Architecture:** Add SQLite tables for extracted accelerator SKUs, field observations, and resolved fields. Keep extraction conservative and provenance-first: raw captures produce observations, and only high-trust non-S5 observations can auto-populate resolved fields. Add backend APIs plus a frontend specs page for inspection and manual re-extraction.

**Tech Stack:** Python 3, SQLite, FastAPI, pytest, React, TypeScript, Vite/Vitest, existing crawler workbench profiles/raw_items.

---

## File Map

- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/accelerator_specs.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_accelerator_specs.py`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/AcceleratorSpecsPage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`
- Modify: `tasks.json`, `progress.md`

## Task 1: Backend Schema And Extraction Core

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/accelerator_specs.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/tests/test_accelerator_specs.py`

- [ ] **Step 1: Write failing schema and extractor tests**

Add `tests/test_accelerator_specs.py` with tests for:

```python
def test_schema_migration_adds_accelerator_spec_tables(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        tables = {row["name"] for row in db.execute("select name from sqlite_master where type = 'table'")}
    assert {"accelerator_skus", "accelerator_observations", "accelerator_resolved_specs"} <= tables
```

```python
def test_extracts_power_and_form_factor_from_official_raw_capture(tmp_path):
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
        raw_item={"id": 7, "raw_path": str(raw_path), "canonical_url": "https://www.birentech.com/product/hardware/166l/"},
        text=raw_path.read_text(encoding="utf-8"),
    )
    assert {(item.field, item.value, item.unit) for item in observations} >= {
        ("tdp", 600, "W"),
        ("form_factor", "冷板式液冷 OAM 模组", "none"),
    }
```

```python
def test_upsert_extracted_specs_preserves_observation_provenance_and_resolves_s1(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    raw_path = settings.wiki_root / "domains/ai_infra/raw/crawler/compute-accelerators-biren-166l/item.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("# Biren\n\n峰值功耗 600W。", encoding="utf-8")
    with open_db(settings.database_path) as db:
        migrate(db)
        insert source_profiles row with config_json for S1/specs_candidate
        insert raw_items row pointing to raw_path
        counts = upsert_extracted_specs_for_raw_item(settings, db, raw_item_id)
        assert counts == {"skus": 1, "observations": 1, "resolved": 1}
        assert observation row has raw_item_id, raw_path, source_rank S1, field tdp
        assert resolved row points to the observation id
```

```python
def test_s5_observations_do_not_auto_resolve(tmp_path):
    insert S5 specs_candidate source and raw item with "memory 256GB HBM3e"
    counts = upsert_extracted_specs_for_raw_item(settings, db, raw_item_id)
    assert counts["observations"] == 1
    assert counts["resolved"] == 0
```

- [ ] **Step 2: Run tests to verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_accelerator_specs.py
```

Expected: fail because tables and module do not exist.

- [ ] **Step 3: Add tables and migration**

Add to `schema.sql`:

```sql
create table if not exists accelerator_skus (
  sku_id text primary key,
  vendor text not null,
  model_name text not null,
  normalized_model text not null,
  scope text not null,
  source_profile_id text not null references source_profiles(id) on delete cascade,
  source_url text not null,
  raw_item_id integer references raw_items(id) on delete set null,
  raw_path text not null,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists accelerator_observations (
  id integer primary key autoincrement,
  sku_id text not null references accelerator_skus(sku_id) on delete cascade,
  field text not null,
  value_text text not null,
  value_number real,
  unit text not null,
  source_profile_id text not null references source_profiles(id) on delete cascade,
  source_rank text not null,
  raw_item_id integer references raw_items(id) on delete set null,
  raw_path text not null,
  evidence_text text not null,
  confidence real not null,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  unique(sku_id, field, value_text, unit, raw_path)
);

create table if not exists accelerator_resolved_specs (
  id integer primary key autoincrement,
  sku_id text not null references accelerator_skus(sku_id) on delete cascade,
  field text not null,
  value_text text not null,
  value_number real,
  unit text not null,
  source_observation_id integer not null references accelerator_observations(id) on delete cascade,
  resolved_by text not null default 'rule',
  confidence text not null,
  conflict_status text not null default 'clean',
  updated_at text not null default current_timestamp,
  unique(sku_id, field)
);
```

Add migration guards in `db.py` only if needed for new columns; new tables are covered by `executescript`.

- [ ] **Step 4: Implement conservative extractor**

Create `accelerator_specs.py` with:

```python
@dataclass
class ExtractedObservation:
    field: str
    value: str | float
    unit: str
    evidence_text: str
    confidence: float
```

Implement:

- `extract_observations_from_text(profile, raw_item, text) -> list[ExtractedObservation]`
- `upsert_extracted_specs_for_raw_item(settings, db, raw_item_id) -> dict[str, int]`
- `extract_specs_for_all_raw_items(settings, db) -> dict[str, int]`
- `list_accelerator_specs(db) -> list[dict[str, object]]`

Rules:

- Run only for profiles whose `config_json.extract_mode` is `specs_candidate`.
- Derive `sku_id` from source id by stripping `compute-accelerators-`.
- Use `vendor_hint` and first `accelerator_scope` from profile config.
- Extract only clear fields: `tdp`, `memory_capacity`, `memory_bandwidth`, `network_bandwidth`, `form_factor`, `host_interface`.
- Auto-resolve only when `source_rank != "S5"` and the field has no conflicting resolved value.
- Preserve all observations even when resolved already exists.

- [ ] **Step 5: Verify green**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_accelerator_specs.py
```

Expected: pass.

## Task 2: Fetch Integration And API

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/tests/test_accelerator_specs.py`

- [ ] **Step 1: Add failing integration/API tests**

Add tests that:

- `run_source_once` on a `specs_candidate` source writes raw and then creates observations.
- `GET /api/accelerator-specs` returns SKU records with observations and resolved fields.
- `POST /api/accelerator-specs/extract` backfills existing raw_items and returns counts.

- [ ] **Step 2: Run integration/API tests to verify red**

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_accelerator_specs.py
```

- [ ] **Step 3: Wire extraction after raw writes**

In `fetch_service.py`, after inserting `content_versions`, call:

```python
if profile.get("extract_mode") == "specs_candidate":
    from .accelerator_specs import upsert_extracted_specs_for_raw_item
    upsert_extracted_specs_for_raw_item(settings, db, int(raw_item_id))
```

- [ ] **Step 4: Add API models and endpoints**

Add response models for SKU/spec records in `schemas.py`.

Add endpoints in `api.py`:

```python
@router.get("/accelerator-specs", response_model=list[AcceleratorSpecResponse])
def accelerator_specs(request: Request) -> list[AcceleratorSpecResponse]: ...

@router.post("/accelerator-specs/extract")
def extract_accelerator_specs(request: Request) -> dict[str, int]: ...
```

- [ ] **Step 5: Verify green**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend
PYTHONPATH=. pytest -q tests/test_accelerator_specs.py tests/test_db_profiles.py tests/test_discovery.py
```

## Task 3: Frontend Specs Page

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/AcceleratorSpecsPage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`

- [ ] **Step 1: Add failing UI tests**

Add tests that mock `getAcceleratorSpecs` and assert:

- Navigation contains `参数库`.
- The specs page renders SKU name, scope, resolved field value, and source raw path.
- The extract button calls `extractAcceleratorSpecs` then refreshes the table.

- [ ] **Step 2: Run frontend tests to verify red**

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test -- Accelerator
```

- [ ] **Step 3: Implement API client and page**

Add types:

```ts
export interface AcceleratorObservation { ... }
export interface AcceleratorResolvedField { ... }
export interface AcceleratorSpecRecord { ... }
```

Add API helpers:

```ts
export async function getAcceleratorSpecs(): Promise<AcceleratorSpecRecord[]>
export async function extractAcceleratorSpecs(): Promise<Record<string, number>>
```

Add `AcceleratorSpecsPage` as a dense table grouped by SKU with resolved fields and expandable observation evidence.

- [ ] **Step 4: Wire navigation**

Add `acceleratorSpecs` to `PageKey`, navigation, and page rendering.

- [ ] **Step 5: Verify green**

```bash
cd personal-wiki/apps/crawler_workbench/frontend
npm test
npm run build
```

## Task 4: Backfill, Validate, And Record Evidence

**Files:**
- Modify: `progress.md`

- [ ] **Step 1: Run the backend extraction backfill**

```bash
curl -sS -X POST http://127.0.0.1:8765/api/accelerator-specs/extract | python -m json.tool
```

If the backend is not running, run the equivalent Python service call against `.personal-wiki-workbench/workbench.sqlite3`.

- [ ] **Step 2: Verify DB counts**

```bash
sqlite3 -header -column .personal-wiki-workbench/workbench.sqlite3 "
select count(*) as skus from accelerator_skus;
select count(*) as observations from accelerator_observations;
select count(*) as resolved_fields from accelerator_resolved_specs;
"
```

- [ ] **Step 3: Run full task verification**

```bash
REPO_ROOT=$(pwd) && cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_accelerator_specs.py tests/test_db_profiles.py tests/test_discovery.py && cd ../frontend && npm test && npm run build && cd "$REPO_ROOT" && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate-accelerators && python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
```

- [ ] **Step 4: Update progress**

Append the backfill counts and verification output to `progress.md`.

