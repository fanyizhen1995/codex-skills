---
source_id: sglang-github-closed-issues-prs
title: Default Hunyuan V3 to bfloat16 when the checkpoint has no dtype
canonical_url: https://github.com/sgl-project/sglang/pull/30594
captured_at: '2026-07-09T23:36:35.338093+00:00'
content_hash: 76d5e5382d4814701e3901e20dce1a40b87fcbce22f08579fd841dd326b45c5a
---
# Default Hunyuan V3 to bfloat16 when the checkpoint has no dtype

URL: https://github.com/sgl-project/sglang/pull/30594
State: closed
Labels: documentation, run-ci, run-ci-extra
Closed at: 2026-07-09T07:10:49Z
Merged at: 

## Motivation

All three Hunyuan V3 checkpoints (`tencent/Hy3`, `tencent/Hy3-FP8`, `tencent/Hy3-preview`) ship a `config.json` **without `torch_dtype`**. `_get_and_verify_dtype` treats a missing dtype as a float32 checkpoint, and `--dtype auto` (the default) downcasts float32 to **float16**:

```
tencent/Hy3-FP8, --dtype auto  ->  resolved dtype: torch.float16
```

Hunyuan V3 is a bf16 model, so this is wrong on two levels:

1. **Crash**: fp16 activations hit bf16-only kernel paths. On current main + recent flashinfer, the server dies during decode CUDA-graph capture in the CuTe `fused_add_rmsnorm` dtype check (`ValueError: Mismatched Tensor ... expected dtype=bfloat16`) — with an error message that gives no hint the root cause is dtype resolution.
2. **Silent numerics change**: on stacks where nothing crashes, the model silently runs in fp16 instead of the bf16 it was trained/released with.

None of the Hy3 cookbook commands specify `--dtype`, so they are affected out of the box.

The crash (H200 TP4, `sglang serve --model-path tencent/Hy3-FP8 --tp 4 --trust-remote-code`, abridged traceback — all 4 TP ranks die during decode CUDA-graph capture):

```
[TP2] Scheduler hit an exception: Traceback (most recent call last):
  ...
  File ".../sglang/srt/model_executor/runner/decode_cuda_graph_runner.py", line 363, in __init__
    self.capture()
  ...
  File ".../sglang/srt/models/hunyuan_v3.py", line 403, in forward
    hidden_states, residual = self.post_attention_layernorm(hidden_states, residual)
  File ".../sglang/srt/layers/layernorm.py", line 327, in forward_cuda
    fused_add_rmsnorm(x, residual, self.weight.data, self.variance_epsilon)
  File "/usr/local/lib/python3.12/dist-packages/sgl_kernel/elementwise.py", line 160, in fused_add_rmsnorm
    _flashinfer_norm.fused_add_rmsnorm(input, residual, weight, eps, enable_pdl)
  File "/usr/local/lib/python3.12/dist-packages/flashinfer/norm/__init__.py", line 274, in fused_add_rmsnorm
    fused_add_rmsnorm_cute(
  File "/usr/local/lib/python3.12/dist-packages/flashinfer/norm/kernels/fused_add_rmsnorm.py", line 1038, in fused_add_rmsnorm_cute
    kernel(input, residual, weight, M, eps)
  File ".../cutlass/cutlass_dsl/tvm_ffi_provider.py", line 593, in __call__
    return tvm_ffi.Function.__call__(self, *args)
  File "python/tvm_ffi/cython/function.pxi", line 968, in tvm_ffi.core.Function.__call__
ValueError: Mismatched Tensor on argument #1 when calling: `__call__(mX: Tensor([n0, 4096], bfloat16),
mR: Tensor([n0, 4096], bfloat16), mW: Tensor([4096], bfloat16), M: int32, eps: float32)`, expected dtype=bfloat16

[...] Received sigquit from a child process. It usually means the child failed.
```

## Modifications

- `_get_and_verify_dtype`: resolve `auto` to **bfloat16** for `model_type == "hy_v3"` when the checkpoint carries no dtype — the same shape as the existing gemma special case. An explicit `--dtype float16` is still honored, and a future `torch_dtype` in the checkpoint config takes precedence.
- Cookbook: add `--dtype bfloat16` to all Hy3 command-generator combos (`hy3.jsx`, 20 entries) and the static example commands in `Hy3.mdx` / `Hunyuan3-Preview.mdx`. This is belt-and-suspenders for users on already-released images that don't contain this fix; it is a no-op once the fix is in.
- New CPU unit test `test/registered/unit/configs/test_model_config_dtype.py` covering: hy_v3 auto → bf16, explicit fp16 honored, generic model auto → fp16 unchanged, config dtype precedence, gemma case unchanged.

## Test

- Unit test: `5 passed` (CPU).
- Resolution check on H200 container: `tencent/Hy3-FP8` + `--dtype auto` now resolves to `torch.bfloat16` (with and without `--trust-remote-code`).
- e2e on H200 TP4: `sglang serve --model-path tencent/Hy3-FP8 --tp 4 --trust-remote-code` (no `--dtype`, i.e. the day-0 cookbook shape) previously crashed at CUDA-graph capture; with this fix the server starts, captures prefill+decode graphs, and greedy generation is correct.

🤖 Generated with [Claude Code](https://claude.com/claude-code)











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28992851210](https://github.com/sgl-project/sglang/actions/runs/28992851210)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28993148507](https://github.com/sgl-project/sglang/actions/runs/28993148507)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
