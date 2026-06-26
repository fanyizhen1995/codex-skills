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


class HarnessEvaluatorCliTests(unittest.TestCase):
    def test_prepare_task_creates_bundle_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex" / "evaluations" / "templates").mkdir(parents=True)
            (root / ".codex" / "evaluations" / "templates" / "input.template.json").write_text("{}", encoding="utf-8")
            (root / ".codex" / "evaluations" / "templates" / "artifacts.template.json").write_text("{}", encoding="utf-8")
            (root / ".codex" / "evaluations" / "templates" / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            output = subprocess.run([
                "python3", "scripts/harness_evaluator_cli.py", "prepare-task", "--repo-root", str(root), "--task-id", "harness-evaluator-gates-01", "--attempt", "1"
            ], check=False, capture_output=True, text=True)
            self.assertEqual(output.returncode, 0, output.stderr)
            bundle_dir = Path(output.stdout.strip())
            self.assertTrue((bundle_dir / "input.json").exists())
            self.assertTrue((bundle_dir / "artifacts.json").exists())
            self.assertTrue((bundle_dir / "summary.md").exists())
            payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(
                payload,
                {
                    "gate": "task",
                    "task_id": "harness-evaluator-gates-01",
                    "final_bundle_id": "",
                    "attempt": 1,
                    "verify_commands": [],
                    "artifact_paths": [],
                    "allowed_scope": "",
                    "must_simulate": True,
                    "scenario_source": str(
                        root
                        / "docs"
                        / "harness"
                        / "evaluator-scenarios"
                        / "harness-evaluator-gates-01.json"
                    ),
                    "user_scenarios": [],
                },
            )

    def test_prepare_task_includes_scenario_metadata_in_input_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex" / "evaluations" / "templates").mkdir(parents=True)
            (root / ".codex" / "evaluations" / "templates" / "input.template.json").write_text("{}", encoding="utf-8")
            (root / ".codex" / "evaluations" / "templates" / "artifacts.template.json").write_text("{}", encoding="utf-8")
            (root / ".codex" / "evaluations" / "templates" / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
            (root / "docs" / "harness" / "evaluator-scenarios").mkdir(parents=True)
            (root / "docs" / "harness" / "evaluator-scenarios" / "demo-task.json").write_text(
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
            (root / "tasks.json").write_text(
                json.dumps(
                    {
                        "eval_defaults": {"task_scope": "code_and_local_k3s"},
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

            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_cli.py",
                    "prepare-task",
                    "--repo-root",
                    str(root),
                    "--task-id",
                    "demo-task",
                    "--attempt",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            bundle_dir = Path(result.stdout.strip())
            payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["must_simulate"])
            self.assertEqual(
                payload["scenario_source"],
                str(root / "docs" / "harness" / "evaluator-scenarios" / "demo-task.json"),
            )
            self.assertEqual(payload["user_scenarios"][0]["scenario_id"], "EUS-01")

    def test_record_result_writes_validated_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            payload = {
                "status": "pass",
                "gate": "task",
                "task_id": "harness-evaluator-gates-01",
                "final_bundle_id": "",
                "attempt": 1,
                "summary": "pass",
                "findings": [],
                "scenario_results": [],
                "rerun_commands": [],
                "environment_checks": [],
                "verdict_reason": "all good",
                "next_action": "proceed_to_user_acceptance",
            }
            result = subprocess.run([
                "python3", "scripts/harness_evaluator_cli.py", "record-result", "--bundle-dir", str(bundle_dir)
            ], input=json.dumps(payload), check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            stored = json.loads((bundle_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(stored, payload)

    def test_record_result_rejects_task_pass_without_required_scenario_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            (bundle_dir / "input.json").write_text(
                json.dumps(
                    {
                        "gate": "task",
                        "task_id": "demo-task",
                        "attempt": 1,
                        "must_simulate": True,
                        "scenario_source": "docs/harness/evaluator-scenarios/demo-task.json",
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
            payload = {
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

            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_cli.py",
                    "record-result",
                    "--bundle-dir",
                    str(bundle_dir),
                ],
                input=json.dumps(payload),
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("scenario_results", result.stderr)

    def test_prepare_final_creates_final_bundle_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_cli.py",
                    "prepare-final",
                    "--repo-root",
                    str(root),
                    "--final-bundle-id",
                    "release-20260624",
                    "--attempt",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            bundle_dir = Path(result.stdout.strip())
            self.assertTrue((bundle_dir / "input.json").exists())
            payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["gate"], "final")
            self.assertEqual(payload["final_bundle_id"], "release-20260624")
            self.assertEqual(payload["attempt"], 1)
            self.assertEqual(payload["task_id"], "")

    def test_render_final_banner_marks_soft_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            (bundle_dir / "result.json").write_text(
                json.dumps(
                    {
                        "status": "fail",
                        "gate": "final",
                        "task_id": "",
                        "final_bundle_id": "release-20260624",
                        "attempt": 1,
                        "summary": "soft fail",
                        "findings": [],
                        "scenario_results": [],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "report overclaim",
                        "next_action": "proceed_with_risk",
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_evaluator_cli.py",
                    "render-final-banner",
                    "--bundle-dir",
                    str(bundle_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("not recommended for acceptance", result.stdout)
