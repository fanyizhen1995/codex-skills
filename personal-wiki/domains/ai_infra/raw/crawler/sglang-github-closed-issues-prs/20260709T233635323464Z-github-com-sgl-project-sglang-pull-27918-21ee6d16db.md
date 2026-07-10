---
source_id: sglang-github-closed-issues-prs
title: '[BCG] Restore Qwen3.5 MRoPE fusion under breakable CUDA graph'
canonical_url: https://github.com/sgl-project/sglang/pull/27918
captured_at: '2026-07-09T23:36:35.323464+00:00'
content_hash: 21ee6d16db0a47d66e8bb944651233a228852d5d6a7eb5891cbdf53a22d31c73
---
# [BCG] Restore Qwen3.5 MRoPE fusion under breakable CUDA graph

URL: https://github.com/sgl-project/sglang/pull/27918
State: closed
Labels: run-ci
Closed at: 2026-07-09T21:30:05Z
Merged at: 2026-07-09T21:30:05Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

 BCG captures `layer_model.forward` directly, while PCG goes through the outer Qwen3.5 multimodal wrapper. That outer wrapper replaces rank-1 positions with rank-2 `forward_batch.mrope_positions` when MRoPE is enabled. BCG bypassed that substitution, so `MRotaryEmbedding.forward_cuda` did not take the Triton MRoPE path and `_triton_mrope_forward_fused` disappeared.

cc @YAMY1234 @nvpohanh 

## Modifications

In `python/sglang/srt/model_executor/runner/prefill_cuda_graph_runner.py` when BCG calls the inner layer model, it now mirrors the outer wrapper and passes mrope_positions for MRoPE models.

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

Not kernel changes.

## Speed Tests and Profiling

Before with BCG:
<img width="2560" height="137" alt="Screenshot 2026-06-11 at 13 28 57" src="https://github.com/user-attachments/assets/37738b8f-9b0d-4208-9339-fbc524ea31c0" />
(Several aten ops before attention)

After with BCG:
<img width="2551" height="95" alt="Screenshot 2026-06-11 at 13 28 23" src="https://github.com/user-attachments/assets/b1c767bf-daf6-4ed7-84d8-82c61dc53356" />
(Aten ops fused)

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28100169600](https://github.com/sgl-project/sglang/actions/runs/28100169600)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28100169402](https://github.com/sgl-project/sglang/actions/runs/28100169402)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
