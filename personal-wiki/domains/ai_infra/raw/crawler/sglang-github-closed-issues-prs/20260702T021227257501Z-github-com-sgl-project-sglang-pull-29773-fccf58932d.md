---
source_id: sglang-github-closed-issues-prs
title: Add class-level defaults on ModelRunner for attributes set in load_model()
canonical_url: https://github.com/sgl-project/sglang/pull/29773
captured_at: '2026-07-02T02:12:27.257501+00:00'
content_hash: fccf58932dd2651642909ad5ef54d3162e2dce2e0f5428cd87e24c358e3328ee
---
# Add class-level defaults on ModelRunner for attributes set in load_model()

URL: https://github.com/sgl-project/sglang/pull/29773
State: closed
Labels: 
Closed at: 2026-07-01T15:45:18Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
Currently, `ModelRunner.load_model()` serves two roles:

1. Loading model weights via PyTorch
2. Initializing derived attributes from the loaded model

For platforms that don't use PyTorch (in this case, MLX on Apple Silicon), role 1 must be skipped, thus load_model() cannot be called directly. 
As a side effect, role 2 is also skipped. But some of these derived attributes are read unconditionally by external code (scheduler, attention backends, load inquirer) via direct attribute access, causing the process to crash. See:
* #29679.

Caused by the introduction of this PR
* #29186

This PR proposes to add class-level defaults on `ModelRunner` so that any subclass which overrides `load_model()` inherits a safe fallback instead of crashing.
## Modifications
<!-- Detail the changes made in this pull request. -->
Add safe class-level defaults for `python/sglang/srt/model_executor/model_runner.py` so subclasses are protected:

- prefill_aware_swa: bool = False
- sliding_window_size: Optional[int] = None
- weight_load_mem_usage: float = 0

load_model() still overrides all three to their real values on the normal path. No behavioral change.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->
N/A — no model output affected. Class defaults are only read by subclasses that skip load_model(); on the normal path load_model() overrides them.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->
 N/A — zero runtime impact. Class attribute access is identical to instance attribute access after load_model() runs.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
4. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
5. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28483554221](https://github.com/sgl-project/sglang/actions/runs/28483554221)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28483554122](https://github.com/sgl-project/sglang/actions/runs/28483554122)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
