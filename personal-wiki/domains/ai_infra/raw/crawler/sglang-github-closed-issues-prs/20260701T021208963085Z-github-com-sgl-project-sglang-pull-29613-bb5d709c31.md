---
source_id: sglang-github-closed-issues-prs
title: '[DSA] Use cos_sin_cache for DSA indexer fusion'
canonical_url: https://github.com/sgl-project/sglang/pull/29613
captured_at: '2026-07-01T02:12:08.963085+00:00'
content_hash: bb5d709c31e771c260905564dbdcb34c6e2150809846e045219a3a27c15b533d
---
# [DSA] Use cos_sin_cache for DSA indexer fusion

URL: https://github.com/sgl-project/sglang/pull/29613
State: closed
Labels: run-ci, jit-kernel
Closed at: 2026-06-30T06:49:01Z
Merged at: 2026-06-30T06:49:01Z

## Summary

This is a follow-up to the DSA indexer fusion work in #27705 and the memory fix in #29576. That fix caches the derived `freqs_cis` table on the shared rotary embedding, but it is still a second RoPE table that has to stay in sync with `rotary_emb.cos_sin_cache`.

This PR makes the V3.2 fused indexer use `cos_sin_cache` directly. That avoids stale-cache behavior if `_ensure_cos_sin_cache_length` replaces the RoPE cache for longer contexts, and it removes the remaining extra RoPE storage from this path.

The indexer math is unchanged. This only changes the DeepSeek-V3.2 DSA fused indexer path, so the native DSV4 indexer path still uses `freqs_cis` the same way as before.

## Accuracy Test

- Benchmark: AIME 2025
- Model: `nvidia/GLM-5.2-NVFP4`
- Settings: 16 repeats, max tokens 64000, temperature 1.0, top-p 0.95

Result:

```text
pass@1[avg-of-16]: 90.83% +/- 4.63% (SEM 1.16%)
```







































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28362321264](https://github.com/sgl-project/sglang/actions/runs/28362321264)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28362321075](https://github.com/sgl-project/sglang/actions/runs/28362321075)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
