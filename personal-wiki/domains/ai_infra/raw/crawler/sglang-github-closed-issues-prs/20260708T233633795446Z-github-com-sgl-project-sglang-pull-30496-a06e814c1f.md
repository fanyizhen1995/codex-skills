---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Gate stage-c on stage-b-test-1-gpu-large-amd'
canonical_url: https://github.com/sgl-project/sglang/pull/30496
captured_at: '2026-07-08T23:36:33.795446+00:00'
content_hash: a06e814c1f204f7db77546efe81ee2897ea4d7067cfe39088714deb47b79b358
---
# [AMD] Gate stage-c on stage-b-test-1-gpu-large-amd

URL: https://github.com/sgl-project/sglang/pull/30496
State: closed
Labels: amd
Closed at: 2026-07-08T07:41:22Z
Merged at: 2026-07-08T07:41:22Z

## Motivation
The AMD PR test workflow (`pr-test-amd.yml`) runs tests in sequential stages
(stage-a → stage-b → stage-c). Each stage gates the next through a
`wait-for-*` job that polls the previous stage's jobs and fails fast if any
of them fail. `wait-for-stage-b-amd` is what gates `stage-c-*` (every stage-c
job has `needs: [..., wait-for-stage-b-amd]` plus `!failure()`).
However, `wait-for-stage-b-amd` only watched two stage-b job families:
`stage-b-test-1-gpu-small-amd` and `stage-b-test-2-gpu-large-amd`.
`stage-b-test-1-gpu-large-amd` was missing from the list, so:
- If `stage-b-test-1-gpu-large-amd` fails, the gate does not fail-fast and
  stage-c still dispatches, wasting multi-GPU runners.
- stage-c is not sequenced after `stage-b-test-1-gpu-large-amd`.
This mirrors the NVIDIA `pr-test.yml`, where `wait-for-base-b` already
includes `base-b-test-1-gpu-large`.
## Modifications
- Add `stage-b-test-1-gpu-large-amd` to the `jobs` list of
  `wait-for-stage-b-amd`, with `expected_count: 3` to match its matrix
  (`part: [0, 1, 2]`).
Scope note: this PR only adds `stage-b-test-1-gpu-large-amd`. Other stage-b
jobs (`-nondeterministic`, `-mi35x`, `stage-b-test-large-8-gpu-mi35x-
disaggregation-amd`) are intentionally left out of scope here.
## Accuracy Tests
N/A — CI workflow configuration change only, no model/kernel code changes.
## Speed Tests and Profiling
N/A

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28925756549](https://github.com/sgl-project/sglang/actions/runs/28925756549)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28925756433](https://github.com/sgl-project/sglang/actions/runs/28925756433)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
