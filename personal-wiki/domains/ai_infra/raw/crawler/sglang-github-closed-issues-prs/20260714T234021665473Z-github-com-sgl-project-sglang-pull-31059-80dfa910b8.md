---
source_id: sglang-github-closed-issues-prs
title: '[Mamba] Support configurable conv-window layouts'
canonical_url: https://github.com/sgl-project/sglang/pull/31059
captured_at: '2026-07-14T23:40:21.665473+00:00'
content_hash: 80dfa910b8112c0307300bd55ff05b805a5f07366c4fac17e2130ac6ee65fd09
---
# [Mamba] Support configurable conv-window layouts

URL: https://github.com/sgl-project/sglang/pull/31059
State: closed
Labels: 
Closed at: 2026-07-14T21:41:11Z
Merged at: 2026-07-14T21:41:11Z

## Motivation

The speculative Mamba conv-window deduplication currently assumes the sliding-window dimension is the trailing axis. Allowing a pool subclass to select that axis lets alternate state layouts reuse the same allocation logic without duplicating the request-pool constructor.

## Modifications

- Add a configurable `MambaPool.conv_window_axis`, defaulting to the existing trailing-axis layout.
- Extract deduplicated physical-buffer/view construction into an axis-aware helper.
- Add a `mamba_pool_cls` construction hook to `HybridReqToTokenPool`.

The default physical shape, view shape, and strides are unchanged.

## Accuracy Tests

- `pre-commit run --files python/sglang/srt/mem_cache/memory_pool.py --show-diff-on-failure`
- `test_mamba_pool_deduplicated_conv_window_axis` (1 passed on CUDA): validates physical/view shapes, per-step slices, overlap consistency, and storage aliasing for the `(K-1, dim)` layout.

## Speed Tests and Profiling

Not run. This only affects pool initialization, and the default allocation and view layout remain unchanged.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). (No documentation changes needed.)
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). (Not performance-sensitive.)
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:warning: [Run #29277449447](https://github.com/sgl-project/sglang/actions/runs/29277449447)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:warning: [Run #29277448438](https://github.com/sgl-project/sglang/actions/runs/29277448438)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
