---
source_id: sglang-github-closed-issues-prs
title: dcp start layer error when enable pp
canonical_url: https://github.com/sgl-project/sglang/pull/29600
captured_at: '2026-07-07T23:35:30.912794+00:00'
content_hash: eec996db9afc640b3ab97297f83da48545c0b2bf337f8ee46fd0e308d081e1c9
---
# dcp start layer error when enable pp

URL: https://github.com/sgl-project/sglang/pull/29600
State: closed
Labels: 
Closed at: 2026-07-07T09:07:33Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

start server error when enable pp

## Modifications

python/sglang/srt/model_executor/runner/eager_runner.py

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

before this pr, enable pp when warm_up 
```
[2026-06-27 08:55:14 PP2 ATTN_CP3 TP3 EP3] Scheduler hit an exception: Traceback (most recent call last):
  File "/home/**/sglang/python/sglang/srt/managers/scheduler.py", line 4303, in run_scheduler_process
    scheduler.run_event_loop()
  File "/home/**/sglang/python/sglang/srt/managers/scheduler.py", line 1501, in run_event_loop
    dispatch_event_loop(self)
  File "/home/**/sglang/python/sglang/srt/managers/scheduler.py", line 4173, in dispatch_event_loop
    scheduler.event_loop_pp_disagg_prefill()
  File "/usr/local/python3.11.15/lib/python3.11/site-packages/torch/utils/_contextlib.py", line 124, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/managers/scheduler_pp_mixin.py", line 269, in event_loop_pp_disagg_prefill
    result, self.launch_event = self._pp_launch_batch(
                                ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/managers/scheduler_pp_mixin.py", line 1251, in _pp_launch_batch
    result = self.run_batch(self.cur_batch, pp_proxy_tensors)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/utils/nvtx_utils.py", line 109, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/managers/scheduler.py", line 3316, in run_batch
    batch_result = self.model_worker.forward_batch_generation(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/managers/tp_worker.py", line 563, in forward_batch_generation
    out = self.model_runner.forward(
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/model_executor/model_runner.py", line 2958, in forward
    output = self._forward_raw(
             ^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/model_executor/model_runner.py", line 3092, in _forward_raw
    ret = self.eager_runner.execute(
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/model_executor/runner/eager_runner.py", line 206, in execute
    return self._execute_extend(forward_batch, pp_proxy_tensors)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/model_executor/runner/eager_runner.py", line 278, in _execute_extend
    get_token_to_kv_pool().get_key_buffer(0).shape,
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/**/sglang/python/sglang/srt/hardware_backend/npu/memory_pool_npu.py", line 399, in get_key_buffer
    return self.k_buffer[layer_id - self.start_layer]
           ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
IndexError: index -18 is out of bounds for dimension 0 with size 10

```
after this pr 
```
[2026-06-27 10:02:58 PP0 ATTN_CP1 TP1 EP1] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP0 ATTN_CP3 TP3 EP3] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP0 ATTN_CP0 TP0 EP0] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP0 ATTN_CP2 TP2 EP2] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.93
[2026-06-27 10:02:58 PP1 ATTN_CP0 TP0 EP0] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP1 ATTN_CP1 TP1 EP1] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP1 ATTN_CP3 TP3 EP3] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.95
[2026-06-27 10:02:58 PP1 ATTN_CP2 TP2 EP2] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP2 ATTN_CP0 TP0 EP0] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP2 ATTN_CP3 TP3 EP3] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP2 ATTN_CP2 TP2 EP2] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP2 ATTN_CP1 TP1 EP1] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.94
[2026-06-27 10:02:58 PP3 ATTN_CP0 TP0 EP0] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.93
[2026-06-27 10:02:58 PP3 ATTN_CP2 TP2 EP2] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.93
[2026-06-27 10:02:58 PP3 ATTN_CP3 TP3 EP3] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.93
[2026-06-27 10:02:58 PP3 ATTN_CP1 TP1 EP1] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, #bootstrap-req: 0, #inflight-req: 1, npu graph: False, input throughput (token/s): 2.93
[2026-06-27 10:02:58] INFO:     80.48.29.109:59868 - "POST /generate HTTP/1.1" 200 OK
[2026-06-27 10:02:58] Disaggregation warmup request completed with status 200, resp: [{'text': ' /', 'output_ids': [608], 'meta_info': {'id': '13d4cb497f624d57ad5469f3d4923f3a', 'finish_reason': {'type': 'length', 'length': 0}, 'prompt_tokens': 4, 'weight_version': 'default', 'num_retractions': 0, 'reasoning_tokens': 0, 'completion_tokens': 1, 'cached_tokens': 0, 'cached_tokens_details': None, 'dp_rank': None, 'e2e_latency': 24.153910679975525, 'response_sent_to_client_ts': 1782554578.7763164}}]
[2026-06-27 10:02:58] End of disaggregation warmup
[2026-06-27 10:02:58] The server is fired up and ready to roll!

```

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28779375162](https://github.com/sgl-project/sglang/actions/runs/28779375162)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28779375022](https://github.com/sgl-project/sglang/actions/runs/28779375022)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
