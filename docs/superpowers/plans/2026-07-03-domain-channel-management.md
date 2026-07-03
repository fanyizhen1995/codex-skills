# Domain Channel Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add domain-scoped channel management to Crawler Workbench so each wiki domain can manage durable access/auth boundaries separately from concrete crawl targets.

**Architecture:** SQLite becomes the runtime source of truth for channel and source configuration. Channels own base URL, access kind, connector, auth state, encrypted local secrets, probe history, trust, and source counts; sources remain concrete crawl targets and gain `channel_id` plus `fetcher_type` compatibility fields. The work is split into four registered demand-development loop tasks: backend model/API compatibility, backend secrets/probes/readiness, frontend Domain Channels workbench, and isolated live e2e validation.

**Tech Stack:** FastAPI, Pydantic, SQLite, pytest, React/Vite, Vitest, Playwright, existing harness evaluator scenario contracts.

---

## File Structure

- Modify `tasks.json`: register four domain-channel tasks with evaluator policy and verify commands.
- Create `docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json`: backend model/API user-flow contract.
- Create `docs/harness/evaluator-scenarios/crawler-domain-channels-probe-secrets-01.json`: backend secrets/probe readiness user-flow contract.
- Create `docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json`: frontend browser user-flow contract.
- Create `docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json`: integrated isolated backend/frontend scenario contract.
- Modify `.codex/loop-runs/crawler-domain-channels-dev-01/run.json`: advance the current loop run after Planner output is written.
- Create `.codex/loop-runs/crawler-domain-channels-dev-01/planner-output.json`: machine-readable Planner result for the first generator task.
- Create `.codex/loop-runs/crawler-domain-channels-dev-01/generator-prompt.md`: handoff prompt for `crawler-domain-channels-model-01`.
- Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`: Task 2 creates `channels` and source compatibility columns; Task 3 creates `channel_secrets` and `channel_probe_runs`.
- Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`: migration helpers for new columns/tables and one-time source import behavior.
- Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`: channel derivation, YAML seed import, source/channel listing, source create/update/delete helpers, and `fetcher_type` compatibility.
- Create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/channels.py`: channel CRUD, normalization, source counts, source relationship checks, and channel readiness helpers.
- Create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/channel_secrets.py`: encrypted local secret storage and key-file lifecycle for synthetic/local credentials.
- Create `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/channel_probe.py`: probe execution, status mapping, and probe history persistence.
- Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`: resolve source channel readiness before fetch and dispatch by legacy `type` while `fetcher_type` is introduced.
- Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`: add channel/source CRUD, secret, probe, and compatible source APIs.
- Modify `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`: response/request models for channels, sources, secrets, and probes.
- Create `personal-wiki/apps/crawler_workbench/backend/tests/test_domain_channels_model.py`: schema/import/API compatibility tests.
- Create `personal-wiki/apps/crawler_workbench/backend/tests/test_domain_channel_secrets.py`: synthetic encrypted secret tests.
- Create `personal-wiki/apps/crawler_workbench/backend/tests/test_domain_channel_probes.py`: probe state/readiness tests.
- Modify existing backend tests `test_db_profiles.py`, `test_api.py`, `test_fetch_service_policy.py`, and `test_scheduler.py`: keep current behaviors compatible.
- Modify `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`: add channel, probe, and source API types.
- Modify `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`: add channel/source/secret/probe API client functions.
- Modify `personal-wiki/apps/crawler_workbench/frontend/src/App.tsx`: add Domain Channels navigation and route.
- Create `personal-wiki/apps/crawler_workbench/frontend/src/pages/DomainChannelsPage.tsx`: approved three-pane channel/source management UI.
- Modify `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`: Vitest coverage for navigation, channel actions, and secret clearing.
- Modify `personal-wiki/apps/crawler_workbench/frontend/tests/smoke.spec.ts`: Playwright user-flow coverage for Domain Channels.
- Modify `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`: workbench styling for channel filters, table, detail panel, secret form, source list, and probe history.
- Modify `scripts/wiki_crawler_e2e_evaluator.py`: extend isolated e2e evaluator with the Domain Channels integrated flow.
- Modify `progress.md`: append completion evidence only after a task passes its verify and evaluator gate.

## Task 1: Planner Registration And Handoff

**Files:**
- Modify: `tasks.json`
- Create: `docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json`
- Create: `docs/harness/evaluator-scenarios/crawler-domain-channels-probe-secrets-01.json`
- Create: `docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json`
- Create: `docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json`
- Create: `docs/superpowers/plans/2026-07-03-domain-channel-management.md`
- Create: `.codex/loop-runs/crawler-domain-channels-dev-01/planner-output.json`
- Create: `.codex/loop-runs/crawler-domain-channels-dev-01/generator-prompt.md`
- Modify: `.codex/loop-runs/crawler-domain-channels-dev-01/run.json`

- [ ] **Step 1: Register tasks**

Insert `crawler-domain-channels-model-01`, `crawler-domain-channels-probe-secrets-01`, `crawler-domain-channels-ui-01`, and `crawler-domain-channels-live-e2e-01` into `tasks.json`. Use `status: "in_progress"` for `crawler-domain-channels-model-01`; use `status: "pending"` and `blocked_by` pointing at the previous task for the later tasks.

- [ ] **Step 2: Write evaluator scenarios**

Create one scenario JSON per task under `docs/harness/evaluator-scenarios/`. Each scenario must have `task_id`, `must_simulate: true`, and a `user_scenarios` entry with `scenario_id`, `user_goal`, `prerequisites`, `entrypoint`, `steps`, `expected_outcomes`, `failure_signals`, `cleanup`, and `automation_hint`.

- [ ] **Step 3: Write Planner output**

Write `.codex/loop-runs/crawler-domain-channels-dev-01/planner-output.json` for the first generator task:

```json
{
  "task_id": "crawler-domain-channels-model-01",
  "policy": "demand_development",
  "task_kind": "registered_task",
  "title": "Implement crawler workbench domain channel data model",
  "goal": "Add backend schema, migration, one-time YAML seed import, channel/source relationship APIs, and source compatibility fields for Domain Channel Management.",
  "non_goals": [
    "Do not implement encrypted secrets or probe execution in this task.",
    "Do not implement frontend UI in this task.",
    "Do not modify personal-wiki domain raw or wiki evidence."
  ],
  "allowed_paths": [
    "personal-wiki/apps/crawler_workbench/backend/crawler_workbench/**",
    "personal-wiki/apps/crawler_workbench/backend/tests/**",
    "personal-wiki/apps/crawler_workbench/config/sources.example.yaml",
    "docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json",
    "tasks.json",
    "progress.md"
  ],
  "denylist_paths": [
    ".env",
    ".env.*",
    ".personal-wiki-workbench/**",
    "**/*token*",
    "**/*key*",
    "personal-wiki/domains/**/raw/**",
    "personal-wiki/domains/**/wiki/**",
    "personal-wiki/apps/crawler_workbench/frontend/**"
  ],
  "verify_commands": [
    "cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channels_model.py tests/test_db_profiles.py tests/test_api.py tests/test_fetch_service_policy.py tests/test_scheduler.py && cd /home/fyz/codex-skills && python3 -m json.tool tasks.json >/dev/null && python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json >/dev/null && git diff --check"
  ],
  "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json",
  "stop_conditions": [
    "passed_waiting_human_merge",
    "stopped_blocked",
    "stopped_budget"
  ],
  "next_planning_hint": "After model/API compatibility passes evaluator, continue with crawler-domain-channels-probe-secrets-01."
}
```

- [ ] **Step 4: Write generator prompt**

Create `.codex/loop-runs/crawler-domain-channels-dev-01/generator-prompt.md` with the first task scope, allowed/deny paths, required tests, and completion requirements.

- [ ] **Step 5: Verify Planner artifacts**

Run:

```bash
python3 -m json.tool tasks.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-probe-secrets-01.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json >/dev/null
python3 -m json.tool .codex/loop-runs/crawler-domain-channels-dev-01/planner-output.json >/dev/null
python3 - <<'PY'
from pathlib import Path
from scripts.harness_loop_contracts import read_json_file, validate_planner_output_payload
validate_planner_output_payload(read_json_file(Path('.codex/loop-runs/crawler-domain-channels-dev-01/planner-output.json')))
PY
git diff --check
```

- [ ] **Step 6: Commit Planner artifacts**

Run:

```bash
git add tasks.json progress.md docs/harness/evaluator-scenarios/crawler-domain-channels-model-01.json docs/harness/evaluator-scenarios/crawler-domain-channels-probe-secrets-01.json docs/harness/evaluator-scenarios/crawler-domain-channels-ui-01.json docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json docs/superpowers/plans/2026-07-03-domain-channel-management.md
git commit -m "chore(crawler): plan domain channel loop tasks"
```

The loop run artifacts under `.codex/loop-runs/crawler-domain-channels-dev-01/` are ignored local evidence. Keep them in the workspace for loop recovery; do not force-add them to the commit.

## Task 2: Backend Channel Model And Source Compatibility

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/profiles.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/channels.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_domain_channels_model.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_db_profiles.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_fetch_service_policy.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_scheduler.py`

- [ ] **Step 1: Write failing schema/import tests**

Create `tests/test_domain_channels_model.py` with tests named:

```python
def test_schema_migration_creates_channel_tables_and_source_columns(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    with open_db(settings.database_path) as db:
        migrate(db)
        tables = {row["name"] for row in db.execute("select name from sqlite_master where type = 'table'")}
        source_columns = {row["name"] for row in db.execute("pragma table_info(source_profiles)")}
    assert "channels" in tables
    assert {"channel_id", "fetcher_type"} <= source_columns

def test_empty_database_imports_sources_yaml_once_and_assigns_channels(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    settings.resolved_state_dir.mkdir(parents=True)
    settings.sources_yaml_path.write_text(PROFILE_YAML, encoding="utf-8")
    with open_db(settings.database_path) as db:
        migrate(db)
        initialize_profiles_from_seed(db, settings.sources_yaml_path)
        source = db.execute("select channel_id, fetcher_type from source_profiles where id = 'nccl-releases'").fetchone()
        channel = db.execute("select base_url, kind, connector from channels where id = ?", (source["channel_id"],)).fetchone()
    assert source["fetcher_type"] == "web_page"
    assert channel["base_url"] == "https://docs.nvidia.com"
    assert channel["kind"] == "web"

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

def test_source_listing_includes_channel_fields(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    seed_domain_channels_fixture(settings)
    client = TestClient(create_app(settings))
    payload = client.get("/api/sources").json()
    source = next(item for item in payload if item["id"] == "nccl-releases")
    assert source["channel_id"]
    assert source["channel_base_url"] == "https://docs.nvidia.com"
    assert source["channel_auth_state"] == "ready"

def test_channel_listing_returns_source_counts(tmp_path):
    settings = Settings(repo_root=tmp_path, state_dir=tmp_path / ".state")
    seed_domain_channels_fixture(settings)
    client = TestClient(create_app(settings))
    payload = client.get("/api/channels", params={"domain": "ai_infra"}).json()
    assert any(item["base_url"] == "https://docs.nvidia.com" and item["source_count"] == 1 for item in payload)
```

Define `PROFILE_YAML` and `seed_domain_channels_fixture(settings: Settings) -> None` in the test file. `seed_domain_channels_fixture()` writes `PROFILE_YAML`, opens the database, runs `migrate()`, and calls `initialize_profiles_from_seed()`.

- [ ] **Step 2: Verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channels_model.py
```

Expected: FAIL because channel tables and fields are not implemented.

- [ ] **Step 3: Add schema and migration compatibility**

Update `schema.sql` and `db.py` so migration creates:

```sql
create table if not exists channels (
  id text primary key,
  target_domain text not null,
  name text not null,
  base_url text not null,
  base_url_normalized text not null,
  probe_url text,
  probe_method text not null default 'GET',
  probe_config_json text not null default '{}',
  kind text not null,
  connector text not null default 'generic',
  trust_level text not null default 'untrusted',
  enabled integer not null default 1,
  auth_required integer not null default 0,
  auth_mode text not null default 'none',
  auth_state text not null default 'ready',
  last_probe_status text,
  last_probe_at text,
  last_probe_summary text,
  notes text not null default '',
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);
create unique index if not exists channels_domain_base_url_idx
on channels(target_domain, base_url_normalized);
```

Add `source_profiles.channel_id text references channels(id) on delete restrict` and `source_profiles.fetcher_type text`. Add `_ensure_column()` calls for existing databases.

- [ ] **Step 4: Add channel derivation and one-time import**

In `profiles.py`, add helpers for:

```python
def initialize_profiles_from_seed(connection: sqlite3.Connection, yaml_path: Path) -> None:
    """Import sources.yaml only when the runtime source table is empty."""

def ensure_source_channels(connection: sqlite3.Connection) -> None:
    """Create/reuse channels and backfill source_profiles.channel_id and fetcher_type."""

def derive_channel_seed(profile: dict[str, Any]) -> dict[str, str]:
    """Return id, base_url, normalized base URL, kind, connector, auth_mode, and auth_required."""

def infer_fetcher_type(profile: dict[str, Any]) -> str:
    """Map legacy source type/config to web_page, rss_feed, github_repo, github_issues, github_releases, or arxiv_query."""
```

The initializer imports YAML only when `select count(*) from source_profiles` is zero, then calls `ensure_source_channels()`. Existing `mirror_profiles()` remains available for tests/manual tools but startup must no longer mirror YAML over a non-empty DB.

- [ ] **Step 5: Add channel/source API helpers**

Create `channels.py` with channel list/create/update/delete helpers. Extend `list_profiles()` to join channel fields and source counts. Add `GET /api/channels?domain=ai_infra`, compatible `GET /api/sources?domain=ai_infra&channel_id=<channel-id>`, `POST /api/sources`, `PATCH /api/sources/{source_id}`, and conservative `DELETE /api/sources/{source_id}`. For first-version delete semantics, hard-delete only draft sources with no `raw_items`, `fetch_runs`, or `ingest_tasks`; otherwise set `enabled = 0`.

- [ ] **Step 6: Verify focused backend tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channels_model.py
```

Expected: PASS.

- [ ] **Step 7: Verify compatibility tests**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_db_profiles.py tests/test_api.py tests/test_fetch_service_policy.py tests/test_scheduler.py
```

Expected: PASS.

- [ ] **Step 8: Commit model task**

Run the task verify command from `tasks.json`, then commit only backend model/API files plus task/progress updates:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests tasks.json progress.md
git commit -m "feat(crawler): add domain channel model"
```

## Task 3: Channel Secrets, Probes, And Run Readiness

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schema.sql`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/db.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/channels.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/channel_secrets.py`
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/channel_probe.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/fetch_service.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_domain_channel_secrets.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_domain_channel_probes.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_fetch_service_policy.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_api.py`

- [ ] **Step 1: Write failing secret tests**

Create tests proving a synthetic token can be written/replaced/deleted, read APIs show only `secret_configured: true/false`, and missing key files fail closed when encrypted secret rows exist.

- [ ] **Step 2: Write failing probe/readiness tests**

Create tests for local HTTP fixture outcomes: public ready, missing secret, 401/403 auth_failed, login/captcha/JS shell needs_browser, DNS/connect timeout network_failed, and unsupported mcp/command kind.

- [ ] **Step 3: Verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channel_secrets.py tests/test_domain_channel_probes.py
```

Expected: FAIL because secrets and probes are not implemented.

- [ ] **Step 4: Implement encrypted local secrets**

Use a local key file under `settings.resolved_state_dir / "secrets.key"`. Do not return plaintext. If an encryption dependency is already present, use it; otherwise use a narrowly scoped standard-library authenticated envelope or add a dependency only with explicit supply-chain evidence recorded in the generator result. Tests must use synthetic values such as `synthetic-token-for-test`, never real tokens.

- [ ] **Step 5: Implement probe execution and persistence**

Add `channel_probe_runs`, `POST /api/channels/{channel_id}/probe`, and `GET /api/channels/{channel_id}/probe-runs`. Persist short summaries only and update channel latest probe fields.

- [ ] **Step 6: Block source runs by channel readiness**

Before fetcher dispatch in `run_source_once()`, load the channel and record failed/skipped `fetch_runs.error` for disabled, missing auth, auth_failed, unsupported, or needs_browser states.

- [ ] **Step 7: Verify backend probe/secrets task**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_domain_channel_secrets.py tests/test_domain_channel_probes.py tests/test_fetch_service_policy.py tests/test_api.py
```

Expected: PASS.

- [ ] **Step 8: Commit probe/secrets task**

Run the task verify command from `tasks.json`, then commit only backend probe/secret files plus task/progress updates:

```bash
git add personal-wiki/apps/crawler_workbench/backend/crawler_workbench personal-wiki/apps/crawler_workbench/backend/tests tasks.json progress.md
git commit -m "feat(crawler): add channel secrets and probes"
```

## Task 4: Domain Channels Frontend

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.tsx`
- Create: `personal-wiki/apps/crawler_workbench/frontend/src/pages/DomainChannelsPage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/tests/smoke.spec.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py`

- [ ] **Step 1: Write failing frontend tests**

Add Vitest coverage for navigation to `Domain Channels`, channel list rendering, channel create/edit payloads, secret replacement clearing the input, probe history rendering, and child source creation visibility.

- [ ] **Step 2: Write failing Playwright flow**

Extend `tests/smoke.spec.ts` or add a focused spec that uses mocked/isolated backend responses to create a channel, replace a synthetic secret, run a probe, create a child source, and navigate back to Sources/Queue.

- [ ] **Step 3: Verify red**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm test -- src/App.test.tsx
```

Expected: FAIL because the page and API client do not exist.

- [ ] **Step 4: Implement API client and types**

Add TypeScript types and API functions for channels, channel secrets, probe runs, source CRUD, and manual source run.

- [ ] **Step 5: Implement the Domain Channels page**

Build the approved layout: left domain/search/filter rail, main channel table, right detail panel with editor, secret status, child sources, and probe history. Use existing style conventions and lucide icons.

- [ ] **Step 6: Verify frontend tests and build**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/frontend && npm test -- src/App.test.tsx && npm run build && npm run test:ui
```

Expected: PASS.

- [ ] **Step 7: Commit UI task**

Run the task verify command from `tasks.json`, then commit only frontend/schema files plus task/progress updates:

```bash
git add personal-wiki/apps/crawler_workbench/frontend/src personal-wiki/apps/crawler_workbench/frontend/tests personal-wiki/apps/crawler_workbench/backend/crawler_workbench/schemas.py tasks.json progress.md
git commit -m "feat(crawler): add domain channels UI"
```

## Task 5: Integrated Live E2E

**Files:**
- Modify: `scripts/wiki_crawler_e2e_evaluator.py`
- Modify: `docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json`
- Modify: `tasks.json`
- Modify: `progress.md`

- [ ] **Step 1: Extend evaluator with isolated channel flow**

Add an isolated Domain Channels flow to `scripts/wiki_crawler_e2e_evaluator.py` that starts backend/frontend without reusing long-running services, creates a synthetic channel/source/secret/probe via API, and validates the UI through Playwright.

- [ ] **Step 2: Add artifact hygiene checks**

Make the evaluator fail if retained JSON/log/trace artifacts include the synthetic secret string. Retain only redacted summaries and evidence paths.

- [ ] **Step 3: Verify live e2e**

Run:

```bash
python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01
```

Expected: PASS with isolated backend/frontend, result.json, summary.md, and browser evidence.

- [ ] **Step 4: Run final verification**

Run:

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q
cd /home/fyz/codex-skills/personal-wiki/apps/crawler_workbench/frontend && npm test && npm run build && npm run test:ui
cd /home/fyz/codex-skills && python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01
python3 -m json.tool tasks.json >/dev/null
git diff --check
```

Expected: PASS.

- [ ] **Step 5: Mark final task done and commit**

Update `tasks.json` and `progress.md` with evidence, then commit:

```bash
git add scripts/wiki_crawler_e2e_evaluator.py docs/harness/evaluator-scenarios/crawler-domain-channels-live-e2e-01.json tasks.json progress.md
git commit -m "test(crawler): validate domain channels e2e"
```

## Verification Notes

- Do not commit real credentials, cookies, token dumps, runtime SQLite databases, or `secrets.key`.
- Do not touch unrelated dirty `personal-wiki/domains/ai_infra/**` raw/wiki/ingest paths.
- If backend code, schema, or runtime config changes are tested against long-running services, restart the backend. If frontend code changes are tested against long-running services, restart the frontend. Integrated evaluator runs must use isolated services.
- Each task must stop at the evaluator gate or human merge gate; do not merge into `main` automatically.

## Self-Review

- Spec coverage: the plan covers channel/source model, one-time SQLite import, encrypted local secrets, probe history, channel readiness, frontend channel/source management, and isolated e2e.
- Placeholder scan: no placeholder markers or unspecified test commands remain.
- Type consistency: task IDs, scenario filenames, and verify commands match the spec and task registry.
