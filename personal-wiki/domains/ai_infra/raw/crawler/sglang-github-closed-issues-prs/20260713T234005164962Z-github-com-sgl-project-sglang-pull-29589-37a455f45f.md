---
source_id: sglang-github-closed-issues-prs
title: 'fa3/fa4: sync-free for all backends and phases'
canonical_url: https://github.com/sgl-project/sglang/pull/29589
captured_at: '2026-07-13T23:40:05.164962+00:00'
content_hash: 37a455f45fad2c0e6225047484e53f1dc9cee331f624b70181151c44a61ba2e6
---
# fa3/fa4: sync-free for all backends and phases

URL: https://github.com/sgl-project/sglang/pull/29589
State: closed
Labels: run-ci
Closed at: 2026-07-13T20:09:57Z
Merged at: 2026-07-13T20:09:57Z

## Motivation

PR #29343 made fa3 sync-free for the dflash hot path but kept `needs_cpu_seq_lens=True` for EAGLE/MTP to avoid crashing multi-layer eagle's tree-mask sizing. This PR extends sync-free to **all spec algos and all phases**.

## Changes

### 1. Preallocated tree-mask scratch (`cuda_graph_custom_mask`)

Mirror trtllm_mla (#26824): allocate a static FULL_MASK tree-mask buffer in `init_cuda_graph_state` and expose it via `get_verify_buffers_to_fill_after_draft`. `build_tree_kernel_efficient` fills it in-place, so `seq_lens_sum` is **never needed** — no dynamic allocation, no D2H sync.

This was the blocker for EAGLE/MTP: their `build_tree_kernel_efficient` call sized a dynamic tree mask via `seq_lens_sum`, which required the CPU mirror.

- The SWA topk>1 merged page table is widened by `speculative_num_draft_tokens` columns so the static `max_seq_len_k` bound passes its `assert_buffer_fits` check.
- The multi-layer eagle worker gets the same `seq_lens_sum is None` fallback as the single-layer worker (covers `--disable-cuda-graph`, where the scratch is never allocated).

### 2. `needs_cpu_seq_lens = False` unconditionally

With the preallocated tree mask, fa3/fa4 no longer need `seq_lens_cpu` for any spec algo. Removed the dflash-only condition — EAGLE, multi-layer EAGLE, MTP all go GPU-only now.

The multi-layer draft-extend runner now threads `seq_lens_cpu` explicitly through `prepare()`/`replay()` (like `seq_lens_sum`) and passes `None` when the mirror was not published, instead of exposing a stale buffer.

### 3. Eager path sync-free

`init_forward_metadata` (non-cuda-graph) used `seq_lens_cpu.max().item()` in 8 places. Replaced with `eager_max_k` (CPU mirror when published, else static `max_context_len` bound).

Key insight: `max_seq_len_k` never reaches the kernel (`flash_attn_with_kvcache` has no `max_seqlen_k` param) — it only feeds page-table slicing and the scheduler_metadata split heuristic. A static bound is safe (correctness unaffected, `cache_seqlens` caps real reads).

Two exceptions that cannot take the static bound:
- `max_seq_len_q` at the extend branch reaches the kernel — uses `max(extend_seq_lens_cpu)` (always published, sync-free).
- The prefill-aware SWA ratchet needs a true upper bound of the device-side prefill lens — takes a local D2H when the mirror is absent rather than being poisoned to `max_context_len` for the process lifetime.

### 4. CUDA-graph replay: tight bound when the mirror is free

The spec replay paths (draft decode topk>1, target verify topk>1, draft-extend v2) use `seq_lens_cpu.max()` when the mirror is published (e.g. TBO forces it on) and only fall back to the static `max_context_len` bound otherwise — same pattern as the normal-decode branch, so mirror-carrying configs keep tight page-table copies.

## Stacking

Stacked on #29343. fa4 shares the same class — benefits for free.

## Remaining (not in this PR)

- Local attention path (`make_local_attention_virtual_batches`) still has CPU numpy syncs — deferred (only Llama4-class models, separate concern).









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29231421670](https://github.com/sgl-project/sglang/actions/runs/29231421670)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29231421338](https://github.com/sgl-project/sglang/actions/runs/29231421338)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
