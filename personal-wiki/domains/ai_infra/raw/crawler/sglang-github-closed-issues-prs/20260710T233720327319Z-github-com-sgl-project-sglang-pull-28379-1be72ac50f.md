---
source_id: sglang-github-closed-issues-prs
title: 'Fix: add grammar ready consensus in PP for structured output'
canonical_url: https://github.com/sgl-project/sglang/pull/28379
captured_at: '2026-07-10T23:37:20.327319+00:00'
content_hash: 1be72ac50fbdf762b8948b3d147f6052d36fc00ba768e8ddf8a2a2df810440fa
---
# Fix: add grammar ready consensus in PP for structured output

URL: https://github.com/sgl-project/sglang/pull/28379
State: closed
Labels: run-ci
Closed at: 2026-07-10T06:37:18Z
Merged at: 

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

**Updated: This PR is superseded by another, more lightweight PR #30747 .**

Fix PP scheduler divergence when structured-output requests (requests using `response_format`) cause grammar-ready inconsistency across PP schedulers.

In PP mode, each worker has its own scheduler. Grammar compilation runs asynchronously on CPU, so the same request's grammar can become ready at different wall-clock times on different PP ranks.
However, `GrammarManager.get_ready_grammar_requests()` only synchronized ready/failed grammar state within TP/DP groups, then immediately popped requests from `grammar_queue`.

**This could make PP ranks schedule different batches, which in turn caused sglang to crash.**
This issue can cause several typical error logs:

<details>
<summary> 1. shape xxx is invalid for input of size … </summary>

```bash
  File "/sgl-workspace/sglang/python/sglang/srt/layers/utils/multi_platform.py", line 73, in forward
    return self._forward_method(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/layers/rotary_embedding/base.py", line 335, in forward_cuda
    q_rope = query.view(batch_size, -1, self.head_size)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: shape '[1911, -1, 64]' is invalid for input of size 2048
```
</details>

<details>
<summary> 2. cuda_graph_runner size mismatch </summary>

```bash
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 117, in _grouped_foreach_copy_
    foreach_copy(group_dsts, group_srcs)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 104, in foreach_copy
    torch._foreach_copy_(dsts, srcs)
RuntimeError: The size of tensor a (512) must match the size of tensor b (8192) at non-singleton dimension 0
```
</details>

<details>
<summary> 3. just stuck, then Scheduler watchdog timeout </summary>
stuck for default 5 minutes, then scheduler watchdog timeout is triggered.
PP ranks show different batches:

```bash
# PP 0
scheduler.cur_batch.batch_size()=3
scheduler.cur_batch.reqs=...
...

# PP 1
scheduler.cur_batch.batch_size()=2
scheduler.cur_batch.reqs=...
```
</details>

This PR makes grammar readiness a PP-consensus decision before requests are moved from `grammar_queue` to the scheduler queue.

Fixes #28424


## Modifications

<!-- Detail the changes made in this pull request. -->

- Split grammar ready handling into two phases (`grammar_manager.py`):
  - `poll_ready_grammar_request_rids()` only polls and returns `[ready_rids, failed_rids]`.
  - `pop_ready_grammar_requests_by_rids()` resolves futures, writes grammar cache, handles failures/timeouts, and removes requests from `grammar_queue`.
  - Keep non-PP behavior through `get_ready_grammar_requests()`, implemented as poll + pop.
  
- Add two-round PP P2P grammar consensus. The flow of this consensus follows the existing consensus implementation mechanism in the PD loop (i.e., bootstrap, release). (`scheduler_pp_mixin.py`):
  - Gate normal grammar ready processing so PP schedulers do not directly pop grammar requests outside PP consensus.
  - First round: PP0 -> last rank, ready rids use intersection and failed rids use union.
  - Second round: last rank -> PP0 -> last rank, and only then every PP rank pops `grammar_queue` and schedules the ready/failed requests.
  - The above grammar-ready consensus applied in regular PP loop and two PD loops. 
- Related small modifications on `scheduler.py` and `disaggregation/decode.py`
- Add unit tests for PP grammar consensus.


## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

No impact on accuracy.

Test on Kimi-K2.6:

  | score
-- | --
aime26 | 1
GPQA_diamond | 0.9141

Test on Qwen3-8B:

```bash
# python3 -m sglang.test.few_shot_gsm8k --num-questions 1319
Accuracy: 0.911
Invalid: 0.000
Latency: 52.761 s
Output throughput: 3073.801 token/s
```


<!-- notionvc: ec5c6ae9-0676-459d-af13-af84790bd0ff -->

## Speed Tests and Profiling

Test with sglang.bench_serving (also with specifying `response_format`). No obvious performance change was observed.


<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
4. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
5. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
6. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28995970083](https://github.com/sgl-project/sglang/actions/runs/28995970083)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28995970027](https://github.com/sgl-project/sglang/actions/runs/28995970027)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
