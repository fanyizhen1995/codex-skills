---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Migrate the first override families: Mistral/Pixtral dtype, MiniMaxM2,
  MiMoV2 (stack 7/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30069
captured_at: '2026-07-05T02:14:10.251976+00:00'
content_hash: d3f90b958d116c5dc8209c437f0e840caadc3370591abf9078f56843027f70f0
---
# [refactor] Migrate the first override families: Mistral/Pixtral dtype, MiniMaxM2, MiMoV2 (stack 7/15)

URL: https://github.com/sgl-project/sglang/pull/30069
State: closed
Labels: 
Closed at: 2026-07-04T09:21:33Z
Merged at: 2026-07-04T09:21:33Z

First arch families through the declarative pipeline; behavior
byte-identical via dual-apply. The unconditional-overwrite semantics
are ported faithfully; whitelist pin extends to {dtype,
enable_tf32_matmul, enable_multi_layer_eagle}. Golden diffs run the
full __post_init__ against local mini configs (the MistralLarge3/
Pixtral family is MLA-shaped, so the mini config carries the MLA shape
fields); config-shape-heavy families are pinned at the callable level.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 7/15 of the declarative config-resolution stack (based on `cheng/gc-pr-06`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)









































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701782953](https://github.com/sgl-project/sglang/actions/runs/28701782953)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28701782713](https://github.com/sgl-project/sglang/actions/runs/28701782713)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
