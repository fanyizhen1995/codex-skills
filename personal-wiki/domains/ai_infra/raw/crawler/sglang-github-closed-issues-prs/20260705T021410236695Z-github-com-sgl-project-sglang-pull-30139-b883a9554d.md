---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Skip cross-node probe in MultimemAllGatherer on single-node runs (fixes
  mooncake EP segfault)'
canonical_url: https://github.com/sgl-project/sglang/pull/30139
captured_at: '2026-07-05T02:14:10.236695+00:00'
content_hash: b883a9554dde38d59563f6eb304919c74a2b6dce9fb9a65fd02233679925d7a9
---
# [Fix] Skip cross-node probe in MultimemAllGatherer on single-node runs (fixes mooncake EP segfault)

URL: https://github.com/sgl-project/sglang/pull/30139
State: closed
Labels: run-ci
Closed at: 2026-07-04T22:36:24Z
Merged at: 2026-07-04T22:36:23Z

## Problem

`test/registered/ep/test_mooncake_ep_small.py` crashes the server at startup with a **segmentation fault** in today's scheduled run:

```
Current thread (most recent call first):
  File ".../torch/distributed/distributed_c10d.py", line 3068 in all_reduce
  ...
  File ".../srt/distributed/parallel_state.py", line 2681 in in_the_same_node_as
  File ".../srt/distributed/device_communicators/triton_symm_mem_ag.py", line 472 in __init__
  File ".../srt/layers/logits_processor.py", line 297 in __init__
```
→ `Server process exited with code 1` → `FAILED (errors=1, skipped=6)`.

## Root cause

PR #29881 ("Avoid logits multimem all-gather on cross-node TP groups") added an `in_the_same_node_as(tp_group.cpu_group, source_rank=0)` probe to `MultimemAllGatherer.__init__`. That probe runs a gloo `all_reduce` during logits-processor construction, and it **segfaults under the mooncake EP + DP-attention config** (tp4 / dp2 / ep4, DeepEP, `nnodes=1`).

Timeline for this test: it last passed on 0702_23; broke on 0703 with the router NaN crash (#29771, fixed by #30079); and now fails on 0704 with this segfault from #29881. Both fixes are needed for it to go green — #30079 is already merged, this PR is the second half.

## Fix

On a single-node deployment every TP rank is trivially co-located, so the cross-node probe is unnecessary. Gate it on `nnodes > 1`:
- single-node runs skip the fragile `all_reduce` and keep multimem enabled (pre-#29881 behavior),
- genuine multi-node deployments still get #29881's cross-node guard.

This unblocks CI and sidesteps the deeper question of *why* that gloo `all_reduce` segfaults under mooncake/DeepEP (worth a follow-up with the #29881 author). Needs a 4-GPU mooncake-EP run to confirm green (I can't run that locally).

🤖 Generated with [Claude Code](https://claude.com/claude-code)





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28721778107](https://github.com/sgl-project/sglang/actions/runs/28721778107)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28721778022](https://github.com/sgl-project/sglang/actions/runs/28721778022)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
