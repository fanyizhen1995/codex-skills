---
source_id: sglang-github-closed-issues-prs
title: '[fix] Wrap the sp_shard test entry point in sys.exit so failures propagate'
canonical_url: https://github.com/sgl-project/sglang/pull/30138
captured_at: '2026-07-05T02:14:10.237953+00:00'
content_hash: e24c5e8a2305012546ef4917660a41e08e4eb243404c29bee6d1766e21eb1c04
---
# [fix] Wrap the sp_shard test entry point in sys.exit so failures propagate

URL: https://github.com/sgl-project/sglang/pull/30138
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-04T21:23:40Z
Merged at: 2026-07-04T21:23:40Z

test_sp_shard.py (added in #30107) runs a bare `pytest.main(...)` in its `__main__` block, which swallows the exit code. The repo hygiene check `test_no_bare_pytest_main` now fails on main and on every open PR's merge commit:

```
AssertionError: ['python/sglang/multimodal_gen/test/unit/test_sp_shard.py:213'] is not false : Found bare pytest.main(...) in __main__ blocks
```

One-line fix: wrap it in `sys.exit(...)` (sys import added). Verified `test_no_bare_pytest_main` passes with this change.

🤖 Generated with [Claude Code](https://claude.com/claude-code)















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28719846149](https://github.com/sgl-project/sglang/actions/runs/28719846149)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28719849266](https://github.com/sgl-project/sglang/actions/runs/28719849266)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
