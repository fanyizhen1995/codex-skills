---
source_id: sglang-github-closed-issues-prs
title: Size KV pool after CUDA graph capture (opt-in)
canonical_url: https://github.com/sgl-project/sglang/pull/30157
captured_at: '2026-07-07T23:35:30.907023+00:00'
content_hash: 334b8f403b64c9fa109d42be90ac98d39a54e72d9838f197230d38c26e360da9
---
# Size KV pool after CUDA graph capture (opt-in)

URL: https://github.com/sgl-project/sglang/pull/30157
State: closed
Labels: run-ci
Closed at: 2026-07-07T19:05:02Z
Merged at: 2026-07-07T19:05:02Z

**Problem:** the KV pool is sized *before* CUDA-graph capture, so graph memory is a heuristic guess baked into `mem_fraction_static`. On large configs the guess can be off by ~10 GB/GPU; the padded activation reserve silently absorbs the difference, wasting memory on some configs and risking OOM on others.

**Fix:** add `SGLANG_ENABLE_POST_CAPTURE_KV_SIZING` (opt-in, **default off**). When enabled:
1. Reserve the KV pool as **virtual memory only** (CUDA VMM arena; tensors get stable pointers, ~0 bytes physical).
2. Capture CUDA graphs first — their baked-in KV pointers stay valid.
3. Size the pool from measured free memory, then physically back it (`cuMemMap`), and drop the per-token activation reserve.


### Test
`test/registered/mem_cache/test_post_capture_kv_sizing.py` launches a server with the flag on and asserts:
- the post-capture sizing path actually ran (log line present, not a silent skip),
- `/server_info` reports `max_total_num_tokens > 0`,
- gsm8k accuracy unchanged (>= 0.80 on Llama-3.1-8B).

Registered in the base CI tier (`base-b` / `1-gpu-large`) so it runs on every PR.



































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28883219805](https://github.com/sgl-project/sglang/actions/runs/28883219805)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28883219626](https://github.com/sgl-project/sglang/actions/runs/28883219626)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
