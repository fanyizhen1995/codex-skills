---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Add --offload-during-compile to fit max-autotune on tight-memory
  GPUs'
canonical_url: https://github.com/sgl-project/sglang/pull/29862
captured_at: '2026-07-03T02:13:21.701246+00:00'
content_hash: 752dfe6db8620346e742fa9f03bde544d181c34643d93322b465e1433dc5d261
---
# [diffusion] Add --offload-during-compile to fit max-autotune on tight-memory GPUs

URL: https://github.com/sgl-project/sglang/pull/29862
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-02T11:39:20Z
Merged at: 2026-07-02T11:39:20Z

## Motivation

`max-autotune` (the default DiT `torch.compile` mode) needs substantially more peak GPU memory during compilation than steady-state inference does, so a large DiT can OOM at compile-warmup time on a GPU that comfortably fits inference — leaving no way to serve it compiled on that hardware.

Concretely, FLUX.2-dev 1024², TP=2 OOMs during the max-autotune warmup on both 2×H200 (peak ~123 GB/GPU) and 2×H100, even though resident inference fits.

## Modifications

Add `--offload-during-compile` (default on). **For the compile warmup only**, offload everything; after the warmup, serving runs with exactly the residency the user configured.

Server args are never mutated — `server_args` only gains the flag, and all mechanics live in `DenoisingStage`:

- **At stage init**, the DiT is layerwise-configured (`configure_layerwise_offload` stages weights to pinned CPU and installs per-layer hooks). Layerwise hooks introduce graph breaks, so each layer compiles/autotunes with only itself resident — this is what caps the compile-time peak.
- **During warmup denoising forwards**, resident non-DiT components (e.g. a resident VAE) are moved off-device and moved back right after the denoising returns. The bracket covers exactly the autotune window: the text encoder has already run, the VAE is back before decoding. Residency strategies and the `server_args` dump stay exactly as configured.
- **On the first real forward**, the DiT is restored to resident (`disable_offload`) — a one-time cost absorbed before serving traffic.
- Skipped when the DiT is already layerwise-offloaded (user-configured), when warmup is disabled (nothing to bracket), under cache-dit / FSDP, or for `DenoisingStage` subclasses that override `forward` (they would never run the restore).

Files: `server_args.py` (+7 lines, flag only), `denoising.py` (stage-local implementation).

## Accuracy Tests

No model code or compute-graph change — this only controls where weights reside during the compile warmup. Equivalence spot-check (Z-Image-Turbo 1024², 9 steps, compile-on, 2×H100, back-to-back runs on the same GPUs): steady-state single-request latency **1.082 s** with the flag off (resident compile) vs **1.078 s** with the flag on. Happy to add an accuracy CI case.

## Speed Tests and Profiling

FLUX.2-dev 1024², 50 steps, TP=2, max-autotune:

| | compile warmup | steady-state |
|---|---|---|
| 2×H200, without flag | **OOM** (peak ~123 GB/GPU) | — |
| 2×H200, with flag | fits (peak ~41 GB/GPU) | ~12.8 s single-request |
| 2×H100, without flag | **OOM** | — |
| 2×H100, with flag | fits (peak ~42 GB/GPU) | 13.1 s single-request, serves resident |

Small models are unaffected (Z-Image: 1.078 s vs 1.082 s baseline).

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Provide accuracy and speed benchmark results.

🤖 Generated with [Claude Code](https://claude.com/claude-code)









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28584386409](https://github.com/sgl-project/sglang/actions/runs/28584386409)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28584386229](https://github.com/sgl-project/sglang/actions/runs/28584386229)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
