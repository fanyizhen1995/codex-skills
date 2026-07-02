# Planner Generator Evaluator Loop Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first usable `autonomous_knowledge` loop that can validate domain loop state, decide no-action, enforce autonomous path policies, auto-commit verified allowlisted work, and continue planning until budget or no-action stop.

**Architecture:** Extend the existing Phase 2 loop rather than replacing it. `scripts/harness_loop_contracts.py` owns Phase 3 schema validation and policy constants, `scripts/harness_loop_autonomous.py` owns domain loop-state, no-action, scope, supply-chain, auto-commit, and fake autonomous task helpers, and `scripts/harness_loop_orchestrator.py` coordinates the new CLI and state transitions.

**Tech Stack:** Python standard library, `unittest`, existing harness evaluator CLI/orchestrator, existing personal-wiki validation CLI, git command-line integration.

---

## File Structure

- Modify `scripts/harness_loop_contracts.py`: allow `autonomous_knowledge`, add `autonomous_implementation_task`, validate `loop-state.json`, validate loop policy files, and expose default autonomous allowlist/denylist helpers.
- Create `scripts/harness_loop_autonomous.py`: domain state creation/loading, no-action decision, scope checks, supply-chain checks, auto-commit helper, and deterministic fake autonomous generator/evaluator helpers used by tests and smoke.
- Modify `scripts/harness_loop_orchestrator.py`: allow autonomous preflight, add `run-autonomous`, route autonomous pass through hygiene, commit, cleanup, and next planning/no-action.
- Create `scripts/harness_loop_phase3_smoke.py`: self-contained smoke that exercises a passing autonomous task, auto-commit, second planning pass, and no-action stop.
- Modify `scripts/tests/test_harness_loop_contracts.py`: add red tests for autonomous policy, planner task kind, loop-state schema, policy schema, and no-action evidence requirements.
- Modify `scripts/tests/test_harness_loop_orchestrator.py`: add red tests for autonomous preflight, no-action stop, auto-commit, denylist blocking, supply-chain blocking, and CLI entrypoint.
- Create `scripts/tests/test_harness_loop_autonomous.py`: focused unit tests for state/no-action/scope/supply-chain/commit helpers.
- Create `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-3-01.json`: evaluator scenario calling the Phase 3 smoke helper.
- Create `docs/harness/loop-policies/demand-development.json` and `docs/harness/loop-policies/autonomous-knowledge.json`: documented policy fixtures.
- Modify `docs/harness/planner-generator-evaluator-loop.md`: Phase 3 operator commands and limits.
- Modify `tasks.json` and `progress.md`: mark Phase 3 done after final verification.

## Task 1: Phase 3 Contracts

**Files:**
- Modify: `scripts/harness_loop_contracts.py`
- Modify: `scripts/tests/test_harness_loop_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Add tests that prove:

```python
def test_validate_run_payload_accepts_autonomous_policy(self) -> None:
    payload = self._run_payload()
    payload["policy"] = "autonomous_knowledge"
    payload["phase"] = "planning"
    payload["domain"] = "ai_infra"
    payload["next_action"] = "run_autonomous_planner"
    validate_run_payload(payload)

def test_validate_planner_output_payload_accepts_autonomous_implementation_task(self) -> None:
    payload = self._planner_payload()
    payload["policy"] = "autonomous_knowledge"
    payload["task_kind"] = "autonomous_implementation_task"
    payload["next_planning_hint"] = "Continue with source backlog."
    validate_planner_output_payload(payload)

def test_validate_loop_state_payload_accepts_no_action_shape(self) -> None:
    validate_loop_state_payload(self._loop_state_payload())

def test_validate_loop_state_payload_rejects_unblocked_gap_without_evidence(self) -> None:
    payload = self._loop_state_payload()
    payload["coverage_gaps"] = [{
        "id": "gap-1",
        "title": "Missing source",
        "source": "manual",
        "status": "pending",
        "updated_at": "2026-07-02T00:00:00Z",
        "evidence": [],
    }]
    with self.assertRaisesRegex(ValueError, "coverage_gaps"):
        validate_loop_state_payload(payload)

def test_validate_loop_policy_payload_accepts_autonomous_policy_file(self) -> None:
    validate_loop_policy_payload({
        "policy": "autonomous_knowledge",
        "auto_commit": True,
        "auto_merge_main": False,
        "allowed_paths": ["personal-wiki/domains/**/wiki/**"],
        "manual_confirm_paths": ["tasks.json"],
        "denylist_paths": [".env", "**/secrets/**"],
        "limits": default_limits(),
        "required_evidence": ["wiki_validate"],
    })
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts.HarnessLoopContractsTests \
  -k 'autonomous or loop_state or loop_policy' -v
```

Expected: failures because validators do not exist or reject autonomous policy.

- [ ] **Step 3: Implement contract support**

Add:

```python
ALLOWED_TASK_KINDS = frozenset({
    "registered_task",
    "candidate_task",
    "task_contract_only",
    "autonomous_implementation_task",
})

REQUIRED_LOOP_STATE_ITEM_KEYS = frozenset({
    "id", "title", "source", "status", "updated_at", "evidence",
})
REQUIRED_BLOCKED_ITEM_KEYS = REQUIRED_LOOP_STATE_ITEM_KEYS | frozenset({
    "blocked_reason",
    "required_human_input",
    "retry_after",
    "retry_count",
    "last_error",
    "requires_user_input",
})
```

Implement `validate_loop_state_payload(payload)` and `validate_loop_policy_payload(payload)` using the local `_require_*` helpers. `validate_run_payload()` and `validate_planner_output_payload()` must normalize both supported policies and reject only unknown policies, not autonomous policy.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts -v
```

Expected: all contract tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness_loop_contracts.py scripts/tests/test_harness_loop_contracts.py
git commit -m "feat(harness): add autonomous loop contracts"
```

## Task 2: Autonomous Helpers

**Files:**
- Create: `scripts/harness_loop_autonomous.py`
- Create: `scripts/tests/test_harness_loop_autonomous.py`

- [ ] **Step 1: Write failing helper tests**

Cover:

```python
def test_create_default_loop_state_records_confirmed_no_action_standards(self) -> None:
    state = create_default_loop_state("ai_infra", "Expand wiki", scan_ttl_days=30)
    validate_loop_state_payload(state)
    self.assertEqual(state["domain"], "ai_infra")
    self.assertEqual(state["last_planner_decision"], "planned")

def test_decide_no_action_requires_empty_backlog_and_fresh_scan(self) -> None:
    state = create_default_loop_state("ai_infra", "Expand wiki", scan_ttl_days=30)
    state["candidate_backlog"] = []
    state["coverage_gaps"] = []
    state["known_sources"] = [{"id": "src-1", "title": "Source", "source": "manual", "status": "scanned", "updated_at": state["last_scan_at"], "evidence": ["checked"]}]
    state["no_action_evidence"] = [{"id": "scan-1", "title": "Scan", "source": "planner", "status": "complete", "updated_at": state["last_scan_at"], "evidence": ["no candidates"]}]
    self.assertTrue(decide_no_action(state).no_action)

def test_scope_check_rejects_denylist_even_when_allowlist_matches(self) -> None:
    result = check_autonomous_scope(["personal-wiki/domains/ai_infra/wiki/page.md", ".env"], autonomous_allowed_paths(), autonomous_denylist_paths())
    self.assertFalse(result.allowed)
    self.assertIn(".env", result.denied_paths)

def test_supply_chain_check_requires_explanation_for_dependency_paths(self) -> None:
    result = check_supply_chain(["requirements.txt"], explanation="", verification=["pytest"])
    self.assertFalse(result.allowed)
    self.assertIn("missing dependency necessity", result.findings[0])
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_autonomous -v
```

Expected: import failure because helper module does not exist.

- [ ] **Step 3: Implement helpers**

Implement dataclasses:

```python
@dataclass(frozen=True)
class NoActionDecision:
    no_action: bool
    reasons: list[str]

@dataclass(frozen=True)
class ScopeCheckResult:
    allowed: bool
    allowed_paths: list[str]
    denied_paths: list[str]
    manual_confirm_paths: list[str]
    findings: list[str]
```

Implement:

- `create_default_loop_state(domain, domain_goal, scan_ttl_days=30)`
- `load_or_create_loop_state(repo_root, domain, domain_goal, scan_ttl_days=30)`
- `write_loop_state(repo_root, domain, state)`
- `decide_no_action(state, now=None)`
- `autonomous_allowed_paths()`
- `autonomous_manual_confirm_paths()`
- `autonomous_denylist_paths()`
- `check_autonomous_scope(changed_paths, allowed_patterns, deny_patterns, manual_confirm_patterns=None)`
- `check_supply_chain(changed_paths, explanation, verification)`
- `run_git_commit(repo_root, paths, message)`

Path matching should use `fnmatch.fnmatch(path, pattern)` and a fallback prefix check for patterns ending in `/**`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_autonomous -v
```

Expected: helper tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness_loop_autonomous.py scripts/tests/test_harness_loop_autonomous.py
git commit -m "feat(harness): add autonomous loop helpers"
```

## Task 3: Orchestrator Autonomous State Machine

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`

- [ ] **Step 1: Write failing orchestrator tests**

Add tests for:

- `create_preflight_run(... mode="autonomous-knowledge", domain="ai_infra", confirm=True)` starts at `planning`.
- `run_autonomous(... fake drivers ...)` stops at `stopped_no_action` when `loop-state.json` has no backlog/gaps and fresh evidence.
- `run_autonomous(... fake drivers ...)` commits an allowlisted wiki/raw change and returns to planning, then stops at no-action on the next pass.
- denylist path in `generator-result.json` stops at `stopped_blocked`.
- dependency path without supply-chain evidence stops at `stopped_blocked`.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopOrchestratorTests \
  -k autonomous -v
```

Expected: failures because `domain` CLI/preflight and `run_autonomous` do not exist.

- [ ] **Step 3: Implement preflight and run-autonomous**

Changes:

- Add `domain` argument to `create_preflight_run()` and CLI `preflight`.
- Permit `autonomous_knowledge` policy. Confirmed autonomous preflight starts at `planning` with `next_action=run_autonomous_planner`.
- Add `run_autonomous(repo_root, run_id, planner_driver, generator_driver, evaluator_driver, max_eval_attempts, max_tasks)`.
- Add CLI subcommand:

```bash
python3 scripts/harness_loop_orchestrator.py run-autonomous \
  --repo-root . \
  --run-id <run-id> \
  --planner-driver fake \
  --generator-driver fake \
  --evaluator-driver fake \
  --max-eval-attempts 2 \
  --max-tasks 3
```

Fake autonomous behavior:

- If `loop-state.json` has no-action evidence and no actionable backlog/gaps, stop at `stopped_no_action`.
- Otherwise fake planner writes `planner-output.json` with `policy=autonomous_knowledge` and `task_kind=autonomous_implementation_task`.
- Fake generator writes a deterministic allowlisted raw note under `personal-wiki/domains/<domain>/raw/loop-autonomous/<run-id>-task-<n>.md`, updates `loop-state.json`, writes `generator-result.json`, and leaves the changed paths for evaluator/hygiene.
- Fake evaluator uses the existing fake evaluator path when a task contract/scenario exists; otherwise writes a pass payload for the fake autonomous smoke only.
- On pass, run artifact hygiene, check scope, run supply-chain check, validate wiki if `personal-wiki/` exists, git commit allowlisted changes, cleanup, and return to `planning`.
- Stop at `stopped_budget` after `max_tasks`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
```

Expected: orchestrator tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py
git commit -m "feat(harness): run autonomous knowledge loop"
```

## Task 4: Policy Files, Smoke, Scenario, Docs

**Files:**
- Create: `scripts/harness_loop_phase3_smoke.py`
- Create: `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-3-01.json`
- Create: `docs/harness/loop-policies/demand-development.json`
- Create: `docs/harness/loop-policies/autonomous-knowledge.json`
- Modify: `docs/harness/planner-generator-evaluator-loop.md`
- Modify: `scripts/tests/test_harness_evaluator_scenarios.py`
- Modify: `tasks.json`
- Modify: `progress.md`

- [ ] **Step 1: Write failing scenario/smoke tests**

Add tests that:

- Load the Phase 3 evaluator scenario.
- Assert its entrypoint uses `scripts/harness_loop_phase3_smoke.py`.
- Run the smoke helper in a temp repo and assert final phase is `stopped_no_action`, at least one commit was created, and `loop-state.json` validates.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v
```

Expected: Phase 3 scenario missing.

- [ ] **Step 3: Implement smoke and docs**

Smoke helper flow:

```bash
python3 scripts/harness_loop_phase3_smoke.py \
  --repo-root . \
  --run-id evaluator-scenario-phase-3 \
  --domain ai_infra \
  --task-id planner-generator-evaluator-loop-phase-3-01
```

It should:

- Remove previous smoke run artifacts for that run id.
- Create confirmed autonomous preflight.
- Seed `personal-wiki/domains/<domain>/loop-state.json` with one candidate backlog item.
- Run autonomous fake loop with `max_tasks=2`.
- Verify first pass created a commit and second pass stopped at no-action.
- Print JSON with `phase`, `next_action`, `commit`, `loop_state_path`, and run artifact paths.

- [ ] **Step 4: Update task metadata**

Set `planner-generator-evaluator-loop-phase-3-01` to `done`, update verify command to include new tests and Phase 3 smoke, and prepend a `progress.md` entry with evidence.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_artifacts scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_evaluator_cli scripts.tests.test_harness_evaluator_orchestrator scripts.tests.test_harness_evaluator_hooks scripts.tests.test_harness_evaluator_scenarios -v
python3 scripts/harness_loop_phase3_smoke.py --repo-root . --run-id evaluator-scenario-phase-3 --domain ai_infra --task-id planner-generator-evaluator-loop-phase-3-01
python3 -m json.tool tasks.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-3-01.json >/dev/null
python3 -m json.tool docs/harness/loop-policies/autonomous-knowledge.json >/dev/null
git diff --check
```

Expected: all checks pass. Remove smoke-generated `.codex` and wiki raw artifacts before final commit if they are not intentionally part of the implementation.

- [ ] **Step 6: Commit**

```bash
git add scripts/harness_loop_phase3_smoke.py scripts/tests/test_harness_evaluator_scenarios.py docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-3-01.json docs/harness/loop-policies docs/harness/planner-generator-evaluator-loop.md tasks.json progress.md
git commit -m "docs(harness): document autonomous loop phase 3"
```

## Final Verification

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_artifacts scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_loop_orchestrator scripts.tests.test_harness_evaluator_cli scripts.tests.test_harness_evaluator_orchestrator scripts.tests.test_harness_evaluator_hooks scripts.tests.test_harness_evaluator_scenarios -v
python3 scripts/harness_loop_phase3_smoke.py --repo-root . --run-id evaluator-scenario-phase-3 --domain ai_infra --task-id planner-generator-evaluator-loop-phase-3-01
python3 -m json.tool tasks.json >/dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-3-01.json >/dev/null
python3 -m json.tool docs/harness/loop-policies/autonomous-knowledge.json >/dev/null
python3 -m json.tool docs/harness/loop-policies/demand-development.json >/dev/null
git diff --check
```

Then run the evaluator task loop:

```bash
python3 scripts/harness_evaluator_orchestrator.py run-task-loop \
  --driver fake \
  --task-id planner-generator-evaluator-loop-phase-3-01 \
  --repo-root . \
  --max-attempts 2
```

Expected:

- Unit tests pass.
- Phase 3 smoke ends at `stopped_no_action` after creating an autonomous commit in its smoke sandbox.
- Evaluator scenario passes.
- Worktree is clean except intentionally retained `.codex/loop-runs/planner-loop-phase-3-dev` demand-development evidence if we decide to keep it.
