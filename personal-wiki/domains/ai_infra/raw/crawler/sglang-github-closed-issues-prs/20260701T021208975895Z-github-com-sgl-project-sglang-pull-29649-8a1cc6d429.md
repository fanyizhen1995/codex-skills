---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] keep image-model auxiliary components resident under auto memory
  policy'
canonical_url: https://github.com/sgl-project/sglang/pull/29649
captured_at: '2026-07-01T02:12:08.975895+00:00'
content_hash: 8a1cc6d42941f5baa30e2d83cf45e07e44b0cdfc7c53a39ed61ce250cd3b4058
---
# [diffusion] keep image-model auxiliary components resident under auto memory policy

URL: https://github.com/sgl-project/sglang/pull/29649
State: closed
Labels: run-ci, diffusion
Closed at: 2026-06-29T17:25:38Z
Merged at: 2026-06-29T17:25:38Z

## Motivation

[#26247](https://github.com/sgl-project/sglang/pull/26247)'s auto memory policy routes image-generation models through the generic layerwise-offload path, offloading their auxiliary components (text encoder, image encoder, VAE) to CPU. On a datacenter-class GPU with ample free memory this is pure overhead: nothing needs the freed VRAM, but every request pays a CPU→GPU reload — dominated by the text-encoder reload in the TextEncoding stage.

Two gaps made image models offload these components unconditionally, regardless of available memory:

1. Image models' `ModelDeploymentConfig` left the keep-resident threshold as `None`, so the high-memory residency filter early-returned and never kept anything resident.
2. The default resident set did not include `"vae"`.

## Changes

- add `"vae"` to the default `keep_resident_components`; exclude `"dit"` — DiT placement is owned by the FSDP / dit-layerwise policy, and forcing it resident would suppress FSDP sharding.
- new `ServerArgsAutoTuner._resolve_keep_resident_min_available_gb()`: explicit per-model config > task-type default (image 45 GB, video/mesh 120 GB).
- both auto-residency entry points route through the resolver.
- FastHunyuan: drop its 150 GB bar, use the global video default.
- rename `auto_disable_component_offload_*` → `keep_resident_*` (the old name read as a double negative) and trim the now-redundant comments.

## Effect

Image models keep their auxiliary components resident once available memory clears the (modality-specific) threshold; video models still offload below 120 GB available (VRAM preserved); FSDP/CFG decisions and explicitly-pinned models are unchanged.

## Test

- `test/unit/test_server_args.py` covers the per-modality residency, the sub-threshold offload path, and that multi-GPU image FSDP selection is unaffected.
- the diffusion nightly tracks the Z-Image fp8 end-to-end latency for this case.

















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28379623036](https://github.com/sgl-project/sglang/actions/runs/28379623036)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28379622946](https://github.com/sgl-project/sglang/actions/runs/28379622946)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
