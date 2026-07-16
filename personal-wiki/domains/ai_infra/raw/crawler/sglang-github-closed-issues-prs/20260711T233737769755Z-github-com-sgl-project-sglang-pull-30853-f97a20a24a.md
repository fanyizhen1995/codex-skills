---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Enable draft extend cuda graph for DeepSeek-V4 attention backend'
canonical_url: https://github.com/sgl-project/sglang/pull/30853
captured_at: '2026-07-11T23:37:37.769755+00:00'
content_hash: f97a20a24ac91c53e4d8c9264cee329fcb6b6564fc1e0149d32ff565b8a2aa08
---
# [Spec] Enable draft extend cuda graph for DeepSeek-V4 attention backend

URL: https://github.com/sgl-project/sglang/pull/30853
State: closed
Labels: 
Closed at: 2026-07-11T09:29:49Z
Merged at: 2026-07-11T09:29:49Z

DeepseekV4AttnBackend already implements the DRAFT_EXTEND graph bucket (capture + replay); register it in the EAGLE draft worker's supported list so draft extend runs under cuda graph instead of eager.

Verification: test_deepseek_v4_flash_fp8_h200.py (TP=4 + EAGLE) exercises this path -- graph capture happens at server startup, so the test passing covers capture and replay.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29147214733](https://github.com/sgl-project/sglang/actions/runs/29147214733)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29147214595](https://github.com/sgl-project/sglang/actions/runs/29147214595)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
