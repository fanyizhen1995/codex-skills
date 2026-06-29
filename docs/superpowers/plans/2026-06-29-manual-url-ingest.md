# Manual URL Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Workbench path where a user can paste a URL and have it fetched, ingested into wiki, validated, and committed through existing queue machinery.

**Architecture:** Add a backend orchestration service for manual URLs, expose it through `POST /api/manual-ingests`, then add a small Sources page form. The orchestration reuses source profiles, `run_source_once`, `approve_task`, and `run_approved_task` so queue, Codex, validation, and commit behavior stay centralized.

**Tech Stack:** FastAPI, SQLite, existing crawler fetchers, React/Vite, Vitest, pytest.

---

### Task 1: Backend Manual URL Orchestration

**Files:**
- Create: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/manual_ingest.py`
- Modify: `personal-wiki/apps/crawler_workbench/backend/crawler_workbench/api.py`
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/test_manual_ingest.py`

- [ ] **Step 1: Write failing backend tests**

Add tests that call the service/API with a static fetcher and fake Codex runner. Assert that a manual URL source is created, raw evidence is stored, an ingest task succeeds, and `auto_commit_enabled` is passed through.

- [ ] **Step 2: Run tests to verify failure**

Run: `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_manual_ingest.py`

Expected: import or endpoint failures because `manual_ingest.py` and `/api/manual-ingests` do not exist.

- [ ] **Step 3: Implement service and API**

Implement:
- `manual_source_id(url: str) -> str`
- `run_manual_url_ingest(settings, db, url, domain, auto_commit_enabled=True, fetcher=None, codex_runner=None) -> dict`
- API request model and route.

- [ ] **Step 4: Run backend tests**

Run: `cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q tests/test_manual_ingest.py tests/test_api.py tests/test_fetch_service_policy.py tests/test_ingest_git.py`

Expected: all selected tests pass.

### Task 2: Frontend Manual URL Form

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/api.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/types.ts`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/pages/SourcesPage.tsx`
- Modify: `personal-wiki/apps/crawler_workbench/frontend/src/App.test.tsx`
- Modify as needed: `personal-wiki/apps/crawler_workbench/frontend/src/styles.css`

- [ ] **Step 1: Write failing frontend test**

Add a Vitest case that navigates to Sources, enters a URL into the manual ingest form, submits it, and expects `createManualIngest` to be called and a success notice to render.

- [ ] **Step 2: Run test to verify failure**

Run: `cd personal-wiki/apps/crawler_workbench/frontend && npm test -- src/App.test.tsx`

Expected: failure because API/form does not exist.

- [ ] **Step 3: Implement frontend form**

Add API types and function, then render a compact form above the candidate/source lists.

- [ ] **Step 4: Run frontend tests/build**

Run: `cd personal-wiki/apps/crawler_workbench/frontend && npm test -- src/App.test.tsx && npm run build`

Expected: tests and build pass.

### Task 3: Task Registry, Evaluator, Final Verification

**Files:**
- Modify: `tasks.json`
- Modify: `progress.md`
- Modify if needed: `AGENTS.md` or harness docs only if deployment workflow changes.

- [ ] **Step 1: Register task**

Add `crawler-manual-url-ingest-01` with `requires_eval=true` and a verify command that runs backend tests, frontend tests/build, and the crawler e2e evaluator.

- [ ] **Step 2: Run full verification**

Run the task verify command from `tasks.json`.

- [ ] **Step 3: Run evaluator**

Run: `python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-manual-url-ingest-01`

- [ ] **Step 4: Commit**

Commit only files belonging to this task. Do not include `.personal-wiki-workbench/sources.yaml`.
