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
import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import harness_evaluator_hooks


class HarnessEvaluatorHookTests(unittest.TestCase):
    def test_main_prints_valid_stop_hook_json_when_legacy_cli_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {"cwd": str(root)}
            output = io.StringIO()
            with patch.object(
                harness_evaluator_hooks,
                "stop_hook",
                return_value={
                    "decision": "block",
                    "reason": "rerun task evaluator",
                    "action": "rerun_task_evaluator",
                    "bundle_dir": str(root / "bundle"),
                },
            ), patch("sys.argv", ["harness_evaluator_hooks.py", "stop"]):
                with patch("sys.stdin.read", return_value=json.dumps(payload)):
                    with redirect_stdout(output):
                        exit_code = harness_evaluator_hooks.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(output.getvalue().strip()),
            {
                "continue": False,
                "stopReason": "rerun task evaluator",
            },
        )

    def test_stop_hook_skips_tasks_when_requires_eval_is_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "docs-session.json").write_text(
                json.dumps(
                    {
                        "task": "docs-task",
                        "branch": "task/docs-task",
                        "worktree": str(root),
                        "status": "implementation",
                        "evaluator": {
                            "phase": "implementation",
                            "task_eval_attempt": 0,
                            "last_task_eval_result": "",
                            "final_eval_attempt": 0,
                            "last_final_eval_result": "",
                            "repair_from_eval": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            templates_dir = root / ".codex" / "evaluations" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (templates_dir / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {
                            "task_level_required": True,
                            "final_level_required": True,
                            "task_scope": "code_and_local_k3s",
                            "final_scope": "report_and_artifacts",
                            "max_task_eval_attempts": 3,
                            "max_final_eval_attempts": 2,
                        },
                        "tasks": [
                            {
                                "id": "docs-task",
                                "title": "Docs task",
                                "description": "docs only",
                                "verify": "python3 -m unittest demo -v",
                                "requires_eval": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            decision = harness_evaluator_hooks.stop_hook(root)

            self.assertIsNone(decision)

    def test_stop_hook_auto_prepares_bundle_for_requires_eval_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                        "evaluator": {
                            "phase": "implementation",
                            "task_eval_attempt": 0,
                            "last_task_eval_result": "",
                            "final_eval_attempt": 0,
                            "last_final_eval_result": "",
                            "repair_from_eval": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            templates_dir = root / ".codex" / "evaluations" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (templates_dir / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {
                            "task_level_required": True,
                            "final_level_required": False,
                            "task_scope": "code_and_local_k3s",
                            "final_scope": "report_and_artifacts",
                            "max_task_eval_attempts": 3,
                            "max_final_eval_attempts": 2,
                        },
                        "tasks": [
                            {
                                "id": "demo-task",
                                "title": "Demo task",
                                "description": "demo",
                                "verify": "python3 -m unittest demo -v",
                                "requires_eval": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "demo-task.json").write_text(
                json.dumps(
                    {
                        "task_id": "demo-task",
                        "must_simulate": True,
                        "user_scenarios": [
                            {
                                "scenario_id": "EUS-01",
                                "user_goal": "Run the public flow.",
                                "prerequisites": [],
                                "entrypoint": "python3 scripts/demo.py",
                                "steps": ["Run the command."],
                                "expected_outcomes": ["It exits with status 0."],
                                "failure_signals": ["It exits non-zero."],
                                "cleanup": [],
                                "automation_hint": "shell",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            decision = harness_evaluator_hooks.stop_hook(root)

            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertEqual(decision["decision"], "block")
            self.assertEqual(decision["action"], "run_task_evaluator")
            bundle_dir = Path(decision["bundle_dir"])
            self.assertTrue((bundle_dir / "input.json").exists())
            self.assertIn(".codex/evaluations/tasks/demo-task", decision["bundle_dir"])

    def test_stop_hook_auto_prepares_bundle_from_latest_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                        "evaluator": {
                            "phase": "implementation",
                            "task_eval_attempt": 0,
                            "last_task_eval_result": "",
                            "final_eval_attempt": 0,
                            "last_final_eval_result": "",
                            "repair_from_eval": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            templates_dir = root / ".codex" / "evaluations" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (templates_dir / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {
                            "task_level_required": True,
                            "final_level_required": False,
                            "task_scope": "code_and_local_k3s",
                            "final_scope": "report_and_artifacts",
                            "max_task_eval_attempts": 3,
                            "max_final_eval_attempts": 2,
                        },
                        "tasks": [
                            {
                                "id": "demo-task",
                                "title": "Demo task",
                                "description": "demo",
                                "verify": "python3 -m unittest demo -v",
                                "requires_eval": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "demo-task.json").write_text(
                json.dumps(
                    {
                        "task_id": "demo-task",
                        "must_simulate": True,
                        "user_scenarios": [
                            {
                                "scenario_id": "DOCS-01",
                                "user_goal": "Run the docs scenario.",
                                "prerequisites": [],
                                "entrypoint": "python3 scripts/docs_scenario.py",
                                "steps": ["Run the docs scenario."],
                                "expected_outcomes": ["Docs scenario runs."],
                                "failure_signals": ["Docs scenario fails."],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            loop_root = root / ".codex" / "loop-runs"
            old_contract_dir = loop_root / "old-run"
            latest_contract_dir = loop_root / "latest-run"
            old_contract_dir.mkdir(parents=True)
            latest_contract_dir.mkdir(parents=True)
            contract_payload = {
                "task_id": "demo-task",
                "title": "Demo task",
                "description": "Contract task.",
                "verify_commands": ["python3 -m unittest contract -v"],
                "scenario_commands": ["python3 -c \"print('contract-latest')\""],
                "artifact_paths": ["docs/contract.md"],
                "required_services": ["demo-backend"],
                "evaluator_driver": "harness_auto_gate",
                "eval_policy": {"task_level_required": True, "task_scope": "local_repo_and_harness"},
                "allowed_scope": "local_repo_and_harness",
                "must_simulate": True,
                "user_scenarios": [
                    {
                        "scenario_id": "CONTRACT-LATEST-01",
                        "user_goal": "Run the contract scenario.",
                        "prerequisites": [],
                        "steps": ["Run the contract command."],
                        "expected_outcomes": ["Contract output is present."],
                        "failure_signals": ["Contract command is missing."],
                    }
                ],
            }
            old_payload = dict(contract_payload)
            old_payload["scenario_commands"] = ["python3 -c \"print('contract-old')\""]
            old_payload["user_scenarios"] = [
                {
                    "scenario_id": "CONTRACT-OLD-01",
                    "user_goal": "Run the old contract scenario.",
                    "prerequisites": [],
                    "steps": ["Run the old contract command."],
                    "expected_outcomes": ["Old contract output is present."],
                    "failure_signals": ["Old contract command is missing."],
                }
            ]
            old_contract = old_contract_dir / "task-contract.json"
            latest_contract = latest_contract_dir / "task-contract.json"
            old_contract.write_text(json.dumps(old_payload), encoding="utf-8")
            latest_contract.write_text(json.dumps(contract_payload), encoding="utf-8")
            old_mtime = 1_800_000_000
            latest_mtime = old_mtime + 10
            os.utime(old_contract, (old_mtime, old_mtime))
            os.utime(latest_contract, (latest_mtime, latest_mtime))

            decision = harness_evaluator_hooks.stop_hook(root)

            self.assertIsNotNone(decision)
            assert decision is not None
            bundle_dir = Path(decision["bundle_dir"])
            input_payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(input_payload["scenario_source"], str(latest_contract))
            self.assertEqual(input_payload["scenario_commands"], ["python3 -c \"print('contract-latest')\""])
            self.assertEqual(input_payload["artifact_paths"], ["docs/contract.md"])
            self.assertEqual(input_payload["required_services"], ["demo-backend"])
            self.assertEqual(input_payload["allowed_scope"], "local_repo_and_harness")
            self.assertEqual(input_payload["user_scenarios"][0]["scenario_id"], "CONTRACT-LATEST-01")
            self.assertEqual(
                input_payload["user_scenarios"][0]["entrypoint"],
                "python3 -c \"print('contract-latest')\"",
            )

    def test_stop_hook_auto_prepares_next_attempt_after_fail_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                        "evaluator": {
                            "phase": "repair_after_task_eval_fail",
                            "task_eval_attempt": 1,
                            "last_task_eval_result": "fail",
                            "final_eval_attempt": 0,
                            "last_final_eval_result": "",
                            "repair_from_eval": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            templates_dir = root / ".codex" / "evaluations" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (templates_dir / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {
                            "task_level_required": True,
                            "final_level_required": False,
                            "task_scope": "code_and_local_k3s",
                            "final_scope": "report_and_artifacts",
                            "max_task_eval_attempts": 3,
                            "max_final_eval_attempts": 2,
                        },
                        "tasks": [
                            {
                                "id": "demo-task",
                                "title": "Demo task",
                                "description": "demo",
                                "verify": "python3 -m unittest demo -v",
                                "requires_eval": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            scenario_payload = {
                "task_id": "demo-task",
                "must_simulate": True,
                "user_scenarios": [
                    {
                        "scenario_id": "EUS-01",
                        "user_goal": "Run the public flow.",
                        "prerequisites": [],
                        "entrypoint": "python3 scripts/demo.py",
                        "steps": ["Run the command."],
                        "expected_outcomes": ["It exits with status 0."],
                        "failure_signals": ["It exits non-zero."],
                        "cleanup": [],
                        "automation_hint": "shell",
                    }
                ],
            }
            scenario_path = scenario_dir / "demo-task.json"
            scenario_path.write_text(json.dumps(scenario_payload), encoding="utf-8")
            first_bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260625T000000Z-attempt-1"
            )
            first_bundle.mkdir(parents=True)
            (first_bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "verify_commands": [],
                        "artifact_paths": [],
                        "allowed_scope": "code_and_local_k3s",
                        "must_simulate": True,
                        "scenario_source": str(scenario_path),
                        "user_scenarios": scenario_payload["user_scenarios"],
                    }
                ),
                encoding="utf-8",
            )
            (first_bundle / "result.json").write_text(
                json.dumps(
                    {
                        "status": "fail",
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "summary": "scenario failed",
                        "findings": [
                            {
                                "id": "F-001",
                                "severity": "major",
                                "category": "scenario_failed",
                                "evidence": ["summary.md#EUS-01"],
                                "recommended_action": "repair",
                            }
                        ],
                        "scenario_results": [
                            {
                                "scenario_id": "EUS-01",
                                "status": "fail",
                                "evidence": ["summary.md#EUS-01"],
                                "notes": "scenario failed",
                            }
                        ],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "scenario failed",
                        "next_action": "repair_and_reevaluate",
                    }
                ),
                encoding="utf-8",
            )

            decision = harness_evaluator_hooks.stop_hook(root)

            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertEqual(decision["decision"], "block")
            self.assertEqual(decision["action"], "rerun_task_evaluator")
            bundle_dir = Path(decision["bundle_dir"])
            self.assertTrue((bundle_dir / "input.json").exists())
            self.assertTrue(decision["bundle_dir"].endswith("-attempt-2"))

    def test_stop_hook_auto_prepares_next_attempt_when_latest_result_schema_is_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                        "evaluator": {
                            "phase": "repair_after_task_eval_fail",
                            "task_eval_attempt": 1,
                            "last_task_eval_result": "fail",
                            "final_eval_attempt": 0,
                            "last_final_eval_result": "",
                            "repair_from_eval": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            templates_dir = root / ".codex" / "evaluations" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (templates_dir / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {
                            "task_level_required": True,
                            "final_level_required": False,
                            "task_scope": "code_and_local_k3s",
                            "final_scope": "report_and_artifacts",
                            "max_task_eval_attempts": 3,
                            "max_final_eval_attempts": 2,
                        },
                        "tasks": [
                            {
                                "id": "demo-task",
                                "title": "Demo task",
                                "description": "demo",
                                "verify": "python3 -m unittest demo -v",
                                "requires_eval": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            scenario_payload = {
                "task_id": "demo-task",
                "must_simulate": True,
                "user_scenarios": [
                    {
                        "scenario_id": "EUS-01",
                        "user_goal": "Run the public flow.",
                        "prerequisites": [],
                        "entrypoint": "python3 scripts/demo.py",
                        "steps": ["Run the command."],
                        "expected_outcomes": ["It exits with status 0."],
                        "failure_signals": ["It exits non-zero."],
                        "cleanup": [],
                        "automation_hint": "shell",
                    }
                ],
            }
            scenario_path = scenario_dir / "demo-task.json"
            scenario_path.write_text(json.dumps(scenario_payload), encoding="utf-8")
            first_bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260625T000000Z-attempt-1"
            )
            first_bundle.mkdir(parents=True)
            (first_bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "verify_commands": [],
                        "artifact_paths": [],
                        "allowed_scope": "code_and_local_k3s",
                        "must_simulate": True,
                        "scenario_source": str(scenario_path),
                        "user_scenarios": scenario_payload["user_scenarios"],
                    }
                ),
                encoding="utf-8",
            )
            (first_bundle / "result.json").write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "gate": "task",
                        "task_id": "demo-task",
                        "attempt": 1,
                        "summary": "legacy payload missing new fields",
                        "findings": [],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "legacy payload",
                        "next_action": "proceed_to_user_acceptance",
                    }
                ),
                encoding="utf-8",
            )

            decision = harness_evaluator_hooks.stop_hook(root)

            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertEqual(decision["decision"], "block")
            self.assertEqual(decision["action"], "rerun_task_evaluator")
            self.assertTrue(decision["bundle_dir"].endswith("-attempt-2"))

    def test_stop_hook_enters_final_gate_after_task_pass_when_final_eval_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                        "evaluator": {
                            "phase": "task_evaluator_passed",
                            "task_eval_attempt": 1,
                            "last_task_eval_result": "pass",
                            "final_eval_attempt": 0,
                            "last_final_eval_result": "",
                            "repair_from_eval": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            templates_dir = root / ".codex" / "evaluations" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (templates_dir / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {
                            "task_level_required": True,
                            "final_level_required": False,
                            "task_scope": "code_and_local_k3s",
                            "final_scope": "report_and_artifacts",
                            "max_task_eval_attempts": 3,
                            "max_final_eval_attempts": 2,
                        },
                        "tasks": [
                            {
                                "id": "demo-task",
                                "title": "Demo task",
                                "description": "demo",
                                "verify": "python3 -m unittest demo -v",
                                "requires_eval": True,
                                "eval_policy": {
                                    "task_level_required": True,
                                    "final_level_required": True,
                                    "task_scope": "code_and_local_k3s",
                                    "final_scope": "report_and_artifacts",
                                    "max_task_eval_attempts": 3,
                                    "max_final_eval_attempts": 2,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            scenario_payload = {
                "task_id": "demo-task",
                "must_simulate": True,
                "user_scenarios": [
                    {
                        "scenario_id": "EUS-01",
                        "user_goal": "Run the public flow.",
                        "prerequisites": [],
                        "entrypoint": "python3 scripts/demo.py",
                        "steps": ["Run the command."],
                        "expected_outcomes": ["It exits with status 0."],
                        "failure_signals": ["It exits non-zero."],
                        "cleanup": [],
                        "automation_hint": "shell",
                    }
                ],
            }
            scenario_path = scenario_dir / "demo-task.json"
            scenario_path.write_text(json.dumps(scenario_payload), encoding="utf-8")
            task_bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260625T000000Z-attempt-1"
            )
            task_bundle.mkdir(parents=True)
            (task_bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "verify_commands": [],
                        "artifact_paths": [],
                        "allowed_scope": "code_and_local_k3s",
                        "must_simulate": True,
                        "scenario_source": str(scenario_path),
                        "user_scenarios": scenario_payload["user_scenarios"],
                    }
                ),
                encoding="utf-8",
            )
            (task_bundle / "result.json").write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "summary": "scenario passed",
                        "findings": [],
                        "scenario_results": [
                            {
                                "scenario_id": "EUS-01",
                                "status": "pass",
                                "evidence": ["summary.md#EUS-01"],
                                "notes": "scenario passed",
                            }
                        ],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "scenario passed",
                        "next_action": "proceed_to_user_acceptance",
                    }
                ),
                encoding="utf-8",
            )
            (root / "sprint_output.md").write_text("# Sprint\n", encoding="utf-8")
            (root / "progress.md").write_text("# Progress\n", encoding="utf-8")

            decision = harness_evaluator_hooks.stop_hook(root)

            self.assertIsNotNone(decision)
            assert decision is not None
            self.assertEqual(decision["decision"], "block")
            self.assertEqual(decision["action"], "run_final_evaluator")
            bundle_dir = Path(decision["bundle_dir"])
            self.assertTrue((bundle_dir / "input.json").exists())
            payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["gate"], "final")
            self.assertEqual(payload["final_bundle_id"], "demo-task")
            self.assertEqual(payload["task_bundle_paths"], [str(task_bundle)])

    def test_stop_hook_blocks_when_task_eval_bundle_exists_without_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)
            (bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "attempt": 1,
                        "must_simulate": False,
                        "user_scenarios": [],
                    }
                ),
                encoding="utf-8",
            )
            payload = {
                "cwd": str(root),
                "stop_hook_active": False,
                "last_assistant_message": "finished implementation",
            }
            result = subprocess.run(
                ["python3", "scripts/harness_evaluator_hooks.py", "stop"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            decision = json.loads(result.stdout)
            self.assertFalse(decision["continue"])
            self.assertIn("record a result", decision["stopReason"])

    def test_stop_hook_blocks_when_must_simulate_bundle_has_no_user_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)
            (bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "attempt": 1,
                        "must_simulate": True,
                        "scenario_source": "docs/harness/evaluator-scenarios/demo-task.json",
                        "user_scenarios": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", "scripts/harness_evaluator_hooks.py", "stop"],
                input=json.dumps(
                    {
                        "cwd": str(root),
                        "stop_hook_active": False,
                        "last_assistant_message": "ready",
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            decision = json.loads(result.stdout)
            self.assertFalse(decision["continue"])
            self.assertIn("scenario", decision["stopReason"])

    def test_stop_hook_blocks_after_passed_result_when_input_json_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)
            (bundle / "result.json").write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "summary": "ok",
                        "findings": [],
                        "scenario_results": [],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "ok",
                        "next_action": "proceed_to_user_acceptance",
                    }
                ),
                encoding="utf-8",
            )
            payload = {
                "cwd": str(root),
                "stop_hook_active": False,
                "last_assistant_message": "ready for acceptance",
            }
            result = subprocess.run(
                ["python3", "scripts/harness_evaluator_hooks.py", "stop"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            decision = json.loads(result.stdout)
            self.assertFalse(decision["continue"])
            self.assertIn("input.json", decision["stopReason"])

    def test_stop_hook_blocks_when_bundle_input_json_is_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)
            (bundle / "input.json").write_text("{not-json", encoding="utf-8")

            result = subprocess.run(
                ["python3", "scripts/harness_evaluator_hooks.py", "stop"],
                input=json.dumps(
                    {
                        "cwd": str(root),
                        "stop_hook_active": False,
                        "last_assistant_message": "ready",
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            decision = json.loads(result.stdout)
            self.assertFalse(decision["continue"])
            self.assertIn("contract", decision["stopReason"])

    def test_stop_hook_blocks_when_bundle_input_json_has_wrong_top_level_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)
            (bundle / "input.json").write_text("[]", encoding="utf-8")

            result = subprocess.run(
                ["python3", "scripts/harness_evaluator_hooks.py", "stop"],
                input=json.dumps(
                    {
                        "cwd": str(root),
                        "stop_hook_active": False,
                        "last_assistant_message": "ready",
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            decision = json.loads(result.stdout)
            self.assertFalse(decision["continue"])
            self.assertIn("contract", decision["stopReason"])

    def test_stop_hook_blocks_when_user_scenarios_has_wrong_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)
            (bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "attempt": 1,
                        "must_simulate": True,
                        "scenario_source": "docs/harness/evaluator-scenarios/demo-task.json",
                        "user_scenarios": "not-a-list",
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", "scripts/harness_evaluator_hooks.py", "stop"],
                input=json.dumps(
                    {
                        "cwd": str(root),
                        "stop_hook_active": False,
                        "last_assistant_message": "ready",
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            decision = json.loads(result.stdout)
            self.assertFalse(decision["continue"])
            self.assertIn("contract", decision["stopReason"])

    def test_stop_hook_blocks_when_user_scenarios_entry_is_not_a_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)
            (bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "attempt": 1,
                        "must_simulate": True,
                        "scenario_source": "docs/harness/evaluator-scenarios/demo-task.json",
                        "user_scenarios": ["bad-entry"],
                    }
                ),
                encoding="utf-8",
            )
            (bundle / "result.json").write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "summary": "ok",
                        "findings": [],
                        "scenario_results": [],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "ok",
                        "next_action": "proceed_to_user_acceptance",
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", "scripts/harness_evaluator_hooks.py", "stop"],
                input=json.dumps(
                    {
                        "cwd": str(root),
                        "stop_hook_active": False,
                        "last_assistant_message": "ready",
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            decision = json.loads(result.stdout)
            self.assertFalse(decision["continue"])
            self.assertIn("contract", decision["stopReason"])

    def test_latest_task_bundle_falls_back_to_shared_checkout_for_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shared_root = Path(tmp) / "repo"
            worktree = shared_root / ".worktrees" / "demo-task"
            worktree.mkdir(parents=True)
            state_dir = shared_root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(worktree),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle = (
                shared_root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "20260624T000000Z-attempt-1"
            )
            bundle.mkdir(parents=True)

            with patch.object(
                harness_evaluator_hooks,
                "_current_branch",
                return_value="task/demo-task",
            ), patch.object(
                harness_evaluator_hooks,
                "repo_roots_for_harness",
                return_value=[worktree, shared_root],
                create=True,
            ):
                self.assertEqual(harness_evaluator_hooks.latest_task_bundle(worktree), bundle)

    def test_latest_task_bundle_prefers_real_attempt_bundle_over_fake_attempt_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )
            bundle_root = root / ".codex" / "evaluations" / "tasks" / "demo-task"
            real_bundle = bundle_root / "20260624T094958Z-attempt-4"
            fake_bundle = bundle_root / "fake-attempt-2"
            real_bundle.mkdir(parents=True)
            fake_bundle.mkdir(parents=True)

            self.assertEqual(harness_evaluator_hooks.latest_task_bundle(root), real_bundle)

    def test_latest_task_bundle_prefers_shared_root_real_bundle_over_worktree_fake_bundle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shared_root = Path(tmp) / "repo"
            worktree = shared_root / ".worktrees" / "demo-task"
            worktree.mkdir(parents=True)

            worktree_state_dir = worktree / ".codex" / "session-state"
            worktree_state_dir.mkdir(parents=True)
            (worktree_state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(worktree),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )

            worktree_bundle_root = worktree / ".codex" / "evaluations" / "tasks" / "demo-task"
            shared_bundle_root = shared_root / ".codex" / "evaluations" / "tasks" / "demo-task"
            fake_bundle = worktree_bundle_root / "fake-attempt-2"
            real_bundle = shared_bundle_root / "20260624T094958Z-attempt-4"
            fake_bundle.mkdir(parents=True)
            real_bundle.mkdir(parents=True)

            with patch.object(
                harness_evaluator_hooks,
                "repo_roots_for_harness",
                return_value=[worktree, shared_root],
                create=True,
            ):
                self.assertEqual(harness_evaluator_hooks.latest_task_bundle(worktree), real_bundle)

    def test_latest_task_bundle_prefers_newer_shared_root_real_bundle_over_older_worktree_real_bundle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shared_root = Path(tmp) / "repo"
            worktree = shared_root / ".worktrees" / "demo-task"
            worktree.mkdir(parents=True)

            worktree_state_dir = worktree / ".codex" / "session-state"
            worktree_state_dir.mkdir(parents=True)
            (worktree_state_dir / "demo-session.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(worktree),
                        "status": "implementation",
                    }
                ),
                encoding="utf-8",
            )

            worktree_bundle_root = worktree / ".codex" / "evaluations" / "tasks" / "demo-task"
            shared_bundle_root = shared_root / ".codex" / "evaluations" / "tasks" / "demo-task"
            older_real_bundle = worktree_bundle_root / "20260624T094958Z-attempt-4"
            newer_real_bundle = shared_bundle_root / "20260624T100001Z-attempt-5"
            older_real_bundle.mkdir(parents=True)
            newer_real_bundle.mkdir(parents=True)

            with patch.object(
                harness_evaluator_hooks,
                "repo_roots_for_harness",
                return_value=[worktree, shared_root],
                create=True,
            ):
                self.assertEqual(
                    harness_evaluator_hooks.latest_task_bundle(worktree),
                    newer_real_bundle,
                )

    def test_latest_task_bundle_with_task_id_prefers_worktree_bundle_for_that_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shared_root = Path(tmp) / "repo"
            worktree = shared_root / ".worktrees" / "demo-task"
            worktree.mkdir(parents=True)

            state_dir = shared_root / ".codex" / "session-state"
            state_dir.mkdir(parents=True)
            (state_dir / "usage-session.json").write_text(
                json.dumps(
                    {
                        "task": "usage-task",
                        "branch": "task/demo-task",
                        "worktree": str(worktree),
                        "status": "implementation",
                        "last_update": "2026-06-25T02:00:00+08:00",
                    }
                ),
                encoding="utf-8",
            )
            (state_dir / "infra-session.json").write_text(
                json.dumps(
                    {
                        "task": "infra-task",
                        "branch": "task/demo-task",
                        "worktree": str(worktree),
                        "status": "implementation",
                        "last_update": "2026-06-25T02:30:00+08:00",
                    }
                ),
                encoding="utf-8",
            )

            shared_bundle = (
                shared_root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "infra-task"
                / "20260625T023000Z-attempt-3"
            )
            worktree_bundle = (
                worktree
                / ".codex"
                / "evaluations"
                / "tasks"
                / "usage-task"
                / "20260625T020000Z-attempt-2"
            )
            shared_bundle.mkdir(parents=True)
            worktree_bundle.mkdir(parents=True)

            with patch.object(
                harness_evaluator_hooks,
                "repo_roots_for_harness",
                return_value=[worktree, shared_root],
                create=True,
            ), patch.object(
                harness_evaluator_hooks,
                "_maybe_current_branch",
                return_value="task/demo-task",
            ):
                self.assertEqual(
                    harness_evaluator_hooks.latest_task_bundle(worktree, task_id="usage-task"),
                    worktree_bundle,
                )
