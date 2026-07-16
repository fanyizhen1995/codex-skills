---
source_id: sglang-github-closed-issues-prs
title: '[Bug] MiniMax-M2 streaming tool_calls: malformed response with name=null and
  duplicated arguments'
canonical_url: https://github.com/sgl-project/sglang/issues/23071
captured_at: '2026-07-11T23:37:37.763641+00:00'
content_hash: bed92d233fb66103fdb780bba6a8b61570e5d0d63ea7ff7566d27ec0a5e5b47a
---
# [Bug] MiniMax-M2 streaming tool_calls: malformed response with name=null and duplicated arguments

URL: https://github.com/sgl-project/sglang/issues/23071
State: closed
Labels: inactive
Closed at: 2026-07-11T00:33:07Z
Merged at: 

# [Bug] MiniMax-M2 streaming tool_calls: malformed response with `name: null` and duplicated `arguments`

## Summary

With `--tool-call-parser minimax_m2` + `stream: true`, a single tool call is sometimes emitted as two `tool_calls` entries:
- entry 1: valid `name`, empty `arguments`
- entry 2: `name: null`, `id: null`, `arguments` contains two concatenated non-terminated JSON objects

Result: clients (ai-sdk, OpenAI SDK) fail to parse the response.

## Observed (sanitized)

```json
"tool_calls": [
  { "id": "call_xxx", "function": { "name": "bash", "arguments": "" } },
  { "id": null, "function": {
      "name": null,
      "arguments": "{\"command\": \"...head -100\"{\"command\": \"...head -100\", \"description\": \"Run tests\"}"
  }}
]
```

Intended: one entry `bash({"command": "...", "description": "Run tests"})`.

Non-streaming for the same input works fine.

## Environment

- SGLang v0.5.10.post1 (image `lmsysorg/sglang@sha256:dd1814f8…`)
- Model: MiniMax-M2.5 FP8
- Args: `--tp 8 --ep 8 --tool-call-parser minimax_m2 --reasoning-parser minimax_m2`
- GPU: 8× RTX 6000 Ada
- Client: opencode (ai-sdk), `stream: true`, `tool_choice: auto`, long multi-turn conversation

## Suspected area

`python/sglang/srt/function_call/minimax_m2.py`:
- `parse_streaming_increment` emits `name` first with empty params, then param fragments later.
- `_parse_and_stream_parameters` opens the JSON with `{` on first batch (L400–L416) and appends `}` later via brace counting (L329–L342).

The duplicated-start shape (`{"command":"..."{"command":...`) looks like the first-batch branch ran twice on the same invoke. The second entry with `name: null` matches what would happen if subsequent `arguments`-only deltas were placed into a new `tool_calls` slot instead of concatenated onto entry 0.

For reference, the vLLM parser (`vllm/tool_parsers/minimax_m2_tool_parser.py` L394–L451) buffers until `<invoke>...</invoke>` is complete, then emits one delta with full `name` + full `arguments`. No fragmentation. Switching the same traffic to vLLM removes the symptom.

## Repro

Not isolated to a minimal case yet. Happens under streaming, long multi-turn history, tool with multiple string params. Happy to capture raw SSE chunks if useful.

## Related (not duplicates)

- #16057 — union-type parsing in minimax_m2 (different symptom)
- #11888 — GLM-4.6 streaming args (different model)
