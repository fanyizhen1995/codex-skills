---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Serialize FanOutCommunicator queueing calls with a FIFO-fair asyncio.Lock'
canonical_url: https://github.com/sgl-project/sglang/pull/30606
captured_at: '2026-07-09T23:36:35.338342+00:00'
content_hash: 4a8e373dfc6b795aa60880c833ddeacf558c0076363e36651732b2d52de92ab3
---
# [Fix] Serialize FanOutCommunicator queueing calls with a FIFO-fair asyncio.Lock

URL: https://github.com/sgl-project/sglang/pull/30606
State: closed
Labels: run-ci
Closed at: 2026-07-09T07:04:44Z
Merged at: 2026-07-09T07:04:44Z

Concurrent `/server_info` requests can intermittently return 500: `FanOutCommunicator.queueing_call` has a wakeup-window race where a caller arriving between the previous caller's cleanup and the queued waiter's wakeup bypasses the ready queue and trips `assert self._result_event is None` (seen in scheduled CI on `test_get_server_info_concurrent`). A caller that hits the assert also never hands off to the waiters queued behind it, leaving them hung. Replace the hand-rolled ready queue with a FIFO-fair `asyncio.Lock` and add a unit test that deterministically reproduces the interleaving (fails on main, passes with this fix).



























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28998767556](https://github.com/sgl-project/sglang/actions/runs/28998767556)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28998767437](https://github.com/sgl-project/sglang/actions/runs/28998767437)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
