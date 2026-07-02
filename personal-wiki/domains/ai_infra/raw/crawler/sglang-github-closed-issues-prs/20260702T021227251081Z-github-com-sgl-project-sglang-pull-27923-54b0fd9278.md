---
source_id: sglang-github-closed-issues-prs
title: Fix MambaPool.clear_slots OOM by replacing expand-based tensor allocation with
  scalar zeroing
canonical_url: https://github.com/sgl-project/sglang/pull/27923
captured_at: '2026-07-02T02:12:27.251081+00:00'
content_hash: 54b0fd9278d14b855107b6740a8c1e764de2bf98728b458182ba595b55ae34f3
---
# Fix MambaPool.clear_slots OOM by replacing expand-based tensor allocation with scalar zeroing

URL: https://github.com/sgl-project/sglang/pull/27923
State: closed
Labels: run-ci
Closed at: 2026-07-02T01:26:56Z
Merged at: 2026-07-02T01:26:56Z

## Motivation

NPU OOM was observed when launching the Qwen3.6-35B-A3B service. The root cause is in `MambaPool.clear_slots`, which creates temporary expanded tensors via `torch.zeros(1).expand(...)` for clearing mamba pool slots. On NPU, this allocates significant temporary memory during each extend forward pass and triggers OOM.

## Modifications

- Replaced the `torch.zeros(1).expand(...)` + advanced indexing assignment in `clear_slots` with direct scalar assignment `t[:, indices] = 0`, which avoids temporary tensor allocation on all devices.

## Accuracy Tests

No accuracy impact — scalar zeroing is semantically identical to the original operation. Model output is unaffected.

```
┌─────────────────┬───────────┬──────────┬──────────┬───────┬─────────┬─────────┐
│ Model           │ Dataset   │ Metric   │ Subset   │   Num │   Score │ Cat.0   │
├─────────────────┼───────────┼──────────┼──────────┼───────┼─────────┼─────────┤
│ Qwen3.5-35B-A3B │ gsm8k     │ mean_acc │ main     │   200 │    0.98 │ default │
└─────────────────┴───────────┴──────────┴──────────┴───────┴─────────┴─────────┘
```

## Speed Tests and Profiling

This fix resolves the OOM issue and allows the service to run normally. By avoiding the intermediate expanded zero tensor, memory pressure during prefill is reduced across all hardware backends.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28503707122](https://github.com/sgl-project/sglang/actions/runs/28503707122)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28503706947](https://github.com/sgl-project/sglang/actions/runs/28503706947)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
