---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Reorder ServerArgs sections common-first; inline LLAMA4/MIMO_V2
  arch tuples'
canonical_url: https://github.com/sgl-project/sglang/pull/30151
captured_at: '2026-07-06T02:14:53.060274+00:00'
content_hash: 20b9f6e35325bc9711f04f51862d828f95a03fe61847ef9f67b4a7ac353269b2
---
# [refactor] Reorder ServerArgs sections common-first; inline LLAMA4/MIMO_V2 arch tuples

URL: https://github.com/sgl-project/sglang/pull/30151
State: closed
Labels: run-ci
Closed at: 2026-07-05T19:17:24Z
Merged at: 2026-07-05T19:17:24Z

## Motivation

The ~39 field sections under `ServerArgs` had grown into an ad-hoc order (e.g. SSL/TLS was near the top, distributed parallelism was buried, perf/backend knobs were scattered). This PR reorders the sections into a **common-first** grouping so the most frequently used options appear first:

1. Core model & runtime config (model/tokenizer, quant/dtype, memory & scheduling, distributed parallelism, device)
2. Serving surface / API (HTTP server, SSL/TLS, API, streaming, logging/metrics, constrained decoding)
3. Performance & backend tuning (kernel backend, cuda graphs, communication, torch compile)
4. Optional features / model capabilities (spec decoding, EP, mamba, hierarchical cache, multimodal, LoRA, ...)
5. Advanced deployment (PD disaggregation, PD-multiplexing, weight update/loading)
6. Debug / experimental / extension (deterministic inference, KV canary, tensor dumps, hooks, ...)

It also inlines the `LLAMA4_MODEL_ARCHS` and `MIMO_V2_MODEL_ARCHS` tuples at their two use sites and drops the module-level constants.

## Modifications

- Move each `ServerArgs` field section as a whole block into the new order. Argparse args are auto-derived from field declaration order, so only the **relative order** of CLI arguments changes.
- Inline the two arch tuples; remove the now-unused constants.

## Correctness / no behavior change

This is a pure reorder. Verified by AST-diffing `ServerArgs` between `main` and this branch:

- 420 fields on both, identical field set
- **0** fields with a changed type annotation (which embeds `Arg(help=..., type_parser=..., choices=...)`)
- **0** fields with a changed default
- 402 of 420 declaration positions differ (the reorder)

Also verified via the auto-derived argparse metadata (435 CLI args): identical set, 0 content diffs (option strings / default / type / choices / help / nargs), only order differs.

## Checklist

- [x] No functional change (pure reorder + constant inlining)































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28736725143](https://github.com/sgl-project/sglang/actions/runs/28736725143)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28736725106](https://github.com/sgl-project/sglang/actions/runs/28736725106)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
