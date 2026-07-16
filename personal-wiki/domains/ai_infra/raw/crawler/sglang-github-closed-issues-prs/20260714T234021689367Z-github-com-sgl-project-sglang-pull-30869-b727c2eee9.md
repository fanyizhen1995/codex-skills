---
source_id: sglang-github-closed-issues-prs
title: 'fix: fix Kimi-VL encoder parallelism'
canonical_url: https://github.com/sgl-project/sglang/pull/30869
captured_at: '2026-07-14T23:40:21.689367+00:00'
content_hash: b727c2eee91e0331c7299077db2a5198fdf05b4f34fc160bb8f57742f56b409a
---
# fix: fix Kimi-VL encoder parallelism

URL: https://github.com/sgl-project/sglang/pull/30869
State: closed
Labels: run-ci
Closed at: 2026-07-14T00:44:06Z
Merged at: 2026-07-14T00:44:06Z

## Summary
- wire MoonViT through the existing encoder-DP sharding helper and preserve the TP=1 projector-facing tensor contract
- make MoonViT layers tensor-parallel when encoder DP is disabled, and avoid TP-collective CUDA-graph capture for DP-sharded image work
- eliminate per-layer GPU synchronization for packed attention metadata and bound the serving-time positional interpolation cache
- resolve the language model once before prefill graph setup and cache supported image-processor kwargs

## Before / after behavior
This is primarily a Kimi-VL correctness/enablement change, not a valid before/after throughput benchmark: **before**, Kimi-VL TP=1 encoder-DP returns a list where the projector requires a tensor and fails on serving; **after**, the output is concatenated and the server completes image requests. No cross-engine number is presented as a PR performance result.

## Validation
- pre-commit on all changed files
- registered Kimi-VL encoder/DP, interpolation-cache eviction, ViT capture-context, and HF image-processor tests
- the Kimi-VL entry was intentionally removed from the shared `test_encoder_dp` matrix.



























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29237951501](https://github.com/sgl-project/sglang/actions/runs/29237951501)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29237951515](https://github.com/sgl-project/sglang/actions/runs/29237951515)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
