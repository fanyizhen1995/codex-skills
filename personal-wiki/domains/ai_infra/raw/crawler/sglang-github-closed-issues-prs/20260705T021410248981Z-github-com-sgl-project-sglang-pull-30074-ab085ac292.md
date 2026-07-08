---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Migrate the page_size resolution chain (stack 12/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30074
captured_at: '2026-07-05T02:14:10.248981+00:00'
content_hash: ab085ac2920076e8b503ce788c5f8fcb454eefb40e0f2d19a942844162b9f723
---
# [refactor] Migrate the page_size resolution chain (stack 12/15)

URL: https://github.com/sgl-project/sglang/pull/30074
State: closed
Labels: 
Closed at: 2026-07-04T09:22:28Z
Merged at: 2026-07-04T09:22:28Z

Back-to-front: the platform/env default fill and the DLLM block-size
alignment first (the two last writers), then the compatibility
handler's eight backend page snaps as three slot-preserving passes (the
six MLA-family snaps consolidate into one pass — no attention pass sits
in that window and the cutedsl prefill fallback cannot flip the
trtllm_mha condition — while the fa4 and intel_xpu constraints keep
their post-attention-flip slots), then the two monolith writers: the
Qwen3.5-hybrid coupled attention+page declaration (its default-backend
helper reads only spec/tp fields, and the trailing mamba-radix helper
still observes the dual-applied page) and the Qwen3VL aiter env fill.
page_size is whitelisted with a flat leaf.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 12/15 of the declarative config-resolution stack (based on `cheng/gc-pr-11`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701804975](https://github.com/sgl-project/sglang/actions/runs/28701804975)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701805172](https://github.com/sgl-project/sglang/actions/runs/28701805172)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
