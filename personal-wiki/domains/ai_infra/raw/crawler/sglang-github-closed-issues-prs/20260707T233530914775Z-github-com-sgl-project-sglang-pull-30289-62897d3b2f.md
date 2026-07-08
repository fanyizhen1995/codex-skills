---
source_id: sglang-github-closed-issues-prs
title: '[DeepSeek V4] Fix stale override wording in ROCm FlashMLA sparse-prefill disable'
canonical_url: https://github.com/sgl-project/sglang/pull/30289
captured_at: '2026-07-07T23:35:30.914775+00:00'
content_hash: 62897d3b2ffe52cba60f1dcd004cbea0f996bfc0844bb6706f39d888fb9c9c9f
---
# [DeepSeek V4] Fix stale override wording in ROCm FlashMLA sparse-prefill disable

URL: https://github.com/sgl-project/sglang/pull/30289
State: closed
Labels: deepseek
Closed at: 2026-07-07T07:29:05Z
Merged at: 

## Motivation

#30237 made the ROCm/HIP disable of `SGLANG_OPT_FLASHMLA_SPARSE_PREFILL` unconditional (dropped the `is_set()` check), which is correct — but the warning message and preceding comment still say the env var can be *set explicitly to override*, which is no longer true. This was also raised by the gemini review bot on #30237.

## Modifications

`python/sglang/srt/arg_groups/deepseek_v4_hook.py`: update the comment and `logger.warning` text to reflect that the flag is unconditionally disabled on ROCm/HIP until the sparse prefill kernel is validated there. No behavior change.

## Accuracy Tests

Comment/log-string only; no functional change.

## Checklist

- [x] Docs/log-string only, no behavior change.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28817248929](https://github.com/sgl-project/sglang/actions/runs/28817248929)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28817248875](https://github.com/sgl-project/sglang/actions/runs/28817248875)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
