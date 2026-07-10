---
source_id: sglang-github-closed-issues-prs
title: '[CI Hot fix] Fix retired dp_attention CP accessors breaking every scheduler
  start'
canonical_url: https://github.com/sgl-project/sglang/pull/30661
captured_at: '2026-07-09T23:36:35.327233+00:00'
content_hash: 85c9c8f0f61aeef20c306ff959a4ace8f0832fed2fe5e7116a81c92c594f3784
---
# [CI Hot fix] Fix retired dp_attention CP accessors breaking every scheduler start

URL: https://github.com/sgl-project/sglang/pull/30661
State: closed
Labels: 
Closed at: 2026-07-09T13:53:33Z
Merged at: 

## Motivation

Main is currently broken: every scheduler start crashes with

```
ImportError: cannot import name 'get_attention_cp_size' from 'sglang.srt.layers.dp_attention'
```

`DefaultPoolConfigurator._compute_cell_size` unconditionally calls `get_glm_dsa_layer_split_effective_num_layers` (added in #29421), which imports `get_attention_cp_size` from `sglang.srt.layers.dp_attention`. #29421 was written against a base where those accessors existed, but the `get_parallel()` refactor (#30492 / #30493) retired them before #29421 merged — a semantic conflict, so the names no longer exist anywhere in the tree. This currently fails `test/registered/unit/model_executor/test_pool_configurator.py` and any CI job that launches a server (see the red scheduled full runs on main).

## Modifications

Switch the three files that still reference the retired accessors to the `get_parallel()` API:

- `sglang/srt/layers/cp/utils.py`: `get_attention_cp_size()` / `get_attention_cp_rank()` → `get_parallel().attn_cp_size` / `.attn_cp_rank`
- `sglang/srt/mem_cache/dsa_cache_layer_split.py`: `get_attention_cp_group()` → `get_parallel().attn_cp_group`
- `test/registered/unit/mem_cache/test_dsa_layer_split_broadcast.py`: same rename in the spawned-rank helper

No behavior change: the `get_parallel()` properties resolve to the same `parallel_state` getters the old wrappers delegated to.

cc @merrymercy @Fridge003

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29020960665](https://github.com/sgl-project/sglang/actions/runs/29020960665)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29020960404](https://github.com/sgl-project/sglang/actions/runs/29020960404)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
