#!/usr/bin/env python3
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import http.client
import json
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


HOST = os.getenv("ROUTER_HOST", "0.0.0.0")
PORT = int(os.getenv("ROUTER_PORT", "8787"))
UPSTREAM_BASE_URL = os.getenv("UPSTREAM_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5.5")
CHEAP_MODEL = os.getenv("CHEAP_MODEL", "gpt-5.4-mini")
MAX_CHEAP_INPUT_CHARS = int(os.getenv("MAX_CHEAP_INPUT_CHARS", "8000"))
MAX_SHADOW_LAST_USER_CHARS = int(os.getenv("MAX_SHADOW_LAST_USER_CHARS", "4000"))
MAX_LAST_USER_EXCERPT_CHARS = int(os.getenv("MAX_LAST_USER_EXCERPT_CHARS", "160"))
MAX_UPSTREAM_ERROR_EXCERPT_CHARS = int(
    os.getenv("MAX_UPSTREAM_ERROR_EXCERPT_CHARS", "300")
)
ROUTER_SHADOW_MODE = os.getenv("ROUTER_SHADOW_MODE", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LOG_FILE = Path(os.getenv("ROUTER_LOG_FILE", "/var/log/codex-router/route.jsonl"))
PROMPT_CACHE_KEY_ENABLED = os.getenv("PROMPT_CACHE_KEY_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

ROUTER_MANAGED_REQUEST_HEADERS = {
    "content-length",
    "content-type",
}

CHEAP_KEYWORDS = [
    "summarize",
    "summary",
    "rewrite",
    "translate",
    "classify",
    "extract",
    "polish",
    "format",
    "tone",
    "总结",
    "摘要",
    "改写",
    "重写",
    "翻译",
    "分类",
    "抽取",
    "提取",
    "润色",
    "整理格式",
    "调整语气",
]

CONTEXT_DEPENDENT_KEYWORDS = [
    "continue",
    "as above",
    "above",
    "previous",
    "last time",
    "刚才",
    "继续",
    "上面",
    "之前",
    "上一",
    "按你的方案",
    "按这个方案",
    "这个问题",
    "这个项目",
]

HARD_BLOCKER_KEYWORDS = [
    "implement",
    "fix",
    "debug",
    "test",
    "build",
    "deploy",
    "review",
    "refactor",
    "run command",
    "read file",
    "edit file",
    "修改",
    "实现",
    "修复",
    "调试",
    "测试",
    "构建",
    "部署",
    "代码审查",
    "审查",
    "重构",
    "读取文件",
    "改文件",
    "执行命令",
]


@dataclasses.dataclass(frozen=True)
class ModelDecision:
    model: str
    reason: str


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def request_text(payload: dict) -> str:
    parts = []
    for key in ("instructions", "input", "messages"):
        if key in payload:
            parts.append(json_text(payload[key]))
    return "\n".join(parts)


def request_text_size(payload: dict) -> int:
    return len(request_text(payload))


def has_tools(payload: dict) -> bool:
    tools = payload.get("tools")
    return isinstance(tools, list) and len(tools) > 0


def content_block_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
        nested = value.get("content")
        if nested is not None:
            return content_block_text(nested)
        return ""
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := content_block_text(item)))
    return ""


def message_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return ""
    return content_block_text(message.get("content"))


def extract_last_user_text(payload: dict) -> str:
    candidates = []
    for key in ("input", "messages"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("role") == "user":
                    text = message_text(item)
                    if text:
                        candidates.append(text)
        elif isinstance(value, str) and key == "input":
            candidates.append(value)
    return candidates[-1] if candidates else ""


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def first_keyword(text: str, keywords: list[str]) -> str | None:
    lowered = text.lower()
    for keyword in keywords:
        if keyword in lowered:
            return keyword
    return None


def tools(payload: dict) -> list[Any]:
    value = payload.get("tools")
    return value if isinstance(value, list) else []


def tool_types(payload: dict) -> list[str]:
    result = []
    for tool in tools(payload):
        if isinstance(tool, dict):
            tool_type = tool.get("type")
            if isinstance(tool_type, str):
                result.append(tool_type)
            else:
                result.append("unknown")
        else:
            result.append(type(tool).__name__)
    return result


def input_item_types(payload: dict) -> list[str]:
    value = payload.get("input")
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, dict):
            item_type = item.get("type")
            if isinstance(item_type, str):
                result.append(item_type)
            elif "role" in item:
                result.append("message")
            else:
                result.append("object")
        else:
            result.append(type(item).__name__)
    return result


def content_types_from_value(value: Any) -> list[str]:
    if isinstance(value, dict):
        result = []
        content_type = value.get("type")
        if isinstance(content_type, str):
            result.append(content_type)
        if "content" in value:
            result.extend(content_types_from_value(value.get("content")))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(content_types_from_value(item))
        return result
    return []


def content_types(payload: dict) -> list[str]:
    result = []
    for key in ("input", "messages"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "content" in item:
                    result.extend(content_types_from_value(item.get("content")))
                else:
                    result.extend(content_types_from_value(item))
        elif value is not None:
            result.extend(content_types_from_value(value))
    return result


def text_hash(text: str) -> str | None:
    if not text:
        return None
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def short_hash(value: Any) -> str:
    digest = hashlib.sha256(json_text(value).encode("utf-8")).hexdigest()
    return digest[:16]


def route_endpoint_name(path: str) -> str:
    if path == "/v1/responses":
        return "responses"
    if path == "/v1/chat/completions":
        return "chat-completions"
    return path.removeprefix("/v1/").replace("/", "-") or "unknown"


def prompt_cache_tool_hash(payload: dict) -> str | None:
    request_tools = tools(payload)
    if not request_tools:
        return None
    digest = hashlib.sha256(json_text(request_tools).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_prompt_cache_key(payload: dict, selected_model: str, path: str) -> str:
    tool_hash = prompt_cache_tool_hash(payload)
    tool_bucket = f"tools-{tool_hash.split(':', 1)[1][:12]}" if tool_hash else "no-tools"
    return f"codex:{selected_model}:{tool_bucket}:{route_endpoint_name(path)}"


def apply_prompt_cache_key(
    payload: dict, selected_model: str, path: str
) -> tuple[str | None, str, str | None]:
    existing = payload.get("prompt_cache_key")
    tool_hash = prompt_cache_tool_hash(payload)
    if isinstance(existing, str) and existing:
        return existing, "client", tool_hash
    if not PROMPT_CACHE_KEY_ENABLED:
        return None, "disabled", tool_hash
    cache_key = build_prompt_cache_key(payload, selected_model, path)
    payload["prompt_cache_key"] = cache_key
    return cache_key, "router_generated", tool_hash


def text_excerpt(text: str) -> str | None:
    if not text:
        return None
    return text[:MAX_LAST_USER_EXCERPT_CHARS]


def request_id_from_headers(headers: dict[str, str]) -> str | None:
    normalized = {key.lower(): value for key, value in headers.items()}
    for key in (
        "x-client-request-id",
        "x-request-id",
        "openai-request-id",
        "request-id",
    ):
        value = normalized.get(key)
        if value:
            return value
    return None


def response_header(response: http.client.HTTPResponse, name: str) -> str | None:
    value = response.getheader(name)
    return value if value else None


def response_request_id(response: http.client.HTTPResponse) -> str | None:
    for key in ("x-request-id", "openai-request-id", "request-id"):
        value = response_header(response, key)
        if value:
            return value
    return None


def error_excerpt_from_bytes(body: bytes) -> str | None:
    if not body:
        return None
    text = body[:MAX_UPSTREAM_ERROR_EXCERPT_CHARS].decode("utf-8", errors="replace")
    return text.replace("\r", "\\r").replace("\n", "\\n")


def usage_value(usage: dict[str, Any] | None, *path: str) -> int | None:
    if not isinstance(usage, dict):
        return None
    value: Any = usage
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, int) else None


def usage_log_fields(usage: dict[str, Any] | None) -> dict[str, Any]:
    input_tokens = usage_value(usage, "input_tokens")
    cached_tokens = usage_value(usage, "input_tokens_details", "cached_tokens")
    output_tokens = usage_value(usage, "output_tokens")
    reasoning_tokens = usage_value(
        usage, "output_tokens_details", "reasoning_tokens"
    )
    total_tokens = usage_value(usage, "total_tokens")
    cache_hit_ratio = None
    if input_tokens and cached_tokens is not None:
        cache_hit_ratio = cached_tokens / input_tokens
    return {
        "usage_input_tokens": input_tokens,
        "usage_cached_tokens": cached_tokens,
        "usage_output_tokens": output_tokens,
        "usage_reasoning_tokens": reasoning_tokens,
        "usage_total_tokens": total_tokens,
        "usage_cache_hit_ratio": cache_hit_ratio,
    }


def extract_usage_from_response_json(body: bytes) -> dict[str, Any] | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        usage = payload.get("usage")
        if isinstance(usage, dict):
            return usage
    return None


class SseUsageCapture:
    def __init__(self) -> None:
        self._buffer = ""
        self.usage: dict[str, Any] | None = None

    def feed(self, chunk: bytes) -> None:
        if self.usage is not None:
            return
        self._buffer += chunk.decode("utf-8", errors="replace")
        while True:
            separator = self._next_separator()
            if separator is None:
                self._trim_buffer()
                return
            event_text = self._buffer[: separator[0]]
            self._buffer = self._buffer[separator[1] :]
            self._capture_event(event_text)
            if self.usage is not None:
                return

    def _next_separator(self) -> tuple[int, int] | None:
        options = [
            (index, index + len(separator))
            for separator in ("\r\n\r\n", "\n\n")
            if (index := self._buffer.find(separator)) >= 0
        ]
        return min(options) if options else None

    def _trim_buffer(self) -> None:
        if len(self._buffer) > 1024 * 1024:
            self._buffer = self._buffer[-4096:]

    def _capture_event(self, event_text: str) -> None:
        data_lines = []
        for line in event_text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            return
        data_text = "\n".join(data_lines)
        if data_text == "[DONE]":
            return
        try:
            event_payload = json.loads(data_text)
        except json.JSONDecodeError:
            return
        if not isinstance(event_payload, dict):
            return
        response = event_payload.get("response")
        if isinstance(response, dict) and isinstance(response.get("usage"), dict):
            self.usage = response["usage"]
            return
        usage = event_payload.get("usage")
        if isinstance(usage, dict):
            self.usage = usage


def choose_model(payload: dict) -> ModelDecision:
    if has_tools(payload):
        return ModelDecision(DEFAULT_MODEL, "has_tools")
    if payload.get("previous_response_id"):
        return ModelDecision(DEFAULT_MODEL, "stateful_conversation")
    if request_text_size(payload) > MAX_CHEAP_INPUT_CHARS:
        return ModelDecision(DEFAULT_MODEL, "large_input")

    text = request_text(payload).lower()
    if any(keyword in text for keyword in CHEAP_KEYWORDS):
        return ModelDecision(CHEAP_MODEL, "simple_text_task")

    return ModelDecision(DEFAULT_MODEL, "default_strong")


def choose_shadow_model(payload: dict) -> ModelDecision:
    if has_tools(payload):
        return ModelDecision(DEFAULT_MODEL, "has_tools")
    if payload.get("previous_response_id"):
        return ModelDecision(DEFAULT_MODEL, "stateful_conversation")

    last_user_text = extract_last_user_text(payload).strip()
    if not last_user_text:
        return ModelDecision(DEFAULT_MODEL, "no_last_user_text")
    if len(last_user_text) > MAX_SHADOW_LAST_USER_CHARS:
        return ModelDecision(DEFAULT_MODEL, "last_user_too_large")
    if contains_any(last_user_text, CONTEXT_DEPENDENT_KEYWORDS):
        return ModelDecision(DEFAULT_MODEL, "last_user_context_dependent")
    if contains_any(last_user_text, HARD_BLOCKER_KEYWORDS):
        return ModelDecision(DEFAULT_MODEL, "last_user_hard_blocker")
    if contains_any(last_user_text, CHEAP_KEYWORDS):
        return ModelDecision(CHEAP_MODEL, "last_user_simple_text_task")
    return ModelDecision(DEFAULT_MODEL, "last_user_default_strong")


def upstream_url(path: str) -> urllib.parse.ParseResult:
    upstream_base = UPSTREAM_BASE_URL.rstrip("/")
    clean_path = path.removeprefix("/v1")
    return urllib.parse.urlparse(f"{upstream_base}{clean_path}")


def filtered_request_headers(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    headers = {}
    for key, value in handler.headers.items():
        lowered = key.lower()
        if (
            lowered not in HOP_BY_HOP_HEADERS
            and lowered not in ROUTER_MANAGED_REQUEST_HEADERS
        ):
            headers[key] = value
    return headers


def filtered_response_headers(response: http.client.HTTPResponse) -> list[tuple[str, str]]:
    return [
        (key, value)
        for key, value in response.getheaders()
        if key.lower() not in HOP_BY_HOP_HEADERS
    ]


def write_log(event: dict) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    except OSError as exc:
        print(f"failed to write route log: {exc}", file=sys.stderr)


def proxy_request(
    *,
    path: str,
    method: str,
    headers: dict[str, str],
    body: bytes,
) -> http.client.HTTPResponse:
    parsed = upstream_url(path)
    connection_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    port = parsed.port
    host = parsed.hostname
    if host is None:
        raise ValueError(f"invalid upstream URL: {UPSTREAM_BASE_URL}")
    target = parsed.path or "/"
    if parsed.query:
        target += f"?{parsed.query}"
    connection = connection_cls(host, port, timeout=600)
    connection.request(method, target, body=body, headers=headers)
    return connection.getresponse()


def send_upstream_response(
    handler: BaseHTTPRequestHandler, upstream_response: http.client.HTTPResponse
) -> None:
    handler.send_response(upstream_response.status, upstream_response.reason)
    for key, value in filtered_response_headers(upstream_response):
        handler.send_header(key, value)
    handler.end_headers()
    while True:
        chunk = upstream_response.read(64 * 1024)
        if not chunk:
            break
        handler.wfile.write(chunk)
        handler.wfile.flush()


def send_upstream_response_and_capture(
    handler: BaseHTTPRequestHandler, upstream_response: http.client.HTTPResponse
) -> tuple[str | None, dict[str, Any] | None]:
    handler.send_response(upstream_response.status, upstream_response.reason)
    for key, value in filtered_response_headers(upstream_response):
        handler.send_header(key, value)
    handler.end_headers()
    captured = bytearray()
    body = bytearray()
    content_type = response_header(upstream_response, "content-type") or ""
    stream_capture = (
        SseUsageCapture()
        if "text/event-stream" in content_type.lower()
        else None
    )
    while True:
        chunk = upstream_response.read(64 * 1024)
        if not chunk:
            break
        if upstream_response.status < 400:
            if stream_capture is not None:
                stream_capture.feed(chunk)
            else:
                body.extend(chunk)
        if upstream_response.status >= 400 and len(captured) < MAX_UPSTREAM_ERROR_EXCERPT_CHARS:
            remaining = MAX_UPSTREAM_ERROR_EXCERPT_CHARS - len(captured)
            captured.extend(chunk[:remaining])
        handler.wfile.write(chunk)
        handler.wfile.flush()
    usage = stream_capture.usage if stream_capture else extract_usage_from_response_json(bytes(body))
    return error_excerpt_from_bytes(bytes(captured)), usage


class RouterHandler(BaseHTTPRequestHandler):
    server_version = "CodexModelRouter/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            body = b'{"ok":true}\n'
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404, "not found")

    def do_POST(self) -> None:
        if not self.path.startswith("/v1/"):
            self.send_error(404, "not found")
            return

        started = time.time()
        length = int(self.headers.get("content-length", "0"))
        raw_body = self.rfile.read(length)
        status = 502
        original_model = None
        selected_model = None
        reason = "unhandled"
        shadow_selected_model = None
        shadow_reason = None
        last_user_text = ""
        input_chars = None
        stream = False
        client_request_id = None
        client_ip = None
        request_content_type = None
        user_agent = None
        upstream_request_id = None
        upstream_content_type = None
        upstream_error_excerpt = None
        response_usage = None
        prompt_cache_key = None
        prompt_cache_key_source = None
        prompt_cache_tool_hash_value = None

        try:
            request_headers_raw = dict(self.headers)
            client_request_id = request_id_from_headers(request_headers_raw)
            client_ip = self.client_address[0] if self.client_address else None
            request_content_type = self.headers.get("content-type")
            user_agent = self.headers.get("user-agent")
            payload = json.loads(raw_body)
            if not isinstance(payload, dict):
                raise ValueError("request JSON must be an object")
            original_model = payload.get("model")
            input_chars = request_text_size(payload)
            stream = bool(payload.get("stream"))

            if self.path not in {"/v1/responses", "/v1/chat/completions"}:
                selected_model = str(original_model) if original_model is not None else None
                reason = "non_text_endpoint_passthrough"
                request_headers = filtered_request_headers(self)
                request_headers["Content-Length"] = str(len(raw_body))
                upstream_response = proxy_request(
                    path=self.path,
                    method="POST",
                    headers=request_headers,
                    body=raw_body,
                )
                status = upstream_response.status
                upstream_request_id = response_request_id(upstream_response)
                upstream_content_type = response_header(upstream_response, "content-type")
                upstream_error_excerpt, response_usage = send_upstream_response_and_capture(
                    self, upstream_response
                )
                return

            shadow_decision = choose_shadow_model(payload)
            shadow_selected_model = shadow_decision.model
            shadow_reason = shadow_decision.reason
            last_user_text = extract_last_user_text(payload).strip()
            decision = (
                ModelDecision(str(original_model or DEFAULT_MODEL), "shadow_mode_passthrough")
                if ROUTER_SHADOW_MODE
                else choose_model(payload)
            )
            selected_model = decision.model
            reason = decision.reason
            payload["model"] = selected_model
            (
                prompt_cache_key,
                prompt_cache_key_source,
                prompt_cache_tool_hash_value,
            ) = apply_prompt_cache_key(payload, selected_model, self.path)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request_headers = filtered_request_headers(self)
            request_headers["Content-Type"] = "application/json"
            request_headers["Content-Length"] = str(len(body))

            upstream_response = proxy_request(
                path=self.path,
                method="POST",
                headers=request_headers,
                body=body,
            )
            status = upstream_response.status
            upstream_request_id = response_request_id(upstream_response)
            upstream_content_type = response_header(upstream_response, "content-type")
            upstream_error_excerpt, response_usage = send_upstream_response_and_capture(
                self, upstream_response
            )
        except Exception as exc:
            reason = f"router_error:{type(exc).__name__}"
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        finally:
            event = {
                    "ts": now_iso(),
                    "path": self.path,
                    "original_model": original_model,
                    "selected_model": selected_model,
                    "reason": reason,
                    "shadow_selected_model": shadow_selected_model,
                    "shadow_reason": shadow_reason,
                    "last_user_chars": len(last_user_text),
                    "last_user_hash": text_hash(last_user_text),
                    "last_user_excerpt": text_excerpt(last_user_text),
                    "matched_keyword": first_keyword(last_user_text, CHEAP_KEYWORDS),
                    "blocker_keyword": first_keyword(last_user_text, HARD_BLOCKER_KEYWORDS),
                    "has_tools": has_tools(payload) if isinstance(payload, dict) else False,
                    "tool_count": len(tools(payload)) if isinstance(payload, dict) else 0,
                    "tool_types": tool_types(payload) if isinstance(payload, dict) else [],
                    "previous_response_id": bool(payload.get("previous_response_id"))
                    if isinstance(payload, dict)
                    else False,
                    "stream": stream,
                    "input_chars": input_chars,
                    "status": status,
                    "duration_ms": int((time.time() - started) * 1000),
                    "client_ip": client_ip,
                    "request_content_type": request_content_type,
                    "user_agent": user_agent,
                    "client_request_id": client_request_id,
                    "upstream_request_id": upstream_request_id,
                    "upstream_content_type": upstream_content_type,
                    "upstream_error_excerpt": upstream_error_excerpt,
                    "prompt_cache_key": prompt_cache_key,
                    "prompt_cache_key_source": prompt_cache_key_source,
                    "prompt_cache_tool_hash": prompt_cache_tool_hash_value,
                    "input_item_types": input_item_types(payload)
                    if isinstance(payload, dict)
                    else [],
                    "content_types": content_types(payload)
                    if isinstance(payload, dict)
                    else [],
                }
            event.update(usage_log_fields(response_usage))
            write_log(event)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", file=sys.stderr)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), RouterHandler)
    print(
        f"codex-model-router listening on {HOST}:{PORT}, upstream={UPSTREAM_BASE_URL}",
        file=sys.stderr,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
