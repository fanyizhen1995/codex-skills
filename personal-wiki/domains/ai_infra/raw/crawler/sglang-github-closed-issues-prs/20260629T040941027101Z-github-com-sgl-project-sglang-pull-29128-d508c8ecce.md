---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Support fsdp for rl_on_policy_target'
canonical_url: https://github.com/sgl-project/sglang/pull/29128
captured_at: '2026-06-29T04:09:41.027101+00:00'
content_hash: d508c8eccec017c5ed65070b96a73a673b1666a8f215a3b4b162c9014eeeda39
---
# [NPU] Support fsdp for rl_on_policy_target

URL: https://github.com/sgl-project/sglang/pull/29128
State: closed
Labels: 
Closed at: 2026-06-24T06:57:20Z
Merged at: 2026-06-24T06:57:20Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
Need use --rl-on-policy-target fsdp on Ascend NPU.

## Modifications

<!-- Detail the changes made in this pull request. -->
1 Disable torch.compile for RotaryEmbedding._apply_rotary_emb_wrapped when use --rl-on-policy-target on Ascend NPU.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

### Serve script
```shell
sglang serve \
--model-path /weights/Qwen3-4B \
--attention-backend ascend --sampling-backend ascend \
--device npu \
--tp-size 1 \
--chunked-prefill-size -1 \
--disable-radix-cache \
--disable-cuda-graph \
--trust-remote-code \
--host 127.0.0.1 --port 31025 \
--mem-fraction-static 0.75 \
--rl-on-policy-target fsdp
```

### Eval script
```shell
evalscope eval \
--model /weights/Qwen3-4B \
--api-url http://127.0.0.1:31025/v1 \
--api-key EMPTY \
--eval-type openai_api \
--generation-config '{
      "max_tokens": 1024,
      "timeout": 600,
      "stream": true
}' \
--datasets gsm8k \
--dataset-args '{"gsm8k": {"dataset_id": "/home/q30063557/workspace/acc-test/dataset/gsm8k"}}' \
--eval-batch-size 64 \
--ignore-errors
```

### Result
Score: 0.58
The difference between this result and the result without the feature is within 1%.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28079957082](https://github.com/sgl-project/sglang/actions/runs/28079957082)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28079956917](https://github.com/sgl-project/sglang/actions/runs/28079956917)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
