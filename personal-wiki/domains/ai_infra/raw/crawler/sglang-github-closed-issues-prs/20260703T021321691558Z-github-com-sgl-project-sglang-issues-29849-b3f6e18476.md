---
source_id: sglang-github-closed-issues-prs
title: '[Bug] `flashinfer_mxfp4` MoE runner crashes with `''DeepEPLLDispatchOutput''
  object has no attribute ''topk_output''` during decode CUDA-graph capture (DeepSeek-V4-Flash
  + DP-attention + DeepEP on B300)'
canonical_url: https://github.com/sgl-project/sglang/issues/29849
captured_at: '2026-07-03T02:13:21.691558+00:00'
content_hash: b3f6e184769e54e820bf0a8d6bb7001e4fc48c1cc6410d5a8616d393828e422a
---
# [Bug] `flashinfer_mxfp4` MoE runner crashes with `'DeepEPLLDispatchOutput' object has no attribute 'topk_output'` during decode CUDA-graph capture (DeepSeek-V4-Flash + DP-attention + DeepEP on B300)

URL: https://github.com/sgl-project/sglang/issues/29849
State: closed
Labels: 
Closed at: 2026-07-02T06:05:06Z
Merged at: 

**Describe the bug**

Serving the native FP4 **DeepSeek-V4-Flash** checkpoint with DP-attention + DeepEP and the `flashinfer_mxfp4` MoE runner crashes during **decode CUDA-graph capture**:

```
AttributeError: 'DeepEPLLDispatchOutput' object has no attribute 'topk_output'
```

Root cause: the `flashinfer_mxfp4` MoE runner reads `dispatch_output.topk_output`, but the DeepEP low-latency dispatch output `DeepEPLLDispatchOutput` (`python/sglang/srt/layers/moe/token_dispatcher/deepep.py`) only exposes `topk_ids` / `topk_weights` / `masked_m` / `expected_m` — there is no `topk_output` field. So `flashinfer_mxfp4` is incompatible with the DeepEP low-latency dispatch path (`deep_gemm` and `flashinfer_cutedsl` runners do handle `DeepEPLLDispatchOutput`).

**Reproduction** (`lmsysorg/sglang:v0.5.14-cu130`, 4×B300, single node):

```bash
python3 -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-V4-Flash --trust-remote-code \
  --tp-size 4 --dp-size 4 --enable-dp-attention \
  --ep-size 4 --moe-a2a-backend deepep \
  --moe-runner-backend flashinfer_mxfp4 \
  --kv-cache-dtype fp8_e4m3
```

`--deepep-mode` defaults to auto → low_latency for decode; the crash happens at CUDA-graph capture, before "ready to roll".

**Traceback (abridged)**

```
File ".../srt/managers/scheduler.py", line 855, in init_all_cuda_graphs
    self.tp_worker.init_cuda_graphs()
File ".../srt/managers/tp_worker.py", line 351, in init_cuda_graphs
    self.model_runner.init_cuda_graphs(...)
File ".../srt/model_executor/model_runner.py", line 901, in init_cuda_graphs
    return self.forward_deepep(...)
File ".../srt/models/deepseek_v2.py", line 1340, in forward_deepep
    return self.forward_impl(hidden_states, topk_output)
  ... (MoE runner) topk_output = dispatch_output.topk_output
AttributeError: 'DeepEPLLDispatchOutput' object has no attribute 'topk_output'
[...] Received sigquit from a child process. It usually means the child failed.
Rank 0 scheduler died during initialization (exit code: -3).
```

(The failing `topk_output = dispatch_output.topk_output` is in the `flashinfer_mxfp4` MoE runner path; `DeepEPLLDispatchOutput` provides `topk_ids`/`topk_weights`/`masked_m`/`expected_m` but no `topk_output`.)

**Workaround**

Use `--moe-runner-backend deep_gemm` instead of `flashinfer_mxfp4`; DP-attention + DeepEP + CUDA graph then boots and serves correctly.

**Expected behavior**

Either make `flashinfer_mxfp4` handle `DeepEPLLDispatchOutput`, or fail fast at startup with a clear message (e.g. "flashinfer_mxfp4 does not support DeepEP low-latency; use --moe-runner-backend deep_gemm") instead of a cryptic `AttributeError` deep inside CUDA-graph capture.

**Environment**

- SGLang v0.5.14 (`lmsysorg/sglang:v0.5.14-cu130`), CUDA 13
- 4× NVIDIA B300 (Blackwell), single node
- DeepSeek-V4-Flash, native FP4 MoE experts

**Related**: #23896
