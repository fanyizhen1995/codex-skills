---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Introduce sglang.kernels namespace and migrate scattered triton_ops
  kernels (RFC #29630, Phase 2)'
canonical_url: https://github.com/sgl-project/sglang/pull/30044
captured_at: '2026-07-10T23:37:20.323441+00:00'
content_hash: 48fc94b0676660415bc78e528972848583604ef051c95ed706ef322f3f5de2c7
---
# [Kernel] Introduce sglang.kernels namespace and migrate scattered triton_ops kernels (RFC #29630, Phase 2)

URL: https://github.com/sgl-project/sglang/pull/30044
State: closed
Labels: documentation, amd, lora, Multi-modal, deepseek, sgl-kernel, blackwell, run-ci, jit-kernel, bypass-fastfail, run-ci-extra
Closed at: 2026-07-10T13:41:09Z
Merged at: 2026-07-10T13:41:09Z

## Motivation

Phase 2 of RFC #29630. Builds on the Phase-1 test baseline (#29636). Establishes `sglang.kernels.ops.<group>` as the one obvious import surface for callable kernels, migrates the scattered `**/triton_ops` kernels into it, and starts routing call sites through it.

```python
from sglang.kernels.ops.layernorm import rmsnorm
from sglang.kernels.ops.activation import silu_and_mul
from sglang.kernels.ops.kvcache import reshape_and_cache_flash
```

## Modifications

**1. Public namespace + registry** (`python/sglang/kernels/`)
- `spec.py` — `KernelSpec` / `KernelBackend` / `FormatSignature` / `CapabilityRequirement` / `PlatformInfo` (`msgspec.Struct`; importing them pulls no kernel backend and triggers no JIT compilation).
- `registry.py` / `selector.py` — inventory + resolution. **No priority ranking or heuristic auto-selection**: each op has a fixed call path (`KernelSpec.target`); a single-backend op resolves directly, a multi-backend op must name its backend. Extra backends are inventory only.
- `ops/<group>/` — 15 operator-group subpackages. Thin wrapper callables are exposed for the curated dual-backend ops (`layernorm`, `activation`, `gemm`, `quantization`, `moe`, `kvcache`) and for `sampling`, `mamba`, `spatial`, `diffusion`. `communication` stays a documented placeholder — its collective ops (custom all-reduce) are stateful (`torch.ops` + a `CustomAllreduce`-style object), not clean thin-wrapper targets.
- The registry is a complete inventory: **95 ops** — the curated wrappers plus every migrated Triton kernel registered with `backend=triton`.

**2. Migrate all scattered `triton_ops` into `sglang.kernels.ops.<group>`** (52 kernel modules; all 9 `srt/**/triton_ops` dirs removed):

| group | modules | from |
|---|---|---|
| kvcache | 9 | attention/triton_ops (KV index/write, trtllm mha page-table/graph-metadata) + mem_cache (MLA buffer) |
| attention | 10 | attention/triton_ops (decode/extend/prefill/merge/metadata/dsa/…) + model_executor/position |
| memory | 3 | mem_cache/triton_ops (allocator/common/virtual_slot) |
| activation | 1 | layers/triton_ops/softcap |
| grammar | 2 | constrained/triton_ops (bitmask/token_filter) |
| speculative | 7 | speculative/triton_ops (tree/eagle/dflash/cache_locs/…) |
| gemm | 11 | lora/triton_ops (SGMV / absorbed) + `csgmv_configs` |
| moe | 2 | lora/triton_ops (fused MoE LoRA) |
| gemm/moe `trtllm_lora_temp/` | 7 | experimental `lora/trtllm_lora_temp/triton_ops` (kept in a subpackage to avoid colliding with the production kernels) |

All import sites rewritten, including package-level `__init__` re-exports (split across groups), `import ... as` aliases, and a hardcoded config path in a tuning benchmark. Dead code `models/triton_ops/deepseek_v4.py` (0 referrers) deleted. `trtllm_lora_temp` itself is **not** deleted — it has 12 active referrers (MoE `topk`, DeepSeek MLA, `qwen2_moe`, lora manager…); only its kernels are relocated.

The moves are purely mechanical (relocation + import rewrites, no logic changes); each migration commit is a self-contained mechanical step and was produced/verified with a reproducible transform script (kept out of tree; available on request).

**3. Route straightforward call sites through the namespace.** Four unambiguous single-function, signature-identical drop-in sites now import from `sglang.kernels.ops.*` instead of `sgl_kernel`: `sgl_per_token_quant_fp8` (fp8_kernel), `topk_softmax` (moe/topk), `moe_align_block_size` (moe_runner), `silu_and_mul` (marlin lora runner). Backend-selection sites (e.g. `cutlass_w4a8_moe`, which picks JIT on CUDA) and presence-guarded sites (`causal_conv1d`) are intentionally left unchanged.

## Accuracy / Behavior

No kernel logic changes — implementations are relocated verbatim; only import paths change. Public wrappers default to the AOT `sgl_kernel` backend (stable wheel boundary); the 4 rerouted call sites call the identical `sgl_kernel` function through the wrapper.

## Testing

Static (local): changed files compile; ruff (repo `F401,F821,UP037`) clean; 0 functional leftover references to any old `triton_ops` path; every rewritten symbol confirmed present in its target module; namespace/registry test 12/12.

Runtime (H200): `import sglang` OK; **all 70 `sglang.kernels.ops.*` modules import** (no circular imports, cross-refs resolve); the 4 rerouted call-site consumer modules import cleanly; a migrated Triton kernel executes correctly end-to-end (softcap, max_err 2.1e-6) and `sampling.top_k_renorm_probs` renormalizes correctly; 95 ops registered.

> Note: the full `sgl_kernel`-dependent suites (`test/registered/{lora,attention}`, etc.) should be run by CI in a clean env.

### Dispatch overhead (new `ops.*` wrapper vs direct `sgl_kernel` call)

The `ops.*` wrappers add one indirection (`get_kernel()` lru-cache lookup + a call frame) over the direct backend call. Measured per-call launch latency on H200 (same inputs, same GPU; both paths hit the identical CUDA kernel, so any delta is pure Python dispatch):

| op | old µs | new µs | Δ µs | Δ% |
|---|--:|--:|--:|--:|
| layernorm.rmsnorm | 18.036 | 18.064 | +0.028 | +0.15% |
| layernorm.gemma_rmsnorm | 18.046 | 18.087 | +0.041 | +0.22% |
| layernorm.fused_add_rmsnorm | 34.878 | 34.886 | +0.008 | +0.02% |
| activation.silu_and_mul | 26.710 | 26.708 | −0.002 | −0.01% |
| activation.gelu_and_mul | 33.837 | 33.874 | +0.037 | +0.11% |
| activation.gelu_tanh_and_mul | 26.679 | 26.686 | +0.007 | +0.03% |
| quantization.sgl_per_token_quant_fp8 | 13.917 | 13.920 | +0.003 | +0.02% |
| quantization.sgl_per_token_group_quant_8bit | 13.968 | 13.995 | +0.027 | +0.19% |
| moe.moe_align_block_size | 15.118 | 15.120 | +0.002 | +0.01% |
| gemm.fp8_scaled_mm | 109.434 | 109.174 | −0.260 | −0.24% |

Fixed wrapper overhead isolated with a dispatch-dominated tiny tensor (`rmsnorm[16,128]`): **+0.215 µs/call** — negligible vs any real kernel, and within noise for all 10 above. Migrated Triton kernels (non-wrapper) are the same function relocated, so their dispatch cost is unchanged by construction.

## Checklist

- [x] Format with pre-commit (isort/black/ruff).
- [x] Unit tests (GPU-free namespace/registry test).
- [x] Docs (`sglang.kernels/README.md`, review rule).

Part of #29630.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->_Not run yet_<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:warning: **Not run on latest push** -- push again to dispatch.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
