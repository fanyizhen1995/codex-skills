# Loop Supervisor Design

Date: 2026-07-09

## Goal

Implement `loop-supervisor-01`: a long-running project-level control plane that keeps the local loop system operating without repeated manual intervention. The Supervisor owns runtime control, not task quality judgment. It keeps Crawler Workbench backend/frontend, Loop Dashboard, and loop recovery online; monitors loop run state; automatically resumes or continues eligible runs; escalates repeated failures; and records operator-readable evidence for every decision.

The current mock is:

- `docs/superpowers/mockups/2026-07-09-loop-supervisor-dashboard-mock.html`

The mock is a contract, not decorative art. Every visible claim in the mock must either be implemented from real Supervisor/Dashboard data or shown as explicitly unavailable. The implementation must not hard-code successful states in the frontend.

## Completion Gate

This task must ship a complete Supervisor slice, not a display-only placeholder. The implementation is incomplete unless all mock-visible Supervisor functions have production data, backend API exposure, frontend rendering, and automated verification.

Minimum complete scope:

- Supervisor runtime writes valid `.codex/supervisor/*` artifacts.
- Dashboard reads those artifacts through backend APIs and renders the global Supervisor section outside the task run list.
- Service health includes reachability, tmux state, runtime version evidence, and stale-version detection.
- Crawler data freshness is target-specific and can fail honestly.
- `stopped_budget` autonomous runs are classified idempotently and can produce continuation plans.
- Retry ceiling and user-decision escalation are implemented from stable `failure_key` records.
- Auditor decisions are consumed as control inputs without Supervisor inventing process-quality conclusions.
- Browser evaluator proves the mock-visible states with fixtures and verifies missing data does not appear as green success.
- Watch mode can run safely against the real project after fixture-backed tests pass.

It is not acceptable to complete this task with only Dashboard panels, static fixture display, or API shells that do not have a Supervisor producer behind them. If implementation discovers a required mock-visible field is not feasible, the field must be removed from the mock/spec or shown as explicitly unavailable before the task can pass.

## Confirmed Decisions

- Architecture choice: create an independent `scripts/harness_loop_supervisor.py` and reuse the existing `scripts/harness_loop_auto_resume.py` as a lower-level recovery primitive.
- Service recovery: the Supervisor may automatically restart trusted local tmux services for Crawler Workbench backend, Crawler Workbench frontend, Loop Dashboard, and loop auto-resume.
- Retry ceiling: for the same `run_id` and `failure_key`, three consecutive failed recovery attempts stop automatic retry and create a user-decision record.
- `autonomous_knowledge` `stopped_budget`: the Supervisor may create a next continuation run when global stop conditions are not met.
- `demand_development` completed state: stays at the human merge/approval gate; the Supervisor does not auto-merge or auto-continue past user approval.
- UI placement: Supervisor is a global agent/control-plane role and must not be shown as an item in the task run list. It gets its own global Dashboard section above or beside task runs.

## Supervisor vs Auditor Boundary

Supervisor is the runtime control plane. It answers: "Can the system keep running, and what operational action should happen next?"

Examples:

- Is crawler backend/frontend online?
- Is the running service version current?
- Is crawler/search/wiki/frontend data fresh after ingest?
- Is a loop stale, blocked, or stopped by budget?
- Should auto-resume be called?
- Should a tmux service be restarted?
- Should an autonomous continuation run be created?
- Has the same failure exceeded the retry ceiling?

Auditor is the process-review plane. It answers: "Is the loop doing the right work in the right way?"

Examples:

- Is the loop empty-spinning?
- Is it tunnel-visioned on a local issue?
- Is it repeatedly making the same class of error?
- Is it doing shallow ingestion instead of deep source-backed work?
- Are skills proliferating and needing consolidation?
- Should the next planner refocus, continue, stop, or remediate?

Interaction rule:

- Auditor produces `must_fix`, `should_fix`, `refocus`, `stop`, or `continue`.
- Supervisor consumes those conclusions and executes the operational decision: recover, create remediation, refocus the next run, stop, or request user decision.
- Supervisor must not invent process-quality conclusions that belong to Auditor.

## Architecture

### Components

1. `scripts/harness_loop_supervisor.py`
   - CLI entrypoint for one-shot and watch modes.
   - Discovers runs, checks services, evaluates freshness, invokes recovery, creates continuation runs, writes state artifacts.

2. `scripts/harness_loop_supervisor_state.py` or equivalent focused module
   - Defines schemas and helpers for Supervisor state, decisions, service checks, failure counters, and user-decision records.
   - Keeps schema logic separate from orchestration code.

3. Existing `scripts/harness_loop_auto_resume.py`
   - Retained as a lower-level primitive for known actionable states.
   - Supervisor may call it instead of duplicating `audit_blocked`, `stopped_blocked`, and interrupted phase recovery logic.

4. Existing `scripts/harness_loop_orchestrator.py`
   - Retained as owner of PGE run execution, autonomous continuation, required-evidence gates, cleanup, and commits.
   - Supervisor may call public CLI/function entrypoints but should not duplicate internal gate logic.

5. Loop Dashboard backend/frontend
   - Adds a project-level Supervisor section separate from task run list.
   - Reads Supervisor artifacts and current task run summaries.

### Artifact Directory

Supervisor writes to:

`.codex/supervisor/`

This is intentionally separate from `.codex/loop-runs/<run-id>/` because Supervisor is global and not a task run.

Required files:

- `supervisor-state.json`
- `events.jsonl`
- `service-health.json`
- `run-decisions.jsonl`
- `recovery-attempts.jsonl`
- `needs-user-decisions/<decision_id>.json`
- `continuation-plans.jsonl`
- `freshness-targets.jsonl`

Dashboard may also expose these artifacts through a synthetic global section, but must not insert `loop-supervisor` into the task run list.

## State Model

### `supervisor-state.json`

Required fields:

```json
{
  "schema_version": 1,
  "project_root": "/home/fyz/codex-skills",
  "status": "healthy | degraded | blocked | stopped",
  "started_at": "ISO-8601",
  "last_heartbeat_at": "ISO-8601",
  "last_tick_at": "ISO-8601",
  "mode": "once | watch",
  "watch_interval_seconds": 30,
  "service_summary": {
    "total": 4,
    "healthy": 4,
    "degraded": 0,
    "blocked": 0
  },
  "run_summary": {
    "active": 0,
    "blocked": 0,
    "continuation_candidates": 0,
    "needs_user_decision": 0
  },
  "failure_summary": {
    "open_failure_keys": 0,
    "max_consecutive_failures": 3
  },
  "last_decision": {
    "decision_id": "string",
    "action": "observe | resume | restart_service | create_continuation | request_user_decision | stop",
    "summary": "string"
  }
}
```

### `service-runtime/<service>.json`

Each long-running service must write or be launched with a runtime metadata file under:

`.codex/service-runtime/<service>.json`

Required fields:

```json
{
  "schema_version": 1,
  "service": "crawler-backend",
  "tmux_session": "personal-wiki-crawler-backend",
  "pid": 12345,
  "cwd": "/home/fyz/codex-skills/personal-wiki/apps/crawler_workbench/backend",
  "command": "python3 -m uvicorn crawler_workbench.main:app --host 0.0.0.0 --port 8765",
  "host": "0.0.0.0",
  "port": 8765,
  "repo_root": "/home/fyz/codex-skills",
  "git_head": "79b0608",
  "origin_main": "79b0608",
  "started_at": "ISO-8601",
  "config_fingerprint": "sha256 string"
}
```

Supervisor must not infer "running latest" from repository `HEAD` alone. A service is latest only when all are true:

- endpoint is reachable;
- tmux session exists when expected;
- runtime metadata exists and is fresh;
- runtime `pid` is still alive;
- runtime `cwd` is under the expected repo/worktree;
- runtime `git_head` matches the expected head for that service;
- runtime port matches the configured endpoint.

If a service cannot yet emit runtime metadata, the UI must show version freshness as `不可用`, not `最新`.

### `service-health.json`

Required top-level shape:

```json
{
  "schema_version": 1,
  "checked_at": "ISO-8601",
  "services": []
}
```

Required fields per `services[]` item:

```json
{
  "service": "crawler-backend",
  "kind": "http | tmux | http_and_tmux",
  "expected_endpoint": "http://127.0.0.1:8765/api/health",
  "tmux_session": "personal-wiki-crawler-backend",
  "status": "healthy | degraded | blocked",
  "reachable": true,
  "running_version": {
    "git_head": "79b0608",
    "origin_main": "79b0608",
    "matches_expected": true,
    "runtime_metadata_path": ".codex/service-runtime/crawler-backend.json",
    "evidence": "string"
  },
  "data_freshness": {
    "status": "pass | fail | not_applicable",
    "target_id": "ai-infra-parent-14-atlas-300i-a2",
    "checks": ["search-api", "wiki-api", "frontend-visible"]
  },
  "last_checked_at": "ISO-8601",
  "last_restart_at": "ISO-8601 or empty",
  "last_error": ""
}
```

### `freshness-targets.jsonl`

Crawler/search/wiki/frontend freshness must be target-specific. A green freshness state must be tied to a concrete recently changed source, commit, or run.

Required fields:

```json
{
  "target_id": "ai-infra-parent-14-atlas-300i-a2",
  "source_run_id": "ai-infra-expansion-continuation-20260708",
  "target_commit": "79b0608",
  "domain": "ai_infra",
  "wiki_paths": [
    "personal-wiki/domains/ai_infra/wiki/projects/compute-accelerator-spec-catalog.md"
  ],
  "search_terms": ["Atlas 300I A2", "64 GB"],
  "expected_frontend_text": ["Atlas 300I A2", "compute-accelerator-spec-catalog"],
  "api_checks": [
    {"kind": "wiki-page", "url": "http://127.0.0.1:8765/api/wiki/page", "status": "pass"},
    {"kind": "search", "url": "http://127.0.0.1:8765/api/search", "status": "pass"}
  ],
  "frontend_checks": [
    {"page": "knowledge-workbench", "status": "pass"}
  ],
  "status": "pass | fail | not_applicable",
  "verified_at": "ISO-8601"
}
```

If no freshness target exists after an ingest or commit, Dashboard must show `暂无 freshness target`, not `数据新鲜度：通过`.

### `run-decisions.jsonl`

One JSON object per Supervisor decision:

```json
{
  "decision_id": "supervisor-20260709-0001",
  "run_id": "ai-infra-expansion-continuation-20260708",
  "run_policy": "autonomous_knowledge",
  "phase": "stopped_budget",
  "next_action": "none",
  "classification": "continuation_candidate",
  "action": "create_continuation",
  "reason": "autonomous run reached budget stop and global stop conditions are not met",
  "auditor_verdict": "continue",
  "created_at": "ISO-8601",
  "evidence_paths": [
    ".codex/loop-runs/ai-infra-expansion-continuation-20260708/run.json",
    ".codex/supervisor/service-health.json"
  ]
}
```

### `continuation-plans.jsonl`

Continuation planning must be idempotent. Supervisor must not create more than one continuation for the same completed budget stop unless the previous continuation is explicitly closed or invalidated.

Required fields:

```json
{
  "schema_version": 1,
  "plan_id": "continuation-ai-infra-expansion-continuation-20260708-001",
  "idempotency_key": "autonomous_knowledge:ai_infra:ai-infra-expansion-continuation-20260708:parent-14:79b0608",
  "previous_run_id": "ai-infra-expansion-continuation-20260708",
  "next_run_id": "ai-infra-expansion-continuation-20260709-001",
  "domain": "ai_infra",
  "policy_file": "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
  "previous_phase": "stopped_budget",
  "previous_task_id": "ai-infra-expansion-continuation-20260708-parent-14",
  "previous_commit": "79b0608",
  "parent_task_counter": 14,
  "audit_cadence_state": {
    "unit": "parent_task",
    "interval": 2,
    "completed_since_last_audit": 0
  },
  "global_stop_result": {
    "status": "continue | stop",
    "checked_conditions": []
  },
  "status": "planned | created | skipped | blocked",
  "created_run_path": ".codex/loop-runs/ai-infra-expansion-continuation-20260709-001/run.json",
  "created_at": "ISO-8601"
}
```

Supervisor must check existing plans by `idempotency_key` before creating a new run. If a matching plan is already `created`, it records an `observe` decision instead of creating a duplicate run.

### `recovery-attempts.jsonl`

One JSON object per restart/resume/recovery attempt:

```json
{
  "attempt_id": "recovery-20260709-0001",
  "failure_key": "dashboard_visibility:ai-infra-expansion-continuation-20260708:loop-dashboard-freshness:timeout",
  "run_id": "ai-infra-expansion-continuation-20260708",
  "action": "resume_required_evidence",
  "status": "pass | fail",
  "consecutive_failure_count": 1,
  "max_consecutive_failures": 3,
  "started_at": "ISO-8601",
  "finished_at": "ISO-8601",
  "summary": "string",
  "evidence_paths": []
}
```

### `failure_key` Normalization

`failure_key` is a stable grouping key used for retry ceilings. It must be deterministic and must survive Supervisor restarts.

Format:

`<category>:<scope_id>:<subject_id>:<normalized_error_class>`

Examples:

- `service_down:project:crawler-backend:connection_refused`
- `stale_version:project:crawler-frontend:git_head_mismatch`
- `dashboard_visibility:ai-infra-expansion-continuation-20260708:loop-dashboard-freshness:timeout`
- `required_evidence:ai-infra-expansion-continuation-20260708:loop-dashboard-freshness:missing_pass_detail`
- `dirty_path:ai-infra-expansion-continuation-20260708:personal-wiki/domains/ai_infra/raw:unexpected_path`
- `auditor_stop:ai-infra-expansion-continuation-20260708:latest-audit:stop`

Allowed categories:

- `service_down`
- `stale_version`
- `data_freshness`
- `dashboard_visibility`
- `required_evidence`
- `dirty_path`
- `audit_blocked`
- `auditor_stop`
- `continuation_duplicate`
- `unsupported_state`
- `unsafe_secret`

The retry counter groups by `(run_id or project, failure_key)`. Passing a recovery attempt resets only that exact key.

### `needs-user-decisions/<decision_id>.json`

Written when automatic control must stop. Multiple decisions may be open at once, so records are stored as one file per decision instead of one global object that can be overwritten.

```json
{
  "decision_id": "user-decision-20260709-0001",
  "status": "open",
  "opened_at": "ISO-8601",
  "reason": "retry_ceiling_exceeded | auditor_stop | unsafe_secret | unsupported_state | service_unrecoverable",
  "failure_key": "dashboard_visibility:ai-infra-expansion-continuation-20260708:loop-dashboard-freshness:timeout",
  "summary": "string",
  "required_user_decision": "string",
  "attempts": [],
  "affected_runs": []
}
```

## Control Policy

### Run Discovery

Supervisor scans:

- `.codex/loop-runs/*/run.json`
- `.worktrees/*/.codex/loop-runs/*/run.json`

It ignores malformed run JSON only after recording an `invalid_run_json` event.

### Action Matrix

| Policy | Phase | Supervisor action |
|---|---|---|
| `autonomous_knowledge` | active phases | call auto-resume or orchestrator resume if stale beyond threshold |
| `autonomous_knowledge` | `stopped_blocked` with known mechanical `next_action` | call auto-resume |
| `autonomous_knowledge` | `audit_blocked` | call auto-resume / audit remediation |
| `autonomous_knowledge` | `stopped_budget` | check global stop conditions, then create continuation or stop |
| `autonomous_knowledge` | `stopped_no_action` | do not continue unless new actionable gap appears |
| `demand_development` | active phases | recover stale/interrupted run |
| `demand_development` | `audit_blocked` | call audit remediation |
| `demand_development` | `passed_waiting_human_merge` | request/await human confirmation; do not merge automatically |
| any | unsupported phase | record user decision requirement |

### Global Stop Conditions for Autonomous Continuation

Supervisor must not create a continuation if any condition is true:

- Auditor verdict is `stop`.
- Any relevant `needs-user-decisions/*.json` record is open.
- Same `failure_key` has reached three consecutive failures.
- No actionable gap exists and the current run has `stopped_no_action`.
- Remaining gaps require `needs_auth`, `needs_seed_url`, or `needs_human_judgement`.
- Git has unclassified dirty paths outside the active task scope.
- Service freshness cannot be restored after three attempts.
- A secret/token/cookie appears in candidate changed paths or logs.

### Automatic Service Restart

Supervisor may restart known tmux sessions only:

- `personal-wiki-crawler-backend`
- `personal-wiki-crawler-frontend`
- `loop-dashboard`
- `loop-auto-resume`

Restart commands must be generated from a repo-local allowlist. No arbitrary command strings from run artifacts may be executed.

After restart, Supervisor must verify:

- endpoint reachable;
- expected project root;
- running git version matches expected `HEAD` or documented worktree;
- crawler data/search/wiki/frontend freshness if relevant.

## Dashboard Design Contract

Supervisor is rendered as a global project section, not a task run. The task run list remains only for loop tasks.

Visible sections:

1. Global Agent: Loop Supervisor
2. Summary metrics
3. Control flow
4. Service keepalive
5. Recent global decisions
6. Failure escalation
7. Auditor interaction
8. Configuration
9. Task run list
10. Task run detail

If a field has no data, the UI must display `暂无数据`, `未启用`, or `不可用`, not a fake success state.

## Mock Traceability Matrix

| Mock display | Data field | Producer | Backend/API | Frontend | Tests |
|---|---|---|---|---|---|
| `Supervisor 在线` | `supervisor-state.status`, heartbeat age | Supervisor | `/api/supervisor` | global supervisor header | backend state test, browser evaluator |
| `最近同步` | `supervisor-state.last_tick_at` | Supervisor | `/api/supervisor` | top global section | backend parse test |
| `在线服务 4/4` | `service_summary` | Supervisor | `/api/supervisor` | metrics | service fixture test |
| service rows | `service-health.json` `services[]` | Supervisor | `/api/supervisor/services` | service keepalive list | backend service health tests |
| runtime metadata | `.codex/service-runtime/<service>.json` | service launcher / Supervisor restart | `/api/supervisor/services` | version freshness chip | pid/cwd/port/git-head tests |
| running version latest | `running_version.matches_expected` | Supervisor | `/api/supervisor/services` | service row chip | stale-version unit test |
| data freshness pass | `freshness-targets.jsonl` + `data_freshness.status` | Supervisor | `/api/supervisor/services` | metric + service row | crawler freshness tests |
| continuation candidate count | `run_summary.continuation_candidates` | Supervisor | `/api/supervisor` | metrics | stopped_budget classification test |
| continuation plan | `continuation-plans.jsonl` with `idempotency_key` | Supervisor | `/api/supervisor/decisions` | continuation candidate detail | continuation idempotency tests |
| failed recovery count | latest `recovery-attempts.jsonl` grouped by `failure_key` | Supervisor | `/api/supervisor/recovery` | failure escalation list | retry ceiling tests |
| control flow | derived from latest tick phases | Supervisor | `/api/supervisor` | control flow cards | browser evaluator |
| recent decisions | `run-decisions.jsonl` | Supervisor | `/api/supervisor/decisions` | decision log | decision parsing test |
| Auditor conclusion | latest audit report summary | Auditor, consumed by Supervisor | `/api/supervisor/auditor` | auditor interaction | auditor consumption tests |
| next audit cadence | run policy/audit cadence state | Orchestrator/Supervisor | `/api/supervisor/auditor` | auditor interaction | cadence fixture test |
| user decision required | `needs-user-decisions/*.json` | Supervisor | `/api/supervisor/decision-required` | top chip + tab | retry ceiling browser evaluator |
| task run list excludes Supervisor | run list from loop runs only | Dashboard store | existing `/api/runs` | left task list | browser evaluator |
| task run detail | existing run detail | Dashboard store | existing `/api/runs/<id>` | right detail | existing dashboard tests |

## Testing Plan

### Unit Tests

Add tests for:

- run discovery across root and worktrees;
- malformed run JSON recording;
- phase classification for `stopped_budget`, `stopped_blocked`, `audit_blocked`, active phases, and human merge gates;
- retry counter grouping by `run_id + failure_key`;
- retry ceiling writes `needs-user-decisions/<decision_id>.json`;
- service health success and failure states;
- service runtime metadata validation for pid/cwd/port/git head;
- stale version detection;
- target-specific crawler data freshness pass/fail;
- restart allowlist rejects arbitrary sessions;
- autonomous continuation plan creation and idempotency;
- demand development human gate is not auto-continued;
- Auditor `stop`, `must_fix`, `refocus`, and `continue` consumption;
- Supervisor artifact schema validation.

### Dashboard Backend Tests

Add tests for:

- `/api/supervisor`;
- `/api/supervisor/services`;
- `/api/supervisor/decisions`;
- `/api/supervisor/recovery`;
- `/api/supervisor/decision-required`;
- task run list excludes Supervisor artifacts;
- missing Supervisor artifacts return honest unavailable states.

### Frontend / Browser Evaluator

Browser evaluator must simulate a user and verify:

- Supervisor appears in a global section, not the task run list;
- service health rows are visible and sourced from fixture artifacts;
- stale version and unavailable version states are visible when fixture runtime metadata is stale or missing;
- stopped_budget autonomous run appears as a task run and as a continuation candidate in Supervisor metrics;
- duplicate continuation plans do not create duplicate Dashboard candidates;
- failure escalation shows 0/3, 1/3, and needs-user-decision states from fixtures;
- Auditor interaction displays `continue`, `must_fix`, and `stop` fixture states correctly;
- task detail remains focused on Planner/Generator/Evaluator/Auditor/logs/artifacts for the selected run;
- no mock-only success text appears when fixture data is missing.

### E2E Runtime Verification

For the real project:

- Start or verify crawler backend, crawler frontend, Loop Dashboard, and Supervisor watch mode.
- Stop one isolated fake tmux service and verify Supervisor restarts it. Real crawler/dashboard services are only checked read-only during tests unless the user explicitly approves destructive service interruption.
- Seed a `stopped_budget` autonomous fixture and verify Supervisor classifies it as a continuation candidate.
- Seed a repeated failure fixture and verify the third failure creates `needs-user-decisions/<decision_id>.json`.
- Verify Dashboard shows the global Supervisor section and still shows task runs separately.

## Non-Goals

- Supervisor does not replace Planner, Generator, Evaluator, or Auditor.
- Supervisor does not decide content quality or domain value; Auditor and evaluator do that.
- Supervisor does not auto-merge demand-development work into `main`.
- Supervisor does not execute arbitrary commands from artifacts.
- Supervisor does not expose unauthenticated network control beyond the current trusted local environment.
- Supervisor does not hide missing data behind green status chips.

## Implementation Notes

- Keep Supervisor modules small. Do not further expand the large orchestrator file unless a narrow public hook is needed.
- Prefer append-only JSONL for decisions and attempts.
- Treat git command failures as explicit errors, never as a clean state.
- Runtime artifacts under `.codex/supervisor/` should not be committed by default.
- Design and mock artifacts under `docs/superpowers/` can be committed.
- Any code change affecting Dashboard or Supervisor must include browser-level evaluator coverage because the UI is intended for human operators.

## Open Questions

No open product questions remain for the first implementation plan. The first build should implement the mock-visible contract above with fixture-backed tests before enabling long-running watch mode on real services.

## 2026-07-10 Runtime Hardening Amendment

This amendment is binding for `loop-runtime-continuation-hardening-01` and resolves six production gaps found while continuing the AI infra autonomous loop.

### Execution Ownership

- `loop-auto-resume` is the only component allowed to execute an existing actionable run through Planner, Generator, Evaluator, audit remediation, cleanup, commit, and push.
- Supervisor must not call `resume_once()` or run a Planner/Generator/Evaluator driver. It observes existing runs and exclusively owns idempotent creation of a new continuation for eligible `autonomous_knowledge` `stopped_budget` runs.
- Every run execution must hold a non-blocking per-run lock under `.codex/loop-locks/<run-id>.lock`. A second executor records `locked_by_other_executor` and skips the run; it must not run concurrently.
- The lock is enforced by the orchestrator execution entrypoints and by mutating phase CLI commands, so direct CLI use cannot race loop-auto-resume. Lock files are harness runtime artifacts and are excluded from orchestrator and Auditor dirty-path findings.
- Supervisor continuation creation must be active outside `--dry-run`, atomic, and idempotent. A `created` plan must point to a real confirmed preflight `run.json`; `planned` is only valid in dry-run mode.
- Continuation planning holds the source-run lock; creation also holds the target-run lock. A new target is first written as non-actionable `preflight`, receives all inheritance fields, and only then becomes `planning`. An interrupted preflight with zero attempts is recoverable on the next Supervisor tick.

### Continuation State Inheritance

- A continuation persists `previous_run_id`, `parent_task_counter`, and `semantic_parent_task_next`. For the current source run, parent-17 is complete and the next semantic task is parent-18.
- Auditor cadence is inherited across run boundaries. The continuation stores `completed_since_last_audit`; the current source run carries one completion after the parent-16 audit. One new completed parent therefore triggers the two-parent audit.
- The run-local task number may restart at one, but prompts, gap proofs, coverage state, Dashboard summaries, and audit cadence must use the inherited semantic parent boundary.
- Each completed ordinary autonomous task advances `parent_task_counter` and `semantic_parent_task_next`. Audit-remediation tasks use a separate completed-remediation ledger: they consume invocation budget but do not advance semantic parent numbering or the two-parent audit cadence.

### Service And Data Freshness

- `service_summary.online` counts endpoint reachability and required tmux presence. A reachable service remains online even when its version is stale or unavailable.
- Version freshness is a separate state based on a service-specific code/config fingerprint, not repository `HEAD`. Wiki-only commits must not mark crawler or Dashboard code stale.
- Endpoint/tmux reachability does not change code freshness. An offline service may be `不可达` while its recorded code fingerprint remains `最新`.
- Runtime metadata records both startup Git SHA for provenance and the service fingerprint used for freshness comparison.
- After a successful autonomous main-branch push and remote-SHA verification, the orchestrator publishes one target-specific record to `.codex/supervisor/freshness-targets.jsonl`. Evidence must match the current run ID/task ID, captured timestamp, orchestrator provenance path, and actual SHA-256. Repeated publication for the same target/commit is idempotent.

### Decisions, Push, And Dashboard

- `supervisor-state.last_decision` is selected from current actionable decisions for the root project. Historical worktree and terminal observations stay in decision history but cannot become the global headline.
- When no open decision exists, the Dashboard headline and control flow display `暂无待处理决策`; historical records remain visible in the decision log with run ID and repo root.
- Supervisor archives an open run-scoped decision when all affected runs no longer classify as needing user input. Project-scoped decisions with no affected run are never auto-archived.
- Autonomous commits on `main` automatically run `git push origin main`. The orchestrator writes `push-result.json` with remote, branch, commit, status, and error.
- A missing `origin`, push failure, timeout, or remote SHA mismatch on `main` stops at retryable `stopped_blocked / retry_autonomous_push`; auto-resume retries without recreating the commit or rerunning Generator. Non-main fixture repositories record `skipped` because automatic push is restricted to `main`.

### Acceptance Additions

- Unit tests must prove execution lock exclusion, no Supervisor call into auto-resume, real continuation creation, parent-18 inheritance, carried Auditor cadence, online/version separation, service-fingerprint behavior, freshness publication idempotency, current-decision selection, push success, and retry after push failure.
- Browser evaluation must prove `在线服务` is reachability-based, version freshness is separate, no stale historical decision is presented as current, and zero open decisions is explicit.
- Runtime acceptance requires the real crawler backend/frontend, Loop Dashboard, loop-auto-resume, and active Supervisor online, followed by four consecutively completed AI infra semantic parent tasks with the expected two-parent Auditor boundary and no manual phase advancement.
