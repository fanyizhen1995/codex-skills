---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Fix the DeepSeek-V2-Coder model accuracy issue'
canonical_url: https://github.com/sgl-project/sglang/pull/29042
captured_at: '2026-06-29T04:09:41.027343+00:00'
content_hash: 926ecb70872bb8b1302165c96bed74c254d8a956c3fb42f597b263740fdcae11
---
# [NPU] Fix the DeepSeek-V2-Coder model accuracy issue

URL: https://github.com/sgl-project/sglang/pull/29042
State: closed
Labels: deepseek, run-ci
Closed at: 2026-06-25T01:14:33Z
Merged at: 2026-06-25T01:14:33Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fix the DeepSeek-V2-Coder model accuracy issue.

## Modifications

1. In `fused_topk_npu()`, determine whether `norm_type` is sigmoid or softmax based on the value of `topk_config.scoring_func`.
2. In `DeepseekV2MoE::__init__()`, pass `config.scoring_func` into `topk_kwargs` so that `self.topk` correctly determines the scoring function based on its construction-time value.

## Accuracy Tests

```
#!/bin/bash

export HCCL_BUFFSIZE="1024"
export PYTHONPATH=/root/RemoteDev/sglang/python:$PYTHONPATH
export SGLANG_LOG_PATH=/root/run_scripts/granite/sglang.log
rm -rf $SGLANG_LOG_PATH

python -m sglang.launch_server \
    --model-path /home/weights/DeepSeek-Coder-V2-Lite-Instruct \
    --trust-remote-code \
    --attention-backend ascend \
    --disable-cuda-graph \
    --mem-fraction-static 0.5 \
    --tp-size 2 \
    --moe-dense-tp-size 1 \
    --device npu \
    --host 127.0.0.1 \
    --port 9090
```
<img width="1665" height="270" alt="DeepSeek-Coder-V2-Lite-Instruct精度" src="https://github.com/user-attachments/assets/65cf9c89-c0ca-4c0f-b3d6-072b7d8bf43c" />


## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
3. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
4. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
5. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28089354692](https://github.com/sgl-project/sglang/actions/runs/28089354692)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28089354534](https://github.com/sgl-project/sglang/actions/runs/28089354534)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
