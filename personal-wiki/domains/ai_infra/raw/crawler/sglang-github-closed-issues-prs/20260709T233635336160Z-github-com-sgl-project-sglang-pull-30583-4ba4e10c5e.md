---
source_id: sglang-github-closed-issues-prs
title: No needed
canonical_url: https://github.com/sgl-project/sglang/pull/30583
captured_at: '2026-07-09T23:36:35.336160+00:00'
content_hash: 4ba4e10c5e01d6457766435d3ee4395dccb9f940a19ee6ce33144b5c62e7fa57
---
# No needed

URL: https://github.com/sgl-project/sglang/pull/30583
State: closed
Labels: 
Closed at: 2026-07-09T08:43:54Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

Currently, in GSP (Generated Shared Prefix) benchmark scenarios, such as the 90% cache scenario, there is an issue where the first prompt from the test set is used for warmup. In a Radix Cache scenario, this causes the first prompt to be 100% cached during actual testing, resulting in anomalous performance metrics.

## Modifications

<!-- Detail the changes made in this pull request. -->

Based on the existing interfaces, two modifications were made:

1. Before generation on the actual test set, the number of warmup prompts was added to the GSP prompts to generate an additional number of test samples equal to the warmup count.
2. During the actual benchmark phase, the test dataset is split into two parts: one dedicated to warmup, and the other for actual evaluation (which corresponds to the original test set).

So, you can keep using it exactly as before. The only change is that GSP now uses unique prompts for warmup, instead of reusing the first test entry.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

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
3. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
4. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
5. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28988682309](https://github.com/sgl-project/sglang/actions/runs/28988682309)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28988682205](https://github.com/sgl-project/sglang/actions/runs/28988682205)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
