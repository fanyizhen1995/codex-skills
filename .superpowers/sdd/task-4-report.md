# Task 4 Report: Bounded Executor And Independent Worker

## Status

`DONE`

## RED / GREEN

- RED: executor/worker tests initially failed during collection because `acquire_repository_mutation_lock` did not exist.
- RED: handler coverage then failed because bounded orchestrator primitives did not exist.
- RED: production `run-autonomous` CLI attempted to load a live run instead of returning deprecation status.
- RED: a simulated `SystemExit(9)` was swallowed and recorded as an action failure instead of leaving a reclaimable lease.
- RED regression: direct `scripts/harness_loop_phase2_smoke.py` execution could not import the new models dependency.
- RED critical review: demand `planned/run_planner` resolved to `RUN_GENERATOR`, autonomous `cleanup/commit_autonomous_changes` resolved to non-mutating `CLEANUP`, and `COMMIT` had no Executor handler.
- GREEN: focused executor, Worker, and lock suite passes 16 tests.
- GREEN: legacy orchestrator compatibility suite passes 202 tests.
- GREEN: `py_compile` and `git diff --check` pass.

## Handler Coverage

`ACTION_HANDLERS` is checked at import time and by tests against every distinct non-terminal, non-user-escalation action in `REGISTRY`. It contains one unique handler for each of:

- `run_planner`
- `run_generator`
- `run_evaluator`
- `run_evidence_gate`
- `run_artifact_hygiene`
- `commit`
- `push`
- `cleanup`
- `create_continuation`
- `recover_generator_result`
- `run_alternate_recovery`
- `run_reviewer`

The dispatcher rejects `ask_user` and terminal `no_op`. Executor source and runtime tests prohibit calls to `run_loop`, `run_autonomous`, and `run_demand_multi`.

## Critical Registry Fix

- Demand `planned/run_planner` now maps exactly to mutating `RUN_PLANNER`; child `planned/run_generator` remains mutating `RUN_GENERATOR`.
- A confirmed demand preflight is reconciled to `RUN_PLANNER`, and a real Worker invocation creates `planner-output.json` and stops in `generating/run_generator` without invoking Generator.
- Autonomous `cleanup/commit_autonomous_changes` now maps exactly to mutating `COMMIT`; `cleanup/run_cleanup` remains non-mutating `CLEANUP`.
- Autonomous `committed/push_autonomous_commit` maps exactly to mutating `PUSH`. Blocked retry/inspection states are not mapped to ordinary cleanup.
- `COMMIT` dispatches only to `run_bounded_commit`. A successful bounded commit stops at `committed/push_autonomous_commit`; the next Reconciler tick queues `PUSH` and does not jump to cleanup or `passed_waiting_human_merge`.

## Critical Real-Chain Fix

- RED: a real fake Generator/Evaluator artifact flow reached `artifact_hygiene`, but bounded hygiene left autonomous runs at `cleanup/run_cleanup`, so the next tick incorrectly queued `CLEANUP` instead of `COMMIT`.
- RED: after correcting hygiene routing, the next PUSH tick opened a `same-revision run state conflict` because legacy phase primitives changed run state without incrementing `state_revision`.
- GREEN: autonomous bounded hygiene now changes only `next_action` to `commit_autonomous_changes`; it does not commit.
- GREEN: Worker detects a changed portable run after one bounded handler and uses fingerprint CAS to atomically advance exactly one revision before Store completion. Unchanged actions do not advance the run revision.
- GREEN: successful PUSH ends only at `cleanup/run_cleanup`. The following separate `CLEANUP` action uses `_finish_autonomous_cleanup`, records the completed ordinary or remediation task, and returns to `planning/run_autonomous_planner` with `last_result=pass`.
- GREEN: the integration test runs four distinct Reconcile/Worker actions (`RUN_ARTIFACT_HYGIENE`, `COMMIT`, `PUSH`, `CLEANUP`) from real fake artifacts, records one commit and one injected push, and verifies the completed-task ledger. It never enters `passed_waiting_human_merge`.
- GREEN: demand cleanup still uses generic `run_cleanup` and ends at `passed_waiting_human_merge/await_human_merge_confirmation`.

## Critical Run-Lock Race Fix

- RED: Reconciler could observe a Worker's legacy same-revision phase write after the handler released the run lock but before revision finalize and Store completion, producing a same-revision conflict or stale projection.
- GREEN: Worker now holds one blocking `RunLockToken` across handler execution, fingerprint-CAS revision finalize, lease-loss check, and `store.complete_action`. Heartbeat remains active through completion; a lost lease never completes the action.
- GREEN: Reconciler keeps project→run lock order and performs secure dirfd reread, projection, Store upsert, and legacy revision upgrade while holding the same blocking per-run lock. Invalid JSON discovery for a concrete run is reread under lock; ownership failures remain failures.
- GREEN: `atomic_save_run_locked` requires an active matching token and retains containment, no-follow dirfd traversal, fingerprint CAS, atomic replace, and fsync checks. The token is invalid immediately after context release, avoiding recursive flock and bare unlocked writes.
- GREEN: completion or lease-loss failure writes `worker-completion-failure-<action-id>.json` recovery evidence and returns `lease_lost`; it cannot report success silently.
- GREEN: both concurrency directions pass: Reconciler blocks through Worker finalize+completion, and Worker blocks while Reconciler projects the run. The tests verify completed action status, file/projected revision `+1`, one next action, and no decision or lease loss.

## Critical Locked-Enqueue Fix

- RED: Reconciler released the run lock after projection, then reused `record.payload` for decision and enqueue. A real Planner Worker could finish in that window and the stale enqueue would reopen its completed old action.
- GREEN: Reconciler now acquires concrete run locks in deterministic order under the project reconcile lock and retains every lock through secure reread, projection/upsert, decision evaluation, desired-action recomputation, and enqueue. Enqueue uses the fresh locked payload fingerprint and active matching token.
- GREEN: advancing a Store run projection atomically marks only older-revision `pending` actions `cancelled`; leased actions are preserved. The shared run lock ensures a live Worker completes or records lease loss before Reconciler can advance that run.
- GREEN: a completed action reopens only when enqueue receives an active matching run-lock token and the locked snapshot fingerprint still equals the Store projection fingerprint. Unlocked duplicate enqueue remains completed.
- GREEN: the reverse concurrency test pauses Reconciler after projection at enqueue, proves the real Planner Worker waits, then verifies one completed old action/attempt, file and Store at revision 1 `generating`, exactly one pending revision-1 Generator action, and no old pending action.

## Worker And Recovery Evidence

- `worker_once()` leases at most one action and leaves the next queued action pending.
- The heartbeat thread uses an independent Store connection and renews both Worker heartbeat and action lease.
- Lease and completion are both guarded by Store revision, phase, lease-owner, lease-expiry, and open-decision checks.
- `SystemExit` propagates without an attempt record, leaving the action leased for expiry-based reclaim.
- A stale crashed-worker heartbeat plus expired action lease is reclaimed and completed by a replacement Worker.
- SIGTERM requests stop new leases; the in-flight result is completed with a repo-relative interruption evidence artifact.

## Locks

- Lock order is per-run lock followed by repository mutation lock.
- Mutation classification is re-derived from the registry, not trusted from queue payload.
- Repository mutation lock uses cross-process `flock` at `.codex/loop-locks/repository-mutation.lock`.
- Owner and PID metadata are written while held, cleared before unlock, replaced by the next owner, and released on exceptional context exit.
- A held repository lock prevents a mutating Worker from entering its action handler and records a retryable failure.

## Deprecation

Production CLI calls to `run`, `run-demand-multi`, and `run-autonomous` return exit code 2 and point to `python3 scripts/harness_loop_supervisor.py --watch`. Historical Python functions remain until Task 9. Existing CLI compatibility tests opt in with `HARNESS_LEGACY_MULTI_ROUND_TEST_COMPAT=1`.

## Verification

```text
python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_runtime_lock.py
16 passed in 0.69s

python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
Ran 202 tests in 10.912s - OK

python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor.py
72 passed in 2.99s

python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_runtime_lock.py
19 passed in 0.95s

python3 -m pytest -q scripts/tests/test_harness_loop_supervisor*.py
224 passed in 9.15s

for i in $(seq 1 10); do python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_worker.py::test_reconciler_waits_for_worker_finalize_and_completion_under_run_lock scripts/tests/test_harness_loop_supervisor_worker.py::test_worker_waits_when_reconciler_holds_same_run_lock || exit 1; done
20 concurrency tests passed across 10 consecutive rounds

ruff check scripts/loop_supervisor/registry.py scripts/loop_supervisor/executor.py scripts/loop_supervisor/worker.py scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor.py
All checks passed

python3 -m py_compile scripts/harness_loop_orchestrator.py scripts/harness_loop_runtime_lock.py scripts/loop_supervisor/executor.py scripts/loop_supervisor/worker.py
exit 0

git diff --check
exit 0
```

## Commit

Scoped commit message: `feat(harness): execute supervisor actions through worker`. The final hash is reported in the Task 4 handoff after this report is included in the commit.

## Concerns

- Resolved: the two Critical Task 1/4 registry concerns are covered by exact transition rules, Executor import guards, Worker integration, and commit-to-PUSH reconciliation tests.
- Resolved: the two Critical real-chain concerns are covered by the four-action autonomous integration test, Worker revision CAS, and demand cleanup regression.
- Resolved: the Critical finalize/completion race is covered by a shared blocking run-lock token, locked atomic save, bidirectional concurrency tests, and recoverable completion-failure evidence.
- Resolved: the Critical stale decision/enqueue race is covered by lock retention through enqueue, pending supersession, locked fingerprint reopen defense, and the real reverse concurrency test.
- Remaining scope is unchanged: Task 5 and Task 6 own full recovery and Reviewer policy.
- No service or live-run restart was required; no live `.codex/loop-runs` or wiki content was modified.
