# AI Infra Loop Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved AI infra loop governance controls and make the governance demand-development loop visible in Loop Dashboard.

**Architecture:** Extend the existing harness instead of adding a separate runner. `scripts/harness_loop_orchestrator.py` remains the state-machine entrypoint, focused helper modules own governance evidence, and Loop Dashboard continues reading `.codex/loop-runs/<run-id>/run.json`. The first implementation task must make real `run-demand-multi` codex-exec execution possible because the current command exposes codex drivers in help but rejects them at runtime.

**Tech Stack:** Python harness scripts and pytest, FastAPI Loop Dashboard backend, existing crawler workbench APIs, Playwright/live evaluator where frontend evidence is required, personal-wiki CLI validation.

## Global Constraints

- Do not create the next AI infra expansion run until governance is implemented or explicitly resumed.
- Keep `ai-infra-expansion-2026-07-07-r10` closed at `stopped_budget`; do not mutate its committed wiki artifacts except through a dedicated repair task.
- The governance run id is `ai-infra-loop-governance-dev`.
- The governance run must be visible in Loop Dashboard as a parent demand-development run with readable purpose, progress, next step, child tasks, and decision state.
- Do not commit `.codex/**`, pid/log files, `generated/**`, `.worktrees/**`, secrets, tokens, cookies, `.env`, build outputs, or dependency caches.
- Every implementation task uses TDD: write a failing test, run it red, implement, run it green.
- If evaluator formal suspicion confirms a bug, the same child task enters repair and must rerun the counterexample before pass.
- Wiki/crawler ingestion commits remain separate from harness/code/docs commits.
- Run `python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra` after touching `personal-wiki/domains/ai_infra/**`.
- Run targeted harness tests after touching `scripts/harness*.py`.

---

## File Structure

- Modify `scripts/harness_loop_orchestrator.py`: allow real demand multi-task loop execution with codex drivers, persist parent/child summaries, and route confirmed bugs back to repair.
- Create `scripts/harness_loop_governance.py`: pure helper functions for egress proof, identity keys, needs queues, candidate classification, depth-acquisition proof, formal suspicion artifacts, and source snapshot validation.
- Modify `scripts/harness_loop_contracts.py`: add validation for governance artifacts where shared schema checks belong.
- Test `scripts/tests/test_harness_loop_governance.py`: unit tests for identity key, scoring gates, needs queue, egress/depth proof, formal suspicion, and source snapshot drift.
- Modify `scripts/tests/test_harness_loop_orchestrator.py`: integration tests for real multi-task parent/child state transitions and repair on confirmed counterexample.
- Modify `apps/loop_dashboard/backend/loop_dashboard/store.py` only if existing dashboard summaries do not expose governance artifacts or formal verification details.
- Test `apps/loop_dashboard/backend/tests/test_store.py` only if dashboard store changes are needed.
- Modify `docs/harness/planner-generator-evaluator-loop.md`: document governance loop commands and formal suspicion pass.
- Create or update `docs/harness/evaluator-scenarios/ai-infra-loop-governance-dev-01.json`: evaluator scenario for governance implementation.

## Task 1: Real Demand Multi-Task Codex Execution

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Test: `scripts/tests/test_harness_loop_orchestrator.py`
- Update: `docs/harness/planner-generator-evaluator-loop.md`

**Interfaces:**
- Consumes: existing `run-demand-multi` CLI and parent/child run schema.
- Produces: `run-demand-multi` accepts `codex-exec` planner/generator/evaluator drivers without rejecting them, while preserving fake-driver tests.

- [ ] **Step 1: Write failing tests**

Add tests that prove `run_demand_multi(..., planner_driver="codex-exec", generator_driver="codex-exec", evaluator_driver="codex-exec")` does not fail with the current fake-only `ValueError`. Use monkeypatched command runners to avoid invoking Codex in unit tests.

- [ ] **Step 2: Run red test**

Run:

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py -k 'demand_multi and codex'
```

Expected before implementation: fails because `run_demand_multi initially supports fake planner drivers`.

- [ ] **Step 3: Implement minimal real-driver path**

Refactor `run_demand_multi` so fake drivers keep the current path and codex drivers call parent planner, child generator, and evaluator prompts through the existing `run_codex_prompt`/evaluator helpers. Keep parent/child dirty path inheritance and accepted paths rules intact.

- [ ] **Step 4: Run green tests**

Run:

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py
```

Expected: all orchestrator tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py docs/harness/planner-generator-evaluator-loop.md
git commit -m "feat(harness): run demand multi loops with codex drivers"
```

## Task 2: Governance Evidence Helpers

**Files:**
- Create: `scripts/harness_loop_governance.py`
- Test: `scripts/tests/test_harness_loop_governance.py`
- Modify: `scripts/harness_loop_contracts.py` if schema validation belongs there

**Interfaces:**
- Produces:
  - `canonical_identity_key(candidate: Mapping[str, Any]) -> str`
  - `classify_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]`
  - `record_needs_transition(item: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any]`
  - `validate_egress_proof(payload: Mapping[str, Any]) -> list[str]`
  - `validate_depth_acquisition_smoke(payload: Mapping[str, Any]) -> list[str]`
  - `validate_source_profile_snapshot(payload: Mapping[str, Any], db_rows: Mapping[str, Any]) -> list[str]`

- [ ] **Step 1: Write failing identity/scoring/needs tests**

Cover URL canonicalization, GitHub issue vs PR keys, hardware variant keys, high-value hard gates, advisory score non-authority, and needs-network cheap reprobe TTL.

- [ ] **Step 2: Run red test**

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_governance.py
```

Expected before implementation: import or function-not-found failures.

- [ ] **Step 3: Implement pure helpers**

Implement deterministic, side-effect-free helpers. Keep network probing outside these helpers; helpers validate probe payloads and state transitions.

- [ ] **Step 4: Run green tests**

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_governance.py
```

Expected: governance helper tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness_loop_governance.py scripts/tests/test_harness_loop_governance.py scripts/harness_loop_contracts.py
git commit -m "feat(harness): add ai infra governance evidence helpers"
```

## Task 3: Governance Preflight And Candidate Gates

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/harness_loop_governance.py`
- Test: `scripts/tests/test_harness_loop_orchestrator.py`
- Test: `scripts/tests/test_harness_loop_governance.py`

**Interfaces:**
- Consumes helper validators from Task 2.
- Produces run-local artifacts:
  - `.codex/loop-runs/<run-id>/egress-proof.json`
  - `.codex/loop-runs/<run-id>/depth-acquisition-smoke.json`
  - `.codex/loop-runs/<run-id>/candidate-scoring/*.json`
  - `.codex/loop-runs/<run-id>/identity-key-audit.json`

- [ ] **Step 1: Write failing preflight gate tests**

Tests prove governance cannot enter implementation child tasks when egress proof, identity key proof, or depth acquisition proof is missing.

- [ ] **Step 2: Run red test**

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py -k governance
```

Expected before implementation: governance preflight artifacts are not enforced.

- [ ] **Step 3: Implement governance preflight gates**

Add a governance mode or run constraint detection for `ai-infra-loop-governance-dev`. The run can stay `demand_development`, but planner prompts and evaluator manifests must require the P0 artifacts before implementation children proceed.

- [ ] **Step 4: Run green tests**

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_governance.py
```

Expected: governance preflight tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness_loop_orchestrator.py scripts/harness_loop_governance.py scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_governance.py
git commit -m "feat(harness): gate ai infra governance preflight evidence"
```

## Task 4: Formal Suspicion Evaluator Pass

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/harness_loop_governance.py`
- Test: `scripts/tests/test_harness_loop_governance.py`
- Test: `scripts/tests/test_harness_loop_orchestrator.py`

**Interfaces:**
- Produces:
  - `.codex/loop-runs/<run-id>/formal-verification/*.json`
  - `.codex/loop-runs/<run-id>/counterexample-tests/*`
  - evaluator results with `status=fail` and `next_action=repair_and_reevaluate` when `confirmed_bug`

- [ ] **Step 1: Write failing formal suspicion tests**

Tests cover confirmed bug, disproved suspicion, inconclusive high-risk suspicion, and repair requiring the original counterexample rerun.

- [ ] **Step 2: Run red test**

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_governance.py -k formal
```

Expected before implementation: formal suspicion functions are missing.

- [ ] **Step 3: Implement formal suspicion pass**

Implement artifact validation and orchestrator handling. Do not let unverified suspicion fail a task. Do not let confirmed bug pass without repair.

- [ ] **Step 4: Run green tests**

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_governance.py scripts/tests/test_harness_loop_orchestrator.py
```

Expected: formal suspicion and repair tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness_loop_governance.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_governance.py scripts/tests/test_harness_loop_orchestrator.py
git commit -m "feat(harness): add evaluator formal suspicion pass"
```

## Task 5: Crawler Source Snapshot And Dashboard Visibility

**Files:**
- Modify: `personal-wiki/apps/crawler_workbench/backend/**` only if snapshot export API is missing.
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py` only if governance artifacts are not readable in run detail.
- Test: `personal-wiki/apps/crawler_workbench/backend/tests/**`
- Test: `apps/loop_dashboard/backend/tests/test_store.py`

**Interfaces:**
- Produces repo-tracked non-sensitive source snapshot manifests under `personal-wiki/domains/ai_infra/manifest-<run-id>-source-profile-snapshot.json`.
- Dashboard detail for `ai-infra-loop-governance-dev` shows parent summary, child status, formal verification artifacts, evaluator scenarios, and decision state.

- [ ] **Step 1: Write failing snapshot/dashboard tests**

Tests prove stale SQLite snapshot fails validation and dashboard exposes formal verification artifacts in run detail.

- [ ] **Step 2: Run red tests**

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q
cd /home/fyz/codex-skills/.worktrees/ai-infra-meta-loop-runtime && PYTHONPATH=apps/loop_dashboard/backend pytest -q apps/loop_dashboard/backend/tests/test_store.py
```

Expected before implementation: snapshot or dashboard artifact assertions fail if missing.

- [ ] **Step 3: Implement minimal snapshot and dashboard support**

Add only the required non-sensitive export/validation path and dashboard artifact display support. Do not expose secrets or encrypted secret payloads.

- [ ] **Step 4: Run green tests**

```bash
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q
cd /home/fyz/codex-skills/.worktrees/ai-infra-meta-loop-runtime && PYTHONPATH=apps/loop_dashboard/backend pytest -q apps/loop_dashboard/backend/tests
```

Expected: crawler backend and dashboard backend tests pass.

- [ ] **Step 5: Commit**

```bash
git add personal-wiki/apps/crawler_workbench/backend apps/loop_dashboard/backend
git commit -m "feat(crawler): snapshot ai infra source governance state"
```

## Task 6: End-To-End Governance Loop Evaluation

**Files:**
- Create or modify: `docs/harness/evaluator-scenarios/ai-infra-loop-governance-dev-01.json`
- Modify: `scripts/loop_dashboard_evaluator.py` only if dashboard evaluator lacks needed assertions.
- Test: `scripts/tests/**` as needed

**Interfaces:**
- Produces evaluator scenario for:
  - E2E-0 egress/depth preflight
  - E2E-1 governance takeover after stopped-budget expansion
  - E2E-2 needs queue blocked split
  - E2E-3 high-value hard gates
  - E2E-4 crawler workbench linkage
  - E2E-5 wiki/API/frontend/dashboard visibility
  - E2E-6 formal suspicion repair loop
  - E2E-7 checkpoint and human merge readiness

- [ ] **Step 1: Write failing evaluator scenario test**

Add scenario metadata and a smoke/evaluator test that fails until all required governance artifacts are produced and dashboard can read the run.

- [ ] **Step 2: Run red test**

```bash
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/ai-infra-loop-governance-dev-01
```

Expected before final wiring: fails on missing governance run or artifacts.

- [ ] **Step 3: Complete final wiring**

Ensure the governance run and artifacts are visible in Loop Dashboard, all tests are wired into evaluator scenario metadata, and failed formal suspicion routes to repair.

- [ ] **Step 4: Run full verification**

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_governance.py scripts/tests/test_harness_loop_orchestrator.py
PYTHONPATH=apps/loop_dashboard/backend pytest -q apps/loop_dashboard/backend/tests
cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q
cd /home/fyz/codex-skills/.worktrees/ai-infra-meta-loop-runtime && python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/ai-infra-loop-governance-dev-01
```

Expected: all commands pass.

- [ ] **Step 5: Commit**

```bash
git add docs/harness/evaluator-scenarios scripts apps personal-wiki/apps/crawler_workbench/backend
git commit -m "test(harness): verify ai infra governance loop end to end"
```

## Execution Notes

- Start the governance demand-development run before implementation so it is visible in Loop Dashboard.
- If `run-demand-multi` cannot yet execute `codex-exec`, keep the parent run in `planning` with `next_action=run_parent_planner` and implement Task 1 first.
- Do not resume AI infra expansion as r11 until the governance parent run reaches `passed_waiting_human_merge` or the user explicitly overrides.
- Keep Loop Dashboard, crawler backend, and crawler frontend online during implementation verification when feasible.
