# codex-model-router

OpenAI-compatible router proxy for Codex.

```text
Codex -> codex-model-router:8787 -> sub2api:8080
```

The router rewrites `model` conservatively before forwarding requests to sub2api. It supports:

- `POST /v1/responses`
- `POST /v1/chat/completions`
- passthrough for other `POST /v1/*` endpoints such as Images API
- streaming pass-through
- Authorization header pass-through
- prompt cache key fallback injection
- usage capture for streaming and non-streaming responses
- JSONL route logs

## Routing Policy

The first version is intentionally conservative:

- simple summary, rewrite, translation, classification, extraction, polishing, and formatting requests route to `CHEAP_MODEL`
- requests with `tools`, `previous_response_id`, or large input route to `DEFAULT_MODEL`
- unknown requests route to `DEFAULT_MODEL`

The router does not log full prompts by default. It logs route metadata only.

Non-text OpenAI-compatible endpoints are not model-routed. For example, `/v1/images/generations` is forwarded to upstream unchanged and logged with `reason=non_text_endpoint_passthrough`.

## Shadow Mode

Enable shadow mode before changing production routing behavior:

```bash
ROUTER_SHADOW_MODE=true
```

In shadow mode, the router forwards the original requested model unchanged, but logs what the last-user-intent strategy would choose:

```json
{
  "selected_model": "gpt-5.5",
  "reason": "shadow_mode_passthrough",
  "shadow_selected_model": "gpt-5.4-mini",
  "shadow_reason": "last_user_simple_text_task",
  "last_user_chars": 42
}
```

The shadow strategy inspects only the last user text and routes to `CHEAP_MODEL` when it is a small, standalone summary, rewrite, translation, classification, extraction, polishing, or formatting request. It falls back to `DEFAULT_MODEL` for tool use, stateful requests, context-dependent wording, implementation/debug/test/deploy/review requests, or uncertain cases.

Route logs include analysis fields without storing full prompts:

- `matched_keyword` and `blocker_keyword`
- `last_user_hash` and short `last_user_excerpt`
- `has_tools`, `tool_count`, and `tool_types`
- `previous_response_id`, `stream`, `status`, and `duration_ms`
- `input_chars`, `last_user_chars`, selected model, and shadow model
- `usage_input_tokens`, `usage_cached_tokens`, `usage_output_tokens`, `usage_reasoning_tokens`, `usage_total_tokens`, and `usage_cache_hit_ratio`
- `prompt_cache_key`, `prompt_cache_key_source`, and `prompt_cache_tool_hash`

## Prompt Cache Key

For `/v1/responses` and `/v1/chat/completions`, the router preserves a client-provided `prompt_cache_key`. If the client does not send one, it injects a low-cardinality fallback key:

```text
codex:<model>:<tool-bucket>:<endpoint>
```

Examples:

```text
codex:gpt-5.5:no-tools:responses
codex:gpt-5.5:tools-94f0105324b2:responses
```

Disable fallback injection with:

```bash
PROMPT_CACHE_KEY_ENABLED=false
```

The router does not set `prompt_cache_retention`.

## Run

```bash
ROUTER_PORT=8787 \
UPSTREAM_BASE_URL=http://127.0.0.1:8080/v1 \
DEFAULT_MODEL=gpt-5.5 \
CHEAP_MODEL=gpt-5.4-mini \
ROUTER_SHADOW_MODE=true \
python3 router.py
```

## Deploy With systemd

```bash
useradd --system --home /opt/codex-model-router --shell /usr/sbin/nologin codex-router
mkdir -p /opt/codex-model-router /var/log/codex-router
cp router.py /opt/codex-model-router/router.py
cp deploy/codex-model-router.service /etc/systemd/system/codex-model-router.service
chown -R codex-router:codex-router /opt/codex-model-router /var/log/codex-router
systemctl daemon-reload
systemctl enable --now codex-model-router.service
```

Check status and logs:

```bash
systemctl status codex-model-router.service
journalctl -u codex-model-router.service -f
tail -f /var/log/codex-router/route.jsonl
```

## Codex Config

```toml
model_provider = "router"
model = "gpt-5.5"
review_model = "gpt-5.5"

[model_providers.router]
name = "router"
base_url = "http://<router-host>:8787/v1"
wire_api = "responses"
requires_openai_auth = true
```

## Test

```bash
python3 -m unittest discover -s tests -v
```
