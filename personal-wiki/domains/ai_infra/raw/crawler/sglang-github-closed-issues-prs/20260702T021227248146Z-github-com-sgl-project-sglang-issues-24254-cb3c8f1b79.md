---
source_id: sglang-github-closed-issues-prs
title: '[Bug] bench_serving sglang-oai reports wrong output_len (stuck at requested
  max_tokens), causes incorrect TPOT / throughput / retokenized metrics'
canonical_url: https://github.com/sgl-project/sglang/issues/24254
captured_at: '2026-07-02T02:12:27.248146+00:00'
content_hash: cb3c8f1b796625e46bffd58d2fe4bf58f0676bd36da240238ef569daf16932c5
---
# [Bug] bench_serving sglang-oai reports wrong output_len (stuck at requested max_tokens), causes incorrect TPOT / throughput / retokenized metrics

URL: https://github.com/sgl-project/sglang/issues/24254
State: closed
Labels: inactive
Closed at: 2026-07-02T00:48:12Z
Merged at: 

## Describe the bug

`sglang.bench_serving --backend sglang-oai` silently reports incorrect token counts.
Every metric derived from `output_len` — TPOT, output token throughput, retokenized
length — is wrong whenever generation stops before `max_tokens` (EOS, length stop,
abort).

The sibling `--backend sglang-oai-chat` path is **correct** — only the completions
path is affected.

## Root cause

In `async_request_openai_completions` (`python/sglang/bench_serving.py` L297-319
on `main` @ `bfccc8e`), the `output_len` update from the trailing usage chunk
is nested inside `if data["choices"][0]["text"]:`:

```python
if data["choices"][0]["text"]:
    ...
    most_recent_timestamp = timestamp
    generated_text += data["choices"][0]["text"]
    output_len = (data.get("usage") or {}).get(       # ← this line
        "completion_tokens", output_len               # ← and this
    )                                                 # ← and this
                                                      #   are indented into
                                                      #   the `if text:` branch
```

sglang streams the final `completion_tokens` in a chunk whose `text` is `""`,
so the `if` evaluates False and the usage update is skipped entirely.
`output_len` stays at its initial fallback `request_func_input.output_len`
(i.e. the requested `max_tokens`).

The sibling chat path (`async_request_openai_chat_completions`, L463-469)
puts the usage update **outside** the content guard — which is why chat is
correct and completions is not. The pattern was cleaned up in #23954
(reasoning chunk fix) for chat; the same cleanup is needed for completions.

Additionally, the same block crashes with `IndexError: list index out of range`
when servers emit usage-only chunks with `choices=[]` (vLLM
`include_usage=true`, see stale-closed #5451). The fix applies the same
`data.get("choices") or []` guard that the chat path uses.

## Reproduction

Minimal SSE server that mimics sglang's stream shape:

```python
# serve.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for c in [
            {"choices":[{"index":0,"text":"Hel"}]},
            {"choices":[{"index":0,"text":"lo"}]},
            {"choices":[{"index":0,"text":"!"}]},
            {"choices":[{"index":0,"text":""}],"usage":{"completion_tokens":3}},
        ]:
            self.wfile.write(b"data: " + json.dumps(c).encode() + b"\n\n")
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")

HTTPServer(("127.0.0.1", 19999), H).serve_forever()
```

```bash
python serve.py &
python -m sglang.bench_serving \
  --backend sglang-oai \
  --host 127.0.0.1 --port 19999 \
  --dataset-name random --random-input 1 --random-output 64 \
  --num-prompts 1 --max-concurrency 1 \
  --tokenizer some-tokenizer
```

Expected: `Total generated tokens: 3`
Actual:   `Total generated tokens: 64` (the requested `max_tokens`).

## Environment

- sglang `main` @ `bfccc8e`
- Also affects 0.5.10 and earlier 0.5.x releases (same code).
- Backend: `sglang-oai` (the `--backend sglang-oai-chat` path is not affected).

## Related

- PR #23954 (merged 2026-04-30) fixed the symmetric bug on the chat path.
- Issue #5451 (stale-closed 2025-06-16) reported the `IndexError` variant on
  vLLM with `include_usage=true`. Same function, different trigger.
