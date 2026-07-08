---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Refactor diffusion weight load planning'
canonical_url: https://github.com/sgl-project/sglang/pull/30118
captured_at: '2026-07-06T02:14:53.066287+00:00'
content_hash: 756ec51f2eefbc16944d233b14a41dc37be165a4f9967768231b393d947f6500
---
# [diffusion] Refactor diffusion weight load planning

URL: https://github.com/sgl-project/sglang/pull/30118
State: closed
Labels: quant, run-ci, diffusion
Closed at: 2026-07-05T03:59:50Z
Merged at: 2026-07-05T03:59:50Z

## Why

#29903 fixed the immediate online FP8 + `dit_cpu_offload` crash by keeping weights on device until `process_weights_after_loading` finished. That fix is correct for the bug, but the decision is really a load-time placement policy rather than a server-args/runtime residency policy.

This PR makes that policy explicit with `WeightLoadPlan`. The goal is to keep these decisions separate:

- checkpoint materialization: where tensors are loaded from files
- weight postprocessing: where online quantization or `process_weights_after_loading` must run
- final runtime residency: still controlled by existing server args/offload behavior

For the online quant + DiT CPU offload case, this lets the loader naturally do `file -> GPU`, run quant/post-load weight processing on GPU, then move `GPU -> CPU` for component offload. It avoids mutating server args and avoids spreading one-off quant/offload conditionals through component loaders.

## What Changed

- Add `WeightLoadPlan` for checkpoint load device, optional weight-postprocess device, and deferred component CPU offload.
- Route transformer and bridge FSDP loading through the plan while preserving existing server-args semantics for runtime residency.
- Mark online FP8/MXFP4 as requiring device-side weight postprocessing when the checkpoint is not already serialized in that quantized format.
- Keep FSDP CPU offload behavior unchanged by ignoring deferred component offload/postprocess-device overrides for FSDP offload.
- Split component loader customized/native load context handling into focused helper methods so placement-specific logic is not mixed into the top-level load flow.

## Behavior Impact

- Online quant + `dit_cpu_offload=True`: load checkpoint tensors on the local device, run weight postprocessing there, then offload the component to CPU.
- Serialized quantized checkpoints: no extra device postprocess requirement is introduced.
- Bridge/native component loading: no intended behavior change beyond passing the default plan through the common loader path.
- Server args remain the source of truth for runtime residency; this PR only clarifies the load-time plan used to reach that state.

## Tests

- `python -m py_compile python/sglang/multimodal_gen/runtime/loader/weight_load_plan.py python/sglang/multimodal_gen/runtime/loader/fsdp_load.py python/sglang/multimodal_gen/runtime/loader/transformer_load_utils.py python/sglang/multimodal_gen/runtime/loader/component_loaders/transformer_loader.py python/sglang/multimodal_gen/runtime/loader/component_loaders/bridge_loader.py python/sglang/multimodal_gen/test/unit/test_transformer_quant.py`
- `python -m ruff check python/sglang/multimodal_gen/runtime/loader/weight_load_plan.py python/sglang/multimodal_gen/runtime/loader/fsdp_load.py python/sglang/multimodal_gen/runtime/loader/transformer_load_utils.py python/sglang/multimodal_gen/runtime/loader/component_loaders/transformer_loader.py python/sglang/multimodal_gen/runtime/loader/component_loaders/bridge_loader.py`
- `python -m ruff check --select F,E9 python/sglang/multimodal_gen/test/unit/test_transformer_quant.py`
- `git diff --check`
- Commit pre-check hooks

Targeted pytest is blocked in this local macOS environment while importing CUDA-only runtime code: `cannot import name '_cuda_beginAllocateCurrentThreadToPool' from 'torch.cuda.memory'`.





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28727859066](https://github.com/sgl-project/sglang/actions/runs/28727859066)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28727859026](https://github.com/sgl-project/sglang/actions/runs/28727859026)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
