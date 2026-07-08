---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Gemma4 E4B: fp8 KV cache crashes with num_kv_shared_layers > 0 — Triton
  extend_attention dtype mismatch'
canonical_url: https://github.com/sgl-project/sglang/issues/22277
captured_at: '2026-07-06T02:14:53.056992+00:00'
content_hash: 1300ffc5cf530f950a17390a7f460273c3a1ba915db6642d5d58ce63dddf693d
---
# [Bug] Gemma4 E4B: fp8 KV cache crashes with num_kv_shared_layers > 0 — Triton extend_attention dtype mismatch

URL: https://github.com/sgl-project/sglang/issues/22277
State: closed
Labels: inactive
Closed at: 2026-07-06T00:41:19Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

### Model
- `google/gemma-4-E4B-it` (`Gemma4ForConditionalGeneration`)
- Key config: `num_kv_shared_layers: 18`, `head_dim: 256`, `global_head_dim: 512`

### Error

Server starts and CUDA graphs capture successfully, but crashes on the first request (warmup):

```
triton.compiler.errors.CompilationError: at 264:17:
            qk = tl.dot(q, k, out_dtype=tl.float32)
                 ^
Unsupported rhs dtype fp8e5
```

The crash is in the **extend** section of `extend_attention.py` (line ~483), NOT the prefix section. `K_Extend` (newly computed keys) is in fp8 dtype, causing a mixed-precision `tl.dot(bf16_q, fp8_k)` that Triton doesn't support.

The prefix section (line ~378) correctly handles this with `tl.dot(q.to(k.dtype), k)`, but the extend section uses `tl.dot(q, k, out_dtype=tl.float32)` without dtype alignment.

### Root Cause

When `num_kv_shared_layers > 0`, KV-sharing layers skip K/V projections and retrieve cached KV from earlier layers. When the KV cache dtype is fp8, the shared/extend keys are stored in fp8 before the attention computation, causing the extend attention path to receive fp8 keys where it expects bf16.

### Evidence

| Config | Result |
|--------|--------|
| Gemma4 31B (`num_kv_shared_layers: 0`) + `fp8_e5m2` | ✅ Works, serves requests |
| Gemma4 E4B (`num_kv_shared_layers: 18`) + `fp8_e5m2` | ❌ Crashes |
| Gemma4 E4B + modified config `num_kv_shared_layers: 0` + `fp8_e5m2` | ✅ Starts and serves requests (output garbage due to weight mismatch, but no crash) |
| Gemma4 E4B (`num_kv_shared_layers: 18`) + `bf16` KV | ✅ Works |

Both `fp8_e5m2` and `fp8_e4m3` fail with the same error for E4B.

### Suggested Fix

The extend section of `extend_attention.py` should align dtypes like the prefix section does:

```python
# Current (line ~483):
qk = tl.dot(q, k, out_dtype=tl.float32)

# Fix — match prefix section pattern (line ~378):
qk = tl.dot(q.to(k.dtype), k)
```

Or alternatively, ensure that KV-sharing layers dequantize extend keys to bf16 before passing them to the attention kernel.


### Reproduction

```bash
sglang serve \
    --model-path google/gemma-4-E4B-it \
    --tp 1 \
    --mem-fraction-static 0.5 \
    --context-length 16384 \
    --kv-cache-dtype fp8_e5m2 \
    --host 0.0.0.0 --port 30000
```

### Environment

- SGLang: **main branch** (also reproduced on PR #21952 gemma4 branch)
- GPU: NVIDIA H200 NVL (143,771 MiB), CUDA capability 9.x
- Docker image: `lmsysorg/sglang:latest` + `pip install -e "git+https://github.com/sgl-project/sglang.git#egg=sglang&subdirectory=python" --no-deps`
- Triton: bundled with Docker image
- transformers: `git+https://github.com/huggingface/transformers.git`
