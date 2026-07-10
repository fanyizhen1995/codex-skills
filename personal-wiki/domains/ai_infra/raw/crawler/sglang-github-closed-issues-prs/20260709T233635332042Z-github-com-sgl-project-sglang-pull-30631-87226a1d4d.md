---
source_id: sglang-github-closed-issues-prs
title: '[fix] Repoint the prefetch-dispatch test at the loader''s current config binding'
canonical_url: https://github.com/sgl-project/sglang/pull/30631
captured_at: '2026-07-09T23:36:35.332042+00:00'
content_hash: 87226a1d4d90b45b85c46005377420096da374cb0411f5a9b4f0a01ce760f0a3
---
# [fix] Repoint the prefetch-dispatch test at the loader's current config binding

URL: https://github.com/sgl-project/sglang/pull/30631
State: closed
Labels: 
Closed at: 2026-07-09T09:21:05Z
Merged at: 2026-07-09T09:21:05Z

## Motivation

#30146 (merged 40 minutes before #30493) added `TestPrefetchDispatch` cases that patch `sglang.srt.model_loader.loader.get_global_server_args`; #30493 flipped that import to `runtime_context.get_server_args`. Both PRs were green individually — the combination leaves six unit tests failing on `main` with `AttributeError: module ... does not have the attribute 'get_global_server_args'`.

## Modifications

One line: the patch target follows the loader's current module-level binding (`loader.get_server_args`), which is what the dispatch code reads — interception is unchanged.

## Verification

`test_prefetch_checkpoints.py` 13/13 pass on main + this fix (was 7/13).

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29007872709](https://github.com/sgl-project/sglang/actions/runs/29007872709)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29007872568](https://github.com/sgl-project/sglang/actions/runs/29007872568)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
