---
source_id: sglang-github-closed-issues-prs
title: '[misc] Move SchedulerRecvSkipper into scheduler_components'
canonical_url: https://github.com/sgl-project/sglang/pull/31222
captured_at: '2026-07-14T23:40:21.664231+00:00'
content_hash: 1e57fce8b9501f988c0951a07470bfb1b63fb9b6227c3e36ca6820c2d331d7c3
---
# [misc] Move SchedulerRecvSkipper into scheduler_components

URL: https://github.com/sgl-project/sglang/pull/31222
State: closed
Labels: run-ci
Closed at: 2026-07-14T23:35:04Z
Merged at: 2026-07-14T23:35:04Z

Pure move: `managers/scheduler_recv_skipper.py` -> `managers/scheduler_components/recv_skipper.py` (R100 rename) plus import updates. The skipper is constructed by the scheduler and consumed by `scheduler_components/request_receiver.py`, matching the directory's convention.

Stacks on #30457.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29373338947](https://github.com/sgl-project/sglang/actions/runs/29373338947)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29373338850](https://github.com/sgl-project/sglang/actions/runs/29373338850)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
