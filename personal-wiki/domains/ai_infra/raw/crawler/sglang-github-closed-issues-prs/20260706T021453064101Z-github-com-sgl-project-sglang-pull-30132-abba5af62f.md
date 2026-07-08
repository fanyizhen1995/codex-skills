---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Resolve the DSA and split attention backends into the flags tier
  (stack 6/10)'
canonical_url: https://github.com/sgl-project/sglang/pull/30132
captured_at: '2026-07-06T02:14:53.064101+00:00'
content_hash: abba5af62f08442723e6a320d5e7208cfd446972d644f52378e106f25872ce58
---
# [refactor] Resolve the DSA and split attention backends into the flags tier (stack 6/10)

URL: https://github.com/sgl-project/sglang/pull/30132
State: closed
Labels: deepseek
Closed at: 2026-07-05T07:01:44Z
Merged at: 

Unit 6 of a 10-PR stack continuing the config-resolution pipeline refactor (previous stack: #30063–#30077). Based on #30131.

_set_default_dsa_backends (including the hisparse arm from
arg_groups/hisparse_hook.py) becomes the slot pass
_dsa_split_backend_resolution, reading the mid-resolution kv-cache dtype and
the device capability exactly like the legacy in-branch fill; the hisparse
policy tests drive the pass through its read-only view.

prefill/decode_attention_backend join the resolvable whitelist with mapped
leaves (attn.prefill_backend / attn.decode_backend), and their post-CLI
writers become declarative, latest first: the CuteDSL decode-only validation
+ prefill fill becomes the slot pass _cutedsl_prefill_backend_fill; the
MossVL branch dissolves into the registry callable _moss_vl_overrides; the
DeepSeek V4 NPU split pins move from the hook into the dispatch declaration.
The NPU early-handler writes stay imperative as earlier writers.
dsa_prefill_backend / dsa_decode_backend get flat flag leaves.

🤖 Generated with [Claude Code](https://claude.com/claude-code)













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28721912673](https://github.com/sgl-project/sglang/actions/runs/28721912673)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28721912609](https://github.com/sgl-project/sglang/actions/runs/28721912609)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
