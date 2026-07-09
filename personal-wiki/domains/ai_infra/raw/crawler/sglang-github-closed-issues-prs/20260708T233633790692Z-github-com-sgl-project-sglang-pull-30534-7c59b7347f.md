---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Temporarily reduce AMD scheduled test frequency to save resource'
canonical_url: https://github.com/sgl-project/sglang/pull/30534
captured_at: '2026-07-08T23:36:33.790692+00:00'
content_hash: 7c59b7347f0c3c7bfe3b64c8a434e60c5b409a30830ae5d256522a2a66f60370
---
# [AMD] Temporarily reduce AMD scheduled test frequency to save resource

URL: https://github.com/sgl-project/sglang/pull/30534
State: closed
Labels: high priority, amd, ci
Closed at: 2026-07-08T16:31:00Z
Merged at: 2026-07-08T16:31:00Z

## Motivation
Reduce CI resource usage (AMD runner consumption) by lowering the trigger frequency of scheduled tests.
## Modifications
- **AMD PR Test (`pr-test-amd.yml`)**: Change scheduled run frequency from every 6 hours to every 12 hours
  - `cron: '0 */6 * * *'` → `cron: '0 */12 * * *'`
  - Daily triggers reduced from 4 to 2 (UTC 00:00 / 12:00)
- **AMD AITER Scout (`amd-aiter-scout.yml`)**: Temporarily disable the second weekly trigger (Thursday)
  - Comment out `cron: '0 20 * * 4'` (Thursday 20:00 UTC), keeping the line for easy restoration
  - Currently only the Monday 20:00 UTC trigger remains active
## Impact
- Lowers the scheduled load on AMD CI runners, saving compute resources
- These changes only affect **scheduled triggers**; normal CI tests on PR submission are unaffected
- The Thursday AITER Scout trigger is temporarily disabled and can be restored by simply uncommenting the line
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28945871887](https://github.com/sgl-project/sglang/actions/runs/28945871887)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28958876894](https://github.com/sgl-project/sglang/actions/runs/28958876894)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
