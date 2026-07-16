---
source_id: sglang-github-closed-issues-prs
title: '[Refactor] Make DeepSeek-V4 attention backend tolerate an absent CPU seq_lens
  mirror'
canonical_url: https://github.com/sgl-project/sglang/pull/30695
captured_at: '2026-07-10T23:37:20.336727+00:00'
content_hash: c77ccfb153ee86453ca3ee92b3515f63e44339ed497f58bd7a7360039ca357ca
---
# [Refactor] Make DeepSeek-V4 attention backend tolerate an absent CPU seq_lens mirror

URL: https://github.com/sgl-project/sglang/pull/30695
State: closed
Labels: deepseek
Closed at: 2026-07-09T23:39:48Z
Merged at: 2026-07-09T23:39:48Z

DeepSeek-V4 metadata paths no longer assume the host seq_lens mirror exists: replay/verify paths take a device-only path when it is absent, and needs_cpu_seq_lens is derived from the spec configuration at init (spec runs keep the relay publish since draft-extend and online-c128 verify planning are host-side). No behavior change for current configurations.
