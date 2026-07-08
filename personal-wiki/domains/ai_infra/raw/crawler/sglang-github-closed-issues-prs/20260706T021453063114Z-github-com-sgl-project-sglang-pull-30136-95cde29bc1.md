---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Flip the readers of resolved fields to the flags tier (stack 10/10)'
canonical_url: https://github.com/sgl-project/sglang/pull/30136
captured_at: '2026-07-06T02:14:53.063114+00:00'
content_hash: 95cde29bc17107e7fa1b17eebb54e9691e0d5b55ca8ca59d0e0258db25f1ff80
---
# [refactor] Flip the readers of resolved fields to the flags tier (stack 10/10)

URL: https://github.com/sgl-project/sglang/pull/30136
State: closed
Labels: amd, deepseek
Closed at: 2026-07-05T07:01:55Z
Merged at: 

Unit 10 of a 10-PR stack continuing the config-resolution pipeline refactor (previous stack: #30063–#30077). Based on #30135.

Mechanical sweep over unambiguous post-publish reads of fully-declared
fields: disable_shared_experts_fusion (all model-file readers),
enable_dp_lm_head (all 40 LM-head constructions plus the logits-processor
init), sampling_backend (the sampler), enable_tf32_matmul (ModelRunner),
attention_backend runtime reads (two-batch overlap, mem-cache alloc paths,
mrope, GptOss sink init — the mapped leaf get_flags().attn.backend), and
the three MTP draft quantization reads. Dual-apply keeps each leaf and its
server_args field in lockstep at every read point, so the flips are
behavior-identical.

Stash-less dataclass publishes (mock ServerArgs fixtures, dummy-path
instances that skipped the monolith) now materialize the whitelist from
their own fields, so flag reads match legacy server_args reads on published
mocks; field-less sentinel publishes still skip. Five tests migrate from
getter monkeypatches to the flags tier. Ratchet baseline 341 -> 278.

🤖 Generated with [Claude Code](https://claude.com/claude-code)













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28721914512](https://github.com/sgl-project/sglang/actions/runs/28721914512)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28721914452](https://github.com/sgl-project/sglang/actions/runs/28721914452)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
