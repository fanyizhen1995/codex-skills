---
source_id: sglang-github-closed-issues-prs
title: Fix hybrid attention graph hook test fixture
canonical_url: https://github.com/sgl-project/sglang/pull/30790
captured_at: '2026-07-10T23:37:20.320499+00:00'
content_hash: c940c06cf679b3b2c493f331fb466031f6aa10c22cd32517742a47d77037f7cf
---
# Fix hybrid attention graph hook test fixture

URL: https://github.com/sgl-project/sglang/pull/30790
State: closed
Labels: 
Closed at: 2026-07-10T18:07:04Z
Merged at: 2026-07-10T18:07:04Z

## Summary

Fixes the hybrid attention graph hook test from #29843 by adding the fake model runner field that became required after #30708

cc @hnyls2002 

## Failure

```text
FAILED registered/attention/test_trtllm_mha_graph_metadata.py::test_hybrid_wrappers_forward_in_graph_hook - AttributeError: 'types.SimpleNamespace' object has no attribute 'server_args'
```











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29100926571](https://github.com/sgl-project/sglang/actions/runs/29100926571)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29100926319](https://github.com/sgl-project/sglang/actions/runs/29100926319)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
