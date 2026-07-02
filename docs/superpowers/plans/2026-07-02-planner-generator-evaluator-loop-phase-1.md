# Planner Generator Evaluator Loop Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 demand-development loop skeleton: preflight gate, JSON contracts, run state, minimal Planner/Generator `codex exec` wrappers, evaluator fail repair handoff, and human merge gate.

**Architecture:** Add a new loop layer beside the existing evaluator harness instead of replacing it. `scripts/harness_loop_contracts.py` owns schema validation, `scripts/harness_loop_agents.py` owns Codex CLI invocation/probing, and `scripts/harness_loop_orchestrator.py` owns CLI state transitions under `.codex/loop-runs/<run-id>/`. Phase 1 supports `demand_development`; autonomous knowledge remains documented but unimplemented until later phases.

**Tech Stack:** Python 3 standard library, `unittest`, existing `scripts/harness_evaluator_orchestrator.py`, existing `tasks.json`/evaluator scenario contracts, Codex CLI via subprocess.

---

## File Structure

- Create `scripts/harness_loop_contracts.py`: policy normalization, run id generation, JSON read/write helpers, and validation for Phase 1 `run.json`, `planner-output.json`, `generator-result.json`, and `agent-attempt.json`.
- Create `scripts/harness_loop_agents.py`: probe `codex exec --help`, build supported Codex commands, run prompts with timeout, and write attempt evidence.
- Create `scripts/harness_loop_orchestrator.py`: CLI entrypoint for `preflight`, `confirm-preflight`, `plan`, `generate`, `evaluate`, `run`, and `status`.
- Create `scripts/tests/test_harness_loop_contracts.py`: unit tests for validators and policy normalization.
- Create `scripts/tests/test_harness_loop_agents.py`: unit tests for Codex command probing and failure result mapping with mocked subprocess.
- Create `scripts/tests/test_harness_loop_orchestrator.py`: unit tests for run directory creation, preflight gating, fake planner/generator, evaluator repair state, and human merge gate.
- Create `docs/harness/planner-generator-evaluator-loop.md`: operator runbook for Phase 1 commands and limitations.
- Modify `tasks.json`: add `planner-generator-evaluator-loop-phase-1-01` task entry.
- Modify `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-1-01.json`: add user-facing evaluator scenario contract for the loop CLI.
- Modify `progress.md`: append a Phase 1 implementation entry after work completes.

## Task 1: Register Phase 1 Task And Scenario

**Files:**
- Modify: `tasks.json`
- Create: `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-1-01.json`

- [ ] **Step 1: Add the task entry to `tasks.json`**

Add this object near the top of the `tasks` array:

```json
{
  "id": "planner-generator-evaluator-loop-phase-1-01",
  "title": "Implement Planner Generator Evaluator loop Phase 1",
  "description": "Add the demand-development loop skeleton with preflight gate, JSON contracts, Codex Planner/Generator wrappers, evaluator repair handoff, and human merge gate.",
  "status": "pending",
  "priority": "high",
  "blocked_by": "",
  "verify": "python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v && python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement \"Phase 1 smoke demand loop\" --run-id smoke-phase-1 --confirm && python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id smoke-phase-1 --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2",
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

- [ ] **Step 2: Create the evaluator scenario contract**

Create `docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-1-01.json`:

```json
{
  "task_id": "planner-generator-evaluator-loop-phase-1-01",
  "must_simulate": true,
  "user_scenarios": [
    {
      "scenario_id": "PGE-PHASE1-CLI-FLOW",
      "user_goal": "As an operator, start a demand-development loop, confirm preflight, run fake planner/generator/evaluator drivers, and see the loop stop at the human merge gate with durable run evidence.",
      "prerequisites": [
        "Repository root is writable.",
        "Existing evaluator harness scripts are available.",
        "No real Codex model call is required for the fake-driver scenario."
      ],
      "entrypoint": "python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement \"Evaluator scenario demand loop\" --run-id evaluator-scenario-phase-1 --confirm && python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id evaluator-scenario-phase-1 --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2",
      "steps": [
        "Create or reuse a loop run with confirmed preflight.",
        "Run the fake Planner driver to write planner-output.json.",
        "Run the fake Generator driver to write generator-result.json.",
        "Run the fake evaluator driver and record evaluator status.",
        "Verify run.json stops at passed_waiting_human_merge."
      ],
      "expected_outcomes": [
        ".codex/loop-runs/evaluator-scenario-phase-1/run.json exists.",
        "planner-output.json and generator-result.json exist and validate.",
        "run.json phase is passed_waiting_human_merge.",
        "run.json next_action is await_human_merge_confirmation."
      ],
      "failure_signals": [
        "The loop executes without confirmed preflight.",
        "The loop reports complete instead of waiting for human merge.",
        "Planner or Generator outputs are missing or fail schema validation."
      ],
      "cleanup": [
        "The evaluator may leave .codex/loop-runs/evaluator-scenario-phase-1 as evidence."
      ],
      "automation_hint": "shell"
    }
  ]
}
```

- [ ] **Step 3: Validate task JSON and scenario contract**

Run:

```bash
python3 -m json.tool tasks.json > /dev/null
python3 -m json.tool docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-1-01.json > /dev/null
python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v
```

Expected: JSON commands exit 0; scenario tests still pass.

- [ ] **Step 4: Commit task registration**

```bash
git add tasks.json docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-1-01.json
git commit -m "chore(harness): register planner loop phase 1 task"
```

## Task 2: Add Loop Contract Validators

**Files:**
- Create: `scripts/harness_loop_contracts.py`
- Create: `scripts/tests/test_harness_loop_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Create `scripts/tests/test_harness_loop_contracts.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.harness_loop_contracts import (
    default_limits,
    normalize_policy_id,
    read_json_file,
    run_dir_for,
    validate_agent_attempt_payload,
    validate_generator_result_payload,
    validate_planner_output_payload,
    validate_run_payload,
    write_json_file,
)


class HarnessLoopContractsTests(unittest.TestCase):
    def test_normalize_policy_id_accepts_dash_and_underscore(self) -> None:
        self.assertEqual(normalize_policy_id("demand-development"), "demand_development")
        self.assertEqual(normalize_policy_id("demand_development"), "demand_development")
        self.assertEqual(normalize_policy_id("autonomous-knowledge"), "autonomous_knowledge")
        with self.assertRaises(ValueError):
            normalize_policy_id("unknown")

    def test_validate_run_payload_requires_phase_and_policy(self) -> None:
        payload = {
            "run_id": "demo",
            "policy": "demand_development",
            "phase": "preflight",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": "/tmp/repo",
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 0, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": default_limits(),
            "last_result": "none",
            "next_action": "await_preflight_confirmation",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        }
        validate_run_payload(payload)
        payload["phase"] = "bogus"
        with self.assertRaises(ValueError):
            validate_run_payload(payload)

    def test_validate_planner_output_payload_requires_task_kind(self) -> None:
        payload = {
            "task_id": "demo-task",
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": "Demo",
            "goal": "Demo goal",
            "non_goals": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "verify_commands": ["python3 -m unittest -v"],
            "evaluator_scenarios_path": "docs/harness/evaluator-scenarios/demo-task.json",
            "stop_conditions": ["human merge gate"],
            "next_planning_hint": "",
        }
        validate_planner_output_payload(payload)
        payload["task_kind"] = "handoff_to_demand_development"
        with self.assertRaises(ValueError):
            validate_planner_output_payload(payload)

    def test_validate_generator_result_payload_rejects_non_list_changed_paths(self) -> None:
        payload = {
            "task_id": "demo-task",
            "status": "implemented",
            "changed_paths": [],
            "commit": "",
            "verify_commands": [],
            "verify_results": [],
            "artifacts": [],
            "cleanup_required": True,
            "notes": "ok",
        }
        validate_generator_result_payload(payload)
        payload["changed_paths"] = "not-a-list"
        with self.assertRaises(ValueError):
            validate_generator_result_payload(payload)

    def test_validate_agent_attempt_payload_accepts_timeout_status(self) -> None:
        payload = {
            "run_id": "demo",
            "role": "planner",
            "attempt": 1,
            "started_at": "2026-07-02T00:00:00Z",
            "finished_at": "2026-07-02T00:00:01Z",
            "exit_code": 124,
            "status": "timeout",
            "prompt_path": "prompt.md",
            "stdout_path": "stdout.log",
            "stderr_path": "stderr.log",
            "output_json_path": "planner-output.json",
            "diff_patch_path": "",
            "verify_log_paths": [],
        }
        validate_agent_attempt_payload(payload)

    def test_read_write_json_file_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "payload.json"
            write_json_file(path, {"ok": True})
            self.assertEqual(read_json_file(path), {"ok": True})

    def test_run_dir_for_uses_repo_root_codex_loop_runs(self) -> None:
        root = Path("/tmp/repo")
        self.assertEqual(run_dir_for(root, "demo"), root / ".codex" / "loop-runs" / "demo")
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.harness_loop_contracts'`.

- [ ] **Step 3: Implement contract validators**

Create `scripts/harness_loop_contracts.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


POLICY_ALIASES = {
    "demand-development": "demand_development",
    "demand_development": "demand_development",
    "autonomous-knowledge": "autonomous_knowledge",
    "autonomous_knowledge": "autonomous_knowledge",
}
ALLOWED_POLICIES = {"demand_development", "autonomous_knowledge"}
ALLOWED_PHASES = {
    "preflight",
    "planned",
    "generating",
    "verifying",
    "evaluating",
    "repair_needed",
    "artifact_hygiene",
    "cleanup",
    "passed_waiting_human_merge",
    "planning",
    "committed",
    "stopped_no_action",
    "stopped_budget",
    "stopped_blocked",
}
ALLOWED_LAST_RESULTS = {"pass", "fail", "blocked", "none"}
ALLOWED_TASK_KINDS = {
    "registered_task",
    "candidate_task",
    "task_contract_only",
    "autonomous_implementation_task",
}
ALLOWED_GENERATOR_STATUSES = {"implemented", "repaired", "blocked", "failed"}
ALLOWED_AGENT_ROLES = {"planner", "generator", "evaluator"}
ALLOWED_AGENT_STATUSES = {"pass", "fail", "blocked", "timeout", "invalid_json"}


def normalize_policy_id(value: str) -> str:
    try:
        return POLICY_ALIASES[value]
    except KeyError as exc:
        raise ValueError(f"invalid policy: {value}") from exc


def default_limits() -> dict[str, int]:
    return {
        "max_tasks_per_run": 3,
        "max_generator_attempts_per_task": 2,
        "max_eval_attempts_per_task": 3,
        "max_wall_time_minutes": 60,
        "max_no_action_rounds": 1,
        "agent_timeout_minutes": 30,
        "cleanup_retention_days": 7,
    }


def run_dir_for(repo_root: Path | str, run_id: str) -> Path:
    return Path(repo_root) / ".codex" / "loop-runs" / run_id


def read_json_file(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def write_json_file(path: Path | str, payload: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), indent=2) + "\n", encoding="utf-8")
    return target


def _require_keys(payload: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"{label} missing required keys: {', '.join(sorted(missing))}")


def _require_list(payload: Mapping[str, Any], key: str, label: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{label}.{key} must be a list")


def validate_run_payload(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        {
            "run_id",
            "policy",
            "phase",
            "task_id",
            "domain",
            "branch",
            "worktree",
            "baseline_dirty_paths",
            "allowed_paths",
            "denylist_paths",
            "attempts",
            "limits",
            "last_result",
            "next_action",
            "attempt_history",
            "cleanup",
        },
        "run",
    )
    if payload["policy"] not in ALLOWED_POLICIES:
        raise ValueError(f"invalid run policy: {payload['policy']}")
    if payload["phase"] not in ALLOWED_PHASES:
        raise ValueError(f"invalid run phase: {payload['phase']}")
    if payload["last_result"] not in ALLOWED_LAST_RESULTS:
        raise ValueError(f"invalid run last_result: {payload['last_result']}")
    for key in ("baseline_dirty_paths", "allowed_paths", "denylist_paths", "attempt_history"):
        _require_list(payload, key, "run")
    if not isinstance(payload.get("attempts"), Mapping):
        raise ValueError("run.attempts must be an object")
    if not isinstance(payload.get("limits"), Mapping):
        raise ValueError("run.limits must be an object")
    if not isinstance(payload.get("cleanup"), Mapping):
        raise ValueError("run.cleanup must be an object")


def validate_planner_output_payload(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        {
            "task_id",
            "policy",
            "task_kind",
            "title",
            "goal",
            "non_goals",
            "allowed_paths",
            "denylist_paths",
            "verify_commands",
            "evaluator_scenarios_path",
            "stop_conditions",
            "next_planning_hint",
        },
        "planner-output",
    )
    if payload["policy"] not in ALLOWED_POLICIES:
        raise ValueError(f"invalid planner-output policy: {payload['policy']}")
    if payload["task_kind"] not in ALLOWED_TASK_KINDS:
        raise ValueError(f"invalid planner-output task_kind: {payload['task_kind']}")
    for key in ("non_goals", "allowed_paths", "denylist_paths", "verify_commands", "stop_conditions"):
        _require_list(payload, key, "planner-output")


def validate_generator_result_payload(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        {
            "task_id",
            "status",
            "changed_paths",
            "commit",
            "verify_commands",
            "verify_results",
            "artifacts",
            "cleanup_required",
            "notes",
        },
        "generator-result",
    )
    if payload["status"] not in ALLOWED_GENERATOR_STATUSES:
        raise ValueError(f"invalid generator-result status: {payload['status']}")
    for key in ("changed_paths", "verify_commands", "verify_results", "artifacts"):
        _require_list(payload, key, "generator-result")
    if not isinstance(payload["cleanup_required"], bool):
        raise ValueError("generator-result.cleanup_required must be a boolean")


def validate_agent_attempt_payload(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        {
            "run_id",
            "role",
            "attempt",
            "started_at",
            "finished_at",
            "exit_code",
            "status",
            "prompt_path",
            "stdout_path",
            "stderr_path",
            "output_json_path",
            "diff_patch_path",
            "verify_log_paths",
        },
        "agent-attempt",
    )
    if payload["role"] not in ALLOWED_AGENT_ROLES:
        raise ValueError(f"invalid agent role: {payload['role']}")
    if payload["status"] not in ALLOWED_AGENT_STATUSES:
        raise ValueError(f"invalid agent status: {payload['status']}")
    if not isinstance(payload["attempt"], int) or payload["attempt"] < 1:
        raise ValueError("agent-attempt.attempt must be a positive integer")
    if not isinstance(payload["exit_code"], int):
        raise ValueError("agent-attempt.exit_code must be an integer")
    _require_list(payload, "verify_log_paths", "agent-attempt")
```

- [ ] **Step 4: Run contract tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts -v
```

Expected: PASS.

- [ ] **Step 5: Commit contracts**

```bash
git add scripts/harness_loop_contracts.py scripts/tests/test_harness_loop_contracts.py
git commit -m "feat(harness): add loop contract validators"
```

## Task 3: Add Preflight And Run State CLI

**Files:**
- Create: `scripts/harness_loop_orchestrator.py`
- Create: `scripts/tests/test_harness_loop_orchestrator.py`

- [ ] **Step 1: Write failing preflight tests**

Create `scripts/tests/test_harness_loop_orchestrator.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.harness_loop_contracts import read_json_file
from scripts.harness_loop_orchestrator import (
    confirm_preflight,
    create_preflight_run,
    load_run,
    status_for_run,
)


class HarnessLoopOrchestratorTests(unittest.TestCase):
    def test_create_preflight_run_writes_run_and_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = create_preflight_run(
                repo_root=root,
                run_id="demo-run",
                mode="demand-development",
                requirement="Build a demo loop.",
                confirm=False,
            )
            self.assertEqual(run_dir, root / ".codex" / "loop-runs" / "demo-run")
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["policy"], "demand_development")
            self.assertEqual(run["phase"], "preflight")
            self.assertEqual(run["next_action"], "await_preflight_confirmation")
            preflight = (run_dir / "preflight.md").read_text(encoding="utf-8")
            self.assertIn("Build a demo loop.", preflight)
            self.assertIn("Fallback Questionnaire", preflight)

    def test_confirm_preflight_moves_run_to_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_preflight_run(
                repo_root=root,
                run_id="demo-run",
                mode="demand-development",
                requirement="Build a demo loop.",
                confirm=False,
            )
            confirm_preflight(root, "demo-run")
            run = load_run(root, "demo-run")
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")

    def test_create_preflight_with_confirm_skips_wait_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_preflight_run(
                repo_root=root,
                run_id="demo-run",
                mode="demand-development",
                requirement="Build a demo loop.",
                confirm=True,
            )
            run = load_run(root, "demo-run")
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")

    def test_status_for_run_reports_phase_and_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_preflight_run(
                repo_root=root,
                run_id="demo-run",
                mode="demand-development",
                requirement="Build a demo loop.",
                confirm=False,
            )
            status = status_for_run(root, "demo-run")
            self.assertEqual(status["run_id"], "demo-run")
            self.assertEqual(status["phase"], "preflight")
            self.assertEqual(status["next_action"], "await_preflight_confirmation")
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
```

Expected: FAIL with missing `scripts.harness_loop_orchestrator`.

- [ ] **Step 3: Implement preflight run state functions and CLI skeleton**

Create `scripts/harness_loop_orchestrator.py` with:

```python
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

try:
    from scripts.harness_loop_contracts import (
        default_limits,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
        validate_run_payload,
        write_json_file,
    )
except ModuleNotFoundError:  # pragma: no cover
    from harness_loop_contracts import (
        default_limits,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
        validate_run_payload,
        write_json_file,
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _current_branch(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = result.stdout.strip()
    return branch or "unknown"


def _baseline_dirty_paths(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _preflight_markdown(run_id: str, mode: str, requirement: str) -> str:
    questions = [
        "1. 本次 loop 的目标产物是什么？",
        "2. 这是 demand_development、autonomous_knowledge，还是需要由 Planner 判断？",
        "3. 哪些路径允许修改，哪些路径必须禁止修改？",
        "4. 是否允许联网、抓取外部内容、调用 GitHub/API、重启本地服务？",
        "5. 是否允许自动 commit？是否允许合入 main？",
        "6. 最多允许多少任务、多少修复轮次、多少 evaluator 轮次、多少运行时间？",
        "7. 遇到鉴权、网络失败、脏工作区、非 allowlist 路径、代码改动需求时如何继续、停止或升级？",
        "8. 用户是否明确说“讨论清楚 / 确认进入 loop”？",
    ]
    return "\n".join(
        [
            f"# Loop Preflight: {run_id}",
            "",
            f"- mode: {mode}",
            f"- created_at: {_timestamp()}",
            "",
            "## Requirement",
            "",
            requirement,
            "",
            "## Fallback Questionnaire",
            "",
            *questions,
            "",
        ]
    )


def load_run(repo_root: Path | str, run_id: str) -> dict[str, Any]:
    payload = read_json_file(run_dir_for(repo_root, run_id) / "run.json")
    validate_run_payload(payload)
    return payload


def save_run(repo_root: Path | str, run_id: str, payload: dict[str, Any]) -> Path:
    validate_run_payload(payload)
    return write_json_file(run_dir_for(repo_root, run_id) / "run.json", payload)


def create_preflight_run(
    repo_root: Path | str,
    run_id: str,
    mode: str,
    requirement: str,
    *,
    confirm: bool = False,
) -> Path:
    root = Path(repo_root)
    policy = normalize_policy_id(mode)
    run_dir = run_dir_for(root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    phase = "planned" if confirm else "preflight"
    next_action = "run_planner" if confirm else "await_preflight_confirmation"
    payload: dict[str, Any] = {
        "run_id": run_id,
        "policy": policy,
        "phase": phase,
        "task_id": "",
        "domain": "",
        "branch": _current_branch(root),
        "worktree": str(root.resolve()),
        "baseline_dirty_paths": _baseline_dirty_paths(root),
        "allowed_paths": [],
        "denylist_paths": [],
        "attempts": {
            "planner": 0,
            "generator": 0,
            "evaluator": 0,
            "artifact_hygiene": 0,
            "cleanup": 0,
        },
        "limits": default_limits(),
        "last_result": "none",
        "next_action": next_action,
        "attempt_history": [],
        "cleanup": {
            "worktrees_removed": [],
            "processes_stopped": [],
            "retained_artifacts": [],
        },
    }
    save_run(root, run_id, payload)
    (run_dir / "preflight.md").write_text(
        _preflight_markdown(run_id, policy, requirement),
        encoding="utf-8",
    )
    return run_dir


def confirm_preflight(repo_root: Path | str, run_id: str) -> Path:
    payload = load_run(repo_root, run_id)
    payload["phase"] = "planned"
    payload["next_action"] = "run_planner"
    return save_run(repo_root, run_id, payload)


def status_for_run(repo_root: Path | str, run_id: str) -> dict[str, Any]:
    payload = load_run(repo_root, run_id)
    return {
        "run_id": payload["run_id"],
        "policy": payload["policy"],
        "phase": payload["phase"],
        "next_action": payload["next_action"],
        "task_id": payload["task_id"],
    }


def _cmd_preflight(args: argparse.Namespace) -> int:
    run_dir = create_preflight_run(
        args.repo_root,
        args.run_id,
        args.mode,
        args.requirement,
        confirm=args.confirm,
    )
    print(run_dir)
    return 0


def _cmd_confirm_preflight(args: argparse.Namespace) -> int:
    print(confirm_preflight(args.repo_root, args.run_id))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    import json

    print(json.dumps(status_for_run(args.repo_root, args.run_id), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    preflight = subcommands.add_parser("preflight")
    preflight.add_argument("--repo-root", default=".")
    preflight.add_argument("--mode", required=True)
    preflight.add_argument("--requirement", required=True)
    preflight.add_argument("--run-id", required=True)
    preflight.add_argument("--confirm", action="store_true")
    preflight.set_defaults(func=_cmd_preflight)

    confirm = subcommands.add_parser("confirm-preflight")
    confirm.add_argument("--repo-root", default=".")
    confirm.add_argument("--run-id", required=True)
    confirm.set_defaults(func=_cmd_confirm_preflight)

    status = subcommands.add_parser("status")
    status.add_argument("--repo-root", default=".")
    status.add_argument("--run-id", required=True)
    status.set_defaults(func=_cmd_status)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run preflight tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_orchestrator -v
```

Expected: PASS.

- [ ] **Step 5: Smoke test CLI preflight**

Run:

```bash
python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement "Smoke preflight" --run-id smoke-preflight --confirm
python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id smoke-preflight
```

Expected: status JSON includes `"phase": "planned"` and `"next_action": "run_planner"`.

- [ ] **Step 6: Commit preflight CLI**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py .codex/loop-runs/smoke-preflight
git commit -m "feat(harness): add loop preflight state"
```

If `.codex/loop-runs/smoke-preflight` contains environment-specific dirty paths that should not be committed, remove the smoke directory before committing and commit only source/test files.

## Task 4: Add Codex Agent Wrapper

**Files:**
- Create: `scripts/harness_loop_agents.py`
- Create: `scripts/tests/test_harness_loop_agents.py`
- Modify: `scripts/harness_loop_orchestrator.py`

- [ ] **Step 1: Write failing agent wrapper tests**

Create `scripts/tests/test_harness_loop_agents.py`:

```python
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.harness_loop_agents import (
    build_codex_exec_command,
    codex_exec_capabilities,
    run_codex_prompt,
)


class HarnessLoopAgentsTests(unittest.TestCase):
    def test_codex_exec_capabilities_detects_supported_flags(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["codex", "exec", "--help"],
            returncode=0,
            stdout="usage: codex exec --json --output-last-message --cd",
            stderr="",
        )
        with patch("subprocess.run", return_value=completed):
            capabilities = codex_exec_capabilities()
        self.assertTrue(capabilities["json"])
        self.assertTrue(capabilities["output_last_message"])

    def test_build_codex_exec_command_uses_output_last_message_when_supported(self) -> None:
        command = build_codex_exec_command(
            repo_root=Path("/tmp/repo"),
            output_message_path=Path("/tmp/repo/out.json"),
            capabilities={"json": True, "output_last_message": True},
        )
        self.assertIn("--output-last-message", command)
        self.assertIn("/tmp/repo/out.json", command)

    def test_run_codex_prompt_writes_attempt_logs_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            prompt = run_dir / "prompt.md"
            prompt.write_text("Do work", encoding="utf-8")
            completed = subprocess.CompletedProcess(
                args=["codex"],
                returncode=2,
                stdout="",
                stderr="boom",
            )
            with patch("subprocess.run", return_value=completed), patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": False, "output_last_message": False},
            ):
                result = run_codex_prompt(
                    role="planner",
                    run_id="demo",
                    repo_root=Path(tmp),
                    run_dir=run_dir,
                    prompt_path=prompt,
                    output_json_path=run_dir / "planner-output.json",
                    attempt=1,
                    timeout_seconds=5,
                )
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["exit_code"], 2)
        self.assertTrue(Path(result["stderr_path"]).exists())
        self.assertIn("boom", Path(result["stderr_path"]).read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_agents -v
```

Expected: FAIL with missing `scripts.harness_loop_agents`.

- [ ] **Step 3: Implement agent wrapper**

Create `scripts/harness_loop_agents.py`:

```python
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.harness_loop_contracts import validate_agent_attempt_payload, write_json_file
except ModuleNotFoundError:  # pragma: no cover
    from harness_loop_contracts import validate_agent_attempt_payload, write_json_file


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def codex_exec_capabilities() -> dict[str, bool]:
    result = subprocess.run(
        ["codex", "exec", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    help_text = f"{result.stdout}\n{result.stderr}"
    return {
        "json": "--json" in help_text,
        "output_last_message": "--output-last-message" in help_text,
    }


def build_codex_exec_command(
    repo_root: Path,
    output_message_path: Path,
    capabilities: Mapping[str, bool],
) -> list[str]:
    command = [
        "codex",
        "-a",
        "never",
        "exec",
        "--cd",
        str(repo_root),
        "--color",
        "never",
    ]
    if capabilities.get("json"):
        command.append("--json")
    if capabilities.get("output_last_message"):
        command.extend(["--output-last-message", str(output_message_path)])
    command.append("-")
    return command


def run_codex_prompt(
    *,
    role: str,
    run_id: str,
    repo_root: Path,
    run_dir: Path,
    prompt_path: Path,
    output_json_path: Path,
    attempt: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    capabilities = codex_exec_capabilities()
    output_message_path = run_dir / f"{role}-message-attempt-{attempt}.json"
    command = build_codex_exec_command(repo_root, output_message_path, capabilities)
    stdout_path = run_dir / f"{role}-attempt-{attempt}.stdout.log"
    stderr_path = run_dir / f"{role}-attempt-{attempt}.stderr.log"
    started_at = _timestamp()
    status = "fail"
    exit_code = 1
    stdout = ""
    stderr = ""
    try:
        result = subprocess.run(
            command,
            input=prompt_path.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        status = "pass" if result.returncode == 0 and output_json_path.exists() else "fail"
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else "codex exec timed out"
        status = "timeout"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    payload: dict[str, Any] = {
        "run_id": run_id,
        "role": role,
        "attempt": attempt,
        "started_at": started_at,
        "finished_at": _timestamp(),
        "exit_code": exit_code,
        "status": status,
        "prompt_path": str(prompt_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "output_json_path": str(output_json_path),
        "diff_patch_path": "",
        "verify_log_paths": [],
    }
    validate_agent_attempt_payload(payload)
    write_json_file(run_dir / f"{role}-attempt-{attempt}.json", payload)
    return payload
```

- [ ] **Step 4: Run agent wrapper tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_agents -v
```

Expected: PASS.

- [ ] **Step 5: Commit agent wrapper**

```bash
git add scripts/harness_loop_agents.py scripts/tests/test_harness_loop_agents.py
git commit -m "feat(harness): add loop codex agent wrapper"
```

## Task 5: Add Planner And Generator Loop Steps

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`

- [ ] **Step 1: Extend orchestrator tests for fake plan/generate**

Append tests to `HarnessLoopOrchestratorTests`:

```python
    def test_fake_plan_writes_valid_planner_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_preflight_run(root, "demo-run", "demand-development", "Build demo", confirm=True)
            from scripts.harness_loop_orchestrator import run_planner

            run_planner(root, "demo-run", driver="fake")
            run_dir = root / ".codex" / "loop-runs" / "demo-run"
            planner_output = json.loads((run_dir / "planner-output.json").read_text(encoding="utf-8"))
            self.assertEqual(planner_output["policy"], "demand_development")
            self.assertEqual(planner_output["task_kind"], "registered_task")
            run = load_run(root, "demo-run")
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")

    def test_fake_generate_writes_valid_generator_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_preflight_run(root, "demo-run", "demand-development", "Build demo", confirm=True)
            from scripts.harness_loop_orchestrator import run_generator, run_planner

            run_planner(root, "demo-run", driver="fake")
            run_generator(root, "demo-run", driver="fake")
            run_dir = root / ".codex" / "loop-runs" / "demo-run"
            generator_result = json.loads((run_dir / "generator-result.json").read_text(encoding="utf-8"))
            self.assertEqual(generator_result["status"], "implemented")
            run = load_run(root, "demo-run")
            self.assertEqual(run["phase"], "evaluating")
            self.assertEqual(run["next_action"], "run_evaluator")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
```

Expected: FAIL with missing `run_planner` and `run_generator`.

- [ ] **Step 3: Implement fake and codex-exec plan/generate functions**

Modify `scripts/harness_loop_orchestrator.py`:

```python
try:
    from scripts.harness_loop_contracts import (
        default_limits,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
        validate_generator_result_payload,
        validate_planner_output_payload,
        validate_run_payload,
        write_json_file,
    )
    from scripts.harness_loop_agents import run_codex_prompt
except ModuleNotFoundError:  # pragma: no cover
    from harness_loop_contracts import (
        default_limits,
        normalize_policy_id,
        read_json_file,
        run_dir_for,
        validate_generator_result_payload,
        validate_planner_output_payload,
        validate_run_payload,
        write_json_file,
    )
    from harness_loop_agents import run_codex_prompt
```

Add:

```python
def _task_id_for_run(run_id: str) -> str:
    return f"{run_id}-task"


def _planner_prompt(requirement: str, run_id: str) -> str:
    return "\n".join(
        [
            "Planner agent task.",
            "Write .codex/loop-runs/{run_id}/planner-output.json only.",
            "Policy: demand_development.",
            f"Requirement: {requirement}",
            "",
        ]
    )


def _generator_prompt(run_id: str) -> str:
    return "\n".join(
        [
            "Generator agent task.",
            f"Read .codex/loop-runs/{run_id}/planner-output.json.",
            f"Write .codex/loop-runs/{run_id}/generator-result.json.",
            "Do not mark final completion; evaluator decides.",
            "",
        ]
    )


def _read_requirement(run_dir: Path) -> str:
    preflight_path = run_dir / "preflight.md"
    text = preflight_path.read_text(encoding="utf-8")
    marker = "## Requirement"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].split("##", 1)[0].strip()


def run_planner(repo_root: Path | str, run_id: str, *, driver: str) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    if run["phase"] == "preflight":
        raise RuntimeError("preflight must be confirmed before planning")
    run_dir = run_dir_for(root, run_id)
    task_id = run["task_id"] or _task_id_for_run(run_id)
    output_path = run_dir / "planner-output.json"
    if driver == "fake":
        payload = {
            "task_id": task_id,
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": f"Loop task {run_id}",
            "goal": _read_requirement(run_dir),
            "non_goals": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "verify_commands": [],
            "evaluator_scenarios_path": "",
            "stop_conditions": ["passed_waiting_human_merge"],
            "next_planning_hint": "",
        }
        validate_planner_output_payload(payload)
        write_json_file(output_path, payload)
    elif driver == "codex-exec":
        prompt_path = run_dir / "planner-prompt.md"
        prompt_path.write_text(_planner_prompt(_read_requirement(run_dir), run_id), encoding="utf-8")
        run_codex_prompt(
            role="planner",
            run_id=run_id,
            repo_root=root,
            run_dir=run_dir,
            prompt_path=prompt_path,
            output_json_path=output_path,
            attempt=int(run["attempts"]["planner"]) + 1,
            timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
        )
        validate_planner_output_payload(read_json_file(output_path))
    else:
        raise ValueError(f"unsupported planner driver: {driver}")
    run["task_id"] = task_id
    run["phase"] = "generating"
    run["next_action"] = "run_generator"
    run["attempts"]["planner"] = int(run["attempts"]["planner"]) + 1
    save_run(root, run_id, run)
    return output_path


def run_generator(repo_root: Path | str, run_id: str, *, driver: str) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    run_dir = run_dir_for(root, run_id)
    planner_output = read_json_file(run_dir / "planner-output.json")
    validate_planner_output_payload(planner_output)
    output_path = run_dir / "generator-result.json"
    if driver == "fake":
        payload = {
            "task_id": planner_output["task_id"],
            "status": "implemented",
            "changed_paths": [],
            "commit": "",
            "verify_commands": planner_output["verify_commands"],
            "verify_results": [],
            "artifacts": [],
            "cleanup_required": False,
            "notes": "fake generator completed",
        }
        validate_generator_result_payload(payload)
        write_json_file(output_path, payload)
    elif driver == "codex-exec":
        prompt_path = run_dir / "generator-prompt.md"
        prompt_path.write_text(_generator_prompt(run_id), encoding="utf-8")
        run_codex_prompt(
            role="generator",
            run_id=run_id,
            repo_root=root,
            run_dir=run_dir,
            prompt_path=prompt_path,
            output_json_path=output_path,
            attempt=int(run["attempts"]["generator"]) + 1,
            timeout_seconds=int(run["limits"]["agent_timeout_minutes"]) * 60,
        )
        validate_generator_result_payload(read_json_file(output_path))
    else:
        raise ValueError(f"unsupported generator driver: {driver}")
    run["phase"] = "evaluating"
    run["next_action"] = "run_evaluator"
    run["attempts"]["generator"] = int(run["attempts"]["generator"]) + 1
    save_run(root, run_id, run)
    return output_path
```

Extend `build_parser()` with `plan` and `generate` subcommands and handlers that call these functions.

- [ ] **Step 4: Run orchestrator tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
```

Expected: PASS.

- [ ] **Step 5: Smoke test fake plan/generate**

Run:

```bash
python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement "Smoke plan generate" --run-id smoke-plan-generate --confirm
python3 scripts/harness_loop_orchestrator.py plan --repo-root . --run-id smoke-plan-generate --driver fake
python3 scripts/harness_loop_orchestrator.py generate --repo-root . --run-id smoke-plan-generate --driver fake
python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id smoke-plan-generate
```

Expected: status JSON includes `"phase": "evaluating"` and `"next_action": "run_evaluator"`.

- [ ] **Step 6: Commit planner/generator skeleton**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py
git commit -m "feat(harness): add loop planner generator skeleton"
```

Remove `.codex/loop-runs/smoke-plan-generate` before committing unless it is intentionally kept as evidence.

## Task 6: Add Evaluator Integration And Human Merge Gate

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`
- Create: `docs/harness/planner-generator-evaluator-loop.md`

- [ ] **Step 1: Add evaluator state tests**

Append tests:

```python
    def test_fake_evaluate_moves_to_human_merge_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_preflight_run(root, "demo-run", "demand-development", "Build demo", confirm=True)
            from scripts.harness_loop_orchestrator import run_evaluator, run_generator, run_planner

            run_planner(root, "demo-run", driver="fake")
            run_generator(root, "demo-run", driver="fake")
            run_evaluator(root, "demo-run", driver="fake", max_attempts=2)
            run = load_run(root, "demo-run")
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["last_result"], "pass")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")

    def test_run_refuses_unconfirmed_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_preflight_run(root, "demo-run", "demand-development", "Build demo", confirm=False)
            from scripts.harness_loop_orchestrator import run_loop

            with self.assertRaises(RuntimeError):
                run_loop(
                    root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                )
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
```

Expected: FAIL with missing `run_evaluator` and `run_loop`.

- [ ] **Step 3: Implement evaluator integration**

Add to `scripts/harness_loop_orchestrator.py`:

```python
def _latest_fake_evaluator_result(repo_root: Path, task_id: str) -> dict[str, Any]:
    task_root = repo_root / ".codex" / "evaluations" / "tasks" / task_id
    candidates = sorted(task_root.glob("fake-attempt-*/result.json"))
    if not candidates:
        raise FileNotFoundError(f"no fake evaluator result for {task_id}")
    return read_json_file(candidates[-1])


def run_evaluator(
    repo_root: Path | str,
    run_id: str,
    *,
    driver: str,
    max_attempts: int,
) -> Path:
    root = Path(repo_root)
    run = load_run(root, run_id)
    task_id = run["task_id"]
    if not task_id:
        raise RuntimeError("run has no task_id")
    if driver == "fake":
        result = subprocess.run(
            [
                "python3",
                "scripts/harness_evaluator_orchestrator.py",
                "run-task-loop",
                "--driver",
                "fake",
                "--task-id",
                task_id,
                "--max-attempts",
                str(max_attempts),
                "--repo-root",
                str(root),
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            run["phase"] = "repair_needed"
            run["last_result"] = "fail"
            run["next_action"] = "repair_from_evaluator_findings"
        else:
            run["phase"] = "passed_waiting_human_merge"
            run["last_result"] = "pass"
            run["next_action"] = "await_human_merge_confirmation"
        evaluator_result = _latest_fake_evaluator_result(root, task_id)
    elif driver == "codex-exec":
        result = subprocess.run(
            [
                "python3",
                "scripts/harness_evaluator_orchestrator.py",
                "run-task-auto-gate",
                "--driver",
                "codex-exec",
                "--task-id",
                task_id,
                "--max-attempts",
                str(max_attempts),
                "--repo-root",
                str(root),
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=False,
        )
        run["phase"] = "passed_waiting_human_merge" if result.returncode == 0 else "repair_needed"
        run["last_result"] = "pass" if result.returncode == 0 else "fail"
        run["next_action"] = "await_human_merge_confirmation" if result.returncode == 0 else "repair_from_evaluator_findings"
        evaluator_result = {"status": run["last_result"], "stdout": result.stdout, "stderr": result.stderr}
    else:
        raise ValueError(f"unsupported evaluator driver: {driver}")
    run_dir = run_dir_for(root, run_id)
    write_json_file(run_dir / "evaluator-result.json", evaluator_result)
    run["attempts"]["evaluator"] = int(run["attempts"]["evaluator"]) + 1
    save_run(root, run_id, run)
    return run_dir / "evaluator-result.json"


def run_loop(
    repo_root: Path | str,
    run_id: str,
    *,
    planner_driver: str,
    generator_driver: str,
    evaluator_driver: str,
    max_eval_attempts: int,
) -> dict[str, Any]:
    run = load_run(repo_root, run_id)
    if run["phase"] == "preflight":
        raise RuntimeError("preflight must be confirmed before running the loop")
    if run["phase"] == "planned":
        run_planner(repo_root, run_id, driver=planner_driver)
    run = load_run(repo_root, run_id)
    if run["phase"] == "generating":
        run_generator(repo_root, run_id, driver=generator_driver)
    run = load_run(repo_root, run_id)
    if run["phase"] == "evaluating":
        run_evaluator(repo_root, run_id, driver=evaluator_driver, max_attempts=max_eval_attempts)
    return status_for_run(repo_root, run_id)
```

Extend parser with:

```text
evaluate --run-id --driver fake|codex-exec --max-attempts
run --run-id --planner-driver fake|codex-exec --generator-driver fake|codex-exec --evaluator-driver fake|codex-exec --max-eval-attempts
```

- [ ] **Step 4: Add minimal scenario metadata for fake evaluator tests**

In fake planner tests or fake planner implementation, ensure `docs/harness/evaluator-scenarios/<task-id>.json` exists under the test temp root before `run-task-loop --driver fake` runs. Use this scenario:

```json
{
  "task_id": "demo-run-task",
  "must_simulate": true,
  "user_scenarios": [
    {
      "scenario_id": "LOOP-FAKE-01",
      "user_goal": "Validate fake loop handoff.",
      "prerequisites": [],
      "entrypoint": "python3 -c 'print(\"ok\")'",
      "steps": ["Run the no-op command."],
      "expected_outcomes": ["The evaluator can produce a pass result."],
      "failure_signals": ["No scenario result is recorded."],
      "cleanup": [],
      "automation_hint": "shell"
    }
  ]
}
```

Also ensure fake planner writes the same `task_id`.

- [ ] **Step 5: Run evaluator integration tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
```

Expected: PASS.

- [ ] **Step 6: Smoke test full fake loop**

Run:

```bash
python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement "Phase 1 full smoke" --run-id smoke-phase-1 --confirm
python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id smoke-phase-1 --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2
python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id smoke-phase-1
```

Expected: status JSON includes:

```json
{
  "phase": "passed_waiting_human_merge",
  "next_action": "await_human_merge_confirmation"
}
```

- [ ] **Step 7: Write Phase 1 runbook**

Create `docs/harness/planner-generator-evaluator-loop.md`:

```markdown
# Planner Generator Evaluator Loop

## Phase 1 Scope

Phase 1 supports demand-development loops only:

1. Create a preflight run.
2. Confirm preflight after the user says the goal, constraints, and stop conditions are clear.
3. Run Planner and Generator with `fake` or `codex-exec` drivers.
4. Run evaluator through the existing harness.
5. Stop at `passed_waiting_human_merge`.

## Commands

```bash
python3 scripts/harness_loop_orchestrator.py preflight \
  --repo-root . \
  --mode demand-development \
  --requirement "..." \
  --run-id <run-id>

python3 scripts/harness_loop_orchestrator.py confirm-preflight \
  --repo-root . \
  --run-id <run-id>

python3 scripts/harness_loop_orchestrator.py run \
  --repo-root . \
  --run-id <run-id> \
  --planner-driver fake \
  --generator-driver fake \
  --evaluator-driver fake \
  --max-eval-attempts 2
```

Use `codex-exec` drivers only after verifying local `codex exec --help` support. The file outputs remain the source of truth even when stdout is noisy.

## Human Gate

Demand loops never merge to `main`. A pass stops at:

```json
{
  "phase": "passed_waiting_human_merge",
  "next_action": "await_human_merge_confirmation"
}
```
```

- [ ] **Step 8: Run full Phase 1 verification**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v
python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement "Phase 1 verification smoke" --run-id smoke-phase-1-verify --confirm
python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id smoke-phase-1-verify --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2
```

Expected: tests pass and the smoke loop stops at `passed_waiting_human_merge`.

- [ ] **Step 9: Commit evaluator integration and docs**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py docs/harness/planner-generator-evaluator-loop.md
git commit -m "feat(harness): connect loop evaluator gate"
```

Do not stage `.codex/loop-runs/smoke-*` unless the artifacts are intentionally required as evidence.

## Task 7: Finalize Task Status And Evidence

**Files:**
- Modify: `tasks.json`
- Modify: `progress.md`

- [ ] **Step 1: Run final verification**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v
python3 scripts/harness_loop_orchestrator.py preflight --repo-root . --mode demand-development --requirement "Phase 1 final smoke" --run-id smoke-phase-1-final --confirm
python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id smoke-phase-1-final --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2
python3 scripts/harness_loop_orchestrator.py status --repo-root . --run-id smoke-phase-1-final
```

Expected:

- unittest exits 0.
- smoke run exits 0.
- status reports `passed_waiting_human_merge`.

- [ ] **Step 2: Run task evaluator gate**

Run:

```bash
python3 scripts/harness_evaluator_orchestrator.py run-task-loop \
  --driver fake \
  --task-id planner-generator-evaluator-loop-phase-1-01 \
  --repo-root . \
  --max-attempts 2
```

Expected: exits 0 and writes `.codex/evaluations/tasks/planner-generator-evaluator-loop-phase-1-01/fake-attempt-2/result.json` with `"status": "pass"`.

- [ ] **Step 3: Mark task done**

Update the `planner-generator-evaluator-loop-phase-1-01` task in `tasks.json`:

```json
"status": "done"
```

- [ ] **Step 4: Append progress entry**

Add a top entry to `progress.md`:

```markdown
## 2026-07-02 — Planner Generator Evaluator Loop Phase 1

- Implemented demand-development loop skeleton with preflight, contracts, fake/codex agent wrappers, evaluator handoff, and human merge gate.
- Verification:
  - `python3 -m unittest scripts.tests.test_harness_loop_contracts scripts.tests.test_harness_loop_agents scripts.tests.test_harness_loop_orchestrator -v`
  - `python3 scripts/harness_loop_orchestrator.py run --repo-root . --run-id smoke-phase-1-final --planner-driver fake --generator-driver fake --evaluator-driver fake --max-eval-attempts 2`
  - `python3 scripts/harness_evaluator_orchestrator.py run-task-loop --driver fake --task-id planner-generator-evaluator-loop-phase-1-01 --repo-root . --max-attempts 2`
```

- [ ] **Step 5: Commit final status**

```bash
git add tasks.json progress.md
git commit -m "chore(harness): record planner loop phase 1 completion"
```

## Self-Review Checklist

- [ ] Phase 1 does not implement autonomous knowledge behavior beyond policy validation fields.
- [ ] `preflight` refuses to run the loop until confirmed.
- [ ] `run.json`, `planner-output.json`, `generator-result.json`, and `agent-attempt.json` are schema-validated.
- [ ] Fake drivers allow deterministic tests without real Codex CLI calls.
- [ ] `codex-exec` wrapper probes supported output flags before adding them.
- [ ] Evaluator pass stops at `passed_waiting_human_merge`, not full completion or merge.
- [ ] No `.codex/loop-runs/smoke-*` artifacts are committed unless explicitly intended.
