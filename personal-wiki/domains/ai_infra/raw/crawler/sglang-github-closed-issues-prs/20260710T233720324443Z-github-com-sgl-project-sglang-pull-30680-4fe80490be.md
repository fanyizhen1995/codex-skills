---
source_id: sglang-github-closed-issues-prs
title: Fix DFlash mamba verify init ordering
canonical_url: https://github.com/sgl-project/sglang/pull/30680
captured_at: '2026-07-10T23:37:20.324443+00:00'
content_hash: 4fe80490be3b0326d161af68f8d998a1e16fb1a421bf4b9031204f2561a3a0f4
---
# Fix DFlash mamba verify init ordering

URL: https://github.com/sgl-project/sglang/pull/30680
State: closed
Labels: run-ci
Closed at: 2026-07-10T00:40:13Z
Merged at: 2026-07-10T00:40:13Z

## Summary

Fixes a DFlash startup crash introduced in #29218. The new code checked the target `ModelRunner.attn_backend` inside `DFlashWorkerV2.__init__`, but the backend is not ready yet at that point. Before this, the server could fail during scheduler startup with:

```text
AttributeError: 'ModelRunner' object has no attribute 'attn_backend'
```

After moving the mamba verify-commit check until after attention backend init, the DFlash worker no longer reads the target backend too early.

















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29057403869](https://github.com/sgl-project/sglang/actions/runs/29057403869)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29057403746](https://github.com/sgl-project/sglang/actions/runs/29057403746)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
