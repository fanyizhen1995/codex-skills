import json
import tempfile
import unittest
from pathlib import Path

from scripts.harness_loop_artifacts import run_scenario_commands


class HarnessLoopArtifactsTests(unittest.TestCase):
    def test_run_scenario_commands_writes_stdout_stderr_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"

            manifest_path = run_scenario_commands(
                repo_root=repo_root,
                run_dir=run_dir,
                commands=[
                    "python3 -c \"import sys; print('out'); print('err', file=sys.stderr)\"",
                ],
                timeout_seconds=30,
            )

            self.assertEqual(manifest_path, run_dir / "scenario-command-results.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "pass")
            self.assertEqual(len(manifest["results"]), 1)
            result = manifest["results"][0]
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(Path(result["stdout_path"]), run_dir / "scenario-commands" / "command-1.stdout.log")
            self.assertEqual(Path(result["stderr_path"]), run_dir / "scenario-commands" / "command-1.stderr.log")
            self.assertIn("out", Path(result["stdout_path"]).read_text(encoding="utf-8"))
            self.assertIn("err", Path(result["stderr_path"]).read_text(encoding="utf-8"))

    def test_run_scenario_commands_marks_failed_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"

            manifest_path = run_scenario_commands(
                repo_root=repo_root,
                run_dir=run_dir,
                commands=["python3 -c \"raise SystemExit(2)\""],
                timeout_seconds=30,
            )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "fail")
            self.assertEqual(manifest["results"][0]["status"], "fail")
            self.assertEqual(manifest["results"][0]["exit_code"], 2)

    def test_run_scenario_commands_marks_timed_out_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"

            manifest_path = run_scenario_commands(
                repo_root=repo_root,
                run_dir=run_dir,
                commands=["python3 -c \"import time; time.sleep(2)\""],
                timeout_seconds=1,
            )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "fail")
            self.assertEqual(manifest["results"][0]["status"], "timeout")
            self.assertEqual(manifest["results"][0]["exit_code"], 124)


if __name__ == "__main__":
    unittest.main()
