---
source_id: sglang-github-closed-issues-prs
title: 'fix(marlin): support FP16 FE8M0 scale dequant'
canonical_url: https://github.com/sgl-project/sglang/pull/30678
captured_at: '2026-07-09T23:36:35.326286+00:00'
content_hash: e79d7c974b2810746806c262d15ad308bf9179b815f1e84323c334e34cbde99a
---
# fix(marlin): support FP16 FE8M0 scale dequant

URL: https://github.com/sgl-project/sglang/pull/30678
State: closed
Labels: quant, jit-kernel
Closed at: 2026-07-09T14:40:16Z
Merged at: 

Add the missing half2 specialization for FE8M0fnu scale dequantization. This fixes ptxas unresolved extern errors in the float16 MXFP4 MoE Marlin JIT path

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Run Qwen3.5-35B-A3B-GPTQ-Int4 with avx2 backend, will get error
`ptxas fatal   : Unresolved extern function '_ZN6device6marlin18dequant_fp8_scalesI7__half2Ll2814749767106568EEEviPT_'
ninja: build stopped: subcommand failed.`

## Modifications

<!-- Detail the changes made in this pull request. -->

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
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29026212084](https://github.com/sgl-project/sglang/actions/runs/29026212084)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29026212009](https://github.com/sgl-project/sglang/actions/runs/29026212009)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
