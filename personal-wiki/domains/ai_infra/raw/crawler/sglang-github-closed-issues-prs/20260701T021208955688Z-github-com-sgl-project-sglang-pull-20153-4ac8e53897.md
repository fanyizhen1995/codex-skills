---
source_id: sglang-github-closed-issues-prs
title: 'Refactor: fix symmetric memory pool isolation per communication group'
canonical_url: https://github.com/sgl-project/sglang/pull/20153
captured_at: '2026-07-01T02:12:08.955688+00:00'
content_hash: 4ac8e538975c3bd53c04f235c066011f55f72e6128c9b965bfad9e2fd625a3ab
---
# Refactor: fix symmetric memory pool isolation per communication group

URL: https://github.com/sgl-project/sglang/pull/20153
State: closed
Labels: run-ci
Closed at: 2026-06-30T17:56:15Z
Merged at: 

CC @nvcastet @yizhang2077 @merrymercy @ShangmingCai @Fridge003 @ch-wan  PTAL, thx.

## Motivation

When multiple communication groups share a single global MemPool, memory blocks released by one group's comm may be reused by another group's comm. However, symmetric memory requires buffers to be registered with a specific `ncclComm` via `ncclCommWindowRegister`. Reusing memory across groups causes the registration to be associated with the wrong communicator.

I refactored SymmPool to replace the global MemPool with a per-group dictionary. Now each communication group has its own MemPool, ensuring proper memory registration and preventing cross-group allocation issues in multi-comm scenarios.

Related PR: https://github.com/sgl-project/sglang/pull/19329#issuecomment-3969031981


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
