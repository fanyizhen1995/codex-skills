---
source_id: sglang-github-closed-issues-prs
title: '[MLX] Size the attention KV pool at the compute dtype for quantized models'
canonical_url: https://github.com/sgl-project/sglang/pull/30097
captured_at: '2026-07-07T23:35:30.919726+00:00'
content_hash: d1ac98ef4df3b8afc942ab181f0a4e5a73cf8b7a6630540c72fbba025efd8705
---
# [MLX] Size the attention KV pool at the compute dtype for quantized models

URL: https://github.com/sgl-project/sglang/pull/30097
State: closed
Labels: apple-silicon
Closed at: 2026-07-07T03:32:00Z
Merged at: 2026-07-07T03:32:00Z

## Motivation

The shared MLX attention KV pool stores **dequantized projection outputs**,
but its dtype is inferred from `k_proj.weight`, so QuantizedLinear's packed
integer weights fall back to float32. The values actually written are
bf16/fp16 (the compute dtype), so the float32 pool:

- doubles pool bytes per slot for zero precision gain (bf16 -> float32 is a
  pure upcast of the same values), halving the auto-sized token capacity for
  every quantized model on the MLX backend, and
- makes prefix-hit forwards run in float32 — `PoolBackedAttentionKVCache`
  concatenates the gathered float32 prefix with new bf16 K/V and MLX promotes
  the whole graph — while no-hit forwards run at the compute dtype, i.e. the
  same request computes at different precision depending on radix state.

## Modifications

`MlxModelRunner._attention_kv_config_for_layer`: when the projection weight
dtype is not a float (packed quantized weights), infer the pool dtype from
the quantization `scales` (which carry the compute dtype), keeping the
float32 fallback when scales are absent or non-float. Unquantized models are
unchanged.

Note on the opt-in AOT RoPE pool-scatter kernel (`SGLANG_MLX_USE_CUSTOM_ROPE`,
default off): its host-side validation requires q/k/v and both pool buffers to
share one dtype, and it only dispatches f16/bf16 kernel specializations
(float32 pools throw "unsupported dtype" at dispatch). So quantized models
with the kernel enabled previously failed loudly on the first decode step
(bf16 activations vs float32 pool, `rope_pool_fused.cpp` dtype check); with
the pool now at the compute dtype, that combination runs on the same bf16
kernel path that unquantized bf16 models already exercise.

## Test

- New `test/registered/unit/hardware_backend/mlx/test_mlx_pool_dtype.py`
  (5 tests): unquantized weight-dtype passthrough, quantized bf16/fp16 via
  scales, missing-scales float32 fallback, bytes-per-slot halving.
- Existing MLX unit suites at base parity (only the known pre-existing
  `forward_ct` error in test_attention_patching, identical on main).
- Apple Silicon (M-series 24 GB), real weights:
  - A/B boot of Qwen1.5-MoE-A2.7B-Chat-4bit, same launch back to back:
    `bytes_per_slot` 393216 -> 196608 (exactly halved; auto-sized
    `pool_size` 6413 -> 22797, budgets varied slightly between boots — the
    structural gain is 2x capacity per byte of budget). Greedy responses
    identical across the boots, and the radix prefix-hit response
    (`#cached-token: 28`) matches the no-hit response.
  - qwen2_moe (Qwen1.5-MoE 4bit) serving regression: PASS (3/3), default
    radix/pool path with prefix hits.
  - qwen3_moe (Qwen3-30B-A3B 4bit) serving regression: PASS (3/3).

cc @yeahdongcn































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28837877415](https://github.com/sgl-project/sglang/actions/runs/28837877415)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28837877385](https://github.com/sgl-project/sglang/actions/runs/28837877385)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
