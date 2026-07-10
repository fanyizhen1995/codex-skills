---
source_id: sglang-github-closed-issues-prs
title: enable moe marlin fp8 for Ampere GPU
canonical_url: https://github.com/sgl-project/sglang/pull/9754
captured_at: '2026-07-09T23:36:35.326053+00:00'
content_hash: d4f1cd83095061192d98aa49406cbecba648b4a633d77af9030423c07e6c2254
---
# enable moe marlin fp8 for Ampere GPU

URL: https://github.com/sgl-project/sglang/pull/9754
State: closed
Labels: run-ci
Closed at: 2026-06-10T08:18:38Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.ai to discuss further. -->

## Motivation

Update the Marlin Moe FP8 implementation to resolve https://github.com/sgl-project/sglang/pull/8990#issuecomment-3206248657 , allow moe fp8 models running on sm8x hardwares.
This pr has been verified on Qwen/Qwen3-30B-A3B-Thinking-2507-FP8 with 1,2,4 A40 and , Qwen3-235B-A22B-Thinking-2507-FP8, and DeepSeek-V3.1-FP8 on 2*8gpus

## Modifications

Add Marlin Moe support in fp8.py, delete some early return before MarlinMoe. Auto enable Marlin for supported archs.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.ai/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.ai/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.ai/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.ai/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.ai/developer_guide/contribution_guide.html#benchmark-the-speed).
