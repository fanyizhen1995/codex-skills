---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Fix DSA indexer fusion for NeoX RoPE'
canonical_url: https://github.com/sgl-project/sglang/pull/30111
captured_at: '2026-07-05T02:14:10.244731+00:00'
content_hash: 44b3b6db47df75aa94d799db698976bd08bd8cba1ff0cb1c48a459c5bf4c2af3
---
# [Fix] Fix DSA indexer fusion for NeoX RoPE

URL: https://github.com/sgl-project/sglang/pull/30111
State: closed
Labels: deepseek
Closed at: 2026-07-04T10:20:56Z
Merged at: 2026-07-04T10:20:56Z

## Summary

- Skip DSA indexer fusion for `is_neox_style=True` indexers while keeping the global fusion env enabled by default.
- Use `self.use_dsa_indexer_fusion` as the only fusion branch guard; the module-level `_use_dsa_indexer_fusion` helper was removed.
- Restore `SGLANG_DISABLE_DSA_INDEXER_FUSION` to `EnvBool(False)` on latest `main`.
- Restore both DeepSeek V3.2 index-cache GSM8K thresholds to `0.935`.

## Root Cause

DSA indexer fusion was controlled only by the global `SGLANG_DISABLE_DSA_INDEXER_FUSION` env flag. NeoX-style RoPE models could still take the fused indexer path, but that path is not compatible with `is_neox_style=True` rotation handling, causing the observed accuracy regression.

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28702478657](https://github.com/sgl-project/sglang/actions/runs/28702478657)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28702478568](https://github.com/sgl-project/sglang/actions/runs/28702478568)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
