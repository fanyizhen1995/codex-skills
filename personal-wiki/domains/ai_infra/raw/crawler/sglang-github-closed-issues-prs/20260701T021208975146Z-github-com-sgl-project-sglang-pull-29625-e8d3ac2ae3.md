---
source_id: sglang-github-closed-issues-prs
title: CUDA graph executable dedup via cudaGraphExecUpdate
canonical_url: https://github.com/sgl-project/sglang/pull/29625
captured_at: '2026-07-01T02:12:08.975146+00:00'
content_hash: e8d3ac2ae3c03cf9bb106b7a8ce87c534d1c4ae88a6c18d1f52541654b772cb4
---
# CUDA graph executable dedup via cudaGraphExecUpdate

URL: https://github.com/sgl-project/sglang/pull/29625
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-06-29T20:56:34Z
Merged at: 2026-06-29T20:56:34Z

## Motivation

When using breakable CUDA graphs (segmented capture), each batch size gets its own set of captured CUDA graph segments. Many of these segments are structurally identical across batch sizes -- same kernels, same topology, same launch parameters -- but each gets a separately instantiated cudaGraphExec. This wastes GPU memory proportional to the number of batch sizes times the number of segments.

## Changes

Introduce CUDA graph executable deduplication: structurally-identical graph segments share a single `cudaGraphExec`, using `cudaGraphExecUpdate` to switch between them at replay time.

### New file: `cuda_graph_dedup_mixin.py`
- **Graph signature**: computes a structural fingerprint of a CUDA graph by walking its nodes in topological order, extracting kernel names, grid/block dims, shared memory, launch attributes, and edge topology.
- **`DedupedCudaGraphRegistry`**: groups captured graphs by signature. First graph in a group instantiates the exec; subsequent graphs verify compatibility via `cudaGraphExecUpdate` on a scratch exec. At seal time the scratch exec is destroyed.
- **`DedupedCudaGraphMixin`**: mixed into `BreakableCudaGraphBackend` to hook capture session begin/end. Manages registry lifecycle and cleanup.

### Modified: `breakable_cuda_graph_backend.py`
- Inherits `DedupedCudaGraphMixin` (MRO before `BaseCudaGraphBackend`)
- `capture_session()` calls `begin_cuda_graph_capture()` / `end_cuda_graph_capture()`
- `capture_one()` passes the active registry to each `BreakableCUDAGraph`
- `cleanup()` calls `self.close()` to destroy dedup registries

### Modified: `breakable_cuda_graph.py`
- `BreakableCUDAGraph.__init__` accepts optional `deduped_cuda_graph` registry
- New `_append_segment()` routes completed segments through dedup registration or plain instantiation
- `BreakableCUDAGraphCapture` uses `torch.cuda.CUDAGraph(keep_graph=True)` when available (needed for `raw_cuda_graph()` access), falls back to standard capture

### Modified: `environ.py`
- New env var `SGLANG_ENABLE_CUDA_GRAPH_DEDUP` (default: `False`)

## How it works

1. During `capture_session`, the mixin creates a `DedupedCudaGraphRegistry`
2. As each segment finishes capture, `_append_segment` calls `registry.register(graph)` which computes the graph signature and either joins an existing group or creates a new one
3. At replay, if the group current raw graph differs from the one being replayed, `cudaGraphExecUpdate` is called to update the shared exec in-place
4. On cleanup, all execs are destroyed and original graph objects are released

## Guarding

- **Off by default**: `SGLANG_ENABLE_CUDA_GRAPH_DEDUP=0`
- **Requires**: `cuda-python` (`cuda.bindings`) and PyTorch with `CUDAGraph(keep_graph=True)` support
- **Incompatible with**: memory saver mode (auto-detected and skipped)
- Falls back gracefully when prerequisites are missing

## Test plan

- [x] Pre-commit hooks pass (isort, ruff, black, codespell)
- [ ] CI: existing breakable CUDA graph tests pass with the feature disabled (default)
- [ ] Manual: `SGLANG_ENABLE_CUDA_GRAPH_DEDUP=1` on a breakable-CG model, verify log line `captured N CUDA graphs, deduped to M execs` where M < N

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28385619687](https://github.com/sgl-project/sglang/actions/runs/28385619687)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28385619434](https://github.com/sgl-project/sglang/actions/runs/28385619434)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
