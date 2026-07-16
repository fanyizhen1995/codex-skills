---
source_id: sglang-github-closed-issues-prs
title: Add VLM prefill profiler ranges
canonical_url: https://github.com/sgl-project/sglang/pull/30871
captured_at: '2026-07-12T23:38:53.056999+00:00'
content_hash: 13b929bc375bb2d87f5739c0fa4dbdb53145a71290c1d9e2073fef761274f13b
---
# Add VLM prefill profiler ranges

URL: https://github.com/sgl-project/sglang/pull/30871
State: closed
Labels: run-ci
Closed at: 2026-07-12T06:07:10Z
Merged at: 2026-07-12T06:07:10Z

## Summary
- add separate `torch.profiler.record_function` ranges for multimodal embedding/ViT work and language-model prefill
- preserve the serving execution path; this only makes the two components directly attributable in profiles

## Before / after behavior
This PR is instrumentation only and has no expected serving performance delta. **Before**, a prefill trace cannot distinguish vision embedding from LLM prefill. **After**, the named ranges attribute the two stages separately (for Qwen3-VL-32B H100 TP=4: about 7.16 ms GPU time in mm embedding/ViT and 57.16 ms in LLM prefill).

## Tests
- pre-commit on the changed file.



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29151977353](https://github.com/sgl-project/sglang/actions/runs/29151977353)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29151977234](https://github.com/sgl-project/sglang/actions/runs/29151977234)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
