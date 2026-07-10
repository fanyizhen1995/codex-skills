---
source_id: sglang-github-closed-issues-prs
title: '[SUPA][1/N] Add device detection and check_env support'
canonical_url: https://github.com/sgl-project/sglang/pull/30605
captured_at: '2026-07-09T23:36:35.339051+00:00'
content_hash: 379421bdee38320dfab9df9e40aec73662f5d69907f98328637d2e64b488f91a
---
# [SUPA][1/N] Add device detection and check_env support

URL: https://github.com/sgl-project/sglang/pull/30605
State: closed
Labels: 
Closed at: 2026-07-09T06:36:05Z
Merged at: 

## Motivation

Add Biren SUPA GPU backend support to SGLang. SUPA is the software stack for Biren GPUs (BR200 series). This is the first PR (1/N) in a series to enable SGLang inference on SUPA devices, starting with basic device detection and environment checking.

## Modifications

### `python/sglang/srt/utils/common.py`
- Add `is_supa()` detection function (cached) that checks `torch.supa.is_available()`
- Add SUPA branch in `get_device()` to return `"supa"` or `"supa:<id>"`
- Add SUPA to `get_device_count()`, `get_device_core_count()`, and `get_device_capability()` by extending existing CUDA/MUSA paths (SUPA uses PrivateUse1 mapped to `torch.cuda` APIs)
- Update error message to include SUPA in the list of supported accelerators

### `python/sglang/check_env.py`
- Import `is_supa` from `sglang.srt.utils`
- Add `SUPAEnv` class (extends `BaseEnv`) with:
  - `get_info()`: reports SUPA availability and device info
  - `get_device_info()`: enumerates SUPA devices by name and ID
  - `_get_supa_version_info()`: reports `FULLSTACK_HOME` path
  - `_get_brcc_info()`: reports Biren compiler (`brcc`) version
  - `_get_supa_driver_version()`: reports driver version via `brsmi -q`
  - `get_topology()`: reports GPU interconnect topology via `brsmi topo -m`
- Register `SUPAEnv` in the `__main__` dispatch (after MUSA, before MPS)

## Accuracy Tests

N/A — This PR only adds device detection and environment reporting utilities. No model computation or kernel logic is modified.

## Speed Tests and Profiling

N/A — No inference path changes. Only device detection functions are added, which are cached with `@lru_cache`.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28998106785](https://github.com/sgl-project/sglang/actions/runs/28998106785)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28998106626](https://github.com/sgl-project/sglang/actions/runs/28998106626)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
