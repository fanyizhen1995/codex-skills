---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Register quant/test_int8_kernel.py for AMD nightly CI'
canonical_url: https://github.com/sgl-project/sglang/pull/29698
captured_at: '2026-07-01T02:12:08.969499+00:00'
content_hash: e9cac1dc7f692942168d27ae99c4384aee1fc7c5f61a1d2603f0283a4927c5f1
---
# [AMD] Register quant/test_int8_kernel.py for AMD nightly CI

URL: https://github.com/sgl-project/sglang/pull/29698
State: closed
Labels: 
Closed at: 2026-06-30T00:38:49Z
Merged at: 

## Summary

Additive registration of `quant/test_int8_kernel.py` to the `nightly-amd-kernel-1-gpu` suite — one `register_amd_ci(...)` line plus `register_amd_ci` on the import. The existing `register_cuda_ci` is preserved; no other changes.

```python
register_cuda_ci(est_time=15, stage="base-b", runner_config="1-gpu-small")
register_amd_ci(est_time=15, suite="nightly-amd-kernel-1-gpu", nightly=True)
```

## Depends on #29694

This test exercises the int8 per-token quant Triton kernel, which currently uses a CUDA-only intrinsic (`tl.extra.cuda.libdevice.round`) that fails to compile on ROCm. **#29694** fixes that (HIP-guarded). This registration should merge **after** #29694, otherwise the AMD nightly job will fail at Triton compile.

## Verification (real MI35x, gfx950)

With #29694 applied, `quant/test_int8_kernel` passes on both ROCm stacks (1 test / 32 subtests, rel error ~3e-3 vs torch reference). Dispatched `nightly-amd-kernel-1-gpu` CI (branch carrying both the fix and this registration) — `test_int8_kernel` ran green (`passed: true`, ~29s, not skipped):
- ROCm 7.0 — [Run #28411605827](https://github.com/sgl-project/sglang/actions/runs/28411605827)
- ROCm 7.2 — [Run #28411606573](https://github.com/sgl-project/sglang/actions/runs/28411606573)

## Approach / scope

- Registration-only, additive; no common-code changes. `nightly-amd-kernel-1-gpu` is already wired in `nightly-test-amd.yml` / `nightly-test-amd-rocm720.yml`, so no workflow changes.
- `collect_tests(sanity_check=True)` + `validate_all_suites` pass; the test is collected into `nightly-amd-kernel-1-gpu`. The file has a `__main__` entry.

## Test plan

- [x] With #29694, `nightly-amd-kernel-1-gpu` runs `test_int8_kernel` green on ROCm 7.0 and 7.2.
- [x] No CUDA/MUSA behavior change (CUDA registration untouched).









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28411891872](https://github.com/sgl-project/sglang/actions/runs/28411891872)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28411891764](https://github.com/sgl-project/sglang/actions/runs/28411891764)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
