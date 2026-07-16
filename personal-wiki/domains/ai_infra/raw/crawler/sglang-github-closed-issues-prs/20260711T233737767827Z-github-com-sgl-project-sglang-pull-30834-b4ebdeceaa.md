---
source_id: sglang-github-closed-issues-prs
title: '[cuda-graph] Size breakable-graph shared buffer from warmup output; slice
  by produced row count'
canonical_url: https://github.com/sgl-project/sglang/pull/30834
captured_at: '2026-07-11T23:37:37.767827+00:00'
content_hash: b4ebdeceaa5a178699a9894bffd0c3b3a44497d9081f94c363b82a818bd9ff94
---
# [cuda-graph] Size breakable-graph shared buffer from warmup output; slice by produced row count

URL: https://github.com/sgl-project/sglang/pull/30834
State: closed
Labels: run-ci
Closed at: 2026-07-11T17:41:45Z
Merged at: 2026-07-11T17:41:45Z

## Motivation

`BreakableCudaGraphBackend.capture_one` aliases the first capture's output tensor as the shared output buffer and slices every capture's output by the shape-key size. This assumes the graph body always produces exactly `shape_key.size` leading rows. A body that shards or prunes its output along dim 0 (e.g. a model-level sequence-parallel scheme that keeps hidden states sharded through the captured region and gathers them later) produces fewer rows, so:

- the shared buffer, created by aliasing the first capture's (possibly sharded) output, can be too small for later captures, and
- the stored output view is sliced to the wrong row count.

## Modifications

- Allocate the shared output buffer up front from the warmup output, sized to the full shape-key size of the first capture (preserving the existing assumption that the first capture is the largest), instead of aliasing the first capture's output tensor.
- Copy and slice each capture's output by the row count the body actually produced (`_output_rows`, clamped to the shape-key size), so sharded/pruned outputs get correctly sized views and full outputs behave exactly as before.

## Testing

Validated on an internal deployment: CUDA-graph capture/replay with a model-level SP scheme returning sharded outputs from the captured region, plus no-regression runs with standard full-row outputs. In this environment I ran `python3 -m py_compile`, black, and isort on the changed file; CI will exercise the graph backends.

## Original commits

- `3f1d32f1c`

— Claude







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29138701070](https://github.com/sgl-project/sglang/actions/runs/29138701070)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29138700966](https://github.com/sgl-project/sglang/actions/runs/29138700966)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
