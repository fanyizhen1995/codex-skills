---
source_id: sglang-github-closed-issues-prs
title: Fix image benchmark backend parity
canonical_url: https://github.com/sgl-project/sglang/pull/30867
captured_at: '2026-07-15T23:40:28.384277+00:00'
content_hash: 79e98f0b162d2661fd7ab1f981878364cb8ba6b12a497972b9d0399c801250d3
---
# Fix image benchmark backend parity

URL: https://github.com/sgl-project/sglang/pull/30867
State: closed
Labels: run-ci
Closed at: 2026-07-15T02:11:22Z
Merged at: 2026-07-15T02:11:22Z

## Summary

- allow the image benchmark dataset to use OpenAI-compatible `vllm-chat` and `lmdeploy-chat` backends
- pass raw text to every chat-completions backend so each server applies its own chat template exactly once
- add backend-coverage tests for image sampling

## Before / after behavior
This PR intentionally does not change the serving path, so there is no before/after performance delta. **Before**, the image benchmark cannot target vLLM/LmDeploy chat endpoints. **After**, the same sampled images, seed, text, and output length can be sent to all three chat-completions backends without double-applying a template.

## Validation

- `PYTHONPATH=python pytest -q test/registered/bench_fn/test_benchmark_datasets_api.py -k image_sampler` (2 passed)
- `ruff format --check`, `ruff check`, `git diff --check`, and project pre-commit hooks

## Impact

Enables apples-to-apples image TTFT and throughput comparisons across SGLang, vLLM, and LMDeploy chat servers.



































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29308883102](https://github.com/sgl-project/sglang/actions/runs/29308883102)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29308882920](https://github.com/sgl-project/sglang/actions/runs/29308882920)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
