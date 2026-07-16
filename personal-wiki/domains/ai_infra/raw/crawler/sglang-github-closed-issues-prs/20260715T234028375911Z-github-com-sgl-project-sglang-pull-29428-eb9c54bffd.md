---
source_id: sglang-github-closed-issues-prs
title: Let cache backend do not couple with owned committed kv details and avoid kv_committed_freed/kv_overallocated_freed
  fields
canonical_url: https://github.com/sgl-project/sglang/pull/29428
captured_at: '2026-07-15T23:40:28.375911+00:00'
content_hash: eb9c54bffd816e2d2301d69b2df999bbe9cda547e0f82598a25af94c15d97589
---
# Let cache backend do not couple with owned committed kv details and avoid kv_committed_freed/kv_overallocated_freed fields

URL: https://github.com/sgl-project/sglang/pull/29428
State: closed
Labels: documentation
Closed at: 2026-07-15T06:43:11Z
Merged at: 2026-07-15T06:43:11Z

Part of the `req_pool_idx` / cache / owned-KV decoupling — a stacked refactor chain.

Stop the cache backend from coupling to owned committed-KV details: thread
`kv_len_to_handle` (= `req.effective_kv_committed_len()`) into `cache_finished_req`
as a keyword argument instead of having the cache call `pop_committed_kv_cache`,
and drop the `kv_committed_freed` / `kv_overallocated_freed` flags. Relies on the
proof that `pop_committed_kv_cache` / `pop_overallocated_kv_cache` were always paired.

---
Stacked on: `op41`. Aggregated CI sandbox: #28636.







































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29395027749](https://github.com/sgl-project/sglang/actions/runs/29395027749)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29395027353](https://github.com/sgl-project/sglang/actions/runs/29395027353)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
