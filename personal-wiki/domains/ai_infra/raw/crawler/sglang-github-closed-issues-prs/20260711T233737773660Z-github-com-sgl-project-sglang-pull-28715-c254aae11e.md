---
source_id: sglang-github-closed-issues-prs
title: '[minimax-m3] Split 4/4: model + VL + glue + function-call + fp8 quant + generic
  infra'
canonical_url: https://github.com/sgl-project/sglang/pull/28715
captured_at: '2026-07-11T23:37:37.773660+00:00'
content_hash: c254aae11e0c3b4eacad12d3d6e71dfc4e7c2e11f1c2c67d36e51b8e56df28a2
---
# [minimax-m3] Split 4/4: model + VL + glue + function-call + fp8 quant + generic infra

URL: https://github.com/sgl-project/sglang/pull/28715
State: closed
Labels: quant, run-ci, jit-kernel, bypass-fastfail, run-ci-extra
Closed at: 2026-07-11T03:11:07Z
Merged at: 2026-07-11T03:11:07Z

Part 4 (final) of the 4-PR split of #27944 (MiniMax-M3). The integration PR — the only split PR that moves forward / quant / attention behavior and carries the e2e validation. Splits 1-3 (#28712 / #28713 / #28714) have merged to `main`; this PR is rebased on top.

## What's in this PR

- **Models + VL**: `minimax_m3.py`, `minimax_m3_vl.py`, `minimax_vl_common.py` + VL processor/configs
- **Glue**: `attention_registry`, `minimax_sparse_backend`, `server_args`, `scheduler`, `template_detection`, `multi_tokenizer_mixin`, `serving_chat`, `warmup`, `forward_batch_info`, `utils/common`, `hf_transformers/common`, `reasoning_parser`
- **Function-call**: `function_call/minimax_m3.py` + `function_call_parser.py` + detector test + template_manager test
- **fp8 quant group**: `fp8.py`, `fp8_kernel.py`, `fp8_utils.py`, `deep_gemm_wrapper/entrypoint.py`, `mxfp8_block_convert.py`
- **Generic MoE infra**: `ep_moe/kernels`, `topk`, `token_dispatcher/standard`, `layernorm`, `moe_fused_gate`, `per_token_group_quant_8bit` (+ cuh/bench/test)
- **`deep_gemm.py`, `radix_attention.py`** — whole files (cross-bucket imports + generic hunk changes)
- **`environ`** — PR4-owned descriptors (the rest resolved on rebase from Splits 1/2)

## Review-driven changes (thanks @BBuf)

- `SGLANG_OPT_USE_JIT_PER_TOKEN_GROUP_QUANT` defaulted to `False` — it reroutes the generic fp8 path (every model, not just MiniMax); M3's deep_gemm MoE quant uses `fuse_silu_and_mul=True` which selects V2 regardless, so the V1 JIT path is opt-in only. Renamed `use_jit_quant` → `use_jit_per_token_group_v1_quant`, extracted `_run_per_token_group_quant_8bit_kernel` helper, added `and not _is_musa` guards (V1 .cuh is CUDA-only).
- GPT-OSS SM120+MXFP4 `moe_runner_backend` reverted to main's `marlin` (carried in from #27944, unrelated to M3).
- `fused_topk` sigmoid branch restructured per review: `assert` → `raise ValueError`, single `scale` honoring `apply_routed_scaling_factor_on_output`.
- `mxfp8` allow-list in `_moe_runner_backend_quant_constraints` keeps `deep_gemm` for M3 and whitelists `triton` on AMD gfx950 (CDNA4 / MI355X, where flashinfer is unavailable); `auto`/override resolve to `triton` there. (gfx950 fix co-authored with @zijiexia, who verified MI355X e2e.)

## e2e validation (4×GB300, M3-MXFP8)

- **GSM8K** (1319, no-thinking): acc 95.2%, stop-rate 97.4%, 0 errors
- **AIME26** (thinking, 480 requests): pass@1 80.8%, pass@16 86.7%, 0 errors
- Multi-turn `</mm:think>` leak regression: clean
- V1 vs V2 per-token-group quant benchmark (B200 + H100, 96 configs each): V1 ≥ V2 in all 192 configs, median 1.10-1.13×, max 1.86×
- `post_reorder_deepgemm` unit test: 14 cases (rsf × pad × tokens) all pass

## Notes

- The `moe_runner_backend` resolution moved to `arg_groups/overrides.py` (`_moe_runner_backend_quant_constraints`) on a recent main rebase; M3's `mxfp8 + deep_gemm` and gfx950 `mxfp8 + triton` are both preserved there.
- M3 model files use `get_server_args()` (runtime_context) instead of the legacy `get_global_server_args()`, matching main's ratchet direction.































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29085664737](https://github.com/sgl-project/sglang/actions/runs/29085664737)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29085664528](https://github.com/sgl-project/sglang/actions/runs/29085664528)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
