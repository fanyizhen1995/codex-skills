# Unified Loop Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the overlapping Supervisor, auto-resume, orchestrator, and Auditor control roles with one SQLite-backed Loop Supervisor, an independent Executor Worker, a real project-global LLM Reviewer, and a paginated mock-matching Dashboard.

**Architecture:** Add a focused `scripts/loop_supervisor/` package that owns contracts, the transition registry, SQLite control state, reconciliation, recovery, Reviewer scheduling, and bounded Worker actions. Existing orchestrator functions are temporarily consumed only as internal phase primitives; the Worker must never call the old multi-round `run_autonomous()` or `run_demand_multi()` loops. Dashboard APIs query SQLite with stable cursors, while large evidence and logs remain safe file artifacts loaded on demand.

**Tech Stack:** Python 3.12 standard library (`sqlite3`, `dataclasses`, subprocess), pytest/unittest, existing Codex CLI adapter, FastAPI, vanilla JavaScript/CSS, Playwright, tmux, git.

## Global Constraints

- Binding spec: `docs/superpowers/specs/2026-07-14-loop-supervisor-unification-design.md`.
- Frontend acceptance contract: `docs/superpowers/mockups/2026-07-14-loop-supervisor-unification-mock.html`.
- Public loop roles after cutover are Supervisor, Supervisor Reviewer, Worker, Planner, Generator, and Evaluator.
- Remove independent auto-resume, Auditor, and public orchestrator runtime roles before marking the task complete.
- Supervisor makes every scheduling, retry, refocus, stop, and user-escalation decision from one transition registry.
- Worker executes one bounded action and never chooses the next action.
- Same-repository Git mutations are serialized; read-only checks and Reviewer preparation may run concurrently.
- Retry one action at most three times, then run one alternate recovery plan, then invoke Reviewer.
- Reviewer failure is fail-open when deterministic safety gates pass.
- User decisions are run-scoped except for secret exposure, repository corruption, permission expansion, irreversible operations, or explicit global stop.
- Regular Reviewer cadence is every two completed semantic parents per `loop_lineage_id`, carried across continuations; concurrent due lineages within ten minutes are coalesced.
- Runtime SQLite and service state under `.codex/` are never committed.
- Preserve current parent-22 partial work, crawler raw captures, and all pre-existing dirty paths during migration.
- Record state changes, not unchanged 30-second ticks; rotate exports at 10 MB and retain detailed history for 90 days.
- Dashboard collections use server-side cursor pagination, default 20, allowed 20/50/100.
- Long log content is fetched on demand through a bounded, redacted, path-safe endpoint.
- Keep Crawler Workbench backend/frontend and Loop Dashboard online and remote-accessible except for documented short restarts during cutover.
- Each task uses TDD, has focused verification, receives specification and code-quality review, and creates a scoped commit.
- Final acceptance includes parent-22 recovery and four consecutive semantic parent tasks without manual phase commands.

---

## File Structure

### New runtime package

- `scripts/loop_supervisor/__init__.py`: public package exports only.
- `scripts/loop_supervisor/models.py`: enums, dataclasses, result and review schemas.
- `scripts/loop_supervisor/registry.py`: single phase/next-action transition registry.
- `scripts/loop_supervisor/store.py`: SQLite migrations, transactions, action leasing, failures, decisions, reviews, pagination, retention.
- `scripts/loop_supervisor/executor.py`: bounded phase action dispatch into existing low-level harness functions.
- `scripts/loop_supervisor/worker.py`: action lease loop, heartbeat, repository lock, result persistence.
- `scripts/loop_supervisor/recovery.py`: error classification, three retries, partial-artifact recovery, alternate plan selection.
- `scripts/loop_supervisor/reviewer.py`: deterministic evidence bundle, Codex Reviewer call, schema validation, cadence, Skill Governance.
- `scripts/loop_supervisor/reconciler.py`: run discovery, SQLite projection, desired-action computation, continuation and service decisions.
- `scripts/loop_supervisor/migration.py`: snapshot inventory, JSONL compaction, legacy cleanup, shadow comparison, rebuild.
- `scripts/loop_supervisor/cli.py`: `watch`, `worker`, `once`, `review`, `migrate`, `shadow-compare`, and `status` commands.
- `scripts/harness_loop_supervisor.py`: thin executable wrapper around `scripts.loop_supervisor.cli.main` during the filename compatibility period.

### Runtime tests

- `scripts/tests/test_harness_loop_supervisor_models.py`
- `scripts/tests/test_harness_loop_supervisor_registry.py`
- `scripts/tests/test_harness_loop_supervisor_store.py`
- `scripts/tests/test_harness_loop_supervisor_executors.py`
- `scripts/tests/test_harness_loop_supervisor_worker.py`
- `scripts/tests/test_harness_loop_supervisor_recovery.py`
- `scripts/tests/test_harness_loop_supervisor_reviewer.py`
- `scripts/tests/test_harness_loop_supervisor_migration.py`
- Existing `scripts/tests/test_harness_loop_supervisor.py` becomes reconciler/service/CLI integration coverage.

### Dashboard

- `apps/loop_dashboard/backend/loop_dashboard/supervisor_store.py`: SQLite read model and paginated Supervisor queries.
- `apps/loop_dashboard/backend/loop_dashboard/pagination.py`: cursor codec and page response helpers.
- `apps/loop_dashboard/backend/loop_dashboard/main.py`: paginated APIs and safe log detail route.
- `apps/loop_dashboard/backend/loop_dashboard/store.py`: run projection and paged run artifact queries; remove legacy Auditor/JSONL Supervisor readers.
- `apps/loop_dashboard/backend/loop_dashboard/models.py`: paged log/event metadata models.
- `apps/loop_dashboard/frontend/pagination.js`: reusable page state and pager rendering.
- `apps/loop_dashboard/frontend/supervisor.js`: real Supervisor tabs and lazy paged data loading.
- Existing `app.js`: run selection, detail tabs, and integration with the two focused frontend modules.
- Existing `index.html` and `styles.css`: mock-matching structure and responsive styles.

### Evaluation and docs

- `scripts/loop_supervisor_e2e_evaluator.py`: isolated runtime, migration, Worker crash, Reviewer, and live-soak evaluator.
- `docs/harness/evaluator-scenarios/loop-supervisor-unification-01.json`: browser and runtime scenarios.
- `docs/harness/loop-supervisor.md`: final operations and recovery guide.
- `AGENTS.md`: new long-running service commands and old service removal.
- `tasks.json` and `progress.md`: task state and final evidence.

---

### Task 1: Shared Models And Transition Registry

**Files:**
- Create: `scripts/loop_supervisor/__init__.py`
- Create: `scripts/loop_supervisor/models.py`
- Create: `scripts/loop_supervisor/registry.py`
- Create: `scripts/tests/test_harness_loop_supervisor_models.py`
- Create: `scripts/tests/test_harness_loop_supervisor_registry.py`
- Modify: `scripts/harness_loop_contracts.py`
- Modify: `scripts/tests/test_harness_loop_contracts.py`

**Interfaces:**
- Produces `ActionType`, `ActionStatus`, `ActionResultClass`, `ActionRequest`, `ActionResult`, `TransitionRule`, `ReviewDecision`.
- Produces `transition_for(policy: str, phase: str, next_action: str) -> TransitionRule`.
- Produces `validate_registry_coverage() -> None`.
- Consumes the allowed policy and phase values from `harness_loop_contracts.py`.

- [ ] **Step 1: Write failing model and registry tests**

```python
def test_every_allowed_parent_phase_has_registry_behavior():
    validate_registry_coverage()

def test_generator_inspection_maps_to_recovery_not_user_decision():
    rule = transition_for("autonomous_knowledge", "stopped_blocked", "inspect_autonomous_generator")
    assert rule.action_type is ActionType.RECOVER_GENERATOR_RESULT
    assert rule.user_escalation is False

def test_action_result_requires_failure_key_for_non_success():
    with pytest.raises(ValueError, match="failure_key"):
        ActionResult(result_class=ActionResultClass.RETRYABLE_FAILURE, summary="capacity")
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_registry.py`

Expected: FAIL because `scripts.loop_supervisor` does not exist.

- [ ] **Step 3: Implement strict models**

```python
class ActionResultClass(StrEnum):
    SUCCESS = "success"
    RETRYABLE_FAILURE = "retryable_failure"
    RECOVERABLE_PARTIAL = "recoverable_partial"
    POLICY_BLOCK = "policy_block"
    TERMINAL_FAILURE = "terminal_failure"

@dataclass(frozen=True)
class ActionResult:
    result_class: ActionResultClass
    summary: str
    failure_key: str = ""
    error_class: str = ""
    artifact_paths: tuple[str, ...] = ()
    checkpoint: str = ""

    def __post_init__(self) -> None:
        if self.result_class is not ActionResultClass.SUCCESS and not self.failure_key:
            raise ValueError("non-success ActionResult requires failure_key")
```

Use enums for every action visible in the spec, including `run_planner`, `run_generator`, `run_evaluator`, evidence gates, commit/push/cleanup, continuation, service restart, partial recovery, alternate recovery, Reviewer, refocus, stop run, and ask user.

- [ ] **Step 4: Implement the table-driven registry**

```python
REGISTRY: dict[tuple[str, str, str], TransitionRule] = {
    ("autonomous_knowledge", "planning", "run_autonomous_planner"): TransitionRule(ActionType.RUN_PLANNER, True),
    ("autonomous_knowledge", "generating", "run_autonomous_generator"): TransitionRule(ActionType.RUN_GENERATOR, True),
    ("autonomous_knowledge", "evaluating", "run_autonomous_evaluator"): TransitionRule(ActionType.RUN_EVALUATOR, False),
    ("autonomous_knowledge", "stopped_blocked", "inspect_autonomous_generator"): TransitionRule(
        ActionType.RECOVER_GENERATOR_RESULT, True, user_escalation=False
    ),
}
```

Represent wildcard next actions explicitly with a sentinel instead of hidden `if` branches. `validate_registry_coverage()` must compare contract-allowed phases and intentional terminal exclusions.

- [ ] **Step 5: Run focused and contract tests**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_contracts.py`

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add scripts/loop_supervisor scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/harness_loop_contracts.py scripts/tests/test_harness_loop_contracts.py
git commit -m "feat(harness): add unified supervisor transition contracts"
```

---

### Task 2: SQLite Control Store, Queue, And Cursor Primitives

**Files:**
- Create: `scripts/loop_supervisor/store.py`
- Create: `scripts/tests/test_harness_loop_supervisor_store.py`

**Interfaces:**
- Produces `SupervisorStore.open(project_root: Path) -> SupervisorStore`.
- Produces `migrate()`, `upsert_run_projection()`, `enqueue_action()`, `lease_next_action()`, `renew_lease()`, `complete_action()`, `record_transition()`, `record_failure()`, `open_user_decision()`, `close_user_decision()`, `record_review()`, `list_page()`.
- Stores only summaries and safe artifact references, not full stdout/stderr.

- [ ] **Step 1: Write failing migration and queue tests**

```python
def test_migrate_creates_all_required_tables(tmp_path):
    store = SupervisorStore.open(tmp_path)
    store.migrate()
    assert set(store.table_names()) >= {
        "runs", "actions", "action_attempts", "transitions", "failures",
        "reviews", "review_findings", "user_decisions", "services",
        "freshness_checks", "skill_snapshots", "aggregates",
    }

def test_enqueue_action_is_idempotent_and_state_change_is_not_duplicated(tmp_path):
    store = migrated_store(tmp_path)
    first = store.enqueue_action(action_request("run-1", revision=3))
    second = store.enqueue_action(action_request("run-1", revision=3))
    assert first.action_id == second.action_id
    assert store.count("actions") == 1

def test_expired_lease_can_be_reclaimed_once(tmp_path, clock):
    store = migrated_store(tmp_path, clock=clock)
    action = store.enqueue_action(action_request("run-1", revision=1))
    assert store.lease_next_action("worker-a", lease_seconds=120).action_id == action.action_id
    clock.advance(seconds=121)
    assert store.lease_next_action("worker-b", lease_seconds=120).action_id == action.action_id
    assert store.lease_next_action("worker-c", lease_seconds=120) is None
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py`

Expected: FAIL because the store does not exist.

- [ ] **Step 3: Implement schema migration 1**

Use `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, and `PRAGMA busy_timeout=5000`. The `actions` table must include a unique `idempotency_key`, lease owner/deadline, run revision, action type, status, priority, recovery tier, timestamps, and artifact JSON. The `transitions` table must have a unique `(run_id, from_revision, to_revision)` constraint.

```sql
CREATE TABLE actions (
  action_id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  run_id TEXT NOT NULL,
  run_revision INTEGER NOT NULL,
  action_type TEXT NOT NULL,
  status TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 100,
  recovery_tier INTEGER NOT NULL DEFAULT 0,
  lease_owner TEXT NOT NULL DEFAULT '',
  lease_expires_at TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

- [ ] **Step 4: Implement transaction-safe queue and transition updates**

Use `BEGIN IMMEDIATE` for lease and completion operations. Completing an action and recording its attempt must happen in one transaction. An unchanged reconcile updates `last_seen_at` on the projection and must not add a transition row.

- [ ] **Step 5: Implement cursor primitives and retention compaction**

Encode cursors as URL-safe base64 JSON containing schema version, sort timestamp, primary key, and direction. Reject malformed or mismatched cursors. Implement page sizes `{20, 50, 100}` and stable `(created_at DESC, primary_key DESC)` ordering. Compact rows older than 90 days into daily aggregates before deletion.

- [ ] **Step 6: Run store tests**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py`

Expected: PASS, including concurrent lease and pagination boundary tests.

- [ ] **Step 7: Commit Task 2**

```bash
git add scripts/loop_supervisor/store.py scripts/tests/test_harness_loop_supervisor_store.py
git commit -m "feat(harness): add supervisor sqlite control store"
```

---

### Task 3: Reconciler, Continuations, And Run-Scoped Decisions

**Files:**
- Create: `scripts/loop_supervisor/reconciler.py`
- Modify: `scripts/harness_loop_supervisor.py`
- Modify: `scripts/tests/test_harness_loop_supervisor.py`
- Modify: `scripts/tests/test_harness_loop_supervisor_state.py`

**Interfaces:**
- Produces `reconcile_once(project_root: Path, store: SupervisorStore, *, shadow: bool = False) -> ReconcileResult`.
- Produces `desired_action_for_run(run: Mapping[str, Any]) -> ActionRequest | None`.
- Consumes Task 1 registry and Task 2 store.

- [ ] **Step 1: Write failing reconciliation tests**

```python
def test_reconcile_generator_block_queues_recovery_without_user_decision(tmp_path):
    seed_run(tmp_path, phase="stopped_blocked", next_action="inspect_autonomous_generator")
    result = reconcile_once(tmp_path, migrated_store(tmp_path))
    assert result.queued_actions[0].action_type is ActionType.RECOVER_GENERATOR_RESULT
    assert result.open_user_decisions == []

def test_run_scoped_decision_does_not_block_independent_continuation(tmp_path):
    seed_run(tmp_path, run_id="blocked", unsafe_secret=True)
    seed_stopped_budget_run(tmp_path, run_id="safe", lineage_id="lineage-safe")
    result = reconcile_once(tmp_path, migrated_store(tmp_path))
    assert result.decision_for("blocked").scope == "run"
    assert result.action_for("safe").action_type is ActionType.CREATE_CONTINUATION

def test_unchanged_tick_does_not_append_transition(tmp_path):
    store = migrated_store(tmp_path)
    seed_run(tmp_path, phase="planning")
    reconcile_once(tmp_path, store)
    reconcile_once(tmp_path, store)
    assert store.count("transitions") == 1
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor.py`

Expected: FAIL on missing Reconciler behavior.

- [ ] **Step 3: Implement run discovery and projection**

Read root and non-symlink worktree run files with path containment. Add `state_revision` to new writes and replace legacy `save_run` with `atomic_save_run`: write a sibling temporary file, flush and `fsync`, then `os.replace` it and `fsync` the parent directory. Increment revision exactly once per accepted state transition. For legacy runs without the field, derive revision zero and upgrade on the first new transition. Invalid JSON creates a run-scoped terminal failure record, except repository ownership failures, which use global scope.

- [ ] **Step 4: Implement desired action and continuation logic**

All decisions call `transition_for(...)`. Continuation keys include lineage, source run, semantic parent, and source commit. Continue only leaf runs; continuation creation itself is queued for Worker execution and not performed inside reconcile.

- [ ] **Step 5: Replace legacy JSONL decision writes**

`harness_loop_supervisor.py` becomes a wrapper that opens SQLite and calls the new Reconciler. It may export bounded status JSON for compatibility, but it must stop appending unchanged run decisions and must not read Auditor control files.

- [ ] **Step 6: Run reconciler and existing Supervisor tests**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_store.py`

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add scripts/loop_supervisor/reconciler.py scripts/harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor_state.py
git commit -m "feat(harness): reconcile loops through supervisor queue"
```

---

### Task 4: Bounded Executor And Independent Worker

**Files:**
- Create: `scripts/loop_supervisor/executor.py`
- Create: `scripts/loop_supervisor/worker.py`
- Create: `scripts/tests/test_harness_loop_supervisor_executors.py`
- Create: `scripts/tests/test_harness_loop_supervisor_worker.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Modify: `scripts/harness_loop_runtime_lock.py`

**Interfaces:**
- Produces `execute_action(request: ActionRequest, repo_root: Path) -> ActionResult`.
- Produces `worker_once(project_root: Path, worker_id: str) -> WorkerResult`.
- Produces `worker_watch(project_root: Path, worker_id: str, poll_seconds: float) -> None`.
- Existing orchestrator exposes bounded phase primitives but no Supervisor decisions.

- [ ] **Step 1: Write failing Worker tests**

```python
def test_worker_executes_one_action_and_never_calls_multi_round_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(legacy, "run_autonomous", forbidden)
    monkeypatch.setattr(legacy, "run_demand_multi", forbidden)
    action = enqueue(tmp_path, ActionType.RUN_GENERATOR)
    result = worker_once(tmp_path, "worker-1")
    assert result.action_id == action.action_id
    assert result.status == "completed"

def test_worker_crash_leaves_reclaimable_lease(tmp_path, clock):
    enqueue(tmp_path, ActionType.RUN_PLANNER)
    simulate_worker_exit_after_lease(tmp_path, "worker-a")
    clock.advance(seconds=121)
    assert worker_once(tmp_path, "worker-b").status == "completed"

def test_repository_mutation_lock_serializes_different_runs(tmp_path):
    first = hold_repository_mutation_lock(tmp_path, owner="worker-a")
    with pytest.raises(RunLockBusy):
        execute_mutating_action(tmp_path, run_id="run-b", owner="worker-b")
    first.release()
```

In `test_harness_loop_supervisor_executors.py`, assert every executable registry action has exactly one bounded handler, each handler returns `ActionResult`, and no handler calls `run_autonomous()` or `run_demand_multi()`.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py`

Expected: FAIL because Worker and bounded dispatcher do not exist.

- [ ] **Step 3: Expose bounded legacy phase primitives**

Add narrow functions for one autonomous/demand Planner, Generator, Evaluator, evidence-gate, commit/push, cleanup, continuation, refocus, and stop action. These functions may reuse existing private helpers but must return `ActionResult` and must not loop into another phase.

```python
def execute_action(request: ActionRequest, repo_root: Path) -> ActionResult:
    handler = ACTION_HANDLERS[request.action_type]
    return handler(repo_root, request)
```

Tests must prove `ACTION_HANDLERS` has one handler per executable registry action.

- [ ] **Step 4: Implement Worker leases and heartbeat**

The Worker leases one action, starts a heartbeat thread that renews both Worker and action leases, acquires per-run and optional repository mutation locks, executes one handler, and atomically records the result. SIGTERM stops new leases and lets the current handler write interruption evidence.

- [ ] **Step 5: Deprecate multi-round orchestrator entrypoints**

Supervisor/Worker code must not call `run_autonomous()` or `run_demand_multi()`. Keep them temporarily for old tests only until Task 9 removes public CLI use. Add a deprecation guard so production invocation prints the Supervisor replacement command.

- [ ] **Step 6: Run Worker, lock, and orchestrator regression tests**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_runtime_lock.py && python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v`

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

```bash
git add scripts/loop_supervisor/executor.py scripts/loop_supervisor/worker.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py scripts/harness_loop_runtime_lock.py
git commit -m "feat(harness): execute supervisor actions through worker"
```

---

### Task 5: Three-Tier Recovery And Partial Artifact Salvage

**Files:**
- Create: `scripts/loop_supervisor/recovery.py`
- Create: `scripts/tests/test_harness_loop_supervisor_recovery.py`
- Modify: `scripts/loop_supervisor/reconciler.py`
- Modify: `scripts/loop_supervisor/executor.py`
- Modify: `scripts/harness_loop_agents.py`
- Modify: `scripts/tests/test_harness_loop_agents.py`

**Interfaces:**
- Produces `classify_attempt_failure(attempt: Mapping[str, Any]) -> FailureClassification`.
- Produces `plan_recovery(store, run, action_result) -> RecoveryPlan`.
- Produces `inspect_partial_artifacts(repo_root, run, action_type) -> PartialArtifactAssessment`.
- Produces `reconstruct_result_envelope(...) -> Path` with explicit recovery provenance.

- [ ] **Step 1: Write failing error classification and retry tests**

```python
@pytest.mark.parametrize((message, expected), [
    ("Selected model is at capacity", "model_capacity"),
    ("stream disconnected before completion", "sse_disconnect"),
    ("Temporary failure in name resolution", "dns_failure"),
    ("fatal: Unable to create '.git/index.lock'", "git_lock"),
])
def test_classify_retryable_errors(message, expected):
    assert classify_attempt_failure({"stderr": message}).error_class == expected

def test_three_retries_then_one_alternate_plan(tmp_path):
    store = migrated_store(tmp_path)
    for _ in range(3):
        record_retryable_failure(store, "run-1", "generator:model_capacity")
    plan = plan_recovery(store, load_run(tmp_path, "run-1"), latest_result(store))
    assert plan.tier == 2
    assert plan.action_type is ActionType.RECOVER_GENERATOR_RESULT
    assert store.open_user_decisions(run_id="run-1") == []
```

- [ ] **Step 2: Write the parent-22 partial recovery fixture test**

Copy only the structural shape of the current parent-22 artifacts into a temp repo. The test must include two timeout attempts, a valid gap proof, verification manifest, declared changed paths, and no final Generator envelope.

```python
def test_parent22_timeout_artifacts_reconstruct_generator_result_then_evaluate(tmp_path):
    seed_parent22_partial_fixture(tmp_path)
    assessment = inspect_partial_artifacts(tmp_path, load_run(tmp_path, PARENT22_RUN_ID), ActionType.RUN_GENERATOR)
    assert assessment.status == "recoverable"
    path = reconstruct_result_envelope(tmp_path, assessment)
    payload = read_json_file(path)
    assert payload["recovery"]["recovered_from_attempts"] == [3, 4]
    assert payload["status"] == "implemented"
```

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py`

Expected: FAIL because recovery module does not exist.

- [ ] **Step 4: Implement failure taxonomy and backoff**

Store stable failure keys by lineage/run/task/action/error class. Retry delays are deterministic under an injected clock/random source for tests. A successful attempt closes the failure; a later occurrence starts a new recovery episode while retaining lifetime aggregate count.

- [ ] **Step 5: Implement partial artifact assessment**

Use existing contract validators, expected output paths, verification evidence, task ownership, baseline dirty paths, and secret/scope checks. Do not infer success from file existence alone. Return `recoverable`, `missing_work`, or `unsafe` plus exact missing checks.

- [ ] **Step 6: Implement bounded alternate recovery**

Allow exactly one alternate plan per recovery episode: reconstruct envelope, run missing verification, resume checkpoint, shrink task, or replan excluding the failed approach. Record the selected strategy in SQLite and the reconstructed envelope. Evaluator acceptance remains mandatory.

- [ ] **Step 7: Run recovery and agent tests**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_supervisor_worker.py`

Expected: PASS.

- [ ] **Step 8: Commit Task 5**

```bash
git add scripts/loop_supervisor/recovery.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/loop_supervisor/reconciler.py scripts/loop_supervisor/executor.py scripts/harness_loop_agents.py scripts/tests/test_harness_loop_agents.py
git commit -m "feat(harness): recover partial loop action artifacts"
```

---

### Task 6: Project-Global LLM Reviewer And Skill Governance

**Files:**
- Create: `scripts/loop_supervisor/reviewer.py`
- Create: `scripts/tests/test_harness_loop_supervisor_reviewer.py`
- Modify: `scripts/loop_supervisor/models.py`
- Modify: `scripts/loop_supervisor/reconciler.py`
- Modify: `scripts/harness_loop_agents.py`
- Modify: `scripts/harness_loop_contracts.py`
- Delete after migration tests move: `scripts/harness_loop_auditor.py`
- Modify/delete: `scripts/tests/test_harness_loop_auditor.py`

**Interfaces:**
- Produces `build_review_evidence(project_root, store, triggering_lineages) -> ReviewEvidenceBundle`.
- Produces `review_due_lineages(store, now) -> list[str]`.
- Produces `run_reviewer(...) -> ReviewerExecutionResult`.
- Produces `validate_review_payload(payload) -> SupervisorReview`.
- Produces `apply_review_decision(store, review) -> list[ActionRequest]`.

- [ ] **Step 1: Write failing cadence and coalescing tests**

```python
def test_review_due_every_two_semantic_parents_across_continuations(tmp_path):
    store = migrated_store(tmp_path)
    record_parent_completion(store, "lineage-a", run_id="run-1", parent=21)
    record_continuation(store, "lineage-a", source="run-1", target="run-2")
    record_parent_completion(store, "lineage-a", run_id="run-2", parent=22)
    assert review_due_lineages(store, now=NOW) == ["lineage-a"]

def test_due_lineages_within_ten_minutes_coalesce_into_one_review(tmp_path):
    store = due_lineages(tmp_path, {"lineage-a": NOW, "lineage-b": NOW_PLUS_5_MIN})
    requests = schedule_due_reviews(store, now=NOW_PLUS_5_MIN)
    assert len(requests) == 1
    assert requests[0].metadata["triggering_lineages"] == ["lineage-a", "lineage-b"]
```

- [ ] **Step 2: Write failing LLM validation and fail-open tests**

```python
def test_reviewer_timeout_is_degraded_and_safe_loop_continues(tmp_path, fake_codex_timeout):
    result = run_reviewer(review_context(tmp_path), driver=fake_codex_timeout)
    assert result.status == "review_degraded"
    assert result.blocks_safe_runs is False

def test_review_refocus_and_stop_run_apply_automatically(tmp_path):
    store = migrated_store(tmp_path)
    actions = apply_review_decision(store, review(decision="refocus", affected_run_ids=["run-1"]))
    assert actions[0].action_type is ActionType.REFOCUS_RUN
    actions = apply_review_decision(store, review(decision="stop_run", affected_run_ids=["run-2"]))
    assert actions[0].action_type is ActionType.STOP_RUN
```

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py`

Expected: FAIL because Reviewer does not exist.

- [ ] **Step 4: Move deterministic evidence gathering into Reviewer**

Port useful deterministic signal computations from `harness_loop_auditor.py`, but produce a project-global bundle with trusted evidence hashes. Include objective, constraints, stop conditions, parent progress, Agent/Evaluator summaries, commits/pushes, failures/recoveries, services/freshness, user decisions, Skill snapshots, and prior finding closure evidence.

- [ ] **Step 5: Implement real Codex Reviewer call and schema**

Use a distinct `supervisor_reviewer` role in `run_codex_prompt`. The prompt is read-only and writes one candidate JSON file. Validate decision, affected run IDs, evidence hashes, finding lifecycle, and prohibited operations before Supervisor writes the accepted review to SQLite.

```python
ALLOWED_REVIEW_DECISIONS = {"continue", "auto_remediate", "refocus", "stop_run", "ask_user"}
```

- [ ] **Step 6: Implement Skill Governance snapshots**

Gather project skills from declared skill roots, bind confirmed usage only to structured execution evidence, group duplicate candidates by normalized purpose and path, and let Reviewer emit `keep`, `merge`, or `delete_candidate`. Log substring matches are excluded.

- [ ] **Step 7: Remove automatic rule-based audit boundary**

Stop creating `audit-reports/audit-*.json`, remove `audit_blocked` as a normal Supervisor control path, and route existing open audit remediation into migration cleanup. Keep old phase values readable during migration but do not create them.

- [ ] **Step 8: Run Reviewer, contract, and reconciler tests**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_contracts.py`

Expected: PASS.

- [ ] **Step 9: Commit Task 6**

```bash
git add scripts/loop_supervisor/reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/loop_supervisor/models.py scripts/loop_supervisor/reconciler.py scripts/harness_loop_agents.py scripts/harness_loop_contracts.py scripts/harness_loop_auditor.py scripts/tests/test_harness_loop_auditor.py
git commit -m "feat(harness): add supervisor global reviewer"
```

---

### Task 7: Paginated Dashboard Backend And Safe Log Detail

**Files:**
- Create: `apps/loop_dashboard/backend/loop_dashboard/pagination.py`
- Create: `apps/loop_dashboard/backend/loop_dashboard/supervisor_store.py`
- Modify: `apps/loop_dashboard/backend/loop_dashboard/main.py`
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Modify: `apps/loop_dashboard/backend/loop_dashboard/models.py`
- Modify: `apps/loop_dashboard/backend/tests/test_api.py`
- Create: `apps/loop_dashboard/backend/tests/test_supervisor_api.py`
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`
- Create: `apps/loop_dashboard/backend/tests/test_pagination.py`

**Interfaces:**
- Produces `Page[T]` JSON with `items`, `next_cursor`, `previous_cursor`, `page_size`, `total`, `has_more`.
- Produces paged Supervisor services/actions/reviews/decisions/skills/transitions and paged run list/events/logs.
- Produces bounded `GET /api/runs/{run_id}/logs/{log_id}` with at most 64 KiB of redacted content plus `truncated` and `total_bytes` metadata.

- [ ] **Step 1: Write failing cursor and API tests**

```python
def test_cursor_pages_are_stable_when_new_row_arrives(client, seeded_actions):
    first = client.get("/api/supervisor/actions?page_size=20").json()
    insert_newer_action()
    second = client.get(f"/api/supervisor/actions?page_size=20&cursor={first['next_cursor']}").json()
    assert set(item["action_id"] for item in first["items"]).isdisjoint(
        item["action_id"] for item in second["items"]
    )

def test_invalid_cursor_and_page_size_are_400(client):
    assert client.get("/api/supervisor/actions?cursor=bad").status_code == 400
    assert client.get("/api/supervisor/actions?page_size=21").status_code == 400

def test_log_list_omits_full_content_and_detail_is_bounded(client):
    item = client.get("/api/runs/run-1/logs?page_size=20").json()["items"][0]
    assert "content" not in item
    detail = client.get(f"/api/runs/run-1/logs/{item['log_id']}").json()
    assert len(detail["content"].encode()) <= 65536
    assert detail["truncated"] is True
    assert detail["total_bytes"] > 65536
```

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_pagination.py apps/loop_dashboard/backend/tests/test_supervisor_api.py apps/loop_dashboard/backend/tests/test_api.py`

Expected: FAIL because endpoints are unpaginated and legacy JSONL-backed.

- [ ] **Step 3: Implement shared cursor codec**

The cursor contains version, endpoint identity, filter fingerprint, timestamp, primary key, and direction. Decode errors become `HTTPException(400)`. Query each page with keyset comparison and fetch `page_size + 1` rows.

- [ ] **Step 4: Implement SQLite Supervisor read model**

`SupervisorDashboardStore` opens SQLite with URI `mode=ro`, sets `PRAGMA query_only=ON` and a busy timeout, and returns honest `unavailable` or `schema_incompatible` diagnostics when it cannot query the required schema. It never migrates or writes runtime state. Each first-page request binds a snapshot upper bound into its cursor; later inserts cannot move an already-open page.

- [ ] **Step 5: Split run artifact pagination from the legacy store**

Keep run summary projection but add paged methods for runs, children, acceptance, events, logs, diagnostics, and artifacts. Remove `/api/supervisor/auditor`; add reviews and Skill Governance routes. Log lists return descriptors and bounded summaries, never full content. Large log detail resolves an opaque ID through a server-side safe map, repeats containment, symlink and regular-file checks, redacts text, and caps returned content at 64 KiB. Action-attempt logs use an opaque attempt ID plus the fixed `stdout` or `stderr` stream name; no endpoint accepts a raw path.

- [ ] **Step 6: Run all backend tests**

Run: `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests`

Expected: PASS.

- [ ] **Step 7: Commit Task 7**

```bash
git add apps/loop_dashboard/backend/loop_dashboard apps/loop_dashboard/backend/tests
git commit -m "feat(dashboard): add supervisor cursor pagination"
```

---

### Task 8: Mock-Matching Dashboard Tabs And Frontend Pagination

**Files:**
- Create: `apps/loop_dashboard/frontend/pagination.js`
- Create: `apps/loop_dashboard/frontend/supervisor.js`
- Modify: `apps/loop_dashboard/frontend/index.html`
- Modify: `apps/loop_dashboard/frontend/app.js`
- Modify: `apps/loop_dashboard/frontend/styles.css`
- Modify: `apps/loop_dashboard/frontend/test_supervisor_contract.py`
- Modify: `scripts/loop_dashboard_evaluator.py`
- Modify: `scripts/tests/test_loop_dashboard_evaluator.py`
- Create: `scripts/loop_dashboard_supervisor_playwright.py`
- Create: `docs/harness/evaluator-scenarios/loop-supervisor-unification-01.json`

**Interfaces:**
- Produces seven real Supervisor tabs and seven run-detail tabs from the mock.
- Produces one reusable pager with independent per-tab URL state. Numbered pages represent only the cursor chain already visited in this browser session; users advance to an unvisited page with `下一页` and cannot jump to an unknown cursor.
- Consumes Task 7 page responses and bounded log detail.

- [ ] **Step 1: Write failing static contract tests**

Assert the built frontend contains all mock tab labels, removes `Auditor`, imports `pagination.js` before `supervisor.js` and `app.js`, exposes page-size choices 20/50/100, and has no `slice(0, N)` truncation for paged collections.

- [ ] **Step 2: Extend browser evaluator with failing scenarios**

Add only scenario dispatch and result aggregation to `loop_dashboard_evaluator.py`; put Supervisor-specific fixture creation, browser actions, screenshots, and canvas/overflow checks in `loop_dashboard_supervisor_playwright.py`. Seed more than 25 actions, reviews, decisions, skills, events, and logs through the real Supervisor DB initializer. Assert:

```python
expect(page.get_by_role("tab", name="任务恢复")).to_be_visible()
page.get_by_role("tab", name="任务恢复").click()
expect(page.get_by_text("第 1-20 条，共 26 条")).to_be_visible()
page.get_by_role("button", name="下一页").click()
expect(page.get_by_text("第 21-26 条，共 26 条")).to_be_visible()
expect(page.get_by_text("action-001")).not_to_be_visible()
```

Also verify refresh restores tab/page/filter and the visited cursor chain, a new row does not move page 2, an unvisited numeric page cannot be selected, log expansion is the only action that fetches detail, mobile has no document-level horizontal overflow, and no independent Auditor/orchestrator/auto-resume role appears.

- [ ] **Step 3: Run frontend/evaluator tests and verify RED**

Run: `python3 -m pytest -q apps/loop_dashboard/frontend/test_supervisor_contract.py scripts/tests/test_loop_dashboard_evaluator.py`

Expected: FAIL on missing real tabs and pagination.

- [ ] **Step 4: Implement reusable frontend pagination**

`pagination.js` owns `{cursor, visitedCursors, pageIndex, pageSize, query, sort}` by tab key, serializes the active page state into URL search params, resets only the changed tab on filter changes, and renders symbol/text controls without changing layout dimensions. Numeric controls are generated only for `visitedCursors`; `下一页` obtains and records the next cursor before exposing that page number.

- [ ] **Step 5: Implement focused Supervisor view**

`supervisor.js` lazily fetches only the selected Supervisor tab. Implement Overview, Services, Task Recovery, Reviewer, Decisions, Skill Governance, and Configuration. Keep Supervisor global and outside the task run list.

- [ ] **Step 6: Refactor run detail to lazy page loading**

Stop fetching full events/logs in `loadSelectedRun`. Fetch paged collection data only when its tab is active. Remove the Auditor tab. Preserve Planner/Generator/Evaluator descriptions and complete human-readable summaries.

- [ ] **Step 7: Match responsive mock and test screenshots**

Use the approved mock's hierarchy, quiet operational palette, 6px-or-smaller card radii, single-column mobile layout, horizontally scrollable tables/tabs, stable toolbar dimensions, and complete text. Verify at 1440x1000 and 390x844 with screenshot and `document.documentElement.scrollWidth <= innerWidth`.

- [ ] **Step 8: Run browser and frontend tests**

Run:

```bash
node --check apps/loop_dashboard/frontend/pagination.js
node --check apps/loop_dashboard/frontend/supervisor.js
node --check apps/loop_dashboard/frontend/app.js
python3 -m pytest -q apps/loop_dashboard/frontend/test_supervisor_contract.py scripts/tests/test_loop_dashboard_evaluator.py
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-unification-01 --scenario loop-supervisor-unification-01
```

Expected: PASS with desktop/mobile screenshots and page-level assertions.

- [ ] **Step 9: Commit Task 8**

```bash
git add apps/loop_dashboard/frontend scripts/loop_dashboard_evaluator.py scripts/tests/test_loop_dashboard_evaluator.py docs/harness/evaluator-scenarios/loop-supervisor-unification-01.json
git commit -m "feat(dashboard): implement unified supervisor views"
```

---

### Task 9: Migration, Shadow Comparison, Cutover, And Legacy Removal

**Files:**
- Create: `scripts/loop_supervisor/migration.py`
- Create: `scripts/tests/test_harness_loop_supervisor_migration.py`
- Modify: `scripts/loop_supervisor/cli.py`
- Modify: `scripts/harness_loop_supervisor.py`
- Delete: `scripts/harness_loop_auto_resume.py`
- Delete/replace: `scripts/tests/test_harness_loop_auto_resume.py`
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Modify: `AGENTS.md`
- Create: `docs/harness/loop-supervisor.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/TECH_DECISIONS.md`

**Interfaces:**
- Produces `inventory_runtime(project_root) -> RuntimeInventory`.
- Produces `migrate_jsonl(project_root, store, *, dry_run: bool) -> MigrationReport`.
- Produces `shadow_compare(project_root, store) -> ShadowComparisonReport`.
- Produces safe legacy cleanup only after validated migration.

- [ ] **Step 1: Write failing migration tests**

```python
def test_migration_compacts_repeated_ticks_and_preserves_first_last_count(tmp_path):
    seed_repeated_decisions(tmp_path, count=6330, unique_state_changes=2)
    report = migrate_jsonl(tmp_path, migrated_store(tmp_path), dry_run=False)
    assert report.source_rows == 6330
    assert report.transition_rows == 2
    failure = report.store.failure("unsupported_state:run-1:run-state:unsupported-state")
    assert failure.occurrence_count == 6330

def test_migration_never_deletes_legacy_files_before_validation(tmp_path, monkeypatch):
    seed_legacy_runtime(tmp_path)
    monkeypatch.setattr("scripts.loop_supervisor.migration.validate_migration", lambda *_: False)
    with pytest.raises(MigrationValidationError):
        migrate_jsonl(tmp_path, migrated_store(tmp_path), dry_run=False)
    assert legacy_decisions_path(tmp_path).exists()

def test_inventory_preserves_parent22_and_crawler_dirty_paths(tmp_path):
    seed_parent22_and_crawler_dirty_paths(tmp_path)
    inventory = inventory_runtime(tmp_path)
    assert PARENT22_VERIFICATION in inventory.protected_paths
    assert AWS_TRN2_RAW in inventory.protected_paths
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_migration.py`

Expected: FAIL because migration module does not exist.

- [ ] **Step 3: Implement streaming JSONL compaction and snapshots**

Read legacy files line-by-line, not into memory. Snapshot runtime artifacts to a timestamped directory outside the repo Git index. Upsert transitions/failures/decisions and verify source counts, unique keys, open decisions, run projections, and first/last timestamps before optional cleanup.

- [ ] **Step 4: Implement shadow comparison**

Compare old classification with new desired actions on copied artifacts. Classify differences as `equivalent`, `new_auto_recovery`, `new_user_intervention`, or `unsafe_divergence`. Any `new_user_intervention` or `unsafe_divergence` fails the cutover gate.

- [ ] **Step 5: Remove independent runtime entrypoints**

Remove auto-resume watcher and service registration. Remove public orchestrator `run`, `run-demand-multi`, and `run-autonomous` execution commands after tests and docs use Supervisor. Keep low-level executor functions in an internal module path; no Dashboard or operator output may present orchestrator as a role.

- [ ] **Step 6: Update operations docs**

Document exactly two long-running tmux commands:

```bash
python3 -m scripts.loop_supervisor.cli watch --project-root /home/fyz/codex-skills
python3 -m scripts.loop_supervisor.cli worker --project-root /home/fyz/codex-skills --worker-id worker-01
```

Document health/status, Reviewer degradation, run-scoped decisions, migration dry-run/apply, rollback, DB rebuild, and retention. Replace AGENTS.md references to `loop-auto-resume`.

- [ ] **Step 7: Run migration and compatibility tests**

Run:

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_migration.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor.py
python3 -m scripts.loop_supervisor.cli migrate --project-root . --dry-run
python3 -m scripts.loop_supervisor.cli shadow-compare --project-root .
git diff --check
```

Expected: PASS; shadow report has zero `new_user_intervention` and zero `unsafe_divergence`.

- [ ] **Step 8: Commit Task 9**

```bash
git add scripts/loop_supervisor scripts/harness_loop_supervisor.py scripts/harness_loop_auto_resume.py scripts/harness_loop_orchestrator.py scripts/tests AGENTS.md docs/harness/loop-supervisor.md docs/ARCHITECTURE.md docs/TECH_DECISIONS.md
git commit -m "refactor(harness): unify loop runtime under supervisor"
```

---

### Task 10: Isolated E2E, Live Cutover, Parent-22 Recovery, And Four-Parent Soak

**Files:**
- Create: `scripts/loop_supervisor_e2e_evaluator.py`
- Create: `scripts/tests/test_loop_supervisor_e2e_evaluator.py`
- Modify: `docs/harness/evaluator-scenarios/loop-supervisor-unification-01.json`
- Modify: `tasks.json`
- Modify: `progress.md`

**Interfaces:**
- Produces `.codex/loop-supervisor-e2e/loop-supervisor-unification-01/result.json` and browser/runtime evidence.
- Produces cutover report, rollback snapshot reference, parent-22 recovery evidence, Reviewer evidence, and four-parent soak evidence.

- [ ] **Step 1: Write failing isolated E2E test**

The evaluator must create a temporary Git repository and Supervisor DB, seed multiple runs and more than one page of records, launch Supervisor/Worker/Dashboard on isolated ports, and verify:

- duplicate reconcile creates one action
- Worker crash lease is reclaimed once
- partial Generator output is recovered and Evaluator runs
- run-scoped user decision does not block an independent continuation
- two semantic parent completions trigger one real Reviewer fixture invocation
- Reviewer timeout is fail-open
- browser tabs and pagination match the mock
- legacy Auditor/auto-resume/orchestrator roles are absent

- [ ] **Step 2: Run isolated E2E and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_loop_supervisor_e2e_evaluator.py`

Expected: FAIL before the evaluator exists.

- [ ] **Step 3: Implement isolated evaluator and formal suspicious-case checks**

The evaluator must independently inspect DB rows, leases, run files, action provenance, browser content, and Git commits. For suspicious behavior, construct and rerun a counterexample test before reporting a bug. A fixture-only rendering pass cannot satisfy runtime scenarios.

- [ ] **Step 4: Run complete pre-cutover verification**

Run the exact `tasks.json` verify command except live tmux cutover clauses. Expected: all unit, integration, API, browser, migration, and isolated E2E scenarios pass.

- [ ] **Step 5: Snapshot and apply live migration**

Record current `git status`, protected dirty paths, service health, run state, old Supervisor PID/session, and rollback directory. Run migration dry-run, validate, stop old Supervisor and auto-resume, apply migration, start new Supervisor and Worker, then immediately verify Crawler backend/frontend and Dashboard.

- [ ] **Step 6: Recover live parent-22**

Confirm the queued action is `recover_generator_result`, not a fresh Generator rerun. Require:

- recovered envelope with attempts 3/4 provenance
- independent Evaluator pass
- wiki validation
- scoped commit and `git push origin main`
- crawler/wiki/search/frontend/Dashboard freshness for Dayu Paratus

- [ ] **Step 7: Run four semantic parent tasks and two Reviews**

Keep Supervisor, Worker, Crawler backend/frontend, and Dashboard online. Prove four consecutive semantic parents complete without manual phase commands, one project-global LLM Review occurs after each two parents, at least one injected retryable failure recovers automatically, and no unchanged decision is written per tick.

- [ ] **Step 8: Run final evaluator and exact task verification**

Run:

```bash
python3 scripts/loop_supervisor_e2e_evaluator.py --repo-root . --output-dir .codex/loop-supervisor-e2e/loop-supervisor-unification-01
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-unification-01 --scenario loop-supervisor-unification-01
python3 personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate --domain ai_infra
python3 -m json.tool tasks.json >/dev/null
git diff --check
```

Expected: all status fields `pass`, two LLM Review records, four completed parent records, no global stop from a run-scoped failure, and remote main containing all task commits.

- [ ] **Step 9: Update task and progress evidence**

Set `loop-supervisor-unification-01` to `done` only after task-level and final-level evaluator gates pass. Prepend `progress.md` with commits, migration report, rollback snapshot, parent-22 recovery, four parent IDs, two Review summaries, service URLs, tests, and any upstream failures.

- [ ] **Step 10: Commit, push, and verify remote**

```bash
git add scripts/loop_supervisor_e2e_evaluator.py scripts/tests/test_loop_supervisor_e2e_evaluator.py docs/harness/evaluator-scenarios/loop-supervisor-unification-01.json tasks.json progress.md
git commit -m "feat(harness): complete unified loop supervisor"
git push origin main
git rev-parse HEAD
git rev-parse origin/main
```

Expected: local `HEAD` equals `origin/main`; only known runtime/crawler paths remain untracked or modified.

---

## Review Gates

After each task:

1. Dispatch a fresh specification reviewer against the task section and diff.
2. Fix all specification gaps before code-quality review.
3. Dispatch a fresh code-quality reviewer.
4. Fix accepted findings and rerun focused tests.
5. Commit only the task's declared files.

After Tasks 4, 6, 8, and 10, run the broader regression suites because they change execution, review, frontend, and cutover contracts respectively.

## Plan Self-Review Checklist

- Every spec component maps to a task.
- The transition registry is single-source and tested for phase coverage.
- SQLite, Worker, recovery, Reviewer, Dashboard, migration, and live soak each have focused tasks.
- Parent-22 and crawler dirty paths are protected before migration.
- Reviewer is a real LLM call with fail-open behavior, not a renamed rule report.
- Auditor, auto-resume, and public orchestrator roles are removed before completion.
- Dashboard mock fields have producers, APIs, frontend consumers, and browser assertions.
- All growing collections have cursor pagination and stable-page tests.
- No implementation step contains an unresolved placeholder.
