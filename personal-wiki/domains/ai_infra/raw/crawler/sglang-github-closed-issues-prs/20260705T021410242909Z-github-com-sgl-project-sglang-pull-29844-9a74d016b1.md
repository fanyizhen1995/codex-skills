---
source_id: sglang-github-closed-issues-prs
title: '[CI] Revert ModelOpt NVFP4 threshold relax'
canonical_url: https://github.com/sgl-project/sglang/pull/29844
captured_at: '2026-07-05T02:14:10.242909+00:00'
content_hash: 9a74d016b14d3c7a5d16b3370abe561ac7bdc39d44749ee4fadb7e09c7197694
---
# [CI] Revert ModelOpt NVFP4 threshold relax

URL: https://github.com/sgl-project/sglang/pull/29844
State: closed
Labels: dependencies, Multi-modal, run-ci, diffusion, run-ci-extra
Closed at: 2026-07-04T13:17:33Z
Merged at: 2026-07-04T13:17:32Z

## Summary

- restore strict B200 consistency thresholds for the ModelOpt NVFP4 diffusion cases relaxed in #29767
- remove stale `nvidia-*-cu12` component wheels before CUDA 13 CI installs dependencies
- force-restore installed CUDA 13 NVIDIA component wheels when cuDNN files are missing after install
- fail early when Blackwell GitHub Actions jobs start without `CUDA_VISIBLE_DEVICES`, which indicates the shared runner did not assign an isolated GPU set
- move the new fused EH norm registered tests onto dispatchable Base CI stage/runner registrations
- install `pytest` in the Arm64 CPU CI image, matching the workflow that runs pytest-based registered CPU tests
- add `zstandard` to the CPU package dependencies for request decompression tests/runtime import parity

## Motivation

The NVFP4 threshold relaxations from #29767 masked a runner/environment problem instead of a model correctness issue. The bad B200 runs were on `b200-cirrascale2` with empty `CUDA_VISIBLE_DEVICES` and stale CUDA 12 NVIDIA wheels leaking into a CUDA 13 / torch 2.11 job. Clean B200 runs had an assigned GPU set and exact/strict consistency for the same target cases.

This keeps H100 behavior unchanged, but makes B200 override the inherited relaxed thresholds back to strict defaults so the CI catches the real environment issue. The CI dependency script now also cleans the stale CUDA 12 wheel set before CUDA 13 installation, restores CUDA 13 NVIDIA wheel files if critical runtime libraries such as `libcudnn.so.9` are missing, and refuses to continue if a Blackwell GitHub Actions job has no assigned `CUDA_VISIBLE_DEVICES`.

While monitoring the PR, CPU CI exposed two dependency gaps: the Arm64 image installed only the CPU runtime package even though the workflow runs pytest-based registered tests, and the CPU package missed `zstandard` even though the request decompression module imports it. The PR now fixes both with minimal dependency additions.

## Tests

- `python3 -m json.tool python/sglang/multimodal_gen/test/server/consistency_thresholds/b200.json`
- `bash -n scripts/ci/cuda/ci_install_dependency.sh`
- `python3 -m py_compile test/registered/jit/test_fused_eh_norm.py test/registered/jit/benchmark/bench_fused_eh_norm.py`
- `python3 -c "import tomllib; tomllib.load(open('python/pyproject_cpu.toml','rb'))"`
- `pre-commit run black-jupyter --files test/registered/jit/test_fused_eh_norm.py test/registered/jit/benchmark/bench_fused_eh_norm.py`
- `pre-commit run check-registered-tests --all-files`
- `git diff --check`
- direct JSON assertion for the B200 threshold overrides
- direct h100+b200 merge assertion matching the threshold loader behavior

Local import-level validation was not runnable on my macOS environment because the installed `transformers` package is broken there (`PreTrainedConfig` import failure), so I validated the JSON merge behavior directly.





















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28585249870](https://github.com/sgl-project/sglang/actions/runs/28585249870)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28585249742](https://github.com/sgl-project/sglang/actions/runs/28585249742)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
