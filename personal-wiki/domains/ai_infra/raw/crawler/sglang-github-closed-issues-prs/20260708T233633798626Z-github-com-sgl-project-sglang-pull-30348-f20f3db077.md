---
source_id: sglang-github-closed-issues-prs
title: '[refactor] ctx.resources: named slots, stream leases, and workspace buffer
  leases'
canonical_url: https://github.com/sgl-project/sglang/pull/30348
captured_at: '2026-07-08T23:36:33.798626+00:00'
content_hash: f20f3db077c76054c06b87a3b42ce84fd2ddf727631ddf444660d451e31a6e4f
---
# [refactor] ctx.resources: named slots, stream leases, and workspace buffer leases

URL: https://github.com/sgl-project/sglang/pull/30348
State: closed
Labels: lora, ready-to-merge, blackwell, piecewise-cuda-graph, mthreads
Closed at: 2026-07-08T04:30:11Z
Merged at: 2026-07-08T04:30:11Z

## Motivation

Process-level resource handles were scattered as module singletons, each with its own get/set pair, no reset lifecycle, and monkeypatch-only test injection: the CUDA graph memory pool, the EPLB expert-distribution recorder (101 call sites), the publish-once expert-location metadata, the LPLB solver map, two side streams, a CUDA-event pool, and one lazily-created workspace buffer per attention backend. ~24 model files additionally each constructed their own alternate stream for intra-layer overlap.

## Modifications

- **`ctx.resources`**: named slots with one reset lifecycle and scoped `override()` injection. The owning accessors stay byte-identical shims (lazy pool creation, the noop recorder default, the publish-once assert, the HSA event-reuse contract).
- **Named stream leases — `ctx.get_stream(name)` / `set_stream(name, stream)`** (the keyed-lazy pattern of the persistent buffers): the DP-TBO comm stream and LoRA side stream become `"dp_tbo_comm"` / `"lora_side"` leases; the 24 per-model alternate streams lease one shared `"alt"` stream (per-site CUDA guards preserved; N duplicate driver streams → 1; intra-forward semantics unchanged since each instance already shared its single stream across layers).
- **Named buffer leases — `ctx.get_buffer(name, factory)`**: the uniform workspace family (flashinfer, flashinfer-MLA, the two zero-init TRT-LLM workspaces, DSA, MUSA MATE-MLA) body-swaps in; grow-only and device-checked variants (tokenspeed, SM120 page-split, Marlin LoRA) keep their exact semantics managing registry entries directly. Buffer names stay per-backend, matching today's footprint (same-size workspace sharing is a noted follow-up, not taken here).
- Two dead globals (compilation `global_graph_pool`, aiter workspace) deleted.

## Verification

Full unit suite name-identical to base; registry unit tests; GLM-4.7-Flash tp2 smokes (default backend for the alt-stream lease; `--attention-backend flashinfer` for the workspace lease).

Stacked on the runtime-flags PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28917598344](https://github.com/sgl-project/sglang/actions/runs/28917598344)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28917598376](https://github.com/sgl-project/sglang/actions/runs/28917598376)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
