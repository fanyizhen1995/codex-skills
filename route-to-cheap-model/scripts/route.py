#!/usr/bin/env python3
"""Route a small text-only task to an OpenAI-compatible chat API."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_MAX_INPUT_CHARS = 12_000
DEFAULT_MAX_TOKENS = 512
DEFAULT_TIMEOUT = 60
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_LOG_FILE = (
    Path.home() / ".agents" / "skills" / "route-to-cheap-model" / "logs" / "route.jsonl"
)

SYSTEM_PROMPT = """You are a low-cost assistant handling a bounded text-only subtask.
Return only the requested answer. Do not claim to have inspected files, run tools,
used the internet, or verified facts beyond the text provided."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a bounded task to an OpenAI-compatible chat completions API."
    )
    parser.add_argument("--task", required=True, help="Task instruction for the model.")
    parser.add_argument("--input", help="Task input. If omitted, stdin is used.")
    parser.add_argument(
        "--model",
        default=None,
        help=f"Model override. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--system",
        default=SYSTEM_PROMPT,
        help="System prompt to send to the cheap model.",
    )
    parser.add_argument(
        "--max-input-chars",
        type=int,
        default=int(os.getenv("CHEAP_MODEL_MAX_INPUT_CHARS", DEFAULT_MAX_INPUT_CHARS)),
        help="Reject input above this many characters unless --truncate is set.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate oversized input instead of failing.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("CHEAP_MODEL_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        help="Completion token cap.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.getenv("CHEAP_MODEL_TEMPERATURE", "0")),
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("CHEAP_MODEL_TIMEOUT", DEFAULT_TIMEOUT)),
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a JSON object with content, model, and usage.",
    )
    parser.add_argument(
        "--log-file",
        default=os.getenv("CHEAP_MODEL_LOG_FILE", str(DEFAULT_LOG_FILE)),
        help="JSONL audit log path. Defaults to the installed skill logs directory.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable JSONL audit logging for this invocation.",
    )
    return parser.parse_args()


def codex_home() -> Path:
    return Path(os.getenv("CODEX_HOME", Path.home() / ".codex")).expanduser()


def load_codex_config() -> dict:
    path = codex_home() / "config.toml"
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"failed to read Codex config {path}: {exc}") from exc


def load_codex_api_key() -> str | None:
    path = codex_home() / "auth.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("OPENAI_API_KEY")
    return value if isinstance(value, str) and value else None


def resolve_codex_provider(config: dict) -> dict:
    provider_name = config.get("model_provider")
    providers = config.get("model_providers")
    if not isinstance(provider_name, str) or not isinstance(providers, dict):
        return {}
    provider = providers.get(provider_name)
    return provider if isinstance(provider, dict) else {}


def resolve_config(args: argparse.Namespace) -> dict:
    codex_config = load_codex_config()
    provider = resolve_codex_provider(codex_config)

    base_url = os.getenv("CHEAP_MODEL_BASE_URL") or provider.get("base_url")
    model = (
        args.model
        or os.getenv("CHEAP_MODEL_NAME")
        or os.getenv("CHEAP_MODEL_MODEL")
        or DEFAULT_MODEL
    )
    api_key = os.getenv("CHEAP_MODEL_API_KEY") or load_codex_api_key()
    wire_api = os.getenv("CHEAP_MODEL_WIRE_API") or provider.get("wire_api") or "chat"

    missing = []
    if not base_url:
        missing.append("CHEAP_MODEL_BASE_URL or Codex model provider base_url")
    if missing:
        raise ConfigError("missing required config: " + ", ".join(missing))

    return {
        "base_url": str(base_url),
        "model": str(model),
        "api_key": api_key,
        "wire_api": str(wire_api),
    }


class ConfigError(Exception):
    pass


class ApiError(Exception):
    pass


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def completions_url(base_url: str) -> str:
    base = normalize_base_url(base_url)
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def responses_url(base_url: str) -> str:
    base = normalize_base_url(base_url)
    if base.endswith("/responses"):
        return base
    return f"{base}/responses"


def read_input(args: argparse.Namespace) -> str:
    text = args.input if args.input is not None else sys.stdin.read()
    if len(text) <= args.max_input_chars:
        return text
    if not args.truncate:
        raise ConfigError(
            f"input too large: {len(text)} chars exceeds --max-input-chars={args.max_input_chars}; "
            "summarize locally first or pass --truncate"
        )
    keep = max(0, args.max_input_chars - len("\n\n[truncated]"))
    return text[:keep] + "\n\n[truncated]"


def build_payload(args: argparse.Namespace, model: str, input_text: str) -> dict:
    user_content = f"Task:\n{args.task}\n\nInput:\n{input_text}"
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }


def build_responses_payload(
    args: argparse.Namespace, model: str, input_text: str
) -> dict:
    return {
        "model": model,
        "instructions": args.system,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Task:\n{args.task}\n\nInput:\n{input_text}",
                    }
                ],
            }
        ],
        "max_output_tokens": args.max_tokens,
        "temperature": args.temperature,
    }


def call_api(url: str, api_key: str | None, payload: dict, timeout: float) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(extract_error_message(body) or f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(str(exc.reason)) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ApiError("API returned invalid JSON") from exc


def extract_error_message(body: str) -> str | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body[:500] if body else None
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    if isinstance(error, str):
        return error
    return None


def extract_content(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if not isinstance(first, dict):
            raise ApiError("API response choice has unexpected shape")
        message = first.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
        text = first.get("text")
        if isinstance(text, str):
            return text

    output = payload.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        if parts:
            return "".join(parts)

    raise ApiError("API response did not include message content")


def now_utc_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def write_audit_log(args: argparse.Namespace, event: dict) -> None:
    if args.no_log:
        return
    log_file = Path(args.log_file).expanduser()
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    except OSError as exc:
        print(f"route-to-cheap-model: failed to write audit log: {exc}", file=sys.stderr)


def build_audit_event(
    *,
    args: argparse.Namespace,
    config: dict | None,
    input_text: str | None,
    content: str | None,
    response: dict | None,
    success: bool,
    error: str | None = None,
) -> dict:
    event = {
        "ts": now_utc_iso(),
        "task": args.task,
        "model": config.get("model") if config else args.model,
        "wire_api": config.get("wire_api") if config else None,
        "input_chars": len(input_text) if input_text is not None else None,
        "output_chars": len(content) if content is not None else None,
        "success": success,
    }
    if response is not None:
        event["usage"] = response.get("usage")
    if error:
        event["error"] = error
    return event


def main() -> int:
    args = parse_args()
    config = None
    input_text = None
    response = None
    content = None
    try:
        config = resolve_config(args)
        base_url = config["base_url"]
        model = config["model"]
        api_key = config["api_key"]
        input_text = read_input(args)
        if config["wire_api"] == "responses":
            payload = build_responses_payload(args, model, input_text)
            url = responses_url(base_url)
        else:
            payload = build_payload(args, model, input_text)
            url = completions_url(base_url)
        response = call_api(url, api_key, payload, args.timeout)
        content = extract_content(response)
    except (ConfigError, ApiError) as exc:
        write_audit_log(
            args,
            build_audit_event(
                args=args,
                config=config,
                input_text=input_text,
                content=content,
                response=response,
                success=False,
                error=str(exc),
            ),
        )
        print(f"route-to-cheap-model: {exc}", file=sys.stderr)
        return 1

    write_audit_log(
        args,
        build_audit_event(
            args=args,
            config=config,
            input_text=input_text,
            content=content,
            response=response,
            success=True,
        ),
    )

    if args.json:
        print(
            json.dumps(
                {
                    "model": model,
                    "content": content,
                    "usage": response.get("usage"),
                },
                ensure_ascii=False,
            )
        )
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
