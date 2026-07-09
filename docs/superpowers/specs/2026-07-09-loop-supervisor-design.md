# Loop Supervisor Design

Date: 2026-07-09

## Goal

Implement `loop-supervisor-01`: a long-running project-level control plane that keeps the local loop system operating without repeated manual intervention. The Supervisor owns runtime control, not task quality judgment. It keeps Crawler Workbench backend/frontend, Loop Dashboard, and loop recovery online; monitors loop run state; automatically resumes or continues eligible runs; escalates repeated failures; and records operator-readable evidence for every decision.

The current mock is:

- `docs/superpowers/mockups/2026-07-09-loop-supervisor-dashboard-mock.html`

The mock is a contract, not decorative art. Every visible claim in the mock must either be implemented from real Supervisor/Dashboard data or shown as explicitly unavailable. The implementation must not hard-code successful states in the frontend.

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
- `needs-user-decision.json`
- `continuation-plans.jsonl`

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

### `service-health.json`

Required fields per service:

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
    "evidence": "string"
  },
  "data_freshness": {
    "status": "pass | fail | not_applicable",
    "checks": ["search-api", "wiki-api", "frontend-visible"]
  },
  "last_checked_at": "ISO-8601",
  "last_restart_at": "ISO-8601 or empty",
  "last_error": ""
}
```

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

### `recovery-attempts.jsonl`

One JSON object per restart/resume/recovery attempt:

```json
{
  "attempt_id": "recovery-20260709-0001",
  "failure_key": "dashboard_freshness_timeout",
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

### `needs-user-decision.json`

Written when automatic control must stop:

```json
{
  "status": "open",
  "opened_at": "ISO-8601",
  "reason": "retry_ceiling_exceeded | auditor_stop | unsafe_secret | unsupported_state | service_unrecoverable",
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
- `needs-user-decision.json` is open.
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
| service rows | `service-health.json.services[]` | Supervisor | `/api/supervisor/services` | service keepalive list | backend service health tests |
| running version latest | `running_version.matches_expected` | Supervisor | `/api/supervisor/services` | service row chip | stale-version unit test |
| data freshness pass | `data_freshness.status` | Supervisor | `/api/supervisor/services` | metric + service row | crawler freshness tests |
| continuation candidate count | `run_summary.continuation_candidates` | Supervisor | `/api/supervisor` | metrics | stopped_budget classification test |
| failed recovery count | latest `recovery-attempts.jsonl` grouped by `failure_key` | Supervisor | `/api/supervisor/recovery` | failure escalation list | retry ceiling tests |
| control flow | derived from latest tick phases | Supervisor | `/api/supervisor` | control flow cards | browser evaluator |
| recent decisions | `run-decisions.jsonl` | Supervisor | `/api/supervisor/decisions` | decision log | decision parsing test |
| Auditor conclusion | latest audit report summary | Auditor, consumed by Supervisor | `/api/supervisor/auditor` | auditor interaction | auditor consumption tests |
| next audit cadence | run policy/audit cadence state | Orchestrator/Supervisor | `/api/supervisor/auditor` | auditor interaction | cadence fixture test |
| user decision required | `needs-user-decision.json` | Supervisor | `/api/supervisor/decision-required` | top chip + tab | retry ceiling browser evaluator |
| task run list excludes Supervisor | run list from loop runs only | Dashboard store | existing `/api/runs` | left task list | browser evaluator |
| task run detail | existing run detail | Dashboard store | existing `/api/runs/<id>` | right detail | existing dashboard tests |

## Testing Plan

### Unit Tests

Add tests for:

- run discovery across root and worktrees;
- malformed run JSON recording;
- phase classification for `stopped_budget`, `stopped_blocked`, `audit_blocked`, active phases, and human merge gates;
- retry counter grouping by `run_id + failure_key`;
- retry ceiling writes `needs-user-decision.json`;
- service health success and failure states;
- stale version detection;
- crawler data freshness pass/fail;
- restart allowlist rejects arbitrary sessions;
- autonomous continuation plan creation;
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
- stopped_budget autonomous run appears as a task run and as a continuation candidate in Supervisor metrics;
- failure escalation shows 0/3, 1/3, and needs-user-decision states from fixtures;
- Auditor interaction displays `continue`, `must_fix`, and `stop` fixture states correctly;
- task detail remains focused on Planner/Generator/Evaluator/Auditor/logs/artifacts for the selected run;
- no mock-only success text appears when fixture data is missing.

### E2E Runtime Verification

For the real project:

- Start or verify crawler backend, crawler frontend, Loop Dashboard, and Supervisor watch mode.
- Stop one allowed tmux service in an isolated test and verify Supervisor restarts it.
- Seed a `stopped_budget` autonomous fixture and verify Supervisor classifies it as a continuation candidate.
- Seed a repeated failure fixture and verify the third failure creates `needs-user-decision.json`.
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
