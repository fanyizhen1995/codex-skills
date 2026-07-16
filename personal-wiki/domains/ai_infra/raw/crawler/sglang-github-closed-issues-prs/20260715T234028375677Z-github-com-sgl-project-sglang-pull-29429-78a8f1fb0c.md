---
source_id: sglang-github-closed-issues-prs
title: Let the presence of req.kv indicate the existence of owned kv resources
canonical_url: https://github.com/sgl-project/sglang/pull/29429
captured_at: '2026-07-15T23:40:28.375677+00:00'
content_hash: 78a8f1fb0c29f2471cb03bd33f07c10c27168814cea58d34112be5e24539ed47
---
# Let the presence of req.kv indicate the existence of owned kv resources

URL: https://github.com/sgl-project/sglang/pull/29429
State: closed
Labels: 
Closed at: 2026-07-15T06:47:17Z
Merged at: 2026-07-15T06:47:17Z

Part of the `req_pool_idx` / cache / owned-KV decoupling — a stacked refactor chain.

Make the presence of `req.kv` mean "owned KV resources are allocated": allocate /
free `req.kv` exactly where the KV is really allocated / freed (not where
`req_pool_idx` is), and never construct zero/None placeholder `ReqKvInfo` objects.

---
Stacked on: `op3`. Aggregated CI sandbox: #28636.









































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29395208659](https://github.com/sgl-project/sglang/actions/runs/29395208659)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29395208518](https://github.com/sgl-project/sglang/actions/runs/29395208518)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
