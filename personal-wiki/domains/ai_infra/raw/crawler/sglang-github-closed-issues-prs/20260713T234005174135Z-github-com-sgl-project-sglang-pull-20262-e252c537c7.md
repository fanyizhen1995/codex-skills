---
source_id: sglang-github-closed-issues-prs
title: Fix predict.fill_(100) decode hang on byte-token models (#20154)
canonical_url: https://github.com/sgl-project/sglang/pull/20262
captured_at: '2026-07-13T23:40:05.174135+00:00'
content_hash: e252c537c7092079b07e03d9f9c0f8e061c8f7aa594338e7e38ac56b7fa32280
---
# Fix predict.fill_(100) decode hang on byte-token models (#20154)

URL: https://github.com/sgl-project/sglang/pull/20262
State: closed
Labels: 
Closed at: 2026-07-13T18:39:40Z
Merged at: 

Use tokenizer-derived safe token ID instead of hardcoded 100, which causes
detokenizer hangs on byte-token models like Kimi-K2.5.

Closes #20154
