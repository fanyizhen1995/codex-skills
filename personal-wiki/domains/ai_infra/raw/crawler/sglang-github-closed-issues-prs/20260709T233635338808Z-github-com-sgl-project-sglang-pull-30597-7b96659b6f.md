---
source_id: sglang-github-closed-issues-prs
title: fix arm test_norm.py error
canonical_url: https://github.com/sgl-project/sglang/pull/30597
captured_at: '2026-07-09T23:36:35.338808+00:00'
content_hash: 7b96659b6fbdd4a958f7e60952cad292d86050a6fecf86ea0fc6b187277ddb36
---
# fix arm test_norm.py error

URL: https://github.com/sgl-project/sglang/pull/30597
State: closed
Labels: cpu, run-ci
Closed at: 2026-07-09T06:36:45Z
Merged at: 2026-07-09T06:36:45Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fix arm ci error after https://github.com/sgl-project/sglang/pull/30216 landed.
Isolate avx512 specific optimizations for intel platform only.



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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28993409314](https://github.com/sgl-project/sglang/actions/runs/28993409314)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28993431364](https://github.com/sgl-project/sglang/actions/runs/28993431364)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
