---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Prefix cache causes staging-buffer chunk mismatch and decode staging
  ring leak in PD disaggregation'
canonical_url: https://github.com/sgl-project/sglang/issues/23797
captured_at: '2026-07-11T23:37:37.765746+00:00'
content_hash: f24cb547a71b2d13477b832504d0472a48820a3ff612052efd7de816e5fbf55e
---
# [Bug] Prefix cache causes staging-buffer chunk mismatch and decode staging ring leak in PD disaggregation

URL: https://github.com/sgl-project/sglang/issues/23797
State: closed
Labels: inactive
Closed at: 2026-07-11T00:32:55Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

In PD disaggregation with staging buffer enabled, prefix cache can make prefill and decode disagree on transfer chunk boundaries.

A concrete example:
- `chunked_prefill_size = 2000`
- logical prompt length = `4000`
- decode preallocates 2 staging chunks (`A` and `B`)
- prefix cache hits `3000` tokens on the prefill side
- only `1000` uncached tokens remain, so prefill finishes in a single forward pass
- prefill then treats this as one final chunk (`is_last_chunk=True`)

At this point, decode still expects the original **2-chunk transfer plan**, but prefill only sends **1 final chunk**. This causes chunk accounting to become inconsistent.

Observed consequences:
- dirty write into the decode staging ring
- one decode-side staging allocation is never reclaimed
- watermark cannot advance
- later requests block forever waiting for reusable staging ring space

So the issue is not just a hang. It is effectively a decode-side staging ring allocation leak / ring-space leak caused by prefix-cache-induced chunk mismatch.

Expected behavior:
prefix cache should reduce compute work, but it should not change the logical transfer chunk plan already established by decode. Prefill should still honor the decode-side chunk boundaries.

### Reproduction

prefill node: SGLANG_DISAGG_STAGING_BUFFER=1   \
python3 -m sglang.launch_server \
  --model-path qwen35 \
  --trust-remote-code \
  --tp-size 2 \
  --chunked-prefill-size 2000 \
  --page-size 1 \
  --disaggregation-mode prefill \
  --disaggregation-bootstrap-port 1234 

decode node: SGLANG_DISAGG_STAGING_BUFFER=1   \
python3 -m sglang.launch_server \
    --model-path qwen35 \
    --trust-remote-code \
    --tp 4 \
    --disable-radix-cache \
    --page-size 1 \
    --disaggregation-mode decode \
    --disaggregation-bootstrap-port 1234 

bench: python3 -m sglang.bench_serving \
  --backend sglang-oai-chat \
  --base-url ${URL} \
  --model qwen35 \
  --dataset-name generated-shared-prefix \
  --num-prompts 1000 \
  --request-rate 8 \
  --gsp-num-groups 1 \
  --gsp-prompts-per-group 1000 \
  --gsp-system-prompt-len 1500 \
  --gsp-question-len 1500 \
  --gsp-output-len 200 \
  --extra-request-body '{"ignore_eos": true, "nvext": {"ignore_eos": true}}'

### Environment

Python: 3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0,1: NVIDIA H800
GPU 0,1 Compute Capability: 9.0
NVCC: Cuda compilation tools, release 12.8, V12.8.61
CUDA Driver Version: 550.163.01
PyTorch: 2.9.1+cu128
sglang: 0.5.10.post1
sglang-kernel: 0.4.1
flashinfer_python: 0.6.7.post3
flashinfer_cubin: 0.6.7.post3
triton: 3.5.1
transformers: 5.3.0
