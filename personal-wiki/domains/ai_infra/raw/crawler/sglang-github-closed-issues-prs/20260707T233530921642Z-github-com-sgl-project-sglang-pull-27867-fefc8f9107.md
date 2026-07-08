---
source_id: sglang-github-closed-issues-prs
title: '[DSv4] Loading Time Weight Dequant'
canonical_url: https://github.com/sgl-project/sglang/pull/27867
captured_at: '2026-07-07T23:35:30.921642+00:00'
content_hash: fefc8f91078f861320eca010f5c1eb628fb24de29683b0a63c01c4547a00b3a7
---
# [DSv4] Loading Time Weight Dequant

URL: https://github.com/sgl-project/sglang/pull/27867
State: closed
Labels: documentation, quant, amd, dependencies, Multi-modal, deepseek, npu, run-ci, diffusion, model-gateway, bypass-fastfail
Closed at: 2026-07-07T01:54:35Z
Merged at: 2026-07-07T01:54:35Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
Current available weights for DSv4 Flash (from deepseek-ai or sgl-project) do not support TP8, which performs better in H20.
Dequanting FP4 to FP8 would be more preferrable during weight loading. Because this process depends on the TP size.
usage:
```
SGLANG_DSV4_FP4_DEQUANT=1 \
python -m sglang.launch_server \
  --model deepseek-ai/DeepSeek-V4-Flash/ \
  --tp 8 \
  --tool-call-parser deepseekv4 \
  --reasoning-parser deepseek-v4 \
```
cc @AniZpZ #23602 

<!-- Describe the purpose and goals of this pull request. -->

## Accuracy Tests
MMLU tests pass.
<img width="1644" height="186" alt="image" src="https://github.com/user-attachments/assets/dc8d6ba9-ed00-46ae-99b5-a4b6f1fcc614" />

## Benchmark
Setup:
1P1D 8xH20, radix cache off
Prefill: TP8+CP8
Decode: TP8
ISL: 15k, OSL: 700

Results:
batch size = 1
| Metric | TP8 | TP4 | Speedup |
|---|---:|---:|---:|
| P50 TPOT (ms) | 484 | 753 | 1.56x |
| P50 TTFT (ms) | 3.13 | 3.43 | 1.10x |

qps=0.83
| Metric | TP8 | TP4 | Speedup |
|---|---:|---:|---:|
| P50 TPOT (ms) | 699 | 1557 | 2.23x |
| P50 TTFT (ms) | 3.98 | 4.43 | 1.11x |

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28561076492](https://github.com/sgl-project/sglang/actions/runs/28561076492)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28561076381](https://github.com/sgl-project/sglang/actions/runs/28561076381)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
