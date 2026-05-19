#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


SCRIPT = Path(__file__).with_name("route.py")


class MockHandler(BaseHTTPRequestHandler):
    requests = []
    status = 200
    body = {
        "choices": [
            {"message": {"content": "mocked cheap model answer"}},
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5},
    }

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "payload": payload,
            }
        )
        response = json.dumps(type(self).body).encode("utf-8")
        self.send_response(type(self).status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *_args):
        return


class RouteScriptTest(unittest.TestCase):
    def setUp(self):
        MockHandler.requests = []
        MockHandler.status = 200
        MockHandler.body = {
            "choices": [
                {"message": {"content": "mocked cheap model answer"}},
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5},
        }

    def run_script(self, args, env=None, input_text=None):
        merged_env = os.environ.copy()
        for key in list(merged_env):
            if key.startswith("CHEAP_MODEL_"):
                del merged_env[key]
        if env:
            merged_env.update(env)
        if "CODEX_HOME" in merged_env:
            return self._run_script(args, merged_env, input_text)
        with tempfile.TemporaryDirectory() as tmpdir:
            merged_env["CODEX_HOME"] = tmpdir
            return self._run_script(args, merged_env, input_text)

    def _run_script(self, args, env, input_text=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=input_text,
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
        )

    def test_missing_config_fails_before_network(self):
        result = self.run_script(["--task", "Summarize this text"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CHEAP_MODEL_BASE_URL", result.stderr)

    def test_sends_openai_compatible_payload(self):
        with running_server() as base_url:
            result = self.run_script(
                [
                    "--task",
                    "Summarize",
                    "--input",
                    "Long text",
                    "--temperature",
                    "0.1",
                    "--max-tokens",
                    "123",
                ],
                env={
                    "CHEAP_MODEL_BASE_URL": base_url,
                    "CHEAP_MODEL_API_KEY": "secret-key",
                    "CHEAP_MODEL_NAME": "cheap/test-model",
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mocked cheap model answer", result.stdout)
        self.assertEqual(len(MockHandler.requests), 1)
        request = MockHandler.requests[0]
        self.assertEqual(request["path"], "/v1/chat/completions")
        self.assertEqual(request["headers"]["Authorization"], "Bearer secret-key")
        self.assertEqual(request["payload"]["model"], "cheap/test-model")
        self.assertEqual(request["payload"]["max_tokens"], 123)
        self.assertEqual(request["payload"]["temperature"], 0.1)
        self.assertEqual(request["payload"]["messages"][-1]["role"], "user")

    def test_reuses_codex_config_with_responses_api(self):
        with tempfile.TemporaryDirectory() as tmpdir, running_server() as base_url:
            codex_home = Path(tmpdir)
            (codex_home / "config.toml").write_text(
                f'''
model_provider = "sub2api"
model = "gpt-5.5"

[model_providers.sub2api]
name = "sub2api"
base_url = "{base_url}"
wire_api = "responses"
requires_openai_auth = true
''',
                encoding="utf-8",
            )
            (codex_home / "auth.json").write_text(
                json.dumps({"OPENAI_API_KEY": "codex-secret"}),
                encoding="utf-8",
            )

            result = self.run_script(
                ["--task", "Rewrite", "--input", "hello"],
                env={
                    "CODEX_HOME": str(codex_home),
                    "CHEAP_MODEL_NAME": "gpt-5.4-mini",
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mocked cheap model answer", result.stdout)
        request = MockHandler.requests[0]
        self.assertEqual(request["path"], "/v1/responses")
        self.assertEqual(request["headers"]["Authorization"], "Bearer codex-secret")
        self.assertEqual(request["payload"]["model"], "gpt-5.4-mini")
        self.assertIn("input", request["payload"])
        self.assertNotIn("messages", request["payload"])

    def test_defaults_to_gpt_54_mini_with_codex_config(self):
        with tempfile.TemporaryDirectory() as tmpdir, running_server() as base_url:
            codex_home = Path(tmpdir)
            (codex_home / "config.toml").write_text(
                f'''
model_provider = "sub2api"
model = "gpt-5.5"

[model_providers.sub2api]
name = "sub2api"
base_url = "{base_url}"
wire_api = "responses"
requires_openai_auth = true
''',
                encoding="utf-8",
            )
            (codex_home / "auth.json").write_text(
                json.dumps({"OPENAI_API_KEY": "codex-secret"}),
                encoding="utf-8",
            )

            result = self.run_script(
                ["--task", "Rewrite", "--input", "hello"],
                env={"CODEX_HOME": str(codex_home)},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        request = MockHandler.requests[0]
        self.assertEqual(request["payload"]["model"], "gpt-5.4-mini")

    def test_model_flag_overrides_default(self):
        with tempfile.TemporaryDirectory() as tmpdir, running_server() as base_url:
            codex_home = Path(tmpdir)
            (codex_home / "config.toml").write_text(
                f'''
model_provider = "sub2api"

[model_providers.sub2api]
base_url = "{base_url}"
wire_api = "responses"
''',
                encoding="utf-8",
            )

            result = self.run_script(
                ["--task", "Rewrite", "--input", "hello", "--model", "custom-mini"],
                env={"CODEX_HOME": str(codex_home)},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        request = MockHandler.requests[0]
        self.assertEqual(request["payload"]["model"], "custom-mini")

    def test_rejects_oversized_input_by_default(self):
        result = self.run_script(
            ["--task", "Summarize", "--input", "x" * 12001],
            env={
                "CHEAP_MODEL_BASE_URL": "http://127.0.0.1:9/v1",
                "CHEAP_MODEL_NAME": "cheap/test-model",
            },
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("input too large", result.stderr)

    def test_truncates_when_requested(self):
        with running_server() as base_url:
            result = self.run_script(
                ["--task", "Summarize", "--input", "x" * 12001, "--truncate"],
                env={
                    "CHEAP_MODEL_BASE_URL": base_url,
                    "CHEAP_MODEL_NAME": "cheap/test-model",
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        user_content = MockHandler.requests[0]["payload"]["messages"][-1][
            "content"
        ]
        self.assertLessEqual(len(user_content), 12500)
        self.assertIn("[truncated]", user_content)

    def test_reports_api_errors(self):
        MockHandler.status = 500
        MockHandler.body = {"error": {"message": "backend unavailable"}}
        with running_server() as base_url:
            result = self.run_script(
                ["--task", "Summarize", "--input", "text"],
                env={
                    "CHEAP_MODEL_BASE_URL": base_url,
                    "CHEAP_MODEL_NAME": "cheap/test-model",
                },
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("backend unavailable", result.stderr)

    def test_writes_success_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir, running_server() as base_url:
            log_file = Path(tmpdir) / "route.jsonl"
            result = self.run_script(
                [
                    "--task",
                    "Summarize",
                    "--input",
                    "text",
                    "--log-file",
                    str(log_file),
                ],
                env={
                    "CHEAP_MODEL_BASE_URL": base_url,
                    "CHEAP_MODEL_NAME": "cheap/test-model",
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["task"], "Summarize")
        self.assertEqual(event["model"], "cheap/test-model")
        self.assertEqual(event["wire_api"], "chat")
        self.assertEqual(event["input_chars"], 4)
        self.assertEqual(event["output_chars"], len("mocked cheap model answer"))
        self.assertTrue(event["success"])
        self.assertEqual(event["usage"], {"prompt_tokens": 12, "completion_tokens": 5})

    def test_writes_failure_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "route.jsonl"
            result = self.run_script(
                [
                    "--task",
                    "Summarize",
                    "--input",
                    "text",
                    "--log-file",
                    str(log_file),
                ]
            )

            self.assertNotEqual(result.returncode, 0)
            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["task"], "Summarize")
        self.assertFalse(event["success"])
        self.assertIn("CHEAP_MODEL_BASE_URL", event["error"])
        self.assertIsNone(event["input_chars"])

    def test_no_log_disables_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir, running_server() as base_url:
            log_file = Path(tmpdir) / "route.jsonl"
            result = self.run_script(
                [
                    "--task",
                    "Summarize",
                    "--input",
                    "text",
                    "--log-file",
                    str(log_file),
                    "--no-log",
                ],
                env={
                    "CHEAP_MODEL_BASE_URL": base_url,
                    "CHEAP_MODEL_NAME": "cheap/test-model",
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(log_file.exists())


class running_server:
    def __enter__(self):
        self.server = HTTPServer(("127.0.0.1", 0), MockHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


if __name__ == "__main__":
    unittest.main()
