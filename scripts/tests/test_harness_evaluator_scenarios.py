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

from scripts.harness_evaluator_scenarios import load_task_scenarios


class HarnessEvaluatorScenarioTests(unittest.TestCase):
    def test_load_task_scenarios_reads_expected_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            scenario_file = scenario_dir / "demo-task.json"
            scenario_file.write_text(
                json.dumps(
                    {
                        "task_id": "demo-task",
                        "must_simulate": True,
                        "user_scenarios": [
                            {
                                "scenario_id": "EUS-01",
                                "user_goal": "Run the public CLI flow.",
                                "prerequisites": ["python3 is available"],
                                "entrypoint": "python3 scripts/demo.py",
                                "steps": ["Run the CLI command."],
                                "expected_outcomes": ["The command exits with status 0."],
                                "failure_signals": ["The command exits non-zero."],
                                "cleanup": ["Remove generated temp files."],
                                "automation_hint": "shell",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            contract = load_task_scenarios(root, "demo-task")
            self.assertTrue(contract["must_simulate"])
            self.assertEqual(contract["task_id"], "demo-task")
            self.assertEqual(contract["source"], str(scenario_file))
            self.assertEqual(contract["user_scenarios"][0]["scenario_id"], "EUS-01")

    def test_load_task_scenarios_returns_empty_list_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = load_task_scenarios(root, "missing-task")
            self.assertTrue(contract["must_simulate"])
            self.assertEqual(contract["task_id"], "missing-task")
            self.assertEqual(contract["user_scenarios"], [])

    def test_load_task_scenarios_rejects_missing_required_scenario_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "broken-task.json").write_text(
                json.dumps(
                    {
                        "task_id": "broken-task",
                        "must_simulate": True,
                        "user_scenarios": [
                            {
                                "scenario_id": "EUS-01",
                                "user_goal": "Missing the rest of the contract."
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_task_scenarios(root, "broken-task")

    def test_load_task_scenarios_rejects_non_mapping_scenario_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "invalid-shape-task.json").write_text(
                json.dumps(
                    {
                        "task_id": "invalid-shape-task",
                        "must_simulate": True,
                        "user_scenarios": ["not-a-dict"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_task_scenarios(root, "invalid-shape-task")

    def test_load_task_scenarios_rejects_mismatched_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "demo-task.json").write_text(
                json.dumps(
                    {
                        "task_id": "other-task",
                        "must_simulate": True,
                        "user_scenarios": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_task_scenarios(root, "demo-task")

    def test_load_task_scenarios_rejects_non_mapping_top_level_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_dir = root / "docs" / "harness" / "evaluator-scenarios"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "invalid-top-level.json").write_text(
                json.dumps(["not-a-mapping"]),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_task_scenarios(root, "invalid-top-level")

    def test_harness_evaluator_demo_cli_round_trip(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / ".codex" / "evaluator-demo" / "harness-evaluator-demo-01"
            write_result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_demo.py",
                    "write-expected",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(write_result.returncode, 0, write_result.stderr)
            self.assertEqual(
                (output_dir / "result.txt").read_text(encoding="utf-8"),
                "step4-ready\n",
            )

            assert_result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_demo.py",
                    "assert-expected",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(assert_result.returncode, 0, assert_result.stderr)

    def test_harness_evaluator_demo_cli_fails_without_expected_file(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / ".codex" / "evaluator-demo" / "harness-evaluator-demo-01"
            assert_result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_demo.py",
                    "assert-expected",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(assert_result.returncode, 0)
            self.assertIn("missing expected file", assert_result.stderr or assert_result.stdout)

    def test_harness_evaluator_demo_cli_fails_on_unexpected_content(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / ".codex" / "evaluator-demo" / "harness-evaluator-demo-01"
            output_dir.mkdir(parents=True)
            (output_dir / "result.txt").write_text("wrong\n", encoding="utf-8")
            assert_result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_demo.py",
                    "assert-expected",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(assert_result.returncode, 0)
            self.assertIn("unexpected content", assert_result.stderr or assert_result.stdout)

    def test_load_task_scenarios_reads_harness_evaluator_demo_contract(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        contract = load_task_scenarios(repo_root, "harness-evaluator-demo-01")
        self.assertEqual(contract["task_id"], "harness-evaluator-demo-01")
        self.assertTrue(contract["must_simulate"])
        scenario = contract["user_scenarios"][0]
        self.assertEqual(scenario["scenario_id"], "EUS-01")
        self.assertEqual(
            scenario["entrypoint"],
            "python3 scripts/harness_evaluator_demo.py assert-expected --output-dir .codex/evaluator-demo/harness-evaluator-demo-01",
        )
        self.assertEqual(
            scenario["prerequisites"],
            ["The developer task has run scripts/harness_evaluator_demo.py write-expected."],
        )
        self.assertEqual(
            scenario["expected_outcomes"],
            [
                "The command exits with status 0.",
                "The file .codex/evaluator-demo/harness-evaluator-demo-01/result.txt contains step4-ready.",
            ],
        )
