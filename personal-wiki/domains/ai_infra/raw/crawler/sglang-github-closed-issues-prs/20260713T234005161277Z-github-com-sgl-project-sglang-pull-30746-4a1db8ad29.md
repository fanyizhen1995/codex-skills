---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Fix CUDA graph lookup when padding is disabled'
canonical_url: https://github.com/sgl-project/sglang/pull/30746
captured_at: '2026-07-13T23:40:05.161277+00:00'
content_hash: 4a1db8ad29f8eb028ab32a8333e627ec4f3ec7d0ed81263c6099154f3377654d
---
# [Bugfix] Fix CUDA graph lookup when padding is disabled

URL: https://github.com/sgl-project/sglang/pull/30746
State: closed
Labels: 
Closed at: 2026-07-13T22:12:19Z
Merged at: 

## Motivation

`--disable-cuda-graph-padding` should use a captured CUDA graph for an exact capture size and fall back to eager execution for an uncaptured size.

After CUDA graph backends migrated to typed `ShapeKey` keys, the decode runners still queried `backend.can_run()` with a bare integer (or a legacy PDMux string). The lookup therefore missed every captured graph and silently sent exact-size batches to eager execution.

## Modifications

- Build the decode lookup key with the same `_make_graph_key()` path used by capture and replay, including PDMux stream and LoRA variant fields.
- Use typed shape keys in the EAGLE draft, draft-extend, and multi-layer draft-extend runners as well.
- Add CPU regression coverage for:
  - exact captured size accepted and non-exact size rejected
  - PDMux stream keys
  - LoRA variant keys
  - speculative runner lookups

## Accuracy Tests

This changes graph selection only; model math and outputs are unchanged.

A pure-SGLang GB200 runtime check reproduced the bug before the patch: with graph padding disabled, an exact captured batch reported `cuda graph: False`. With the typed-key patch, the exact batch reported `cuda graph: True`, while non-exact batches correctly remained eager. A latest-container validation is in progress and will be added here.

## Speed Tests and Profiling

The fix restores CUDA graph replay for exact captured batches that previously ran eager. No comparative throughput claim is included yet.

## Checklist

- [x] Format checked with Black.
- [x] Ruff checks pass.
- [x] Added CPU unit tests.
- [ ] CI unit tests.
- [ ] Documentation update is not needed; this restores the documented flag behavior.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29073130379](https://github.com/sgl-project/sglang/actions/runs/29073130379)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29073130214](https://github.com/sgl-project/sglang/actions/runs/29073130214)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
