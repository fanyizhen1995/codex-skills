---
source_id: sglang-github-closed-issues-prs
title: 'sgl-kernel: bump sgl-attn for varlen num_splits OOM fix'
canonical_url: https://github.com/sgl-project/sglang/pull/29551
captured_at: '2026-07-03T02:13:21.705363+00:00'
content_hash: e7a0c5be562c90fbf94568e8c9986ce62cdcb28aea6383132b1877b9d6ac6bde
---
# sgl-kernel: bump sgl-attn for varlen num_splits OOM fix

URL: https://github.com/sgl-project/sglang/pull/29551
State: closed
Labels: sgl-kernel, run-ci, run-ci-extra
Closed at: 2026-07-02T04:13:54Z
Merged at: 2026-07-02T04:13:54Z

### Motivation

Bumps the vendored `sgl-attn` pin to `f89bc23` to pull in the varlen `get_num_splits` heuristic fix ([sgl-project/sgl-attn#46](https://github.com/sgl-project/sgl-attn/pull/46)).

A varlen batch of many short segments (NSA-style `cu_seqlens_q = arange(N+1)`) made the previous "pretend batch=1" upper bound under-count `total_mblocks`, so `get_num_splits` over-split and the fp32 `out_accum` workspace blew up (OOM, observed in DeepSeek-V3.2 NSA prefill). The fix sizes the heuristic from the real `total_q` for varlen while keeping the non-varlen path byte-identical.

Net delta vs the current pin (`65c54cc5`) is exactly that one commit.

### Modifications

- `sgl-kernel/CMakeLists.txt`: bump `repo-flash-attention` pin `65c54cc5` → `f89bc23` (+ updated `URL_HASH`).
- `sgl-kernel/tests/test_flash_attention.py`: move the regression test here (per the sgl-attn#46 review) — a many-short-segment varlen case with large K that exercises the `num_splits=0` heuristic path and checks numerics against a per-segment reference.

### Accuracy Test

Built sgl-kernel with the new pin on H100 (sm90, torch 2.11+cu130) and ran the regression test:

```
1 passed
```

### Checklist

- [x] Format your code according to the [Code Formatting with Pre-Commit](https://docs.sglang.ai/developer_guide/contribution_guide.html#code-formatting-with-pre-commit).
- [x] Provide accuracy results.

























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28434447384](https://github.com/sgl-project/sglang/actions/runs/28434447384)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28434447096](https://github.com/sgl-project/sglang/actions/runs/28434447096)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
