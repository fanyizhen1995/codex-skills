---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Resolve the kv-cache dtype into the flags tier (stack 5/10)'
canonical_url: https://github.com/sgl-project/sglang/pull/30131
captured_at: '2026-07-06T02:14:53.064348+00:00'
content_hash: 995eb9f5a82946538a2ad73990e813cefac1f48f357502fbe3fe991a2301041e
---
# [refactor] Resolve the kv-cache dtype into the flags tier (stack 5/10)

URL: https://github.com/sgl-project/sglang/pull/30131
State: closed
Labels: deepseek
Closed at: 2026-07-05T07:01:42Z
Merged at: 

Unit 5 of a 10-PR stack continuing the config-resolution pipeline refactor (previous stack: #30063–#30077). Based on #30130.

kv_cache_dtype joins the resolvable whitelist with a flat flag leaf, and
every post-CLI writer becomes declarative: the weight-resolved auto+FP8
write in configure_kv_cache_dtype goes through declare_load_time_override
(mock runners whose server_args is not the published object keep the plain
write); the DSA device-capability default becomes the slot pass
_dsa_kv_cache_dtype_default; and the DeepSeek V4 hook's kv writes become
_deepseek_v4_kv_cache_dtype (the NPU bfloat16 pin folds into the
declaration). Validation asserts ride inside the passes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28721912178](https://github.com/sgl-project/sglang/actions/runs/28721912178)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28721912103](https://github.com/sgl-project/sglang/actions/runs/28721912103)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
