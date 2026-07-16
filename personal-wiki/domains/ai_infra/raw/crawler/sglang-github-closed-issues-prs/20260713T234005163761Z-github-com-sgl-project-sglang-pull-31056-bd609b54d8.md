---
source_id: sglang-github-closed-issues-prs
title: Fix MockDSV4ModelRunner missing spec_algorithm
canonical_url: https://github.com/sgl-project/sglang/pull/31056
captured_at: '2026-07-13T23:40:05.163761+00:00'
content_hash: bd609b54d8147eda2659832932806a6563ff760396562f69c0d7bc33f3ea1689
---
# Fix MockDSV4ModelRunner missing spec_algorithm

URL: https://github.com/sgl-project/sglang/pull/31056
State: closed
Labels: run-ci
Closed at: 2026-07-13T20:24:28Z
Merged at: 2026-07-13T20:24:28Z

## Motivation
DSpark (#30261) switched `DeepseekV4AttnBackend.__init__` from reading
`server_args.speculative_algorithm` to `model_runner.spec_algorithm`, which the
attention-unittest mock runner does not define, so every dsv4 backend construction
through the kit crashes with `AttributeError: 'MockDSV4ModelRunner' object has no
attribute 'spec_algorithm'` (e.g. all `dsv4_c4_*` cases in
`test/registered/attention/unittests/dsv4/test_deepseek_v4.py`). This breaks CI for
every PR based on current main.

## Modifications
Give the mock `SpeculativeAlgorithm.NONE`, matching the pre-DSpark behavior for
non-spec cases: the old gate was `server_args.speculative_algorithm is not None`,
which the mock overrides to `None`, so with `NONE` the new gate resolves identically
(`needs_cpu_seq_lens` unset, `is_dspark_draft` False). One attribute plus its import in
`python/sglang/test/kits/attention_unittest/attention_methods/dsv4_attention.py`;
`is_draft_worker`, the other attribute the new code reads, was already defined.

## Accuracy Tests
N/A — test-kit-only change; no runtime code touched.

## Speed Tests and Profiling
N/A.

## Checklist
- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). (This PR repairs the existing dsv4 attention unit tests themselves.)
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29281398333](https://github.com/sgl-project/sglang/actions/runs/29281398333)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29281398028](https://github.com/sgl-project/sglang/actions/runs/29281398028)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
