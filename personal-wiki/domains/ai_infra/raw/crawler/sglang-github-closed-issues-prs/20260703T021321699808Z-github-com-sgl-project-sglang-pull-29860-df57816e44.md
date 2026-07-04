---
source_id: sglang-github-closed-issues-prs
title: Fix SWA eviction tombstoning the last leaf
canonical_url: https://github.com/sgl-project/sglang/pull/29860
captured_at: '2026-07-03T02:13:21.699808+00:00'
content_hash: df57816e44be6fec9b56ddfc0c19cff3979632b9586945e43c4dc5305be256eb
---
# Fix SWA eviction tombstoning the last leaf

URL: https://github.com/sgl-project/sglang/pull/29860
State: closed
Labels: run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-02T13:42:30Z
Merged at: 2026-07-02T13:42:30Z

## Motivation

With `SGLANG_OPT_UNIFIED_CACHE_FREE_OUT_OF_WINDOW_SLOTS` enabled, `cache_unfinished_req` eagerly frees out-of-window SWA slots before inserting. On the radix path this subtracted `window + page_size`, and `SGLANG_OPT_SWA_EVICT_DROP_PAGE_MARGIN` dropped the extra page down to just `window`. With both set and `page_size > sliding_window_size`, the page-aligned floor advanced the eviction frontier onto `page_floor(seq_len)`, leaving the last inserted leaf fully out of window (an all-tombstone leaf that then hits an assert on overlap free or leaks SWA memory).

The extra page margin is unnecessary: `max(window, page_size)` already keeps the page-aligned frontier a full page below the insert boundary. The radix path now uses `max(window, page_size)`, which also saves a page, and `SGLANG_OPT_SWA_EVICT_DROP_PAGE_MARGIN` is removed. Chunk cache keeps `pre_len - window` since it builds no radix tree.

Fixes the case reported in https://github.com/sgl-project/sglang/pull/29282

































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28564377415](https://github.com/sgl-project/sglang/actions/runs/28564377415)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28564377208](https://github.com/sgl-project/sglang/actions/runs/28564377208)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
