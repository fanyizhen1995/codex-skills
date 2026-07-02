---
source_id: sglang-github-closed-issues-prs
title: '[bug1] keep full kv when swa skips leaf data'
canonical_url: https://github.com/sgl-project/sglang/pull/29351
captured_at: '2026-07-01T02:12:08.956425+00:00'
content_hash: 3b85386db74d4cfd428d90abd8ce789dcb564f30f46c0aae42f35b0d3b43470b
---
# [bug1] keep full kv when swa skips leaf data

URL: https://github.com/sgl-project/sglang/pull/29351
State: closed
Labels: documentation, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-06-30T16:51:19Z
Merged at: 2026-06-30T16:51:18Z

Split 2 from https://github.com/sgl-project/sglang/pull/29349

## Motivation
This PR fixes a unified-cache consistency issue where SWA tombstone state could prevent valid Full KV from being inserted.

In unified cache, Full KV and auxiliary component state are stored on the same radix nodes, but an auxiliary component may legitimately have no value for a span. SWA can tombstone a span that is outside its sliding window, while the Full KV for the same span is still valid and reusable.

## Modifications
Remove SWA's leaf-creation veto. Full KV now creates the leaf normally, and SWA simply leaves its component value empty when the span is outside the SWA window.

#### Bug 1: SWA could prevent creation of a valid Full KV leaf
  - **Root cause:** `SWA.should_skip_leaf_creation(...)` could veto leaf creation when the new leaf was fully outside the SWA window. That decision is valid only for SWA
  data; the Full KV leaf is still valid and should remain cacheable.
  - **Fix:** Stop using auxiliary components to veto leaf creation. Materialize the Full KV leaf and let SWA store a tombstone for that span.
  - **Commit:** 15d16d25ee



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28374798451](https://github.com/sgl-project/sglang/actions/runs/28374798451)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28376015491](https://github.com/sgl-project/sglang/actions/runs/28376015491)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
