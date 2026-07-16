---
source_id: sglang-github-closed-issues-prs
title: filter None from stop_token_ids to avoid scheduler crash (#22144)
canonical_url: https://github.com/sgl-project/sglang/pull/22347
captured_at: '2026-07-13T23:40:05.174801+00:00'
content_hash: 1f8a089e2ba72bd873cd3f6adf0afa7eb3e471bd46ea78fffe56492e01a90556
---
# filter None from stop_token_ids to avoid scheduler crash (#22144)

URL: https://github.com/sgl-project/sglang/pull/22347
State: closed
Labels: 
Closed at: 2026-07-13T18:39:39Z
Merged at: 

## Summary
Drop `None` entries from `stop_token_ids` in `SamplingParams.__init__` and reject non-ints in `verify()`. `"stop_token_ids": [null]` previously crashed the min-new-tokens penalizer when building a tensor from the set.

Closes #22144.
