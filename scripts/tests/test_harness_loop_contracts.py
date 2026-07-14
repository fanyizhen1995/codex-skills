import json
import tempfile
import unittest
from pathlib import Path

import scripts.harness_loop_contracts as harness_loop_contracts
from scripts.harness_loop_contracts import (
    default_limits,
    load_loop_policy,
    normalize_policy_id,
    read_json_file,
    run_dir_for,
    validate_agent_attempt_payload,
    validate_audit_report_payload,
    validate_artifact_hygiene_result_payload,
    validate_evaluator_result_payload,
    validate_generator_result_payload,
    validate_loop_policy_payload,
    validate_loop_state_payload,
    validate_planner_output_payload,
    validate_run_payload,
    validate_scenario_command_result_payload,
    validate_task_contract_payload,
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
            "skill_invocations": [],
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
            "skill_invocations": [],
        }

    def _loop_state_payload(self) -> dict:
        return {
            "policy": "autonomous_knowledge",
            "domain": "ai_infra",
            "domain_goal": "Expand wiki coverage",
            "last_planner_decision": "no_action",
            "last_scan_at": "2026-07-02T00:00:00Z",
            "scan_ttl_days": 30,
            "candidate_backlog": [],
            "coverage_gaps": [],
            "known_sources": [
                {
                    "id": "source-1",
                    "title": "Known source",
                    "source": "manual",
                    "status": "scanned",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "evidence": ["checked source index"],
                }
            ],
            "blocked_items": [],
            "no_action_evidence": [
                {
                    "id": "scan-1",
                    "title": "Fresh scan",
                    "source": "planner",
                    "status": "complete",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "evidence": ["no candidates found"],
                }
            ],
        }

    def _coverage_map_payload(self) -> dict:
        now = "2026-07-02T00:00:00Z"
        return {
            "domain": "ai_infra",
            "domain_goal": "Expand wiki coverage",
            "layers": {
                layer: {
                    "status": "covered",
                    "covered_pages": [f"wiki/{layer}.md"],
                    "raw_evidence": [f"raw/{layer}.json"],
                    "candidate_gaps": [],
                    "blocked_reason": "",
                    "last_scanned_at": now,
                    "notes": "",
                }
                for layer in (
                    "training-distributed",
                    "inference-runtime",
                    "orchestration-scheduling",
                    "data-rag-vector",
                    "eval-observability-reliability",
                    "security-governance-cost",
                    "hardware-accelerator",
                    "network-storage-cluster",
                )
            },
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

    def _task_contract_payload(self) -> dict:
        return {
            "task_id": "phase-2-task",
            "title": "Phase 2 task",
            "description": "Exercise task contract bundle preparation.",
            "verify_commands": ["python3 -m unittest scripts.tests.test_harness_loop_contracts -v"],
            "scenario_commands": ["python3 -c \"print('scenario-ok')\""],
            "artifact_paths": ["docs/harness/planner-generator-evaluator-loop.md"],
            "required_services": ["crawler_workbench_backend"],
            "evaluator_driver": "harness_auto_gate",
            "eval_policy": {"task_level_required": True, "task_scope": "local_repo_and_harness"},
            "allowed_scope": "local_repo_and_harness",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "PGE-PHASE2-TASK-CONTRACT",
                    "user_goal": "Prepare an evaluator bundle from a temporary task contract.",
                    "prerequisites": ["Temporary task contract exists."],
                    "steps": ["Run prepare-task with --task-contract."],
                    "expected_outcomes": ["input.json includes scenario commands."],
                    "failure_signals": ["Bundle ignores task contract fields."],
                }
            ],
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

    def test_validate_run_payload_rejects_unknown_policy(self) -> None:
        payload = self._run_payload()
        payload["policy"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown policy"):
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
            "skill_invocations": [],
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
            "skill_invocations": [],
        }
        validate_generator_result_payload(payload)
        payload["changed_paths"] = "not-a-list"
        with self.assertRaises(ValueError):
            validate_generator_result_payload(payload)

    def test_agent_result_contracts_reject_malformed_skill_invocations(self) -> None:
        invocation = {
            "invocation_id": "invocation-alpha",
            "skill_path": "skills/alpha/SKILL.md",
            "artifact_path": ".codex/loop-runs/demo/planner-skill-invocation.json",
            "artifact_sha256": f"sha256:{'a' * 64}",
        }
        planner = {
            "task_id": "demo-task",
            "policy": "demand_development",
            "task_kind": "registered_task",
            "title": "Demo",
            "goal": "Demo goal",
            "non_goals": [],
            "allowed_paths": [],
            "denylist_paths": [],
            "verify_commands": [],
            "evaluator_scenarios_path": "",
            "stop_conditions": [],
            "next_planning_hint": "",
            "skill_invocations": [invocation],
        }
        generator = {
            "task_id": "demo-task",
            "status": "implemented",
            "changed_paths": [],
            "commit": "",
            "verify_commands": [],
            "verify_results": [],
            "artifacts": [],
            "cleanup_required": False,
            "notes": "done",
            "skill_invocations": [invocation],
        }
        evaluator = {
            "status": "pass",
            "task_id": "demo-task",
            "driver": "fake",
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "skill_invocations": [invocation],
        }
        for validator, payload in (
            (validate_planner_output_payload, planner),
            (validate_generator_result_payload, generator),
            (validate_evaluator_result_payload, evaluator),
        ):
            validator(payload)
            missing = json.loads(json.dumps(payload))
            del missing["skill_invocations"]
            with self.assertRaisesRegex(ValueError, "skill_invocations"):
                validator(missing)
            malformed = json.loads(json.dumps(payload))
            malformed["skill_invocations"][0]["artifact_sha256"] = "forged"
            with self.assertRaisesRegex(ValueError, "artifact_sha256"):
                validator(malformed)

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

    def test_validate_coverage_map_payload_accepts_ai_infra_layers(self) -> None:
        payload = self._coverage_map_payload()

        harness_loop_contracts.validate_coverage_map_payload(payload)

    def test_run_dir_for_uses_repo_root_codex_loop_runs(self) -> None:
        root = Path("/tmp/repo")
        self.assertEqual(run_dir_for(root, "demo"), root / ".codex" / "loop-runs" / "demo")

    def test_run_dir_for_rejects_path_escape_run_id(self) -> None:
        root = Path("/tmp/repo")

        with self.assertRaisesRegex(ValueError, "run_id"):
            run_dir_for(root, "../escape")

    def test_validate_run_payload_rejects_path_escape_run_id(self) -> None:
        payload = self._run_payload()
        payload["run_id"] = "../escape"

        with self.assertRaisesRegex(ValueError, "run_id"):
            validate_run_payload(payload)

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

    def test_validate_planner_output_payload_rejects_unknown_policy(self) -> None:
        payload = self._planner_payload()
        payload["policy"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown policy"):
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

    def test_validate_agent_attempt_payload_accepts_auditor_role(self) -> None:
        payload = self._agent_attempt_payload()
        payload["role"] = "auditor"
        validate_agent_attempt_payload(payload)

    def test_validate_agent_attempt_payload_accepts_supervisor_reviewer_role(self) -> None:
        payload = self._agent_attempt_payload()
        payload["role"] = "supervisor_reviewer"
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
            "skill_invocations": [],
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

    def test_validate_task_contract_payload_accepts_phase_2_shape(self) -> None:
        validate_task_contract_payload(self._task_contract_payload())

    def test_validate_task_contract_payload_rejects_missing_scenario_commands(self) -> None:
        payload = self._task_contract_payload()
        del payload["scenario_commands"]
        with self.assertRaisesRegex(ValueError, "scenario_commands"):
            validate_task_contract_payload(payload)

    def test_validate_task_contract_payload_rejects_non_list_required_services(self) -> None:
        payload = self._task_contract_payload()
        payload["required_services"] = "backend"
        with self.assertRaisesRegex(ValueError, "required_services"):
            validate_task_contract_payload(payload)

    def test_validate_task_contract_payload_rejects_non_string_scenario_command(self) -> None:
        payload = self._task_contract_payload()
        payload["scenario_commands"] = [123]
        with self.assertRaisesRegex(ValueError, "scenario_commands\\[0\\]|scenario_commands"):
            validate_task_contract_payload(payload)

    def test_validate_task_contract_payload_rejects_malformed_user_scenario(self) -> None:
        payload = self._task_contract_payload()
        payload["user_scenarios"] = [{}]
        with self.assertRaisesRegex(ValueError, "scenario_id"):
            validate_task_contract_payload(payload)

    def test_validate_scenario_command_result_payload_accepts_command_evidence(self) -> None:
        validate_scenario_command_result_payload(
            {
                "command": "python3 -c \"print('ok')\"",
                "cwd": "/tmp/repo",
                "exit_code": 0,
                "stdout_path": ".codex/loop-runs/demo/scenario-commands/command-1.stdout.log",
                "stderr_path": ".codex/loop-runs/demo/scenario-commands/command-1.stderr.log",
                "duration_seconds": 0,
                "status": "pass",
            }
        )

    def test_validate_scenario_command_result_payload_rejects_unknown_status(self) -> None:
        payload = {
            "command": "python3 -c \"print('ok')\"",
            "cwd": "/tmp/repo",
            "exit_code": 0,
            "stdout_path": "stdout.log",
            "stderr_path": "stderr.log",
            "duration_seconds": 0,
            "status": "success",
        }
        with self.assertRaisesRegex(ValueError, "status"):
            validate_scenario_command_result_payload(payload)

    def test_validate_scenario_command_result_payload_rejects_negative_duration(self) -> None:
        payload = {
            "command": "python3 -c \"print('ok')\"",
            "cwd": "/tmp/repo",
            "exit_code": 0,
            "stdout_path": "stdout.log",
            "stderr_path": "stderr.log",
            "duration_seconds": -1,
            "status": "pass",
        }
        with self.assertRaisesRegex(ValueError, "duration_seconds"):
            validate_scenario_command_result_payload(payload)

    def test_validate_artifact_hygiene_result_payload_accepts_redaction_manifest(self) -> None:
        validate_artifact_hygiene_result_payload(
            {
                "status": "redacted",
                "scanned_paths": ["artifact.txt"],
                "redacted_paths": ["artifact.redacted.txt"],
                "omitted_paths": [],
                "manifest_path": ".codex/loop-runs/demo/artifact-manifest.json",
                "redaction_manifest_path": ".codex/loop-runs/demo/redaction-manifest.json",
                "original_hashes": {"artifact.txt": "abc123"},
                "redaction_map": [{"path": "artifact.txt", "rule_id": "token", "replacement": "[REDACTED]"}],
                "findings": [{"path": "artifact.txt", "severity": "warning", "message": "token redacted"}],
            }
        )

    def test_validate_run_payload_accepts_autonomous_policy(self) -> None:
        payload = self._run_payload()
        payload["policy"] = "autonomous_knowledge"
        payload["phase"] = "planning"
        payload["domain"] = "ai_infra"
        payload["next_action"] = "run_autonomous_planner"
        validate_run_payload(payload)

    def test_validate_planner_output_payload_accepts_autonomous_implementation_task(self) -> None:
        payload = self._planner_payload()
        payload["policy"] = "autonomous_knowledge"
        payload["task_kind"] = "autonomous_implementation_task"
        payload["next_planning_hint"] = "Continue with source backlog."
        validate_planner_output_payload(payload)

    def test_validate_planner_output_payload_rejects_autonomous_task_kind_for_demand_policy(self) -> None:
        payload = self._planner_payload()
        payload["policy"] = "demand_development"
        payload["task_kind"] = "autonomous_implementation_task"
        with self.assertRaisesRegex(ValueError, "autonomous_implementation_task"):
            validate_planner_output_payload(payload)

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

        autonomous_child = self._run_payload()
        autonomous_child.update(
            {
                "policy": "autonomous_knowledge",
                "run_kind": "child",
                "parent_run_id": "demo-parent",
                "child_index": 2,
                "phase": "planning",
                "domain": "ai_infra",
                "policy_file": "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                "next_action": "run_autonomous_planner",
                "reader_summary": {
                    "purpose": "Expansion child",
                    "planner_action": "",
                    "generator_action": "",
                    "evaluator_action": "",
                    "acceptance_result": "",
                },
            }
        )
        validate_run_payload(autonomous_child)

        audit_parent = self._run_payload()
        audit_parent.update(
            {
                "run_kind": "parent",
                "phase": "audit_blocked",
                "current_child_run_id": "",
                "child_run_ids": [],
                "backlog": [],
                "aggregate_acceptance": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "blocked": 0,
                    "pending": 0,
                    "user_decision_required": True,
                },
                "reader_summary": {
                    "purpose": "Build feature",
                    "current_progress": "Audit blocked",
                    "next_step": "Create audit remediation task",
                    "decision_needed": "No",
                },
                "accepted_changed_paths": [],
            }
        )
        validate_run_payload(audit_parent)

    def test_validate_run_payload_rejects_child_audit_blocked_phase(self) -> None:
        child = self._run_payload()
        child.update(
            {
                "run_kind": "child",
                "parent_run_id": "demo-parent",
                "child_index": 1,
                "phase": "audit_blocked",
                "reader_summary": {
                    "purpose": "Child",
                    "planner_action": "Planned child",
                    "generator_action": "Implemented child",
                    "evaluator_action": "Evaluated child",
                    "acceptance_result": "Passed",
                },
            }
        )
        with self.assertRaisesRegex(ValueError, "child phase"):
            validate_run_payload(child)

    def test_validate_audit_report_payload_accepts_pass_and_rejects_unproven_must_fix(self) -> None:
        payload = {
            "schema_version": 1,
            "run_id": "demo",
            "audit_id": "audit-001",
            "created_at": "2026-07-08T00:00:00Z",
            "created_by": "harness_loop_orchestrator",
            "verdict": "pass",
            "deterministic_signals": {
                "artifact_path": ".codex/loop-runs/demo/deterministic-signals.json",
                "artifact_sha256": "a" * 64,
                "summary": {"same_evaluator_finding_count": 0},
            },
            "cadence": {"unit": "boundary", "current_interval": 1, "steps_since_last_audit": 1},
            "direction_control": {"action": "continue", "reason": "healthy"},
            "finding_lifecycle": {"open_findings": [], "closed_findings": []},
        }
        validate_audit_report_payload(payload)

        payload["verdict"] = "must_fix"
        with self.assertRaisesRegex(ValueError, "open must_fix"):
            validate_audit_report_payload(payload)

        closed_must_fix = json.loads(json.dumps(payload))
        closed_must_fix["finding_lifecycle"]["open_findings"] = [
            {
                "finding_id": "audit-001-repeat-001",
                "severity": "must_fix",
                "status": "closed",
                "title": "Closed finding",
                "summary": "A closed finding must not satisfy the open must_fix gate.",
                "required_planner_action": "none",
            }
        ]
        with self.assertRaisesRegex(ValueError, "open must_fix"):
            validate_audit_report_payload(closed_must_fix)

    def test_validate_run_payload_rejects_demand_child_planning_phase(self) -> None:
        child = self._run_payload()
        child.update(
            {
                "run_kind": "child",
                "parent_run_id": "demo-parent",
                "child_index": 1,
                "phase": "planning",
                "next_action": "run_planner",
                "reader_summary": {
                    "purpose": "Demand child",
                    "planner_action": "",
                    "generator_action": "",
                    "evaluator_action": "",
                    "acceptance_result": "",
                },
            }
        )

        with self.assertRaisesRegex(ValueError, "child phase"):
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

        del payload["blocked_reason"]
        with self.assertRaisesRegex(ValueError, "blocked_reason"):
            validate_planner_output_payload(payload)

    def test_validate_loop_state_payload_accepts_no_action_shape(self) -> None:
        validate_loop_state_payload(self._loop_state_payload())

    def test_validate_loop_state_payload_requires_no_action_evidence_for_no_action_decision(self) -> None:
        payload = self._loop_state_payload()
        payload["last_planner_decision"] = "no_action"
        payload["no_action_evidence"] = []
        with self.assertRaisesRegex(ValueError, "no_action_evidence"):
            validate_loop_state_payload(payload)

    def test_validate_loop_state_payload_rejects_unknown_planner_decision(self) -> None:
        payload = self._loop_state_payload()
        payload["last_planner_decision"] = "noop"
        with self.assertRaisesRegex(ValueError, "last_planner_decision"):
            validate_loop_state_payload(payload)

    def test_validate_loop_state_payload_rejects_unblocked_gap_without_evidence(self) -> None:
        payload = self._loop_state_payload()
        payload["coverage_gaps"] = [
            {
                "id": "gap-1",
                "title": "Missing source",
                "source": "manual",
                "status": "pending",
                "updated_at": "2026-07-02T00:00:00Z",
                "evidence": [],
            }
        ]
        with self.assertRaisesRegex(ValueError, "coverage_gaps"):
            validate_loop_state_payload(payload)

    def test_validate_loop_state_payload_rejects_actionable_gap_with_evidence(self) -> None:
        payload = self._loop_state_payload()
        payload["coverage_gaps"] = [
            {
                "id": "gap-1",
                "title": "Missing source",
                "source": "manual",
                "status": "pending",
                "updated_at": "2026-07-02T00:00:00Z",
                "evidence": ["planner found the gap"],
            }
        ]
        with self.assertRaisesRegex(ValueError, "coverage_gaps"):
            validate_loop_state_payload(payload)

    def test_validate_loop_state_payload_rejects_blocked_gap_without_blocked_reason(self) -> None:
        payload = self._loop_state_payload()
        payload["coverage_gaps"] = [
            {
                "id": "gap-1",
                "title": "Missing source",
                "source": "manual",
                "status": "blocked",
                "updated_at": "2026-07-02T00:00:00Z",
                "evidence": ["source requires auth"],
            }
        ]
        with self.assertRaisesRegex(ValueError, "blocked_reason"):
            validate_loop_state_payload(payload)

    def test_validate_loop_state_payload_rejects_blocked_gap_with_non_string_blocked_reason(self) -> None:
        payload = self._loop_state_payload()
        payload["coverage_gaps"] = [
            {
                "id": "gap-1",
                "title": "Missing source",
                "source": "manual",
                "status": "blocked",
                "updated_at": "2026-07-02T00:00:00Z",
                "evidence": ["source requires auth"],
                "blocked_reason": [],
            }
        ]
        with self.assertRaisesRegex(ValueError, "blocked_reason"):
            validate_loop_state_payload(payload)

    def test_validate_loop_policy_payload_accepts_autonomous_policy_file(self) -> None:
        validate_loop_policy_payload(
            {
                "policy": "autonomous_knowledge",
                "auto_commit": True,
                "auto_merge_main": False,
                "allowed_paths": ["personal-wiki/domains/**/wiki/**"],
                "manual_confirm_paths": ["tasks.json"],
                "denylist_paths": [".env", "**/secrets/**"],
                "limits": default_limits(),
                "required_evidence": ["wiki_validate"],
            }
        )

    def test_validate_loop_policy_payload_accepts_demand_policy_file(self) -> None:
        validate_loop_policy_payload(
            {
                "policy": "demand_development",
                "auto_commit": False,
                "auto_merge_main": False,
                "allowed_paths": ["scripts/**", "docs/harness/**"],
                "manual_confirm_paths": ["main"],
                "denylist_paths": [".env", "**/secrets/**"],
                "limits": default_limits(),
                "required_evidence": ["task_evaluator"],
            }
        )

    def test_validate_run_payload_accepts_optional_policy_runtime_metadata(self) -> None:
        payload = self._run_payload()
        payload["policy_file"] = "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json"
        payload["manual_confirm_paths"] = ["tasks.json", "scripts/**"]
        payload["required_evidence"] = ["service availability evidence"]

        validate_run_payload(payload)

    def test_load_loop_policy_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "repo-relative"):
                load_loop_policy(repo_root, "../outside.json")

    def test_load_loop_policy_rejects_mismatched_policy_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            policy_path = repo_root / "policy.json"
            write_json_file(
                policy_path,
                {
                    "policy": "demand-development",
                    "auto_commit": True,
                    "auto_merge_main": False,
                    "allowed_paths": ["**"],
                    "manual_confirm_paths": [],
                    "denylist_paths": [".codex/**"],
                    "limits": default_limits(),
                    "required_evidence": [],
                },
            )

            payload = load_loop_policy(repo_root, "policy.json")

            self.assertEqual(payload["policy"], "demand_development")

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

    def test_supervisor_terminal_phases_are_allowed_contract_phases(self) -> None:
        self.assertEqual(
            harness_loop_contracts.SUPERVISOR_TERMINAL_PHASES,
            frozenset(
                {
                    "audit_passed",
                    "passed",
                    "stopped_no_action",
                    "stopped_by_reviewer",
                }
            ),
        )
        self.assertTrue(
            harness_loop_contracts.SUPERVISOR_TERMINAL_PHASES <= harness_loop_contracts.ALLOWED_PHASES
        )
        self.assertNotIn("passed_waiting_human_merge", harness_loop_contracts.SUPERVISOR_TERMINAL_PHASES)
