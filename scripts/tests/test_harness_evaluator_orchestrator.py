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
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.harness_evaluator_orchestrator import (
    consume_decision_with_codex_exec,
    _codex_exec_prompt,
    next_loop_action,
    run_one_stop_auto_gate,
    run_codex_exec_auto_task_gate,
    run_fake_auto_task_gate,
    run_fake_task_loop,
)


class HarnessEvaluatorOrchestratorTests(unittest.TestCase):
    def test_next_loop_action_pass_completes_loop(self) -> None:
        decision = next_loop_action("pass", attempt=1, max_attempts=3, gate="task")
        self.assertEqual(decision, "complete")

    def test_next_loop_action_fail_requests_repair_when_attempts_remain(self) -> None:
        decision = next_loop_action("fail", attempt=1, max_attempts=3, gate="task")
        self.assertEqual(decision, "repair")

    def test_next_loop_action_fail_stops_when_attempt_limit_reached(self) -> None:
        decision = next_loop_action("fail", attempt=3, max_attempts=3, gate="task")
        self.assertEqual(decision, "stop")

    def test_next_loop_action_final_fail_is_soft_fail(self) -> None:
        decision = next_loop_action("fail", attempt=1, max_attempts=2, gate="final")
        self.assertEqual(decision, "soft_fail")

    def test_run_fake_task_loop_blocks_when_scenarios_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exit_code = run_fake_task_loop(
                task_id="missing-scenarios-task",
                max_attempts=2,
                repo_root=root,
            )
            self.assertEqual(exit_code, 1)
            blocked_result = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "missing-scenarios-task"
                / "fake-attempt-1"
                / "result.json"
            )
            self.assertTrue(blocked_result.exists())
            self.assertIn(
                '"status": "blocked"',
                blocked_result.read_text(encoding="utf-8"),
            )

    def test_run_fake_task_loop_writes_scenario_results_when_scenarios_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
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
                ),
                encoding="utf-8",
            )
            exit_code = run_fake_task_loop(task_id="demo-task", max_attempts=2, repo_root=root)
            self.assertEqual(exit_code, 0)
            pass_result = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "fake-attempt-2"
                / "result.json"
            )
            self.assertIn('"scenario_id": "EUS-01"', pass_result.read_text(encoding="utf-8"))
            self.assertIn('"status": "pass"', pass_result.read_text(encoding="utf-8"))
            pass_summary = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "demo-task"
                / "fake-attempt-2"
                / "summary.md"
            )
            self.assertIn("## Scenario Results", pass_summary.read_text(encoding="utf-8"))
            self.assertIn("### EUS-01", pass_summary.read_text(encoding="utf-8"))

    def test_run_fake_task_loop_accepts_task_contract_without_registered_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "task-contract.json"
            contract_path.write_text(
                json.dumps(
                    {
                        "task_id": "contract-task",
                        "title": "Contract task",
                        "description": "Temporary contract task.",
                        "verify_commands": [],
                        "scenario_commands": ["python3 -c \"print('contract')\""],
                        "artifact_paths": [],
                        "required_services": [],
                        "evaluator_driver": "fake",
                        "eval_policy": {"task_level_required": True},
                        "allowed_scope": "local_repo_and_harness",
                        "must_simulate": True,
                        "user_scenarios": [
                            {
                                "scenario_id": "CONTRACT-01",
                                "user_goal": "Use task contract scenarios.",
                                "prerequisites": [],
                                "steps": ["Run command."],
                                "expected_outcomes": ["Scenario passes."],
                                "failure_signals": ["Scenario is missing."],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            exit_code = run_fake_task_loop(
                task_id="contract-task",
                max_attempts=2,
                repo_root=root,
                task_contract_path=contract_path,
            )

            self.assertEqual(exit_code, 0)
            bundle = root / ".codex" / "evaluations" / "tasks" / "contract-task" / "fake-attempt-2"
            input_payload = json.loads((bundle / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(input_payload["scenario_source"], str(contract_path))
            self.assertEqual(input_payload["scenario_commands"], ["python3 -c \"print('contract')\""])
            self.assertEqual(input_payload["user_scenarios"][0]["scenario_id"], "CONTRACT-01")

    def test_run_task_loop_cli_accepts_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "task-contract.json"
            contract_path.write_text(
                json.dumps(
                    {
                        "task_id": "contract-task",
                        "title": "Contract task",
                        "description": "Temporary contract task.",
                        "verify_commands": [],
                        "scenario_commands": ["python3 -c \"print('contract')\""],
                        "artifact_paths": [],
                        "required_services": [],
                        "evaluator_driver": "fake",
                        "eval_policy": {"task_level_required": True},
                        "allowed_scope": "local_repo_and_harness",
                        "must_simulate": True,
                        "user_scenarios": [
                            {
                                "scenario_id": "CONTRACT-01",
                                "user_goal": "Use task contract scenarios.",
                                "prerequisites": [],
                                "steps": ["Run command."],
                                "expected_outcomes": ["Scenario passes."],
                                "failure_signals": ["Scenario is missing."],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_orchestrator.py",
                    "run-task-loop",
                    "--driver",
                    "fake",
                    "--task-id",
                    "contract-task",
                    "--max-attempts",
                    "2",
                    "--repo-root",
                    str(root),
                    "--task-contract",
                    str(contract_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            bundle = root / ".codex" / "evaluations" / "tasks" / "contract-task" / "fake-attempt-2"
            input_payload = json.loads((bundle / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(input_payload["scenario_source"], str(contract_path))

    def test_shell_scenario_timeout_records_failed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / ".codex" / "evaluations" / "tasks" / "timeout-task" / "attempt-1"
            bundle.mkdir(parents=True)
            (bundle / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "timeout-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "verify_commands": [],
                        "artifact_paths": [],
                        "allowed_scope": "local_repo_and_harness",
                        "must_simulate": True,
                        "scenario_source": "task-contract.json",
                        "user_scenarios": [
                            {
                                "scenario_id": "TIMEOUT-01",
                                "user_goal": "Timeout.",
                                "prerequisites": [],
                                "entrypoint": "python3 -c \"import time; time.sleep(60)\"",
                                "steps": ["Run command."],
                                "expected_outcomes": ["Command times out."],
                                "failure_signals": ["Command hangs indefinitely."],
                                "cleanup": [],
                                "automation_hint": "shell",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (bundle / "artifacts.json").write_text("{}", encoding="utf-8")

            class TimeoutProcess:
                pid = 123456
                returncode = None

                def __init__(self) -> None:
                    self.calls = 0

                def communicate(self, timeout: int | None = None) -> tuple[str, str]:
                    self.calls += 1
                    if self.calls == 1:
                        raise subprocess.TimeoutExpired(cmd="timeout", timeout=timeout or 1, output="partial", stderr="late")
                    self.returncode = -9
                    return "partial", "late"

                def kill(self) -> None:
                    self.returncode = -9

            from scripts.harness_evaluator_orchestrator import _run_shell_scenarios

            with patch("scripts.harness_evaluator_orchestrator.subprocess.Popen", return_value=TimeoutProcess()), patch(
                "scripts.harness_evaluator_orchestrator.os.killpg"
            ):
                _run_shell_scenarios(bundle, root, timeout_seconds=1)

            artifacts = json.loads((bundle / "artifacts.json").read_text(encoding="utf-8"))
            output = artifacts["scenario_outputs"][0]
            self.assertEqual(output["scenario_id"], "TIMEOUT-01")
            self.assertEqual(output["exit_code"], 124)
            self.assertEqual(output["status"], "timeout")
            self.assertTrue((bundle / "TIMEOUT-01.stdout.log").exists())
            self.assertTrue((bundle / "TIMEOUT-01.stderr.log").exists())

    def test_run_fake_task_loop_writes_result_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "harness-evaluator-gates-01.json").write_text(
                json.dumps(
                    {
                        "task_id": "harness-evaluator-gates-01",
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
                ),
                encoding="utf-8",
            )
            exit_code = run_fake_task_loop(
                task_id="harness-evaluator-gates-01",
                max_attempts=2,
                repo_root=root,
            )
            self.assertEqual(exit_code, 0)
            first_attempt = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "harness-evaluator-gates-01"
                / "fake-attempt-1"
            )
            second_attempt = (
                root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "harness-evaluator-gates-01"
                / "fake-attempt-2"
            )
            self.assertTrue((first_attempt / "result.json").exists())
            self.assertTrue((first_attempt / "summary.md").exists())
            self.assertTrue((second_attempt / "result.json").exists())
            self.assertIn("status: pass", (second_attempt / "summary.md").read_text(encoding="utf-8"))

    def test_run_fake_auto_task_gate_creates_initial_and_repair_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session_dir = root / ".codex" / "session-state"
            session_dir.mkdir(parents=True)
            (session_dir / "demo-session.json").write_text(
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

            exit_code = run_fake_auto_task_gate(
                task_id="demo-task",
                repo_root=root,
                max_attempts=3,
            )

            self.assertEqual(exit_code, 0)
            task_root = root / ".codex" / "evaluations" / "tasks" / "demo-task"
            attempt_dirs = sorted(path.name for path in task_root.iterdir() if path.is_dir())
            self.assertGreaterEqual(len(attempt_dirs), 2)
            self.assertTrue(any(name.endswith("-attempt-1") for name in attempt_dirs))
            self.assertTrue(any(name.endswith("-attempt-2") for name in attempt_dirs))

    def test_run_fake_auto_task_gate_updates_session_state_to_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session_dir = root / ".codex" / "session-state"
            session_dir.mkdir(parents=True)
            session_path = session_dir / "demo-session.json"
            session_path.write_text(
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

            exit_code = run_fake_auto_task_gate(
                task_id="demo-task",
                repo_root=root,
                max_attempts=3,
            )

            self.assertEqual(exit_code, 0)
            state = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertEqual(state["evaluator"]["phase"], "task_evaluator_passed")
            self.assertEqual(state["evaluator"]["last_task_eval_result"], "pass")
            self.assertGreaterEqual(state["evaluator"]["task_eval_attempt"], 2)

    def test_run_fake_auto_task_gate_uses_loaded_session_when_branch_differs_from_git_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session_dir = root / ".codex" / "session-state"
            session_dir.mkdir(parents=True)
            session_path = session_dir / "demo-session.json"
            session_path.write_text(
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
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True, capture_output=True, text=True)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True, text=True)

            exit_code = run_fake_auto_task_gate(
                task_id="demo-task",
                repo_root=root,
                max_attempts=1,
            )

            self.assertEqual(exit_code, 1)
            task_root = root / ".codex" / "evaluations" / "tasks" / "demo-task"
            result_paths = sorted(task_root.glob("*/result.json"))
            self.assertEqual(len(result_paths), 1)
            result_payload = json.loads(result_paths[0].read_text(encoding="utf-8"))
            self.assertEqual(result_payload["status"], "fail")
            state = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertEqual(state["evaluator"]["last_task_eval_result"], "fail")

    def test_run_codex_exec_auto_task_gate_consumes_stop_hook_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session_dir = root / ".codex" / "session-state"
            session_dir.mkdir(parents=True)
            session_path = session_dir / "demo-session.json"
            session_path.write_text(
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

            fake_result = json.dumps(
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
                            "notes": "validated from user flow",
                        }
                    ],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "scenario passed",
                    "next_action": "proceed_to_user_acceptance",
                }
            )

            real_run = subprocess.run

            def fake_run(cmd, **kwargs):
                if cmd and cmd[0] == "codex":
                    self.assertIn("exec", cmd)
                    return subprocess.CompletedProcess(cmd, 0, stdout=fake_result, stderr="")
                return real_run(cmd, **kwargs)

            with patch("scripts.harness_evaluator_orchestrator.subprocess.run", side_effect=fake_run):
                exit_code = run_codex_exec_auto_task_gate(
                    task_id="demo-task",
                    repo_root=root,
                    max_attempts=2,
                )

            self.assertEqual(exit_code, 0)
            task_root = root / ".codex" / "evaluations" / "tasks" / "demo-task"
            attempt_dirs = sorted(path for path in task_root.iterdir() if path.is_dir())
            self.assertEqual(len(attempt_dirs), 1)
            result_payload = json.loads((attempt_dirs[0] / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result_payload["status"], "pass")
            state = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertEqual(state["evaluator"]["phase"], "task_evaluator_passed")

    def test_consume_decision_with_codex_exec_runs_shell_scenarios_and_records_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir(parents=True)
            (root / "scripts" / "demo.py").write_text(
                "\n".join(
                    [
                        "from pathlib import Path",
                        "import sys",
                        "",
                        "output_dir = Path(sys.argv[sys.argv.index('--output-dir') + 1])",
                        "output_dir.mkdir(parents=True, exist_ok=True)",
                        "(output_dir / 'result.txt').write_text('step4-ready\\n', encoding='utf-8')",
                        "print('scenario-ok')",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            templates_dir = root / ".codex" / "evaluations" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "artifacts.template.json").write_text(
                json.dumps(
                    {
                        "logs": [],
                        "reports": [],
                        "screenshots": [],
                        "kubectl_outputs": [],
                        "scenario_outputs": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
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
                )
                + "\n",
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
                                "entrypoint": "python3 scripts/demo.py --output-dir .codex/evaluator-demo/demo-task",
                                "steps": ["Run the command."],
                                "expected_outcomes": ["It exits with status 0."],
                                "failure_signals": ["It exits non-zero."],
                                "cleanup": [],
                                "automation_hint": "shell",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            session_dir = root / ".codex" / "session-state"
            session_dir.mkdir(parents=True)
            (session_dir / "demo-session.json").write_text(
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
                )
                + "\n",
                encoding="utf-8",
            )
            bundle_dir = root / ".codex" / "evaluations" / "tasks" / "demo-task" / "20260626T000000Z-attempt-1"
            bundle_dir.mkdir(parents=True)
            (bundle_dir / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "verify_commands": ["python3 -m unittest demo -v"],
                        "artifact_paths": [],
                        "allowed_scope": "code_and_local_k3s",
                        "must_simulate": True,
                        "scenario_source": str(scenario_dir / "demo-task.json"),
                        "user_scenarios": [
                            {
                                "scenario_id": "EUS-01",
                                "user_goal": "Run the public flow.",
                                "prerequisites": [],
                                "entrypoint": "python3 scripts/demo.py --output-dir .codex/evaluator-demo/demo-task",
                                "steps": ["Run the command."],
                                "expected_outcomes": ["It exits with status 0."],
                                "failure_signals": ["It exits non-zero."],
                                "cleanup": [],
                                "automation_hint": "shell",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (bundle_dir / "artifacts.json").write_text(
                json.dumps(
                    {
                        "logs": [],
                        "reports": [],
                        "screenshots": [],
                        "kubectl_outputs": [],
                        "scenario_outputs": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with patch(
                "scripts.harness_evaluator_orchestrator._run_codex_exec_evaluator",
                return_value={
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
                            "evidence": ["artifacts.json#scenario_outputs[0]"],
                            "notes": "scenario passed",
                        }
                    ],
                    "rerun_commands": [],
                    "environment_checks": [],
                    "verdict_reason": "scenario passed",
                    "next_action": "proceed_to_user_acceptance",
                },
            ):
                handled = consume_decision_with_codex_exec(
                    root,
                    root,
                    "task/demo-task",
                    "demo-task",
                    {
                        "action": "run_task_evaluator",
                        "bundle_dir": str(bundle_dir),
                    },
                )

            self.assertTrue(handled)
            artifacts_payload = json.loads((bundle_dir / "artifacts.json").read_text(encoding="utf-8"))
            self.assertEqual(len(artifacts_payload["scenario_outputs"]), 1)
            scenario_output = artifacts_payload["scenario_outputs"][0]
            self.assertEqual(scenario_output["scenario_id"], "EUS-01")
            self.assertEqual(scenario_output["exit_code"], 0)
            self.assertIn("scenario-ok", scenario_output["stdout"])
            self.assertTrue(any(item["path"].endswith("result.txt") for item in scenario_output["artifacts"]))
            input_payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertTrue(any(path.endswith("result.txt") for path in input_payload["artifact_paths"]))

    def test_codex_exec_prompt_embeds_artifacts_json_and_small_artifact_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle_dir = root / "bundle"
            bundle_dir.mkdir()
            artifact = root / "result.txt"
            artifact.write_text("step4-ready\n", encoding="utf-8")
            (bundle_dir / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "verify_commands": [],
                        "artifact_paths": [str(artifact)],
                        "allowed_scope": "code_and_local_k3s",
                        "must_simulate": True,
                        "scenario_source": "demo-task.json",
                        "user_scenarios": [
                            {
                                "scenario_id": "EUS-01",
                                "user_goal": "Confirm the demo artifact.",
                                "prerequisites": [],
                                "entrypoint": "python3 scripts/demo.py",
                                "steps": ["Run the demo."],
                                "expected_outcomes": ["The command exits 0."],
                                "failure_signals": ["The command exits non-zero."],
                                "cleanup": [],
                                "automation_hint": "shell",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (bundle_dir / "artifacts.json").write_text(
                json.dumps(
                    {
                        "logs": [],
                        "reports": [],
                        "screenshots": [],
                        "kubectl_outputs": [],
                        "scenario_outputs": [
                            {
                                "scenario_id": "EUS-01",
                                "command": "python3 scripts/demo.py",
                                "exit_code": 0,
                                "stdout": "",
                                "stderr": "",
                                "artifacts": [{"path": str(artifact)}],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            prompt = _codex_exec_prompt(bundle_dir, "task")

            self.assertIn('"scenario_outputs"', prompt)
            self.assertIn('"exit_code": 0', prompt)
            self.assertIn(str(artifact), prompt)
            self.assertIn("step4-ready", prompt)

    def test_run_one_stop_auto_gate_returns_followup_rerun_after_fail_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = {
                "task": "demo-task",
                "branch": "task/demo-task",
                "worktree": str(root),
            }
            first_decision = {
                "decision": "block",
                "reason": "run evaluator",
                "action": "run_task_evaluator",
                "bundle_dir": str(root / "attempt-1"),
            }
            followup_decision = {
                "decision": "block",
                "reason": "repair and rerun",
                "action": "rerun_task_evaluator",
                "bundle_dir": str(root / "attempt-2"),
            }
            with patch(
                "scripts.harness_evaluator_orchestrator._load_session",
                return_value=session,
            ) as mocked_session, patch(
                "scripts.harness_evaluator_orchestrator.harness_evaluator_hooks.stop_hook_for_session",
                side_effect=[first_decision, followup_decision],
            ) as mocked_stop, patch(
                "scripts.harness_evaluator_orchestrator.consume_decision_with_codex_exec",
                return_value=True,
            ) as mocked_consume:
                decision = run_one_stop_auto_gate("demo-task", root)

            self.assertEqual(decision, followup_decision)
            mocked_session.assert_called_once_with(root, "demo-task")
            self.assertEqual(mocked_stop.call_count, 2)
            mocked_consume.assert_called_once_with(root, root, "task/demo-task", "demo-task", first_decision)

    def test_run_one_stop_auto_gate_uses_loaded_session_when_branch_differs_from_git_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex" / "evaluations" / "templates").mkdir(parents=True)
            (root / ".codex" / "evaluations" / "templates" / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (root / ".codex" / "evaluations" / "templates" / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / ".codex" / "session-state").mkdir(parents=True)
            (root / "docs" / "harness" / "evaluator-scenarios").mkdir(parents=True)
            (root / "docs" / "harness" / "evaluator-scenarios" / "demo-task.json").write_text(
                json.dumps(
                    {
                        "task_id": "demo-task",
                        "must_simulate": True,
                        "user_scenarios": [
                            {
                                "scenario_id": "EUS-01",
                                "user_goal": "Run demo.",
                                "prerequisites": [],
                                "entrypoint": "python3 scripts/demo.py",
                                "steps": ["Run demo."],
                                "expected_outcomes": ["Demo passes."],
                                "failure_signals": ["Demo fails."],
                                "cleanup": [],
                                "automation_hint": "manual",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".codex" / "session-state" / "demo-task.json").write_text(
                json.dumps(
                    {
                        "task": "demo-task",
                        "branch": "task/demo-task",
                        "worktree": str(root),
                        "evaluator": {
                            "phase": "implementation",
                            "task_eval_attempt": 0,
                            "last_task_eval_result": "",
                            "final_eval_attempt": 0,
                            "last_final_eval_result": "",
                            "repair_from_eval": False,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {
                            "task_level_required": True,
                            "final_level_required": False,
                        },
                        "tasks": [
                            {
                                "id": "demo-task",
                                "title": "Demo",
                                "description": "Demo",
                                "verify": "python3 scripts/demo.py",
                                "requires_eval": True,
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True, capture_output=True, text=True)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True, text=True)

            with patch(
                "scripts.harness_evaluator_orchestrator.consume_decision_with_codex_exec",
                return_value=True,
            ) as mocked_consume:
                decision = run_one_stop_auto_gate("demo-task", root)

            self.assertEqual(decision["action"], "run_task_evaluator")
            mocked_consume.assert_called_once()
            bundle_root = root / ".codex" / "evaluations" / "tasks" / "demo-task"
            self.assertTrue(any(bundle_root.iterdir()))
