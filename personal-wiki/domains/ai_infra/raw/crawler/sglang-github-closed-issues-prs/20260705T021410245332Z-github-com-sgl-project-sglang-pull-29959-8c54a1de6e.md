---
source_id: sglang-github-closed-issues-prs
title: '[DSA][GLM5.2] Index Share for MHA'
canonical_url: https://github.com/sgl-project/sglang/pull/29959
captured_at: '2026-07-05T02:14:10.245332+00:00'
content_hash: 8c54a1de6e68006f8f1bf3332153e996bdff0256d78445e7fb02497e3ae75582
---
# [DSA][GLM5.2] Index Share for MHA

URL: https://github.com/sgl-project/sglang/pull/29959
State: closed
Labels: run-ci
Closed at: 2026-07-04T09:50:27Z
Merged at: 2026-07-04T09:50:27Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
Closes https://github.com/sgl-project/sglang/issues/29951

Indexer is run on Layer38, Layer39 skips it.
<img width="2578" height="859" alt="Screenshot 2026-07-03 at 09 30 58" src="https://github.com/user-attachments/assets/9ca0e147-10d7-45af-9408-feaba5fd96fe" />


## Modifications

<!-- Detail the changes made in this pull request. -->
- Skip DSA indexer on shared indexer layers.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->
```bash
== aime25 ==
30 examples x 16 repeats  |  4721.4s  |  1943 tok/s  |  9.2M tokens

* pass@1[avg-of-16]  =  90.83% +/- 3.94% (SEM 0.99%)
  pass@16            =  100.00%
  majority@16        =  93.33%
  no_answer          =  0.21%
  stop_rate          =  100.00%
  truncated_rate     =  0.00%
  error_rate         =  0.00%
 ```
Cookbook reports 87.7 %.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28653902841](https://github.com/sgl-project/sglang/actions/runs/28653902841)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28653902712](https://github.com/sgl-project/sglang/actions/runs/28653902712)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
