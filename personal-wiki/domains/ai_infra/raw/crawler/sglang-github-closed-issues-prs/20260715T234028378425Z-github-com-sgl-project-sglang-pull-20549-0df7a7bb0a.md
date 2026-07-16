---
source_id: sglang-github-closed-issues-prs
title: '[WIP] Support nvfp4 online weight quantization'
canonical_url: https://github.com/sgl-project/sglang/pull/20549
captured_at: '2026-07-15T23:40:28.378425+00:00'
content_hash: 0df7a7bb0a15ed10edcfc24043507b82e3568aaeee1891ca9c7db07cbb30523a
---
# [WIP] Support nvfp4 online weight quantization

URL: https://github.com/sgl-project/sglang/pull/20549
State: closed
Labels: documentation, quant, blackwell
Closed at: 2026-07-15T06:11:53Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Since #18012 Introduced activation online-input-scale compute, this PR further extends the online weight quantization based on that. This PR introduces a direct `bf16 -> nvfp4` weight quantization during loading by turning on `--quantization nvfp4` flag

## Modifications
**This PR is still working in progress for refactoring**

**New quant method nvfp4:**
Added NvFp4Config (extends ModelOptFp4Config) with online weight quantization by default, group_size=16, and no required quant config file.
Wired into registry / config / CLI so --quantization nvfp4 works and is treated as a ModelOpt method.

**Online NVFP4 linear path:**
Added NvFp4LinearMethod (extends ModelOptFp4LinearMethod) that always uses online weight quant (no env flag).
Weights are loaded into _weight_fp_temp, then quantized to NVFP4 and written into the packed weight+weight_scale params.

## Accuracy Tests
Testing machine: NVIDIA B200
```
python3 benchmark/gsm8k/bench_sglang.py --num-shots 8 --num-questions 1209 --parallel 1209 --platinum

# full precision bf16 checkpoint
python3 -m sglang.launch_server --kv-cache-dtype bf16 --model-path meta-llama/Llama-3.1-8B-Instruct --port 30000
Accuracy: 0.806
Invalid: 0.000
Latency: 6.689 s
Output throughput: 16865.526 token/s

# nvfp4 checkpoint with online input scale
SGLANG_NVFP4_ONLINE_INPUT_SCALE=1 python3 -m sglang.launch_server --kv-cache-dtype bf16   --model-path nvidia/Llama-3.1-8B-Instruct-NVFP4   --port 30000 
Accuracy: 0.714
Invalid: 0.001
Latency: 8.408 s
Output throughput: 13473.763 token/s

# bf16 checkpoint with online weight quant
python3 -m sglang.launch_server --kv-cache-dtype bf16 --model-path meta-llama/Llama-3.1-8B-Instruct --quantization nvfp4 --port 30000
Accuracy: 0.706
Invalid: 0.001
Latency: 8.646 s
Output throughput: 13146.952 token/s






```

## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

1. Ping Merge Oncalls to start the PR flow. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - `/tag-run-ci-label`, `/rerun-failed-ci`, `/tag-and-rerun-ci`
4. After green CI and required approvals, ask Merge Oncalls to merge.
