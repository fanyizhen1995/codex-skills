import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.harness_loop_artifacts import run_artifact_hygiene, run_scenario_commands


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

    def test_run_scenario_commands_records_partial_evidence_when_second_communicate_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"

            class TimeoutProcess:
                pid = 123456
                returncode = None

                def __init__(self) -> None:
                    self.calls = 0

                def communicate(self, timeout: int | None = None) -> tuple[str, str]:
                    self.calls += 1
                    if self.calls == 1:
                        raise subprocess.TimeoutExpired(
                            cmd="timeout",
                            timeout=timeout or 1,
                            output="partial stdout",
                            stderr="partial stderr",
                        )
                    raise subprocess.TimeoutExpired(cmd="timeout", timeout=timeout or 1)

                def kill(self) -> None:
                    self.returncode = -9

            with patch("scripts.harness_loop_artifacts.subprocess.Popen", return_value=TimeoutProcess()), patch(
                "scripts.harness_loop_artifacts.os.killpg"
            ):
                manifest_path = run_scenario_commands(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    commands=["python3 -c \"import time; time.sleep(60)\""],
                    timeout_seconds=1,
                )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            result = manifest["results"][0]
            self.assertEqual(result["status"], "timeout")
            self.assertEqual(result["exit_code"], 124)
            self.assertTrue(result["second_communicate_timeout"])
            self.assertEqual(Path(result["stdout_path"]).read_text(encoding="utf-8"), "partial stdout")
            self.assertEqual(Path(result["stderr_path"]).read_text(encoding="utf-8"), "partial stderr")


class HarnessLoopArtifactHygieneTests(unittest.TestCase):
    def test_run_artifact_hygiene_redacts_sensitive_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text("Authorization: Bearer secret-token\n", encoding="utf-8")

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["artifact.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "redacted")
            self.assertEqual(result["scanned_paths"], ["artifact.txt"])
            self.assertEqual(result["redacted_paths"], ["artifact.txt.redacted"])
            redacted = repo_root / "artifact.txt.redacted"
            self.assertIn("[REDACTED]", redacted.read_text(encoding="utf-8"))
            redaction_manifest = json.loads(Path(result["redaction_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(redaction_manifest["redactions"][0]["rule_id"], "authorization_header")

    def test_run_artifact_hygiene_redacts_inline_authorization_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text('curl -H "Authorization: Bearer secret"\n', encoding="utf-8")

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["artifact.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "redacted")
            redacted = (repo_root / "artifact.txt.redacted").read_text(encoding="utf-8")
            self.assertIn("[REDACTED]", redacted)
            self.assertNotIn("Bearer secret", redacted)
            redaction_manifest = json.loads(Path(result["redaction_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(redaction_manifest["redactions"][0]["rule_id"], "authorization_header")

    def test_run_artifact_hygiene_redacts_leading_whitespace_authorization_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text("  Authorization: Bearer secret\n", encoding="utf-8")

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["artifact.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "redacted")
            redacted = (repo_root / "artifact.txt.redacted").read_text(encoding="utf-8")
            self.assertIn("[REDACTED]", redacted)
            self.assertNotIn("Bearer secret", redacted)
            redaction_manifest = json.loads(Path(result["redaction_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(redaction_manifest["redactions"][0]["rule_id"], "authorization_header")

    def test_run_artifact_hygiene_omits_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "large.bin"
            artifact_path.write_bytes(b"x" * 20)

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["large.bin"],
                max_file_bytes=10,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["omitted_paths"], ["large.bin"])

    def test_run_artifact_hygiene_does_not_hash_omitted_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "large.bin"
            artifact_path.write_bytes(b"x" * 20)

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["large.bin"],
                max_file_bytes=10,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertNotIn("large.bin", result["original_hashes"])

    def test_run_artifact_hygiene_rejects_traversal_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            repo_root.mkdir()
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            outside_path = parent / "outside-token.txt"
            outside_path.write_text("Authorization: Bearer secret-token\n", encoding="utf-8")

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["../outside-token.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["omitted_paths"], ["../outside-token.txt"])
            self.assertEqual(result["scanned_paths"], [])
            self.assertFalse((parent / "outside-token.txt.redacted").exists())

    def test_run_artifact_hygiene_rejects_parent_segment_inside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text("ok\n", encoding="utf-8")

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["sub/../artifact.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["omitted_paths"], ["sub/../artifact.txt"])
            self.assertEqual(result["scanned_paths"], [])

    def test_run_artifact_hygiene_rejects_absolute_path_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            repo_root.mkdir()
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            outside_path = parent / "outside-token.txt"
            outside_path.write_text("Authorization: Bearer secret-token\n", encoding="utf-8")

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=[str(outside_path)],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["omitted_paths"], [str(outside_path)])
            self.assertEqual(result["scanned_paths"], [])
            self.assertFalse(Path(str(outside_path) + ".redacted").exists())

    def test_run_artifact_hygiene_rejects_symlink_escape_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            repo_root.mkdir()
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            outside_path = parent / "outside-token.txt"
            outside_path.write_text("Authorization: Bearer secret-token\n", encoding="utf-8")
            link_path = repo_root / "linked-token.txt"
            link_path.symlink_to(outside_path)

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["linked-token.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["omitted_paths"], ["linked-token.txt"])
            self.assertEqual(result["scanned_paths"], [])
            self.assertFalse((repo_root / "linked-token.txt.redacted").exists())

    def test_run_artifact_hygiene_blocks_preexisting_redacted_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            repo_root.mkdir()
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text("Authorization: Bearer secret-token\n", encoding="utf-8")
            outside_redacted = parent / "outside-redacted.txt"
            outside_redacted.write_text("sentinel\n", encoding="utf-8")
            redacted_link = repo_root / "artifact.txt.redacted"
            redacted_link.symlink_to(outside_redacted)

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["artifact.txt"],
                max_file_bytes=1024,
                max_total_bytes=4096,
            )

            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertIn("artifact.txt", result["omitted_paths"])
            self.assertEqual(result["redacted_paths"], [])
            self.assertEqual(outside_redacted.read_text(encoding="utf-8"), "sentinel\n")
            self.assertTrue(redacted_link.is_symlink())
            self.assertEqual(redacted_link.resolve(), outside_redacted)


if __name__ == "__main__":
    unittest.main()
