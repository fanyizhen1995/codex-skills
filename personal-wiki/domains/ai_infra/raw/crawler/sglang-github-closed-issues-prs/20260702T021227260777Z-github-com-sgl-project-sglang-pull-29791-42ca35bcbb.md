---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Add 5090 diffusion consumer GPU guard'
canonical_url: https://github.com/sgl-project/sglang/pull/29791
captured_at: '2026-07-02T02:12:27.260777+00:00'
content_hash: 42ca35bcbbd2dbad0b8511c278aa0ed4368d122b1a5db1c37a127573814662d3
---
# [diffusion] Add 5090 diffusion consumer GPU guard

URL: https://github.com/sgl-project/sglang/pull/29791
State: closed
Labels: Multi-modal, DO NOT MERGE, run-ci, diffusion
Closed at: 2026-07-01T11:09:43Z
Merged at: 2026-07-01T11:09:43Z

## Summary

Add a lightweight SGLang-Diffusion PR canary job for the `1-gpu-5090` consumer Blackwell runner.

This now also folds in the platform baseline split from #29805:

- diffusion perf baselines live under `test/server/perf_baselines/` with H100, B200, and 5090 files
- 5090 perf baselines come from real CI history: [run `28492141274`, job `84450974283`](https://github.com/sgl-project/sglang/actions/runs/28492141274/job/84450974283?pr=29791), runner `5090-d-runner-3`
- consistency thresholds live under `test/server/consistency_thresholds/` with platform override files
- consistency GT lookup can prefer platform subdirectories such as `sglang_generated/5090/` and fall back to the existing shared GT files

It also adds targeted guardrails for recent consumer-GPU regressions:

- `flux_image_t2i_layerwise_cpu_offload_5090` exercises the #18997 failure mode where explicit `--dit-cpu-offload` must stay enabled with `--dit-layerwise-offload` for low-VRAM cards.
- `turbo_wan2_1_t2v_1.3b` plus a CPU unit test guard TurboWan sparse-attention backend fallback on consumer-level GPU CI.

## 5090 consistency policy

The previous 5090 run showed two different classes of consistency drift:

- `zimage_image_t2i` only missed the H100-derived PSNR threshold slightly, so the 5090 threshold override keeps that case as a consistency guard.
- `wan2_1_t2v_1.3b` produced visually different frames under the 5090 path, so the 5090 canary keeps perf coverage for it but does not compare against H100 GT until 5090-specific GT is added.

## Validation

- `pre-commit run --files .github/workflows/pr-test-multimodal-gen.yml python/sglang/multimodal_gen/test/server/gpu_cases.py python/sglang/multimodal_gen/test/server/test_server_1_gpu_5090.py python/sglang/multimodal_gen/test/unit/test_turbo_wan_backend.py python/sglang/multimodal_gen/test/scripts/gen_perf_baselines.py python/sglang/multimodal_gen/test/server/testcase_configs.py python/sglang/multimodal_gen/test/server/test_server_common.py scripts/ci/utils/diffusion/diffusion_case_parser.py python/sglang/multimodal_gen/test/server/perf_baselines/h100.json python/sglang/multimodal_gen/test/server/perf_baselines/b200.json python/sglang/multimodal_gen/test/server/perf_baselines/5090.json python/sglang/multimodal_gen/test/test_utils.py python/sglang/multimodal_gen/test/unit/test_consistency_metrics.py python/sglang/multimodal_gen/test/server/consistency_thresholds/h100.json python/sglang/multimodal_gen/test/server/consistency_thresholds/b200.json python/sglang/multimodal_gen/test/server/consistency_thresholds/5090.json`













<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28503132678](https://github.com/sgl-project/sglang/actions/runs/28503132678)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28503132372](https://github.com/sgl-project/sglang/actions/runs/28503132372)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
