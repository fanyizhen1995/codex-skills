---
source_id: sglang-github-closed-issues-prs
title: '[NPU] ascend support decode radix cache'
canonical_url: https://github.com/sgl-project/sglang/pull/30087
captured_at: '2026-07-13T23:40:05.189802+00:00'
content_hash: a427d3638eb869f31d135101c4b8379602838aeafe9aad79f66760c83f5e737b
---
# [NPU] ascend support decode radix cache

URL: https://github.com/sgl-project/sglang/pull/30087
State: closed
Labels: run-ci
Closed at: 2026-07-13T07:53:09Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Ascend PD disaggregation supports decode radix cache, and Ascend deployments may also enable speculative decoding such as `--speculative-algorithm NEXTN`.

Before this change, launching a decode server with all of the following options failed during argument validation:

```bash
--disaggregation-transfer-backend ascend
--disaggregation-decode-enable-radix-cache
--speculative-algorithm NEXTN
```

The error was:

```text
--disaggregation-decode-enable-radix-cache is incompatible with speculative decoding (--speculative-algorithm NEXTN)
```

This validation is too strict for the Ascend transfer backend.

## Modifications

Relax the PD disaggregation argument check so speculative decoding is still rejected for non-Ascend transfer backends, but allowed when using:

```bash
--disaggregation-transfer-backend ascend
```

The existing incompatibility checks for `--enable-hisparse` and `--disaggregation-transfer-backend fake` are unchanged.

## Accuracy Tests

Not applicable. This PR only changes server argument validation and does not modify model forward computation or kernels.

## Speed Tests and Profiling

Not applicable. This PR only allows a previously rejected Ascend configuration to pass validation and does not change runtime execution paths.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28760948150](https://github.com/sgl-project/sglang/actions/runs/28760948150)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28760948094](https://github.com/sgl-project/sglang/actions/runs/28760948094)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
