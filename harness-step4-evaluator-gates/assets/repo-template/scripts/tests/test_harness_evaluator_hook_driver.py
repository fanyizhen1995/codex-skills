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

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import harness_evaluator_hook_driver


class HarnessEvaluatorHookDriverTests(unittest.TestCase):
    def test_main_with_payload_writes_trace_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "hook-trace.jsonl"
            with patch.dict(
                os.environ,
                {"HARNESS_EVALUATOR_TRACE_FILE": str(trace_path)},
                clear=False,
            ):
                with patch.object(
                    harness_evaluator_hook_driver,
                    "_run_stop_pipeline",
                    return_value=None,
                ):
                    exit_code = harness_evaluator_hook_driver.main_with_payload(
                        "stop",
                        {"cwd": str(root)},
                    )
            self.assertEqual(exit_code, 0)
            lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["mode"], "stop")
            self.assertEqual(payload["cwd"], str(root))
            self.assertFalse(payload["recursive_guard"])

    def test_main_with_payload_skips_when_recursive_guard_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = io.StringIO()
            with patch.dict(os.environ, {"HARNESS_EVALUATOR_SKIP_HOOKS": "1"}, clear=False):
                with patch.object(
                    harness_evaluator_hook_driver,
                    "_run_stop_pipeline",
                ) as mocked_pipeline:
                    with redirect_stdout(output):
                        exit_code = harness_evaluator_hook_driver.main_with_payload("stop", {"cwd": str(root)})
        self.assertEqual(exit_code, 0)
        mocked_pipeline.assert_not_called()
        self.assertEqual(json.loads(output.getvalue().strip()), {"continue": True})

    def test_main_with_payload_stop_returns_zero_when_pipeline_allows_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {"cwd": str(root)}
            output = io.StringIO()
            with patch.object(
                harness_evaluator_hook_driver,
                "_run_stop_pipeline",
                return_value=None,
            ) as mocked_pipeline:
                with redirect_stdout(output):
                    exit_code = harness_evaluator_hook_driver.main_with_payload("stop", payload)

            self.assertEqual(exit_code, 0)
            mocked_pipeline.assert_called_once_with(root)
            self.assertEqual(json.loads(output.getvalue().strip()), {"continue": True})

    def test_main_with_payload_prints_decision_when_stop_pipeline_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {"cwd": str(root)}
            decision = {
                "decision": "block",
                "reason": "rerun task evaluator",
                "action": "rerun_task_evaluator",
                "bundle_dir": str(root / "bundle"),
            }
            output = io.StringIO()
            with patch.object(
                harness_evaluator_hook_driver,
                "_run_stop_pipeline",
                return_value=decision,
            ):
                with redirect_stdout(output):
                    exit_code = harness_evaluator_hook_driver.main_with_payload("stop", payload)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                json.loads(output.getvalue().strip()),
                {
                    "continue": False,
                    "stopReason": "rerun task evaluator",
                },
            )

    def test_main_with_payload_returns_stop_reason_when_stop_hook_already_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {
                "cwd": str(root),
                "stop_hook_active": True,
            }
            decision = {
                "decision": "block",
                "reason": "rerun task evaluator",
                "action": "rerun_task_evaluator",
                "bundle_dir": str(root / "bundle"),
            }
            output = io.StringIO()
            with patch.object(
                harness_evaluator_hook_driver,
                "_run_stop_pipeline",
                return_value=decision,
            ):
                with redirect_stdout(output):
                    exit_code = harness_evaluator_hook_driver.main_with_payload("stop", payload)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                json.loads(output.getvalue().strip()),
                {
                    "continue": False,
                    "stopReason": "rerun task evaluator",
                },
            )

    def test_main_with_payload_subagent_stop_returns_continue_when_unblocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = io.StringIO()
            with patch.object(
                harness_evaluator_hook_driver.harness_evaluator_hooks,
                "subagent_stop_hook",
                return_value=None,
            ) as mocked_hook:
                with redirect_stdout(output):
                    exit_code = harness_evaluator_hook_driver.main_with_payload(
                        "subagent-stop",
                        {"cwd": str(root)},
                    )

        self.assertEqual(exit_code, 0)
        mocked_hook.assert_called_once_with(root)
        self.assertEqual(json.loads(output.getvalue().strip()), {"continue": True})

    def test_run_stop_pipeline_chains_once_into_final_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = {"task": "demo-task"}
            final_decision = {
                "decision": "soft_block",
                "reason": "final evaluator flagged report risk",
                "action": "rerun_final_evaluator",
                "bundle_dir": str(root / "final-bundle"),
            }
            with patch.object(
                harness_evaluator_hook_driver.harness_evaluator_hooks,
                "_resolve_session",
                return_value=session,
            ) as mocked_session, patch.object(
                harness_evaluator_hook_driver.harness_evaluator_orchestrator,
                "run_one_stop_auto_gate",
                return_value=final_decision,
            ) as mocked_pipeline:
                decision = harness_evaluator_hook_driver._run_stop_pipeline(root)

            self.assertEqual(decision, final_decision)
            mocked_session.assert_called_once_with(root)
            mocked_pipeline.assert_called_once_with("demo-task", root)
