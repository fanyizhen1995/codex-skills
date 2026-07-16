---
source_id: sglang-github-closed-issues-prs
title: 'feat: disaggregation_decode_enable_offload_kvcache support for LMCache'
canonical_url: https://github.com/sgl-project/sglang/pull/15323
captured_at: '2026-07-13T23:40:05.193139+00:00'
content_hash: 1c0e69732fdd4e72253a81f425ce6784a114c2b51b4924475923381e2066542b
---
# feat: disaggregation_decode_enable_offload_kvcache support for LMCache

URL: https://github.com/sgl-project/sglang/pull/15323
State: closed
Labels: hicache
Closed at: 2026-07-13T02:57:54Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

`disaggregation_decode_enable_offload_kvcache` is supported with HiCache only, this PR added LMCache support with the same pattern.

## Modifications

<!-- Detail the changes made in this pull request. -->
* New: [decode_kvcache_offload_manager.py](https://github.com/sgl-project/sglang/compare/main...wxsms:lmcache_decode_offload?expand=1#diff-5a37b10aa2ba117951e11c1d5407fca1db20fb04630e10bb5f5151d783e2c903) act  as a common base class
* Edit: [hicache_decode_offload_manager.py](https://github.com/sgl-project/sglang/compare/main...wxsms:lmcache_decode_offload?expand=1#diff-75f1a652067ba1eb58ab463acb730365a747553df25b1cc5326ea2b503d63f34) basiclly the same, except inhenric from base
* New: [lmc_decode_offload_manager.py](https://github.com/sgl-project/sglang/compare/main...wxsms:lmcache_decode_offload?expand=1#diff-ec17a02cf731a3c353f85ada571cbc46e26303e527349fdfe2fcc7aebd777793) the LMCache decode offload manager
* [scheduler.py](https://github.com/sgl-project/sglang/compare/main...wxsms:lmcache_decode_offload?expand=1#diff-c3b8cc39d10c245933a25aa9c2fd6397f6b31ed8d85c0ecbb926c1f42afdd178) and [scheduler_runtime_checker_mixin.py](https://github.com/sgl-project/sglang/compare/main...wxsms:lmcache_decode_offload?expand=1#diff-c9ee384ecedbdfc2df3c2905dcbf11f834d3ce69da4a4306f4e08299ba54db5c): change `ongoing_offload` to a public method

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

this should not affect model outputs

## Benchmarking and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

Since the main branch is using torch==2.9.0, where the latest lmcache is using 2.8.0, have to wait for an update of LMCache to test the perf.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).
- [ ] Work with maintainers to merge your PR. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process)
