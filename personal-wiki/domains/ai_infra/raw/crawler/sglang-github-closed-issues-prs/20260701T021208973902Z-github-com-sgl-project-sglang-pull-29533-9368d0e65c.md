---
source_id: sglang-github-closed-issues-prs
title: 'feat(mem_cache): page-major (layer-major within a page) KV/state layout'
canonical_url: https://github.com/sgl-project/sglang/pull/29533
captured_at: '2026-07-01T02:12:08.973902+00:00'
content_hash: 9368d0e65c38a7401e2f432da5f441495d0e18a562f7c189e86a82f81bfbaed8
---
# feat(mem_cache): page-major (layer-major within a page) KV/state layout

URL: https://github.com/sgl-project/sglang/pull/29533
State: closed
Labels: documentation, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-06-29T21:49:55Z
Merged at: 2026-06-29T21:49:55Z

## Motivation

SGLang stores the KV cache (and Mamba conv/SSM state) as **per-layer tensors** — layer 0's slots, then layer 1's slots, etc. (a *layer-major* layout). Each token's K/V for a given layer is contiguous, but a single token/page is scattered across `num_layers` separate allocations.

This PR adds an **opt-in** physical layout, `--enable-page-major-kv-layout`, that flips the outermost axis to the **page**: each page's whole depth — all layers' K/V (and all Mamba conv/temporal state) — lives in one contiguous byte buffer, laid out layer-major *within* the page. At `page_size=1` this is a per-token envelope. Co-locating a page's whole depth is a building block for page-granular KV operations (movement, transfer, offload, allocation) and improves locality for those paths.

The layout is **off by default and behavior-preserving when off** — the hot paths are byte-identical (the page-aware Triton kernels constexpr-fold to the legacy addressing at `page_size=1`).

## Modifications

- **`mem_cache/layout/page_major.py`** — standalone strided-view builders (`build_page_major_mha_views`, `build_page_major_mamba_views`) + byte geometry; hold no allocator state.
- **`PageMajorMHATokenToKVPool`** — a subclass of `MHATokenToKVPool` (not in-class branching) selected via new `_store_kv_layer` / `_move_kv_cache_impl` template hooks. Layout-incompatible inherited methods (contiguous-buf-infos, CPU offload, prefix-commit) `raise NotImplementedError` instead of silently mis-indexing the 4-D strided views. `MambaPool` gains an envelope branch for conv/temporal state.
- **Triton decode/extend + `store_cache_4d` kernels** — page-aware strides behind a `PAGE_SIZE` constexpr; at `page_size=1` the page math is dead-code-eliminated, so the SASS is identical to today.
- **GDN prefill gather/scatter** (`gdn_backend.forward_extend`) — the prefill conv (`causal_conv1d_fwd`) and `chunk_gated_delta_rule` kernels write state back assuming a contiguous slot layout; under the strided envelope they silently dropped the write. The hybrid prefill now runs on contiguous per-sequence copies and scatters the updated state back. (`TODO(ch-wan)` left to make those kernels stride-aware and drop the copies.)
- **`server_args`** — `--enable-page-major-kv-layout` flag + a validator requiring the Triton attention / linear-attn / Mamba backends; `model_runner_kv_cache_mixin` routes the layout into the plain-MHA, SWA-hybrid, and Mamba-hybrid pools.
- Removed the dead `enable_kvcache_transpose` parameter (was always `False`).
- **Tests + docs** — kernel parity (`store_cache_4d`, decode/extend), CPU view/move tests, two e2e accuracy tests (gpt-oss, qwen) in the label-gated `extra` suite, and the server-arg doc.

## Accuracy Tests

GSM8K (5-shot/300, Triton backend), page-major vs baseline:

| Model | Path | Baseline | Page-major |
|---|---|---|---|
| Llama-2-7b-chat | plain MHA | 0.243 | **0.243** |
| Qwen3.5-4B | hybrid GDN (Mamba) | 0.863 | **0.863** |
| gpt-oss-20b | hybrid-SWA MoE | 0.56 | 0.52 (within noise; reasoning model underperforms few-shot completion) |

A GDN-prefill state-persistence bug (page-major dropped Qwen3.5 to ~0.61) was found and fixed; the table reflects the fix. A dedicated review confirmed the **disabled path is behavior-preserving** with no measurable overhead.

## Speed Tests and Profiling

Not yet benchmarked — this PR is a layout/correctness foundation, off by default. The `page_size=1` path is a verified no-op (constexpr-folded), so no regression is expected when disabled. Throughput/locality benchmarking of the enabled path is a follow-up.

## Notes / follow-ups

- `--enable-page-major-kv-layout` is not yet supported with fp4 KV cache (asserted) or the speculative-decode target-verify path.
- The GDN prefill still pays a `.contiguous()` gather/scatter under the envelope (`TODO(ch-wan)`); making the conv / `chunk_gated_delta_rule` kernels stride-aware would remove it.

## Checklist

- [x] Format code with pre-commit
- [x] Add unit tests (kernel parity + CPU view/move + e2e accuracy), registered to CI
- [x] Update documentation (`server_arguments.mdx`)
- [x] Accuracy results provided (above); speed benchmarking is a follow-up
- [x] Follow SGLang code style

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28317513541](https://github.com/sgl-project/sglang/actions/runs/28317513541)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28317513466](https://github.com/sgl-project/sglang/actions/runs/28317513466)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
