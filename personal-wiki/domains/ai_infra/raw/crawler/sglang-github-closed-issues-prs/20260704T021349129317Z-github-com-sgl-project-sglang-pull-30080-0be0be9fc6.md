---
source_id: sglang-github-closed-issues-prs
title: '[MiMo-VL] Fix missing padded_context_dim in vision patch merger (fixes test_mimo_v2
  init crash)'
canonical_url: https://github.com/sgl-project/sglang/pull/30080
captured_at: '2026-07-04T02:13:49.129317+00:00'
content_hash: 0be0be9fc61e3ab3106674fd6844710ac2e9e20d8b914cc7dc4b5eff839d1511
---
# [MiMo-VL] Fix missing padded_context_dim in vision patch merger (fixes test_mimo_v2 init crash)

URL: https://github.com/sgl-project/sglang/pull/30080
State: closed
Labels: 
Closed at: 2026-07-04T01:32:02Z
Merged at: 

## Problem

`test/registered/models_e2e/test_mimo_v2.py` fails: the MiMo-V2.5 server dies at model init with
```
TypeError: Qwen2_5_VisionPatchMerger.__init__() missing 1 required positional argument: 'padded_context_dim'
```
→ all TP ranks raise it → `RuntimeError: Rank 0 scheduler died during initialization`.

## Root cause

PR #20072 ("[CPU] Padding for dim divisibility in TP3/6 cases", commit `aff44d748d`) added a **required** `padded_context_dim` parameter to `Qwen2_5_VisionPatchMerger.__init__` and updated its own caller in `qwen2_5_vl.py`, but missed the second caller in `mimo_vl.py`. MiMo-V2.5 is multimodal (`--mm-enable-dp-encoder`), so it instantiates the vision merger and hits the missing argument.

First failing scheduled run: 07-02_11 (`119b76567d`), the first to contain `aff44d748d`.

## Fix

Pass `padded_context_dim=hidden_size`. For the standard (unpadded) case this equals `context_dim`, which matches both the pre-#20072 merger MLP width and the `qwen2_5_vl.py` caller's `num_heads * head_dim` (that reduces to `hidden_size` on GPU when `hidden_size % num_heads == 0`). So the merger MLP shape and weight loading are preserved. Using `hidden_size` directly (rather than `num_heads * head_dim`) is safe here because MiMo-VL's `head_dim` may be `qk_channels`, which need not equal `hidden_size / num_heads`.

Needs GPU CI validation on `test_mimo_v2.py`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
