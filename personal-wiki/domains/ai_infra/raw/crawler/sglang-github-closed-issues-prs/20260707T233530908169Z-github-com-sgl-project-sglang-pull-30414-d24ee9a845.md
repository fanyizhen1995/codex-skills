---
source_id: sglang-github-closed-issues-prs
title: 'feat: add opt-in prefill timers and multimodal embedding-cache hit co…'
canonical_url: https://github.com/sgl-project/sglang/pull/30414
captured_at: '2026-07-07T23:35:30.908169+00:00'
content_hash: d24ee9a845c02b027622463bb32880da1b056f5e9b12cbb496dd214882c2bc42
---
# feat: add opt-in prefill timers and multimodal embedding-cache hit co…

URL: https://github.com/sgl-project/sglang/pull/30414
State: closed
Labels: 
Closed at: 2026-07-07T17:10:38Z
Merged at: 

…unters

Three small serving-observability additions, all backend/model-agnostic:

- SGLANG_PREFILL_FORWARD_TIMER=1: GPU-synced wall time of each prefill forward (attention planning + model.forward; for VLMs this includes the vision encode). Measures the server-side prefill boundary, excluding HTTP/tokenizer-process preprocessing. Off by default; the sync perturbs pipelining, so it is a diagnostic, not an always-on metric.
- SGLANG_ATTN_PLAN_TIMER=1: GPU-synced wall time of attention-metadata planning (init_forward_metadata) per prefill. Off by default.
- mm_cache_stats: always-on hit/miss counters for the multimodal (ViT) embedding cache, incremented per item lookup during prefill; surfaced as 'mm-cache-hit: H/N' on the scheduler's standard prefill log line.

Both timers cost one env read per prefill when disabled.

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28884665531](https://github.com/sgl-project/sglang/actions/runs/28884665531)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28884665251](https://github.com/sgl-project/sglang/actions/runs/28884665251)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
