---
source_id: sglang-github-closed-issues-prs
title: '[Quantization] Update error message strings with correct framework name in
  Quark/compressed-tensors'
canonical_url: https://github.com/sgl-project/sglang/pull/25467
captured_at: '2026-07-09T23:36:35.322952+00:00'
content_hash: 4adf26616b003096a2449865679103d8c153c57b7378fedf4dc1c0d72c4ae6ea
---
# [Quantization] Update error message strings with correct framework name in Quark/compressed-tensors

URL: https://github.com/sgl-project/sglang/pull/25467
State: closed
Labels: 
Closed at: 2026-07-09T21:41:55Z
Merged at: 2026-07-09T21:41:55Z

## Motivation
These ValueErrors is Quark/compressed-tensors error messages are referencing "vLLM" in user-facing text raised from SGLang. Update them to say "SGLang" so the messages match the framework actually raising them.

## Modifications
Replacing strong "vLLM" with "SGLang" in three error messages in quantization code files.

## Accuracy Tests

N/A

## Speed Tests and Profiling

N/A

## Checklist

- [Done] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [Done] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28313701042](https://github.com/sgl-project/sglang/actions/runs/28313701042)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28313701006](https://github.com/sgl-project/sglang/actions/runs/28313701006)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
