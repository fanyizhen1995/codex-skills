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
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.harness_evaluator_cli import create_task_bundle, main
from scripts.harness_evaluator_hooks import _bundle_contract_issue


class HarnessEvaluatorCliTests(unittest.TestCase):
    def _write_bundle_templates(self, repo_root: Path) -> None:
        templates_dir = repo_root / ".codex" / "evaluations" / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "artifacts.template.json").write_text("{}", encoding="utf-8")
        (templates_dir / "summary.template.md").write_text("# Summary\n", encoding="utf-8")

    def _task_contract(self) -> dict:
        return {
            "task_id": "contract-task",
            "title": "Contract task",
            "description": "Temporary contract task.",
            "verify_commands": ["python3 -m json.tool tasks.json"],
            "scenario_commands": ["python3 -c \"print('scenario-ok')\""],
            "artifact_paths": ["tasks.json"],
            "required_services": ["backend"],
            "evaluator_driver": "harness_auto_gate",
            "eval_policy": {"task_level_required": True, "task_scope": "local_repo_and_harness"},
            "allowed_scope": "local_repo_and_harness",
            "must_simulate": True,
            "user_scenarios": [
                {
                    "scenario_id": "CONTRACT-01",
                    "user_goal": "Use task contract.",
                    "prerequisites": ["Task contract exists."],
                    "steps": ["Prepare bundle."],
                    "expected_outcomes": ["input.json includes contract data."],
                    "failure_signals": ["input.json omits contract data."],
                }
            ],
        }

    def test_create_task_bundle_accepts_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._write_bundle_templates(repo_root)
            contract_path = repo_root / "task-contract.json"
            contract_path.write_text(json.dumps(self._task_contract()), encoding="utf-8")

            bundle_dir = create_task_bundle(
                repo_root,
                "ignored-task",
                1,
                task_contract_path=contract_path,
            )

            input_payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            self.assertEqual(input_payload["task_id"], "contract-task")
            self.assertEqual(input_payload["verify_commands"], ["python3 -m json.tool tasks.json"])
            self.assertEqual(input_payload["scenario_commands"], ["python3 -c \"print('scenario-ok')\""])
            self.assertEqual(input_payload["artifact_paths"], ["tasks.json"])
            self.assertEqual(input_payload["required_services"], ["backend"])
            self.assertEqual(input_payload["allowed_scope"], "local_repo_and_harness")
            self.assertEqual(
                input_payload["evaluator_driver"],
                "harness_auto_gate",
            )
            self.assertEqual(
                input_payload["eval_policy"],
                {"task_level_required": True, "task_scope": "local_repo_and_harness"},
            )
            self.assertTrue(input_payload["must_simulate"])
            self.assertEqual(input_payload["scenario_source"], str(contract_path))
            self.assertEqual(input_payload["user_scenarios"][0]["scenario_id"], "CONTRACT-01")

    def test_task_contract_bundle_is_normalized_for_stop_hook_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._write_bundle_templates(repo_root)
            contract_path = repo_root / "task-contract.json"
            contract_path.write_text(json.dumps(self._task_contract()), encoding="utf-8")

            bundle_dir = create_task_bundle(
                repo_root,
                "ignored-task",
                1,
                task_contract_path=contract_path,
            )

            input_payload = json.loads((bundle_dir / "input.json").read_text(encoding="utf-8"))
            scenario = input_payload["user_scenarios"][0]
            self.assertEqual(scenario["entrypoint"], "python3 -c \"print('scenario-ok')\"")
            self.assertEqual(scenario["cleanup"], [])
            self.assertEqual(scenario["automation_hint"], "shell")
            self.assertIsNone(_bundle_contract_issue(bundle_dir))

    def test_prepare_task_cli_accepts_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._write_bundle_templates(repo_root)
            contract_path = repo_root / "task-contract.json"
            contract_path.write_text(json.dumps(self._task_contract()), encoding="utf-8")

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "prepare-task",
                            "--repo-root",
                            str(repo_root),
                            "--task-id",
                            "ignored-task",
                            "--attempt",
                            "1",
                            "--task-contract",
                            str(contract_path),
                        ]
                    ),
                    0,
                )

            bundles = list(
                (
                    repo_root / ".codex" / "evaluations" / "tasks" / "contract-task"
                ).glob("*-attempt-1")
            )
            self.assertEqual(len(bundles), 1)
            self.assertEqual(Path(stdout.getvalue().strip()), bundles[0])

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
                    "scenario_commands": [],
                    "artifact_paths": [],
                    "required_services": [],
                    "allowed_scope": "",
                    "evaluator_driver": "",
                    "eval_policy": {},
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
