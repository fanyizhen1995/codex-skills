---
source_id: sglang-github-closed-issues-prs
title: 'docs: add PD disaggregation to GLM-5.2 cookbook playground'
canonical_url: https://github.com/sgl-project/sglang/pull/29544
captured_at: '2026-07-03T02:13:21.697582+00:00'
content_hash: 6bb7701cbfabf2881b1e904c8bfac93a053489ed8846b52fd498c0c4247a9089
---
# docs: add PD disaggregation to GLM-5.2 cookbook playground

URL: https://github.com/sgl-project/sglang/pull/29544
State: closed
Labels: documentation
Closed at: 2026-07-02T16:57:39Z
Merged at: 2026-07-02T16:57:39Z

## Motivation

GLM-5.2 uses the `glm_moe_dsa` architecture — the same DeepSeek Sparse Attention (DSA) family as DeepSeek-V3.2 / V4 — which SGLang already supports under prefill/decode (PD) disaggregation. The GLM-5.2 cookbook page did not yet surface this, while its DSA sibling DeepSeek-V4 does. This exposes PD disaggregation in the GLM-5.2 Playground.

## Modifications

- **`docs_new/src/snippets/configs/zai-org/glm-5.2.jsx`** — add a `pdDisagg` Playground card (Mode: off / prefill / decode · Transfer Backend: Mooncake / NiXL · router template), mirroring the DeepSeek-V4 DSA config. Mooncake's NVLink-multinode `NCCL_MNNVL`/`MC_FORCE_MNNVL` env is gated to GB300 via `envWhen`. No IB-device knob — Mooncake auto-detects the HCA.
- **`docs_new/cookbook/autoregressive/GLM/GLM-5.2.mdx`** — add a *PD Disaggregation* Configuration-Tips bullet (router command, IB auto-detect + `--disaggregation-ib-device` fallback, H200 Docker IB-exposure caveat for Mooncake).
- **`docs_new/src/snippets/_playground.jsx`** (shared engine) — simplify the single-host PD port strategy: drop the auto-injected `--dist-init-addr` (that flag is the torch.distributed rendezvous, not the PD bootstrap) and space the role serve ports 100 apart (prefill `30000` / decode `30100`) so the derived ZMQ/dist port ranges (`--port + ZMQ_TCP_PORT_DELTA`, =233) no longer overlap between the two co-located engines. **Multi-node PD still gets a cross-node `--dist-init-addr` from the renderer.** This also cleans up DeepSeek-V4 / MiniMax-M3 / Laguna single-host PD commands (no behavior change beyond the dropped flag + decode port).

The shared `_playground.jsx` engine already supported `pdDisagg` (emits `--disaggregation-mode/-transfer-backend`, pins role serving ports), so the GLM addition itself needs no new engine plumbing.

## Checklist

- [x] `mint validate` passes
- [x] Rebased on latest `main` (incl. GLM-5.2 NVFP4 recipes)
- [ ] Mintlify preview reviewed
- [ ] Verify PD-disagg recipe end-to-end on hardware

> Draft: opening for docs preview. PD-disagg knobs are Playground (experiment-beyond-the-verified-matrix) controls, not new verified Deploy cells.

🤖 Generated with [Claude Code](https://claude.com/claude-code)











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28476273251](https://github.com/sgl-project/sglang/actions/runs/28476273251)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28476272981](https://github.com/sgl-project/sglang/actions/runs/28476272981)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
