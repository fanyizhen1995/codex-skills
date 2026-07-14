# Task 4 Report: Bounded Executor And Independent Worker

## Status

`DONE_WITH_CONCERNS`

## RED / GREEN

- RED: executor/worker tests initially failed during collection because `acquire_repository_mutation_lock` did not exist.
- RED: handler coverage then failed because bounded orchestrator primitives did not exist.
- RED: production `run-autonomous` CLI attempted to load a live run instead of returning deprecation status.
- RED: a simulated `SystemExit(9)` was swallowed and recorded as an action failure instead of leaving a reclaimable lease.
- RED regression: direct `scripts/harness_loop_phase2_smoke.py` execution could not import the new models dependency.
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
- `push`
- `cleanup`
- `create_continuation`
- `recover_generator_result`
- `run_alternate_recovery`
- `run_reviewer`

The dispatcher rejects `ask_user` and terminal `no_op`. Executor source and runtime tests prohibit calls to `run_loop`, `run_autonomous`, and `run_demand_multi`.

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
Ran 202 tests in 10.646s - OK

python3 -m py_compile scripts/harness_loop_orchestrator.py scripts/harness_loop_runtime_lock.py scripts/loop_supervisor/executor.py scripts/loop_supervisor/worker.py
exit 0

git diff --check
exit 0
```

## Commit

Scoped commit message: `feat(harness): execute supervisor actions through worker`. The final hash is reported in the Task 4 handoff after this report is included in the commit.

## Concerns

- Task 1 registry maps demand `planned/run_planner` through the wildcard `run_generator`, while the bounded demand Planner requires `planned`. It also maps autonomous `cleanup/commit_autonomous_changes` to non-mutating `cleanup`, so the new bounded `commit` primitive is not currently queue-reachable. These are upstream registry contract mismatches outside the Task 4 file brief and need correction before end-to-end Supervisor cutover.
- Task 5 and Task 6 still own full recovery and Reviewer policy. Task 4 supplies bounded adapters for the current registry entries but does not add those later policy engines.
- No service or live-run restart was required; no live `.codex/loop-runs` or wiki content was modified.
