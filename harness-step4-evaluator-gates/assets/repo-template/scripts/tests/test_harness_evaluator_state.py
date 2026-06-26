# Copyright 2024 The HAMi Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import tempfile
import unittest
from pathlib import Path

from scripts.harness_evaluator_state import (
    find_active_session_state,
    resolve_effective_eval_policy,
    validate_task_eval_result_against_input,
    validate_eval_result_payload,
)


class HarnessEvaluatorStateTests(unittest.TestCase):
    def test_resolve_effective_eval_policy_defaults_from_requires_eval(self) -> None:
        task = {"id": "demo", "requires_eval": True}
        defaults = {
            "task_level_required": True,
            "final_level_required": False,
            "task_scope": "code_and_local_k3s",
            "final_scope": "report_and_artifacts",
            "max_task_eval_attempts": 3,
            "max_final_eval_attempts": 2,
            "scopes": ["code", "artifacts"],
        }
        policy = resolve_effective_eval_policy(task, defaults)
        self.assertEqual(policy, defaults)
        self.assertIsNot(policy, defaults)

        policy["task_scope"] = "changed"
        self.assertEqual(defaults["task_scope"], "code_and_local_k3s")
        policy["scopes"].append("local_k3s")
        self.assertEqual(defaults["scopes"], ["code", "artifacts"])

    def test_resolve_effective_eval_policy_turns_off_gates_when_requires_eval_false(self) -> None:
        task = {"id": "docs-only", "requires_eval": False}
        defaults = {
            "task_level_required": True,
            "final_level_required": True,
            "task_scope": "code_and_local_k3s",
            "final_scope": "report_and_artifacts",
            "max_task_eval_attempts": 3,
            "max_final_eval_attempts": 2,
        }
        policy = resolve_effective_eval_policy(task, defaults)
        self.assertFalse(policy["task_level_required"])
        self.assertFalse(policy["final_level_required"])

    def test_find_active_session_state_matches_current_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            matching_payload = {
                "task": "demo-task",
                "branch": "task/demo-task",
                "worktree": str(root),
                "status": "implementation",
            }
            (state_dir / "match.json").write_text(json.dumps(matching_payload), encoding="utf-8")
            state = find_active_session_state(root, "task/demo-task", state_dir)
            self.assertEqual(state, matching_payload)

    def test_find_active_session_state_rejects_same_worktree_wrong_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            same_worktree_wrong_branch = {
                "task": "wrong-branch-task",
                "branch": "task/other-task",
                "worktree": str(root),
                "status": "implementation",
            }
            (state_dir / "same-worktree-wrong-branch.json").write_text(
                json.dumps(same_worktree_wrong_branch), encoding="utf-8"
            )

            with self.assertRaises(FileNotFoundError):
                find_active_session_state(root, "task/demo-task", state_dir)

    def test_find_active_session_state_rejects_same_branch_wrong_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            other_worktree = root / "other-worktree"
            other_worktree.mkdir()
            same_branch_wrong_worktree = {
                "task": "wrong-worktree-task",
                "branch": "task/demo-task",
                "worktree": str(other_worktree),
                "status": "implementation",
            }
            (state_dir / "same-branch-wrong-worktree.json").write_text(
                json.dumps(same_branch_wrong_worktree), encoding="utf-8"
            )

            with self.assertRaises(FileNotFoundError):
                find_active_session_state(root, "task/demo-task", state_dir)

    def test_validate_eval_result_payload_rejects_missing_recommended_action(self) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "missing fields",
                    "findings": [
                        {
                            "id": "F-001",
                            "severity": "major",
                            "category": "missing_verification",
                            "evidence": ["summary.md"],
                        }
                    ],
                    "scenario_results": [],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "missing action",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_non_mapping_top_level_payload(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload([])

    def test_validate_eval_result_payload_rejects_non_list_findings_container(self) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad findings container",
                    "findings": {"id": "F-001"},
                    "scenario_results": [],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad findings container",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_non_mapping_finding_entry(self) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad finding entry",
                    "findings": ["bad-entry"],
                    "scenario_results": [],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad finding entry",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_invalid_top_level_status(self) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "maybe",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad status",
                    "findings": [],
                    "scenario_results": [],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad status",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_invalid_top_level_gate(self) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task-or-final",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad gate",
                    "findings": [],
                    "scenario_results": [],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad gate",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_invalid_top_level_next_action(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad next_action",
                    "findings": [],
                    "scenario_results": [],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad next_action",
                    "next_action": "ship_it",
                }
            )

    def test_validate_eval_result_payload_rejects_non_list_scenario_evidence(self) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad evidence shape",
                    "findings": [],
                    "scenario_results": [
                        {
                            "scenario_id": "EUS-01",
                            "status": "fail",
                            "evidence": "summary.md#EUS-01",
                        }
                    ],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad evidence shape",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_non_list_scenario_results_container(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad scenario_results container",
                    "findings": [],
                    "scenario_results": {"scenario_id": "EUS-01"},
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad scenario_results container",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_non_mapping_scenario_result_entry(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad scenario_result entry",
                    "findings": [],
                    "scenario_results": ["bad-entry"],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad scenario_result entry",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_non_string_scenario_evidence_item(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad evidence item type",
                    "findings": [],
                    "scenario_results": [
                        {
                            "scenario_id": "EUS-01",
                            "status": "fail",
                            "evidence": ["summary.md#EUS-01", 42],
                        }
                    ],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad evidence item type",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_invalid_scenario_result_status(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "task",
                    "task_id": "demo-task",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "summary": "bad scenario status",
                    "findings": [],
                    "scenario_results": [
                        {
                            "scenario_id": "EUS-01",
                            "status": "unknown",
                            "evidence": ["summary.md#EUS-01"],
                        }
                    ],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "bad scenario status",
                    "next_action": "repair_and_reevaluate",
                }
            )

    def test_validate_eval_result_payload_rejects_duplicate_scenario_ids_globally(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            validate_eval_result_payload(
                {
                    "status": "fail",
                    "gate": "final",
                    "task_id": "",
                    "final_bundle_id": "release-20260624",
                    "attempt": 1,
                    "summary": "duplicate scenario ids",
                    "findings": [],
                    "scenario_results": [
                        {
                            "scenario_id": "EUS-01",
                            "status": "fail",
                            "evidence": ["summary.md#EUS-01-a"],
                        },
                        {
                            "scenario_id": "EUS-01",
                            "status": "blocked",
                            "evidence": ["summary.md#EUS-01-b"],
                        },
                    ],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "duplicate scenario ids",
                    "next_action": "request_missing_evidence",
                }
            )

    def test_validate_task_eval_result_against_input_rejects_pass_without_scenario_results(self) -> None:
        input_payload = {
            "gate": "task",
            "task_id": "demo-task",
            "attempt": 1,
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "EUS-01",
                    "user_goal": "Run the public CLI flow.",
                    "prerequisites": [],
                    "entrypoint": "python3 scripts/demo.py",
                    "steps": ["Run the CLI command."],
                    "expected_outcomes": ["It exits with status 0."],
                    "failure_signals": ["It exits non-zero."],
                    "cleanup": [],
                    "automation_hint": "shell",
                }
            ],
        }
        result_payload = {
            "status": "pass",
            "gate": "task",
            "task_id": "demo-task",
            "final_bundle_id": "",
            "attempt": 1,
            "summary": "missing simulation evidence",
            "findings": [],
            "scenario_results": [],
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": "missing simulation evidence",
            "next_action": "proceed_to_user_acceptance",
        }

        with self.assertRaises(ValueError):
            validate_task_eval_result_against_input(input_payload, result_payload)

    def test_validate_task_eval_result_against_input_accepts_pass_when_all_required_scenarios_pass(
        self,
    ) -> None:
        input_payload = {
            "gate": "task",
            "task_id": "demo-task",
            "attempt": 1,
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "EUS-01",
                    "user_goal": "Run the public CLI flow.",
                    "prerequisites": [],
                    "entrypoint": "python3 scripts/demo.py",
                    "steps": ["Run the CLI command."],
                    "expected_outcomes": ["It exits with status 0."],
                    "failure_signals": ["It exits non-zero."],
                    "cleanup": [],
                    "automation_hint": "shell",
                }
            ],
        }
        result_payload = {
            "status": "pass",
            "gate": "task",
            "task_id": "demo-task",
            "final_bundle_id": "",
            "attempt": 1,
            "summary": "all scenarios passed",
            "findings": [],
            "scenario_results": [
                {
                    "scenario_id": "EUS-01",
                    "status": "pass",
                    "evidence": ["summary.md#EUS-01"],
                    "notes": "CLI command exited with status 0.",
                }
            ],
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": "all required scenarios passed",
            "next_action": "proceed_to_user_acceptance",
        }

        validate_task_eval_result_against_input(input_payload, result_payload)

    def test_validate_task_eval_result_against_input_rejects_result_for_different_task_bundle(
        self,
    ) -> None:
        input_payload = {
            "gate": "task",
            "task_id": "demo-task",
            "attempt": 2,
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "EUS-01",
                    "user_goal": "Run the public CLI flow.",
                    "prerequisites": [],
                    "entrypoint": "python3 scripts/demo.py",
                    "steps": ["Run the CLI command."],
                    "expected_outcomes": ["It exits with status 0."],
                    "failure_signals": ["It exits non-zero."],
                    "cleanup": [],
                    "automation_hint": "shell",
                }
            ],
        }
        result_payload = {
            "status": "pass",
            "gate": "final",
            "task_id": "other-task",
            "final_bundle_id": "release-1",
            "attempt": 1,
            "summary": "wrong bundle",
            "findings": [],
            "scenario_results": [
                {
                    "scenario_id": "EUS-01",
                    "status": "pass",
                    "evidence": ["summary.md#EUS-01"],
                    "notes": "CLI command exited with status 0.",
                }
            ],
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": "mismatched bundle metadata",
            "next_action": "proceed_to_user_acceptance",
        }

        with self.assertRaises(ValueError):
            validate_task_eval_result_against_input(input_payload, result_payload)

    def test_validate_task_eval_result_against_input_rejects_result_for_different_final_bundle(
        self,
    ) -> None:
        input_payload = {
            "gate": "final",
            "task_id": "",
            "final_bundle_id": "release-20260624",
            "attempt": 2,
        }
        result_payload = {
            "status": "pass",
            "gate": "final",
            "task_id": "",
            "final_bundle_id": "release-20260625",
            "attempt": 2,
            "summary": "wrong final bundle",
            "findings": [],
            "scenario_results": [],
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": "mismatched final bundle metadata",
            "next_action": "proceed_with_risk",
        }

        with self.assertRaises(ValueError):
            validate_task_eval_result_against_input(input_payload, result_payload)

    def test_validate_task_eval_result_against_input_rejects_malformed_scenario_result_entry(
        self,
    ) -> None:
        input_payload = {
            "gate": "task",
            "task_id": "demo-task",
            "attempt": 1,
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "EUS-01",
                    "user_goal": "Run the public CLI flow.",
                    "prerequisites": [],
                    "entrypoint": "python3 scripts/demo.py",
                    "steps": ["Run the CLI command."],
                    "expected_outcomes": ["It exits with status 0."],
                    "failure_signals": ["It exits non-zero."],
                    "cleanup": [],
                    "automation_hint": "shell",
                }
            ],
        }
        result_payload = {
            "status": "pass",
            "gate": "task",
            "task_id": "demo-task",
            "final_bundle_id": "",
            "attempt": 1,
            "summary": "malformed scenario result",
            "findings": [],
            "scenario_results": [
                {
                    "status": "pass",
                    "evidence": ["summary.md#EUS-01"],
                }
            ],
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": "missing scenario_id field",
            "next_action": "proceed_to_user_acceptance",
        }

        with self.assertRaises(ValueError):
            validate_task_eval_result_against_input(input_payload, result_payload)

    def test_validate_task_eval_result_against_input_rejects_duplicate_scenario_results(
        self,
    ) -> None:
        input_payload = {
            "gate": "task",
            "task_id": "demo-task",
            "attempt": 1,
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "EUS-01",
                    "user_goal": "Run the public CLI flow.",
                    "prerequisites": [],
                    "entrypoint": "python3 scripts/demo.py",
                    "steps": ["Run the CLI command."],
                    "expected_outcomes": ["It exits with status 0."],
                    "failure_signals": ["It exits non-zero."],
                    "cleanup": [],
                    "automation_hint": "shell",
                }
            ],
        }
        result_payload = {
            "status": "pass",
            "gate": "task",
            "task_id": "demo-task",
            "final_bundle_id": "",
            "attempt": 1,
            "summary": "duplicate scenario entries",
            "findings": [],
            "scenario_results": [
                {
                    "scenario_id": "EUS-01",
                    "status": "fail",
                    "evidence": ["summary.md#EUS-01-fail"],
                },
                {
                    "scenario_id": "EUS-01",
                    "status": "pass",
                    "evidence": ["summary.md#EUS-01-pass"],
                },
            ],
            "rerun_commands": [],
            "environment_checks": [],
            "verdict_reason": "duplicate scenario_result entries",
            "next_action": "repair_and_reevaluate",
        }

        with self.assertRaises(ValueError):
            validate_task_eval_result_against_input(input_payload, result_payload)
