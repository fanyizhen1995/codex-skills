---
source_id: sglang-github-closed-issues-prs
title: '[LoRA] DSA indexer targets + MoE-LoRA cuda-graph and RL adapter-reload fixes'
canonical_url: https://github.com/sgl-project/sglang/pull/29874
captured_at: '2026-07-04T02:13:49.131056+00:00'
content_hash: af0ea95cc6f33981ec3c549a89fe79187cd89476a1b8d1b2136bd8b253c8de06
---
# [LoRA] DSA indexer targets + MoE-LoRA cuda-graph and RL adapter-reload fixes

URL: https://github.com/sgl-project/sglang/pull/29874
State: closed
Labels: lora
Closed at: 2026-07-03T20:14:28Z
Merged at: 2026-07-03T20:14:28Z

## Summary

This branch makes LoRA serving work for GLM-5.1 / DeepSeek-V3.2-family models in an RL (colocate, per-step adapter refresh) setting. It adds DSA indexer projections (`indexer.wq_b`, `indexer.wk`, `indexer.weights_proj`) as LoRA targets, and fixes four LoRA serving bugs: dense `gate_up` LoRA-B mis-sizing under `--moe-dense-tp-size 1`, an illegal-memory-access during cuda-graph capture with MoE-expert LoRA under `--enable-dp-attention`, stale served adapter weights after per-step unload/reload, and a buffer-load crash under `--experts-shared-outer-loras`.

## Below is CC’s summary of the dev journal and unit test correctness. You can ignore it.

## Bug fixes

- **Dense `gate_up_proj` LoRA-B sizing crash under `--moe-dense-tp-size 1`** (`python/sglang/srt/lora/mem_pool.py`): rollout crashed with `LoRA B output dim != base partition prefix dim` on the dense-MLP layers of MoE models. Root cause: `_get_standard_shape` unconditionally divided the column-parallel output dim by the global TP size, but under `--moe-dense-tp-size 1` the dense `gate_up_proj` is fully **replicated** (`output_size_per_partition == output_size`), so LoRA-B was undersized relative to the base partition. Fix: new `_column_parallel_out_partition()` probes the actual base module's `output_size_per_partition` (the same ground truth `set_lora_info` validates against, cached per `(module_name, layer_idx)`); when the base is replicated, LoRA-B keeps the full output dim instead of being sharded.

- **MoE-expert LoRA illegal memory access during cuda-graph capture under `--enable-dp-attention`** (`python/sglang/srt/lora/backend/base_backend.py`, `python/sglang/srt/lora/triton_ops/virtual_experts.py`): capture died with `cudaErrorIllegalInstruction`. Two root causes:
  - The MoE runs on **DP-gathered** tokens (up to `max_bs * attn_dp_size`, i.e. `global_dp_buffer_len`), but the per-token LoRA routing buffers (`token_lora_mapping`, `weight_indices_long`, `token_mask`, padded-token bounds) were sized for the per-rank `max_bs`, so the MoE-LoRA kernels read past them. Fix: size these buffers by the gathered token count; `_compute_moe_lora_info` gains a `mapping_len` parameter, fills only the per-rank prefix `[0, num_tokens)`, and resets the gathered tail to `-1` (adapter-disabled).
  - `_merged_experts_fused_moe_lora_add_impl` trimmed `sorted_token_ids` / `expert_ids` to a "tight" bound that can be smaller than `num_tokens_post_padded` (a GPU-side runtime count), while the shrink/fused-MoE kernels read those buffers **without a bounds mask** up to that count. In eager mode the slack still lived inside the original worst-case allocation; under the cuda-graph mempool's tight packing it could land in another tensor or past a page. Fix: keep the full worst-case-allocated buffers.
  - Correctness follow-up in the same path: the last per-rank token's adapter id is broadcast across the DP-gathered tail so tokens gathered from other DP ranks also get the LoRA delta on this rank's local experts. The broadcast is **unconditional** (any time the gathered count exceeds the per-rank count and the rank has tokens), which is only correct under a single active adapter per batch (the colocate-RL case) — a multi-adapter batch would have its tail stamped with the last request's adapter id rather than kept at `-1` (see notes).

- **Stale served weights on per-step adapter reload** (`python/sglang/srt/lora/lora_manager.py`, `python/sglang/srt/lora/mem_pool.py`): in RL colocate serving, each step pushes a fresh adapter uid via unload + load, but the rollout kept serving the old weights. Root cause: unload deleted the manager-side bookkeeping while leaving the mem-pool's `uid_to_buffer_id` entry dangling, so the next load skipped the in-place buffer copy in `prepare_lora_batch` and the cuda-graph-captured buffer kept the previous step's weights. Fix: new `LoRAMemoryPool.free_lora()` (called from the unload path) releases the buffer slot, eviction-policy entry, and `buffer_id_to_uid` mapping, so the next load re-copies into the same fixed-address slot — cuda-graph-replay-safe, mirroring the existing eviction path.

- **Shared-outer MoE-LoRA buffer-load crash** (`python/sglang/srt/lora/mem_pool.py::load_lora_weight_to_buffer`): loading an adapter under `--experts-shared-outer-loras` either raised `TypeError` (`... [expert_id] = name` on a `None` cache_keys dict) or silently clobbered already-loaded weights. Root cause: under shared-outer, one side of each projection is a shared 3D tensor while the other is a per-expert dict (fc1 = shared A + per-expert B, fc2 the opposite), but the per-expert init keyed all four dicts (A/B buffers and cache_keys) off `temp_A_buffer is None` — leaving the per-expert side's cache_keys as `None`, or overwriting the shared 3D side the `dim()==3` branch had populated. Fix: initialize each side's buffer and cache_keys independently, with asserts enforcing exactly one layout (shared 3D vs per-expert dict) per projection side.

## New features

- **DSA indexer LoRA targets for GLM-5.1 / DeepSeek-V3.2-family models** (#28110): `wq_b`, `wk`, and `weights_proj` are now accepted in `--lora-target-modules` (added to `SUPPORTED_LORA_TARGET_MODULES` in `python/sglang/srt/utils/common.py`) and normalized to parent-qualified names `indexer.wq_b` / `indexer.wk` / `indexer.weights_proj`, since the bare leaf names collide with unrelated modules in other model families (e.g. DeepSeek-V4 attention `wq_b`, Pixtral vision `wk`).
  - `python/sglang/srt/lora/utils.py`: `get_hidden_dim` shapes for the three indexer projections (via `get_dsa_index_n_heads` / `get_dsa_index_head_dim`); the new `DSA_INDEXER_LORA_NAMES` set is registered as replicated linears and known targets; `auto_detect_lora_target_modules` only picks these leaf names up when the module path proves an `indexer` parent.
  - `python/sglang/srt/lora/lora_manager.py`: module-to-target matching now also checks the last two path components so `indexer.*`-qualified targets resolve.
  - `python/sglang/srt/layers/attention/dsa/dsa_indexer.py`: when `weights_proj` is LoRA-wrapped, the indexer uses an eager module call (wrapper owns base + delta) instead of the fused head-gate paths in both the dual-stream decode and standard branches, and raises an explicit `RuntimeError` if combined with piecewise CUDA graph (see notes).

## Validation

- The net diff was verified to be exactly the five changes above; an experimental `lora_checksum` WeightChecker action was added and reverted on this branch and does not appear in the net diff.
- MoE-expert LoRA (per-expert layout) was validated end-to-end on a 5-layer GLM MoE toy model with EP=8 in a colocate RL run: trainer/rollout parity abs_diff ≈ 0.0104, train↔rollout KL ≈ 1.15e-4, no cuda-graph crash.
- The dp-attention cuda-graph IMA, the `moe_dense_tp_size=1` LoRA-B sizing crash, and the shared-outer buffer-load `TypeError` were all reproducible in GLM-5 LoRA RL rollouts before their respective fixes and no longer occur with them.
- The adapter-unload fix was isolated during a train↔rollout weight-parity investigation of per-step adapter refresh: without it, the served (cuda-graph) buffers keep the previous step's weights after a fresh-uid reload; with it, each reload's weights are served.

## Notes for reviewers

- `indexer.weights_proj` LoRA is **incompatible with piecewise CUDA graph** — the indexer raises a descriptive `RuntimeError` telling the user to drop the prefill cuda-graph backend override or remove `indexer.weights_proj` from the targets, rather than silently applying base-only weights via `logits_head_gate_pcg`.
- Memory cost: the MoE-LoRA per-token routing buffers now scale with `max_bs * attn_dp_size` when dp-attention is enabled, and `virtual_experts.py` keeps the worst-case padded routing allocation instead of trimming — both are deliberate trades for cuda-graph safety.
- The DP-gathered-tail adapter broadcast assumes a single active adapter per batch (the colocate-RL case) but is applied **unconditionally**: it copies the last per-rank token's adapter id over the tail whenever the gathered count exceeds the per-rank count. A multi-adapter batch under dp-attention would therefore get the last request's adapter id (not `-1`) on its gathered tail — that combination is outside the validated colocate-RL scope and would need a single-adapter guard before being relied on.
- The replicated-column-parallel probe in `mem_pool.py` walks `base_model.named_modules()` once per `(module_name, layer_idx)` and caches the result; it falls back to the old TP-divided sizing whenever no matching base module is found.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01Coq2vP8FEpyXMxXxdqocCX















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28628101950](https://github.com/sgl-project/sglang/actions/runs/28628101950)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28628101890](https://github.com/sgl-project/sglang/actions/runs/28628101890)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
