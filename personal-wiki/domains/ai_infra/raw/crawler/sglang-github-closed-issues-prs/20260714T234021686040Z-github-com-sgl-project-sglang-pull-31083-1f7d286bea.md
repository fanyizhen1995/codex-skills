---
source_id: sglang-github-closed-issues-prs
title: '[Cherry-pick to release/v0.5.15] Stabilize GLM-5.2 MTP IndexShare across PD
  and CUDA graph replay (#30839)'
canonical_url: https://github.com/sgl-project/sglang/pull/31083
captured_at: '2026-07-14T23:40:21.686040+00:00'
content_hash: 1f7d286beaef557f5b8cbe1c70fd5fcc6e4857c5ae097f4701eb362770779d9c
---
# [Cherry-pick to release/v0.5.15] Stabilize GLM-5.2 MTP IndexShare across PD and CUDA graph replay (#30839)

URL: https://github.com/sgl-project/sglang/pull/31083
State: closed
Labels: deepseek, speculative-decoding
Closed at: 2026-07-14T02:37:15Z
Merged at: 2026-07-14T02:37:15Z

Backport of #30839 to `release/v0.5.15`.

Structured as two commits to stay conflict-free against the release branch:

1. **Reapply #29787** — reverts the release-branch revert #30842, reinstating the GLM-5.2 MTP IndexShare draft-extend anchor that this fix builds on.
2. **Squashed backport of #30839** — the stabilization work itself.

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

🤖 Generated with [Claude Code](https://claude.com/claude-code)



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29295651002](https://github.com/sgl-project/sglang/actions/runs/29295651002)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29295650791](https://github.com/sgl-project/sglang/actions/runs/29295650791)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
