# Demand Multi-Task Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement demand-development parent/child multi-task loops and make Loop Dashboard display the parent requirement, child task queue, agent actions, acceptance evidence, diagnostics, and E2E results.

**Architecture:** Extend the existing harness without replacing the single-run flow. `harness_loop_contracts.py` owns schema validation, `harness_loop_orchestrator.py` owns parent/child state transitions and fake-driver E2E flows, and `apps/loop_dashboard/backend/loop_dashboard/store.py` aggregates parent/child run artifacts for the frontend. The frontend remains read-only and renders parent-centered details while preserving old single-run behavior.

**Tech Stack:** Python standard library, unittest, pytest, FastAPI TestClient, existing Loop Dashboard vanilla JS/CSS, existing `scripts/loop_dashboard_evaluator.py` for HTTP and Playwright browser checks.

---

## File Map

- Modify `scripts/harness_loop_contracts.py`
  - Add run-kind constants, parent/child phase validation, demand parent planner decision validation, and default demand multi-task limits.
- Modify `scripts/tests/test_harness_loop_contracts.py`
  - Unit tests for single compatibility, parent/child phase combinations, planner decision combinations, and invalid parent linkage.
- Modify `scripts/harness_loop_orchestrator.py`
  - Add demand parent/child helpers, event writer, accepted changed path handling, resume logic, dirty path gate, fake drivers, budget limits, task-contract writing, and `run-demand-multi` CLI.
- Modify `scripts/tests/test_harness_loop_orchestrator.py`
  - Integration and E2E non-UI tests for E2E-01, E2E-02, E2E-03, E2E-06, E2E-07, and E2E-09.
- Modify `tasks.json`
  - Register the parent implementation task so the harness task list records the demand multi-task loop work and verification entrypoint.
- Modify `apps/loop_dashboard/backend/loop_dashboard/store.py`
  - Add parent/child relationship indexing, relationship diagnostics, structured event parsing, parent detail aggregation, path traversal protection, and single-run compatibility.
- Modify `apps/loop_dashboard/backend/tests/test_store.py`
  - Backend tests for parent/child aggregation, relationship conflict sorting, events precedence, redaction, path traversal, and old single runs.
- Modify `apps/loop_dashboard/backend/tests/test_api.py`
  - API shape tests for `GET /api/runs` and `GET /api/runs/{parent}`.
- Modify `apps/loop_dashboard/frontend/app.js`
  - Render parent run list entries, child summaries, reader summary, child queue, relationship diagnostics, and richer acceptance/events views.
- Modify `apps/loop_dashboard/frontend/styles.css`
  - Add responsive parent/child layout, readable child cards, desktop/mobile wrapping rules, and no-truncation styles.
- Modify `scripts/loop_dashboard_evaluator.py`
  - Add parent/child fixture scenario checks and browser/screenshot checks for E2E-04, E2E-05, E2E-08, E2E-10.

## Test Coverage Matrix

- E2E-01: `scripts/tests/test_harness_loop_orchestrator.py::HarnessLoopDemandMultiTaskTests::test_run_demand_multi_fake_completes_three_children_and_waits_for_human_merge`
- E2E-02: `scripts/tests/test_harness_loop_orchestrator.py::HarnessLoopDemandMultiTaskTests::test_run_demand_multi_repairs_same_failed_child_before_next_child`
- E2E-03: `scripts/tests/test_harness_loop_orchestrator.py::HarnessLoopDemandMultiTaskTests::test_run_demand_multi_blocks_on_unaccepted_dirty_path`
- E2E-04: `python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/demand-multi-task`
- E2E-05: `apps/loop_dashboard/backend/tests/test_store.py::test_single_run_without_run_kind_remains_top_level`
- E2E-06: `scripts/tests/test_harness_loop_orchestrator.py::HarnessLoopDemandMultiTaskTests::test_run_demand_multi_blocks_on_agent_timeout_invalid_json_and_missing_artifact`
- E2E-07: `scripts/tests/test_harness_loop_orchestrator.py::HarnessLoopDemandMultiTaskTests::test_run_demand_multi_resumes_current_child_without_repeating_passed_child`
- E2E-08: `apps/loop_dashboard/backend/tests/test_store.py::test_parent_child_relationship_conflicts_are_deduped_sorted_and_diagnosed`
- E2E-09: `scripts/tests/test_harness_loop_orchestrator.py::HarnessLoopDemandMultiTaskTests::test_run_demand_multi_planner_blocked_or_failed_creates_no_child`
- E2E-10: `apps/loop_dashboard/backend/tests/test_store.py::test_parent_child_relationship_rejects_path_traversal`

## Task 1: Register Parent Task

**Files:**
- Modify: `tasks.json`

- [ ] **Step 1: Add parent task entry**

Add this object to the `tasks` array in `tasks.json`:

```json
{
  "id": "demand-multi-task-loop-01",
  "title": "Implement demand-development multi-task loop",
  "description": "Implement parent/child demand-development loops, child task contracts, budget limits, resume behavior, dashboard aggregation, and browser evaluator coverage.",
  "status": "todo",
  "priority": "high",
  "blocked_by": "planner-generator-evaluator-loop-phase-3-01",
  "verify": "python3 -m unittest scripts.tests.test_harness_loop_contracts -v && python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v && PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests && python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/demand-multi-task-final && git diff --check",
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

- [ ] **Step 2: Validate task list JSON**

Run:

```bash
python3 -m json.tool tasks.json >/dev/null
```

Expected: PASS.

- [ ] **Step 3: Commit task registration**

```bash
git add tasks.json
git commit -m "chore(harness): register demand multi-task loop task"
```

## Task 2: Contracts And Schema Validation

**Files:**
- Modify: `scripts/harness_loop_contracts.py`
- Modify: `scripts/tests/test_harness_loop_contracts.py`

- [ ] **Step 1: Add failing tests for parent/child run validation**

Append these tests to `scripts/tests/test_harness_loop_contracts.py` inside `HarnessLoopContractsTests`:

```python
    def test_validate_run_payload_accepts_parent_and_child_run_kinds(self) -> None:
        parent = self._run_payload()
        parent.update(
            {
                "run_kind": "parent",
                "phase": "planning",
                "child_run_ids": ["demo-child-001"],
                "current_child_run_id": "demo-child-001",
                "backlog": [
                    {
                        "child_id": "child-001",
                        "title": "Child",
                        "description": "Do child work",
                        "status": "running",
                        "priority": 10,
                        "depends_on": [],
                        "evidence": [],
                    }
                ],
                "aggregate_acceptance": {
                    "total": 1,
                    "passed": 0,
                    "failed": 0,
                    "blocked": 0,
                    "pending": 1,
                    "user_decision_required": False,
                },
                "reader_summary": {
                    "purpose": "Build feature",
                    "current_progress": "Planning",
                    "next_step": "Run child",
                    "decision_needed": "No",
                },
                "accepted_changed_paths": [],
            }
        )
        validate_run_payload(parent)

        child = self._run_payload()
        child.update(
            {
                "run_kind": "child",
                "parent_run_id": "demo-parent",
                "child_index": 1,
                "phase": "passed",
                "reader_summary": {
                    "purpose": "Child",
                    "planner_action": "Planned child",
                    "generator_action": "Implemented child",
                    "evaluator_action": "Evaluated child",
                    "acceptance_result": "Passed",
                },
            }
        )
        validate_run_payload(child)

    def test_validate_run_payload_rejects_parent_child_phase_mismatch(self) -> None:
        parent = self._run_payload()
        parent.update(
            {
                "run_kind": "parent",
                "phase": "generating",
                "child_run_ids": [],
                "current_child_run_id": "",
                "backlog": [],
                "aggregate_acceptance": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "blocked": 0,
                    "pending": 0,
                    "user_decision_required": False,
                },
                "reader_summary": {
                    "purpose": "",
                    "current_progress": "",
                    "next_step": "",
                    "decision_needed": "",
                },
                "accepted_changed_paths": [],
            }
        )
        with self.assertRaisesRegex(ValueError, "parent phase"):
            validate_run_payload(parent)

        child = self._run_payload()
        child.update(
            {
                "run_kind": "child",
                "parent_run_id": "demo-parent",
                "child_index": 1,
                "phase": "passed_waiting_human_merge",
                "reader_summary": {
                    "purpose": "",
                    "planner_action": "",
                    "generator_action": "",
                    "evaluator_action": "",
                    "acceptance_result": "",
                },
            }
        )
        with self.assertRaisesRegex(ValueError, "child phase"):
            validate_run_payload(child)

    def test_validate_planner_output_payload_accepts_demand_parent_decisions(self) -> None:
        payload = self._planner_payload()
        payload.update(
            {
                "planner_decision": "next_child",
                "next_child_task": {
                    "child_id": "child-001",
                    "title": "Child one",
                    "description": "Implement child one",
                    "allowed_paths": ["scripts/"],
                    "denylist_paths": [".env"],
                    "verify_commands": ["python3 -m unittest scripts.tests.test_harness_loop_contracts -v"],
                    "scenario_commands": [],
                    "done_criteria": ["contract tests pass"],
                },
                "backlog": [],
                "blocked_reason": "",
                "done_criteria": [],
                "reader_summary": {
                    "purpose": "Build",
                    "current_progress": "Planning",
                    "next_step": "Run child",
                    "decision_needed": "No",
                },
                "decision_required": False,
            }
        )
        validate_planner_output_payload(payload)

        payload["planner_decision"] = "parent_done"
        payload["next_child_task"] = {}
        payload["done_criteria"] = ["all children passed"]
        validate_planner_output_payload(payload)

    def test_validate_planner_output_payload_rejects_invalid_decision_combinations(self) -> None:
        payload = self._planner_payload()
        payload.update(
            {
                "planner_decision": "next_child",
                "next_child_task": {},
                "backlog": [],
                "blocked_reason": "",
                "done_criteria": [],
                "reader_summary": {
                    "purpose": "",
                    "current_progress": "",
                    "next_step": "",
                    "decision_needed": "",
                },
                "decision_required": False,
            }
        )
        with self.assertRaisesRegex(ValueError, "next_child_task"):
            validate_planner_output_payload(payload)

        payload["planner_decision"] = "blocked"
        payload["blocked_reason"] = ""
        with self.assertRaisesRegex(ValueError, "blocked_reason"):
            validate_planner_output_payload(payload)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts.HarnessLoopContractsTests.test_validate_run_payload_accepts_parent_and_child_run_kinds scripts.tests.test_harness_loop_contracts.HarnessLoopContractsTests.test_validate_run_payload_rejects_parent_child_phase_mismatch scripts.tests.test_harness_loop_contracts.HarnessLoopContractsTests.test_validate_planner_output_payload_accepts_demand_parent_decisions scripts.tests.test_harness_loop_contracts.HarnessLoopContractsTests.test_validate_planner_output_payload_rejects_invalid_decision_combinations -v
```

Expected: FAIL because `run_kind`, child `passed`, and `planner_decision` are not supported yet.

- [ ] **Step 3: Implement contract validation**

In `scripts/harness_loop_contracts.py`, add constants near `ALLOWED_PHASES`:

```python
ALLOWED_RUN_KINDS = frozenset({"single", "parent", "child"})
PARENT_ONLY_PHASES = frozenset({"planning", "child_running", "passed_waiting_human_merge"})
CHILD_ONLY_PHASES = frozenset({"planned", "generating", "evaluating", "artifact_hygiene", "cleanup", "passed"})
SHARED_PARENT_CHILD_PHASES = frozenset({"repair_needed", "stopped_budget", "stopped_blocked"})
ALLOWED_PHASES = ALLOWED_PHASES | frozenset({"child_running", "passed"})
ALLOWED_DEMAND_PARENT_PLANNER_DECISIONS = frozenset({"next_child", "parent_done", "blocked", "failed"})
```

Add helper functions before `validate_run_payload`:

```python
def _optional_run_kind(payload: dict[str, Any]) -> str:
    run_kind = payload.get("run_kind", "single")
    if not isinstance(run_kind, str):
        raise ValueError("run_kind must be a string")
    if run_kind not in ALLOWED_RUN_KINDS:
        raise ValueError(f"unknown run_kind: {run_kind}")
    return run_kind


def _validate_run_kind_phase(run_kind: str, phase: str) -> None:
    if run_kind == "parent" and phase not in (PARENT_ONLY_PHASES | SHARED_PARENT_CHILD_PHASES):
        raise ValueError(f"parent phase is not allowed: {phase}")
    if run_kind == "child" and phase not in (CHILD_ONLY_PHASES | SHARED_PARENT_CHILD_PHASES):
        raise ValueError(f"child phase is not allowed: {phase}")


def _require_reader_summary(payload: dict[str, Any], keys: set[str]) -> None:
    summary = _require_object(payload.get("reader_summary"), "reader_summary")
    _require_keys(summary, keys, "reader_summary")
    for key in keys:
        _require_string(summary, key)


def _validate_parent_run_payload(payload: dict[str, Any]) -> None:
    for key in ("child_run_ids", "backlog", "accepted_changed_paths"):
        _require_list(payload, key)
    _require_string(payload, "current_child_run_id")
    aggregate = _require_object(payload.get("aggregate_acceptance"), "aggregate_acceptance")
    for key in ("total", "passed", "failed", "blocked", "pending"):
        _require_int(aggregate, key)
    _require_bool(aggregate, "user_decision_required")
    _require_reader_summary(payload, {"purpose", "current_progress", "next_step", "decision_needed"})


def _validate_child_run_payload(payload: dict[str, Any]) -> None:
    _require_string(payload, "parent_run_id")
    if not payload["parent_run_id"]:
        raise ValueError("child run requires parent_run_id")
    _require_int(payload, "child_index")
    _require_reader_summary(
        payload,
        {"purpose", "planner_action", "generator_action", "evaluator_action", "acceptance_result"},
    )
```

Inside `validate_run_payload`, after phase validation:

```python
    run_kind = _optional_run_kind(payload)
    _validate_run_kind_phase(run_kind, payload["phase"])
```

Before cleanup validation returns:

```python
    if run_kind == "parent":
        _validate_parent_run_payload(payload)
    elif run_kind == "child":
        _validate_child_run_payload(payload)
```

Add planner decision helpers before `validate_planner_output_payload`:

```python
def _has_multi_task_planner_fields(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in ("planner_decision", "next_child_task", "backlog", "blocked_reason", "done_criteria", "reader_summary", "decision_required")
    )


def _validate_next_child_task(payload: dict[str, Any]) -> None:
    task = _require_object(payload, "next_child_task")
    _require_keys(
        task,
        {"child_id", "title", "description", "allowed_paths", "denylist_paths", "verify_commands", "scenario_commands", "done_criteria"},
        "next_child_task",
    )
    for key in ("child_id", "title", "description"):
        _require_string(task, key)
        if not task[key]:
            raise ValueError(f"next_child_task.{key} must not be empty")
    for key in ("allowed_paths", "denylist_paths", "verify_commands", "scenario_commands", "done_criteria"):
        _require_list(task, key)


def _validate_multi_task_planner_fields(payload: dict[str, Any]) -> None:
    _require_enum(payload, "planner_decision", ALLOWED_DEMAND_PARENT_PLANNER_DECISIONS)
    _require_list(payload, "backlog")
    _require_string(payload, "blocked_reason")
    _require_list(payload, "done_criteria")
    _require_reader_summary(payload, {"purpose", "current_progress", "next_step", "decision_needed"})
    _require_bool(payload, "decision_required")
    decision = payload["planner_decision"]
    next_child_task = payload.get("next_child_task")
    if decision == "next_child":
        _validate_next_child_task(next_child_task)
    else:
        if isinstance(next_child_task, dict) and next_child_task:
            raise ValueError("next_child_task must be empty unless planner_decision is next_child")
        if decision == "parent_done" and not payload["done_criteria"]:
            raise ValueError("done_criteria must not be empty for parent_done")
        if decision in {"blocked", "failed"} and not payload["blocked_reason"]:
            raise ValueError("blocked_reason must not be empty for blocked or failed")
```

Inside `validate_planner_output_payload`, after existing list validation:

```python
    if _has_multi_task_planner_fields(payload):
        _validate_multi_task_planner_fields(payload)
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
git commit -m "feat(harness): validate demand parent child loop contracts"
```

## Task 3: Demand Multi-Task Orchestrator Fake Flow

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`

- [ ] **Step 1: Add failing fake-flow tests**

Append a new class to `scripts/tests/test_harness_loop_orchestrator.py`:

```python
class HarnessLoopDemandMultiTaskTests(unittest.TestCase):
    def _create_parent(self, repo_root: Path, run_id: str = "parent-run") -> dict[str, object]:
        payload = create_preflight_run(
            repo_root=repo_root,
            mode="demand-development",
            requirement="Build multi child feature",
            run_id=run_id,
            confirm=True,
        )
        payload["run_kind"] = "parent"
        payload["phase"] = "planning"
        payload["next_action"] = "run_parent_planner"
        payload["child_run_ids"] = []
        payload["current_child_run_id"] = ""
        payload["backlog"] = []
        payload["aggregate_acceptance"] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "pending": 0,
            "user_decision_required": False,
        }
        payload["reader_summary"] = {
            "purpose": "Build multi child feature",
            "current_progress": "Planning",
            "next_step": "Create first child",
            "decision_needed": "No",
        }
        payload["accepted_changed_paths"] = []
        write_json_file(run_dir_for(repo_root, run_id) / "run.json", payload)
        return payload

    def test_run_demand_multi_fake_completes_three_children_and_waits_for_human_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="parent-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "parent-run") / "run.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["phase"], "passed_waiting_human_merge")
            self.assertEqual(len(parent["child_run_ids"]), 3)
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 3)
            self.assertEqual(parent["aggregate_acceptance"]["pending"], 0)
            self.assertTrue(parent["accepted_changed_paths"])
            self.assertFalse((repo_root / ".git" / "MERGE_HEAD").exists())
            for child_run_id in parent["child_run_ids"]:
                child = read_json_file(run_dir_for(repo_root, child_run_id) / "run.json")
                self.assertEqual(child["run_kind"], "child")
                self.assertEqual(child["phase"], "passed")
                self.assertEqual(child["parent_run_id"], "parent-run")

    def test_run_demand_multi_repairs_same_failed_child_before_next_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "repair-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="repair-parent",
                planner_driver="fake",
                generator_driver="fake-fail-child-2-once",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "repair-parent") / "run.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 3)
            self.assertEqual(len(parent["child_run_ids"]), 3)
            child2 = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][1]) / "run.json")
            self.assertEqual(child2["phase"], "passed")
            events = (run_dir_for(repo_root, child2["run_id"]) / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("repair", events)

    def test_run_demand_multi_planner_blocked_or_failed_creates_no_child(self) -> None:
        for planner_driver, expected_reason in [
            ("fake-blocked", "fake planner blocked"),
            ("fake-failed", "fake planner failed"),
        ]:
            with self.subTest(planner_driver=planner_driver), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                self._create_parent(repo_root, f"{planner_driver}-parent")

                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id=f"{planner_driver}-parent",
                    planner_driver=planner_driver,
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=3,
                )

                parent = read_json_file(run_dir_for(repo_root, f"{planner_driver}-parent") / "run.json")
                planner_output = read_json_file(run_dir_for(repo_root, f"{planner_driver}-parent") / "planner-output.json")
                self.assertEqual(payload["phase"], "stopped_blocked")
                self.assertEqual(parent["child_run_ids"], [])
                self.assertEqual(planner_output["blocked_reason"], expected_reason)

    def test_run_demand_multi_writes_child_task_contract_and_stops_on_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "budget-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="budget-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=0,
            )

            parent = read_json_file(run_dir_for(repo_root, "budget-parent") / "run.json")
            self.assertEqual(payload["phase"], "stopped_budget")
            self.assertEqual(parent["child_run_ids"], [])

            self._create_parent(repo_root, "contract-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="contract-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=2,
            )
            contract_parent = read_json_file(run_dir_for(repo_root, "contract-parent") / "run.json")
            child_run_id = contract_parent["child_run_ids"][0]
            task_contract = read_json_file(run_dir_for(repo_root, child_run_id) / "task-contract.json")
            self.assertEqual(task_contract["task_id"], f"{child_run_id}-task")
            self.assertEqual(task_contract["evaluator_driver"], "harness_auto_gate")
            self.assertTrue(task_contract["must_simulate"])
```

Add `run_demand_multi` to the import list from `scripts.harness_loop_orchestrator`.

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests -v
```

Expected: FAIL because `run_demand_multi` does not exist.

- [ ] **Step 3: Implement fake parent/child helpers**

In `scripts/harness_loop_orchestrator.py`, add helpers after `_task_id_for_run`:

```python
def _child_run_id(parent_run_id: str, child_index: int) -> str:
    return f"{parent_run_id}-child-{child_index:03d}"


def _event_path(repo_root: Path, run_id: str) -> Path:
    return run_dir_for(repo_root, run_id) / "events.jsonl"


def append_loop_event(
    repo_root: Path,
    *,
    run_id: str,
    actor: str,
    event_type: str,
    summary: str,
    parent_run_id: str = "",
    child_id: str = "",
    details: dict[str, Any] | None = None,
    artifact_paths: list[str] | None = None,
) -> Path:
    payload = {
        "timestamp": _timestamp(),
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "child_id": child_id,
        "actor": actor,
        "event_type": event_type,
        "summary": summary,
        "details": details or {},
        "artifact_paths": artifact_paths or [],
    }
    path = _event_path(repo_root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _ensure_parent_fields(run: dict[str, Any]) -> dict[str, Any]:
    run.setdefault("run_kind", "parent")
    run.setdefault("child_run_ids", [])
    run.setdefault("current_child_run_id", "")
    run.setdefault("backlog", [])
    run.setdefault(
        "aggregate_acceptance",
        {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "pending": 0, "user_decision_required": False},
    )
    run.setdefault(
        "reader_summary",
        {"purpose": run.get("requirement", ""), "current_progress": "", "next_step": "", "decision_needed": "No"},
    )
    run.setdefault("accepted_changed_paths", [])
    return run
```

Add `_create_child_run`:

```python
def _create_child_run(repo_root: Path, parent: dict[str, Any], child_index: int, child_task: dict[str, Any]) -> dict[str, Any]:
    child_run_id = _child_run_id(parent["run_id"], child_index)
    child = {
        "run_id": child_run_id,
        "run_kind": "child",
        "parent_run_id": parent["run_id"],
        "child_index": child_index,
        "policy": "demand_development",
        "phase": "generating",
        "task_id": f"{child_run_id}-task",
        "domain": "",
        "branch": parent.get("branch", ""),
        "worktree": parent.get("worktree", ""),
        "requirement": str(child_task.get("description") or child_task.get("title") or parent.get("requirement", "")),
        "constraints": list(parent.get("constraints", [])),
        "stop_conditions": ["passed"],
        "baseline_dirty_paths": list(parent.get("baseline_dirty_paths", [])),
        "allowed_paths": list(child_task.get("allowed_paths", [])),
        "denylist_paths": list(child_task.get("denylist_paths", [])),
        "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
        "limits": dict(parent.get("limits", default_limits())),
        "last_result": "none",
        "next_action": "run_child_generator",
        "attempt_history": [],
        "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
        "reader_summary": {
            "purpose": str(child_task.get("title", "")),
            "planner_action": "Parent planner selected this child",
            "generator_action": "",
            "evaluator_action": "",
            "acceptance_result": "",
        },
    }
    write_json_file(run_dir_for(repo_root, child_run_id) / "run.json", child)
    write_json_file(
        run_dir_for(repo_root, child_run_id) / "planner-output.json",
        {
            "task_id": child["task_id"],
            "policy": "demand_development",
            "task_kind": "task_contract_only",
            "title": str(child_task.get("title", "")),
            "goal": str(child_task.get("description", "")),
            "non_goals": [],
            "allowed_paths": list(child_task.get("allowed_paths", [])),
            "denylist_paths": list(child_task.get("denylist_paths", [])),
            "verify_commands": list(child_task.get("verify_commands", [])),
            "evaluator_scenarios_path": "",
            "stop_conditions": ["passed"],
            "next_planning_hint": "return to parent planner",
        },
    )
    write_json_file(
        run_dir_for(repo_root, child_run_id) / "task-contract.json",
        {
            "task_id": child["task_id"],
            "title": str(child_task.get("title", "")),
            "description": str(child_task.get("description", "")),
            "verify_commands": list(child_task.get("verify_commands", [])),
            "scenario_commands": list(child_task.get("scenario_commands", [])),
            "artifact_paths": list(child_task.get("allowed_paths", [])),
            "required_services": [],
            "evaluator_driver": "harness_auto_gate",
            "eval_policy": {"task_level_required": True, "task_scope": "local_repo_and_harness"},
            "allowed_scope": "local_repo_and_harness",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": f"{child_run_id}-scenario",
                    "user_goal": str(child_task.get("description", "")),
                    "prerequisites": ["Parent demand multi-task run exists."],
                    "steps": ["Run child generator.", "Run child evaluator."],
                    "expected_outcomes": list(child_task.get("done_criteria", [])),
                    "failure_signals": ["Child evaluator fails.", "Changed paths leave allowed scope."],
                }
            ],
        },
    )
    append_loop_event(
        repo_root,
        run_id=child_run_id,
        parent_run_id=parent["run_id"],
        child_id=str(child_task.get("child_id", "")),
        actor="planner",
        event_type="plan",
        summary=f"Planner selected child {child_index}: {child_task.get('title', '')}",
    )
    return child
```

- [ ] **Step 4: Implement fake planner/generator/evaluator and run loop**

Add:

```python
def _fake_parent_planner_payload(parent: dict[str, Any], *, decision: str = "next_child", max_children: int = 3) -> dict[str, Any]:
    passed = int(parent.get("aggregate_acceptance", {}).get("passed", 0))
    if decision in {"blocked", "failed"}:
        return {
            "task_id": parent.get("task_id", ""),
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": "Demand parent planner",
            "goal": parent.get("requirement", ""),
            "non_goals": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "verify_commands": [],
            "evaluator_scenarios_path": "",
            "stop_conditions": ["passed_waiting_human_merge", "stopped_blocked", "stopped_budget"],
            "planner_decision": decision,
            "backlog": [],
            "next_child_task": {},
            "blocked_reason": f"fake planner {decision}",
            "done_criteria": [],
            "reader_summary": {
                "purpose": parent.get("requirement", ""),
                "current_progress": "Blocked",
                "next_step": "User decision required",
                "decision_needed": "Yes",
            },
            "decision_required": True,
            "next_planning_hint": "",
        }
    if passed >= max_children:
        planner_decision = "parent_done"
        next_child_task: dict[str, Any] = {}
        done_criteria = ["all fake children passed"]
    else:
        planner_decision = "next_child"
        next_index = passed + 1
        next_child_task = {
            "child_id": f"child-{next_index:03d}",
            "title": f"Fake child {next_index}",
            "description": f"Implement fake child {next_index}",
            "allowed_paths": [f"generated/child-{next_index:03d}.txt"],
            "denylist_paths": [".env"],
            "verify_commands": [],
            "scenario_commands": [],
            "done_criteria": [f"child {next_index} passes fake evaluator"],
        }
        done_criteria = []
    return {
        "task_id": parent.get("task_id", ""),
        "policy": "demand_development",
        "task_kind": "registered_task",
        "title": "Demand parent planner",
        "goal": parent.get("requirement", ""),
        "non_goals": [],
        "allowed_paths": [],
        "denylist_paths": [],
        "verify_commands": [],
        "evaluator_scenarios_path": "",
        "stop_conditions": ["passed_waiting_human_merge", "stopped_blocked", "stopped_budget"],
        "planner_decision": planner_decision,
        "backlog": list(parent.get("backlog", [])),
        "next_child_task": next_child_task,
        "blocked_reason": "",
        "done_criteria": done_criteria,
        "reader_summary": {
            "purpose": parent.get("requirement", ""),
            "current_progress": f"{passed} children passed",
            "next_step": "Run next child" if planner_decision == "next_child" else "Await human merge",
            "decision_needed": "No",
        },
        "decision_required": False,
        "next_planning_hint": "",
    }
```

Add `run_demand_multi`:

```python
def run_demand_multi(
    repo_root: Path | str,
    run_id: str,
    *,
    planner_driver: str,
    generator_driver: str,
    evaluator_driver: str,
    max_eval_attempts: int,
    max_children: int,
) -> dict[str, str]:
    root = Path(repo_root)
    parent = _ensure_parent_fields(load_run(root, run_id))
    if parent["phase"] == "preflight":
        raise RuntimeError("run_demand_multi requires confirmed preflight")
    if planner_driver not in {"fake", "fake-blocked", "fake-failed"}:
        raise ValueError("run_demand_multi initially supports fake planner drivers")
    if evaluator_driver != "fake":
        raise ValueError("run_demand_multi initially supports fake evaluator driver")

    while True:
        parent = _ensure_parent_fields(load_run(root, run_id))
        if max_children < 1:
            parent["phase"] = "stopped_budget"
            parent["last_result"] = "blocked"
            parent["next_action"] = "inspect_budget_limits"
            parent["aggregate_acceptance"]["user_decision_required"] = True
            save_run(root, parent)
            append_loop_event(root, run_id=run_id, actor="orchestrator", event_type="blocked", summary="max_children budget exhausted")
            return status_for_run(root, run_id)
        if parent["aggregate_acceptance"]["passed"] >= max_children:
            parent["phase"] = "passed_waiting_human_merge"
            parent["next_action"] = "await_human_merge_confirmation"
            parent["last_result"] = "pass"
            parent["aggregate_acceptance"]["total"] = max_children
            parent["aggregate_acceptance"]["pending"] = 0
            save_run(root, parent)
            append_loop_event(root, run_id=run_id, actor="orchestrator", event_type="decision", summary="All child tasks passed; awaiting human merge")
            return status_for_run(root, run_id)

        planner_payload = _fake_parent_planner_payload(
            parent,
            decision={"fake-blocked": "blocked", "fake-failed": "failed"}.get(planner_driver, "next_child"),
            max_children=max_children,
        )
        validate_planner_output_payload(planner_payload)
        write_json_file(run_dir_for(root, run_id) / "planner-output.json", planner_payload)
        parent["attempts"]["planner"] = int(parent["attempts"]["planner"]) + 1

        if planner_payload["planner_decision"] in {"blocked", "failed"}:
            parent["phase"] = "stopped_blocked"
            parent["last_result"] = "blocked"
            parent["next_action"] = "inspect_parent_planner_blocked"
            parent["reader_summary"] = planner_payload["reader_summary"]
            parent["aggregate_acceptance"]["user_decision_required"] = True
            save_run(root, parent)
            append_loop_event(root, run_id=run_id, actor="planner", event_type="blocked", summary=planner_payload["blocked_reason"])
            return status_for_run(root, run_id)

        child_index = len(parent["child_run_ids"]) + 1
        child = _create_child_run(root, parent, child_index, planner_payload["next_child_task"])
        parent["child_run_ids"].append(child["run_id"])
        parent["current_child_run_id"] = child["run_id"]
        parent["phase"] = "child_running"
        parent["next_action"] = "run_child_generator"
        parent["aggregate_acceptance"]["total"] = max_children
        parent["aggregate_acceptance"]["pending"] = max_children - parent["aggregate_acceptance"]["passed"]
        save_run(root, parent)

        _run_fake_demand_child(root, parent, child, generator_driver=generator_driver, max_eval_attempts=max_eval_attempts)
```

Add `_run_fake_demand_child`:

```python
def _run_fake_demand_child(
    repo_root: Path,
    parent: dict[str, Any],
    child: dict[str, Any],
    *,
    generator_driver: str,
    max_eval_attempts: int,
) -> None:
    child_run_dir = run_dir_for(repo_root, child["run_id"])
    child_index = int(child["child_index"])
    generated_path = f"generated/child-{child_index:03d}.txt"
    target = repo_root / generated_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"child {child_index}\n", encoding="utf-8")
    generator_payload = {
        "task_id": child["task_id"],
        "status": "implemented",
        "changed_paths": [generated_path],
        "commit": "",
        "verify_commands": [],
        "verify_results": [{"command": "fake", "status": "pass"}],
        "artifacts": [generated_path],
        "cleanup_required": False,
        "notes": "fake demand child generated",
    }
    validate_generator_result_payload(generator_payload)
    write_json_file(child_run_dir / "generator-result.json", generator_payload)
    child["attempts"]["generator"] = int(child["attempts"]["generator"]) + 1
    child["reader_summary"]["generator_action"] = f"Generated {generated_path}"
    append_loop_event(
        repo_root,
        run_id=child["run_id"],
        parent_run_id=parent["run_id"],
        child_id=f"child-{child_index:03d}",
        actor="generator",
        event_type="implement",
        summary=f"Generator wrote {generated_path}",
        artifact_paths=[generated_path],
    )

    should_fail_once = generator_driver == "fake-fail-child-2-once" and child_index == 2 and int(child["attempts"]["evaluator"]) == 0
    evaluator_status = "fail" if should_fail_once else "pass"
    evaluator_payload = {
        "status": evaluator_status,
        "task_id": child["task_id"],
        "driver": "fake",
        "returncode": 1 if should_fail_once else 0,
        "stdout": "fake evaluator fail\n" if should_fail_once else "fake evaluator pass\n",
        "stderr": "",
    }
    validate_evaluator_result_payload(evaluator_payload)
    write_json_file(child_run_dir / "evaluator-result.json", evaluator_payload)
    child["attempts"]["evaluator"] = int(child["attempts"]["evaluator"]) + 1
    if should_fail_once and child["attempts"]["evaluator"] < max_eval_attempts:
        child["phase"] = "repair_needed"
        child["last_result"] = "fail"
        child["next_action"] = "repair_child"
        append_loop_event(repo_root, run_id=child["run_id"], parent_run_id=parent["run_id"], child_id=f"child-{child_index:03d}", actor="evaluator", event_type="evaluate", summary="Evaluator failed child; repair required")
        write_json_file(child_run_dir / "run.json", child)
        append_loop_event(repo_root, run_id=child["run_id"], parent_run_id=parent["run_id"], child_id=f"child-{child_index:03d}", actor="generator", event_type="repair", summary="Generator repaired same child")
        child["attempts"]["evaluator"] = int(child["attempts"]["evaluator"]) + 1
        evaluator_payload["status"] = "pass"
        evaluator_payload["returncode"] = 0
        evaluator_payload["stdout"] = "fake evaluator pass after repair\n"
        write_json_file(child_run_dir / "evaluator-result.json", evaluator_payload)
    child["phase"] = "passed"
    child["last_result"] = "pass"
    child["next_action"] = "return_to_parent_planner"
    child["reader_summary"]["evaluator_action"] = "Fake evaluator passed"
    child["reader_summary"]["acceptance_result"] = "Passed"
    write_json_file(child_run_dir / "run.json", child)
    append_loop_event(repo_root, run_id=child["run_id"], parent_run_id=parent["run_id"], child_id=f"child-{child_index:03d}", actor="evaluator", event_type="evaluate", summary="Evaluator passed child")

    parent = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
    parent["accepted_changed_paths"] = sorted(set(parent["accepted_changed_paths"] + generator_payload["changed_paths"]))
    parent["aggregate_acceptance"]["passed"] = int(parent["aggregate_acceptance"]["passed"]) + 1
    parent["aggregate_acceptance"]["pending"] = max(0, int(parent["aggregate_acceptance"]["total"]) - int(parent["aggregate_acceptance"]["passed"]))
    parent["current_child_run_id"] = child["run_id"]
    parent["phase"] = "planning"
    parent["next_action"] = "run_parent_planner"
    save_run(repo_root, parent)
```

- [ ] **Step 5: Add CLI parser**

In `_build_parser`, add after `run` parser:

```python
    run_demand_multi_parser = subparsers.add_parser("run-demand-multi", help="Run demand-development parent/child loop.")
    run_demand_multi_parser.add_argument("--repo-root", default=".")
    run_demand_multi_parser.add_argument("--run-id", required=True)
    run_demand_multi_parser.add_argument("--planner-driver", choices=("fake", "fake-blocked", "fake-failed", "codex-exec"), required=True)
    run_demand_multi_parser.add_argument(
        "--generator-driver",
        choices=(
            "fake",
            "fake-fail-child-2-once",
            "fake-dirty-path",
            "fake-timeout",
            "fake-invalid-json",
            "fake-missing-artifact",
            "fake-stop-after-child-1",
            "codex-exec",
        ),
        required=True,
    )
    run_demand_multi_parser.add_argument("--evaluator-driver", choices=("fake", "codex-exec"), required=True)
    run_demand_multi_parser.add_argument("--max-eval-attempts", type=int, default=2)
    run_demand_multi_parser.add_argument("--max-children", type=int, default=3)
```

In `main`, add before `run-autonomous`:

```python
    elif args.command == "run-demand-multi":
        payload = run_demand_multi(
            repo_root=args.repo_root,
            run_id=args.run_id,
            planner_driver=args.planner_driver,
            generator_driver=args.generator_driver,
            evaluator_driver=args.evaluator_driver,
            max_eval_attempts=args.max_eval_attempts,
            max_children=args.max_children,
        )
```

- [ ] **Step 6: Run orchestrator fake-flow tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests -v
```

Expected: PASS.

- [ ] **Step 7: Commit fake orchestrator**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py
git commit -m "feat(harness): run demand multi-task fake loop"
```

## Task 4: Dirty Path Gate, Resume, And Agent Failure Cases

**Files:**
- Modify: `scripts/harness_loop_orchestrator.py`
- Modify: `scripts/tests/test_harness_loop_orchestrator.py`

- [ ] **Step 1: Add failing tests for E2E-03, E2E-06, E2E-07**

Append tests to `HarnessLoopDemandMultiTaskTests`:

```python
    def test_run_demand_multi_blocks_on_unaccepted_dirty_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            self._create_parent(repo_root, "dirty-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="dirty-parent",
                planner_driver="fake",
                generator_driver="fake-dirty-path",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            parent = read_json_file(run_dir_for(repo_root, "dirty-parent") / "run.json")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent["last_result"], "blocked")
            events = (run_dir_for(repo_root, "dirty-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("unexpected dirty path", events)

    def test_run_demand_multi_blocks_on_agent_timeout_invalid_json_and_missing_artifact(self) -> None:
        for driver, expected in [
            ("fake-timeout", "timeout"),
            ("fake-invalid-json", "invalid_json"),
            ("fake-missing-artifact", "missing artifact"),
        ]:
            with self.subTest(driver=driver), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                self._create_parent(repo_root, f"agent-{driver}")

                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id=f"agent-{driver}",
                    planner_driver="fake",
                    generator_driver=driver,
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=1,
                )

                parent = read_json_file(run_dir_for(repo_root, f"agent-{driver}") / "run.json")
                self.assertEqual(payload["phase"], "stopped_blocked")
                self.assertTrue(parent["aggregate_acceptance"]["user_decision_required"])
                events = (run_dir_for(repo_root, f"agent-{driver}") / "events.jsonl").read_text(encoding="utf-8")
                self.assertIn(expected, events)

    def test_run_demand_multi_resumes_current_child_without_repeating_passed_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "resume-parent")

            first = run_demand_multi(
                repo_root=repo_root,
                run_id="resume-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )
            self.assertEqual(first["phase"], "child_running")
            parent_before = read_json_file(run_dir_for(repo_root, "resume-parent") / "run.json")
            first_child = parent_before["child_run_ids"][0]
            first_child_events_before = (run_dir_for(repo_root, first_child) / "events.jsonl").read_text(encoding="utf-8")

            second = run_demand_multi(
                repo_root=repo_root,
                run_id="resume-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent_after = read_json_file(run_dir_for(repo_root, "resume-parent") / "run.json")
            first_child_events_after = (run_dir_for(repo_root, first_child) / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(second["phase"], "passed_waiting_human_merge")
            self.assertEqual(len(parent_after["child_run_ids"]), 3)
            self.assertEqual(first_child_events_before, first_child_events_after)
            parent_events = (run_dir_for(repo_root, "resume-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("resume", parent_events)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests -v
```

Expected: FAIL on the new driver cases.

- [ ] **Step 3: Add dirty path helper**

In `scripts/harness_loop_orchestrator.py`, add:

```python
def _dirty_paths_after_baseline(repo_root: Path, parent: dict[str, Any], child: dict[str, Any]) -> list[str]:
    baseline = {str(path) for path in parent.get("baseline_dirty_paths", [])}
    accepted = {str(path) for path in parent.get("accepted_changed_paths", [])}
    allowed = {str(path) for path in child.get("allowed_paths", [])}
    unexpected: list[str] = []
    for porcelain in _baseline_dirty_paths(repo_root):
        path = porcelain[3:] if len(porcelain) > 3 else porcelain
        if porcelain in baseline or path in baseline or path in accepted or path in allowed:
            continue
        unexpected.append(path)
    return sorted(set(unexpected))


def _block_parent(repo_root: Path, parent: dict[str, Any], reason: str, *, actor: str = "orchestrator") -> dict[str, str]:
    parent["phase"] = "stopped_blocked"
    parent["last_result"] = "blocked"
    parent["next_action"] = "inspect_blocked_diagnostics"
    parent["aggregate_acceptance"]["user_decision_required"] = True
    save_run(repo_root, parent)
    append_loop_event(repo_root, run_id=parent["run_id"], actor=actor, event_type="blocked", summary=reason)
    return status_for_run(repo_root, parent["run_id"])
```

- [ ] **Step 4: Implement fake failure drivers and resume stop**

In `_run_fake_demand_child`, before writing normal generator result:

```python
    if generator_driver in {"fake-timeout", "fake-invalid-json", "fake-missing-artifact"}:
        reason = {
            "fake-timeout": "generator timeout",
            "fake-invalid-json": "generator invalid_json",
            "fake-missing-artifact": "generator missing artifact",
        }[generator_driver]
        append_loop_event(repo_root, run_id=parent["run_id"], actor="generator", event_type="blocked", summary=reason)
        parent = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
        _block_parent(repo_root, parent, reason, actor="generator")
        return
```

For `fake-dirty-path`, after normal target write:

```python
    if generator_driver == "fake-dirty-path":
        (repo_root / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
```

After normal generator result and before evaluator pass:

```python
    parent_for_dirty = _ensure_parent_fields(load_run(repo_root, parent["run_id"]))
    unexpected_dirty = _dirty_paths_after_baseline(repo_root, parent_for_dirty, child)
    if unexpected_dirty:
        _block_parent(repo_root, parent_for_dirty, f"unexpected dirty path: {', '.join(unexpected_dirty)}")
        return
```

At the end of `_run_fake_demand_child`, after saving passed child and parent accepted paths:

```python
    if generator_driver == "fake-stop-after-child-1" and child_index == 1:
        parent["phase"] = "child_running"
        parent["next_action"] = "resume_current_child"
        save_run(repo_root, parent)
        append_loop_event(repo_root, run_id=parent["run_id"], actor="orchestrator", event_type="decision", summary="resume checkpoint after child 1")
        return
```

In `run_demand_multi`, after loading parent at the top of the loop:

```python
        if parent.get("phase") == "child_running" and parent.get("current_child_run_id"):
            current_child = load_run(root, parent["current_child_run_id"])
            if current_child.get("phase") == "passed":
                append_loop_event(root, run_id=run_id, actor="orchestrator", event_type="decision", summary=f"resume from passed child {current_child['run_id']}")
                parent["phase"] = "planning"
                parent["next_action"] = "run_parent_planner"
                save_run(root, parent)
                continue
```

If `_run_fake_demand_child` blocked parent, make `run_demand_multi` return immediately:

```python
        parent_after_child = load_run(root, run_id)
        if parent_after_child["phase"] in {"stopped_blocked", "stopped_budget"}:
            return status_for_run(root, run_id)
```

- [ ] **Step 5: Run orchestrator demand tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_orchestrator.HarnessLoopDemandMultiTaskTests -v
```

Expected: PASS.

- [ ] **Step 6: Commit dirty/resume/failure handling**

```bash
git add scripts/harness_loop_orchestrator.py scripts/tests/test_harness_loop_orchestrator.py
git commit -m "feat(harness): handle demand child failure and resume"
```

## Task 5: Dashboard Backend Parent/Child Aggregation

**Files:**
- Modify: `apps/loop_dashboard/backend/loop_dashboard/store.py`
- Modify: `apps/loop_dashboard/backend/tests/test_store.py`
- Modify: `apps/loop_dashboard/backend/tests/test_api.py`

- [ ] **Step 1: Add failing backend tests**

Append helpers and tests to `apps/loop_dashboard/backend/tests/test_store.py`:

```python
def seed_parent_child_runs(repo_root: Path) -> None:
    parent_dir = repo_root / ".codex" / "loop-runs" / "parent-run"
    write_json(
        parent_dir / "run.json",
        {
            "run_id": "parent-run",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "Parent requirement for dashboard",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 2, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_parent_planner",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["parent-run-child-002", "missing-child"],
            "current_child_run_id": "parent-run-child-002",
            "backlog": [],
            "aggregate_acceptance": {"total": 2, "passed": 1, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            "reader_summary": {"purpose": "Explain parent", "current_progress": "One child passed", "next_step": "Run child 2", "decision_needed": "No"},
            "accepted_changed_paths": ["generated/child-001.txt"],
        },
    )
    for index, phase in [(1, "passed"), (2, "generating")]:
        child_id = f"parent-run-child-{index:03d}"
        child_dir = repo_root / ".codex" / "loop-runs" / child_id
        write_json(
            child_dir / "run.json",
            {
                "run_id": child_id,
                "run_kind": "child",
                "parent_run_id": "parent-run",
                "child_index": index,
                "policy": "demand_development",
                "phase": phase,
                "task_id": f"{child_id}-task",
                "domain": "",
                "branch": "main",
                "worktree": str(repo_root),
                "requirement": f"Child {index} description with enough text to wrap cleanly",
                "constraints": [],
                "stop_conditions": ["passed"],
                "baseline_dirty_paths": [],
                "allowed_paths": [f"generated/child-{index:03d}.txt"],
                "denylist_paths": [],
                "attempts": {"planner": 1, "generator": 1, "evaluator": 1 if phase == "passed" else 0, "artifact_hygiene": 0, "cleanup": 0},
                "limits": {},
                "last_result": "pass" if phase == "passed" else "none",
                "next_action": "return_to_parent_planner" if phase == "passed" else "run_child_generator",
                "attempt_history": [],
                "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
                "reader_summary": {
                    "purpose": f"Child {index}",
                    "planner_action": "Planner picked child",
                    "generator_action": "Generator wrote file",
                    "evaluator_action": "Evaluator checked result",
                    "acceptance_result": "Passed" if phase == "passed" else "Pending",
                },
            },
        )
        (child_dir / "events.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": "2026-07-03T00:00:00Z",
                    "run_id": child_id,
                    "parent_run_id": "parent-run",
                    "child_id": f"child-{index:03d}",
                    "actor": "planner",
                    "event_type": "plan",
                    "summary": f"Planner selected child {index}",
                    "details": {},
                    "artifact_paths": [],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )


def test_parent_child_runs_are_aggregated_with_children_and_events(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    store = LoopDashboardStore(tmp_path)

    runs = store.list_runs()
    parent = next(run for run in runs if run["run_id"] == "parent-run")
    detail = store.get_run("parent-run")
    events = store.get_events("parent-run")

    assert parent["run_kind"] == "parent"
    assert parent["children_summary"]["total"] == 2
    assert parent["children_summary"]["passed"] == 1
    assert detail["reader_summary"]["purpose"] == "Explain parent"
    assert [child["run_id"] for child in detail["children"]] == ["parent-run-child-001", "parent-run-child-002"]
    assert detail["children"][0]["reader_summary"]["acceptance_result"] == "Passed"
    assert any(event["kind"] == "plan" and "Planner selected child 1" in event["message"] for event in events)
    assert any(item["kind"] == "child_artifact_missing" for item in detail["relationship_diagnostics"])


def test_parent_child_relationship_conflicts_are_deduped_sorted_and_diagnosed(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    other_parent = tmp_path / ".codex" / "loop-runs" / "other-parent" / "run.json"
    payload = json.loads((tmp_path / ".codex" / "loop-runs" / "parent-run" / "run.json").read_text(encoding="utf-8"))
    payload["run_id"] = "other-parent"
    payload["child_run_ids"] = ["parent-run-child-001"]
    write_json(other_parent, payload)
    child_path = tmp_path / ".codex" / "loop-runs" / "parent-run-child-001" / "run.json"
    child_payload = json.loads(child_path.read_text(encoding="utf-8"))
    child_payload["parent_run_id"] = "other-parent"
    child_path.write_text(json.dumps(child_payload, indent=2), encoding="utf-8")

    detail = LoopDashboardStore(tmp_path).get_run("parent-run")

    assert [child["run_id"] for child in detail["children"]].count("parent-run-child-001") == 0
    assert any(item["kind"] == "child_parent_conflict" for item in detail["relationship_diagnostics"])


def test_parent_child_relationship_rejects_path_traversal(tmp_path: Path) -> None:
    seed_parent_child_runs(tmp_path)
    parent_path = tmp_path / ".codex" / "loop-runs" / "parent-run" / "run.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent["child_run_ids"].append("../outside")
    parent_path.write_text(json.dumps(parent, indent=2), encoding="utf-8")

    detail = LoopDashboardStore(tmp_path).get_run("parent-run")

    assert all(child["run_id"] != "../outside" for child in detail["children"])
    assert any(item["kind"] == "unsafe_child_reference" for item in detail["relationship_diagnostics"])


def test_single_run_without_run_kind_remains_top_level(tmp_path: Path) -> None:
    seed_run(tmp_path, "single-run", "passed_waiting_human_merge", last_result="pass", next_action="await_human_merge_confirmation")

    runs = LoopDashboardStore(tmp_path).list_runs()
    detail = LoopDashboardStore(tmp_path).get_run("single-run")

    assert runs[0]["run_kind"] == "single"
    assert "children" not in detail or detail["children"] == []
```

- [ ] **Step 2: Run backend store tests and verify they fail**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests/test_store.py -k 'parent_child or single_run_without'
```

Expected: FAIL because parent/child aggregation is not implemented.

- [ ] **Step 3: Implement parent/child relationship index**

In `apps/loop_dashboard/backend/loop_dashboard/store.py`, add helpers to `LoopDashboardStore`:

```python
    def _run_kind(self, run_data: dict[str, Any]) -> str:
        value = run_data.get("run_kind")
        return str(value) if value in {"parent", "child"} else "single"

    def _safe_child_run_id(self, run_id: str) -> bool:
        return self._safe_run_id(run_id)

    def _all_run_data_by_id(self) -> dict[str, tuple[RunSource, dict[str, Any]]]:
        result: dict[str, tuple[RunSource, dict[str, Any]]] = {}
        for source in self._run_sources():
            data = self._read_json(source.run_dir / "run.json", allowed_root=source.run_dir)
            if not isinstance(data, dict):
                continue
            run_id = str(data.get("run_id") or source.run_dir.name)
            if self._safe_run_id(run_id):
                result[run_id] = (source, data)
        return result
```

Add `_relationship_diagnostic`:

```python
    def _relationship_diagnostic(self, kind: str, message: str, source: str) -> dict[str, Any]:
        return {"kind": kind, "severity": "warning", "title": kind.replace("_", " "), "message": message, "source": source}
```

Add `_children_for_parent`:

```python
    def _children_for_parent(self, parent_run_id: str, parent_data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        all_runs = self._all_run_data_by_id()
        diagnostics: list[dict[str, Any]] = []
        child_ids: set[str] = set()
        for child_id in parent_data.get("child_run_ids", []):
            child_id_text = str(child_id)
            if not self._safe_child_run_id(child_id_text):
                diagnostics.append(self._relationship_diagnostic("unsafe_child_reference", f"Unsafe child reference ignored: {child_id_text}", child_id_text))
                continue
            if child_id_text not in all_runs:
                diagnostics.append(self._relationship_diagnostic("child_artifact_missing", f"Child artifact is missing: {child_id_text}", child_id_text))
                continue
            child_ids.add(child_id_text)
        for run_id, (_source, run_data) in all_runs.items():
            if str(run_data.get("run_kind") or "") == "child" and str(run_data.get("parent_run_id") or "") == parent_run_id:
                if run_id not in child_ids:
                    diagnostics.append(self._relationship_diagnostic("parent_index_missing", f"Child points to parent but parent child_run_ids omitted it: {run_id}", run_id))
                child_ids.add(run_id)
        children: list[dict[str, Any]] = []
        for child_id in child_ids:
            source, child_data = all_runs[child_id]
            child_parent = str(child_data.get("parent_run_id") or "")
            if child_parent and child_parent != parent_run_id:
                diagnostics.append(self._relationship_diagnostic("child_parent_conflict", f"Child {child_id} points to {child_parent}, not {parent_run_id}", child_id))
                continue
            summary = self._load_run_summary(source.run_dir, source.source_kind)
            summary["reader_summary"] = child_data.get("reader_summary", {})
            summary["child_index"] = child_data.get("child_index", 0)
            children.append(summary)
        children.sort(key=lambda child: (int(child.get("child_index") or 0), str(child.get("updated_at") or ""), str(child.get("run_id") or "")))
        return children, diagnostics
```

- [ ] **Step 4: Extend summaries and details**

In `_load_run_summary`, include:

```python
        run_kind = self._run_kind(run_data)
```

In returned dict add:

```python
            "run_kind": run_kind,
            "parent_run_id": str(run_data.get("parent_run_id") or ""),
            "current_child_run_id": str(run_data.get("current_child_run_id") or ""),
            "reader_summary": run_data.get("reader_summary", {}),
            "children_summary": self._children_summary(run_data),
            "decision_required": bool((run_data.get("aggregate_acceptance") or {}).get("user_decision_required", False)),
```

Add helper:

```python
    def _children_summary(self, run_data: dict[str, Any]) -> dict[str, int]:
        aggregate = run_data.get("aggregate_acceptance")
        if not isinstance(aggregate, dict):
            return {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "pending": 0}
        return {
            "total": int(aggregate.get("total") or 0),
            "passed": int(aggregate.get("passed") or 0),
            "failed": int(aggregate.get("failed") or 0),
            "blocked": int(aggregate.get("blocked") or 0),
            "pending": int(aggregate.get("pending") or 0),
        }
```

In `get_run`, after reading `run_data`, add:

```python
        if self._run_kind(run_data) == "parent":
            children, relationship_diagnostics = self._children_for_parent(str(run_data.get("run_id") or run_id), run_data)
        else:
            children, relationship_diagnostics = [], []
```

In `summary.update`, add:

```python
                "reader_summary": run_data.get("reader_summary", {}),
                "aggregate_acceptance": run_data.get("aggregate_acceptance", {}),
                "children": children,
                "relationship_diagnostics": relationship_diagnostics,
```

Also append `relationship_diagnostics` to `blocked_diagnostics`:

```python
                "blocked_diagnostics": [*summary.get("blocked_diagnostics", []), *relationship_diagnostics],
```

- [ ] **Step 5: Read structured events**

In `get_events`, before log collection, read `events.jsonl`:

```python
        events.extend(self._structured_events(run_dir))
        run_data = self._read_json(run_dir / "run.json", allowed_root=run_dir)
        if isinstance(run_data, dict) and self._run_kind(run_data) == "parent":
            children, _diagnostics = self._children_for_parent(str(run_data.get("run_id") or run_id), run_data)
            for child in children:
                child_source = self._run_source(str(child.get("run_id") or ""))
                if child_source is not None:
                    events.extend(self._structured_events(child_source.run_dir))
```

Add:

```python
    def _structured_events(self, run_dir: Path) -> list[Event]:
        path = run_dir / "events.jsonl"
        if not path.exists() or self._safe_file_under(path, run_dir) is None:
            return []
        events: list[Event] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            events.append(
                Event(
                    str(payload.get("event_type") or "event"),
                    self._relative_artifact(path),
                    redact_text(str(payload.get("summary") or "")),
                    str(payload.get("timestamp") or self._mtime_iso(path)),
                )
            )
        return events
```

- [ ] **Step 6: Add API tests for parent/child shape**

Append to `apps/loop_dashboard/backend/tests/test_api.py`:

```python
def seed_parent_child_api_run(repo_root: Path) -> None:
    parent_dir = repo_root / ".codex" / "loop-runs" / "api-parent"
    write_json(
        parent_dir / "run.json",
        {
            "run_id": "api-parent",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "API parent",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_parent_planner",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["api-parent-child-001"],
            "current_child_run_id": "api-parent-child-001",
            "backlog": [],
            "aggregate_acceptance": {"total": 1, "passed": 0, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            "reader_summary": {"purpose": "API summary", "current_progress": "running", "next_step": "child", "decision_needed": "No"},
            "accepted_changed_paths": [],
        },
    )
    child_dir = repo_root / ".codex" / "loop-runs" / "api-parent-child-001"
    child_payload = json.loads((parent_dir / "run.json").read_text(encoding="utf-8"))
    child_payload.update(
        {
            "run_id": "api-parent-child-001",
            "run_kind": "child",
            "parent_run_id": "api-parent",
            "child_index": 1,
            "phase": "generating",
            "task_id": "api-parent-child-001-task",
            "requirement": "API child",
            "stop_conditions": ["passed"],
            "attempts": {"planner": 1, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "reader_summary": {
                "purpose": "API child",
                "planner_action": "planned",
                "generator_action": "pending",
                "evaluator_action": "pending",
                "acceptance_result": "pending",
            },
        }
    )
    write_json(child_dir / "run.json", child_payload)


def test_api_returns_parent_child_fields(tmp_path: Path) -> None:
    seed_parent_child_api_run(tmp_path)
    client = TestClient(create_app(project_root=tmp_path))

    runs = client.get("/api/runs").json()
    detail = client.get("/api/runs/api-parent").json()

    parent = next(run for run in runs if run["run_id"] == "api-parent")
    assert parent["run_kind"] == "parent"
    assert parent["children_summary"]["total"] == 1
    assert detail["reader_summary"]["purpose"] == "API summary"
    assert detail["children"][0]["run_id"] == "api-parent-child-001"
```

- [ ] **Step 7: Run backend tests**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
```

Expected: PASS.

- [ ] **Step 8: Commit backend aggregation**

```bash
git add apps/loop_dashboard/backend/loop_dashboard/store.py apps/loop_dashboard/backend/tests/test_store.py apps/loop_dashboard/backend/tests/test_api.py
git commit -m "feat(loop-dashboard): aggregate demand parent child runs"
```

## Task 6: Dashboard Frontend Parent/Child UI

**Files:**
- Modify: `apps/loop_dashboard/frontend/app.js`
- Modify: `apps/loop_dashboard/frontend/styles.css`

- [ ] **Step 1: Add parent/child rendering helpers in JS**

In `apps/loop_dashboard/frontend/app.js`, add helper functions near labels:

```javascript
function runKindLabel(runKind) {
  const labels = { parent: "父需求", child: "子任务", single: "单任务" };
  return labels[runKind] || "单任务";
}

function childrenProgressLabel(summary) {
  if (!summary || !summary.total) {
    return "无子任务";
  }
  return `${summary.passed || 0} / ${summary.total || 0} 通过`;
}
```

- [ ] **Step 2: Update run list entries**

In `runButton(run)`, after summary append child progress:

```javascript
  const metaParts = [runKindLabel(run.run_kind), phaseLabel(run.phase), formatTime(run.updated_at)];
  if (run.run_kind === "parent") {
    metaParts.splice(1, 0, childrenProgressLabel(run.children_summary));
  }
```

Replace the existing `run-meta` line with:

```javascript
    el("div", "run-meta", metaParts.join(" · ")),
```

If `run.run_kind === "parent"`, append:

```javascript
  if (run.run_kind === "parent" && run.current_child_run_id) {
    button.append(el("div", "run-child-current", `当前子任务：${run.current_child_run_id}`));
  }
```

- [ ] **Step 3: Render parent reader summary and child queue**

In `renderDetail`, after `summary.append(decisionGrid);`, add:

```javascript
  if (detail.run_kind === "parent") {
    summary.append(renderParentReaderSummary(detail), renderChildQueue(detail.children || []));
  }
```

Add functions:

```javascript
function renderParentReaderSummary(detail) {
  const summary = detail.reader_summary || {};
  const section = el("section", "parent-reader-summary");
  section.append(el("div", "detail-section-title", "父需求读者摘要"));
  [
    ["目的", summary.purpose || detail.task_description || detail.task_summary],
    ["当前进展", summary.current_progress || phaseLabel(detail.phase)],
    ["下一步", summary.next_step || actionLabel(detail.next_action)],
    ["用户决策", summary.decision_needed || "不需要"],
  ].forEach(([label, value]) => section.append(infoRow(label, value)));
  return section;
}

function renderChildQueue(children) {
  const section = el("section", "child-queue");
  section.append(el("div", "detail-section-title", "子任务队列"));
  if (!children.length) {
    section.append(empty("暂无子任务"));
    return section;
  }
  children.forEach((child) => {
    const card = el("article", "child-card");
    const reader = child.reader_summary || {};
    card.append(
      el("div", "child-card-title", `${child.child_index || ""}. ${text(child.task_description || child.task_summary || child.run_id)}`),
      el("div", "child-card-meta", `${phaseLabel(child.phase)} · ${text(child.run_id)}`),
      childReaderRow("Planner", reader.planner_action),
      childReaderRow("Generator", reader.generator_action),
      childReaderRow("Evaluator", reader.evaluator_action),
      childReaderRow("验收", reader.acceptance_result),
    );
    section.append(card);
  });
  return section;
}

function childReaderRow(label, value) {
  const row = el("div", "child-reader-row");
  row.append(el("span", "child-reader-label", `${label}:`), el("span", "child-reader-value", text(value, "暂无")));
  return row;
}
```

- [ ] **Step 4: Render relationship diagnostics**

In `renderDiagnostics`, before `setChildren`, combine diagnostics:

```javascript
  const relationshipDiagnostics = state.detail && Array.isArray(state.detail.relationship_diagnostics) ? state.detail.relationship_diagnostics : [];
  const diagnostics = [
    ...(state.detail && Array.isArray(state.detail.blocked_diagnostics) ? state.detail.blocked_diagnostics : []),
    ...relationshipDiagnostics,
  ];
```

Remove the old `const diagnostics = ...` line.

- [ ] **Step 5: Add responsive styles**

Append to `apps/loop_dashboard/frontend/styles.css`:

```css
.run-child-current {
  margin-top: 6px;
  color: #526172;
  font-size: 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.parent-reader-summary,
.child-queue {
  margin-top: 14px;
  border-top: 1px solid var(--border-subtle, #e6ebf2);
  padding-top: 14px;
}

.child-card {
  border: 1px solid var(--border-subtle, #e0e6ee);
  border-radius: 8px;
  padding: 12px;
  margin-top: 10px;
  background: #fff;
}

.child-card-title {
  font-weight: 700;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.child-card-meta {
  margin-top: 4px;
  color: #657284;
  font-size: 12px;
}

.child-reader-row {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 8px;
  margin-top: 8px;
  line-height: 1.45;
}

.child-reader-label {
  font-weight: 700;
  color: #334155;
}

.child-reader-value {
  color: #4d5a69;
  overflow-wrap: anywhere;
}

@media (max-width: 720px) {
  .child-reader-row {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
```

- [ ] **Step 6: Run backend tests and static sanity**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
node --check apps/loop_dashboard/frontend/app.js
```

Expected: PASS and `node --check` exits 0.

- [ ] **Step 7: Commit frontend UI**

```bash
git add apps/loop_dashboard/frontend/app.js apps/loop_dashboard/frontend/styles.css
git commit -m "feat(loop-dashboard): show parent child demand loops"
```

## Task 7: Dashboard Evaluator E2E Coverage

**Files:**
- Modify: `scripts/loop_dashboard_evaluator.py`

- [ ] **Step 1: Inspect existing evaluator structure**

Run:

```bash
sed -n '1,260p' scripts/loop_dashboard_evaluator.py
```

Expected: identify existing functions for service startup, HTTP checks, and browser checks.

- [ ] **Step 2: Add parent/child fixture seeding function**

In `scripts/loop_dashboard_evaluator.py`, add a function that creates a parent run, two child runs, a single legacy run, relationship conflict fixture, and events with fake secrets:

```python
def seed_demand_multi_task_dashboard_fixture(repo_root: Path) -> None:
    parent_dir = repo_root / ".codex" / "loop-runs" / "parent-run"
    write_json(
        parent_dir / "run.json",
        {
            "run_id": "parent-run",
            "run_kind": "parent",
            "policy": "demand_development",
            "phase": "child_running",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "验证需求开发多子任务 loop 看板",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
            "baseline_dirty_paths": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "attempts": {"planner": 2, "generator": 0, "evaluator": 0, "artifact_hygiene": 0, "cleanup": 0},
            "limits": {},
            "last_result": "none",
            "next_action": "run_parent_planner",
            "attempt_history": [],
            "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
            "child_run_ids": ["parent-run-child-001", "parent-run-child-002", "missing-child"],
            "current_child_run_id": "parent-run-child-002",
            "backlog": [],
            "aggregate_acceptance": {"total": 2, "passed": 1, "failed": 0, "blocked": 0, "pending": 1, "user_decision_required": False},
            "reader_summary": {"purpose": "验证父需求读者摘要", "current_progress": "一个子任务已通过", "next_step": "继续子任务 2", "decision_needed": "不需要"},
            "accepted_changed_paths": ["generated/child-001.txt"],
        },
    )
    for index, phase in [(1, "passed"), (2, "generating")]:
        child_id = f"parent-run-child-{index:03d}"
        child_dir = repo_root / ".codex" / "loop-runs" / child_id
        write_json(
            child_dir / "run.json",
            {
                "run_id": child_id,
                "run_kind": "child",
                "parent_run_id": "parent-run",
                "child_index": index,
                "policy": "demand_development",
                "phase": phase,
                "task_id": f"{child_id}-task",
                "domain": "",
                "branch": "main",
                "worktree": str(repo_root),
                "requirement": f"子任务 {index} 的完整长描述，用于验证看板换行和可读性，不允许被截断。",
                "constraints": [],
                "stop_conditions": ["passed"],
                "baseline_dirty_paths": [],
                "allowed_paths": [f"generated/child-{index:03d}.txt"],
                "denylist_paths": [],
                "attempts": {"planner": 1, "generator": 1, "evaluator": 1 if phase == "passed" else 0, "artifact_hygiene": 0, "cleanup": 0},
                "limits": {},
                "last_result": "pass" if phase == "passed" else "none",
                "next_action": "return_to_parent_planner" if phase == "passed" else "run_child_generator",
                "attempt_history": [],
                "cleanup": {"worktrees_removed": [], "processes_stopped": [], "retained_artifacts": []},
                "reader_summary": {
                    "purpose": f"子任务 {index}",
                    "planner_action": "Planner 选择了这个子任务",
                    "generator_action": "Generator 写入了验证文件",
                    "evaluator_action": "Evaluator 模拟用户检查",
                    "acceptance_result": "通过" if phase == "passed" else "等待",
                },
            },
        )
        (child_dir / "events.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": "2026-07-03T00:00:00Z",
                    "run_id": child_id,
                    "parent_run_id": "parent-run",
                    "child_id": f"child-{index:03d}",
                    "actor": "planner",
                    "event_type": "plan",
                    "summary": f"Planner selected child {index}; Authorization: Bearer secret-token",
                    "details": {},
                    "artifact_paths": [],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    write_json(
        repo_root / ".codex" / "loop-runs" / "legacy-single" / "run.json",
        {
            "run_id": "legacy-single",
            "policy": "demand_development",
            "phase": "passed_waiting_human_merge",
            "task_id": "legacy-task",
            "domain": "",
            "branch": "main",
            "worktree": str(repo_root),
            "requirement": "旧 single run",
            "constraints": [],
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
    conflict_path = repo_root / ".codex" / "loop-runs" / "conflict-parent" / "run.json"
    conflict_payload = json.loads((parent_dir / "run.json").read_text(encoding="utf-8"))
    conflict_payload["run_id"] = "conflict-parent"
    conflict_payload["child_run_ids"] = ["parent-run-child-001"]
    write_json(conflict_path, conflict_payload)
```

Call `seed_demand_multi_task_dashboard_fixture(fixture_root)` inside `seed_fixture_project(project_root: Path)` after the existing `seed_rich_evaluator_result(project_root)` call.

- [ ] **Step 3: Extend evaluator checks**

Add checks to the evaluator main flow:

```python
def verify_demand_multi_task_api(base_url: str) -> dict[str, object]:
    with urllib.request.urlopen(f"{base_url}/api/runs", timeout=5) as response:
        runs = json.loads(response.read().decode("utf-8"))
    if not isinstance(runs, list):
        raise AssertionError("/api/runs should return a JSON list")
    parent = next(run for run in runs if run["run_id"] == "parent-run")
    assert parent["run_kind"] == "parent"
    assert parent["children_summary"]["total"] >= 2
    detail = read_json_url(f"{base_url}/api/runs/parent-run")
    assert detail["children"]
    assert detail["reader_summary"]["purpose"]
    assert "relationship_diagnostics" in detail
    events = read_json_url(f"{base_url}/api/runs/parent-run/events")["events"]
    assert any(event["kind"] == "plan" for event in events)
    assert all("secret-token" not in str(event) for event in events)
    try:
        urllib.request.urlopen(f"{base_url}/api/runs/..%2Foutside", timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("path traversal run lookup should return 404")
    return {"parent_children": len(detail["children"]), "events": len(events)}
```

Call `verify_demand_multi_task_api(dashboard_url)` in `main()` after `wait_for_dashboard(...)` and before `run_browser_checks(...)`. Add its return value to `result.json` under `"demand_multi_task_api"`.

- [ ] **Step 4: Add browser checks for desktop and mobile**

Extend the existing `run_browser_checks(dashboard_url: str, output_dir: Path)` function in `scripts/loop_dashboard_evaluator.py`. After the current `expect(page.get_by_test_id("run-list")).to_contain_text("loop-dashboard-dev")` assertion, add:

```python
            page.get_by_role("button").filter(has_text="parent-run").first.click()
            parent_detail = page.get_by_test_id("run-detail")
            expect(parent_detail).to_contain_text("父需求读者摘要")
            expect(parent_detail).to_contain_text("子任务队列")
            expect(parent_detail).to_contain_text("验证父需求读者摘要")
            expect(parent_detail).to_contain_text("parent-run-child-001")
            expect(parent_detail).to_contain_text("parent-run-child-002")
            expect(parent_detail).to_contain_text("Planner 选择了这个子任务")
            expect(parent_detail).to_contain_text("Evaluator 模拟用户检查")
            tabs.get_by_role("tab", name="阻塞诊断").click()
            expect(page.get_by_test_id("blocked-diagnostics")).to_contain_text("child_artifact_missing")
            tabs.get_by_role("tab", name="日志").click()
            expect(page.get_by_test_id("log-list")).to_contain_text("Planner selected child 1")
            page.get_by_test_id("log-keyword-filter").fill("secret-token")
            expect(page.get_by_test_id("log-list")).to_contain_text("没有匹配的日志")
            if "secret-token" in page.content():
                raise AssertionError("dashboard rendered an unredacted fixture token")
            page.set_viewport_size({"width": 390, "height": 844})
            expect(parent_detail).to_contain_text("父需求读者摘要")
            expect(parent_detail).to_contain_text("子任务队列")
            overflow_after_parent = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if overflow_after_parent:
                raise AssertionError("parent/child dashboard has horizontal overflow at 390px viewport width")
```

The evaluator must fail if this browser check cannot run. Do not convert missing browser support into a pass.

- [ ] **Step 5: Run evaluator**

Run:

```bash
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/demand-multi-task
```

Expected: PASS, with `result.json` and browser screenshot artifacts in `.codex/loop-dashboard-eval/demand-multi-task`.

- [ ] **Step 6: Commit evaluator**

```bash
git add scripts/loop_dashboard_evaluator.py
git commit -m "test(loop-dashboard): evaluate demand parent child UI"
```

## Task 8: Final Regression And Self-Hosted Loop Validation

**Files:**
- No planned file edits. If a regression command fails, edit only the source or test file named by that failure and rerun the failed command before continuing.

- [ ] **Step 1: Run contract and orchestrator tests**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_loop_contracts -v
python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v
```

Expected: PASS.

- [ ] **Step 2: Run dashboard backend tests**

Run:

```bash
PYTHONPATH=apps/loop_dashboard/backend python3 -m pytest -q apps/loop_dashboard/backend/tests
```

Expected: PASS.

- [ ] **Step 3: Run evaluator scenario regression**

Run:

```bash
python3 -m unittest scripts.tests.test_harness_evaluator_scenarios -v
```

Expected: PASS.

- [ ] **Step 4: Run full scripts unit suite**

Run:

```bash
python3 -m unittest discover scripts/tests -v
```

Expected: PASS. On failure, record the failing test id and first assertion/error line in the implementation notes, then fix it when the failure touches files in this plan. Stop and ask the user only when the failing test is unrelated to this plan and cannot be isolated with a focused passing command from Steps 1-3.

- [ ] **Step 5: Run dashboard evaluator**

Run:

```bash
python3 scripts/loop_dashboard_evaluator.py --repo-root . --output-dir .codex/loop-dashboard-eval/demand-multi-task-final
```

Expected: PASS.

- [ ] **Step 6: Run a self-hosted fake demand multi-task loop**

Create a disposable repo under `/tmp` and run:

```bash
export SELF_CHECK_REPO="$(mktemp -d)"
trap 'rm -rf "$SELF_CHECK_REPO"' EXIT
git init "$SELF_CHECK_REPO"
PYTHONPATH=. python3 scripts/harness_loop_orchestrator.py preflight --repo-root "$SELF_CHECK_REPO" --mode demand-development --requirement "Self-check demand multi-task loop" --run-id demand-multi-task-self-check --confirm
python3 - <<'PY'
import os
from pathlib import Path
from scripts.harness_loop_contracts import read_json_file, run_dir_for, write_json_file
repo = Path(os.environ["SELF_CHECK_REPO"])
path = run_dir_for(repo, "demand-multi-task-self-check") / "run.json"
payload = read_json_file(path)
payload["run_kind"] = "parent"
payload["phase"] = "planning"
payload["next_action"] = "run_parent_planner"
payload["child_run_ids"] = []
payload["current_child_run_id"] = ""
payload["backlog"] = []
payload["aggregate_acceptance"] = {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "pending": 0, "user_decision_required": False}
payload["reader_summary"] = {"purpose": "Self-check", "current_progress": "Planning", "next_step": "Run fake children", "decision_needed": "No"}
payload["accepted_changed_paths"] = []
write_json_file(path, payload)
PY
PYTHONPATH=. python3 scripts/harness_loop_orchestrator.py run-demand-multi --repo-root "$SELF_CHECK_REPO" --run-id demand-multi-task-self-check --planner-driver fake --generator-driver fake --evaluator-driver fake --max-children 2
python3 - <<'PY'
import os
from pathlib import Path
from scripts.harness_loop_contracts import read_json_file, run_dir_for
repo = Path(os.environ["SELF_CHECK_REPO"])
payload = read_json_file(run_dir_for(repo, "demand-multi-task-self-check") / "run.json")
assert payload["phase"] == "passed_waiting_human_merge", payload
assert len(payload["child_run_ids"]) == 2, payload
PY
```

Expected: command exits 0 after asserting final JSON has `"phase": "passed_waiting_human_merge"` and child count 2. The shell trap removes the disposable directory.

- [ ] **Step 7: Check git diff and whitespace**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors. Status should only include intentional source/test/doc changes and generated evaluator artifacts if intentionally retained for review.

- [ ] **Step 8: Final commit if needed**

If verification fixes produced changes, stage only the implementation files touched by this plan:

```bash
git add tasks.json scripts/harness_loop_contracts.py scripts/harness_loop_orchestrator.py scripts/loop_dashboard_evaluator.py scripts/tests/test_harness_loop_contracts.py scripts/tests/test_harness_loop_orchestrator.py apps/loop_dashboard/backend/loop_dashboard/store.py apps/loop_dashboard/backend/tests/test_store.py apps/loop_dashboard/backend/tests/test_api.py apps/loop_dashboard/frontend/app.js apps/loop_dashboard/frontend/styles.css
git commit -m "fix(harness): complete demand multi-task loop verification"
```

If no changes are needed, do not create an empty commit.

## Implementation Notes

- Keep compatibility with old run artifacts. A missing `run_kind` is `single`.
- Do not auto-merge `main` in demand-development flow.
- Do not introduce child checkpoint commits in Phase 1. Use `accepted_changed_paths`.
- Keep dashboard read-only.
- Use `apply_patch` for manual edits.
- Preserve unrelated dirty wiki/crawler files in the worktree.
- After each task, run the task-specific tests before committing.
