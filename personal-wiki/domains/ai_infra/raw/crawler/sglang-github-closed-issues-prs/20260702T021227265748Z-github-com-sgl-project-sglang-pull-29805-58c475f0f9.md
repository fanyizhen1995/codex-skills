---
source_id: sglang-github-closed-issues-prs
title: Split diffusion perf baselines by GPU platform
canonical_url: https://github.com/sgl-project/sglang/pull/29805
captured_at: '2026-07-02T02:12:27.265748+00:00'
content_hash: 58c475f0f95acd81b371645a7e154a7c591afb6fb0f5848b4c030c8ecec233f5
---
# Split diffusion perf baselines by GPU platform

URL: https://github.com/sgl-project/sglang/pull/29805
State: closed
Labels: diffusion
Closed at: 2026-07-01T06:50:50Z
Merged at: 

## Summary
- move diffusion perf baselines into `test/server/perf_baselines/` with `h100.json`, `b200.json`, and `5090.json`
- select the runtime baseline file from the detected GPU platform, with `SGLANG_DIFFUSION_PERF_BASELINE_PLATFORM` as an override
- keep CI case-parser estimates compatible with the platform baseline directory

## 5090 baseline source
- real CI history from PR #29791: [run `28492141274`, job `84450974283`](https://github.com/sgl-project/sglang/actions/runs/28492141274/job/84450974283?pr=29791), runner `5090-d-runner-3`
- added the 5090 cases that produced perf data in that job: `flux_2_klein_base_image_t2i`, `wan2_1_t2v_1.3b`, `zimage_image_t2i`
- did not add `turbo_wan2_1_t2v_1.3b` or `flux_image_t2i_layerwise_cpu_offload_5090` because that run did not produce usable perf metrics for them

## Test Plan
- `python -m json.tool python/sglang/multimodal_gen/test/server/perf_baselines/h100.json`
- `python -m json.tool python/sglang/multimodal_gen/test/server/perf_baselines/b200.json`
- `python -m json.tool python/sglang/multimodal_gen/test/server/perf_baselines/5090.json`
- parser smoke test for `load_baselines(Path("python/sglang/multimodal_gen/test/server/perf_baselines"))`
- `pre-commit run --files python/sglang/multimodal_gen/test/scripts/gen_perf_baselines.py python/sglang/multimodal_gen/test/server/testcase_configs.py python/sglang/multimodal_gen/test/server/test_server_common.py scripts/ci/utils/diffusion/diffusion_case_parser.py python/sglang/multimodal_gen/test/server/perf_baselines/h100.json python/sglang/multimodal_gen/test/server/perf_baselines/b200.json python/sglang/multimodal_gen/test/server/perf_baselines/5090.json`











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28493977998](https://github.com/sgl-project/sglang/actions/runs/28493977998)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28493977893](https://github.com/sgl-project/sglang/actions/runs/28493977893)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
