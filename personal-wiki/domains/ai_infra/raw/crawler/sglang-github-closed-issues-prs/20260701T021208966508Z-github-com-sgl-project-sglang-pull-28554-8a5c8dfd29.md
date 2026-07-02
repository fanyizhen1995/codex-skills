---
source_id: sglang-github-closed-issues-prs
title: '[AMD]: CI add NIXL PD disaggregation tests'
canonical_url: https://github.com/sgl-project/sglang/pull/28554
captured_at: '2026-07-01T02:12:08.966508+00:00'
content_hash: 8a5c8dfd2948f9d1cf91e1ddd54225178b221edb6bdea4d57715655cde3175bd
---
# [AMD]: CI add NIXL PD disaggregation tests

URL: https://github.com/sgl-project/sglang/pull/28554
State: closed
Labels: amd
Closed at: 2026-06-30T04:49:00Z
Merged at: 

 ## Motivation

  Add CI coverage for PD disaggregation over the optional NIXL (ai-dynamo/nixl + UCX `--with-rocm`) backend on ROCm. The backend itself is added
  by a separate Dockerfile PR; this PR adds only the tests.

  ## Modifications

  - Register a PD-over-NIXL e2e test in the AMD suite `stage-b-test-large-8-gpu-mi35x-disaggregation-amd` (smoke + GSM8K accuracy). Modeled on the
   existing MORI transfer-engine test; pins `--disaggregation-transfer-backend nixl` and skips gracefully when the image was built without
  `--build-arg ENABLE_NIXL=1`.
  - Add a PR build-test workflow that builds `docker/rocm.Dockerfile` with `ENABLE_NIXL=1` on both the ROCm 7.0 (gfx950) and 7.2 (gfx950-rocm720)
  bases and asserts nixl imports with UCX present and plugins discoverable.


## Accuracy Tests

N/A

## Speed Tests and Profiling

N/A

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27715749389](https://github.com/sgl-project/sglang/actions/runs/27715749389)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27715749424](https://github.com/sgl-project/sglang/actions/runs/27715749424)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
