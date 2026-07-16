---
source_id: sglang-github-closed-issues-prs
title: Support Waterfill with MegaMoE backend
canonical_url: https://github.com/sgl-project/sglang/pull/27350
captured_at: '2026-07-13T23:40:05.187626+00:00'
content_hash: 5f5dfe4c62f31525e529a49c23afdc960f303a7b14ea3c5170e657e532079845
---
# Support Waterfill with MegaMoE backend

URL: https://github.com/sgl-project/sglang/pull/27350
State: closed
Labels: documentation, deepseek, npu, run-ci, jit-kernel, bypass-fastfail, run-ci-extra
Closed at: 2026-07-13T10:56:46Z
Merged at: 2026-07-13T10:56:46Z

## Summary
- allow Waterfill to preserve an explicit MegaMoE backend instead of forcing DeepEP
- allow the MegaMoE env path to be selected before Waterfill fallback logic runs
- use a rank-local shared expert slot semantic helper for TopK, FusedMoE, and DeepSeek shared expert fusion call sites
- add server-args tests for explicit MegaMoE and MegaMoE env selection under Waterfill

## Dependency
Depends on #27349, which adds the MegaMoE/shared expert fusion loading compatibility needed by the current DeepSeek-V4-Flash FP4 test path. This branch is stacked on top of `xutizhou:fix/megamoe-shared-fusion-quant`; after #27349 lands, this PR should be rebased on `main` so its diff only shows the Waterfill+MegaMoE changes.

## Testing
- python3 -m compileall -q python/sglang/srt/layers/moe/fused_moe_triton/layer.py python/sglang/srt/models/deepseek_v2.py python/sglang/srt/layers/moe/topk.py python/sglang/srt/layers/moe/utils.py python/sglang/srt/server_args.py
- B200 MMLU subset: pure MegaMoE accuracy 0.8509861213; Waterfill+MegaMoE accuracy 0.8531775018























































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29149824508](https://github.com/sgl-project/sglang/actions/runs/29149824508)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29149824332](https://github.com/sgl-project/sglang/actions/runs/29149824332)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
