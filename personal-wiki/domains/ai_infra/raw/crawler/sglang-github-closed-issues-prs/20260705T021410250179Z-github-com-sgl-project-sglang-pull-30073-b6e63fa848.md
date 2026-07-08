---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Migrate the attention_backend resolution chain (stack 11/15)'
canonical_url: https://github.com/sgl-project/sglang/pull/30073
captured_at: '2026-07-05T02:14:10.250179+00:00'
content_hash: b6e63fa848c2028713c49af498e1e888409b9df9f8d5eb80105209670e905a98
---
# [refactor] Migrate the attention_backend resolution chain (stack 11/15)

URL: https://github.com/sgl-project/sglang/pull/30073
State: closed
Labels: 
Closed at: 2026-07-04T09:22:17Z
Merged at: 2026-07-04T09:22:17Z

attention_backend enters the pipeline back-to-front, last writer first:
- DLLM platform forcing (HIP/NPU/cuda-graph) — attention_backend is
  whitelisted with the first mapped leaf, flags.attn.backend.
- The compatibility handler's six write sites become four
  slot-preserving passes (default fill via the pure-read
  _get_default_attn_backend, fa3+fp8 fallback, intel amx/xmx hardware
  fallbacks, dual-chunk fill + mismatch error): a single
  head-of-handler extraction would change what interleaved readers
  observe mid-chain, so each pass keeps its exact legacy slot.
- The deterministic-inference platform/DeepSeek-conditional fill.
- Nine arch families' branch selections join their callables (GptOss,
  Step3p, Olmo2, Llama4 incl. its cpu-device guard, Gemma4 both fill
  paths, MiniCPMV4_6, FalconH1/Jet, GraniteMoeHybrid with its
  layer_types guard, Lfm2); branch asserts/logs that read the value
  observe the dual-applied result exactly as they observed the legacy
  writes. Platform paths are pinned with patched-probe callable tests.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---
Part 11/15 of the declarative config-resolution stack (based on `cheng/gc-pr-10`). Full-stack CI runs on the top PR #30062; `run-ci` is added per PR as it reaches the front of the merge order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)





















































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28701800353](https://github.com/sgl-project/sglang/actions/runs/28701800353)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28701800216](https://github.com/sgl-project/sglang/actions/runs/28701800216)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
