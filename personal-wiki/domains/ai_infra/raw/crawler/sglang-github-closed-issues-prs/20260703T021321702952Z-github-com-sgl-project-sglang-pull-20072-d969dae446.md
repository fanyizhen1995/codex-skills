---
source_id: sglang-github-closed-issues-prs
title: '[CPU] Padding for dim divisibility in TP3/6 cases'
canonical_url: https://github.com/sgl-project/sglang/pull/20072
captured_at: '2026-07-03T02:13:21.702952+00:00'
content_hash: d969dae4465d587502d5552272b2dcb9093ae1fe6000b3b3332eccf85dfc95b2
---
# [CPU] Padding for dim divisibility in TP3/6 cases

URL: https://github.com/sgl-project/sglang/pull/20072
State: closed
Labels: sgl-kernel, intel, cpu, run-ci
Closed at: 2026-07-02T05:14:40Z
Merged at: 2026-07-02T05:14:40Z

## Motivation

For some flagship Intel(R) 6th Gen Xeon(R) Processors, there are 2 nodes with SNC3 per node on a host server, so TP3/6 needs to be supported to fully utilize the computing resources for maximum performance.

This has been supported in pure-text LLMs, but not well supported in the vision modules of some VLMs.

Also added similar fix for MXFP4 GPT-OSS model from co-author @blzheng (dependent on #16775 )

## Modifications

Add padding functionalities for modules in `python/sglang/srt/configs/update_config.py`.

Update the modeling files correspondingly:

- Llama4: `python/sglang/srt/models/mllama4.py`
- Llama-3.2-11B-Vision: `python/sglang/srt/models/mllama.py` (also requires changes in #8666 )
- GPT-OSS: `python/sglang/srt/models/gpt_oss.py`
- Qwen2.5-VL: `python/sglang/srt/models/qwen2.py` and `python/sglang/srt/models/qwen2_5_vl.py` (originated from @blzheng 's [commit](https://github.com/blzheng/sglang/commit/bac21b769e1ea9b0728b8a6695976fcdf6cfb3c1)and made some corrections).

## Functionality Tests

Locally verified

## Accuracy Tests

to be added

## Benchmarking and Profiling

N/A

## Checklist

- [X] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.

































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28557573983](https://github.com/sgl-project/sglang/actions/runs/28557573983)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28567127992](https://github.com/sgl-project/sglang/actions/runs/28567127992)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
