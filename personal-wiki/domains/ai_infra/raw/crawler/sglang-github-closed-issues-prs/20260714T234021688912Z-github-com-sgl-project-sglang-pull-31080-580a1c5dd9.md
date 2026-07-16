---
source_id: sglang-github-closed-issues-prs
title: '[CI] Use torch.testing.assert_close in custom-all-reduce test (~1400x faster
  compare)'
canonical_url: https://github.com/sgl-project/sglang/pull/31080
captured_at: '2026-07-14T23:40:21.688912+00:00'
content_hash: 580a1c5dd956a50de7ec817bfac9f626fdff04c11b6670be4e2acae4c905bd3e
---
# [CI] Use torch.testing.assert_close in custom-all-reduce test (~1400x faster compare)

URL: https://github.com/sgl-project/sglang/pull/31080
State: closed
Labels: run-ci
Closed at: 2026-07-14T00:53:20Z
Merged at: 2026-07-14T00:53:20Z

## Motivation

`triton.testing.assert_close` copies both tensors to CPU (bf16→fp32 upcast + `.cpu().numpy()`) and compares with single-threaded numpy. This test runs it 16x per parametrization on every rank, on tensors up to 4x2M — measured **142.9 ms vs 0.1 ms** per compare against `torch.testing.assert_close` on an idle H100 (worse under 8-rank CPU contention). A major contributor to this file's CI slowness and its super-linear scaling with world size (98s @ 2 GPUs → 209s @ 4 → ~625s @ 8).

## Modification

Swap to `torch.testing.assert_close` (on-GPU compare). Drop-in: `atol=0, rtol=0` exact equality, same dtype/device, no NaNs. Credit to Ziyi Xu for the diagnosis.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29293184294](https://github.com/sgl-project/sglang/actions/runs/29293184294)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29293192894](https://github.com/sgl-project/sglang/actions/runs/29293192894)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
