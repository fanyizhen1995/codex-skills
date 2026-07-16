---
source_id: sglang-github-closed-issues-prs
title: Enable breakable prefill CUDA graph for DP attention
canonical_url: https://github.com/sgl-project/sglang/pull/30898
captured_at: '2026-07-13T23:40:05.192134+00:00'
content_hash: 19b02fa45fb336a852c71a6ddf85de768463cc0229ec83f7a50c7f2dd11c8a59
---
# Enable breakable prefill CUDA graph for DP attention

URL: https://github.com/sgl-project/sglang/pull/30898
State: closed
Labels: deepseek, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-13T00:10:05Z
Merged at: 2026-07-13T00:10:05Z

## Summary

- Allow breakable prefill CUDA graph replay to use consistent DP padding across ranks.
- Preserve non-padded token accounting through prefill graph capture and replay.
- Carry prefill logprob metadata through breakable CUDA graph replay.

## Testing

- `python3 -m py_compile python/sglang/srt/managers/scheduler_components/dp_attn.py python/sglang/srt/model_executor/cuda_graph_buffer_registry.py python/sglang/srt/model_executor/forward_batch_info.py python/sglang/srt/model_executor/runner/prefill_cuda_graph_runner.py python/sglang/srt/model_executor/runner_utils/buffers.py python/sglang/srt/server_args.py test/registered/unit/model_executor/test_cuda_graph_buffer_registry.py`
- `with-proxy uv run pre-commit run --files python/sglang/srt/managers/scheduler_components/dp_attn.py python/sglang/srt/model_executor/cuda_graph_buffer_registry.py python/sglang/srt/model_executor/forward_batch_info.py python/sglang/srt/model_executor/runner/prefill_cuda_graph_runner.py python/sglang/srt/model_executor/runner_utils/buffers.py python/sglang/srt/server_args.py test/registered/unit/model_executor/test_cuda_graph_buffer_registry.py`
- `with-proxy uv run pytest test/registered/unit/model_executor/test_cuda_graph_buffer_registry.py -q`

## Original commits

- `624a9b21af`



























































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29193679942](https://github.com/sgl-project/sglang/actions/runs/29193679942)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29193679875](https://github.com/sgl-project/sglang/actions/runs/29193679875)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
