---
source_id: sglang-github-closed-issues-prs
title: Fix VLM runtime stability
canonical_url: https://github.com/sgl-project/sglang/pull/30865
captured_at: '2026-07-11T23:37:37.768554+00:00'
content_hash: 837cf682dad383be9ae0c68269a274b8436b6787d2f38d500dcf174f66acf023
---
# Fix VLM runtime stability

URL: https://github.com/sgl-project/sglang/pull/30865
State: closed
Labels: Multi-modal, deepseek, piecewise-cuda-graph
Closed at: 2026-07-11T12:03:18Z
Merged at: 

## Summary

- make mRoPE and forward-batch metadata dynamic for piecewise CUDA graphs
- avoid capture-stream misuse during runtime recompilation and preserve Kimi deepstack warmup inputs
- fix Kimi MoonViT DP encoder behavior for TP=1 and avoid DP/TP CUDA-graph capture interference
- remove TileLang import side effects from the Qwen/DeepSeek-V4 runtime path

## Root cause

VLM-specific metadata and optional deepstack inputs were specialized by CUDA-graph warmup. Kimi's TP=1 DP vision path also returned a list of image tensors where the projector requires a tensor.

## Validation

- H100 CUDA: Kimi encoder tests (6 passed)
- H100 CUDA: broader VLM/MoE regression set (67 passed)
- `ruff format --check`, `ruff check` (with repository legacy import-style exclusions), `git diff --check`, and project pre-commit hooks

## Impact

Eliminates runtime PCG recompiles for tested 128/256/512 token VLM shapes and restores Kimi-VL TP=1 serving.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
