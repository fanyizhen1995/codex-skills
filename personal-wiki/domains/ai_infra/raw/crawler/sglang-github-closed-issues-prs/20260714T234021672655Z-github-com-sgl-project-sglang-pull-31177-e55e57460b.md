---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Support fal Ideogram V4 Fast and Instant'
canonical_url: https://github.com/sgl-project/sglang/pull/31177
captured_at: '2026-07-14T23:40:21.672655+00:00'
content_hash: e55e57460baaf2f68c623cce8be96f2364ad40c307ed78b7f3ad38ad08d273cb
---
# [Diffusion] Support fal Ideogram V4 Fast and Instant

URL: https://github.com/sgl-project/sglang/pull/31177
State: closed
Labels: documentation, run-ci, diffusion
Closed at: 2026-07-14T11:51:36Z
Merged at: 2026-07-14T11:51:36Z

## Summary

- add fully native single-branch pipelines for `fal/ideogram-v4-fast` and `fal/ideogram-v4-instant`
- resolve the transformer-only repositories against the pinned Ideogram NF4 tokenizer, text encoder, VAE, and scheduler components
- load the distilled floating-point DiTs with TP-aware unquantized linears and Diffusers attention weight mappings
- support TP, Ulysses sequence parallelism, and DiT layerwise offload while replicating the bitsandbytes NF4 text encoder under TP
- add Fast/Instant sampling presets, compatibility inventory entries, cookbook guidance, and unit coverage

## Motivation

The fal Fast and Instant releases are gated, transformer-only distilled checkpoints. The existing Ideogram pipeline expected both conditional and unconditional transformers and defaulted to the official row-wise FP8 linear path, so these checkpoints could not be loaded or executed correctly.

This change reuses the native Ideogram stages with a single denoiser branch, selects the correct floating-point linear implementation, and downloads only the shared components referenced by the model cards.

## User impact

Users with access to the gated repositories can pass either fal model ID directly to `sglang generate` or `sglang serve`. The cookbook documents the required dependencies, structured caption format, TP2/Ulysses2 commands, layerwise offload, and the Fast checkpoint's NVFP4 quality caveat.

## Validation

- `pre-commit run --from-ref origin/main --to-ref HEAD`
- `python -m pytest -q python/sglang/multimodal_gen/test/unit/test_ideogram4.py python/sglang/multimodal_gen/test/unit/test_diffusion_bcg_padding.py` (64 passed)
- real-weight generation for both variants in single-GPU, TP2, and Ulysses2 layouts
- real-weight Instant generation with transformer layerwise offload enabled











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29321089973](https://github.com/sgl-project/sglang/actions/runs/29321089973)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29321089955](https://github.com/sgl-project/sglang/actions/runs/29321089955)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
