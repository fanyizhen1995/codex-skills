import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.harness_loop_agents import (
    build_codex_exec_command,
    codex_exec_capabilities,
    run_codex_prompt,
)
from scripts.harness_loop_contracts import read_json_file, validate_agent_attempt_payload


class HarnessLoopAgentsTests(unittest.TestCase):
    def test_codex_exec_capabilities_detects_json_and_output_last_message(self) -> None:
        completed = subprocess.CompletedProcess(
            ["codex", "exec", "--help"],
            0,
            stdout="Usage: codex exec [OPTIONS]\n  --json\n  --output-last-message <FILE>\n",
            stderr="",
        )
        with mock.patch("scripts.harness_loop_agents.subprocess.run", return_value=completed) as run:
            capabilities = codex_exec_capabilities()

        run.assert_called_once_with(
            ["codex", "exec", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(capabilities, {"json": True, "output_last_message": True})

    def test_codex_exec_capabilities_returns_false_when_probe_fails(self) -> None:
        with mock.patch("scripts.harness_loop_agents.subprocess.run", side_effect=OSError("missing")):
            capabilities = codex_exec_capabilities()

        self.assertEqual(capabilities, {"json": False, "output_last_message": False})

    def test_build_codex_exec_command_uses_supported_flags_and_stdin_prompt(self) -> None:
        message_path = Path("/tmp/run/planner-attempt-1.message.json")
        command = build_codex_exec_command(
            repo_root=Path("/tmp/repo"),
            output_message_path=message_path,
            capabilities={"json": True, "output_last_message": True},
        )

        self.assertEqual(
            command,
            [
                "codex",
                "-a",
                "never",
                "exec",
                "--cd",
                "/tmp/repo",
                "--color",
                "never",
                "--json",
                "--output-last-message",
                str(message_path),
                "-",
            ],
        )

    def test_build_codex_exec_command_omits_unsupported_optional_flags(self) -> None:
        command = build_codex_exec_command(
            repo_root=Path("/tmp/repo"),
            output_message_path=Path("/tmp/run/output.json"),
            capabilities={"json": False, "output_last_message": False},
        )

        self.assertEqual(
            command,
            [
                "codex",
                "-a",
                "never",
                "exec",
                "--cd",
                "/tmp/repo",
                "--color",
                "never",
                "-",
            ],
        )

    def test_run_codex_prompt_writes_attempt_logs_and_returns_failure_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".codex" / "loop-runs" / "run-1"
            prompt_path = run_dir / "prompt.md"
            output_json_path = run_dir / "planner-output.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Do the thing", encoding="utf-8")
            completed = subprocess.CompletedProcess(
                ["codex"],
                2,
                stdout="partial output",
                stderr="boom",
            )

            with mock.patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": True, "output_last_message": True},
            ), mock.patch("scripts.harness_loop_agents.subprocess.run", return_value=completed) as run:
                payload = run_codex_prompt(
                    role="planner",
                    run_id="run-1",
                    repo_root=root,
                    run_dir=run_dir,
                    prompt_path=prompt_path,
                    output_json_path=output_json_path,
                    attempt=1,
                    timeout_seconds=30,
                )

            run.assert_called_once()
            self.assertEqual(run.call_args.kwargs["input"], "Do the thing")
            self.assertEqual(run.call_args.kwargs["timeout"], 30)
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["exit_code"], 2)
            validate_agent_attempt_payload(payload)
            self.assertEqual((run_dir / "planner-attempt-1.stdout.log").read_text(encoding="utf-8"), "partial output")
            self.assertEqual((run_dir / "planner-attempt-1.stderr.log").read_text(encoding="utf-8"), "boom")
            self.assertIn("boom", Path(payload["stderr_path"]).read_text(encoding="utf-8"))
            self.assertEqual(read_json_file(run_dir / "planner-attempt-1.json"), payload)
            self.assertEqual(payload["diff_patch_path"], "")
            self.assertEqual(payload["verify_log_paths"], [])

    def test_run_codex_prompt_passes_when_contract_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".codex" / "loop-runs" / "run-1"
            prompt_path = run_dir / "prompt.md"
            output_json_path = run_dir / "planner-output.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Do the thing", encoding="utf-8")

            def run_side_effect(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                message_path = Path(command[command.index("--output-last-message") + 1])
                self.assertNotEqual(message_path, output_json_path)
                message_path.write_text('{"type":"message"}', encoding="utf-8")
                output_json_path.write_text('{"status":"pass"}', encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, stdout="done", stderr="")

            with mock.patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": True, "output_last_message": True},
            ), mock.patch("scripts.harness_loop_agents.subprocess.run", side_effect=run_side_effect):
                payload = run_codex_prompt(
                    role="planner",
                    run_id="run-1",
                    repo_root=root,
                    run_dir=run_dir,
                    prompt_path=prompt_path,
                    output_json_path=output_json_path,
                    attempt=1,
                    timeout_seconds=30,
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["exit_code"], 0)
            self.assertEqual(payload["output_json_path"], str(output_json_path))
            validate_agent_attempt_payload(payload)

    def test_run_codex_prompt_uses_final_message_json_when_contract_output_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".codex" / "loop-runs" / "run-1"
            prompt_path = run_dir / "prompt.md"
            output_json_path = run_dir / "planner-output.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Do the thing", encoding="utf-8")

            def run_side_effect(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                message_path = Path(command[command.index("--output-last-message") + 1])
                message_path.write_text('{"task_id":"from-final-message"}', encoding="utf-8")
                self.assertFalse(output_json_path.exists())
                return subprocess.CompletedProcess(command, 0, stdout="done", stderr="")

            with mock.patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": True, "output_last_message": True},
            ), mock.patch("scripts.harness_loop_agents.subprocess.run", side_effect=run_side_effect):
                payload = run_codex_prompt(
                    role="planner",
                    run_id="run-1",
                    repo_root=root,
                    run_dir=run_dir,
                    prompt_path=prompt_path,
                    output_json_path=output_json_path,
                    attempt=1,
                    timeout_seconds=30,
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(read_json_file(output_json_path), {"task_id": "from-final-message"})
            validate_agent_attempt_payload(payload)

    def test_run_codex_prompt_extracts_fenced_final_message_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".codex" / "loop-runs" / "run-1"
            prompt_path = run_dir / "prompt.md"
            output_json_path = run_dir / "planner-output.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Do the thing", encoding="utf-8")

            def run_side_effect(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                message_path = Path(command[command.index("--output-last-message") + 1])
                message_path.write_text('Here is the payload:\n```json\n{"task_id":"from-fence"}\n```', encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, stdout="done", stderr="")

            with mock.patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": True, "output_last_message": True},
            ), mock.patch("scripts.harness_loop_agents.subprocess.run", side_effect=run_side_effect):
                payload = run_codex_prompt(
                    role="planner",
                    run_id="run-1",
                    repo_root=root,
                    run_dir=run_dir,
                    prompt_path=prompt_path,
                    output_json_path=output_json_path,
                    attempt=1,
                    timeout_seconds=30,
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(read_json_file(output_json_path), {"task_id": "from-fence"})
            validate_agent_attempt_payload(payload)

    def test_run_codex_prompt_treats_missing_contract_output_as_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".codex" / "loop-runs" / "run-1"
            prompt_path = run_dir / "prompt.md"
            output_json_path = run_dir / "planner-output.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Do the thing", encoding="utf-8")

            def run_side_effect(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                message_path = Path(command[command.index("--output-last-message") + 1])
                message_path.write_text("I could not write the output artifact.", encoding="utf-8")
                self.assertTrue(message_path.exists())
                self.assertFalse(output_json_path.exists())
                return subprocess.CompletedProcess(command, 0, stdout="done", stderr="")

            with mock.patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": True, "output_last_message": True},
            ), mock.patch("scripts.harness_loop_agents.subprocess.run", side_effect=run_side_effect):
                payload = run_codex_prompt(
                    role="planner",
                    run_id="run-1",
                    repo_root=root,
                    run_dir=run_dir,
                    prompt_path=prompt_path,
                    output_json_path=output_json_path,
                    attempt=1,
                    timeout_seconds=30,
                )

            self.assertEqual(payload["status"], "invalid_json")
            self.assertEqual(payload["exit_code"], 0)
            self.assertEqual(payload["output_json_path"], str(output_json_path))
            validate_agent_attempt_payload(payload)

    def test_run_codex_prompt_handles_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".codex" / "loop-runs" / "run-1"
            prompt_path = run_dir / "prompt.md"
            output_json_path = run_dir / "planner-output.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Do the thing", encoding="utf-8")
            timeout = subprocess.TimeoutExpired(
                ["codex"],
                timeout=3,
                output="before timeout",
                stderr="too slow",
            )

            with mock.patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": False, "output_last_message": False},
            ), mock.patch("scripts.harness_loop_agents.subprocess.run", side_effect=timeout):
                payload = run_codex_prompt(
                    role="generator",
                    run_id="run-1",
                    repo_root=root,
                    run_dir=run_dir,
                    prompt_path=prompt_path,
                    output_json_path=output_json_path,
                    attempt=2,
                    timeout_seconds=3,
                )

            self.assertEqual(payload["status"], "timeout")
            self.assertEqual(payload["exit_code"], 124)
            validate_agent_attempt_payload(payload)
            self.assertEqual((run_dir / "generator-attempt-2.stdout.log").read_text(encoding="utf-8"), "before timeout")
            self.assertIn("too slow", (run_dir / "generator-attempt-2.stderr.log").read_text(encoding="utf-8"))
            self.assertEqual(json.loads((run_dir / "generator-attempt-2.json").read_text(encoding="utf-8")), payload)

    def test_run_codex_prompt_recovers_timeout_when_final_message_is_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".codex" / "loop-runs" / "run-1"
            prompt_path = run_dir / "prompt.md"
            output_json_path = run_dir / "planner-output.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Do the thing", encoding="utf-8")

            def run_side_effect(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                message_path = Path(command[command.index("--output-last-message") + 1])
                message_path.write_text('{"task_id":"from-timeout-final-message"}', encoding="utf-8")
                raise subprocess.TimeoutExpired(
                    command,
                    timeout=3,
                    output="before timeout",
                    stderr="too slow",
                )

            with mock.patch(
                "scripts.harness_loop_agents.codex_exec_capabilities",
                return_value={"json": True, "output_last_message": True},
            ), mock.patch("scripts.harness_loop_agents.subprocess.run", side_effect=run_side_effect):
                payload = run_codex_prompt(
                    role="planner",
                    run_id="run-1",
                    repo_root=root,
                    run_dir=run_dir,
                    prompt_path=prompt_path,
                    output_json_path=output_json_path,
                    attempt=3,
                    timeout_seconds=3,
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["exit_code"], 124)
            self.assertEqual(read_json_file(output_json_path), {"task_id": "from-timeout-final-message"})
            validate_agent_attempt_payload(payload)


if __name__ == "__main__":
    unittest.main()
