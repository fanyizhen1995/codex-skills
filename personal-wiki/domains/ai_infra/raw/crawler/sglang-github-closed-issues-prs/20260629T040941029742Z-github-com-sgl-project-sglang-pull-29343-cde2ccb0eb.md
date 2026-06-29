---
source_id: sglang-github-closed-issues-prs
title: '[dflash] fa3/fa4: device-side page table; drop seq_lens_cpu D2H sync'
canonical_url: https://github.com/sgl-project/sglang/pull/29343
captured_at: '2026-06-29T04:09:41.029742+00:00'
content_hash: cde2ccb0eb0ab44e1b32aac550e813072fc6d885da93c814d7583dffdc1e0799
---
# [dflash] fa3/fa4: device-side page table; drop seq_lens_cpu D2H sync

URL: https://github.com/sgl-project/sglang/pull/29343
State: closed
Labels: high priority, run-ci, run-ci-extra
Closed at: 2026-06-29T01:06:34Z
Merged at: 2026-06-29T01:06:34Z

## Summary

- Build the page table on-device via `build_trtllm_mha_page_table` (Triton kernel from #28106, self-guards per request on `cache_seqlens`) in the cuda-graph decode / draft-decode / target-verify paths — no host-side `seq_lens_cpu.max().item()` for page-table sizing
- Set `needs_cpu_seq_lens = not is_dflash()` so **only dflash** opts out of the CPU mirror; EAGLE/MTP/standalone keep `True` until #29589 adds preallocated tree-mask scratch
- `max_seq_len_k` uses the static `max_context_len` bound on device-build paths (fa3 kernel never reads it — only `cache_seqlens` + `page_table`)
- `_host_max_seq_len` helper for cold paths (topk>1, draft-extend, prefill-aware SWA) that still need a host max — falls back to `max_context_len` when `seq_lens_cpu` is `None`
- Test: page-table write-boundedness for the no-host-max path

## Background

PR #29232 unified dflash's seq_lens CPU-value relay through the FutureMap. But dflash+fa3 still paid a `resolve_seq_lens_cpu` D2H + `synchronize()` (~370us/iter of forward occupancy) because fa3 declared `needs_cpu_seq_lens = True` and read `seq_lens_cpu.max().item()` for dynamic page-table sizing.

trtllm_mha solved this in #28106 with a device-side page-table builder. This PR reuses that pattern for fa3, scoped to dflash only.

## Follow-ups

- **#29589**: extends sync-free to all spec algos (EAGLE/MTP) via preallocated `cuda_graph_custom_mask` + unconditional `needs_cpu_seq_lens = False`
