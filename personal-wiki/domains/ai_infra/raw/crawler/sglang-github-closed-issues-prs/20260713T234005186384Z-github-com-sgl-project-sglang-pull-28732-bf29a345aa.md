---
source_id: sglang-github-closed-issues-prs
title: fix bench_one_batch by extending array with array not list
canonical_url: https://github.com/sgl-project/sglang/pull/28732
captured_at: '2026-07-13T23:40:05.186384+00:00'
content_hash: bf29a345aa3b9ef658ad7ccca14120f1448d93fa99e25f4b9ae5533b037f685e
---
# fix bench_one_batch by extending array with array not list

URL: https://github.com/sgl-project/sglang/pull/28732
State: closed
Labels: run-ci
Closed at: 2026-06-21T00:28:41Z
Merged at: 2026-06-21T00:28:41Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->
issue due to https://github.com/sgl-project/sglang/pull/26637
```
[rank0]: Traceback (most recent call last):
[rank0]:   File "<frozen runpy>", line 198, in _run_module_as_main
[rank0]:   File "<frozen runpy>", line 88, in _run_code
[rank0]:   File "/home/jvarma/upstream/sglang/python/sglang/bench_one_batch.py", line 1016, in <module>
[rank0]:     main(server_args, bench_args)
[rank0]:   File "/home/jvarma/upstream/sglang/python/sglang/bench_one_batch.py", line 978, in main
[rank0]:     work_func(server_args, port_args, bench_args, 0, 0)
[rank0]:   File "/home/jvarma/upstream/sglang/python/sglang/bench_one_batch.py", line 665, in correctness_test
[rank0]:     reqs = prepare_extend_inputs_for_correctness_test(
[rank0]:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[rank0]:   File "/home/jvarma/upstream/sglang/python/sglang/bench_one_batch.py", line 396, in prepare_extend_inputs_for_correctness_test
[rank0]:     req.full_untruncated_fill_ids += input_ids[i][bench_args.cut_len :]
[rank0]: TypeError: can only extend array with array (not "list")

```

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #27837330316](https://github.com/sgl-project/sglang/actions/runs/27837330316)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #27858408652](https://github.com/sgl-project/sglang/actions/runs/27858408652)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
