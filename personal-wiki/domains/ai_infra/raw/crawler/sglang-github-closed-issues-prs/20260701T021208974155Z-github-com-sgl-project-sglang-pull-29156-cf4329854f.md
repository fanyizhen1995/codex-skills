---
source_id: sglang-github-closed-issues-prs
title: Fix bounded checkpoint prefetching and buffered drop-cache handling
canonical_url: https://github.com/sgl-project/sglang/pull/29156
captured_at: '2026-07-01T02:12:08.974155+00:00'
content_hash: cf4329854f6cd6922805a7d08c9247cff105f34e526783a118228f190bd93ec0
---
# Fix bounded checkpoint prefetching and buffered drop-cache handling

URL: https://github.com/sgl-project/sglang/pull/29156
State: closed
Labels: run-ci
Closed at: 2026-06-29T21:49:17Z
Merged at: 2026-06-29T21:49:17Z

## Summary

This cleans up checkpoint prefetching by using a bounded thread pool and rejecting invalid thread counts instead of letting them hang. It also fixes the buffered safetensors loader so `drop_cache_after_load` actually runs for each shard, with tests covering the prefetch and drop-cache paths.













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28370610690](https://github.com/sgl-project/sglang/actions/runs/28370610690)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28370610470](https://github.com/sgl-project/sglang/actions/runs/28370610470)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
