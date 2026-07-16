---
source_id: sglang-github-closed-issues-prs
title: 'docs: document CUDA crash dump output'
canonical_url: https://github.com/sgl-project/sglang/pull/31333
captured_at: '2026-07-15T23:40:28.357774+00:00'
content_hash: b47d00a41d2cdb0eb314cfd50614071ae88117781b6e6ba0ff603aaade05ae43
---
# docs: document CUDA crash dump output

URL: https://github.com/sgl-project/sglang/pull/31333
State: closed
Labels: documentation, run-ci
Closed at: 2026-07-15T14:18:37Z
Merged at: 2026-07-15T14:18:37Z

## Motivation

`--crash-dump-folder` was documented only as a request-history dump location, but the implementation also configures NVIDIA CUDA device coredumps. 

The incomplete description confused my colleague so I want to update the document lol.

## Modifications

- Describe the completed and in-flight requests stored in the replayable pickle file.
- Document CUDA exception and user-triggered device coredumps, their default path, and environment-variable precedence.
- Clarify that the option does not configure OS process core dumps.
- Keep the CLI help and server-argument reference synchronized.

## Accuracy Tests

Not applicable. This PR changes documentation and CLI help text only; it does not affect model outputs.

## Speed Tests and Profiling

Not applicable. This PR does not change runtime behavior or inference performance.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). Not applicable because runtime behavior is unchanged.
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). Not applicable because model outputs and runtime performance are unchanged.
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29422418545](https://github.com/sgl-project/sglang/actions/runs/29422418545)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29422416974](https://github.com/sgl-project/sglang/actions/runs/29422416974)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
