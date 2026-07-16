---
source_id: sglang-github-closed-issues-prs
title: 'feat: Optimize radix cache insert and match tree traversal'
canonical_url: https://github.com/sgl-project/sglang/pull/22337
captured_at: '2026-07-15T23:40:28.381963+00:00'
content_hash: ebcfd6bb6bbb0f83475185f9884b018d69aee025ce04fee7f98c3cdd170cb35d
---
# feat: Optimize radix cache insert and match tree traversal

URL: https://github.com/sgl-project/sglang/pull/22337
State: closed
Labels: 
Closed at: 2026-07-15T04:09:42Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
The goal of this pull request is to reduce CPU overhead during token prefix caching. Previously, when handling unfinished requests in the hierarchical radix cache, the system performed two separate tree traversals. It would first walk the tree down to insert the new tokens, and then it would start entirely over from the root to run a match and retrieve the exact same device indices. Merging these operations saves unnecessary CPU cycles.
## Modifications
1. Added a new `insert_and_match` C++ function in `tree_v2.cpp` and `tree_v2.h` that completes the insertion and immediately walks back up to collect the node handles and device indices.
2. Exposed the new atomic function via PyBind11 in `tree_v2_binding.cpp` and typed it into the Python `RadixTreeCpp` wrapper structure.
3. Updated `cache_unfinished_req` inside `radix_cache_cpp.py` to utilize `_insert_and_match`, cleanly removing the duplicate `match_prefix` call and resolving the prior TODO note.
4. Added a fast standalone unit test `test_insert_and_match.py` directly testing the C++ extensions.
## Accuracy Tests
No direct model forward code was changed. The caching structural inputs and outputs were validated against the new python test file where the concatenated index tensors returned exact parity with the legacy matching method. 

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
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
