---
source_id: sglang-github-closed-issues-prs
title: add missing logprob args to bench_speculative dummy namespace (#22013)
canonical_url: https://github.com/sgl-project/sglang/pull/22348
captured_at: '2026-07-13T23:40:05.175413+00:00'
content_hash: 4021ab07f261920d4638d81ef1c2c756bed48845e734010278e9c4da6011300c
---
# add missing logprob args to bench_speculative dummy namespace (#22013)

URL: https://github.com/sgl-project/sglang/pull/22348
State: closed
Labels: speculative-decoding
Closed at: 2026-07-13T18:39:37Z
Merged at: 

## Summary
Add `logprob_start_len`, `top_logprobs_num`, and `token_ids_logprob` to the dummy `SimpleNamespace`. `set_global_args` doesn't apply defaults like `run_benchmark` does, so `benchmark()` crashed with `AttributeError`.

Closes #22013.
