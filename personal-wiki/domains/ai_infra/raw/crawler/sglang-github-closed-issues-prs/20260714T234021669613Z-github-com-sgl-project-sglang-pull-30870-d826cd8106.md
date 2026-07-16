---
source_id: sglang-github-closed-issues-prs
title: Avoid TileLang CUDA runtime pollution
canonical_url: https://github.com/sgl-project/sglang/pull/30870
captured_at: '2026-07-14T23:40:21.669613+00:00'
content_hash: d826cd8106aaac1bcd5b2b61900fc3878c0887395e1fe654928250a26fa31ce9
---
# Avoid TileLang CUDA runtime pollution

URL: https://github.com/sgl-project/sglang/pull/30870
State: closed
Labels: deepseek, run-ci
Closed at: 2026-07-14T14:30:28Z
Merged at: 2026-07-14T14:30:28Z

## Summary
- defer DeepSeek-V4’s TileLang-backed MHC import until a DeepSeek-V4 forward needs it
- remove an unused TileLang import from the DeepSeek-V4 RoPE module
- choose the real CUDA runtime rather than TileLang’s `libcudart_stub.so` when resolving CUDA IPC / collective symbols
- handle deleted library mappings and expose MHC operations with named fields

## Before / after behavior
This is a startup/correctness enablement fix, not a microbenchmark optimization: **before**, importing the model registry could resolve TileLang’s CUDA stub and make unrelated Qwen3-VL Hopper startup fail during CUDA IPC / FlashInfer collective workspace initialization. **after**, the real `libcudart.so` is selected and the server reaches readiness. There is no meaningful pre-fix serving-latency baseline to report.

## Validation
- pre-commit on all changed files
- registered CUDA tests cover TileLang-stub preference and `/proc/self/maps` paths with ` (deleted)`.



























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29308952241](https://github.com/sgl-project/sglang/actions/runs/29308952241)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29308952156](https://github.com/sgl-project/sglang/actions/runs/29308952156)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
