import importlib.util
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "router.py"


def load_router():
    spec = importlib.util.spec_from_file_location("router", APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules["router"] = module
    spec.loader.exec_module(module)
    return module


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class UpstreamHandler(BaseHTTPRequestHandler):
    requests = []
    stream = False
    status = 200
    body = {"id": "resp_mock", "output_text": "upstream answer"}
    response_headers = {}

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length)
        payload = json.loads(body) if body else {}
        type(self).requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "payload": payload,
            }
        )
        if type(self).stream:
            chunks = [
                b"data: {\"type\":\"response.output_text.delta\",\"delta\":\"he\"}\n\n",
                b"data: {\"type\":\"response.output_text.delta\",\"delta\":\"llo\"}\n\n",
                (
                    b"event: response.completed\n"
                    b"data: {\"type\":\"response.completed\",\"response\":{\"id\":\"resp_mock\","
                    b"\"usage\":{\"input_tokens\":27,"
                    b"\"input_tokens_details\":{\"cached_tokens\":9},"
                    b"\"output_tokens\":10,"
                    b"\"output_tokens_details\":{\"reasoning_tokens\":4},"
                    b"\"total_tokens\":37}}}\n\n"
                ),
                b"data: [DONE]\n\n",
            ]
            self.send_response(type(self).status)
            self.send_header("content-type", "text/event-stream")
            for key, value in type(self).response_headers.items():
                self.send_header(key, value)
            self.end_headers()
            for chunk in chunks:
                self.wfile.write(chunk)
                self.wfile.flush()
            return
        response = json.dumps(type(self).body).encode("utf-8")
        self.send_response(type(self).status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(response)))
        for key, value in type(self).response_headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *_args):
        return


class RunningUpstream:
    def __enter__(self):
        UpstreamHandler.requests = []
        UpstreamHandler.stream = False
        UpstreamHandler.status = 200
        UpstreamHandler.body = {"id": "resp_mock", "output_text": "upstream answer"}
        UpstreamHandler.response_headers = {}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


class RunningRouter:
    def __init__(self, upstream, log_file, shadow_mode=False):
        self.port = free_port()
        self.upstream = upstream
        self.log_file = log_file
        self.shadow_mode = shadow_mode
        self.process = None

    def __enter__(self):
        env = os.environ.copy()
        env.update(
            {
                "ROUTER_HOST": "127.0.0.1",
                "ROUTER_PORT": str(self.port),
                "UPSTREAM_BASE_URL": self.upstream,
                "DEFAULT_MODEL": "gpt-5.5",
                "CHEAP_MODEL": "gpt-5.4-mini",
                "ROUTER_LOG_FILE": str(self.log_file),
                "ROUTER_SHADOW_MODE": "true" if self.shadow_mode else "false",
            }
        )
        self.process = subprocess.Popen(
            [sys.executable, str(APP)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/healthz", timeout=0.2)
                return f"http://127.0.0.1:{self.port}/v1"
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.05)
        stdout, stderr = self.process.communicate(timeout=1)
        raise AssertionError(f"router did not start\nstdout={stdout}\nstderr={stderr}")

    def __exit__(self, exc_type, exc, tb):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.process:
            if self.process.stdout:
                self.process.stdout.close()
            if self.process.stderr:
                self.process.stderr.close()


class RouterTest(unittest.TestCase):
    def test_choose_model_routes_simple_text_to_cheap_model(self):
        router = load_router()
        payload = {
            "model": "gpt-5.5",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": "请总结这段文字"}]}],
        }

        decision = router.choose_model(payload)

        self.assertEqual(decision.model, "gpt-5.4-mini")
        self.assertEqual(decision.reason, "simple_text_task")

    def test_choose_model_keeps_tools_on_default_model(self):
        router = load_router()
        payload = {
            "model": "gpt-5.5",
            "input": "请总结",
            "tools": [{"type": "function", "name": "shell"}],
        }

        decision = router.choose_model(payload)

        self.assertEqual(decision.model, "gpt-5.5")
        self.assertEqual(decision.reason, "has_tools")

    def test_shadow_decision_routes_large_request_by_last_user_intent(self):
        router = load_router()
        payload = {
            "model": "gpt-5.5",
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": "x" * 20000}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": "请翻译 hello world"}],
                },
            ],
        }

        decision = router.choose_shadow_model(payload)

        self.assertEqual(decision.model, "gpt-5.4-mini")
        self.assertEqual(decision.reason, "last_user_simple_text_task")

    def test_shadow_decision_keeps_context_dependent_task_on_default_model(self):
        router = load_router()
        payload = {
            "model": "gpt-5.5",
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": "继续按刚才的方案实现"}],
                }
            ],
        }

        decision = router.choose_shadow_model(payload)

        self.assertEqual(decision.model, "gpt-5.5")
        self.assertEqual(decision.reason, "last_user_context_dependent")

    def test_shadow_mode_logs_candidate_without_rewriting_model(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file, shadow_mode=True) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "input": [
                                {
                                    "role": "system",
                                    "content": [
                                        {"type": "input_text", "text": "x" * 20000}
                                    ],
                                },
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "input_text", "text": "请翻译 hello"}
                                    ],
                                },
                            ],
                        }
                    ).encode("utf-8"),
                    headers={"content-type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    json.loads(response.read().decode("utf-8"))

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        upstream_request = UpstreamHandler.requests[0]
        self.assertEqual(upstream_request["payload"]["model"], "gpt-5.5")
        self.assertEqual(events[0]["selected_model"], "gpt-5.5")
        self.assertEqual(events[0]["reason"], "shadow_mode_passthrough")
        self.assertEqual(events[0]["shadow_selected_model"], "gpt-5.4-mini")
        self.assertEqual(events[0]["shadow_reason"], "last_user_simple_text_task")
        self.assertEqual(events[0]["last_user_chars"], len("请翻译 hello"))
        self.assertEqual(events[0]["matched_keyword"], "翻译")
        self.assertIsNone(events[0]["blocker_keyword"])
        self.assertEqual(events[0]["tool_count"], 0)
        self.assertEqual(events[0]["has_tools"], False)
        self.assertEqual(events[0]["previous_response_id"], False)
        self.assertEqual(events[0]["last_user_excerpt"], "请翻译 hello")
        self.assertTrue(events[0]["last_user_hash"].startswith("sha256:"))

    def test_shadow_log_records_blocker_keyword_and_tool_count(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file, shadow_mode=True) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "input": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "input_text", "text": "请运行测试"}
                                    ],
                                }
                            ],
                            "tools": [
                                {"type": "function", "name": "shell"},
                                {"type": "image_generation"},
                            ],
                        }
                    ).encode("utf-8"),
                    headers={"content-type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    json.loads(response.read().decode("utf-8"))

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(events[0]["shadow_reason"], "has_tools")
        self.assertEqual(events[0]["tool_count"], 2)
        self.assertEqual(events[0]["tool_types"], ["function", "image_generation"])
        self.assertIsNone(events[0]["matched_keyword"])
        self.assertEqual(events[0]["blocker_keyword"], "测试")

    def test_forwards_responses_request_and_rewrites_model(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            UpstreamHandler.body = {
                "id": "resp_mock",
                "output_text": "upstream answer",
                "usage": {
                    "input_tokens": 25,
                    "input_tokens_details": {"cached_tokens": 10},
                    "output_tokens": 7,
                    "output_tokens_details": {"reasoning_tokens": 3},
                    "total_tokens": 32,
                },
            }
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "input": "请翻译 hello",
                        }
                    ).encode("utf-8"),
                    headers={
                        "content-type": "application/json",
                        "authorization": "Bearer test-key",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    body = json.loads(response.read().decode("utf-8"))

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(body["output_text"], "upstream answer")
        self.assertEqual(len(UpstreamHandler.requests), 1)
        upstream_request = UpstreamHandler.requests[0]
        self.assertEqual(upstream_request["path"], "/v1/responses")
        self.assertEqual(upstream_request["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(upstream_request["payload"]["model"], "gpt-5.4-mini")
        self.assertEqual(
            upstream_request["payload"]["prompt_cache_key"],
            "codex:gpt-5.4-mini:no-tools:responses",
        )
        self.assertEqual(events[0]["selected_model"], "gpt-5.4-mini")
        self.assertEqual(events[0]["reason"], "simple_text_task")
        self.assertEqual(events[0]["status"], 200)
        self.assertEqual(
            events[0]["prompt_cache_key"],
            "codex:gpt-5.4-mini:no-tools:responses",
        )
        self.assertEqual(events[0]["prompt_cache_key_source"], "router_generated")
        self.assertIsNone(events[0]["prompt_cache_tool_hash"])
        self.assertEqual(events[0]["usage_input_tokens"], 25)
        self.assertEqual(events[0]["usage_cached_tokens"], 10)
        self.assertEqual(events[0]["usage_output_tokens"], 7)
        self.assertEqual(events[0]["usage_reasoning_tokens"], 3)
        self.assertEqual(events[0]["usage_total_tokens"], 32)
        self.assertEqual(events[0]["usage_cache_hit_ratio"], 0.4)

    def test_preserves_client_prompt_cache_key(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file, shadow_mode=True) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "input": "ping",
                            "prompt_cache_key": "client-provided-key",
                        }
                    ).encode("utf-8"),
                    headers={"content-type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    response.read()

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        upstream_request = UpstreamHandler.requests[0]
        self.assertEqual(
            upstream_request["payload"]["prompt_cache_key"],
            "client-provided-key",
        )
        self.assertEqual(events[0]["prompt_cache_key"], "client-provided-key")
        self.assertEqual(events[0]["prompt_cache_key_source"], "client")

    def test_prompt_cache_key_includes_tool_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file, shadow_mode=True) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "input": "ping",
                            "tools": [
                                {"type": "function", "name": "shell"},
                                {"type": "image_generation"},
                            ],
                        }
                    ).encode("utf-8"),
                    headers={"content-type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    response.read()

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        upstream_payload = UpstreamHandler.requests[0]["payload"]
        self.assertTrue(
            upstream_payload["prompt_cache_key"].startswith(
                "codex:gpt-5.5:tools-"
            )
        )
        self.assertTrue(
            upstream_payload["prompt_cache_key"].endswith(":responses")
        )
        self.assertEqual(events[0]["prompt_cache_key_source"], "router_generated")
        self.assertTrue(events[0]["prompt_cache_tool_hash"].startswith("sha256:"))

    def test_rewritten_json_request_does_not_duplicate_content_type_header(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file, shadow_mode=True) as router_url:
                parsed = urllib.parse.urlparse(router_url)
                connection = http.client.HTTPConnection(
                    parsed.hostname, parsed.port, timeout=5
                )
                body = json.dumps(
                    {
                        "model": "gpt-5.5",
                        "input": "ping",
                    }
                ).encode("utf-8")
                connection.putrequest("POST", "/v1/responses")
                connection.putheader("content-type", "application/json")
                connection.putheader("content-length", str(len(body)))
                connection.endheaders(body)
                response = connection.getresponse()
                response.read()
                connection.close()

        upstream_headers = UpstreamHandler.requests[0]["headers"]
        content_type_headers = [
            key for key in upstream_headers if key.lower() == "content-type"
        ]
        self.assertEqual(content_type_headers, ["Content-Type"])

    def test_streaming_response_is_proxied(self):
        UpstreamHandler.stream = True
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            UpstreamHandler.stream = True
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "stream": True,
                            "input": "请总结 hello",
                        }
                    ).encode("utf-8"),
                    headers={"content-type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    content_type = response.headers.get("content-type")

        self.assertIn("text/event-stream", content_type)
        self.assertIn("response.output_text.delta", body)
        self.assertIn("[DONE]", body)

    def test_streaming_response_usage_is_logged(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            UpstreamHandler.stream = True
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "stream": True,
                            "input": "请总结 hello",
                        }
                    ).encode("utf-8"),
                    headers={"content-type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    response.read()

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(events[0]["usage_input_tokens"], 27)
        self.assertEqual(events[0]["usage_cached_tokens"], 9)
        self.assertEqual(events[0]["usage_output_tokens"], 10)
        self.assertEqual(events[0]["usage_reasoning_tokens"], 4)
        self.assertEqual(events[0]["usage_total_tokens"], 37)
        self.assertAlmostEqual(events[0]["usage_cache_hit_ratio"], 1 / 3)

    def test_non_text_v1_endpoint_is_passed_through_without_model_routing(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file, shadow_mode=True) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/images/generations",
                    data=json.dumps(
                        {
                            "model": "gpt-image-1",
                            "prompt": "a small router diagram",
                        }
                    ).encode("utf-8"),
                    headers={"content-type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    json.loads(response.read().decode("utf-8"))

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        upstream_request = UpstreamHandler.requests[0]
        self.assertEqual(upstream_request["path"], "/v1/images/generations")
        self.assertEqual(upstream_request["payload"]["model"], "gpt-image-1")
        self.assertEqual(events[0]["reason"], "non_text_endpoint_passthrough")
        self.assertEqual(events[0]["selected_model"], "gpt-image-1")
        self.assertIsNone(events[0]["shadow_selected_model"])

    def test_logs_upstream_error_excerpt_and_request_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir, RunningUpstream() as upstream:
            UpstreamHandler.status = 502
            UpstreamHandler.body = {
                "error": "upstream error: 400 message=Unsupported content type"
            }
            UpstreamHandler.response_headers = {
                "x-request-id": "sub2api-request-123",
            }
            log_file = Path(tmpdir) / "route.jsonl"
            with RunningRouter(upstream, log_file, shadow_mode=True) as router_url:
                request = urllib.request.Request(
                    f"{router_url}/responses",
                    data=json.dumps(
                        {
                            "model": "gpt-5.5",
                            "stream": True,
                            "input": [
                                {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "input_text",
                                            "text": "请分析这个报错",
                                        },
                                        {
                                            "type": "input_file",
                                            "file_id": "file_123",
                                        },
                                    ],
                                }
                            ],
                            "tools": [{"type": "namespace", "name": "shell"}],
                        }
                    ).encode("utf-8"),
                    headers={
                        "content-type": "application/json",
                        "x-client-request-id": "client-request-123",
                        "user-agent": "codex-test/1.0",
                    },
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=5)
                raised.exception.read()

            events = [
                json.loads(line)
                for line in log_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(events[0]["status"], 502)
        self.assertEqual(events[0]["client_ip"], "127.0.0.1")
        self.assertEqual(events[0]["request_content_type"], "application/json")
        self.assertEqual(events[0]["user_agent"], "codex-test/1.0")
        self.assertEqual(events[0]["client_request_id"], "client-request-123")
        self.assertEqual(events[0]["upstream_request_id"], "sub2api-request-123")
        self.assertEqual(events[0]["upstream_content_type"], "application/json")
        self.assertIn("Unsupported content type", events[0]["upstream_error_excerpt"])
        self.assertEqual(events[0]["input_item_types"], ["message"])
        self.assertEqual(events[0]["content_types"], ["input_text", "input_file"])


if __name__ == "__main__":
    unittest.main()
