# Loop Dashboard Auditor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make the real Loop Dashboard show Loop Auditor state, deterministic audit signals, direction control, audit findings, and project skill inventory, and prove this implementation loop is visible in the dashboard.

**Architecture:** Extend the existing read-only `apps/loop_dashboard` backend store so run detail payloads include `audit_summary` and `skill_inventory`. Render these sections in the current vanilla JS frontend without introducing a new framework. Keep all data sourced from repo/run artifacts: `.codex/loop-runs`, `audit-reports`, `deterministic-signals*.json`, `SKILL.md`, and existing run state.

**Tech Stack:** Python FastAPI backend, pytest, vanilla JavaScript frontend, existing Playwright-based `scripts/loop_dashboard_evaluator.py`.

## Global Constraints

- Work in `/home/fyz/codex-skills/.worktrees/loop-dashboard-auditor` on branch `loop-dashboard-auditor`.
- The implementation loop run id is `loop-dashboard-auditor-dev`; it must remain visible through the root dashboard as a worktree source.
- UI copy is Chinese by default.
- Do not introduce a frontend framework or new runtime dependency.
- Dashboard remains read-only.
- Evaluator must simulate a user viewing the dashboard and verify Auditor and skill content is visible.
- Do not stage unrelated root checkout wiki/crawler dirty files.

---

### Task 1: Backend Audit And Skill Payload

**Files:**
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Test: `apps/loop_dashboard/backend/tests/test_store.py`

**Interfaces:**
- Produces `detail["audit_summary"]` with keys `status`, `verdict`, `open_must_fix`, `direction_action`, `latest_report_path`, `findings`, `signals`, and `cadence`.
- Produces `detail["skill_inventory"]` with keys `total_project_skills`, `loop_related_skills`, `used_recently`, `candidate_skills`, and `items`.

- [x] **Step 1: Write failing backend test**

Add tests that seed a run with:

```text
.codex/loop-runs/audited-run/audit-reports/audit-003.json
.codex/loop-runs/audited-run/deterministic-signals.json
custom-skill/SKILL.md
```

Expected assertions:

```python
detail = LoopDashboardStore(tmp_path).get_run("audited-run")
assert detail["audit_summary"]["verdict"] == "observe"
assert detail["audit_summary"]["open_must_fix"] == 1
assert detail["audit_summary"]["signals"]["unclassified_dirty_paths"] == 2
assert detail["skill_inventory"]["total_project_skills"] == 1
assert detail["skill_inventory"]["items"][0]["name"] == "custom-skill"
```

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py -k "audit_summary or skill_inventory"
```

Expected: fail because the payload keys do not exist.

- [x] **Step 3: Implement backend parsing**

Implement small private helpers in `LoopDashboardStore`:

```python
_audit_summary(run_dir: Path) -> dict[str, Any]
_latest_audit_report(run_dir: Path) -> tuple[Path | None, dict[str, Any]]
_latest_deterministic_signals(run_dir: Path) -> dict[str, Any]
_skill_inventory() -> dict[str, Any]
```

Rules:
- Ignore `node_modules`, `.git`, `.worktrees`, and `generated`.
- Parse `SKILL.md` frontmatter `name` and `description` if present.
- Treat candidate skills from the Auditor spec as static suggestions until real artifacts exist: `pge-loop-agent-contract` and `loop-closeout-audit`.
- Do not throw on malformed JSON; return `status="invalid_artifact"` for audit summary and keep the page readable.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py -k "audit_summary or skill_inventory"
```

Expected: pass.

### Task 2: Frontend Auditor And Skill Sections

**Files:**
- Modify: `apps/loop_dashboard/frontend/index.html`
- Modify: `apps/loop_dashboard/frontend/app.js`
- Modify: `apps/loop_dashboard/frontend/styles.css`
- Test: `apps/loop_dashboard/backend/tests/test_api.py`

**Interfaces:**
- Consumes `audit_summary` and `skill_inventory` from run detail API.
- Adds visible sections to the existing detail view and tabs without breaking current Overview/Agent/Acceptance/Logs behavior.

- [x] **Step 1: Write failing API/static test**

Add an API test that seeds an audited run and asserts `/api/runs/<id>` includes `audit_summary` and `skill_inventory`. Also assert `/` serves markup containing the new tab label `审计与 Skill`.

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_api.py -k "auditor"
```

Expected: fail because the frontend label or API payload is missing.

- [x] **Step 3: Implement frontend**

Add one tab `审计与 Skill` and render:
- latest audit verdict and open must_fix count
- direction control action
- deterministic signal metrics
- audit findings list
- project skill summary counts
- skill table with name, source path, usage, and recommendation

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_api.py -k "auditor"
```

Expected: pass.

### Task 3: Browser Evaluator And Full Verification

**Files:**
- Modify: `scripts/loop_dashboard_evaluator.py`
- Modify: `progress.md`
- Test: `scripts/loop_dashboard_evaluator.py`

**Interfaces:**
- Evaluator must open the Loop Dashboard, select `loop-dashboard-auditor-dev` or seeded evaluator run, and verify visible text: `审计与 Skill`, `Auditor`, `当前项目 Skill`, and `open must_fix`.

- [x] **Step 1: Add evaluator assertions**

Extend the existing evaluator scenario with checks for the new tab and content.

- [x] **Step 2: Run full verification**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-auditor-01
python3 -m json.tool tasks.json >/dev/null
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 3: Update task state and progress**

Set `tasks.json` task `loop-dashboard-auditor-01` to `done` only after verification passes. Append evidence to `progress.md`.

- [x] **Step 4: Commit**

Commit only this task's files:

```bash
git add apps/loop_dashboard scripts/loop_dashboard_evaluator.py tasks.json progress.md docs/superpowers/plans/2026-07-08-loop-dashboard-auditor.md .codex/loop-runs/loop-dashboard-auditor-dev
git commit -m "feat(dashboard): show loop auditor state and skills"
```
