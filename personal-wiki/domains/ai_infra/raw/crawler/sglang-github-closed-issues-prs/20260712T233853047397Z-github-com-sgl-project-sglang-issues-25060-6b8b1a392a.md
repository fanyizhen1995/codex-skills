---
source_id: sglang-github-closed-issues-prs
title: '[Bug] [PDD] Priority scheduling is broken in PD disaggregation mode'
canonical_url: https://github.com/sgl-project/sglang/issues/25060
captured_at: '2026-07-12T23:38:53.047397+00:00'
content_hash: 6b8b1a392a02dcac18fa4727281ba6d5a386ac109906104a166d1d3d3412ab97
---
# [Bug] [PDD] Priority scheduling is broken in PD disaggregation mode

URL: https://github.com/sgl-project/sglang/issues/25060
State: closed
Labels: inactive
Closed at: 2026-07-12T00:35:49Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug


When `--enable-priority-scheduling `is used with prefill-decode disaggregation (`--disaggregation-mode` `prefill` or `decode`), request priorities are never assigned req.priority stays None. This causes silent wrong behavior or crashes when the prefill scheduler tries to sort by priority.

 ## Root causes:

  1. _set_or_validate_priority was only called inside the DisaggregationMode.NULL branch of _add_request_to_queue, so PREFILL and DECODE mode requests never got a default
  priority assigned.
  2. get_new_prebuilt_batch (decode side) never called policy.calc_priority, so the waiting queue was always processed FIFO regardless of priority.
  3. DecodePreallocQueue.pop_preallocated processed requests in insertion order — higher-priority requests didn't get KV pre-allocation slots first. Additionally, the sort
  was placed after the abort-scan loop, which invalidated saved indices and could drop healthy requests or leave failed ones in the queue.


### Reproduction

  Start a decode disaggregation server with priority scheduling enabled:
```bash
  python -m sglang.launch_server \
    --model-path <model> \
    --disaggregation-mode {prefill|decode} \
    --enable-priority-scheduling
```

Send a `/generate` request and the prefill server fails:

```bash
File "/venv/lib/python3.12/site-packages/sglang/srt/disaggregation/prefill.py", line 428, in event_loop_overlap_disagg_prefill
[prefill:0]     batch = self.get_next_disagg_prefill_batch_to_run()
[prefill:0]             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[prefill:0]   File "/venv/lib/python3.12/site-packages/sglang/srt/disaggregation/prefill.py", line 375, in get_next_disagg_prefill_batch_to_run
[prefill:0]     batch = self.get_new_batch_prefill()
[prefill:0]             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[prefill:0]   File "/venv/lib/python3.12/site-packages/sglang/srt/managers/scheduler.py", line 2315, in get_new_batch_prefill
[prefill:0]     ret = self._get_new_batch_prefill_raw(
[prefill:0]           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[prefill:0]   File "/venv/lib/python3.12/site-packages/sglang/srt/managers/scheduler.py", line 2361, in _get_new_batch_prefill_raw
[prefill:0]     self.policy.calc_priority(self.waiting_queue, self.running_batch)
[prefill:0]   File "/venv/lib/python3.12/site-packages/sglang/srt/managers/schedule_policy.py", line 122, in calc_priority
[prefill:0]     SchedulePolicy._sort_by_priority_and_fcfs(
[prefill:0]   File "/venv/lib/python3.12/site-packages/sglang/srt/managers/schedule_policy.py", line 307, in _sort_by_priority_and_fcfs
[prefill:0]     waiting_queue.sort(
[prefill:0]   File "/venv/lib/python3.12/site-packages/sglang/srt/managers/schedule_policy.py", line 309, in <lambda>
[prefill:0]     x.priority * priority_sign,
[prefill:0]     ~~~~~~~~~~~^~~~~~~~~~~~~~~
[prefill:0] TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'

```

### Environment

N/A
