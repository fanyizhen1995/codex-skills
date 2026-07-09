# Loop Supervisor 01 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `loop-supervisor-01`, a real project-level control plane that keeps crawler services, Loop Dashboard, auto-resume, and eligible loop runs moving without repeated manual intervention.

**Architecture:** Add a focused Supervisor runtime under `scripts/harness_loop_supervisor*.py` that writes `.codex/supervisor/*` artifacts and consumes the existing orchestrator/auto-resume primitives instead of duplicating PGE logic. Extend Loop Dashboard backend APIs and frontend UI to render a global Supervisor section from those real artifacts, outside the task run list. Add fixture-backed unit/API/browser evaluator coverage that proves the mock-visible contract and rejects display-only green states.

**Tech Stack:** Python 3 scripts and pytest/unittest, FastAPI TestClient, existing vanilla JS/CSS Loop Dashboard frontend, Playwright through `scripts/loop_dashboard_evaluator.py`, tmux CLI for allowlisted service checks.

## Global Constraints

- Use `docs/superpowers/specs/2026-07-09-loop-supervisor-design.md` as the binding spec.
- Use `docs/superpowers/mockups/2026-07-09-loop-supervisor-dashboard-mock.html` as the frontend acceptance contract.
- Supervisor is a global control-plane role and must not appear as an item in `/api/runs` or the task run list.
- This task is incomplete unless mock-visible Supervisor functions have production data, backend API exposure, frontend rendering, and automated verification.
- Missing fields must render as `暂无数据`, `未启用`, or `不可用`; the frontend must not hard-code successful states.
- Supervisor writes runtime artifacts under `.codex/supervisor/`; these runtime artifacts are not committed.
- Service runtime metadata is read from `.codex/service-runtime/<service>.json`.
- Service restart may only target tmux sessions `personal-wiki-crawler-backend`, `personal-wiki-crawler-frontend`, `loop-dashboard`, and `loop-auto-resume`.
- Restart commands must come from a repo-local allowlist, not from run artifacts.
- Retry ceiling is three consecutive failures for the same `(run_id or project, failure_key)`.
- `failure_key` format is `<category>:<scope_id>:<subject_id>:<normalized_error_class>`.
- `autonomous_knowledge` `stopped_budget` runs may create idempotent continuation plans only when global stop conditions are not met.
- `demand_development` human merge gates must not be auto-merged or auto-continued.
- Auditor verdicts are inputs; Supervisor must not invent process-quality conclusions.
- Git command failures must be explicit errors, never treated as a clean tree.
- Any frontend change must keep the mock page and implementation behavior aligned, and evaluator coverage must verify that alignment.
- Keep Crawler Workbench backend/frontend, Loop Dashboard, and loop-auto-resume online and remote-accessible during and after the task.

---

## File Structure

- Create `scripts/harness_loop_supervisor_state.py`: schema helpers, JSON/JSONL IO, failure-key normalization, event records, retry counter logic, and user-decision record creation.
- Create `scripts/harness_loop_supervisor.py`: CLI entrypoint, one-shot/watch tick loop, service health checks, run classification, continuation planning, auto-resume/restart orchestration, and artifact writing.
- Create `scripts/tests/test_harness_loop_supervisor_state.py`: state/schema/retry/unit tests.
- Create `scripts/tests/test_harness_loop_supervisor.py`: service health, run classification, continuation, restart allowlist, and CLI tests using temp repos and fake tmux/http services.
- Modify `apps/loop_dashboard/backend/loop_dashboard/store.py`: read `.codex/supervisor/*`, expose parsed Supervisor state/services/decisions/recovery/user decisions with redaction and honest unavailable defaults.
- Modify `apps/loop_dashboard/backend/loop_dashboard/main.py`: add `/api/supervisor`, `/api/supervisor/services`, `/api/supervisor/decisions`, `/api/supervisor/recovery`, `/api/supervisor/decision-required`, and `/api/supervisor/auditor`.
- Modify `apps/loop_dashboard/backend/tests/test_api.py` and `apps/loop_dashboard/backend/tests/test_store.py`: backend API and parsing tests.
- Modify `apps/loop_dashboard/frontend/index.html`, `apps/loop_dashboard/frontend/app.js`, and `apps/loop_dashboard/frontend/styles.css`: global Supervisor panel, tabs/cards, Chinese copy, and unavailable states matching the mock.
- Modify `scripts/loop_dashboard_evaluator.py`: add `loop-supervisor-01` browser scenario fixtures and assertions.
- Create `docs/harness/evaluator-scenarios/loop-supervisor-01.json`: Step4 evaluator scenario metadata.
- Modify `tasks.json` and `progress.md`: record `loop-supervisor-01` and completion evidence.
- Do not modify `docs/superpowers/mockups/2026-07-09-loop-supervisor-dashboard-mock.html` unless implementation discovers an impossible field; if changed, update this plan's mock traceability by commit.

---

### Task 1: Supervisor State Contracts

**Files:**
- Create: `scripts/harness_loop_supervisor_state.py`
- Create: `scripts/tests/test_harness_loop_supervisor_state.py`

**Interfaces:**
- Produces:
  - `utc_now_iso() -> str`
  - `supervisor_dir(project_root: Path) -> Path`
  - `append_jsonl(path: Path, payload: Mapping[str, Any]) -> None`
  - `read_jsonl(path: Path) -> list[dict[str, Any]]`
  - `normalize_error_class(value: str) -> str`
  - `make_failure_key(category: str, scope_id: str, subject_id: str, error_class: str) -> str`
  - `record_recovery_attempt(project_root: Path, attempt: RecoveryAttemptInput) -> dict[str, Any]`
  - `open_user_decision(project_root: Path, *, reason: str, failure_key: str, summary: str, required_user_decision: str, affected_runs: list[str], attempts: list[dict[str, Any]]) -> dict[str, Any]`
  - `build_supervisor_state(project_root: Path, *, mode: str, service_health: dict[str, Any], run_summary: dict[str, Any], failure_summary: dict[str, Any], last_decision: dict[str, Any] | None, watch_interval_seconds: int) -> dict[str, Any]`
- Consumes: standard library only.

- [ ] **Step 1: Write failing state tests**

Add tests that assert:

```python
def test_failure_key_normalizes_and_rejects_unknown_category():
    assert make_failure_key("service_down", "Project Root", "Crawler Backend", "Connection refused!") == (
        "service_down:project-root:crawler-backend:connection-refused"
    )
    with pytest.raises(ValueError):
        make_failure_key("other", "project", "service", "error")

def test_recovery_attempt_counter_opens_user_decision_on_third_failure(tmp_path):
    key = make_failure_key("service_down", "project", "crawler-backend", "connection_refused")
    for index in range(3):
        attempt = record_recovery_attempt(tmp_path, RecoveryAttemptInput(
            failure_key=key,
            run_id="",
            action="restart_service",
            status="fail",
            summary=f"fail {index}",
            evidence_paths=[],
        ))
    assert attempt["consecutive_failure_count"] == 3
    decisions = sorted((tmp_path / ".codex" / "supervisor" / "needs-user-decisions").glob("*.json"))
    assert len(decisions) == 1
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_state.py`

Expected: FAIL because `scripts.harness_loop_supervisor_state` does not exist.

- [ ] **Step 3: Implement state helpers**

Implement dataclasses and helpers with strict allowed categories:

```python
ALLOWED_FAILURE_CATEGORIES = {
    "service_down", "stale_version", "data_freshness", "dashboard_visibility",
    "required_evidence", "dirty_path", "audit_blocked", "auditor_stop",
    "continuation_duplicate", "unsupported_state", "unsafe_secret",
}
MAX_CONSECUTIVE_FAILURES = 3
```

Use append-only JSONL for attempts and decisions. When a failed attempt reaches `MAX_CONSECUTIVE_FAILURES`, write exactly one open user-decision file for that `failure_key` unless an open one already exists.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_state.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add scripts/harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor_state.py
git commit -m "feat(harness): add supervisor state contracts"
```

---

### Task 2: Supervisor Runtime Engine

**Files:**
- Create: `scripts/harness_loop_supervisor.py`
- Create/modify: `scripts/tests/test_harness_loop_supervisor.py`
- Modify: `scripts/harness_loop_supervisor_state.py` if Task 2 needs focused schema helpers.

**Interfaces:**
- Consumes Task 1 helpers.
- Produces:
  - `SupervisorConfig(project_root: Path, mode: str = "once", watch_interval_seconds: int = 30, include_worktrees: bool = True, dry_run: bool = False, restart_services: bool = False, create_continuations: bool = True)`
  - `run_supervisor_once(config: SupervisorConfig) -> dict[str, Any]`
  - `discover_run_records(project_root: Path, include_worktrees: bool = True) -> list[RunRecord]`
  - `classify_run(run_record: RunRecord, auditor_summary: dict[str, Any] | None = None) -> dict[str, Any]`
  - `check_service_health(config: SupervisorConfig, service: ServiceConfig) -> dict[str, Any]`
  - `plan_continuation(config: SupervisorConfig, run_record: RunRecord) -> dict[str, Any]`

- [ ] **Step 1: Write failing runtime tests**

Cover these behaviors:

```python
def test_run_supervisor_once_writes_required_artifacts(tmp_path):
    seed_service_runtime(tmp_path, "loop-dashboard", port=8766, git_head="abc123")
    seed_stopped_budget_autonomous_run(tmp_path, "ai-infra-r10")
    result = run_supervisor_once(SupervisorConfig(project_root=tmp_path, dry_run=True))
    assert result["status"] in {"healthy", "degraded"}
    assert (tmp_path / ".codex" / "supervisor" / "supervisor-state.json").exists()
    assert (tmp_path / ".codex" / "supervisor" / "service-health.json").exists()
    assert (tmp_path / ".codex" / "supervisor" / "run-decisions.jsonl").exists()

def test_stopped_budget_autonomous_plan_is_idempotent(tmp_path):
    seed_stopped_budget_autonomous_run(tmp_path, "ai-infra-r10", parent_counter=14)
    config = SupervisorConfig(project_root=tmp_path, dry_run=True)
    first = run_supervisor_once(config)
    second = run_supervisor_once(config)
    plans = read_jsonl(tmp_path / ".codex" / "supervisor" / "continuation-plans.jsonl")
    assert len({plan["idempotency_key"] for plan in plans}) == 1
    assert second["run_summary"]["continuation_candidates"] == 1

def test_restart_allowlist_rejects_unknown_session(tmp_path):
    with pytest.raises(ValueError):
        restart_service(SupervisorConfig(project_root=tmp_path), "rm-random-session")
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor.py`

Expected: FAIL because runtime module/functions do not exist.

- [ ] **Step 3: Implement runtime engine**

Implement a one-shot tick that:

- writes `events.jsonl`;
- reads service runtime metadata from `.codex/service-runtime`;
- marks version freshness `不可用`/`matches_expected=false` when metadata is missing/stale;
- checks HTTP endpoints with a short timeout;
- checks tmux sessions via `tmux has-session -t <session>`;
- classifies runs from root and `.worktrees/*/.codex/loop-runs`;
- calls `scripts.harness_loop_auto_resume.resume_once` only for actionable `audit_blocked`, supported `stopped_blocked`, and active autonomous phases;
- creates idempotent continuation plans for eligible `autonomous_knowledge` `stopped_budget` runs without duplicating plans;
- refuses demand-development human merge continuation;
- records explicit user decisions for unsupported states, auditor stop, retry ceiling, unsafe-secret signal, or unrecoverable service state.

Do not create real continuation runs in dry-run mode. For this task, `plan_continuation` may write a `planned` continuation plan; actual orchestrator continuation creation can be a later explicit action, but duplicate planning must already be impossible.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add scripts/harness_loop_supervisor.py scripts/harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor_state.py
git commit -m "feat(harness): add loop supervisor runtime"
```

---

### Task 3: Dashboard Backend Supervisor APIs

**Files:**
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Modify: `apps/loop_dashboard/backend/loop_dashboard/main.py`
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`
- Modify: `apps/loop_dashboard/backend/tests/test_api.py`

**Interfaces:**
- Consumes `.codex/supervisor/supervisor-state.json`, `service-health.json`, `run-decisions.jsonl`, `recovery-attempts.jsonl`, `continuation-plans.jsonl`, `needs-user-decisions/*.json`, and latest audit summaries.
- Produces:
  - `LoopDashboardStore.supervisor_summary() -> dict[str, Any]`
  - `LoopDashboardStore.supervisor_services() -> dict[str, Any]`
  - `LoopDashboardStore.supervisor_decisions() -> dict[str, Any]`
  - `LoopDashboardStore.supervisor_recovery() -> dict[str, Any]`
  - `LoopDashboardStore.supervisor_decision_required() -> dict[str, Any]`
  - `LoopDashboardStore.supervisor_auditor() -> dict[str, Any]`

- [ ] **Step 1: Write failing API/store tests**

Add fixture-backed tests:

```python
def test_supervisor_api_returns_honest_missing_state(tmp_path):
    client = TestClient(create_app(project_root=tmp_path))
    payload = client.get("/api/supervisor").json()
    assert payload["status"] == "unavailable"
    assert payload["state"]["status_label"] == "暂无数据"

def test_supervisor_api_reads_services_decisions_recovery_and_user_decisions(tmp_path):
    seed_supervisor_artifacts(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))
    assert client.get("/api/supervisor").json()["status"] == "healthy"
    assert client.get("/api/supervisor/services").json()["services"][0]["service"] == "crawler-backend"
    assert client.get("/api/supervisor/decisions").json()["continuation_plans"][0]["idempotency_key"]
    assert client.get("/api/supervisor/recovery").json()["attempts"][0]["consecutive_failure_count"] == 1
    assert client.get("/api/supervisor/decision-required").json()["open_count"] == 1

def test_run_list_excludes_supervisor_global_artifacts(tmp_path):
    seed_supervisor_artifacts(tmp_path)
    runs = TestClient(create_app(project_root=tmp_path)).get("/api/runs").json()
    assert all(run["run_id"] != "loop-supervisor" for run in runs)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_api.py apps/loop_dashboard/backend/tests/test_store.py`

Expected: FAIL on missing Supervisor API methods/routes.

- [ ] **Step 3: Implement backend parsing and routes**

Parse artifacts defensively:

- malformed JSON returns `status=invalid_artifact` with redacted diagnostics;
- missing artifacts return `unavailable` and Chinese unavailable labels;
- JSONL readers limit output to recent entries but include counts;
- open user decisions are sorted by `opened_at`;
- no Supervisor artifact is mixed into run list.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_api.py apps/loop_dashboard/backend/tests/test_store.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add apps/loop_dashboard/backend/loop_dashboard/store.py apps/loop_dashboard/backend/loop_dashboard/main.py apps/loop_dashboard/backend/tests/test_api.py apps/loop_dashboard/backend/tests/test_store.py
git commit -m "feat(dashboard): expose supervisor APIs"
```

---

### Task 4: Dashboard Frontend Global Supervisor Panel

**Files:**
- Modify: `apps/loop_dashboard/frontend/index.html`
- Modify: `apps/loop_dashboard/frontend/app.js`
- Modify: `apps/loop_dashboard/frontend/styles.css`

**Interfaces:**
- Consumes Supervisor backend APIs from Task 3.
- Produces visible global UI matching the mock sections: global agent header, summary metrics, control flow, service keepalive, recent decisions, failure escalation, Auditor interaction, configuration, and unchanged task run detail.

- [ ] **Step 1: Write failing frontend/unit checks**

If current frontend test harness supports browserless checks, add assertions to existing frontend tests. If it does not, write the frontend-facing checks in Task 5's evaluator first and mark this task RED by running that evaluator against the old UI.

Minimum expected failure before implementation:

```text
Loop Dashboard page does not contain "全局 Agent：Loop Supervisor"
Loop Dashboard page does not show "服务保活"
Loop Dashboard task run list includes only task runs and no Supervisor run
```

- [ ] **Step 2: Run RED command**

Run: `node --check apps/loop_dashboard/frontend/app.js`

Then run the Task 5 evaluator after its RED tests are added, expecting frontend assertions to fail before this implementation.

- [ ] **Step 3: Implement frontend**

Add a global Supervisor section above the existing two-column task dashboard. The frontend must:

- fetch `/api/supervisor`, `/api/supervisor/services`, `/api/supervisor/decisions`, `/api/supervisor/recovery`, `/api/supervisor/decision-required`, and `/api/supervisor/auditor`;
- render Chinese labels from real fields;
- render unavailable states for missing artifacts;
- show user-decision required as a warning chip;
- show service rows with reachable/tmux/version/freshness evidence;
- show continuation `idempotency_key` and duplicate prevention text only when backend data exists;
- show Auditor input/verdict without claiming Supervisor performed quality judgment;
- leave the existing task run list and detail behavior intact.

- [ ] **Step 4: Run frontend checks**

Run:

```bash
node --check apps/loop_dashboard/frontend/app.js
python3 -m pytest -q scripts/tests/test_harness_loop_supervisor.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add apps/loop_dashboard/frontend/index.html apps/loop_dashboard/frontend/app.js apps/loop_dashboard/frontend/styles.css
git commit -m "feat(dashboard): render global loop supervisor"
```

---

### Task 5: Browser Evaluator and Scenario Contract

**Files:**
- Modify: `scripts/loop_dashboard_evaluator.py`
- Create: `docs/harness/evaluator-scenarios/loop-supervisor-01.json`
- Add test if useful: `scripts/tests/test_loop_dashboard_evaluator.py`

**Interfaces:**
- Consumes frontend/backend changes from Tasks 3-4 and Supervisor fixtures.
- Produces evaluator scenario `loop-supervisor-01` and automated browser evidence under `.codex/loop-dashboard-eval/loop-supervisor-01`.

- [ ] **Step 1: Write failing evaluator scenario**

Add a scenario path that seeds:

- valid Supervisor state and service health;
- missing runtime metadata for one service;
- stale runtime metadata for one service;
- a stopped-budget autonomous run and duplicate continuation fixture;
- recovery attempts at 0/3, 1/3, and 3/3 with open user decision;
- Auditor input states `continue`, `must_fix`, and `stop`;
- no synthetic `loop-supervisor` run in `.codex/loop-runs`.

The browser assertions must fail on the old UI and pass only when the global Supervisor panel renders real fixture data.

- [ ] **Step 2: Run evaluator RED**

Run: `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-01 --scenario loop-supervisor-01`

Expected: FAIL before Task 4 implementation, or FAIL on missing evaluator path before this task is implemented.

- [ ] **Step 3: Implement evaluator fixtures and browser assertions**

Implement scenario-specific helpers without hard-coding success in production UI. Assertions must check:

- `全局 Agent：Loop Supervisor` is visible;
- task run list does not contain Supervisor;
- service rows show healthy, stale, and unavailable version states;
- continuation candidate and `idempotency_key` appear once;
- retry ceiling creates `需要用户决策`;
- Auditor section distinguishes control input from quality judgment;
- removing Supervisor artifacts changes the UI to `暂无数据`/`不可用`, not green success.

- [ ] **Step 4: Run evaluator GREEN**

Run: `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-01 --scenario loop-supervisor-01`

Expected: PASS and writes `result.json`/`summary.md`.

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add scripts/loop_dashboard_evaluator.py docs/harness/evaluator-scenarios/loop-supervisor-01.json scripts/tests/test_loop_dashboard_evaluator.py
git commit -m "test(dashboard): add supervisor browser evaluator"
```

If `scripts/tests/test_loop_dashboard_evaluator.py` is not needed, omit it from `git add`.

---

### Task 6: Real Service Runtime Metadata and Watch Mode

**Files:**
- Modify: `scripts/harness_loop_supervisor.py`
- Modify: `scripts/tests/test_harness_loop_supervisor.py`
- Modify: `docs/harness/planner-generator-evaluator-loop.md` if commands or service metadata startup instructions change.

**Interfaces:**
- Consumes Task 2 CLI/runtime.
- Produces:
  - `python3 scripts/harness_loop_supervisor.py --project-root . --once`
  - `python3 scripts/harness_loop_supervisor.py --project-root . --watch --interval-seconds 30`
  - service runtime metadata writing/refresh command support.

- [ ] **Step 1: Write failing tests for watch/metadata behavior**

Tests must prove:

```python
def test_once_cli_writes_state_and_exits_zero(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/harness_loop_supervisor.py", "--project-root", str(tmp_path), "--once", "--dry-run"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert (tmp_path / ".codex" / "supervisor" / "supervisor-state.json").exists()

def test_watch_mode_can_stop_after_max_ticks(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/harness_loop_supervisor.py", "--project-root", str(tmp_path), "--watch", "--max-ticks", "1", "--interval-seconds", "1", "--dry-run"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q scripts/tests/test_harness_loop_supervisor.py`

Expected: FAIL on missing CLI/watch flags or metadata behavior.

- [ ] **Step 3: Implement CLI/watch support**

Add CLI flags:

- `--project-root`
- `--once`
- `--watch`
- `--interval-seconds`
- `--max-ticks`
- `--include-worktrees` / `--no-include-worktrees`
- `--dry-run`
- `--restart-services`
- `--no-create-continuations`

Watch mode must update `last_heartbeat_at` and `last_tick_at`. It must not mutate real services unless `--restart-services` is set. Tests must use fake service fixtures and must not kill real crawler/dashboard services.

- [ ] **Step 4: Run tests and docs check**

Run:

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor.py
python3 scripts/harness_loop_supervisor.py --project-root . --once --dry-run
```

Expected: PASS/exit 0 and `.codex/supervisor/supervisor-state.json` exists in the worktree runtime area.

- [ ] **Step 5: Commit Task 6**

Run:

```bash
git add scripts/harness_loop_supervisor.py scripts/tests/test_harness_loop_supervisor.py docs/harness/planner-generator-evaluator-loop.md
git commit -m "feat(harness): add supervisor watch mode"
```

---

### Task 7: Task Registry, Progress, and Service Deployment Check

**Files:**
- Modify: `tasks.json`
- Modify: `progress.md`
- Modify: `AGENTS.md` only if implementation discovers a missing durable operating rule.

**Interfaces:**
- Consumes all prior task outputs and verification evidence.
- Produces durable task tracking and operator instructions.

- [ ] **Step 1: Add failing task registry validation if missing**

Run before editing:

```bash
python3 -m json.tool tasks.json > /dev/null
```

Add `loop-supervisor-01` with all existing required fields and `requires_eval=true`. The `verify` field must include unit tests, backend tests, frontend/evaluator, and service health checks.

- [ ] **Step 2: Validate task registry**

Run: `python3 -m json.tool tasks.json > /dev/null`

Expected: PASS.

- [ ] **Step 3: Append progress entry**

Append a top entry to `progress.md` describing:

- implementation commits;
- test commands;
- evaluator evidence path;
- service status and URLs;
- whether Supervisor watch mode was started.

- [ ] **Step 4: Commit Task 7**

Run:

```bash
git add tasks.json progress.md AGENTS.md
git commit -m "docs(harness): record loop supervisor task"
```

If `AGENTS.md` was not changed, omit it from `git add`.

---

### Task 8: Final Verification, Review, Merge, and Push

**Files:**
- No new production files unless final review finds defects.

**Interfaces:**
- Consumes all implementation commits.
- Produces clean final branch, merged `main`, pushed `origin/main`, and live services.

- [ ] **Step 1: Run full relevant verification**

Run:

```bash
python3 -m pytest -q scripts/tests/test_harness_loop_supervisor_state.py scripts/tests/test_harness_loop_supervisor.py scripts/tests/test_harness_loop_auto_resume.py scripts/tests/test_harness_loop_contracts.py
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_api.py apps/loop_dashboard/backend/tests/test_store.py
node --check apps/loop_dashboard/frontend/app.js
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-supervisor-01 --scenario loop-supervisor-01
git diff --check
```

- [ ] **Step 2: Run final code review**

Use `superpowers:requesting-code-review` for a whole-branch review package. Fix any Critical/Important findings and rerun impacted tests.

- [ ] **Step 3: Verify live services remain online**

From `/home/fyz/codex-skills` on `main` after merge:

```bash
curl --noproxy '*' http://127.0.0.1:8765/api/health
curl --noproxy '*' -I http://127.0.0.1:5173/
curl --noproxy '*' http://127.0.0.1:8766/api/health
tmux has-session -t loop-auto-resume
tmux has-session -t loop-supervisor
```

If `loop-supervisor` is not running, start it in tmux with:

```bash
tmux new -d -s loop-supervisor 'cd /home/fyz/codex-skills && python3 scripts/harness_loop_supervisor.py --project-root /home/fyz/codex-skills --watch --interval-seconds 30'
```

- [ ] **Step 4: Merge and push**

Run:

```bash
git checkout main
git pull --ff-only origin main
git merge --ff-only loop-supervisor-01
git push origin main
```

If `--ff-only` fails because main moved, rebase or merge only after reviewing conflicts and protecting unrelated user changes.

- [ ] **Step 5: Final report**

Report:

- commit hashes;
- verification commands and pass/fail status;
- evaluator evidence path;
- live URLs and health checks;
- any residual risks or intentionally unavailable fields.

---

## Self-Review

- Spec coverage: The plan covers producer artifacts, retry ceiling, service/runtime metadata, continuation idempotency, Auditor consumption, dashboard APIs, frontend global section, evaluator scenario, real service checks, and task/progress records.
- Placeholder scan: No implementation step depends on TBD behavior. Each task has concrete file paths, functions, commands, and expected outcomes.
- Type consistency: Task 2 consumes Task 1 helpers by name; Task 3 consumes `.codex/supervisor/*`; Task 4 consumes Task 3 endpoints; Task 5 verifies the visible frontend contract; Task 8 ties the branch back to `main` and `origin`.
