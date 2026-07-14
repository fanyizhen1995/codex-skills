# Task 6 Implementation Report

## Scope

- Base before Task 6: `91f1517`
- Implementation commit: `abdd05d`
- Worktree: `/home/fyz/codex-skills/.worktrees/loop-supervisor-unification`
- Runtime `.codex` state was not staged or committed.
- `tasks.json` and `progress.md` were not modified.

## Requirement Review

1. Project-global real Reviewer: `scripts.loop_supervisor.reviewer` provides a standalone `--once` service path, leases only `RUN_REVIEWER`, calls `run_codex_prompt` with role `supervisor_reviewer`, and forces the Codex read-only sandbox. Ordinary Worker handler coverage excludes `RUN_REVIEWER`.
2. Cadence and coalescing: semantic parent IDs are deduplicated by stable `loop_lineage_id` across continuation runs. Two unreviewed parents make a lineage due. Due lineages within ten minutes update one pending Reviewer action atomically.
3. Trusted evidence and schema: each project-global evidence section and the bundle are SHA-256 bound. Top-level, finding lifecycle, affected runs, Skill Governance shapes, allowed decisions, evidence references, and prohibited extra fields are validated before acceptance.
4. Fail-open policy: `ReviewerContext` defaults to fail closed. The queued Reviewer service permits degraded fail-open only after checking that no global safety decision is open. Degraded execution is persisted as `review_degraded` and does not create a user decision by itself.
5. Registry-owned application: `continue`, `auto_remediate`, `refocus`, `stop_run`, and `ask_user` resolve through Reviewer registry rules. Remediation/refocus update the next Planner contract, stop enters terminal `stopped_by_reviewer`, and ask-user remains run-scoped. Supervisor-owned actions are claimed and completed outside the ordinary Worker.
6. Skill Governance: inventory comes from declared roots; usage requires structured execution evidence; logs and arbitrary JSON are ignored; duplicate groups use normalized purpose and path; accepted actions are exactly `keep`, `merge`, or `delete_candidate` with trusted evidence.
7. Audit migration: legacy `audit_pending`, `auditing`, and `audit_blocked` remain schema-readable but are no-op registry states and are migrated to Planner directives before dispatch. Existing audit artifacts remain readable and unchanged; the unified Supervisor does not create `audit-reports/audit-*.json` or new `audit_blocked` states. Physical legacy Auditor removal remains deferred until migration acceptance, as required by the binding design's cutover/removal sequence.

## TDD Evidence

Takeover baseline:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py
................                                                         [100%]
16 passed in 0.51s
```

Initial added regressions failed for the intended missing behavior:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor_registry.py
8 failed, 71 passed in 2.46s
```

The eight failures covered pending-review coalescing, unknown finding runs, unproven Skill Governance actions, automatic refocus/stop/remediation application, legacy audit migration, and all three legacy active audit phases.

Additional RED checks:

```text
domain output metrics: 1 failed in 0.08s
standalone Reviewer service path: 1 failed in 0.10s
atomic in-place pending review coalescing: 1 failed in 0.10s
fail-closed default: 1 failed in 0.09s
legacy migration with existing Reviewer directives: 1 failed in 0.10s
```

Focused GREEN result:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py
....................                                                     [100%]
20 passed in 0.69s
```

## Final Verification

Required brief command:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_contracts.py
........................................................................ [ 56%]
........................................................                 [100%]
128 passed in 2.47s
```

Relevant Supervisor, Worker, recovery, contracts, agents, and Auditor compatibility regressions:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_auditor.py
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 88%]
............................                                           [100%]
244 passed, 2 subtests passed in 11.06s
```

Planner/orchestrator compatibility after adding Reviewer directives:

```text
$ python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
----------------------------------------------------------------------
Ran 202 tests in 11.794s

OK
```

Static checks:

```text
$ ruff check scripts/harness_loop_agents.py scripts/harness_loop_contracts.py scripts/harness_loop_orchestrator.py scripts/loop_supervisor scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_reviewer.py
All checks passed!

$ python3 -m py_compile scripts/harness_loop_agents.py scripts/harness_loop_contracts.py scripts/harness_loop_orchestrator.py scripts/loop_supervisor/__init__.py scripts/loop_supervisor/executor.py scripts/loop_supervisor/models.py scripts/loop_supervisor/reconciler.py scripts/loop_supervisor/registry.py scripts/loop_supervisor/reviewer.py scripts/loop_supervisor/store.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_reviewer.py
exit 0; no output

$ git diff --check
exit 0; no output
```

## Service Evidence

No service was restarted. Existing long-lived services stayed online throughout:

```text
$ curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health
{"status":"ok","bind_host":"0.0.0.0","bind_port":8765,"authenticated":false,"warning":"No login is enabled. Expose this service only on a trusted network."}

$ curl --noproxy '*' -fsSI http://127.0.0.1:5173/
HTTP/1.1 200 OK

$ curl --noproxy '*' -fsS http://127.0.0.1:8766/api/health
{"status":"ok"}
```

## Final Takeover Verification Addendum (2026-07-15)

The interrupted final fix wave was resumed from committed base `f45b2d5`
without resetting or reverting its existing uncommitted changes. The takeover
found and closed two additional gaps before final verification:

1. Planner/Generator/Evaluator contracts accepted a missing
   `skill_invocations` key as an implicit empty list. The field is now required,
   every production/fake producer emits it explicitly, the demand-parent Codex
   prompt requests it, and bounded extraction also rejects omission.
2. A v10 non-`continue` accepted review could reconstruct without any
   revision-bound application target. Migration now requires the affected run
   set to exactly match the persisted target set or records
   `review_migration_blocked` and prevents another Reviewer LLM invocation.

### Additional RED/GREEN evidence

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_contracts.py::HarnessLoopContractsTests::test_agent_result_contracts_reject_malformed_skill_invocations
1 failed in 0.03s

$ python3 -m pytest -q scripts/tests/test_harness_loop_contracts.py::HarnessLoopContractsTests::test_agent_result_contracts_reject_malformed_skill_invocations scripts/tests/test_harness_loop_supervisor_worker.py::test_worker_atomically_records_real_bounded_skill_invocations
4 passed in 0.31s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'v10_affected_review_without_revision_targets'
1 failed, 49 deselected in 0.23s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'v10_applying_review or v10_affected_review'
3 passed, 47 deselected in 0.29s
```

Making the structured field mandatory initially exposed every old-shape
producer and fixture instead of silently treating omission as no usage:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_loop_dashboard_evaluator.py
22 failed, 288 passed in 14.09s
```

### Final fresh verification

Focused Findings 19-23 and related runtime:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_loop_dashboard_evaluator.py
310 passed in 14.76s
```

Required Task 6 brief suites:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_contracts.py
159 passed in 4.27s
```

Broad Supervisor and dashboard regressions:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_auditor.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_loop_dashboard_evaluator.py
307 passed, 2 subtests passed in 13.26s
```

Full orchestrator regressions:

```text
$ python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
Ran 202 tests in 10.610s
OK
```

Isolated browser evaluator:

```text
$ python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-01 --scenario loop-supervisor-01
exit 0; no stdout
result.json: status=pass, scenario_id=LOOP-SUPERVISOR-BROWSER-E2E
```

Static, syntax, and diff checks:

```text
$ python3 -m ruff check scripts/harness_loop_contracts.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/recovery.py scripts/loop_supervisor/reviewer.py scripts/loop_supervisor/store.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_loop_dashboard_evaluator.py
All checks passed!

$ python3 -m py_compile scripts/harness_loop_contracts.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/recovery.py scripts/loop_supervisor/reviewer.py scripts/loop_supervisor/store.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_loop_dashboard_evaluator.py
exit 0; no output

$ git diff --check
exit 0; no output
```

The empty evaluator test lock under `.codex/loop-locks` and the ignored browser
evaluator output created/refreshed by this task were removed after verification.
No live service or main-worktree artifact was changed or restarted.

## Final Re-review Fix Wave (2026-07-15)

No Finding 19-23 requirement conflicted with the binding design. The existing
uncommitted recovery work was preserved and completed in place.

### Finding 19: closed recovery episodes

Historical failed alternates now exclude failures whose recovery episode is
closed. If a closed episode owns the failed source attempt, reconciliation
requeues the normal registry action at tier zero instead of reopening Reviewer.
Coverage includes degraded fail-open, accepted `continue`, and revision-changing
`refocus` decisions.

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py -k 'failed_alternate_queues_reviewer_once or closed_recovery_episode_ignores_historical'
3 failed, 25 deselected in 0.70s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py -k 'failed_alternate_queues_reviewer_once or closed_recovery_episode_ignores_historical'
3 passed, 25 deselected in 0.58s
```

### Finding 20: safe v10 applying-review migration

Schema v12 reconstructs a pre-v11 applying review only when one nonterminal
Reviewer source action can be identified and the owned evidence bundle,
accepted artifact, review schema, and revision/fingerprint targets validate.
Unsafe or ambiguous rows become `review_migration_blocked`, their source action
becomes `migration_blocked`, and Reviewer returns idle without invoking an LLM.

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'v10_applying_review'
2 failed, 47 deselected in 0.38s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'v10_applying_review' scripts/tests/test_harness_loop_supervisor_store.py -k 'migrate_creates_required or migrate_adds_state or migrate_v3 or legacy_migration_normalizes'
6 passed, 144 deselected in 0.41s
```

### Finding 21: structured P/G/E Skill invocation contract

Planner, Generator, and Evaluator result contracts accept a strict structured
`skill_invocations` field. Bounded production primitives require exact
run/task/role-owned JSON evidence under the run directory, reject symlink
traversal and mismatched hashes, carry validated records in `ActionResult`, and
let Worker persist attempts plus invocations in one transaction. Prompts forbid
log/prose inference and fake producers emit an explicit empty list.

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_contracts.py::HarnessLoopContractsTests::test_agent_result_contracts_reject_malformed_skill_invocations scripts/tests/test_harness_loop_supervisor_worker.py::test_worker_atomically_records_successful_skill_invocations
2 failed in 0.16s

$ python3 -m pytest -q scripts/tests/test_harness_loop_contracts.py::HarnessLoopContractsTests::test_agent_result_contracts_reject_malformed_skill_invocations scripts/tests/test_harness_loop_supervisor_worker.py::test_worker_atomically_records_successful_skill_invocations
2 passed in 0.14s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_worker.py::test_worker_atomically_records_real_bounded_skill_invocations
3 passed in 0.33s
```

### Finding 22: source-action retention cutpoint

Retention excludes reviews whose source Reviewer action is nonterminal, even
when the application and review are already complete. The existing incomplete
application and Skill invocation FK retention protections remain intact.

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py -k 'retention_preserves_completed_review_while_source'
1 failed in 0.17s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py -k 'retention_preserves_completed_review_while_source or retention_preserves_incomplete or retention_aggregates_and_deletes_skill'
3 passed, 99 deselected in 0.16s
```

### Finding 23: Dashboard historical audit migration

The Dashboard fixture now reparses the historical `audit-001.json`, validates
`audit-remediation-result.json` with an empty `new_audit_report`, and fails if
`audit-002.json` exists. Browser assertions show the historical report and
migration artifact and explicitly reject a successor report.

```text
$ python3 -m pytest -q scripts/tests/test_loop_dashboard_evaluator.py -k 'auditor_engine_fixture'
.F                                                                       [100%]
1 failed, 1 passed, 8 deselected in 0.07s

$ python3 -m pytest -q scripts/tests/test_loop_dashboard_evaluator.py -k 'auditor_engine_fixture'
..                                                                       [100%]
2 passed, 8 deselected in 0.07s
```

### Final verification

Focused Findings 19-23 and related Reviewer runtime:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_loop_dashboard_evaluator.py
309 passed in 14.69s
```

Required brief suites:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_contracts.py
158 passed in 4.05s
```

Broad Supervisor/orchestrator-adjacent regressions:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_auditor.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_loop_dashboard_evaluator.py
307 passed, 2 subtests passed in 13.52s
```

Full orchestrator regressions:

```text
$ python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
Ran 202 tests in 10.890s
OK
```

Isolated browser evaluator:

```text
$ python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-01 --scenario loop-supervisor-01
exit 0; no stdout
result.json: status=pass, scenario_id=LOOP-SUPERVISOR-BROWSER-E2E
```

Static, syntax, and diff checks:

```text
$ python3 -m ruff check scripts/harness_loop_contracts.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/recovery.py scripts/loop_supervisor/reviewer.py scripts/loop_supervisor/store.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_loop_dashboard_evaluator.py
All checks passed!

$ python3 -m py_compile scripts/harness_loop_contracts.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/recovery.py scripts/loop_supervisor/reviewer.py scripts/loop_supervisor/store.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_loop_dashboard_evaluator.py
exit 0; no output

$ git diff --check
exit 0; no output
```

The browser evaluator output and generated `.codex/loop-locks` were removed
after verification. No runtime `.codex` state is included in the commit.

## Re-review Integration Fix Wave (Findings 10-18)

No Re-review Finding 10-18 conflicts with the binding design. The changes
preserve the first review fix wave and add schema-v11 migration readability.

### TDD evidence

Takeover focused baseline:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py
40 passed in 1.65s
```

Reviewer ownership, run-decision isolation, evidence position, and migration
backfill RED:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py::test_failed_alternate_queues_reviewer_once_without_user_decision scripts/tests/test_harness_loop_supervisor_reviewer.py::test_run_decision_does_not_block_project_global_reviewer_lease scripts/tests/test_harness_loop_supervisor_reviewer.py::test_global_decision_blocks_project_global_reviewer_lease scripts/tests/test_harness_loop_supervisor_reviewer.py::test_review_evidence_includes_parents_reserved_for_current_review scripts/tests/test_harness_loop_supervisor_store.py::test_migrate_backfills_legacy_reviewer_actions_to_reviewer_owner
4 failed, 1 passed in 0.51s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py::test_migrate_backfills_legacy_reviewer_actions_to_reviewer_owner
1 failed in 0.14s
```

The failures showed Task 5 recovery actions and migrated rows remained
Worker-owned, a run-scoped decision blocked the global Reviewer lease, and the
reserved position hid both triggering parents. GREEN:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py::test_failed_alternate_queues_reviewer_once_without_user_decision scripts/tests/test_harness_loop_supervisor_reviewer.py::test_run_decision_does_not_block_project_global_reviewer_lease scripts/tests/test_harness_loop_supervisor_reviewer.py::test_global_decision_blocks_project_global_reviewer_lease scripts/tests/test_harness_loop_supervisor_reviewer.py::test_review_evidence_includes_parents_reserved_for_current_review scripts/tests/test_harness_loop_supervisor_store.py::test_migrate_backfills_legacy_reviewer_actions_to_reviewer_owner
5 passed in 0.39s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_recovery.py::test_failed_alternate_queues_reviewer_once_without_user_decision
1 passed in 0.21s
```

The final Task 5 regression also executes the recovery-created action through
`run_queued_reviewer` and records the attempt under the distinct Reviewer ID.

Cold-store restart RED/GREEN:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py::test_queued_reviewer_resumes_persisted_outbox_after_cold_store_reopen
1 failed in 0.16s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py::test_queued_reviewer_resumes_persisted_outbox_after_cold_store_reopen
1 passed in 0.18s
```

The RED failure was `KeyError: 'source_action_id'`. Schema v11 now stores the
complete accepted `SupervisorReview` and source Reviewer action. After lease
expiry and store reopen, the persisted outbox completes before a driver that
raises if any new LLM call is attempted.

Fresh owned deterministic safety RED/GREEN:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py::test_reviewer_fail_open_gate_reads_fresh_owned_global_safety_signals
5 failed in 0.30s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py::test_reviewer_fail_open_gate_reads_fresh_owned_global_safety_signals scripts/tests/test_harness_loop_supervisor.py::test_binding_spec_global_stop_exceptions_are_global scripts/tests/test_harness_loop_supervisor_reviewer.py::test_evidence_build_failure_uses_fresh_deterministic_gate scripts/tests/test_harness_loop_supervisor_reviewer.py::test_queued_reviewer_resumes_persisted_outbox_after_cold_store_reopen
11 passed in 0.49s
```

The five RED cases failed open before reconciliation for confirmed secret
exposure, repository corruption, permission expansion, irreversible operation,
and explicit global stop. Reviewer and reconciler now share canonical signal
classification, and Reviewer reads fresh owned run files directly.

Production Skill invocation RED/GREEN:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_worker.py::test_worker_atomically_records_successful_skill_invocations scripts/tests/test_harness_loop_supervisor_store.py::test_complete_action_rolls_back_forged_skill_invocation_with_attempt
2 errors in 0.17s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_worker.py::test_worker_atomically_records_successful_skill_invocations scripts/tests/test_harness_loop_supervisor_store.py::test_complete_action_rolls_back_forged_skill_invocation_with_attempt scripts/tests/test_harness_loop_supervisor_reviewer.py::test_evidence_bundle_hashes_global_signals_and_uses_only_structured_skill_usage
3 passed in 0.24s
```

The RED collection errors identified the absent `SkillInvocationEvidence`
contract. Successful Worker results now carry immutable invocation data;
`complete_action` validates owned skill/artifact paths and SHA-256 and commits
attempt, invocation, and action completion atomically. Forged hashes roll back
all database effects. Dead recursive JSON skill scanners were removed.

Retention RED/GREEN:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py::test_retention_aggregates_and_deletes_skill_invocations_before_attempts scripts/tests/test_harness_loop_supervisor_store.py::test_retention_preserves_incomplete_review_application_and_applied_attempt
2 failed in 0.22s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py::test_retention_aggregates_and_deletes_skill_invocations_before_attempts scripts/tests/test_harness_loop_supervisor_store.py::test_retention_preserves_incomplete_review_application_and_applied_attempt scripts/tests/test_harness_loop_supervisor_store.py::test_retention_aggregates_rows_older_than_90_days_before_deleting scripts/tests/test_harness_loop_supervisor_store.py::test_retention_preserves_reviews_with_active_findings_and_compacts_terminal_ones
4 passed in 0.21s
```

The RED failures reproduced the invocation foreign-key abort and deletion of an
`applying` review. Retention now aggregates and deletes eligible invocation rows
before attempts, while preserving incomplete applications, reviews, target
actions, and already-applied target attempts needed for idempotent resume.

Cross-slice focused regression and scheduling/evidence separation:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_worker.py
3 failed, 226 passed in 13.48s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_worker.py
229 passed in 13.34s
```

The intermediate failures proved scheduling still needs
`max(reviewed_position, reserved_position)` while evidence must use completed
`reviewed_position` only. Separate helpers now enforce those semantics.

### Final verification

Required brief command:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_contracts.py
155 passed in 3.77s
```

Broad Supervisor, Worker, recovery, state, agents, Auditor migration,
auto-resume, and Dashboard evaluator regressions:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_auditor.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_loop_dashboard_evaluator.py
300 passed, 2 subtests passed in 12.66s
```

Full orchestrator regressions:

```text
$ python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
Ran 202 tests in 10.174s
OK
```

Static, syntax, and diff checks:

```text
$ python3 -m ruff check scripts/harness_loop_auditor.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py
All checks passed!

$ python3 -m py_compile scripts/harness_loop_auditor.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/*.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_worker.py
exit 0; no output

$ git diff --check
exit 0; no output
```

### Finding 10-18 self-review

10. Task 5 `RUN_REVIEWER` recovery actions explicitly use Reviewer ownership;
    schema-v11 migration backfills prior rows and recomputes canonical identity.
11. Accepted review payloads and source action IDs are durable. Reclaimed queued
    Reviewer actions resume incomplete or already-applied outboxes before driver
    invocation, including a real close/reopen cutpoint reproduction.
12. Reviewer leasing ignores representative-run decisions and still blocks on
    open global decisions. Worker/Supervisor run-scoped behavior is unchanged.
13. Scheduling uses reserved positions; evidence uses completed reviewed
    positions, so the triggering semantic parents remain visible.
14. Shared canonical safety classification covers all five binding global stop
    conditions, and fail-open evaluates fresh owned run files before decisions.
15. Successful `ActionResult` values carry strict Skill invocation provenance;
    Worker completion persists it atomically with validated hashes.
16. Retention aggregates Skill invocation counts and deletes child evidence
    before eligible attempts, eliminating the foreign-key failure.
17. Incomplete review applications, associated reviews/actions, applied target
    attempts, and their invocation evidence are excluded from retention.
18. `_structured_skill_usage`, `_SKILL_USAGE_KEYS`, and the dead run-local JSON
    evidence classifier are removed. Active usage comes only from
    `skill_invocations`. The strict prompt schema tests remain green.

### Service evidence

No service was restarted. Existing services remained online:

```text
$ curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health
{"status":"ok","bind_host":"0.0.0.0","bind_port":8765,"authenticated":false,"warning":"No login is enabled. Expose this service only on a trusted network."}

$ curl --noproxy '*' -fsSI http://127.0.0.1:5173/
HTTP/1.1 200 OK

$ curl --noproxy '*' -fsS http://127.0.0.1:8766/api/health
{"status":"ok"}
```

## Safety Re-review Findings 24-26 Completion (2026-07-15)

Finding 24 now applies the canonical global safety gate to Reviewer lease
renewal, completion, and each outbox application checkpoint. It recomputes the
gate after the driver returns, so an in-flight global decision or any canonical
safety signal blocks accepted application and degraded fail-open.

Finding 25 binds v10 applying-review recovery to its matching reservation and
Reviewer action, recomputes owned evidence and bundle hashes, validates the
accepted candidate and revision-bound targets, and marks unprovable rows
`review_migration_blocked` without another Reviewer invocation.

Finding 26 replaces the active Auditor browser fixture with an explicitly
historical pre-cutover report and disabled migration result. The browser
asserts read-only presentation, migration artifact visibility, and absence of
active-engine or successor-report behavior.

### Focused safety, migration, and dashboard checks

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_loop_dashboard_evaluator.py -k 'inflight or in_flight or global_stop or global_decision or canonical or safety_signal or v10 or auditor_engine_fixture or historical_disabled'
26 passed, 150 deselected in 1.33s
```

The historical fixture test was first corrected to guard removed active symbols
with `create=True`; it then failed because the fixture still called
`compute_deterministic_signals`. Replacing that path with static historical
evidence and a disabled migration result produced:

```text
$ python3 -m pytest -q scripts/tests/test_loop_dashboard_evaluator.py::LoopDashboardEvaluatorGovernanceTests::test_auditor_engine_fixture_is_historical_disabled_and_read_only scripts/tests/test_loop_dashboard_evaluator.py::LoopDashboardEvaluatorGovernanceTests::test_auditor_engine_fixture_rejects_successor_audit_report
2 passed in 0.05s
```

### Required and broad regression checks

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_contracts.py
170 passed in 4.91s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_auditor.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_loop_dashboard_evaluator.py
308 passed, 2 subtests passed in 13.18s

$ python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
Ran 202 tests in 10.789s
OK
```

### Browser and static checks

```text
$ python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir /tmp/task6-dashboard-safety-eval
exit 0; /tmp/task6-dashboard-safety-eval/result.json: status=pass, scenario_id=LOOP-DASHBOARD-CLICK-SMOKE

$ python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir /tmp/task6-loop-supervisor-eval --scenario loop-supervisor-01
exit 0; /tmp/task6-loop-supervisor-eval/result.json: status=pass, scenario_id=LOOP-SUPERVISOR-BROWSER-E2E

$ python3 -m ruff check scripts/loop_dashboard_evaluator.py scripts/loop_supervisor scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_loop_dashboard_evaluator.py
All checks passed!

$ python3 -m py_compile scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/*.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_loop_dashboard_evaluator.py
exit 0; no output

$ git diff --check
exit 0; no output
```

The zero-byte `.codex/loop-locks/evaluator-scenario-phase-2-test.lock` was
created by the 202-test orchestrator smoke scenario and was removed after its
ownership and empty state were confirmed. No live service or main worktree
state was changed.

Access URLs: `http://127.0.0.1:5173`, `http://127.0.0.1:8765`, and `http://127.0.0.1:8766`.

## Review Fix Wave (2026-07-15)

- Review fix commit: `beac24b`

No review finding conflicted with the binding design. Legacy removal timing was
resolved by disabling every production producer now while retaining read-only
migration parsing and explicit historical fixtures until physical removal.

### TDD evidence

Takeover baseline after the prior uncommitted fix wave:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py
1 failed, 28 passed in 1.39s
```

The failure showed the old closure-evidence test attempting an illegal direct
creation of a closed finding. The fixture was corrected to close an existing
open finding. New application status and lease cutpoint tests then produced:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'closure_requires or does_not_mark_complete or lease_loss_before_file_write or lease_loss_before_database'
1 failed, 3 passed, 26 deselected in 0.26s
```

The failure proved `run_reviewer` recorded `review_complete` before outbox
application. After making the outbox the sole completion owner:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py
32 passed in 1.51s
```

Legacy producer RED/GREEN:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'legacy_auditor_production or legacy_audit_boundary'
2 failed, 30 deselected in 0.16s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'legacy_auditor_production or legacy_audit_boundary'
2 passed, 30 deselected in 0.06s
```

Exact prompt schema RED/GREEN:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'prompt_embeds_exact_schema'
1 failed, 32 deselected in 0.08s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'prompt_embeds_exact_schema'
1 passed, 32 deselected in 0.03s
```

Schema/lifecycle regression diagnosis and repair:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_auditor.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py
11 failed, 235 passed, 2 subtests passed in 11.62s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_store.py
97 passed in 5.72s
```

The failures were stale schema-v9 assertions and audit-era finding fixtures;
they were updated to schema v10 and stable `open -> closed|accepted_risk`
identity/evidence rules. Historical migration collapse tests remained intact.

Legacy orchestration RED/GREEN:

```text
$ python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
Ran 202 tests in 10.832s
FAILED (failures=7, errors=1)

$ python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py -k 'audit_blocked_runs_remediation or audit_blocked_uses_deterministic or autonomous_audit_blocked_runs_remediation'
3 failed, 200 deselected in 0.38s

$ python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py -k 'audit_blocked_runs_remediation or audit_blocked_uses_deterministic or autonomous_audit_blocked_runs_remediation or ignores_legacy_open or does_not_generate_legacy or run_auditor_fake_is_disabled or cadence_does_not_run'
8 passed, 195 deselected in 0.29s
```

The three focused failures proved migration cleanup still emitted
`audit-002.json`; cleanup now writes only `audit-remediation-result.json` with
an empty `new_audit_report` and leaves the original report readable.

Production cadence/application and lease-boundary RED/GREEN found during
self-review:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'queued_degraded_review or propagates_outbox_failure'
2 failed, 34 deselected in 0.20s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'queued_degraded_review or propagates_outbox_failure'
2 passed, 34 deselected in 0.12s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'lease_loss_before_persistence or lease_loss_before_file_write'
3 failed, 35 deselected in 0.24s

$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py -k 'lease_loss_before_persistence or lease_loss_before_file_write'
3 passed, 35 deselected in 0.13s
```

These failures proved degraded reviews advanced cadence, application failures
were misclassified as degradation, and outbox persistence preceded the first
lease checkpoint. Only `review_complete` now advances cadence; degradation
releases/requeues the reservation, accepted-review application failures
propagate, and all persistence/file/finalization boundaries are checkpointed.

### Final verification

Required brief command:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_contracts.py
146 passed in 4.29s
```

Broad Supervisor, Worker, recovery, state, agents, Auditor migration, auto-resume,
and Dashboard evaluator regressions:

```text
$ python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_models.py scripts/tests/test_harness_loop_supervisor_store.py scripts/tests/test_harness_loop_supervisor_registry.py scripts/tests/test_harness_loop_supervisor_executors.py scripts/tests/test_harness_loop_supervisor_worker.py scripts/tests/test_harness_loop_supervisor_recovery.py scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_agents.py scripts/tests/test_harness_loop_auditor.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_loop_dashboard_evaluator.py
295 passed, 2 subtests passed in 13.47s
```

Full orchestrator regressions:

```text
$ python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
Ran 202 tests in 11.181s
OK
```

Static and syntax checks:

```text
$ ruff check scripts/harness_loop_auditor.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/models.py scripts/loop_supervisor/registry.py scripts/loop_supervisor/reviewer.py scripts/loop_supervisor/reviewer_outbox.py scripts/loop_supervisor/reviewer_runtime.py scripts/loop_supervisor/reviewer_safety.py scripts/loop_supervisor/store.py scripts/loop_supervisor/worker.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py
All checks passed!

$ python3 -m py_compile scripts/harness_loop_auditor.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/loop_supervisor/models.py scripts/loop_supervisor/registry.py scripts/loop_supervisor/reviewer.py scripts/loop_supervisor/reviewer_outbox.py scripts/loop_supervisor/reviewer_runtime.py scripts/loop_supervisor/reviewer_safety.py scripts/loop_supervisor/store.py scripts/loop_supervisor/worker.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_harness_loop_orchestrator.py scripts/tests/test_harness_loop_supervisor_reviewer.py scripts/tests/test_harness_loop_supervisor_reviewer_runtime.py scripts/tests/test_harness_loop_supervisor_store.py
exit 0; no output

$ git diff --check
exit 0; no output
```

### Review finding self-check

1. Cadence reservations advance only on `review_complete`; cancellation and
   degradation release cadence and requeue the stable action. Two-parent lineage
   counting survives continuations and ten-minute coalescing remains reserved by
   project-global ledger rows.
2. `queue_owner` is part of action identity and atomic lease predicates. Ordinary
   Worker leasing defaults to Worker-owned actions only; Reviewer and Supervisor
   actions require explicit owner sets.
3. Reviewer and per-target application leases heartbeat in background threads.
   Explicit checkpoints precede evidence/prompt/accepted writes, outbox
   persistence, run-file writes, decisions, target finalization, and cadence
   completion/release.
4. Registry rules own target transitions. Accepted reviews bind target revision
   and fingerprint; the per-target outbox preflights all targets, persists before
   mutation, resumes after file-write cutpoints, and marks the review complete
   only after every target is applied.
5. Every attempt records a fresh persisted deterministic safety gate. Evidence
   and setup exceptions degrade inside the attempt boundary; fail-open requires
   that fresh gate to pass, while accepted-review application errors propagate.
6. Skill Governance ignores logs and forgeable run-local JSON. Confirmed usage
   comes only from Supervisor `skill_invocations` tied to successful action
   attempts, owned artifact paths, and matching SHA-256 hashes.
7. Finding IDs remain stable by `finding_key`; legal transitions are
   `open -> open|closed|accepted_risk`; terminal findings cannot reopen; closure
   requires fresh finding-specific evidence. Historical migration rows remain
   readable.
8. `run_auditor`, report writers, automatic boundaries, and the private
   `audit_blocked` producer are disabled. Existing reports/phases remain readable
   and migration cleanup emits no successor audit report.
9. The production prompt embeds a machine-readable strict schema with exact
   top-level, finding, keep/delete, and merge contracts plus a canonical fixture
   accepted by `validate_review_payload` after substituting a trusted bundle hash.

### Service evidence

No service was restarted. Existing services remained online:

```text
$ curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health
{"status":"ok","bind_host":"0.0.0.0","bind_port":8765,"authenticated":false,"warning":"No login is enabled. Expose this service only on a trusted network."}

$ curl --noproxy '*' -fsSI http://127.0.0.1:5173/
HTTP/1.1 200 OK

$ curl --noproxy '*' -fsS http://127.0.0.1:8766/api/health
{"status":"ok"}
```
