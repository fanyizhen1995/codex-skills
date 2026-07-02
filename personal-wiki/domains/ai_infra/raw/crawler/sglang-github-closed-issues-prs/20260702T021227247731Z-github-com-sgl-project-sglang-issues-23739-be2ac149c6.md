---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Qwen3.5-35B-A3B-GPTQ-Int4 on RTX 5090 fails on first generation request
  with Triton CompilationError on latest main'
canonical_url: https://github.com/sgl-project/sglang/issues/23739
captured_at: '2026-07-02T02:12:27.247731+00:00'
content_hash: be2ac149c68a979236d3c0ef1c898af58e3a27f1ebd9b2483134b9d36e8f0705
---
# [Bug] Qwen3.5-35B-A3B-GPTQ-Int4 on RTX 5090 fails on first generation request with Triton CompilationError on latest main

URL: https://github.com/sgl-project/sglang/issues/23739
State: closed
Labels: inactive
Closed at: 2026-07-02T00:48:13Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

## Draft issue body

### Describe the bug

On latest `main`, `Qwen3.5-35B-A3B-GPTQ-Int4` can load successfully on RTX 5090 when I use:

- `--tensor-parallel-size 1`
- `--attention-backend triton`
- `--quantization gptq_marlin`

The server reaches `Uvicorn running`, but the **first generation request** crashes the scheduler with a Triton compile-time error in the Mamba / causal conv path:

```text
triton.compiler.errors.CompilationError
AssertionError("Mismatched type for col0 between then block (<['256'], bf16>) and else block (<['256'], fp16>)")
```

This appears to be a different issue from #20670. I am filing this separately because:

- the original `TP=2 + flashinfer` path is still blocked earlier by `_load_w2`
- this new failure happens only after using the `TP=1 + triton` workaround path

### Reproduction

Environment:

- GPU: `2x NVIDIA GeForce RTX 5090`
- Driver: `580.126.09`
- Python: `3.12.3`
- Torch: `2.9.1+cu130`
- Latest SGLang main commit tested: `714173555c1e9bbc82b2daeeb404d3acfdc83083`
- `sglang==0.0.0.dev1+g714173555`
- `sglang-kernel==0.4.1+cu130`
- `flashinfer-python==0.6.8.post1`
- `transformers==5.5.4`

Model:

- `Qwen3.5-35B-A3B-GPTQ-Int4`

Launch command:

```bash
cd /sgl-workspace/sglang-main-7141735/python

./.venv/bin/python -m sglang.launch_server \
  --model-path /workspace/models/Qwen3.5-35B-A3B-GPTQ-Int4-merged-3af5ca29 \
  --trust-remote-code \
  --dtype float16 \
  --quantization gptq_marlin \
  --context-length 8096 \
  --mem-fraction-static 0.85 \
  --schedule-policy lpm \
  --chunked-prefill-size 8192 \
  --attention-backend triton \
  --tensor-parallel-size 1 \
  --host 127.0.0.1 \
  --port 19182
```

Minimal request:

```bash
curl -X POST http://127.0.0.1:19182/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/workspace/models/Qwen3.5-35B-A3B-GPTQ-Int4-merged-3af5ca29",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 8,
    "temperature": 0
  }'
```

### Expected behavior

The server should either generate normally, or at least complete the first request without a Triton compile-time assertion.

### Actual behavior

The server becomes ready:

```text
INFO:     Uvicorn running on http://127.0.0.1:19182
```

Then the first generation request crashes the scheduler with:

```text
triton.compiler.errors.CompilationError
...
AssertionError("Mismatched type for col0 between then block (<['256'], bf16>) and else block (<['256'], fp16>)")
```

Relevant log references:

- ready: `/tmp/sglang_main_qwen35_tp1_triton.log:75`
- compilation error: `/tmp/sglang_main_qwen35_tp1_triton.log:181`
- assertion: `/tmp/sglang_main_qwen35_tp1_triton.log:195`

### Additional context

For comparison:

- On `0.5.9`, the same `TP=1 + triton` workaround reaches ready but then fails with:
  - `RuntimeError: Expected conv_states_.scalar_type() == input_type to be true, but got false.`

- On latest `main`, that older runtime error is no longer what I see. It has changed into the Triton compilation failure above.

Also, the original `TP=2 + flashinfer` path is still blocked earlier by:

```text
RuntimeError: start (4) + length (4) exceeds dimension size (4).
```

in:

```text
sglang/srt/layers/moe/fused_moe_triton/layer.py::_load_w2
```

So this issue is specifically about the **latest-main `TP=1 + triton` generation path**, not the original `TP=2` blocker.


### Reproduction

```bash
cd /sgl-workspace/sglang-main-7141735/python

./.venv/bin/python -m sglang.launch_server \
  --model-path /workspace/models/Qwen3.5-35B-A3B-GPTQ-Int4-merged-3af5ca29 \
  --trust-remote-code \
  --dtype float16 \
  --quantization gptq_marlin \
  --context-length 8096 \
  --mem-fraction-static 0.85 \
  --schedule-policy lpm \
  --chunked-prefill-size 8192 \
  --attention-backend triton \
  --tensor-parallel-size 1 \
  --host 127.0.0.1 \
  --port 19182
```

### Environment

Environment:

- GPU: `2x NVIDIA GeForce RTX 5090`
- Driver: `580.126.09`
- Python: `3.12.3`
- Torch: `2.9.1+cu130`
- Latest SGLang main commit tested: `714173555c1e9bbc82b2daeeb404d3acfdc83083`
- `sglang==0.0.0.dev1+g714173555`
- `sglang-kernel==0.4.1+cu130`
- `flashinfer-python==0.6.8.post1`
- `transformers==5.5.4`
