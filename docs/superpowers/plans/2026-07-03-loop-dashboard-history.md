# Loop Dashboard History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show completed loop history from project-local worktrees in the Loop Dashboard.

**Architecture:** Extend `LoopDashboardStore` to discover run directories from both the current checkout and project-local worktrees, attach source metadata to every summary/detail payload, and keep the existing frontend list/detail interaction. Browser evaluator fixtures will include a completed run under `.worktrees` to prove the user-facing path.

**Tech Stack:** Python FastAPI backend, pytest, static HTML/CSS/JS frontend, Playwright evaluator.

---

## Files

- Modify `apps/loop_dashboard/backend/loop_dashboard/store.py`: add run source discovery, dedupe, and source metadata.
- Modify `apps/loop_dashboard/backend/tests/test_store.py`: add backend regression tests.
- Modify `apps/loop_dashboard/backend/tests/test_api.py`: verify detail/events/logs for worktree runs.
- Modify `apps/loop_dashboard/frontend/app.js`: show source in run detail.
- Modify `scripts/loop_dashboard_evaluator.py`: seed and verify a worktree history run.
- Modify `docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json`: mention worktree history visibility.
- Modify `tasks.json` and `progress.md`: track task status and evidence.

### Task 1: Backend History Discovery

**Files:**
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`

- [ ] **Step 1: Write failing test**

Add a test that seeds `.worktrees/loop-dashboard/.codex/loop-runs/loop-dashboard-dev/run.json`, calls `LoopDashboardStore(tmp_path).list_runs()`, and asserts `loop-dashboard-dev` is returned with `source_kind == "worktree"`.

- [ ] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py::test_list_runs_includes_project_worktree_history
```

Expected: FAIL because the current store only scans `.codex/loop-runs`.

- [ ] **Step 3: Implement minimal discovery**

Add a private run source helper that yields current checkout runs first, then `.worktrees/*/.codex/loop-runs/*` run directories. Add `source_kind` and `source_path` to summaries and details.

- [ ] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py::test_list_runs_includes_project_worktree_history
```

Expected: PASS.

### Task 2: API Detail Lookup And Dedupe

**Files:**
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`
- Modify: `apps/loop_dashboard/backend/tests/test_api.py`
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`

- [ ] **Step 1: Write failing tests**

Add tests for duplicate `run_id` handling and API access to a worktree run's detail/events/logs.

- [ ] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py::test_duplicate_run_id_prefers_newest_source apps/loop_dashboard/backend/tests/test_api.py::test_api_serves_worktree_history_run
```

Expected: FAIL before lookup uses the discovered source map.

- [ ] **Step 3: Implement lookup**

Resolve `run_id` through the deduped source map in `get_run`, `get_events`, and `get_logs`.

- [ ] **Step 4: Verify green**

Run the same focused command. Expected: PASS.

### Task 3: Frontend Source Display

**Files:**
- Modify: `apps/loop_dashboard/frontend/app.js`
- Modify: `scripts/loop_dashboard_evaluator.py`

- [ ] **Step 1: Extend evaluator fixture and assertion**

Seed a completed `.worktrees/loop-dashboard/.codex/loop-runs/loop-dashboard-dev` run and assert the browser can select it and see `来源`.

- [ ] **Step 2: Verify red**

Run:

```bash
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/history-red
```

Expected: FAIL before the frontend displays the source row.

- [ ] **Step 3: Implement frontend row**

Add `["来源", detail.source_path]` to the `运行信息` rows, keeping one field per row.

- [ ] **Step 4: Verify green**

Run:

```bash
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/history-green
```

Expected: PASS.

### Task 4: Final Verification And Task Record

**Files:**
- Modify: `tasks.json`
- Modify: `progress.md`
- Modify: `docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json`

- [ ] **Step 1: Run full verification**

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-history-01
python3 -m json.tool tasks.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json >/dev/null
git diff --check
```

- [ ] **Step 2: Mark task done and commit**

Commit only files changed for `loop-dashboard-history-01`.
