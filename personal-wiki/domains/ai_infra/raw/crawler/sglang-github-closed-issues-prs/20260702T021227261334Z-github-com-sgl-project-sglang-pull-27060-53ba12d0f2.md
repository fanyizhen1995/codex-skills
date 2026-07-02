---
source_id: sglang-github-closed-issues-prs
title: 'feat(hicache): Use NIXL path-mode'
canonical_url: https://github.com/sgl-project/sglang/pull/27060
captured_at: '2026-07-02T02:12:27.261334+00:00'
content_hash: 53ba12d0f2d582f3694738bc9d5f9223976af828eb5091f78a5f512e129f1a3d
---
# feat(hicache): Use NIXL path-mode

URL: https://github.com/sgl-project/sglang/pull/27060
State: closed
Labels: hicache, run-ci
Closed at: 2026-07-01T09:59:46Z
Merged at: 2026-07-01T09:59:46Z

## Motivation

The worker process spends a lot of time holding the GIL, thus every `file.open()` called from python introduces a delay because of the GIL lock re-acquire. NIXL can now use the path-mode ( https://github.com/ai-dynamo/nixl/pull/1635 , available since NIXL release 1.3.0 ), which batch-opens the files in the native code side of NIXL and ammortizes the re-acquire over the whole batch of files.

## Modifications

HiCache NIXL detects the feature and if present, uses it to read and write cache files.

## Accuracy Tests

No changes

## Speed Tests and Profiling

Benchmarked on 8xA100 (tp=1 I/O-dominant / tp=4 realistic compute), Qwen-32B, ctx=31768 tokens, SGLANG_HICACHE_NIXL_USE_DIRECT_IO=1. "Warm TTFT" = KV-cache flushed, OS page cache cold for the KV store, L2 host cache warm. Reported as median over 4 warm rounds.

<img width="1080" height="600" alt="image" src="https://github.com/user-attachments/assets/5ac5e2de-5701-4e28-9ff6-1fd1c6bc8247" />


## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [N/A] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). 
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28499135960](https://github.com/sgl-project/sglang/actions/runs/28499135960)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28499135799](https://github.com/sgl-project/sglang/actions/runs/28499135799)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
