---
source_id: sglang-github-closed-issues-prs
title: Fix diffusion BCG lifetime and add Z-Image-Turbo CI
canonical_url: https://github.com/sgl-project/sglang/pull/30584
captured_at: '2026-07-10T23:37:20.323719+00:00'
content_hash: 3b9821cacbeb19816541854dbaa1ac862298ae0e16f61ac54b6d1671b7d038a3
---
# Fix diffusion BCG lifetime and add Z-Image-Turbo CI

URL: https://github.com/sgl-project/sglang/pull/30584
State: closed
Labels: performance, Multi-modal, ci, run-ci, piecewise-cuda-graph, diffusion, bypass-fastfail, run-ci-extra
Closed at: 2026-07-10T13:20:00Z
Merged at: 2026-07-10T13:20:00Z

## Summary
- keep BCG eager breakpoint outputs strongly referenced during replay so downstream graph segments keep a valid bridge-buffer address
- add a CUDA regression test that asserts the eager output bridge buffer is held strongly
- add diffusion unit coverage that the image-generation BCG allowlist stays registered
- add a standalone H100 `bcg-diffusion` CI job that runs real Z-Image-Turbo BCG generation through `sglang generate`

## Regression boundary
- `25d2266699` from the old #27436 force-push line uses `captured_output = output` and Z-Image-Turbo true BCG passes.
- Final #27436 head `28c1c28946`, merge commit `33c3dfd7e0`, and current main use `captured_output = _weak_ref_if_tensor(output)`.
- There is no later main commit after `33c3dfd7e0` that touched the relevant BCG/Z-Image paths; the weak-ref version was already present when #27436 merged.
- With the #27436 body `--performance-mode speed` command, final head logs BCG capture failures and runs eager for Z-Image-Turbo. Forcing true BCG with torch.compile/offload disabled reproduces the segfault in `copy_ -> cudaMemcpyAsync/cuMemcpyDtoDAsync`.

## Testing
- `python3 -m py_compile python/sglang/multimodal_gen/test/single_test_file/test_diffusion_bcg_zimage_turbo.py python/sglang/multimodal_gen/test/server/gpu_cases.py python/sglang/multimodal_gen/test/run_suite.py`
- `python3 -m ruff check ...`
- `python3 -m ruff format --check ...`
- `git diff --check`
- Ruby YAML parse for `.github/workflows/pr-test-multimodal-gen.yml` and `.github/workflows/_pr-test-check-changes.yml`
- `pytest -q python/sglang/multimodal_gen/test/unit/test_diffusion_bcg_padding.py -q` on ion8-h200 container: 16 passed
- `pytest -q test/registered/cuda_graph/breakable/test_breakable_cuda_graph.py::TestBreakableCUDAGraphBasic::test_eager_output_is_held_strongly_for_replay_bridge -q` on ion8-h200 container: passed
- `python3 sglang/multimodal_gen/test/run_suite.py --suite bcg-diffusion` on ion8-h200 container: 1 passed; real Z-Image-Turbo native backend, 512x512, 9 steps, `--enable-breakable-cuda-graph --bcg-text-buckets 128 --enable-torch-compile false --dit-layerwise-offload false --dit-cpu-offload false`; capture succeeded with 35 segments and generation completed

No diffusion server smoke cases are added in this PR; the new CI coverage uses real Z-Image-Turbo BCG generation.

























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29078508002](https://github.com/sgl-project/sglang/actions/runs/29078508002)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29078507861](https://github.com/sgl-project/sglang/actions/runs/29078507861)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
