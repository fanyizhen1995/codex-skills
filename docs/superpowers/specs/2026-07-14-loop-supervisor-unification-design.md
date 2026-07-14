# Unified Loop Supervisor Design

Date: 2026-07-14

Task: `loop-supervisor-unification-01`

## Status

Approved in conversation. This spec supersedes the runtime ownership and Auditor boundaries in:

- `docs/superpowers/specs/2026-07-08-loop-auditor-design.md`
- `docs/superpowers/specs/2026-07-09-loop-supervisor-design.md`

Historical documents remain useful as implementation history, but this document is authoritative for future loop runtime work.

The frontend contract is:

- `docs/superpowers/mockups/2026-07-14-loop-supervisor-unification-mock.html`

Every state, metric, row, tab, and pagination control in that mock must be backed by the producers, SQLite schema, APIs, and tests defined here. Missing data must render as unavailable, never as synthetic success.

## Problem Statement

The current runtime has three overlapping control layers:

1. `harness_loop_orchestrator.py` executes phases and also makes multi-round decisions.
2. `harness_loop_auto_resume.py` independently decides which interrupted states can resume.
3. `harness_loop_supervisor.py` independently classifies states, creates continuations, restarts services, and opens user decisions.

This split has caused production behavior that is worse than the pre-Supervisor loop in several respects:

- Supervisor and auto-resume maintain different recoverable-state allowlists.
- A local, recoverable failure can create a project-wide stop through one open user decision.
- Planner, Generator, and Evaluator retry exhaustion becomes `unsupported_state` instead of a recovery workflow.
- Agent timeouts discard useful on-disk work because there is no partial-artifact recovery contract.
- The same unchanged decision is appended every 30 seconds. By 2026-07-14, `run-decisions.jsonl` had 254,508 rows and occupied about 140 MB.
- Seventeen user-decision files had been created; sixteen were archived and one remained open. Since 2026-07-10, two real AI infra runs produced 6,330 repeated `unsupported_state` observations.
- Parent-22 remained blocked for four days even though its Generator had produced substantial validated output and all four managed services were healthy.

The current Auditor does not provide the intended LLM global review:

- `run_auditor(..., driver="codex-exec")` exists, but automatic audit boundaries call `write_rule_based_audit_report(...)` directly.
- Actual reports are deterministic threshold reports, not global LLM judgments.
- Supervisor consumes Auditor decisions while also making control decisions, creating an unnecessary role boundary.

The Dashboard also grows poorly:

- Supervisor section labels are not real interactive tabs.
- Events and logs APIs return unpaginated collections.
- Child tasks, findings, diagnostics, artifacts, skills, and acceptance scenarios are rendered in full or silently truncated.
- New content extends the page vertically and makes long-running projects progressively harder to read.

## Goals

1. Present one public runtime role: Loop Supervisor.
2. Fold orchestrator execution, auto-resume recovery, and Auditor judgment into one Supervisor subsystem with clear internal modules.
3. Keep long-running Agent execution in a separate Worker process so the control plane remains responsive.
4. Use one transition registry, one retry policy, one stop policy, and one user-escalation policy.
5. Recover useful partial Agent output before rerunning work.
6. Run a real read-only LLM Reviewer from a project-global perspective every two completed semantic parent tasks.
7. Let Reviewer decisions automatically continue, remediate, refocus, or stop an affected run.
8. Isolate user decisions to the affected run except for explicit global safety conditions.
9. Replace repetitive JSONL runtime state with a transactional SQLite control store.
10. Give every growing Dashboard collection real server-side pagination and stable navigation.
11. Preserve Crawler Workbench backend/frontend, Loop Dashboard, and Supervisor availability during development and migration.
12. Prove the final system with unit, integration, browser E2E, restart, migration, and four-parent live soak tests.

## Non-Goals

- Do not replace Planner, Generator, or Evaluator.
- Do not let Reviewer replace task-level functional acceptance.
- Do not put all control and execution code in one process or one giant file.
- Do not introduce Celery, Temporal, Redis, or another external workflow service.
- Do not expose mutation APIs outside the existing trusted network environment.
- Do not auto-merge demand-development work that still has an explicit human merge gate.
- Do not commit `.codex/supervisor/supervisor.db` or runtime logs.
- Do not migrate legacy Auditor reports into the new Reviewer model.
- Do not lose current parent-22, crawler raw, or other pre-existing dirty work during migration.

## Confirmed Decisions

- Architecture: one Loop Supervisor subsystem backed by SQLite and an independent Executor Worker process.
- Public roles: Supervisor, Supervisor Reviewer, Worker, Planner, Generator, and Evaluator.
- Removed public roles: orchestrator, auto-resume, and Auditor.
- Reviewer failure policy: fail open when deterministic safety gates pass; record `review_degraded` and retry later.
- User decisions are run-scoped by default.
- Recovery policy: three retries, then one alternate recovery plan, then Reviewer escalation.
- Reviewer scope: project-global, not current-run-only.
- Reviewer cadence: every two completed semantic parent tasks, with early review on strong stagnation or repeated-recovery signals.
- Reviewer authority: `continue`, `auto_remediate`, `refocus`, and `stop_run` apply automatically. Global stop, permission expansion, and irreversible operations require the user.
- Legacy Auditor UI and report compatibility are removed.
- Skill inventory moves to a Supervisor `Skill Governance` tab.
- Runtime history records state changes only, rotates at 10 MB, retains detailed history for 90 days, and keeps long-term aggregates.
- Dashboard layout: real tabs plus server-side cursor pagination, default page size 20, selectable 20/50/100.

## Architecture

### Public Runtime

```text
Loop Supervisor
  +-- Reconciler
  +-- Transition Registry
  +-- Decision Engine
  +-- Recovery Engine
  +-- Reviewer Scheduler
  +-- Service Keeper
  +-- SQLite Action Queue
  +-- Executor Worker process
        +-- Planner Executor
        +-- Generator Executor
        +-- Evaluator Executor
        +-- Evidence Gates
        +-- Commit / Push / Cleanup
```

The Dashboard talks only to the Supervisor read API. Operator documentation starts and stops only `loop-supervisor`, `loop-supervisor-worker`, and `loop-dashboard` for loop operations.

### Process Boundaries

#### Supervisor process

- Reconciles run files and runtime evidence.
- Computes the next desired action from the shared transition registry.
- Creates idempotent queue entries.
- Tracks action leases and Worker heartbeat.
- Classifies failures and chooses recovery tiers.
- Schedules project-global LLM reviews.
- Applies validated Reviewer decisions.
- Maintains services, decisions, freshness, retention, and Dashboard projections.

The Supervisor never synchronously runs a long Planner, Generator, Evaluator, or Reviewer prompt inside its watch loop.

#### Executor Worker process

- Atomically leases one queued action.
- Acquires the per-run lock and, for mutations, the repository mutation lock.
- Calls one bounded execution primitive.
- Renews its lease and heartbeat while the action runs.
- Writes structured result and evidence paths.
- Does not decide the next action.

Only one Git-mutating action may execute in a repository at a time. Read-only service checks and Reviewer preparation may run concurrently.

#### Reviewer process

Reviewer is a short-lived, read-only LLM subprocess launched by Supervisor. It has no direct write access to `run.json`, SQLite decision tables, or repository content. Its output is validated before Supervisor applies it.

## Orchestrator Consolidation

The current orchestrator is not retained as a public role. Its useful capabilities move into focused Supervisor executor modules:

- phase execution
- Agent prompt execution and timeout capture
- contract validation
- deterministic evidence gates
- artifact hygiene
- commit, push, and cleanup
- demand and autonomous run-specific state transitions

During implementation, the current `harness_loop_orchestrator.py` CLI becomes a temporary compatibility adapter that submits a Supervisor action. It must emit a deprecation warning and must not own a second transition policy. All documented commands and tests must use Supervisor entrypoints, and the public adapter must be removed before this task is marked complete.

`harness_loop_auto_resume.py` loses its watcher and independent actionable-state list. A temporary one-shot compatibility command may request Supervisor reconciliation but cannot execute a run itself.

`harness_loop_auditor.py`, Auditor CLI commands, audit remediation state, Auditor Dashboard tab, and legacy audit report readers are removed after migration acceptance.

## State Ownership

### File artifacts

`run.json` remains the portable execution fact for one run. Planner, Generator, Evaluator, scenario, trusted live evidence, verification, and commit artifacts remain files under the run directory.

### SQLite control store

`.codex/supervisor/supervisor.db` is the operational source of truth for scheduling, recovery, review, and queries. It is runtime-only and rebuildable from run files plus retained transition artifacts.

Use Python `sqlite3`, WAL mode, foreign keys, busy timeout, explicit transactions, and schema migrations. No new dependency is required.

Core tables:

| Table | Purpose |
|---|---|
| `runs` | Current run projection, policy, phase, parent/child relation, revision, update time |
| `actions` | Idempotent queue entry, priority, status, lease, Worker, and desired transition |
| `action_attempts` | Attempt timing, result class, error class, evidence, and recovery tier |
| `transitions` | Actual state changes only |
| `failures` | Stable failure key, first/last occurrence, count, current resolution |
| `reviews` | Reviewer trigger, evidence bundle, model execution status, validated decision |
| `review_findings` | Project-global finding lifecycle and remediation linkage |
| `user_decisions` | Genuine run-scoped or global user decisions |
| `services` | Current reachability, process, and version projection |
| `freshness_checks` | Target-specific crawler/wiki/search/frontend freshness history |
| `skill_snapshots` | Project skill inventory, duplicate groups, and recommendations |
| `aggregates` | Long-term counts after detailed retention expires |

### Atomicity and reconciliation

- Every action has an idempotency key derived from project, run revision, phase, action type, and task identity.
- Repeated reconcile updates an existing queue record rather than enqueueing a duplicate.
- The Worker claims an action with an atomic status-and-lease update.
- A lease can be reclaimed only after expiry and a missing Worker heartbeat.
- Run-file changes are revisioned. If the file write succeeds but the SQLite projection fails, the next reconcile repairs SQLite. If SQLite marks an action complete but run state did not advance, the action is not considered successful and is reconciled again.
- Git failures are explicit errors, never clean-state fallbacks.

## Transition Registry

One table-driven registry is imported by Supervisor, Worker adapters, tests, and compatibility CLIs. Each entry defines:

- policy
- phase
- optional next action
- executable action type
- whether it mutates Git
- allowed result classes
- recovery policy
- terminal classification
- user escalation eligibility

No other module may maintain an independent actionable-phase or stopped-blocked whitelist.

Registry coverage tests must fail when a schema-allowed phase has no explicit transition behavior.

## Action Result Contract

Every bounded Worker action returns one of:

| Result | Meaning | Default handling |
|---|---|---|
| `success` | Phase completed and evidence validates | Advance through registry |
| `retryable_failure` | Transient capacity, transport, DNS, Git lock, or process failure | Retry with classified backoff |
| `recoverable_partial` | Action timed out or exited but useful valid artifacts exist | Run artifact recovery |
| `policy_block` | Secret, permission, path scope, or irreversible operation | Run-scoped or global safety decision |
| `terminal_failure` | State is corrupt or recovery cannot be proven | Reviewer or user escalation |

Results include `error_class`, `failure_key`, `artifact_paths`, `checkpoint`, `started_at`, `finished_at`, and a human-readable summary. Raw stdout/stderr stay in files and are loaded on demand.

## Recovery Policy

### Tier 1: classified retry

Retry the same action at most three times. Backoff is based on error class and includes jitter. The recovery ledger is per stable failure key and task, not a global process counter.

### Tier 2: one alternate recovery plan

After Tier 1 exhaustion, Supervisor chooses one bounded alternate plan:

- validate on-disk artifacts and reconstruct the missing result envelope
- rerun only missing verification commands
- resume from a recorded checkpoint
- reduce the current task boundary while preserving its goal
- replan the same goal while explicitly excluding the failed approach

Alternate recovery cannot silently weaken safety, evidence, evaluator, or commit gates.

### Tier 3: Reviewer escalation

If alternate recovery fails, Supervisor triggers an early Reviewer pass. Reviewer may return:

- `auto_remediate`
- `refocus`
- `stop_run`
- `ask_user`

Only `ask_user` creates a user decision. A technical failure is not itself sufficient reason to ask the user.

### Partial artifact recovery

Before rerunning an Agent after timeout, recovery must inspect:

- expected output envelope
- changed paths
- verification manifests and command results
- gap proof and required evidence
- evaluator prerequisites
- current Git diff and baseline ownership

If artifacts satisfy the normal contract, Supervisor reconstructs only the missing envelope with explicit `recovered_from_attempt` provenance and proceeds to Evaluator. If evidence is incomplete, the alternate action runs only the missing work. It never marks the task complete without independent Evaluator acceptance.

Parent-22 is the required real migration case for this behavior.

## User Decision and Stop Policy

Run-scoped decisions pause only affected runs. Other independent runs and continuations remain eligible.

Global stop is allowed only for:

- confirmed secret or credential exposure
- repository corruption that prevents trustworthy ownership checks
- an explicit user global stop
- required permission expansion affecting the project
- an irreversible operation requiring approval

Demand-development `passed_waiting_human_merge` remains a deliberate run-scoped human gate.

Resolved decisions close automatically when their failure condition is no longer present. An archived or resolved decision cannot block a continuation.

## Supervisor Reviewer

### Triggering

- Regular trigger: every two completed semantic parent tasks.
- Early trigger: repeated recovery exhaustion, strong stagnation signal, repeated failure class after remediation, or evidence of direction drift.
- A single transient Agent failure does not trigger Reviewer before Tier 1 recovery.

Regular cadence is tracked by stable `loop_lineage_id`, not by continuation run ID. The counter survives continuation creation, ordinary parent completions increment it, and audit-remediation or technical-recovery actions do not. A due lineage triggers a project-global review and advances only that lineage's cadence ledger. If several lineages become due within the same ten-minute window, Supervisor coalesces them into one global review whose evidence bundle names every triggering lineage.

### Evidence bundle

The orchestrator-owned evidence bundle includes:

- current objective, constraints, and global stop conditions
- semantic parent progress since the last review
- Planner, Generator, and Evaluator summaries
- commits, pushes, changed paths, and domain output metrics
- failure keys, recovery attempts, and whether prior remediation worked
- service and target-specific data freshness
- current user decisions and blocked runs
- project skill inventory and duplicate groups
- prior Reviewer findings and closure evidence

Supervisor gathers and hashes this evidence. Reviewer cannot rely on an Agent's unverified self-report.

### Output contract

Reviewer returns:

```json
{
  "schema_version": 1,
  "review_id": "review-0001",
  "scope": "project",
  "decision": "continue | auto_remediate | refocus | stop_run | ask_user",
  "affected_run_ids": [],
  "summary": "operator-readable global judgment",
  "evidence_refs": [],
  "findings": [],
  "skill_governance": [],
  "next_review_after_parent_tasks": 2
}
```

Supervisor validates affected runs, evidence hashes, allowed decision values, and prohibited operations before application.

### Reviewer failure

Timeout, capacity, malformed output, or temporary unavailability writes `review_degraded`. If deterministic safety gates pass, the loop continues and Reviewer retries at the next cadence. Reviewer infrastructure failure does not become a user decision by itself.

### Authority

Validated `continue`, `auto_remediate`, `refocus`, and `stop_run` apply automatically. `ask_user`, project-wide stop, permission expansion, and irreversible actions require the user.

## Skill Governance

Skill inventory is a project-level Supervisor concern. It is not repeated in each run detail.

Supervisor produces periodic snapshots with:

- total project skills
- skills referenced by verified execution evidence
- candidate process skills
- duplicate or overlapping groups
- merge, keep, or delete recommendations

Log substring matches are not usage proof. Reviewer may recommend consolidation, but deletion or modification of committed skills follows normal task implementation and evaluation.

## Runtime History and Retention

- Persist only state transitions and changed decisions.
- For an unchanged observation, update `occurrence_count`, `last_seen_at`, and aggregate counters in place.
- Rotate exported detailed logs at 10 MB.
- Retain detailed transition, action-attempt, and review rows for 90 days.
- Compact expired rows into daily and per-failure aggregates before deletion.
- Do not write one decision row per Supervisor tick.
- Large stdout/stderr files use normal artifact retention and are not copied into SQLite.

## Service Health

Supervisor manages:

- Crawler Workbench backend
- Crawler Workbench frontend
- Loop Dashboard
- Supervisor Executor Worker

Health distinguishes endpoint reachability, process/session existence, heartbeat, running code fingerprint, and target-specific data freshness.

A tmux session that exists but has a dead or unhealthy process is not healthy. Supervisor may terminate and restart only allowlisted managed services, then must verify endpoint, PID, heartbeat, and version before reporting recovery.

## Dashboard and API

### Global information architecture

The global Supervisor control plane is separate from task run history. It has real interactive tabs:

1. Overview
2. Services
3. Task Recovery
4. Reviewer
5. Decisions
6. Skill Governance
7. Configuration

Run detail retains:

1. Overview
2. Children
3. Agent Results
4. Acceptance
5. Logs
6. Block Diagnostics
7. Artifacts

Auditor is removed from run detail. Orchestrator and auto-resume are not displayed as independent roles.

### Pagination contract

All growing collection endpoints support stable cursor pagination:

```json
{
  "items": [],
  "next_cursor": "opaque-or-null",
  "previous_cursor": "opaque-or-null",
  "page_size": 20,
  "total": 126,
  "has_more": true
}
```

Rules:

- default page size: 20
- allowed page sizes: 20, 50, 100
- stable sort uses timestamp plus primary key
- cursors are opaque and validated
- invalid cursors return HTTP 400
- new rows do not reorder the user's already-open page
- each tab stores cursor, page size, sort, filter, and query in the URL
- changing filter resets only that tab to the first page

Server-side pagination is mandatory for:

- transitions and events
- logs
- actions and attempts
- recovery records
- Reviewer reports and findings
- decisions
- services and freshness history
- skill snapshots and skill rows
- run list and completed history

Children, acceptance scenarios, diagnostics, and artifacts use the same frontend pagination component and an API paged collection when their count can grow beyond one page.

### Log detail

Log lists return metadata and a bounded summary. Full content is fetched through a separate safe artifact endpoint when the user expands one row. The endpoint enforces path containment, redaction, and a response-size limit.

### Required endpoints

Exact route grouping may follow existing FastAPI conventions, but the implementation must provide equivalent contracts for:

- Supervisor summary
- services and freshness
- actions and attempts
- transitions
- reviews and findings
- decisions
- skill governance
- paged run list
- paged run events and logs
- bounded log detail

## Dashboard Mock Contract

The mock at `docs/superpowers/mockups/2026-07-14-loop-supervisor-unification-mock.html` is an acceptance artifact. It demonstrates:

- Supervisor as the only global control role
- Worker health and queue state
- real tabs rather than decorative labels
- Reviewer global judgment and automatic action
- run-scoped user decisions
- recovery attempts and partial artifact salvage
- Skill Governance outside run detail
- pager, page-size control, filters, stable counts, and long-row expansion
- honest unavailable/degraded states

The implementation evaluator must compare the delivered page with the mock's key structure and interactions.

## Migration

### Protection first

Before cutover:

- inventory current tracked and untracked paths
- preserve parent-22 partial work and newer crawler raw files
- snapshot current run directories and Supervisor artifacts outside Git
- do not reset, clean, or overwrite user or crawler work

### Shadow phase

1. Build SQLite, registry, Reconciler, Worker, and Reviewer behind isolated runtime paths.
2. Run new Supervisor in shadow mode against copied run artifacts.
3. Old runtime remains the only executor.
4. Compare desired actions, stop decisions, failure classification, and continuation decisions.
5. Any difference that increases user intervention blocks cutover until explained and tested.

### Cutover

1. Stop old Supervisor and auto-resume watcher.
2. Migrate and compact existing Supervisor JSONL into SQLite transitions, failures, and aggregates.
3. Rebuild run projections from `run.json`.
4. Validate counts, open decisions, active runs, and service state.
5. Start `loop-supervisor` and `loop-supervisor-worker`.
6. Recover parent-22 through partial-artifact recovery.
7. Verify Evaluator, commit, push, crawler/wiki/search/frontend freshness, and Dashboard visibility.
8. Run four consecutive semantic parent tasks without manual phase advancement.

### Removal

After acceptance:

- delete old Supervisor JSONL runtime files after verified compaction
- delete legacy audit runtime reports
- remove Auditor Dashboard/API readers
- remove auto-resume watcher and service registration
- remove public orchestrator execution entrypoints after the compatibility window
- update AGENTS.md and harness docs with the new start, stop, health, and recovery commands

SQLite is rebuildable from retained run artifacts and migrations. A failed cutover rolls back by stopping the new processes and restoring the runtime snapshot; it must not alter Git-tracked knowledge content.

## Test Strategy

All tests in this section are required for delivery and must pass before cutover.

### Unit tests

- every schema-allowed phase has an explicit registry behavior
- Supervisor, Worker, and compatibility CLI import the same registry
- action idempotency and duplicate reconcile
- lease claim, renewal, expiry, and reclaim
- repository mutation lock exclusion
- classified backoff and three-attempt ceiling
- partial-artifact classification and envelope reconstruction
- alternate recovery only once per stable failure key
- run-scoped versus global decision rules
- Reviewer cadence and early-trigger rules
- Reviewer output validation and fail-open behavior
- Reviewer automatic `refocus` and `stop_run`
- SQLite migrations, rollback, rebuild, and retention compaction
- cursor encode/decode, stable sort, invalid cursor, page-size limits
- log-summary and bounded-detail redaction

### Integration tests

1. Generator times out with valid artifacts; Supervisor reconstructs the result and Evaluator runs.
2. Generator times out with incomplete artifacts; alternate recovery runs only missing work.
3. Worker exits with a live lease; the lease expires and exactly one Worker reclaims it.
4. One run needs the user; an independent run and continuation still advance.
5. Two semantic parent tasks trigger one project review.
6. Reviewer timeout produces `review_degraded` and does not block a safe loop.
7. Reviewer `refocus` changes the next Planner contract.
8. Reviewer `stop_run` stops only affected runs.
9. Supervisor restart reconstructs pending actions without duplicates.
10. tmux exists but managed process is dead; Supervisor restarts and verifies it.
11. JSONL migration deduplicates repeated ticks and preserves first/last/count.
12. Old Auditor and auto-resume artifacts do not re-enter the new state model.

### Browser E2E scenarios

1. A user opens Supervisor and switches through all seven real tabs.
2. A user paginates actions, reviews, decisions, skills, run events, and logs.
3. Page 2 contains no duplicates from page 1.
4. Page size changes among 20, 50, and 100 and persists in the URL.
5. Filters reset only the current tab cursor.
6. Refresh restores the selected tab, page, filter, and selected run.
7. A new record does not move the user's current page.
8. A user expands one log row and receives bounded, redacted content.
9. Reviewer degraded, Worker offline, no data, and user-decision states display honestly.
10. Auditor, auto-resume, and orchestrator do not appear as independent roles.
11. Skill Governance shows inventory and consolidation recommendations.
12. The delivered page matches the mock's key hierarchy and controls at desktop and mobile viewports.

### Live soak acceptance

- Crawler backend/frontend and Dashboard remain reachable during the run.
- Supervisor and Worker remain online and current.
- Parent-22 is recovered without manually reconstructing its Generator result.
- Four consecutive semantic parent tasks complete without manual phase commands.
- One Reviewer pass occurs after every two completed parents.
- At least one injected retryable failure recovers without a user decision.
- No unchanged decision is written once per tick.
- No project-global stop is created by a run-scoped failure.
- New knowledge is committed, pushed to `origin/main`, and visible through API, search, Wiki browse, frontend, and Dashboard.

## Delivery Phases

1. Shared registry and bounded executor interfaces.
2. SQLite store, Reconciler, action queue, and Worker leases.
3. Recovery tiers and partial-artifact salvage.
4. Supervisor Reviewer and Skill Governance.
5. Dashboard API pagination and mock-matching frontend.
6. Shadow comparison, migration, cutover, legacy removal, and four-parent soak.

Each phase must have focused tests and leave the old production runtime usable until the cutover phase.

## Completion Gate

The task is incomplete unless all are true:

- Supervisor is the only public control role.
- Worker executes queued actions without independent policy.
- No independent auto-resume watcher runs.
- No independent Auditor, auto-resume watcher, or public orchestrator runtime remains when the task is marked complete.
- Transition behavior comes from one registry.
- SQLite action, failure, review, and decision data are transactional and paged.
- Parent-22 partial output is recovered through the production mechanism.
- Reviewer is a real LLM global review and not a deterministic report labeled as LLM judgment.
- Reviewer outages fail open when deterministic safety gates pass.
- run-scoped failures do not stop independent runs.
- Dashboard implements every mock-visible tab, state, metric, and pagination interaction.
- Required unit, integration, browser E2E, migration, and live soak tests pass.
- Crawler and Dashboard services reflect current code and knowledge data.
- Implementation, migration, and resulting wiki/crawler artifacts are committed and pushed according to repository rules.

## Open Questions

No product questions remain. Implementation details may be refined only when they preserve the confirmed behavior and mock contract above.
