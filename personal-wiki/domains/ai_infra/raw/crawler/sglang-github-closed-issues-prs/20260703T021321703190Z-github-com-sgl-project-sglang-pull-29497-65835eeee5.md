---
source_id: sglang-github-closed-issues-prs
title: '[CPU] Fix model failures on Xeon'
canonical_url: https://github.com/sgl-project/sglang/pull/29497
captured_at: '2026-07-03T02:13:21.703190+00:00'
content_hash: 65835eeee5801a2b3f9d866e156393d4523b8c083035e8006d2bb0e11e12ac47
---
# [CPU] Fix model failures on Xeon

URL: https://github.com/sgl-project/sglang/pull/29497
State: closed
Labels: documentation, dependencies, intel, cpu, run-ci
Closed at: 2026-07-02T05:20:19Z
Merged at: 2026-07-02T05:20:19Z

## Motivation

Fix the model launching failures on Xeon CPU.

## Modifications

- Fix Qwen3.5/3.6 series: #26924 introduced `fused_sigmoid_mul` triton kernel, but it is not applicable on CPU. Added a gating for this.
(Update: the gating is deprecated and reverted as it is not needed as CPU `fused_sigmoid_mul` is implemented in #29378 )

- Fix Llama-3.2-11B-Vision: Fixed the seq_len dtype mismatch of encoder introduced in #27407.The input seq_len tensor dtype changed from int64 to int32 to accommodate the feature, but CPU device should exempt from it. The author had an incomplete fix in #27840, leaving encoder part unfixed.

- Fix GPT-OSS: The model can run TP1 but not TP2 as the sliced local shapes do not fit the AMX prepack criteria. A torch native fallback path is added for MXFP4 MoE. (padding for odd TP was implemented in #20072 )

Misc updates piggybacked:

- Removal of `Support Model List` in the CPU doc page as the info has been added in the cookbook pages.
- Adding example command of pulling a prebuilt image from lmsysorg DockeHub repo.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28558886275](https://github.com/sgl-project/sglang/actions/runs/28558886275)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28567367502](https://github.com/sgl-project/sglang/actions/runs/28567367502)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
