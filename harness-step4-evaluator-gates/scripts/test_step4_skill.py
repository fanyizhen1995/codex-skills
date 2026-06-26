#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from install_step4 import main as install_main
from patch_codex_config import main as patch_main
import run_live_smoke
from run_live_smoke import main as smoke_main


class Step4SkillTests(unittest.TestCase):
    def test_send_terminal_line_uses_carriage_return(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        run_live_smoke._send_terminal_line(child, "/exit")
        self.assertEqual(child.sent, ["/exit\r"])

    def test_startup_prompt_dismisses_update_banner_only_once(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._indexes = iter([0, 0, 3])

            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return next(self._indexes)

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        run_live_smoke._wait_for_startup_prompt(child, set())
        self.assertEqual(child.sent, ["2\r"])

    def test_startup_prompt_accepts_trust_prompt(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._indexes = iter([2, 7])

            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return next(self._indexes)

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        run_live_smoke._wait_for_startup_prompt(child, set())
        self.assertEqual(child.sent, ["1\r"])

    def test_spawn_interactive_codex_includes_initial_prompt(self) -> None:
        recorded = {}

        class FakeSpawn:
            def __init__(self, _command, args, **kwargs):  # type: ignore[no-untyped-def]
                recorded["args"] = args
                recorded["kwargs"] = kwargs
                self.logfile_read = None
                self._harness_transcript_handle = None

            def isalive(self) -> bool:
                return False

            def close(self, force: bool = False) -> None:
                return None

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            trace_path = repo_root / ".codex" / "tmp" / "trace.jsonl"
            transcript_path = repo_root / ".codex" / "tmp" / "transcript.log"
            with patch.object(run_live_smoke.pexpect, "spawn", FakeSpawn):
                child = run_live_smoke._spawn_interactive_codex(
                    repo_root,
                    trace_path,
                    transcript_path,
                    repo_root / ".codex-home",
                    "demo initial prompt",
                )
                run_live_smoke._close_interactive_codex(child)
            self.assertIsNotNone(child)
            self.assertEqual(recorded["args"][-1], "demo initial prompt")
            self.assertIn("--dangerously-bypass-hook-trust", recorded["args"])
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", recorded["args"])
            self.assertIn("--disable", recorded["args"])
            self.assertIn("plugins", recorded["args"])
            self.assertIn("--cd", recorded["args"])
            self.assertEqual(
                recorded["args"][recorded["args"].index("--cd") + 1],
                str(repo_root),
            )
            self.assertNotEqual(recorded["kwargs"]["cwd"], str(repo_root))

    def test_prepare_isolated_codex_home_copies_required_user_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            user_codex_home = Path(tmp) / "user-codex-home"
            user_codex_home.mkdir()
            (user_codex_home / "config.toml").write_text(
                '\n'.join(
                    [
                        'cli_auth_credentials_store = "file"',
                        'model_provider = "infra44"',
                        'model = "gpt-5.5"',
                        'review_model = "gpt-5.5"',
                        'model_reasoning_effort = "xhigh"',
                        'disable_response_storage = true',
                        'personality = "pragmatic"',
                        "",
                        "[model_providers.infra44]",
                        'name = "infra44"',
                        'base_url = "http://example.invalid/v1"',
                        'wire_api = "responses"',
                        "requires_openai_auth = true",
                        "",
                        "[mcp_servers.playwright]",
                        'command = "npx"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (user_codex_home / "auth.json").write_text('{"access_token":"token"}\n', encoding="utf-8")
            (user_codex_home / "installation_id").write_text("install-1\n", encoding="utf-8")
            with patch.object(run_live_smoke, "_user_codex_home", return_value=user_codex_home):
                isolated = run_live_smoke._prepare_isolated_codex_home(repo_root, "20260625T000000Z")

            self.assertTrue((isolated / "config.toml").exists())
            self.assertTrue((isolated / "auth.json").exists())
            self.assertTrue((isolated / "installation_id").exists())
            config_text = (isolated / "config.toml").read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.5"', config_text)
            self.assertIn('model_provider = "infra44"', config_text)
            self.assertIn("[model_providers.infra44]", config_text)
            self.assertIn("[features]\nplugins = false", config_text)
            self.assertIn(
                f'[projects."{repo_root}"]\ntrust_level = "trusted"',
                config_text,
            )
            self.assertIn("Running task evaluator auto-gate", config_text)
            self.assertIn("Checking evaluator subagent output", config_text)
            self.assertNotIn("[mcp_servers.playwright]", config_text)

    def test_park_repo_local_codex_configs_moves_ancestor_configs_and_restores_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "main" / ".worktrees" / "task-01"
            repo_root.mkdir(parents=True)
            ancestor_config = root / "main" / ".codex" / "config.toml"
            ancestor_config.parent.mkdir(parents=True)
            ancestor_config.write_text("old hook config\n", encoding="utf-8")
            user_config = root / ".codex" / "config.toml"
            user_config.parent.mkdir(parents=True)
            user_config.write_text("user config\n", encoding="utf-8")

            with patch.object(run_live_smoke, "_git_repo_root", return_value=root / "main"):
                parked = run_live_smoke._park_repo_local_codex_configs(repo_root)
            self.assertFalse(ancestor_config.exists())
            self.assertTrue(user_config.exists())
            self.assertEqual(len(parked), 1)
            parked_path, restore_path = parked[0]
            self.assertTrue(parked_path.exists())
            self.assertEqual(restore_path, ancestor_config)

            run_live_smoke._restore_parked_repo_local_codex_configs(parked)
            self.assertTrue(ancestor_config.exists())
            self.assertEqual(ancestor_config.read_text(encoding="utf-8"), "old hook config\n")

    def test_park_repo_local_codex_configs_moves_shared_checkout_config_for_nested_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_checkout = root / "main"
            repo_root = shared_checkout / ".worktrees" / "task-01"
            repo_root.mkdir(parents=True)
            shared_config = shared_checkout / ".codex" / "config.toml"
            shared_config.parent.mkdir(parents=True)
            shared_config.write_text("shared hook config\n", encoding="utf-8")

            with patch.object(run_live_smoke, "_git_repo_root", return_value=repo_root), patch.object(
                run_live_smoke,
                "_git_common_checkout_root",
                return_value=shared_checkout,
            ):
                parked = run_live_smoke._park_repo_local_codex_configs(repo_root)

            self.assertFalse(shared_config.exists())
            self.assertEqual(len(parked), 1)
            parked_path, restore_path = parked[0]
            self.assertTrue(parked_path.exists())
            self.assertEqual(restore_path, shared_config)

            run_live_smoke._restore_parked_repo_local_codex_configs(parked)
            self.assertTrue(shared_config.exists())
            self.assertEqual(shared_config.read_text(encoding="utf-8"), "shared hook config\n")

    def test_wait_for_implementation_accepts_trust_prompt(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._indexes = iter([2])

            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return next(self._indexes)

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        with patch.object(run_live_smoke, "_demo_output_ready", side_effect=[False, True]), patch.object(
            run_live_smoke,
            "_progress_marker_present",
            return_value=True,
        ):
            run_live_smoke._wait_for_implementation(
                child,
                Path("/tmp/repo"),
                "demo-task",
                "marker",
                set(),
            )
        self.assertEqual(child.sent, ["1\r"])

    def test_wait_for_exit_accepts_trust_prompt(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._indexes = iter([4, 6])

            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return next(self._indexes)

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        exited = run_live_smoke._wait_for_exit(child, set())
        self.assertTrue(exited)
        self.assertEqual(child.sent, ["1\r"])

    def test_wait_for_exit_requests_exit_after_prompt(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._indexes = iter([5, 6])

            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return next(self._indexes)

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        exited = run_live_smoke._wait_for_exit(child, set())
        self.assertTrue(exited)
        self.assertEqual(child.sent, ["/exit\r"])

    def test_wait_for_exit_detects_prompt_after_explicit_exit(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self._indexes = iter([5])

            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return next(self._indexes)

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        with self.assertRaisesRegex(RuntimeError, "returned to the prompt instead of exiting"):
            run_live_smoke._wait_for_exit(child, set(), exit_requested=True)
        self.assertEqual(child.sent, [])

    def test_install_step4_copies_template_and_inserts_demo_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "repo"
            repo_root.mkdir()
            (repo_root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
            (repo_root / "progress.md").write_text("# progress\n", encoding="utf-8")
            (repo_root / "docs").mkdir()
            (repo_root / "tasks.json").write_text(
                json.dumps({"tasks": []}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            with patch("sys.argv", ["install_step4.py", "--repo-root", str(repo_root)]):
                exit_code = install_main()

            self.assertEqual(exit_code, 0)
            tasks_payload = json.loads((repo_root / "tasks.json").read_text(encoding="utf-8"))
            self.assertTrue(any(task["id"] == "harness-evaluator-demo-01" for task in tasks_payload["tasks"]))
            self.assertTrue((repo_root / "scripts" / "harness_evaluator_hook_driver.py").exists())
            result_schema = (
                repo_root / ".codex" / "evaluations" / "templates" / "result.schema.json"
            )
            self.assertTrue(result_schema.exists())
            result_schema_payload = json.loads(result_schema.read_text(encoding="utf-8"))
            self.assertEqual(result_schema_payload["type"], "object")
            self.assertIn("status", result_schema_payload["properties"])
            scenario_item = result_schema_payload["properties"]["scenario_results"]["items"]
            self.assertEqual(
                sorted(scenario_item["required"]),
                sorted(scenario_item["properties"].keys()),
            )
            self.assertTrue(
                (repo_root / "docs" / "harness" / "evaluator-scenarios" / "harness-evaluator-demo-01.json").exists()
            )

    def test_patch_codex_config_inserts_hook_blocks_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text('model = "gpt-5.5"\n', encoding="utf-8")

            with patch("sys.argv", ["patch_codex_config.py", "--config", str(config_path)]):
                exit_code = patch_main()

            self.assertEqual(exit_code, 0)
            text = config_path.read_text(encoding="utf-8")
            self.assertIn(
                'command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py stop; else printf \'{\\"continue\\":true}\\\\n\'; fi"',
                text,
            )
            self.assertIn("timeout = 180", text)
            self.assertIn(
                'command = "if [ -f scripts/harness_evaluator_hook_driver.py ]; then python3 scripts/harness_evaluator_hook_driver.py subagent-stop; else printf \'{\\"continue\\":true}\\\\n\'; fi"',
                text,
            )

    def test_patch_codex_config_uses_json_noop_when_repo_script_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text('model = "gpt-5.5"\n', encoding="utf-8")

            with patch("sys.argv", ["patch_codex_config.py", "--config", str(config_path)]):
                exit_code = patch_main()

            self.assertEqual(exit_code, 0)
            text = config_path.read_text(encoding="utf-8")
            self.assertIn("printf '{\\\"continue\\\":true}\\\\n'", text)

    def test_run_live_smoke_drives_interactive_flow_and_checks_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            session_dir = repo_root / ".codex" / "session-state"
            session_dir.mkdir(parents=True)
            original_session = session_dir / "main.json"
            original_session.write_text(
                json.dumps({"task": "main-task", "worktree": str(repo_root)}, ensure_ascii=False),
                encoding="utf-8",
            )
            trace_path = repo_root / ".codex" / "tmp" / "trace.jsonl"
            transcript_path = repo_root / ".codex" / "tmp" / "transcript.log"
            observed = {}

            class FakeChild:
                def isalive(self) -> bool:
                    return False

                def close(self, force: bool = False) -> None:
                    return None

            def fake_run_interactive_smoke_session(
                path: Path, task_id: str, run_id: str
            ) -> tuple[FakeChild, Path, Path, Path, bool]:
                observed["repo_root"] = path
                observed["task_id"] = task_id
                observed["run_id"] = run_id
                demo_dir = repo_root / ".codex" / "evaluator-demo" / task_id
                demo_dir.mkdir(parents=True, exist_ok=True)
                (demo_dir / "result.txt").write_text("step4-ready\n", encoding="utf-8")
                repo_root.joinpath("progress.md").write_text(
                    f"# progress\n- {task_id} live smoke implementation finished ({run_id})\n",
                    encoding="utf-8",
                )
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                trace_path.write_text(
                    json.dumps({"mode": "stop", "cwd": str(repo_root), "recursive_guard": False}) + "\n",
                    encoding="utf-8",
                )
                result_dir = (
                    repo_root
                    / ".codex"
                    / "evaluations"
                    / "tasks"
                    / task_id
                    / "20260625T000001Z-attempt-1"
                )
                result_dir.mkdir(parents=True, exist_ok=True)
                (result_dir / "result.json").write_text(
                    json.dumps(
                        {
                            "status": "pass",
                            "gate": "task",
                            "task_id": task_id,
                        }
                    ),
                    encoding="utf-8",
                )
                transcript_path.write_text("interactive smoke transcript\n", encoding="utf-8")
                return FakeChild(), trace_path, transcript_path, repo_root / ".codex-home", True

            with patch.object(
                run_live_smoke,
                "_run_interactive_smoke_session",
                side_effect=fake_run_interactive_smoke_session,
            ):
                with patch("sys.argv", ["run_live_smoke.py", "--repo-root", str(repo_root)]):
                    exit_code = smoke_main()

            self.assertEqual(exit_code, 0)
            session_state = repo_root / ".codex" / "session-state" / "harness-evaluator-demo-01-live-smoke.json"
            self.assertFalse(session_state.exists())
            self.assertTrue(original_session.exists())
            self.assertEqual(observed["repo_root"], repo_root)
            self.assertEqual(observed["task_id"], "harness-evaluator-demo-01")
            self.assertTrue(trace_path.exists())
            self.assertTrue(transcript_path.exists())

    def test_run_live_smoke_accepts_pass_result_even_if_interactive_exit_was_forced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / ".codex" / "session-state").mkdir(parents=True)
            trace_path = repo_root / ".codex" / "tmp" / "trace.jsonl"
            transcript_path = repo_root / ".codex" / "tmp" / "transcript.log"
            result_dir = (
                repo_root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "harness-evaluator-demo-01"
                / "20260625T000001Z-attempt-1"
            )

            class FakeChild:
                def isalive(self) -> bool:
                    return False

                def close(self, force: bool = False) -> None:
                    return None

            def fake_run_interactive_smoke_session(
                _: Path, task_id: str, __: str
            ) -> tuple[FakeChild, Path, Path, Path, bool]:
                demo_dir = repo_root / ".codex" / "evaluator-demo" / task_id
                demo_dir.mkdir(parents=True, exist_ok=True)
                (demo_dir / "result.txt").write_text("step4-ready\n", encoding="utf-8")
                repo_root.joinpath("progress.md").write_text("# progress\n", encoding="utf-8")
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                trace_path.write_text(
                    json.dumps({"mode": "stop", "cwd": str(repo_root), "recursive_guard": False}) + "\n",
                    encoding="utf-8",
                )
                transcript_path.write_text("interactive smoke transcript\n", encoding="utf-8")
                return FakeChild(), trace_path, transcript_path, repo_root / ".codex-home", False

            fake_payload = {
                "status": "pass",
                "gate": "task",
                "task_id": "harness-evaluator-demo-01",
            }
            with patch.object(
                run_live_smoke,
                "_run_interactive_smoke_session",
                side_effect=fake_run_interactive_smoke_session,
            ), patch.object(
                run_live_smoke,
                "_wait_for_new_result",
                return_value=(result_dir, fake_payload),
            ):
                with patch("sys.argv", ["run_live_smoke.py", "--repo-root", str(repo_root)]):
                    exit_code = smoke_main()

            self.assertEqual(exit_code, 0)

    def test_run_interactive_smoke_waits_for_transcript_idle_before_exit(self) -> None:
        events: list[str] = []

        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []
                self.logfile_read = None
                self._harness_transcript_handle = None

            def isalive(self) -> bool:
                return False

            def close(self, force: bool = False) -> None:
                return None

            def send(self, text: str) -> None:
                events.append(f"send:{text}")

        def fake_wait_for_startup_prompt(_child, _dismissed) -> None:  # type: ignore[no-untyped-def]
            events.append("startup")

        def fake_wait_for_implementation(_child, repo_root, task_id, marker, _dismissed) -> None:  # type: ignore[no-untyped-def]
            events.append("implementation")
            demo_dir = repo_root / ".codex" / "evaluator-demo" / task_id
            demo_dir.mkdir(parents=True, exist_ok=True)
            (demo_dir / "result.txt").write_text("step4-ready\n", encoding="utf-8")
            repo_root.joinpath("progress.md").write_text(f"# progress\n{marker}\n", encoding="utf-8")

        def fake_wait_for_transcript_idle(path: Path, **_kwargs) -> None:
            events.append(f"idle:{path.name}")

        def fake_wait_for_exit(_child, _dismissed, *, exit_requested=False) -> None:  # type: ignore[no-untyped-def]
            events.append(f"exit:{exit_requested}")
            return True

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            trace_path = repo_root / ".codex" / "tmp" / "trace.jsonl"
            transcript_path = repo_root / ".codex" / "tmp" / "transcript.log"
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            transcript_path.write_text("transcript\n", encoding="utf-8")
            child = FakeChild()

            with patch.object(run_live_smoke, "_spawn_interactive_codex", return_value=child), patch.object(
                run_live_smoke,
                "_wait_for_startup_prompt",
                side_effect=fake_wait_for_startup_prompt,
            ), patch.object(
                run_live_smoke,
                "_wait_for_implementation",
                side_effect=fake_wait_for_implementation,
            ), patch.object(
                run_live_smoke,
                "_wait_for_transcript_idle",
                side_effect=fake_wait_for_transcript_idle,
            ), patch.object(
                run_live_smoke,
                "_wait_for_exit",
                side_effect=fake_wait_for_exit,
            ):
                run_live_smoke._run_interactive_smoke(repo_root, "harness-evaluator-demo-01", "20260625T000000Z")

        self.assertEqual(events[0:2], ["startup", "implementation"])
        self.assertTrue(events[2].startswith("idle:harness-evaluator-demo-01-live-smoke-"))
        self.assertEqual(events[3], "send:/exit\r")
        self.assertEqual(events[4], "exit:True")

    def test_wait_for_exit_returns_false_after_timeout(self) -> None:
        class FakeChild:
            def __init__(self) -> None:
                self.sent: list[str] = []

            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return 7

            def send(self, text: str) -> None:
                self.sent.append(text)

        child = FakeChild()
        with patch.object(run_live_smoke.time, "monotonic", side_effect=[0, 0, 181]):
            exited = run_live_smoke._wait_for_exit(child, set(), exit_requested=True)
        self.assertFalse(exited)

    def test_wait_for_exit_returns_false_after_exit_requested_idle_grace(self) -> None:
        class FakeChild:
            def expect(self, _patterns, timeout=0):  # type: ignore[no-untyped-def]
                return 7

        child = FakeChild()
        with patch.object(run_live_smoke.time, "monotonic", side_effect=[0, 0, 0, 91]):
            exited = run_live_smoke._wait_for_exit(child, set(), exit_requested=True)
        self.assertFalse(exited)

    def test_wait_for_new_result_detects_new_pass_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            bundle = (
                repo_root
                / ".codex"
                / "evaluations"
                / "tasks"
                / "harness-evaluator-demo-01"
                / "20260625T000001Z-attempt-1"
            )
            bundle.mkdir(parents=True, exist_ok=True)
            (bundle / "result.json").write_text(
                json.dumps({"status": "pass", "gate": "task", "task_id": "harness-evaluator-demo-01"}),
                encoding="utf-8",
            )
            latest, payload = run_live_smoke._wait_for_new_result(
                repo_root,
                "harness-evaluator-demo-01",
                existing_bundles=set(),
                timeout_seconds=1,
            )
        self.assertEqual(latest.name, "20260625T000001Z-attempt-1")
        self.assertEqual(payload["status"], "pass")

    def test_run_live_smoke_fails_when_interactive_flow_creates_no_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / ".codex" / "session-state").mkdir(parents=True)
            transcript_path = repo_root / ".codex" / "tmp" / "transcript.log"

            class FakeChild:
                def isalive(self) -> bool:
                    return False

                def close(self, force: bool = False) -> None:
                    return None

            def fake_run_interactive_smoke_session(
                _: Path, task_id: str, __: str
            ) -> tuple[FakeChild, Path, Path, Path, bool]:
                demo_dir = repo_root / ".codex" / "evaluator-demo" / task_id
                demo_dir.mkdir(parents=True, exist_ok=True)
                (demo_dir / "result.txt").write_text("step4-ready\n", encoding="utf-8")
                repo_root.joinpath("progress.md").write_text("# progress\n", encoding="utf-8")
                result_dir = (
                    repo_root
                    / ".codex"
                    / "evaluations"
                    / "tasks"
                    / task_id
                    / "20260625T000001Z-attempt-1"
                )
                result_dir.mkdir(parents=True, exist_ok=True)
                (result_dir / "result.json").write_text(
                    json.dumps(
                        {
                            "status": "pass",
                            "gate": "task",
                            "task_id": task_id,
                        }
                    ),
                    encoding="utf-8",
                )
                transcript_path.parent.mkdir(parents=True, exist_ok=True)
                transcript_path.write_text("interactive smoke transcript\n", encoding="utf-8")
                return (
                    FakeChild(),
                    repo_root / ".codex" / "tmp" / "missing.trace.jsonl",
                    transcript_path,
                    repo_root / ".codex-home",
                    True,
                )

            with patch.object(
                run_live_smoke,
                "_run_interactive_smoke_session",
                side_effect=fake_run_interactive_smoke_session,
            ):
                with patch("sys.argv", ["run_live_smoke.py", "--repo-root", str(repo_root)]):
                    with self.assertRaises(SystemExit) as ctx:
                        smoke_main()

            self.assertIn("Stop hook trace was not written", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
