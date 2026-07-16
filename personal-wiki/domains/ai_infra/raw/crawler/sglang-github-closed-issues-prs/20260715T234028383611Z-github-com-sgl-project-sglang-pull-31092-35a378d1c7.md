---
source_id: sglang-github-closed-issues-prs
title: Fix post-capture KV sizing for SWA pools
canonical_url: https://github.com/sgl-project/sglang/pull/31092
captured_at: '2026-07-15T23:40:28.383611+00:00'
content_hash: 35a378d1c7759f7c9cbe3bae66137b9092fe598a0e0923960a70f315b1249a8e
---
# Fix post-capture KV sizing for SWA pools

URL: https://github.com/sgl-project/sglang/pull/31092
State: closed
Labels: run-ci
Closed at: 2026-07-15T03:06:15Z
Merged at: 2026-07-15T03:06:15Z

## Summary
- Pass `post_capture_active=self.post_capture_kv_active` into the CUDA hybrid-SWA `SWAKVPool` constructor.
- Keep post-capture KV sizing gated off for pool families that do not yet implement post-capture backing/finalization: FP4 MHA, DeepSeek-V4, and MiniMax sparse.

## Tests
- `python3 -m py_compile python/sglang/srt/server_args.py python/sglang/srt/mem_cache/kv_cache_configurator.py`
- `git diff --check origin/main...HEAD -- python/sglang/srt/mem_cache/kv_cache_configurator.py python/sglang/srt/server_args.py`









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29373373645](https://github.com/sgl-project/sglang/actions/runs/29373373645)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29373373585](https://github.com/sgl-project/sglang/actions/runs/29373373585)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
