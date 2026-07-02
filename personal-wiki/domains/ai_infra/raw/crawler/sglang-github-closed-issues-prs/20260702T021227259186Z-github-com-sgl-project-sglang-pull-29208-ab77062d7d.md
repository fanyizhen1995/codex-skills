---
source_id: sglang-github-closed-issues-prs
title: Revert DeepSeek-V4 Online Compress support MTP
canonical_url: https://github.com/sgl-project/sglang/pull/29208
captured_at: '2026-07-02T02:12:27.259186+00:00'
content_hash: ab77062d7d977e176e3395893375ab7af52c25156e82155df2606bbe0b1791b1
---
# Revert DeepSeek-V4 Online Compress support MTP

URL: https://github.com/sgl-project/sglang/pull/29208
State: closed
Labels: deepseek, jit-kernel
Closed at: 2026-06-24T21:52:37Z
Merged at: 

## Summary

- Reverts #26471 / merge commit `063ab89ac1685e99e2252fdc95eea444dc83635e`.
- Removes the online C128 MTP kernel, Python wrapper, benchmark, env flag, and integration hooks.
- Preserves later non-MTP DSV4 refactors that conflicted during the revert resolution.

## Testing

- `pre-commit run --from-ref origin/main --to-ref HEAD`
- `python -m compileall -q python/sglang/jit_kernel/dsv4/compress.py python/sglang/srt/environ.py python/sglang/srt/layers/attention/deepseek_v4_backend.py python/sglang/srt/layers/attention/dsv4/compressor_v2.py python/sglang/srt/mem_cache/deepseek_v4_compress_state.py python/sglang/srt/mem_cache/deepseek_v4_memory_pool.py python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py python/sglang/srt/model_executor/pool_configurator.py`











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28131288720](https://github.com/sgl-project/sglang/actions/runs/28131288720)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28131288623](https://github.com/sgl-project/sglang/actions/runs/28131288623)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
