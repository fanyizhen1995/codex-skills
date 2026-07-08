---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] fix: slice img_shapes per-sample in rollout response extractor'
canonical_url: https://github.com/sgl-project/sglang/pull/29989
captured_at: '2026-07-07T23:35:30.923308+00:00'
content_hash: 0ce07e3ae23a93d3e52bc2a8999197f78d203d9bd262a3a8a8dfec6fbe52eb16
---
# [diffusion] fix: slice img_shapes per-sample in rollout response extractor

URL: https://github.com/sgl-project/sglang/pull/29989
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-07T00:56:52Z
Merged at: 2026-07-07T00:56:52Z

## Motivation

After the qwen-image cond batch alignment fix (`a9d657bf3`), `pos_cond_kwargs` contains an `img_shapes` list of length `batch_size` (one entry per multi-output sample) instead of length 1. `_extract_single_sample_tensor` recurses into lists element-wise without slicing by `sample_idx`, so each per-sample response carried back the full N-length `img_shapes`, breaking downstream consumers that assume per-sample `img_shapes` is length 1.

## Modifications

Thread the current dict key through the recursion and special-case the `img_shapes` list: when `len == batch_size`, take `obj[sample_idx]` and re-wrap as a length-1 list to preserve the `[(1, H, W)]` shape contract.

- `python/sglang/multimodal_gen/runtime/entrypoints/post_training/rollout_api.py`: add `current_key` kwarg to `_extract_single_sample_tensor` and handle `img_shapes` per-sample slicing (+12 / -4 lines)

## Accuracy Tests

N/A — this fix restores correct per-sample `img_shapes` extraction; no model forward code is changed.

## Speed Tests and Profiling

N/A — pure Python control-flow change in response extraction, no hot path affected.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28647918989](https://github.com/sgl-project/sglang/actions/runs/28647918989)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28647918920](https://github.com/sgl-project/sglang/actions/runs/28647918920)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
