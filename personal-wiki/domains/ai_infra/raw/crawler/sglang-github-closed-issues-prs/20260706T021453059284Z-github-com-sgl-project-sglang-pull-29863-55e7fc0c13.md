---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Refresh LTX HQ consistency GT'
canonical_url: https://github.com/sgl-project/sglang/pull/29863
captured_at: '2026-07-06T02:14:53.059284+00:00'
content_hash: 55e7fc0c135a92a8677ed31439a5373139798da89af9163f1120764e969f5817
---
# [diffusion] Refresh LTX HQ consistency GT

URL: https://github.com/sgl-project/sglang/pull/29863
State: closed
Labels: diffusion
Closed at: 2026-07-06T01:27:58Z
Merged at: 

## Summary
- fix the diffusion GT generation script import after `collect_test_items` moved to `test.runner.pytest_runner`
- refresh `ltx_2_3_hq_pipeline` native CI GT under `sglang_generated` and pin ci-data to `9ec165b301fda67c54b1bb41ce14fe32c099f4cd`
- route `ltx_2_3_hq_pipeline` explicitly through `SGL_TEST_FILES_SGLANG_CONSISTENCY_GT_BASE` via `SGL_TEST_FILES_SGLANG_CONSISTENCY_GT_CASES`
- remove stale `official_generated/ltx_2_3_hq_pipeline_1gpu_frame_{0,mid,last}.png` files from ci-data so official-first lookup paths cannot select 1024x1024 GT
- tighten the H100 consistency threshold for `ltx_2_3_hq_pipeline` to near-exact matching
- add a unit guard that keeps LTX HQ on `sglang_generated` GT

## Validation
- GT generation: https://github.com/sgl-project/sglang/actions/runs/28537086966 (`multimodal-diffusion-gen-1gpu (2)` published ci-data commit `8db1f7d4da`)
- Consistency rerun: https://github.com/sgl-project/sglang/actions/runs/28537663480
- Metrics probe: https://github.com/sgl-project/sglang/actions/runs/28537969669 showed `sim=1.0000`, `ssim=1.0000`, `psnr=inf`, `mean_abs_diff=0.0000` against the refreshed GT
- ci-data cleanup revision `9ec165b301fda67c54b1bb41ce14fe32c099f4cd`: `official_generated` HQ frames are 404; `sglang_generated` HQ frames are 200
- H100 rerun https://github.com/sgl-project/sglang/actions/runs/28560345810 checked out `6f5a4fba28b` and passed consistency for `ltx_2_3_hq_pipeline`; the remaining failure in that run is unrelated performance baseline drift in `LTX2AVDecodingStage`









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28666932448](https://github.com/sgl-project/sglang/actions/runs/28666932448)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28666932339](https://github.com/sgl-project/sglang/actions/runs/28666932339)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
