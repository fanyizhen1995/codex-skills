# Loop Auditor Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current Loop Auditor dashboard visibility slice into a truthful display and add a minimal real Auditor engine that computes deterministic signals, validates audit reports, runs an independent auditor step, and blocks normal loop progress on open `must_fix` findings.

**Architecture:** Keep display-only fixes in `apps/loop_dashboard` and put the runtime engine in a new focused `scripts/harness_loop_auditor.py` module. `scripts/harness_loop_orchestrator.py` imports that module to compute signals and enforce the audit gate at parent/autonomous loop boundaries without adding more audit logic into the giant orchestrator file.

**Tech Stack:** Python stdlib, existing harness JSON contract helpers, FastAPI dashboard store, vanilla JS dashboard frontend, unittest/pytest, Playwright evaluator.

## Global Constraints

- Auditor artifacts are stored under `.codex/loop-runs/<run-id>/audit-reports/` and `deterministic-signals.json`.
- Phase 1 dashboard text must not claim hard blocking is active unless the orchestrator gate is actually wired.
- Deterministic signals are schema-based; arbitrary JSON numeric flattening must not be displayed as fact.
- `must_fix` hard blocking applies only to parent demand-development runs and autonomous-knowledge runs, not child runs.
- Auditor agent cannot directly modify `run.json`; orchestrator validates and writes audit artifacts.
- Existing long-running Loop Dashboard on port `8766` must stay usable after changes.

---

### Task 1: Fix Dashboard Truthfulness

**Files:**
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`
- Modify: `apps/loop_dashboard/frontend/app.js`
- Modify: `scripts/loop_dashboard_evaluator.py`

**Interfaces:**
- Produces: `audit_summary["engine_status"]`, `audit_summary["phase_notice"]`, schema-filtered `audit_summary["signals"]`, and `skill_inventory["usage_signal"]`.

- [ ] **Step 1: Write failing store tests**

Add tests that prove unknown deterministic signal numbers are ignored, `audit-10.json` wins over `audit-2.json` even when mtimes differ, and skill usage is labelled as log mentions rather than confirmed usage.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py::test_audit_summary_filters_unknown_signal_fields apps/loop_dashboard/backend/tests/test_store.py::test_latest_audit_report_prefers_numeric_audit_id apps/loop_dashboard/backend/tests/test_store.py::test_skill_inventory_labels_recent_usage_as_log_mentions`

- [ ] **Step 3: Implement minimal store/frontend fixes**

Replace arbitrary numeric flattening with a whitelist of the deterministic signal schema, add explicit Phase 1/engine status fields, pick latest audit report by `audit-<n>` before mtime, and change UI copy from "近期调用" to "近期日志提及".

- [ ] **Step 4: Run tests and evaluator**

Run:
`PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests`
`python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-auditor-01`

### Task 2: Add Auditor Contracts And Deterministic Signals

**Files:**
- Create: `scripts/harness_loop_auditor.py`
- Create: `scripts/tests/test_harness_loop_auditor.py`
- Modify: `scripts/harness_loop_contracts.py`
- Modify: `scripts/tests/test_harness_loop_contracts.py`

**Interfaces:**
- Produces: `compute_deterministic_signals(repo_root: Path, run: Mapping[str, Any]) -> dict[str, Any]`.
- Produces: `validate_audit_report_payload(payload: dict[str, Any]) -> None`.
- Produces: `write_deterministic_signals(repo_root: Path, run: Mapping[str, Any]) -> Path`.

- [ ] **Step 1: Write failing tests**

Cover the exact minimum schema from the spec: progress counters, repeat counters, hygiene counters, and tunnel-vision inputs. Verify `verdict=must_fix` is rejected without at least one open `must_fix` finding and without deterministic signal artifact provenance.

- [ ] **Step 2: Run tests and confirm failure**

Run: `python3 -m unittest scripts.tests.test_harness_loop_auditor scripts.tests.test_harness_loop_contracts -v`

- [ ] **Step 3: Implement contracts and deterministic computation**

Compute signals from run artifacts, child run summaries, evaluator results, dirty paths, required evidence results, trusted live evidence, git unpushed count, and coverage-map layer snapshots where present. Unknown signal fields are not emitted.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m unittest scripts.tests.test_harness_loop_auditor scripts.tests.test_harness_loop_contracts -v`

### Task 3: Add Audit Gate And Auditor Step

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Modify: `scripts/harness_loop_agents.py`

**Interfaces:**
- Consumes: `write_deterministic_signals(...)`, `validate_audit_report_payload(...)`.
- Produces: `run_audit(repo_root: Path, run_id: str, driver: str) -> Path`.
- Produces: `audit_gate(repo_root: Path, run: dict[str, Any]) -> dict[str, Any]`.

- [ ] **Step 1: Write failing orchestrator tests**

Test that an open `must_fix` audit report moves a parent run to `audit_blocked`, prevents new child planning, and forces `next_action="create_audit_remediation_task"`. Test autonomous runs block before ordinary planning. Test child runs do not enter `audit_blocked`.

- [ ] **Step 2: Run tests and confirm failure**

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v`

- [ ] **Step 3: Implement audit phases and gate wiring**

Add `audit_pending`, `auditing`, `audit_passed`, `audit_blocked` to contracts, allow `auditor` agent attempts, run deterministic signal writes after child/evaluator completion and before parent/autonomous planning, and enforce open `must_fix` before ordinary planning or human merge.

- [ ] **Step 4: Add minimal fake auditor driver**

`fake` auditor reads deterministic signals and emits `pass` when signals are healthy, `must_fix` when repeated evaluator findings or tunnel-vision counters cross policy thresholds. `codex-exec` support may call `run_codex_prompt(role="auditor", ...)` and must still be validated before artifact write.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m unittest scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_loop_agents -v`

### Task 4: Dashboard And E2E Verification For Real Engine

**Files:**
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`
- Modify: `scripts/loop_dashboard_evaluator.py`
- Create: `docs/harness/evaluator-scenarios/loop-auditor-engine-01.json`
- Modify: `tasks.json`
- Modify: `progress.md`

**Interfaces:**
- Consumes: real `deterministic-signals.json` and `audit-reports/audit-<n>.json`.
- Produces: dashboard evidence that real audit artifacts generated by orchestrator appear for `loop-auditor-engine-dev`.

- [ ] **Step 1: Write evaluator scenario and dashboard assertions**

The evaluator must run a fake audit scenario, then open the dashboard and verify: engine status, audit report path, deterministic signals, and `audit_blocked`/remediation text are visible.

- [ ] **Step 2: Run full verification**

Run:
`python3 -m unittest scripts.tests.test_harness_loop_auditor scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v`
`PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests`
`python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-auditor-engine-01`
`python3 -m json.tool tasks.json >/dev/null`
`git diff --check`

- [ ] **Step 3: Restart remote dashboard**

Restart tmux session `loop-dashboard` on `0.0.0.0:8766` from the feature worktree and verify `/api/runs/loop-auditor-engine-dev`.

- [ ] **Step 4: Commit**

Commit message: `feat(harness): add loop auditor engine`.
