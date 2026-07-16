---
source_id: sglang-github-closed-issues-prs
title: '[Bug] DCP metadata path crashes GLM-5.2/DeepSeek-V2 under pipeline parallelism
  (hardcoded get_key_buffer(0)), even with dcp_size=1'
canonical_url: https://github.com/sgl-project/sglang/issues/30464
captured_at: '2026-07-12T23:38:53.046804+00:00'
content_hash: ff389f26d5a0f9cc27876b656f25cdf8c699088b7aeb8d9d15d55e22ae33d6a0
---
# [Bug] DCP metadata path crashes GLM-5.2/DeepSeek-V2 under pipeline parallelism (hardcoded get_key_buffer(0)), even with dcp_size=1

URL: https://github.com/sgl-project/sglang/issues/30464
State: closed
Labels: 
Closed at: 2026-07-12T03:48:04Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Under pipeline parallelism (pp_size > 1), the DCP (decode context parallel)
metadata path crashes all non-first PP stages on the first extend/prefill
forward — even when DCP is NOT enabled (dcp_size=1).

In `python/sglang/srt/model_executor/runner/eager_runner.py`, `_execute_extend()`
runs this block gated ONLY on hasattr(...), not on dcp_size:

    if forward_batch.needs_forward_metadata_init():
        if hasattr(model_runner.model, "prepare_context_parallel_metadata_for_dcp"):
            forward_batch.attn_dcp_metadata = model_runner.model.prepare_context_parallel_metadata_for_dcp(
                ...,
                get_token_to_kv_pool().get_key_buffer(0).shape,   # hardcoded global layer 0
                ...,
            )

get_key_buffer(layer_id) indexes self.kv_buffer[layer_id - self.start_layer].
On PP stages other than the first, start_layer > 0 (e.g. 20/40/60), so
get_key_buffer(0) -> kv_buffer[-20] -> IndexError. That scheduler process dies;
peer ranks then fail the gloo collective with "Connection closed by peer", and
the whole PP group crash-loops.

DeepSeek-V2 / GLM-5.2 (MLA) models always define
prepare_context_parallel_metadata_for_dcp, so this fires for ANY PP deployment
of these models regardless of dcp_size.

Traceback:
  File ".../model_executor/runner/eager_runner.py", line 278, in _execute_extend
    get_token_to_kv_pool().get_key_buffer(0).shape,
  File ".../mem_cache/memory_pool.py", line 2226, in get_key_buffer
    return self.kv_buffer[layer_id - self.start_layer].view(self.dtype)
IndexError: list index out of range

Introduced by #14194 ("[feature] implement dcp for deepseek_v2"). Still present
on current main (eager_runner.py ~line 270/273).

Suggested fix:
  1. Use the rank-local first layer instead of hardcoded 0:
     get_token_to_kv_pool().get_key_buffer(get_token_to_kv_pool().start_layer).shape
     (KV shape is identical across layers; this index is valid on every PP rank.)
  2. Gate the block on dcp_size > 1 (or server_args.enable_dcp), not just hasattr().

### Reproduction

Serve a DeepSeek-V2 / GLM-5.2 (MLA) model with TP + PP across 2 nodes, WITHOUT
enabling DCP (dcp_size defaults to 1). Server warmup (or the first request)
triggers it.

Launch (leader; worker identical with --node-rank 1):

  python3 -m sglang.launch_server \
    --model-path zai-org/GLM-5.2-FP8 \
    --tp-size 4 --pp-size 4 --nnodes 2 --node-rank 0 \
    --dist-init-addr <leader>:5000 \
    --trust-remote-code \
    --kv-cache-dtype fp8_e4m3 \
    --context-length 1048576 \
    --chunked-prefill-size 8192 \
    --mem-fraction-static 0.82 \
    --host 0.0.0.0 --port 30000

Then send any request:

  curl http://<leader>:30000/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"GLM-5.2-FP8","messages":[{"role":"user","content":"hi"}],"max_tokens":8}'

PP stages with start_layer>0 raise IndexError in _execute_extend at the first
forward, then the group crash-loops.

Note: --disable-cuda-graph / --disable-piecewise-cuda-graph and
--skip-server-warmup do NOT help (extend always runs the eager runner; skipping
warmup only defers the crash to the first real request).

### Environment

# Reproduced on SGLang main @ commit eeee3abbbf8196e54c227faecfd5faba7b1dfc4b
# (check_env prints sglang 0.0.0.dev0 due to a setuptools_scm fallback in our build;
#  the offending code is also present on current main.)

Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0-7: NVIDIA H100 80GB HBM3
GPU Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 580.105.08
PyTorch: 2.11.0+cu130
sglang: 0.0.0.dev0   (commit eeee3abbbf)
sgl_kernel: 0.4.4
flashinfer_python: 0.6.12
triton: 3.6.0
transformers: 5.8.1
torchao: 0.17.0+cu130
numpy: 2.3.5
fastapi: 0.139.0
pydantic: 2.13.4
pyzmq: 27.1.0
uvicorn: 0.50.0
xgrammar: 0.2.1
openai: 2.6.1
Deployment: 2 nodes x 8x H100 80GB, TP=4 PP=4 (16 GPUs), Kubernetes LeaderWorkerSet
