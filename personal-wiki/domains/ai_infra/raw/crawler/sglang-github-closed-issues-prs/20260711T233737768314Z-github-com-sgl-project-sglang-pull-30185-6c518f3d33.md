---
source_id: sglang-github-closed-issues-prs
title: Support DP attention for breakable prefill CUDA graphs
canonical_url: https://github.com/sgl-project/sglang/pull/30185
captured_at: '2026-07-11T23:37:37.768314+00:00'
content_hash: 6c518f3d33f66180a5a3bab912606816488da8788c2d5b0e6ea4b36dfe791e0b
---
# Support DP attention for breakable prefill CUDA graphs

URL: https://github.com/sgl-project/sglang/pull/30185
State: closed
Labels: run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-11T17:25:27Z
Merged at: 

## Summary

- Enable breakable prefill CUDA graph replay for DP attention batches that include idle ranks.
- Carry logprob and non-padded-token metadata through prefill graph replay.
- Clamp prefill CUDA graph capture sizes after the DP chunked-prefill adjustment.
- Remove the config-time block that disabled breakable prefill CUDA graph when DP attention is enabled.
- Add a registered e2e KL test for DP attention + breakable prefill CUDA graph that compares prefill/decode cache-hit logprobs against replayed input logprobs.

## Testing

- `CUDA_VISIBLE_DEVICES=0,1 LD_PRELOAD=/lib64/libnuma.so.1 uv run --no-sync python test/registered/dp_attn/test_dp_attention_breakable_cuda_graph_kl.py -v`
  - `Ran 2 tests in 174.246s`
  - `avg KL: 0.000221`
  - `KL threshold: 0.002500`
- `pre-commit run black-jupyter --files test/registered/dp_attn/test_dp_attention_breakable_cuda_graph_kl.py`
- `python3 -m py_compile python/sglang/srt/server_args.py test/registered/dp_attn/test_dp_attention_breakable_cuda_graph_kl.py`
- `git diff --check -- python/sglang/srt/server_args.py test/registered/dp_attn/test_dp_attention_breakable_cuda_graph_kl.py`









































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28822209659](https://github.com/sgl-project/sglang/actions/runs/28822209659)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28822209464](https://github.com/sgl-project/sglang/actions/runs/28822209464)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
