---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [Fix] Fix --attention-backend triton work for DeepSeek MLA on MI355
  (null-K + decode dispatch + RoPE)'
canonical_url: https://github.com/sgl-project/sglang/pull/30355
captured_at: '2026-07-15T23:40:28.353201+00:00'
content_hash: 31931c5d7d44b1961fb2cee6b52f2de1757247b403b605c975fa9684072aece7
---
# [AMD] [Fix] Fix --attention-backend triton work for DeepSeek MLA on MI355 (null-K + decode dispatch + RoPE)

URL: https://github.com/sgl-project/sglang/pull/30355
State: closed
Labels: amd, deepseek, run-ci
Closed at: 2026-07-15T21:19:24Z
Merged at: 2026-07-15T21:19:24Z

## Motivation

DeepSeek MLA models could not run with `--attention-backend triton` on gfx95 (MI300/MI355) when `SGLANG_USE_AITER=1` (the ROCm image default). Triton is the common NVIDIA/AMD path and should not GPU-fault or produce wrong output on a valid backend selection.

Root cause is a recurring anti-pattern: several gfx95/aiter fused MLA paths are gated on env vars (`SGLANG_USE_AITER`, `SGLANG_ROCM_FUSED_DECODE_MLA`) or on "not in the absorb-core backend list", **not on the actually selected attention backend**. As a result the triton backend inherits aiter-only fused paths that it cannot consume:

1. **Prefill null-K GPU fault** — in `forward_absorb_core`, triton fell into the aiter-fused `fused_qk_rope_cat_and_cache_mla` path, which writes K into the KV cache and returns an empty `k` (numel=0, null ptr) for the aiter kernel to read from the buffer. Triton's extend kernel reads `k` directly → `Memory access fault on address (nil)`.
2. **Decode dispatch fault** — `_dispatch_mla_subtype` honored `SGLANG_ROCM_FUSED_DECODE_MLA=1` for any backend, routing triton decode to `MLA_FUSED_ROPE_ROCM` (`forward_absorb_fused_mla_rope_prepare`), which is neither MXFP4-aware (`bmm` sees packed `w_kc`, 64 vs 128) nor triton-metadata-compatible (`ForwardMetadata` unpack).
3. **Accuracy 0.03** — `_skip_rope_for_aiter_fused_mla` returned True for triton (backend not in the absorb-core list), so RoPE was silently skipped in prepare while triton took the standard cat path → garbage output.

## Modifications

`forward_mla.py`:
- `forward_absorb_core`: gate the aiter-fused path to `self.current_attention_backend == "aiter"` so triton builds a real `k = torch.cat([k_nope, k_pe])` with `save_kv_cache=True`.
- rope-in-prepare condition: allow triton through (`or self.current_attention_backend == "triton"`).
- `_skip_rope_for_aiter_fused_mla`: restrict to `== "aiter"` so triton applies RoPE in prepare (the 0.03 → 0.945 fix).

`attention_backend_handler.py`:
- `_dispatch_mla_subtype`: gate `MLA_FUSED_ROPE_ROCM` on `current_attention_backend == "aiter"` so triton (and other backends) decode via the standard `MLA` path.

All changes are backend-scoped; aiter/fa3/flashinfer/CUDA paths are unchanged.

## Accuracy Tests

DeepSeek-R1-MXFP4 (Quark MXFP4), MI355X gfx950, tp4, `--kv-cache-dtype fp8_e4m3`, gsm8k (200q):

| Backend | Config | gsm8k |
|---|---|---|
| aiter (baseline) | + spec + cuda graph | 0.955 |
| **triton (this PR)** | **no spec** | **0.945** |

`--attention-backend triton` now runs DeepSeek-R1-MXFP4 end-to-end with correct output.

## Scope / Known Limitation

This PR makes triton MLA correct for **non-speculative** decode. `--attention-backend triton` **+ EAGLE speculative decoding is still broken** (GPU fault in the NextN draft/verify path, independent of cuda graph) and is out of scope here — that is a separate draft-path bug. For DeepSeek MLA with speculative decoding, continue using `--attention-backend aiter` (fully working, 0.955).

## Checklist

- [x] Backend-scoped; no change to aiter/CUDA behavior.
- [x] Verified triton correctness on real DeepSeek-R1-MXFP4 (0.945).
- [x] Follows `[Tag] Description` commit/PR convention.









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29228875042](https://github.com/sgl-project/sglang/actions/runs/29228875042)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29228874957](https://github.com/sgl-project/sglang/actions/runs/29228874957)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
