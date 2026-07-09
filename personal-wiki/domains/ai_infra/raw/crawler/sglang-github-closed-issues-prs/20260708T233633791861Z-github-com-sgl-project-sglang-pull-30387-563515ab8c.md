---
source_id: sglang-github-closed-issues-prs
title: Fix zero expert routed ids for MoE backends
canonical_url: https://github.com/sgl-project/sglang/pull/30387
captured_at: '2026-07-08T23:36:33.791861+00:00'
content_hash: 563515ab8c59d312277ef6ae1770d99f42c55aea3b035eec5901602da0ca6db0
---
# Fix zero expert routed ids for MoE backends

URL: https://github.com/sgl-project/sglang/pull/30387
State: closed
Labels: run-ci
Closed at: 2026-07-08T13:23:26Z
Merged at: 2026-07-08T13:23:26Z

## Summary

- Keep zero-expert routed ids valid before entering the routed MoE backend.
- Use expert id `0` with zero scale instead of `-1` for zero-expert selections.
- Add a CUDA unit test for the zero-expert preprocessing mutation and identity output.

## Why

LongCat-Flash zero experts are represented as top-k ids `>= num_experts`. The previous preprocessing converted those ids to `-1` and zeroed their scales before calling the routed MoE backend. Some MoE kernels still treat the ids as gather/sort inputs and do not handle negative ids reliably, which can surface as CUDA illegal memory access under concurrent serving.

Using a valid expert id with zero scale is mathematically equivalent for the routed-expert contribution and avoids passing negative ids to those kernels.

## Validation

- H200: `python3 -m black --check python/sglang/srt/layers/moe/ep_moe/kernels.py test/registered/moe/test_zero_experts.py`
- H200: `PYTHONPATH=/data/repos/sglang-zero-expert-fix/python pytest -q test/registered/moe/test_zero_experts.py`: `1 passed`
- H200 CI-style entry: `PYTHONPATH=/data/repos/sglang-zero-expert-fix/python python3 test/registered/moe/test_zero_experts.py`: `OK`
- Investigation note: disabling CUDA graph did not avoid the LongCat-Flash-Lite FP8 serving crash; after this id remap, TP8 serving with CUDA graph enabled completed GSM8K without CUDA illegal memory access.

























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28860955308](https://github.com/sgl-project/sglang/actions/runs/28860955308)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28862814898](https://github.com/sgl-project/sglang/actions/runs/28862814898)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
