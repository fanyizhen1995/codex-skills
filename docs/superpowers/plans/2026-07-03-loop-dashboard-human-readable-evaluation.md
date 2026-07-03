# Loop Dashboard Human-Readable Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Loop Dashboard understandable to a non-technical reader by showing what the task is, where it is in the loop, what evaluator scenarios were tested, what bugs exist, and whether user action is required.

**Architecture:** Extend the read-only backend store to derive structured `decision_summary` and `acceptance_summary` from existing loop artifacts and evaluator result bundles. Update the frontend to prioritize these summaries above raw artifacts/logs, while keeping the raw event log available as supporting evidence. Extend the browser evaluator fixture and checks so simulated user acceptance steps are recorded and visible.

**Tech Stack:** Python FastAPI/store tests, vanilla JS frontend, CSS, Playwright-backed evaluator script.

---

### Task 1: Backend Summaries

**Files:**
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`

- [ ] Add failing tests that assert `get_run()` includes:
  - `decision_summary.requires_user_decision`
  - `decision_summary.decision_label`
  - `acceptance_summary.status`
  - `acceptance_summary.scenarios`
  - `acceptance_summary.checked`
- [ ] Implement minimal store helpers that derive these fields from `run.json`, `planner-output.json`, `evaluator-result.json`, and rich evaluator `result.json`.
- [ ] Run `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py`.

### Task 2: Frontend Human-Readable View

**Files:**
- Modify: `apps/loop_dashboard/frontend/app.js`
- Modify: `apps/loop_dashboard/frontend/styles.css`

- [ ] Render a top-level human summary with task objective, current phase, next action, and user decision state.
- [ ] Render an acceptance section with scenario rows, checked UI areas, evidence, and rerun commands.
- [ ] Rename the raw event area visually to make clear it is supporting artifacts/logs, not the acceptance checklist.
- [ ] Preserve full wrapping behavior and avoid truncating text.
- [ ] Run `node --check apps/loop_dashboard/frontend/app.js`.

### Task 3: Evaluator Evidence and Verification

**Files:**
- Modify: `scripts/loop_dashboard_evaluator.py`

- [ ] Add structured acceptance steps to evaluator output and fixture rich result.
- [ ] Extend browser checks to assert the dashboard shows task context, acceptance scenarios, bug status, and decision requirement.
- [ ] Run:
  - `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests`
  - `python3 -m unittest scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_evaluator_scenarios -v`
  - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/human-readable-final`
  - `python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id loop-dashboard-dev`
  - `python3 -m json.tool tasks.json >/dev/null`
  - `python3 -m json.tool docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json >/dev/null`
  - `git diff --check`

### Task 4: Live Service and Commit

**Files:**
- Modify only the files above plus this plan.

- [ ] Restart the `loop-dashboard` tmux service on `0.0.0.0:8766`.
- [ ] Run a live Playwright check against `http://127.0.0.1:8766`.
- [ ] Commit with `fix(loop-dashboard): surface evaluator acceptance context`.
