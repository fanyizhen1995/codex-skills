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
    validate_evaluator_result_payload,
    validate_generator_result_payload,
    validate_planner_output_payload,
    validate_run_payload,
    write_json_file,
)


class HarnessLoopContractsTests(unittest.TestCase):
    def _run_payload(self) -> dict:
        return {
            "run_id": "demo",
            "policy": "demand_development",
            "phase": "preflight",
            "task_id": "",
            "domain": "",
            "branch": "main",
            "worktree": "/tmp/repo",
            "requirement": "Demo requirement",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
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

    def _planner_payload(self) -> dict:
        return {
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

    def _generator_payload(self) -> dict:
        return {
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

    def _agent_attempt_payload(self) -> dict:
        return {
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
            "requirement": "Demo requirement",
            "constraints": [],
            "stop_conditions": ["passed_waiting_human_merge"],
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

    def test_validate_run_payload_rejects_phase_1_autonomous_policy(self) -> None:
        payload = self._run_payload()
        payload["policy"] = "autonomous_knowledge"
        with self.assertRaisesRegex(ValueError, "demand_development"):
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
            self.assertEqual(write_json_file(path, {"ok": True}), path)
            self.assertEqual(read_json_file(path), {"ok": True})

    def test_read_json_file_rejects_non_object_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"
            path.write_text(json.dumps([1, 2]), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_json_file(path)

    def test_run_dir_for_uses_repo_root_codex_loop_runs(self) -> None:
        root = Path("/tmp/repo")
        self.assertEqual(run_dir_for(root, "demo"), root / ".codex" / "loop-runs" / "demo")

    def test_validate_run_payload_accepts_phase_1_run_phases(self) -> None:
        for phase in ("planned", "passed_waiting_human_merge"):
            payload = self._run_payload()
            payload["phase"] = phase
            validate_run_payload(payload)

    def test_validate_run_payload_requires_phase_1_attempt_keys(self) -> None:
        for attempt_key in ("artifact_hygiene", "cleanup"):
            payload = self._run_payload()
            del payload["attempts"][attempt_key]
            with self.assertRaises(ValueError):
                validate_run_payload(payload)

    def test_validate_run_payload_uses_phase_1_last_result_values(self) -> None:
        for last_result in ("pass", "fail"):
            payload = self._run_payload()
            payload["last_result"] = last_result
            validate_run_payload(payload)
        payload = self._run_payload()
        payload["last_result"] = "success"
        with self.assertRaises(ValueError):
            validate_run_payload(payload)

    def test_validate_planner_output_payload_uses_phase_1_task_kinds(self) -> None:
        for task_kind in ("registered_task", "candidate_task", "task_contract_only"):
            payload = self._planner_payload()
            payload["task_kind"] = task_kind
            validate_planner_output_payload(payload)
        payload = self._planner_payload()
        payload["task_kind"] = "ad_hoc_task"
        with self.assertRaises(ValueError):
            validate_planner_output_payload(payload)

    def test_validate_planner_output_payload_rejects_phase_1_autonomous_policy(self) -> None:
        payload = self._planner_payload()
        payload["policy"] = "autonomous_knowledge"
        with self.assertRaisesRegex(ValueError, "demand_development"):
            validate_planner_output_payload(payload)

    def test_validate_planner_output_payload_rejects_phase_1_autonomous_task_kind(self) -> None:
        payload = self._planner_payload()
        payload["task_kind"] = "autonomous_implementation_task"
        with self.assertRaisesRegex(ValueError, "autonomous_implementation_task"):
            validate_planner_output_payload(payload)

    def test_validate_generator_result_payload_accepts_repaired_status(self) -> None:
        payload = self._generator_payload()
        payload["status"] = "repaired"
        validate_generator_result_payload(payload)

    def test_validate_generator_result_payload_accepts_blocked_and_failed_statuses(self) -> None:
        for status in ("blocked", "failed"):
            payload = self._generator_payload()
            payload["status"] = status
            validate_generator_result_payload(payload)

    def test_validate_agent_attempt_payload_accepts_generator_and_evaluator_roles(self) -> None:
        for role in ("generator", "evaluator"):
            payload = self._agent_attempt_payload()
            payload["role"] = role
            validate_agent_attempt_payload(payload)

    def test_validate_agent_attempt_payload_rejects_non_positive_attempt(self) -> None:
        for attempt in (0, -1):
            payload = self._agent_attempt_payload()
            payload["attempt"] = attempt
            with self.assertRaises(ValueError):
                validate_agent_attempt_payload(payload)

    def test_validate_agent_attempt_payload_uses_phase_1_roles_and_statuses(self) -> None:
        for status in ("pass", "fail", "invalid_json"):
            payload = self._agent_attempt_payload()
            payload["status"] = status
            validate_agent_attempt_payload(payload)
        payload = self._agent_attempt_payload()
        payload["status"] = "success"
        with self.assertRaises(ValueError):
            validate_agent_attempt_payload(payload)
        payload = self._agent_attempt_payload()
        payload["role"] = "cleanup"
        with self.assertRaises(ValueError):
            validate_agent_attempt_payload(payload)

    def test_validate_run_payload_requires_requirement_constraints_and_stop_conditions(self) -> None:
        payload = self._run_payload()
        validate_run_payload(payload)
        for key in ("requirement", "constraints", "stop_conditions"):
            invalid = self._run_payload()
            del invalid[key]
            with self.assertRaises(ValueError):
                validate_run_payload(invalid)

    def test_validate_run_payload_requires_constraints_and_stop_conditions_lists(self) -> None:
        payload = self._run_payload()
        payload["constraints"] = "keep scope tight"
        with self.assertRaisesRegex(ValueError, "constraints"):
            validate_run_payload(payload)
        payload = self._run_payload()
        payload["stop_conditions"] = "passed_waiting_human_merge"
        with self.assertRaisesRegex(ValueError, "stop_conditions"):
            validate_run_payload(payload)

    def test_validate_evaluator_result_payload_accepts_loop_level_shape(self) -> None:
        payload = {
            "status": "pass",
            "task_id": "demo-task",
            "driver": "fake",
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
        }
        validate_evaluator_result_payload(payload)

    def test_validate_evaluator_result_payload_rejects_unknown_status(self) -> None:
        payload = {
            "status": "success",
            "task_id": "demo-task",
            "driver": "fake",
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
        }
        with self.assertRaisesRegex(ValueError, "status"):
            validate_evaluator_result_payload(payload)

    def test_validate_evaluator_result_payload_requires_returncode_int(self) -> None:
        payload = {
            "status": "blocked",
            "task_id": "demo-task",
            "driver": "fake",
            "returncode": "1",
            "stdout": "",
            "stderr": "blocked",
        }
        with self.assertRaisesRegex(ValueError, "returncode"):
            validate_evaluator_result_payload(payload)

    def test_default_limits_returns_phase_1_limit_keys(self) -> None:
        self.assertEqual(
            default_limits(),
            {
                "max_tasks_per_run": 3,
                "max_generator_attempts_per_task": 2,
                "max_eval_attempts_per_task": 3,
                "max_wall_time_minutes": 60,
                "max_no_action_rounds": 1,
                "agent_timeout_minutes": 30,
                "cleanup_retention_days": 7,
            },
        )
