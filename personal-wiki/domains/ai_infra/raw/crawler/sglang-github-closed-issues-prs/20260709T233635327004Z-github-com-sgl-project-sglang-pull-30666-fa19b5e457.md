---
source_id: sglang-github-closed-issues-prs
title: Fix GLM DSA CP helper imports
canonical_url: https://github.com/sgl-project/sglang/pull/30666
captured_at: '2026-07-09T23:36:35.327004+00:00'
content_hash: fa19b5e457e52cae72f8e9110773f315181c80f324ec6a85728ed34e0836dce8
---
# Fix GLM DSA CP helper imports

URL: https://github.com/sgl-project/sglang/pull/30666
State: closed
Labels: 
Closed at: 2026-07-09T13:55:01Z
Merged at: 

## Summary

Fixes the GLM DSA cache layer-split helpers so non-CP / layer-split-disabled serving does not crash while sizing the KV pool.

- return early before importing CP rank/size helpers when DSA cache layer split is disabled
- use the current attention-CP distributed APIs instead of the removed `dp_attention.get_attention_cp_*` helpers

Fixes #30663
Fixes #30665

## Testing

- `python3 -m py_compile python/sglang/srt/layers/cp/utils.py`
- targeted disabled-path check for `get_glm_dsa_cp_layer_shard_info` and `get_glm_dsa_layer_split_effective_num_layers`
- targeted enabled-path check with mocked CP rank/size
- `pre-commit run ruff --files python/sglang/srt/layers/cp/utils.py`
- `pre-commit run isort --files python/sglang/srt/layers/cp/utils.py`
- `pre-commit run black-jupyter --files python/sglang/srt/layers/cp/utils.py`
- verified GLM-5.2 FP8 DP-attention server can launch with the cookbook high-throughput shape







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29023110856](https://github.com/sgl-project/sglang/actions/runs/29023110856)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29023111451](https://github.com/sgl-project/sglang/actions/runs/29023111451)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
