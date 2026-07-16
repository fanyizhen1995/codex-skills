---
source_id: sglang-github-closed-issues-prs
title: Fix abusing presence of req.req_pool_idx to indicate the presence of req.kv
  resources
canonical_url: https://github.com/sgl-project/sglang/pull/29430
captured_at: '2026-07-15T23:40:28.375440+00:00'
content_hash: 02c8d1b7892adbb5e4fec7636cd7e284a44139544802fd1ef76ef4da47278c3b
---
# Fix abusing presence of req.req_pool_idx to indicate the presence of req.kv resources

URL: https://github.com/sgl-project/sglang/pull/29430
State: closed
Labels: 
Closed at: 2026-07-15T06:48:39Z
Merged at: 2026-07-15T06:48:39Z

Part of the `req_pool_idx` / cache / owned-KV decoupling — a stacked refactor chain.

Stop abusing `req.req_pool_idx is not None` to mean "owns KV". Where a check really
asks about KV ownership, use `req.kv is not None`. `req_pool_idx` (a ReqToTokenPool
handle) and owned KV are independent resources and should not share one presence flag.

---
Stacked on: `op27`. Aggregated CI sandbox: #28636.

































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29395298615](https://github.com/sgl-project/sglang/actions/runs/29395298615)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29395298509](https://github.com/sgl-project/sglang/actions/runs/29395298509)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
