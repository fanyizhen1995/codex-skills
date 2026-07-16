---
source_id: sglang-github-closed-issues-prs
title: Add diffusion BCG prompt conditioning guard
canonical_url: https://github.com/sgl-project/sglang/pull/30782
captured_at: '2026-07-11T23:37:37.771698+00:00'
content_hash: 543e39b7c9d9bf58aacb6c3ac6373810a404752a57c5bf00fbb853b364def2b0
---
# Add diffusion BCG prompt conditioning guard

URL: https://github.com/sgl-project/sglang/pull/30782
State: closed
Labels: Multi-modal, ci, run-ci, piecewise-cuda-graph, diffusion, bypass-fastfail
Closed at: 2026-07-11T05:14:32Z
Merged at: 2026-07-11T05:14:32Z

## Summary

- Extend the existing Z-Image-Turbo BCG CI file with an end-to-end prompt-switch reuse guard.
- The guard starts one BCG-enabled diffusion server, lets server warmup capture BCG, then sends two same-seed 512x512 image requests with different prompts.
- It asserts both requests return image data and the server log contains exactly one `[Diffusion BCG] captured` line, proving the prompt switch reused the already captured BCG instead of triggering another capture.
- Keep the coverage in the existing `bcg-diffusion` standalone file and update its estimated runtime to 420s.

## Validation

Local static/lint checks on latest pushed commit `b6df448cfe`:

```bash
python3 -m py_compile \
  python/sglang/multimodal_gen/test/single_test_file/test_diffusion_bcg_zimage_turbo.py \
  python/sglang/multimodal_gen/test/server/gpu_cases.py
python3 -m isort --check-only \
  python/sglang/multimodal_gen/test/single_test_file/test_diffusion_bcg_zimage_turbo.py
python3 -m ruff check \
  python/sglang/multimodal_gen/test/single_test_file/test_diffusion_bcg_zimage_turbo.py \
  python/sglang/multimodal_gen/test/server/gpu_cases.py
python3 -m black --check \
  python/sglang/multimodal_gen/test/single_test_file/test_diffusion_bcg_zimage_turbo.py \
  python/sglang/multimodal_gen/test/server/gpu_cases.py
git diff --check
SKIP=no-commit-to-branch pre-commit run --all-files --show-diff-on-failure
```

H200 end-to-end run on final pushed branch commit `b6df448cfe`:

```bash
cd /tmp/sglang_diffusion_bcg_guard_b6df
CUDA_VISIBLE_DEVICES=0 FLASHINFER_DISABLE_VERSION_CHECK=1 PYTHONPATH=python \
  python python/sglang/multimodal_gen/test/run_suite.py --suite bcg-diffusion
```

Result:

```text
2 passed, 20 warnings in 91.12s (0:01:31)
```

Reuse evidence from the same run:

- Warmup captured BCG once: `[Diffusion BCG] captured 35 segment(s), 10 tensor input(s)`.
- Two different prompt requests both returned `POST /v1/images/generations` 200 and non-empty image data.
- No second capture log appeared during the prompt switch path; the guard asserts `server_log.count("[Diffusion BCG] captured") == 1`.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29099408554](https://github.com/sgl-project/sglang/actions/runs/29099408554)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29101538469](https://github.com/sgl-project/sglang/actions/runs/29101538469)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
