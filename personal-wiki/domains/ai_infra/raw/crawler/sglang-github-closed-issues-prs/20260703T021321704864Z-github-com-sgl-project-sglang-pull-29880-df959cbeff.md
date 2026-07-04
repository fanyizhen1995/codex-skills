---
source_id: sglang-github-closed-issues-prs
title: Revert "[DeepSeek V4] Enable FlashMLA sparse prefill by default"
canonical_url: https://github.com/sgl-project/sglang/pull/29880
captured_at: '2026-07-03T02:13:21.704864+00:00'
content_hash: df959cbeff15934100e9ef53b1a1d7958b51a0679305d56ed838cec8d660e1f9
---
# Revert "[DeepSeek V4] Enable FlashMLA sparse prefill by default"

URL: https://github.com/sgl-project/sglang/pull/29880
State: closed
Labels: deepseek
Closed at: 2026-07-02T04:20:24Z
Merged at: 

Reverts sgl-project/sglang#29775

It breaks CI: https://github.com/sgl-project/sglang/actions/runs/28553763159/job/84656740339?pr=29458.

The kernel may have some precision issues thus it would be better to make more investigation. 











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28559211162](https://github.com/sgl-project/sglang/actions/runs/28559211162)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28559211075](https://github.com/sgl-project/sglang/actions/runs/28559211075)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
