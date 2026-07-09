---
source_id: sglang-github-closed-issues-prs
title: Use FP32 logits in MoEGate fallbacks
canonical_url: https://github.com/sgl-project/sglang/pull/30323
captured_at: '2026-07-08T23:36:33.790936+00:00'
content_hash: d8f0abee642a8595108ff8a81956d508ab47daad6a2ebfed3bf4543d6442bf08
---
# Use FP32 logits in MoEGate fallbacks

URL: https://github.com/sgl-project/sglang/pull/30323
State: closed
Labels: deepseek, run-ci, run-ci-extra
Closed at: 2026-07-08T15:43:46Z
Merged at: 2026-07-08T15:43:46Z

## Summary

Fixes a small gap left after #29783. The prefill-CP branch could still fall back to `F.linear` and produce BF16 router logits.







































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28914364446](https://github.com/sgl-project/sglang/actions/runs/28914364446)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28914364314](https://github.com/sgl-project/sglang/actions/runs/28914364314)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
