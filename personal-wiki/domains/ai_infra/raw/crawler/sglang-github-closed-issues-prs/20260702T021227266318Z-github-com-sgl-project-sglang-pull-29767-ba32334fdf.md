---
source_id: sglang-github-closed-issues-prs
title: '[CI] Relax ModelOpt NVFP4 diffusion consistency thresholds'
canonical_url: https://github.com/sgl-project/sglang/pull/29767
captured_at: '2026-07-02T02:12:27.266318+00:00'
content_hash: ba32334fdf0226b3d9c643aea8956b84cf8ef12f0808fa58ca423944168b1fde
---
# [CI] Relax ModelOpt NVFP4 diffusion consistency thresholds

URL: https://github.com/sgl-project/sglang/pull/29767
State: closed
Labels: run-ci, diffusion, run-ci-extra
Closed at: 2026-07-01T06:45:09Z
Merged at: 2026-07-01T06:45:09Z

## Summary

Relax two case-specific diffusion consistency thresholds for ModelOpt NVFP4 B200 CI:

- Add explicit thresholds for `flux2_modelopt_nvfp4_t2i`.
- Add explicit thresholds for `wan22_modelopt_nvfp4_t2v`.

This keeps the global image/video defaults unchanged and only covers the two cases that failed in PR #29315 base CI run 28428939882.

Observed failures from `call-multimodal-gen-tests / multimodal-gen-test-1-b200`:

- `flux2_modelopt_nvfp4_t2i`: clip `0.9908`, ssim `0.8864`, psnr `17.4954`, mean_abs_diff `8.7758`; old default thresholds were clip>=`0.92`, ssim>=`0.95`, psnr>=`28.0`, mean_abs_diff<=`8.0`.
- `wan22_modelopt_nvfp4_t2v`: clip `0.9978`, ssim `0.9097`, psnr `32.0379`, mean_abs_diff `4.3456`; old default video thresholds were clip>=`0.90`, ssim>=`0.92`, psnr>=`24.0`, mean_abs_diff<=`10.0`.

## Tests

```bash
python3 -m json.tool python/sglang/multimodal_gen/test/server/consistency_threshold.json >/tmp/consistency_threshold.json.checked
git diff --check
```

Also checked the observed failing metrics against the new thresholds locally.

Related failing CI: https://github.com/sgl-project/sglang/actions/runs/28428939882/job/84238725671?pr=29315





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28486788149](https://github.com/sgl-project/sglang/actions/runs/28486788149)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28486788052](https://github.com/sgl-project/sglang/actions/runs/28486788052)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
