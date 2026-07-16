---
source_id: sglang-github-closed-issues-prs
title: Tune VLM MoE paths
canonical_url: https://github.com/sgl-project/sglang/pull/30866
captured_at: '2026-07-12T23:38:53.058445+00:00'
content_hash: f53f1a3e9cfc40c9b8139fdb29e4947b2bd4907cea7fd292214b0dc87dd61ba0
---
# Tune VLM MoE paths

URL: https://github.com/sgl-project/sglang/pull/30866
State: closed
Labels: run-ci
Closed at: 2026-07-12T00:35:59Z
Merged at: 2026-07-12T00:35:59Z

## Summary

- add tuned Triton MoE configurations for Qwen3-VL and Kimi-VL on H100, plus Qwen3-VL on H200
- reuse a tuned up-projection configuration when a separate down-projection configuration is unavailable
- add Kimi-VL architecture recognition to the MoE tuning helper and configurable tuner batch sizes/search spaces
- align the FlashInfer all-reduce microbenchmark precision with the serving path

## Root cause

The VLM MoE shapes were missing current-Triton hardware configurations, causing heuristic or older-config fallback. Kimi-VL was also not recognized by the generic tuning helper.

## Performance data

Isolated H100 Kimi-VL MoE (`E=16`, `N=1408`) tuning improves the selected Triton configurations by **19.8–47%** across the measured batch-size sweep. End-to-end Kimi-VL H100 TP=4 at request-rate=8 improves from **41.59 ms to 40.95 ms mean E2E** (**1.6%**); this deliberately reports the smaller application-level effect rather than extrapolating the microbenchmark gain.

The added Qwen configurations cover H100 TP=4 (`E=32`, `N=768`) and H200 TP=1 (`E=128`, `N=768`).

## Validation

- H100 CUDA MoE configuration tests (2 passed)
- `ruff format --check`, `ruff check`, `git diff --check`, and project pre-commit hooks

## Impact

Uses reproducible tuned configuration selection instead of fallback paths for the measured VLM MoE workloads.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29152897359](https://github.com/sgl-project/sglang/actions/runs/29152897359)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29152897303](https://github.com/sgl-project/sglang/actions/runs/29152897303)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
