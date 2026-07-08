---
source_id: sglang-github-closed-issues-prs
title: '[AMD-miles] Make ROCm aiter fp8 weight pre-shuffle idempotent for RL weight
  reload'
canonical_url: https://github.com/sgl-project/sglang/pull/28963
captured_at: '2026-07-07T23:35:30.922114+00:00'
content_hash: 3a02943ebc24c6184dc5599361cdc0215516526d2174bfc6926d349fcfb1eeb3
---
# [AMD-miles] Make ROCm aiter fp8 weight pre-shuffle idempotent for RL weight reload

URL: https://github.com/sgl-project/sglang/pull/28963
State: closed
Labels: 
Closed at: 2026-07-07T01:40:47Z
Merged at: 

Co-authored-with: @XinyuJiangCMU

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

On ROCm, the aiter FP8 path pre-shuffles weights in `process_weights_after_loading` via `shuffle_weight(..., (16, 16))`, which is not idempotent. In RL training the policy weights are reloaded into the running engine every step, so `process_weights_after_loading` runs again on already-shuffled weights and shuffles them a second time, corrupting the rollout. This PR makes the shuffle idempotent across reloads.

## Modifications

<!-- Detail the changes made in this pull request. -->

- Guard the aiter shuffle on a per-tensor `is_shuffled` flag (set right after shuffling) so repeated `process_weights_after_loading` calls shuffle each weight exactly once. Covers `Fp8LinearMethod` (dense block-quant) and `Fp8MoEMethod` (aiter block-quant).
- Implement `restore_weights_before_loading` on both methods to clear the flag. `ModelRunner` already invokes this hook on every quant method before a weight reload (the same hook compressed-tensors uses); the aiter shuffle is shape-preserving and the reload overwrites the buffer with fresh plain weights, so clearing the flag lets the next `process_weights_after_loading` re-shuffle exactly once.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

Validated end-to-end on Qwen3-30B-A3B (8x MI350X): fp8 blockwise train + rollout matches the bf16 reference to ~0.04 relerr, and stays on-policy (per-step train-vs-rollout logprob abs-diff ~0.04), including under TP2 + sequence parallel (fwd/dgrad/wgrad).

<p float="left">
  <img width="49%" alt="eval:aime" src="https://github.com/user-attachments/assets/1f865c84-83bd-4292-b56b-6678e1c32abb" />
  <img width="49%" alt="rollout:raw_reward" src="https://github.com/user-attachments/assets/d0f2628e-1e89-4853-b3a4-390fbeadf45b" />
</p>

<img width="979" height="492" alt="train:train_rollout_logprob_abs_diff" src="https://github.com/user-attachments/assets/a3e7d132-8c42-4f42-8c8f-67d3a3f22b15" />

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

N/A

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27984409774](https://github.com/sgl-project/sglang/actions/runs/27984409774)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27984408425](https://github.com/sgl-project/sglang/actions/runs/27984408425)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
