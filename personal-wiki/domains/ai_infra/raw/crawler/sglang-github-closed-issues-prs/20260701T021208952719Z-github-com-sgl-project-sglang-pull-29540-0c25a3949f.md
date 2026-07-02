---
source_id: sglang-github-closed-issues-prs
title: '[MLX] Restore prefill_aware_swa on MlxModelRunnerStub'
canonical_url: https://github.com/sgl-project/sglang/pull/29540
captured_at: '2026-07-01T02:12:08.952719+00:00'
content_hash: 0c25a3949fd0758a6b3ee6bb57a062c866c0025b31582cd41c9b0de10a9349d0
---
# [MLX] Restore prefill_aware_swa on MlxModelRunnerStub

URL: https://github.com/sgl-project/sglang/pull/29540
State: closed
Labels: 
Closed at: 2026-07-01T01:21:17Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fix MLX backend startup crash introduced by #29186 (baidu unlimited-ocr). That PR added a `prefill_aware_swa` attribute to `ModelRunner.__init__` and reads it from `scheduler._get_new_batch_prefill_raw`, but `MlxModelRunnerStub` overrides `load_model()` without copying the attribute. The first prefill batch on Apple Silicon crashes with `AttributeError: 'MlxModelRunnerStub' object has no attribute 'prefill_aware_swa'`, blocking all MLX server startups.

## Modifications

- `python/sglang/srt/hardware_backend/mlx/model_runner_stub.py`: add `self.prefill_aware_swa = False` in `load_model()` to mirror the base class attribute.

1 file changed, 1 insertion(+).
## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28309785778](https://github.com/sgl-project/sglang/actions/runs/28309785778)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28309785724](https://github.com/sgl-project/sglang/actions/runs/28309785724)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
