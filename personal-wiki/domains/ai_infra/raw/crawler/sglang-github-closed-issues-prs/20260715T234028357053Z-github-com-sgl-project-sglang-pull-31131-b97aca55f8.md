---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix DSV4 JIT build on rocm '
canonical_url: https://github.com/sgl-project/sglang/pull/31131
captured_at: '2026-07-15T23:40:28.357053+00:00'
content_hash: b97aca55f846deba76008987f1b0416d8d6db3e4f8cc0eaf5b0b8f19dbd9c596
---
# [AMD] Fix DSV4 JIT build on rocm 

URL: https://github.com/sgl-project/sglang/pull/31131
State: closed
Labels: high priority, run-ci, jit-kernel
Closed at: 2026-07-15T16:58:13Z
Merged at: 2026-07-15T16:58:13Z

## Motivation

The Jul-14 scheduled Nightly Test (AMD MI355X 2N 1P1D Disagg) (run 29305625618) failed on every DeepSeek-V4 config (flash/pro × fp8/fp4 × base/dp8ep8/mtp) at scheduler init:

    utils.cuh:245: error: use of undeclared identifier 'cudaDevAttrComputeCapabilityMajor' → ninja exited with status 1 → Rank 0 scheduler died during initialization (exit code: -3)

#30438 added getSMVersion() to jit_kernel/include/sgl_kernel/utils.cuh using the CUDA-only enums cudaDevAttrComputeCapabilityMajor/Minor. The JIT path (tvm-ffi + hipcc) does not run hipify — unlike the compiled sgl-kernel, whose ROCm build hipifies cudaDevAttr* → hipDeviceAttribute* — so on gfx950 those identifiers are undeclared, the DeepSeek-V4 compress-plan JIT fails to build, and the scheduler dies. (Kimi-K2.6 doesn't build this JIT, so it was unaffected.)

## Modifications

Adopting the reviewed approach from #31141 (thanks @kangwangamd, @DarkSharpness): instead of guarding the CUDA-only calls with `#ifndef USE_ROCM`, **move `getSMVersion` out of `utils.cuh` into `runtime.cuh`**, where the `cuda*`→`hip*` attribute shims already live — so it compiles on both CUDA and HIP with no guard.

- Add the `cudaDevAttrComputeCapabilityMinor` → `hipDeviceAttributeComputeCapabilityMinor` `#define` (the Major one was already present).
- Add `get_cc_minor()` mirroring the existing `get_cc_major()`, and express `get_sm_version(id) = get_cc_major(id) * 10 + get_cc_minor(id)` to deduplicate the compute-capability queries.
- Remove `getSMVersion` from `utils.cuh`. It has **no caller in the JIT tree** (its only reference was its own definition; SM120 gating is done in Python via `is_sm120_supported()`), so there is no use-site change. No CUDA-path behavior change.


## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29352408580](https://github.com/sgl-project/sglang/actions/runs/29352408580)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29384613963](https://github.com/sgl-project/sglang/actions/runs/29384613963)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
