---
source_id: sglang-github-closed-issues-prs
title: '[bug-fix] Stabilize GLM-5.2 MTP IndexShare across PD and CUDA graph replay'
canonical_url: https://github.com/sgl-project/sglang/pull/30839
captured_at: '2026-07-14T23:40:21.683488+00:00'
content_hash: 7f7f00ec6ce637aaf85cbccc1ef583a9ff436adfe46ed273c5e8c3f6ef7dcb18
---
# [bug-fix] Stabilize GLM-5.2 MTP IndexShare across PD and CUDA graph replay

URL: https://github.com/sgl-project/sglang/pull/30839
State: closed
Labels: high priority, deepseek, run-ci, bypass-fastfail, run-ci-extra, post version patch
Closed at: 2026-07-14T02:37:08Z
Merged at: 2026-07-14T02:37:08Z

## Motivation

This PR makes GLM-5.2 MTP IndexShare reliable across PD disaggregation, context parallelism, overlap scheduling, batch splitting, and CUDA graph replay. It preserves the correct draft-extend DSA seed across draft steps, avoiding redundant indexer computation without reusing stale or misaligned indices. This improves proposal consistency, acceptance length stability, and inference performance.

This is a follow-up to #29787. The optimization remains gated to EAGLE with `speculative_eagle_topk == 1`, `index_share_for_mtp_iteration=true`, and a valid `index_topk`.

## Modifications

- Transfer per-request DSA top-k seeds from prefill nodes to decode nodes in PD disaggregation, with explicit invalid sentinels and retry-state cleanup.
- Unify eager and CUDA-graph seed capture through `LogitsProcessorOutput`, including correct last-token extraction after CP gather/reordering.
- Preserve seed alignment across context parallelism and Two-Batch Overlap splitting.
- Keep reusable seed state across copied forward batches and graph capture/replay.
- Track seed validity in `FutureMap` to prevent stale overlap/PD state, and fall back to eager recomputation when no valid seed is available.
- Refresh paged-MQA schedules, top-k-v2 plans, and per-step metadata during multi-step DSA graph replay.
- Resolve DSA context-parallel aliases from the effective attention backend.















































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29295157846](https://github.com/sgl-project/sglang/actions/runs/29295157846)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #29295157815](https://github.com/sgl-project/sglang/actions/runs/29295157815)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
