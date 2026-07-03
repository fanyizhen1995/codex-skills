# Loop Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent local Loop Dashboard that monitors the current project's Planner -> Generator -> Evaluator loop runs from a read-only browser UI, and use this feature to validate the demand-development loop workflow end to end.

**Architecture:** Add a focused app under `apps/loop_dashboard/`: a FastAPI backend reads existing loop/evaluator artifacts under a configurable `project_root`, summarizes runs/events/logs with path traversal guards and log redaction, and serves a Chinese static dashboard page. Add a Playwright-backed evaluator helper that starts the backend against temporary fixture data and clicks through the dashboard like a user.

**Tech Stack:** Python 3 standard library, FastAPI, pytest, Playwright for Python, static HTML/CSS/JavaScript, existing harness loop scripts and evaluator scenario contracts.

---

## File Structure

- Create `apps/loop_dashboard/backend/loop_dashboard/__init__.py`: package marker and exported app factory.
- Create `apps/loop_dashboard/backend/loop_dashboard/models.py`: typed dataclasses for run summaries, details, events, log entries, agents, and flow nodes.
- Create `apps/loop_dashboard/backend/loop_dashboard/redaction.py`: reusable log redaction for Authorization, GitHub tokens, token, password, secret, and api key patterns.
- Create `apps/loop_dashboard/backend/loop_dashboard/store.py`: read-only artifact store, safe path helpers, JSON loading, evaluator lookup, event/log collection, and run summarization.
- Create `apps/loop_dashboard/backend/loop_dashboard/main.py`: FastAPI app, CORS, static file serving, API routes, and CLI entrypoint support through uvicorn.
- Create `apps/loop_dashboard/backend/tests/test_redaction.py`: unit tests for sensitive text filtering.
- Create `apps/loop_dashboard/backend/tests/test_store.py`: fixture-backed tests for run parsing, agent summaries, completed states, blocking diagnostics, events/logs, invalid artifacts, and path safety.
- Create `apps/loop_dashboard/backend/tests/test_api.py`: FastAPI TestClient tests for health, project, run list, details, events, logs, empty state, and missing run errors.
- Create `apps/loop_dashboard/frontend/index.html`: independent Chinese dashboard shell.
- Create `apps/loop_dashboard/frontend/styles.css`: dense workbench-style layout with three columns, status colors, responsive behavior, and accessible click targets.
- Create `apps/loop_dashboard/frontend/app.js`: polling data client, run selection, flow rendering, agent cards, logs/events filters, completed run visibility, and error/empty states.
- Create `scripts/loop_dashboard_evaluator.py`: temporary fixture builder, dashboard service launcher, Playwright click-through evaluator, and JSON result writer.
- Create `docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json`: evaluator scenario contract for the dashboard.
- Modify `scripts/tests/test_harness_loop_autonomous.py`: add a regression test for directory pathspec auto-commit safety.
- Modify `scripts/harness_loop_autonomous.py`: make `run_git_commit()` expand directory pathspecs to dirty file paths and reject staged/untracked files not explicitly resolved for commit.
- Modify `scripts/tests/test_harness_evaluator_scenarios.py`: add a scenario registration test for `loop-dashboard-dev-01`.
- Modify `tasks.json`: register `loop-dashboard-dev-01` as an in-progress task with evaluator coverage.
- Modify `progress.md`: add an entry when implementation is complete with actual verification evidence.

## Task 1: Register Task And Fix Auto-Commit Pathspec Safety

**Files:**
- Modify: `tasks.json`
- Modify: `scripts/tests/test_harness_loop_autonomous.py`
- Modify: `scripts/harness_loop_autonomous.py`
- Test: `scripts/tests/test_harness_loop_autonomous.py`

- [ ] **Step 1: Add the task record to `tasks.json`**

  Insert this task object near the top of the `tasks` array, immediately after the Phase 3 loop task:

  ```json
  {
    "id": "loop-dashboard-dev-01",
    "title": "Build local Planner Generator Evaluator loop dashboard",
    "description": "Implement an independent read-only local dashboard for monitoring the current project's loop runs, agent status, skills/tools/logs, completed states, and blocked diagnostics; validate it through a browser-click evaluator scenario and use the demand-development loop workflow to reach the human merge gate.",
    "status": "in_progress",
    "priority": "high",
    "blocked_by": "planner-generator-evaluator-loop-phase-3-01",
    "verify": "python3 -m pytest -q apps/loop_dashboard/backend/tests && python3 -m unittest scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_evaluator_scenarios -v && python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01 && python3 -m json.tool tasks.json >/dev/null && python3 -m json.tool docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json >/dev/null && git diff --check",
    "requires_eval": true,
    "eval_policy": {
      "task_level_required": true,
      "final_level_required": false,
      "task_scope": "local_repo_and_harness",
      "final_scope": "report_and_artifacts",
      "max_task_eval_attempts": 3,
      "max_final_eval_attempts": 2
    }
  }
  ```

- [ ] **Step 2: Write the failing auto-commit regression test**

  Append this test method to `HarnessLoopAutonomousTests` in `scripts/tests/test_harness_loop_autonomous.py` before the `if __name__ == "__main__":` block:

  ```python
      def test_run_git_commit_with_directory_pathspec_does_not_commit_unrequested_dirty_files(self) -> None:
          with tempfile.TemporaryDirectory() as tmp:
              repo_root = Path(tmp)
              subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
              subprocess.run(
                  ["git", "config", "user.email", "codex@example.invalid"],
                  cwd=repo_root,
                  check=True,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
              )
              subprocess.run(
                  ["git", "config", "user.name", "Codex"],
                  cwd=repo_root,
                  check=True,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
              )
              raw_dir = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw"
              raw_dir.mkdir(parents=True)
              requested = raw_dir / "requested.md"
              preexisting = raw_dir / "preexisting.md"
              requested.write_text("requested\n", encoding="utf-8")
              preexisting.write_text("preexisting\n", encoding="utf-8")

              commit_sha = run_git_commit(
                  repo_root,
                  ["personal-wiki/domains/ai_infra/raw/requested.md"],
                  "test: commit requested raw evidence",
              )

              self.assertRegex(commit_sha, r"^[0-9a-f]{40}$")
              committed_files = subprocess.run(
                  ["git", "show", "--name-only", "--format=", "HEAD"],
                  cwd=repo_root,
                  check=True,
                  text=True,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
              )
              self.assertEqual(
                  committed_files.stdout.splitlines(),
                  ["personal-wiki/domains/ai_infra/raw/requested.md"],
              )
              status = subprocess.run(
                  ["git", "status", "--short"],
                  cwd=repo_root,
                  check=True,
                  text=True,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
              )
              self.assertIn("?? personal-wiki/domains/ai_infra/raw/preexisting.md", status.stdout)
  ```

  Then add a second test proving a broad directory pathspec is rejected when it would include multiple dirty files:

  ```python
      def test_run_git_commit_rejects_directory_pathspec_that_matches_multiple_dirty_files(self) -> None:
          with tempfile.TemporaryDirectory() as tmp:
              repo_root = Path(tmp)
              subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
              subprocess.run(
                  ["git", "config", "user.email", "codex@example.invalid"],
                  cwd=repo_root,
                  check=True,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
              )
              subprocess.run(
                  ["git", "config", "user.name", "Codex"],
                  cwd=repo_root,
                  check=True,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
              )
              raw_dir = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw"
              raw_dir.mkdir(parents=True)
              (raw_dir / "requested.md").write_text("requested\n", encoding="utf-8")
              (raw_dir / "preexisting.md").write_text("preexisting\n", encoding="utf-8")

              with self.assertRaisesRegex(ValueError, "directory pathspec"):
                  run_git_commit(
                      repo_root,
                      ["personal-wiki/domains/ai_infra/raw"],
                      "test: unsafe directory pathspec",
                  )
  ```

- [ ] **Step 3: Run the focused regression tests and verify they fail**

  Run:

  ```bash
  python3 -m unittest scripts.tests.test_harness_loop_autonomous.HarnessLoopAutonomousTests.test_run_git_commit_rejects_directory_pathspec_that_matches_multiple_dirty_files -v
  ```

  Expected: FAIL because the current `run_git_commit()` passes directory pathspecs directly to `git add`.

- [ ] **Step 4: Implement the commit path safety fix**

  Replace `run_git_commit()` in `scripts/harness_loop_autonomous.py` with helper-based logic:

  ```python
  def run_git_commit(repo_root: Path | str, paths: Sequence[str], message: str) -> str:
      if not paths:
          raise ValueError("paths must not be empty")
      repo = Path(repo_root)
      resolved_paths = _resolve_commit_pathspecs(repo, paths)
      subprocess.run(["git", "add", "--", *resolved_paths], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      subprocess.run(
          ["git", "commit", "-m", message, "--", *resolved_paths],
          cwd=repo,
          check=True,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
      )
      result = subprocess.run(
          ["git", "rev-parse", "HEAD"],
          cwd=repo,
          check=True,
          text=True,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
      )
      return result.stdout.strip()
  ```

  Add these helpers near `run_git_commit()`:

  ```python
  def _resolve_commit_pathspecs(repo: Path, paths: Sequence[str]) -> list[str]:
      dirty_paths = set(_dirty_files_for_commit(repo))
      resolved: list[str] = []
      for raw_path in paths:
          path = str(raw_path).strip()
          if not path:
              raise ValueError("commit pathspec must not be empty")
          if path.startswith("-") or Path(path).is_absolute() or ".." in Path(path).parts:
              raise ValueError(f"unsafe commit pathspec: {path}")
          candidate = repo / path
          if candidate.exists() and candidate.is_dir():
              matches = sorted(item for item in dirty_paths if item == path or item.startswith(f"{path.rstrip('/')}/"))
              if len(matches) != 1:
                  raise ValueError(f"directory pathspec must resolve to exactly one dirty file: {path}")
              resolved.extend(matches)
          else:
              resolved.append(path)
      unique: list[str] = []
      seen: set[str] = set()
      for path in resolved:
          if path not in seen:
              seen.add(path)
              unique.append(path)
      return unique
  ```

  And:

  ```python
  def _dirty_files_for_commit(repo: Path) -> list[str]:
      result = subprocess.run(
          ["git", "status", "--porcelain", "--untracked-files=all"],
          cwd=repo,
          check=True,
          text=True,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
      )
      dirty: list[str] = []
      for line in result.stdout.splitlines():
          if not line.strip():
              continue
          path = line[3:]
          if " -> " in path:
              path = path.rsplit(" -> ", 1)[1]
          dirty.append(path)
      return dirty
  ```

- [ ] **Step 5: Run focused and full autonomous tests**

  Run:

  ```bash
  python3 -m unittest scripts.tests.test_harness_loop_autonomous -v
  ```

  Expected: PASS, including the new directory pathspec tests.

- [ ] **Step 6: Commit Task 1**

  ```bash
  git add tasks.json scripts/tests/test_harness_loop_autonomous.py scripts/harness_loop_autonomous.py
  git commit -m "fix(harness): harden autonomous commit pathspecs"
  ```

## Task 2: Backend Store, Redaction, And Read-Only API

**Files:**
- Create: `apps/loop_dashboard/backend/loop_dashboard/__init__.py`
- Create: `apps/loop_dashboard/backend/loop_dashboard/models.py`
- Create: `apps/loop_dashboard/backend/loop_dashboard/redaction.py`
- Create: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Create: `apps/loop_dashboard/backend/loop_dashboard/main.py`
- Create: `apps/loop_dashboard/backend/tests/test_redaction.py`
- Create: `apps/loop_dashboard/backend/tests/test_store.py`
- Create: `apps/loop_dashboard/backend/tests/test_api.py`

- [ ] **Step 1: Write failing redaction tests**

  Create `apps/loop_dashboard/backend/tests/test_redaction.py`:

  ```python
  from loop_dashboard.redaction import redact_text


  def test_redacts_common_credentials_but_keeps_context() -> None:
      text = "\n".join(
          [
              "Authorization: Bearer abc.def.ghi",
              "token=ghp_1234567890abcdef",
              "password = hunter2",
              "secret: open-sesame",
              "api_key=sk-test-123",
              "plain line",
          ]
      )

      redacted = redact_text(text)

      assert "Authorization: Bearer [REDACTED]" in redacted
      assert "token=[REDACTED]" in redacted
      assert "password = [REDACTED]" in redacted
      assert "secret: [REDACTED]" in redacted
      assert "api_key=[REDACTED]" in redacted
      assert "plain line" in redacted
      assert "hunter2" not in redacted
      assert "open-sesame" not in redacted
      assert "ghp_1234567890abcdef" not in redacted
  ```

- [ ] **Step 2: Write failing store tests**

  Create `apps/loop_dashboard/backend/tests/test_store.py` with fixture helpers and tests:

  ```python
  import json
  from pathlib import Path

  import pytest

  from loop_dashboard.store import LoopDashboardStore, safe_join


  def write_json(path: Path, payload: dict) -> None:
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


  def seed_run(repo_root: Path, run_id: str, phase: str, last_result: str = "none", next_action: str = "run_generator") -> None:
      run_dir = repo_root / ".codex" / "loop-runs" / run_id
      write_json(
          run_dir / "run.json",
          {
              "run_id": run_id,
              "policy": "demand_development",
              "phase": phase,
              "task_id": "loop-dashboard-dev-01",
              "domain": "",
              "branch": "feat/loop-dashboard",
              "worktree": str(repo_root),
              "requirement": "实现独立本地 Loop Dashboard，监控 loop、agent、skill 和日志。",
              "constraints": ["只读后端", "中文 UI"],
              "stop_conditions": ["passed_waiting_human_merge"],
              "baseline_dirty_paths": [],
              "allowed_paths": [],
              "denylist_paths": [],
              "attempts": {"planner": 1, "generator": 1, "evaluator": 1, "artifact_hygiene": 0, "cleanup": 0},
              "limits": {"max_eval_attempts": 2},
              "last_result": last_result,
              "next_action": next_action,
              "attempt_history": [],
              "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
          },
      )
      write_json(
          run_dir / "planner-output.json",
          {
              "task_id": "loop-dashboard-dev-01",
              "policy": "demand_development",
              "task_kind": "registered_task",
              "title": "Loop 看板",
              "goal": "实现看板",
              "non_goals": [],
              "allowed_paths": ["apps/loop_dashboard"],
              "denylist_paths": [".env"],
              "verify_commands": ["python3 -m pytest -q apps/loop_dashboard/backend/tests"],
              "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json",
              "stop_conditions": ["passed_waiting_human_merge"],
              "next_planning_hint": "",
          },
      )
      write_json(
          run_dir / "generator-result.json",
          {
              "task_id": "loop-dashboard-dev-01",
              "status": "implemented",
              "changed_paths": ["apps/loop_dashboard/backend/loop_dashboard/store.py"],
              "commit": "",
              "verify_commands": ["python3 -m pytest -q apps/loop_dashboard/backend/tests"],
              "verify_results": [{"command": "pytest", "status": "pass"}],
              "artifacts": ["apps/loop_dashboard/backend/loop_dashboard/store.py"],
              "cleanup_required": False,
              "notes": "完成只读 API",
          },
      )
      write_json(
          run_dir / "evaluator-result.json",
          {
              "status": "fail" if phase == "repair_needed" else "pass",
              "gate": "task",
              "task_id": "loop-dashboard-dev-01",
              "final_bundle_id": "",
              "attempt": 1,
              "summary": "点击日志过滤失败" if phase == "repair_needed" else "通过",
              "findings": [
                  {
                      "id": "LD-001",
                      "severity": "major",
                      "category": "frontend_click",
                      "evidence": ["logs filter did not update"],
                      "recommended_action": "修复日志过滤",
                  }
              ]
              if phase == "repair_needed"
              else [],
              "scenario_results": [],
              "rerun_commands": [],
              "environment_checks": [],
              "verdict_reason": "需要修复" if phase == "repair_needed" else "通过",
              "next_action": "repair_and_reevaluate" if phase == "repair_needed" else "proceed_to_user_acceptance",
          },
      )
      (run_dir / "planner-attempt-1.stdout.log").write_text("Planner: 正在拆解需求\nAuthorization: Bearer secret-token\n", encoding="utf-8")
      (run_dir / "generator-attempt-1.stderr.log").write_text("Generator 使用 skill: test-driven-development\n", encoding="utf-8")


  def test_safe_join_rejects_path_traversal(tmp_path: Path) -> None:
      with pytest.raises(ValueError):
          safe_join(tmp_path, "../outside")


  def test_list_runs_summarizes_agents_completed_and_blocked_states(tmp_path: Path) -> None:
      seed_run(tmp_path, "active-run", "repair_needed", last_result="fail", next_action="run_generator_repair")
      seed_run(tmp_path, "complete-run", "passed_waiting_human_merge", last_result="pass", next_action="await_human_merge_confirmation")

      store = LoopDashboardStore(tmp_path)
      runs = store.list_runs()

      assert [run["run_id"] for run in runs] == ["complete-run", "active-run"]
      active = next(run for run in runs if run["run_id"] == "active-run")
      assert active["task_summary"].startswith("实现独立本地 Loop Dashboard")
      assert active["agents"]["planner"]["attempt"] == 1
      assert active["agents"]["generator"]["last_result"] == "完成只读 API"
      assert active["agents"]["evaluator"]["status"] == "fail"
      assert active["blocked_diagnostics"][0]["kind"] == "evaluator_finding"
      assert next(run for run in runs if run["run_id"] == "complete-run")["completed"] is True


  def test_detail_includes_flow_nodes_events_and_redacted_logs(tmp_path: Path) -> None:
      seed_run(tmp_path, "active-run", "repair_needed", last_result="fail", next_action="run_generator_repair")

      store = LoopDashboardStore(tmp_path)
      detail = store.get_run("active-run")
      events = store.get_events("active-run")
      logs = store.get_logs("active-run")

      assert detail["flow_nodes"][0]["label"] == "Preflight"
      assert any(node["status"] == "running" for node in detail["flow_nodes"])
      assert any(event["kind"] == "artifact" for event in events)
      assert any(log["stream"] == "stdout" for log in logs)
      joined = "\n".join(log["content"] for log in logs)
      assert "Authorization: Bearer [REDACTED]" in joined
      assert "secret-token" not in joined


  def test_missing_loop_runs_directory_returns_empty_list(tmp_path: Path) -> None:
      assert LoopDashboardStore(tmp_path).list_runs() == []


  def test_invalid_run_json_is_reported_without_breaking_other_runs(tmp_path: Path) -> None:
      seed_run(tmp_path, "good-run", "passed_waiting_human_merge", last_result="pass", next_action="await_human_merge_confirmation")
      broken = tmp_path / ".codex" / "loop-runs" / "broken-run"
      broken.mkdir(parents=True)
      (broken / "run.json").write_text("{bad json", encoding="utf-8")

      runs = LoopDashboardStore(tmp_path).list_runs()

      assert any(run["run_id"] == "good-run" for run in runs)
      invalid = next(run for run in runs if run["run_id"] == "broken-run")
      assert invalid["phase"] == "invalid_artifact"
      assert invalid["health"] == "blocked"
  ```

- [ ] **Step 3: Write failing API tests**

  Create `apps/loop_dashboard/backend/tests/test_api.py`:

  ```python
  import json
  from pathlib import Path

  from fastapi.testclient import TestClient

  from loop_dashboard.main import create_app


  def write_json(path: Path, payload: dict) -> None:
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


  def seed_minimal_run(repo_root: Path) -> None:
      write_json(
          repo_root / ".codex" / "loop-runs" / "demo-run" / "run.json",
          {
              "run_id": "demo-run",
              "policy": "demand_development",
              "phase": "passed_waiting_human_merge",
              "task_id": "loop-dashboard-dev-01",
              "domain": "",
              "branch": "feat/loop-dashboard",
              "worktree": str(repo_root),
              "requirement": "展示 run 列表和详情",
              "constraints": ["只读"],
              "stop_conditions": ["passed_waiting_human_merge"],
              "baseline_dirty_paths": [],
              "allowed_paths": [],
              "denylist_paths": [],
              "attempts": {"planner": 1, "generator": 1, "evaluator": 1, "artifact_hygiene": 0, "cleanup": 0},
              "limits": {},
              "last_result": "pass",
              "next_action": "await_human_merge_confirmation",
              "attempt_history": [],
              "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
          },
      )


  def test_api_project_runs_detail_events_and_logs(tmp_path: Path) -> None:
      seed_minimal_run(tmp_path)
      client = TestClient(create_app(project_root=tmp_path))

      assert client.get("/api/health").json()["status"] == "ok"
      assert client.get("/api/projects/current").json()["project_root"] == str(tmp_path.resolve())
      runs = client.get("/api/runs").json()
      assert runs[0]["run_id"] == "demo-run"
      assert runs[0]["task_summary"] == "展示 run 列表和详情"
      assert client.get("/api/runs/demo-run").json()["phase"] == "passed_waiting_human_merge"
      assert client.get("/api/runs/demo-run/events").json()["run_id"] == "demo-run"
      assert client.get("/api/runs/demo-run/logs").json()["run_id"] == "demo-run"


  def test_api_returns_404_for_missing_run(tmp_path: Path) -> None:
      client = TestClient(create_app(project_root=tmp_path))

      response = client.get("/api/runs/missing")

      assert response.status_code == 404
      assert response.json()["detail"] == "run not found: missing"
  ```

- [ ] **Step 4: Run backend tests and verify they fail**

  Run:

  ```bash
  PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
  ```

  Expected: FAIL with `ModuleNotFoundError: No module named 'loop_dashboard'`.

- [ ] **Step 5: Implement backend modules**

  Implement:

  - `redact_text(text: str) -> str` in `redaction.py`.
  - `safe_join(root: Path, relative_path: str) -> Path` in `store.py`.
  - `LoopDashboardStore(project_root)` with `list_runs()`, `get_run(run_id)`, `get_events(run_id)`, and `get_logs(run_id)`.
  - Summary fields:
    - `task_summary`: `run["requirement"]` trimmed to 96 chars.
    - `health`: `blocked` for `stopped_blocked`, `repair_needed`, `invalid_artifact`; `completed` for completed phases; otherwise `progressing`.
    - `completed`: true for `passed_waiting_human_merge`, `stopped_no_action`, `stopped_budget`, `stopped_blocked`.
    - `agents`: planner/generator/evaluator attempts, status, current action, last result from artifacts or logs.
    - `flow_nodes`: demand-development and autonomous-knowledge node lists with `done`, `running`, `waiting`, or `blocked`.
    - `blocked_diagnostics`: dirty path, allowlist/denylist, supply-chain, artifact hygiene, cleanup, and evaluator finding summaries when corresponding result files exist.
  - API routes in `main.py`:
    - `GET /api/health`
    - `GET /api/projects/current`
    - `GET /api/runs`
    - `GET /api/runs/{run_id}`
    - `GET /api/runs/{run_id}/events`
    - `GET /api/runs/{run_id}/logs`
    - Static `/` serving `apps/loop_dashboard/frontend/index.html`.

- [ ] **Step 6: Run backend tests and verify they pass**

  Run:

  ```bash
  PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
  ```

  Expected: PASS.

- [ ] **Step 7: Commit Task 2**

  ```bash
  git add apps/loop_dashboard/backend
  git commit -m "feat(loop-dashboard): add read-only loop API"
  ```

## Task 3: Chinese Frontend Dashboard

**Files:**
- Create: `apps/loop_dashboard/frontend/index.html`
- Create: `apps/loop_dashboard/frontend/styles.css`
- Create: `apps/loop_dashboard/frontend/app.js`
- Test indirectly via: `scripts/loop_dashboard_evaluator.py` in Task 4 and backend static route smoke.

- [ ] **Step 1: Create the static dashboard shell**

  Add `index.html` with:

  - `<html lang="zh-CN">`
  - Header title `Loop 看板`
  - Project status element with `data-testid="project-status"`
  - Run list container `data-testid="run-list"`
  - Run detail section `data-testid="run-detail"`
  - Flow diagram container `data-testid="flow-diagram"`
  - Agent cards container `data-testid="agent-cards"`
  - Blocked diagnostics container `data-testid="blocked-diagnostics"`
  - Completed runs section `data-testid="completed-runs"`
  - Event/log filter controls:
    - `<select data-testid="log-kind-filter">`
    - `<input data-testid="log-keyword-filter">`
  - Log list `data-testid="log-list"`

- [ ] **Step 2: Add operational CSS**

  Add `styles.css` with:

  - Three-column desktop layout.
  - Single-column mobile layout under 900px.
  - Stable dimensions for run items, flow nodes, agent cards, and iconless buttons.
  - No marketing hero, no decorative gradients, no nested cards.
  - Clearly labeled status styles for `完成`, `运行中`, `等待`, `阻塞`.
  - Text wrapping and `overflow-wrap: anywhere` for paths and long run IDs.

- [ ] **Step 3: Implement frontend data flow**

  Add `app.js` with:

  - `fetchJson(path)` using same-origin `/api`.
  - `refresh()` that polls `/api/projects/current` and `/api/runs` every 3000 ms.
  - Default selection of most recently active run.
  - Preserve selected run across polling if it still exists.
  - `selectRun(runId)` that loads detail, events, and logs.
  - Click handlers on run buttons.
  - Log filtering by kind and keyword without changing selected run.
  - Empty state for no runs.
  - Recoverable error state if a selected run disappears.
  - Chinese labels for policy, phase, health, agent actions, and redaction notice.

- [ ] **Step 4: Start a local smoke server and inspect the page**

  Run:

  ```bash
  PYTHONPATH=apps/loop_dashboard/backend python3 -m uvicorn loop_dashboard.main:app --host 127.0.0.1 --port 8766
  ```

  Open `http://127.0.0.1:8766` manually or through Playwright in Task 4. Expected: the dashboard loads in Chinese and shows an empty state if no `.codex/loop-runs` exists.

- [ ] **Step 5: Commit Task 3**

  ```bash
  git add apps/loop_dashboard/frontend apps/loop_dashboard/backend/loop_dashboard/main.py
  git commit -m "feat(loop-dashboard): add Chinese dashboard UI"
  ```

## Task 4: Browser-Click Evaluator Scenario

**Files:**
- Create: `scripts/loop_dashboard_evaluator.py`
- Create: `docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json`
- Modify: `scripts/tests/test_harness_evaluator_scenarios.py`
- Test: `scripts/tests/test_harness_evaluator_scenarios.py`

- [ ] **Step 1: Add evaluator scenario registration test**

  Add this method to `HarnessEvaluatorScenarioTests`:

  ```python
      def test_loop_dashboard_dev_entrypoint_is_registered(self) -> None:
          repo_root = Path(__file__).resolve().parents[2]

          contract = load_task_scenarios(repo_root, "loop-dashboard-dev-01")

          self.assertEqual(contract["task_id"], "loop-dashboard-dev-01")
          self.assertTrue(contract["must_simulate"])
          self.assertEqual(contract["user_scenarios"][0]["automation_hint"], "playwright")
          self.assertIn("scripts/loop_dashboard_evaluator.py", contract["user_scenarios"][0]["entrypoint"])
  ```

- [ ] **Step 2: Run the scenario registration test and verify it fails**

  Run:

  ```bash
  python3 -m unittest scripts.tests.test_harness_evaluator_scenarios.HarnessEvaluatorScenarioTests.test_loop_dashboard_dev_entrypoint_is_registered -v
  ```

  Expected: FAIL because the scenario file does not exist yet.

- [ ] **Step 3: Create evaluator scenario JSON**

  Create `docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json`:

  ```json
  {
    "task_id": "loop-dashboard-dev-01",
    "must_simulate": true,
    "user_scenarios": [
      {
        "scenario_id": "LOOP-DASHBOARD-CLICK-SMOKE",
        "user_goal": "As an operator, open the local Loop Dashboard, select loop runs, inspect task and agent summaries, view the visual flow, filter logs, and confirm completed runs are visible.",
        "prerequisites": [
          "FastAPI and Playwright for Python are available.",
          "The evaluator creates temporary loop-run fixture data and does not mutate real project artifacts."
        ],
        "entrypoint": "python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01",
        "steps": [
          "Create fixture loop runs covering active repair, passed_waiting_human_merge, stopped_no_action, stopped_budget, and stopped_blocked states.",
          "Start the dashboard backend against the temporary fixture project root.",
          "Open the dashboard in a browser.",
          "Click the active run and verify task description, phase, next action, agent cards, blocked diagnostics, and flow diagram.",
          "Filter logs by stderr and by keyword.",
          "Click completed runs and verify their terminal states remain visible."
        ],
        "expected_outcomes": [
          "The dashboard page renders in Chinese.",
          "Run selection updates detail, flow diagram, agent cards, logs, and diagnostics.",
          "Completed runs are visible.",
          "Log text is redacted before display.",
          "The evaluator writes result.json with status pass."
        ],
        "failure_signals": [
          "The frontend reports failed to fetch.",
          "Clicking a run does not update detail.",
          "Planner, Generator, or Evaluator summaries are missing.",
          "Log filtering does not change visible entries.",
          "Completed run states are hidden."
        ],
        "cleanup": [
          "Stop the temporary dashboard server.",
          "Remove temporary fixture directories after writing evaluator evidence."
        ],
        "automation_hint": "playwright"
      }
    ]
  }
  ```

- [ ] **Step 4: Implement `scripts/loop_dashboard_evaluator.py`**

  The script must:

  - Parse `--repo-root`, `--output-dir`, and optional `--port`.
  - Create a temporary fixture project root.
  - Seed loop runs for:
    - `active-repair-run`
    - `passed-run`
    - `no-action-run`
    - `budget-run`
    - `blocked-run`
  - Start `python3 -m uvicorn loop_dashboard.main:create_app --factory` is not appropriate because `project_root` must point to the fixture. Instead start a small subprocess with:

    ```bash
    PYTHONPATH=<repo>/apps/loop_dashboard/backend LOOP_DASHBOARD_PROJECT_ROOT=<fixture> python3 -m uvicorn loop_dashboard.main:app --host 127.0.0.1 --port <port>
    ```

  - Poll `/api/health` until ready.
  - Use `playwright.sync_api.sync_playwright()` and Chromium to:
    - open `/`
    - assert text `Loop 看板`
    - click `active-repair-run`
    - assert `实现独立本地 Loop Dashboard`
    - assert `Planner`, `Generator`, `Evaluator`
    - assert flow node `Evaluator`
    - assert blocked diagnostic text `LD-001`
    - filter kind `stderr`
    - assert stderr log text appears
    - filter keyword `REDACTED`
    - assert redacted Authorization appears
    - click `passed-run`, `no-action-run`, `budget-run`, and `blocked-run`
    - assert their states appear in the detail area.
  - Write `<output-dir>/result.json`:

    ```json
    {
      "status": "pass",
      "scenario_id": "LOOP-DASHBOARD-CLICK-SMOKE",
      "checked": ["run-list", "run-detail", "flow-diagram", "agent-cards", "logs", "completed-runs"],
      "dashboard_url": "http://127.0.0.1:<port>"
    }
    ```

  - On failure, write `status: fail`, capture a screenshot to `<output-dir>/failure.png`, include the exception message, and exit non-zero.
  - Always terminate the uvicorn subprocess.

- [ ] **Step 5: Run evaluator tests**

  Run:

  ```bash
  python3 -m unittest scripts.tests.test_harness_evaluator_scenarios.HarnessEvaluatorScenarioTests.test_loop_dashboard_dev_entrypoint_is_registered -v
  python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01
  ```

  Expected: both pass, and the evaluator writes `.codex/loop-dashboard-eval/loop-dashboard-dev-01/result.json`.

- [ ] **Step 6: Commit Task 4**

  ```bash
  git add scripts/loop_dashboard_evaluator.py docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json scripts/tests/test_harness_evaluator_scenarios.py
  git commit -m "test(loop-dashboard): add browser evaluator scenario"
  ```

## Task 5: Demand Loop Smoke, Docs, Progress, And Final Verification

**Files:**
- Modify: `docs/harness/planner-generator-evaluator-loop.md`
- Modify: `tasks.json`
- Modify: `progress.md`
- Temporary local artifacts only: `.codex/loop-runs/loop-dashboard-dev/` and `.codex/loop-dashboard-eval/loop-dashboard-dev-01/`

- [ ] **Step 1: Create confirmed demand-development preflight for this feature**

  Run:

  ```bash
  python3 scripts/harness_loop_orchestrator.py preflight \
    --repo-root . \
    --mode demand-development \
    --requirement "实现独立本地 Loop Dashboard，用于中文可视化监控当前项目 Planner Generator Evaluator loop、agent、skill、日志、完成态和阻塞诊断；本次也要验证需求开发 loop 流程，发现流程 bug 直接修复。" \
    --run-id loop-dashboard-dev \
    --task-id loop-dashboard-dev-01 \
    --constraint "后端只读，不提供执行、删除、重启、合入、回滚等写操作。" \
    --constraint "前端使用中文，轮询刷新间隔为 3 秒。" \
    --constraint "evaluator 必须通过前端点击模拟用户验证主要路径。" \
    --constraint "最终停在 passed_waiting_human_merge，等待用户确认合入。" \
    --stop-condition passed_waiting_human_merge \
    --confirm
  ```

  Expected: `.codex/loop-runs/loop-dashboard-dev/run.json` has phase `planned`.

- [ ] **Step 2: Run the demand loop fake gate to verify workflow still reaches human merge**

  Run:

  ```bash
  python3 scripts/harness_loop_orchestrator.py run \
    --repo-root . \
    --run-id loop-dashboard-dev \
    --planner-driver fake \
    --generator-driver fake \
    --evaluator-driver fake \
    --max-eval-attempts 2
  python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id loop-dashboard-dev
  ```

  Expected: status JSON reports `phase` as `passed_waiting_human_merge` and `next_action` as `await_human_merge_confirmation`.

- [ ] **Step 3: Document dashboard development and evaluator commands**

  Add a `## Loop Dashboard` section to `docs/harness/planner-generator-evaluator-loop.md` with:

  ```markdown
  ## Loop Dashboard

  The local read-only dashboard lives under `apps/loop_dashboard/`.
  Start it against the current checkout:

  ```bash
  PYTHONPATH=apps/loop_dashboard/backend \
  LOOP_DASHBOARD_PROJECT_ROOT=/home/fyz/codex-skills \
  python3 -m uvicorn loop_dashboard.main:app --host 0.0.0.0 --port 8766
  ```

  Open `http://127.0.0.1:8766`. The backend only reads loop and evaluator
  artifacts from the configured project root. It does not execute, delete,
  restart, merge, or roll back loop runs.

  Browser-click evaluator:

  ```bash
  python3 scripts/loop_dashboard_evaluator.py \
    --repo-root . \
    --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01
  ```
  ```

- [ ] **Step 4: Mark the task done and append progress evidence**

  In `tasks.json`, change `loop-dashboard-dev-01` status from `in_progress` to `done` after all verification commands pass.

  Add a top `progress.md` entry:

  ```markdown
  ## 2026-07-03 Loop Dashboard

  - Completed `loop-dashboard-dev-01`: added an independent read-only Loop Dashboard for current-project loop runs, agent summaries, visual flow, logs/events, completed states, and blocked diagnostics.
  - Added a browser-click evaluator that starts the dashboard against temporary fixture loop artifacts and validates run selection, agent cards, flow diagram, log filtering, redaction, and completed states.
  - Fixed autonomous loop auto-commit pathspec safety so directory pathspecs cannot accidentally commit unrelated dirty files.
  - Evidence:
    - `python3 -m pytest -q apps/loop_dashboard/backend/tests`
    - `python3 -m unittest scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_evaluator_scenarios -v`
    - `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01`
    - `python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id loop-dashboard-dev`
    - `git diff --check`
  ```

- [ ] **Step 5: Run full verification**

  Run:

  ```bash
  python3 -m pytest -q apps/loop_dashboard/backend/tests
  python3 -m unittest scripts.tests.test_harness_loop_autonomous scripts.tests.test_harness_evaluator_scenarios -v
  python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/loop-dashboard-dev-01
  python3 -m json.tool tasks.json >/dev/null
  python3 -m json.tool docs/harness/evaluator-scenarios/loop-dashboard-dev-01.json >/dev/null
  git diff --check
  ```

  Expected: all commands pass.

- [ ] **Step 6: Commit Task 5**

  ```bash
  git add docs/harness/planner-generator-evaluator-loop.md tasks.json progress.md
  git commit -m "docs(loop-dashboard): record development workflow"
  ```

## Final Review And Handoff

- [ ] Dispatch a spec compliance reviewer for the full implementation against `docs/superpowers/specs/2026-07-03-loop-dashboard-design.md`.
- [ ] Dispatch a code quality reviewer for the full branch diff from `b800bca` to `HEAD`.
- [ ] Fix any Critical or Important reviewer findings with tests.
- [ ] Run the full verification command set from Task 5 again.
- [ ] Use `superpowers:finishing-a-development-branch`; the expected outcome for this user request is to stop at the human merge gate and ask before merging.
