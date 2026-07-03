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
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.harness_evaluator_scenarios import load_task_scenarios


def copy_worktree_files(repo_root: Path, fixture: Path, paths: list[str]) -> None:
    for relative in paths:
        source = repo_root / relative
        target = fixture / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


class HarnessEvaluatorScenarioTests(unittest.TestCase):
    def test_loop_dashboard_find_free_port_returns_bindable_port(self) -> None:
        from scripts.loop_dashboard_evaluator import find_free_port

        port = find_free_port()

        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))

    def test_loop_dashboard_wait_rejects_mismatched_project_root(self) -> None:
        from scripts.loop_dashboard_evaluator import wait_for_dashboard

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/api/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
                if self.path == "/api/projects/current":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"project_root":"/wrong/root"}')
                    return
                self.send_response(404)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                expected_root = Path(tmp).resolve()
                with self.assertRaisesRegex(RuntimeError, "project root mismatch"):
                    wait_for_dashboard(
                        f"http://127.0.0.1:{server.server_port}",
                        expected_root,
                        timeout_seconds=0.1,
                    )
        finally:
            server.shutdown()
            server.server_close()

    def test_loop_dashboard_failure_result_includes_server_output(self) -> None:
        from scripts.loop_dashboard_evaluator import collect_server_output, failure_payload

        process = subprocess.Popen(
            [
                "python3",
                "-c",
                "import sys; print('server stdout marker'); print('server stderr marker', file=sys.stderr)",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        process.wait(timeout=5)

        from scripts.loop_dashboard_evaluator import write_json

        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "result.json"
            write_json(
                result_path,
                failure_payload(
                    RuntimeError("startup failed"),
                    "http://127.0.0.1:1",
                    Path("/tmp/fixture-root"),
                    collect_server_output(process),
                ),
            )
            payload = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["server_stdout"].strip(), "server stdout marker")
        self.assertEqual(payload["server_stderr"].strip(), "server stderr marker")

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

    def test_compute_accelerator_monthly_discovery_entrypoint_is_portable(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        contract = load_task_scenarios(repo_root, "compute-accelerator-monthly-discovery-01")
        entrypoint = contract["user_scenarios"][0]["entrypoint"]

        self.assertNotIn(".worktrees", entrypoint)
        self.assertIn("personal-wiki/apps/crawler_workbench/backend", entrypoint)

    def test_loop_dashboard_dev_entrypoint_is_registered(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        contract = load_task_scenarios(repo_root, "loop-dashboard-dev-01")

        self.assertEqual(contract["task_id"], "loop-dashboard-dev-01")
        self.assertTrue(contract["must_simulate"])
        self.assertEqual(contract["user_scenarios"][0]["automation_hint"], "playwright")
        self.assertIn("scripts/loop_dashboard_evaluator.py", contract["user_scenarios"][0]["entrypoint"])

    def test_compute_accelerator_spec_extraction_contract_is_registered(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        contract = load_task_scenarios(repo_root, "compute-accelerator-spec-extraction-01")
        entrypoint = contract["user_scenarios"][0]["entrypoint"]

        self.assertEqual(contract["task_id"], "compute-accelerator-spec-extraction-01")
        self.assertIn("tests/test_accelerator_specs.py", entrypoint)
        self.assertIn("validate-accelerators", entrypoint)

    def test_phase_3_scenario_entrypoint_uses_smoke_helper(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        contract = load_task_scenarios(repo_root, "planner-generator-evaluator-loop-phase-3-01")
        entrypoint = contract["user_scenarios"][0]["entrypoint"]

        self.assertEqual(contract["task_id"], "planner-generator-evaluator-loop-phase-3-01")
        self.assertIn("scripts/harness_loop_phase3_smoke.py", entrypoint)
        self.assertIn("--domain ai_infra", entrypoint)
        self.assertIn("--isolate-clone", entrypoint)

    def test_phase_3_smoke_helper_exercises_autonomous_commit_and_no_action(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixture"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-hardlinks",
                    str(repo_root),
                    str(fixture),
                ],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            copy_worktree_files(
                repo_root,
                fixture,
                [
                    "scripts/harness_loop_phase3_smoke.py",
                    "scripts/harness_loop_orchestrator.py",
                    "scripts/harness_loop_contracts.py",
                    "scripts/tests/test_harness_evaluator_scenarios.py",
                    "docs/harness/evaluator-scenarios/planner-generator-evaluator-loop-phase-3-01.json",
                    "docs/harness/planner-generator-evaluator-loop.md",
                ],
            )
            subprocess.run(
                ["git", "config", "user.email", "codex@example.invalid"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "config", "user.name", "Codex"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_loop_phase3_smoke.py",
                    "--repo-root",
                    ".",
                    "--run-id",
                    "evaluator-scenario-phase-3",
                    "--domain",
                    "ai_infra",
                    "--task-id",
                    "planner-generator-evaluator-loop-phase-3-01",
                ],
                cwd=fixture,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["phase"], "stopped_no_action")
            self.assertTrue(payload["commit"])
            loop_state_path = fixture / payload["loop_state_path"]
            self.assertTrue(loop_state_path.exists())
            for key in (
                "planner_output_path",
                "generator_result_path",
                "evaluator_result_path",
                "artifact_manifest_path",
                "commit_result_path",
            ):
                self.assertTrue((fixture / payload[key]).exists(), key)

    def test_phase_3_smoke_helper_rejects_dirty_loop_state_before_seeding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            subprocess.run(["git", "init"], cwd=fixture, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "config", "user.email", "codex@example.invalid"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "config", "user.name", "Codex"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            (fixture / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=fixture, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "commit", "-m", "test: initial"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            dirty_loop_state = fixture / "personal-wiki" / "domains" / "ai_infra" / "loop-state.json"
            dirty_loop_state.parent.mkdir(parents=True, exist_ok=True)
            dirty_loop_state.write_text("{\"dirty\": true}\n", encoding="utf-8")

            from scripts.harness_loop_phase3_smoke import run_phase3_smoke

            with self.assertRaisesRegex(RuntimeError, "dirty smoke paths"):
                run_phase3_smoke(
                    fixture,
                    "evaluator-scenario-phase-3",
                    "ai_infra",
                    "planner-generator-evaluator-loop-phase-3-01",
                )

    def test_phase_3_smoke_helper_does_not_delete_other_domain_raw_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            subprocess.run(["git", "init"], cwd=fixture, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "config", "user.email", "codex@example.invalid"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "config", "user.name", "Codex"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            (fixture / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=fixture, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "commit", "-m", "test: initial"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            other_raw_note = (
                fixture
                / "personal-wiki"
                / "domains"
                / "other_domain"
                / "raw"
                / "loop-autonomous"
                / "evaluator-scenario-phase-3-task-existing.md"
            )
            other_raw_note.parent.mkdir(parents=True, exist_ok=True)
            other_raw_note.write_text("must stay\n", encoding="utf-8")

            from scripts.harness_loop_phase3_smoke import _clean_previous_smoke

            _clean_previous_smoke(fixture, "evaluator-scenario-phase-3", "ai_infra")

            self.assertTrue(other_raw_note.exists())

    def test_phase_3_smoke_helper_rejects_dirty_current_domain_raw_note_before_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            subprocess.run(["git", "init"], cwd=fixture, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "config", "user.email", "codex@example.invalid"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "config", "user.name", "Codex"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            (fixture / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=fixture, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "commit", "-m", "test: initial"],
                cwd=fixture,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            dirty_raw_note = (
                fixture
                / "personal-wiki"
                / "domains"
                / "ai_infra"
                / "raw"
                / "loop-autonomous"
                / "evaluator-scenario-phase-3-task-existing.md"
            )
            dirty_raw_note.parent.mkdir(parents=True, exist_ok=True)
            dirty_raw_note.write_text("dirty\n", encoding="utf-8")

            from scripts.harness_loop_phase3_smoke import run_phase3_smoke

            with self.assertRaisesRegex(RuntimeError, "dirty smoke paths"):
                run_phase3_smoke(
                    fixture,
                    "evaluator-scenario-phase-3",
                    "ai_infra",
                    "planner-generator-evaluator-loop-phase-3-01",
                )
