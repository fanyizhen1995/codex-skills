---
source_id: sglang-github-closed-issues-prs
title: Add DP cache affinity by routing key
canonical_url: https://github.com/sgl-project/sglang/pull/26091
captured_at: '2026-07-10T23:37:20.330814+00:00'
content_hash: 6fdc31730ae9ed1fdb40e086bad96200894b31bfebd6a799dc11460f98d91abb
---
# Add DP cache affinity by routing key

URL: https://github.com/sgl-project/sglang/pull/26091
State: closed
Labels: 
Closed at: 2026-07-10T02:54:42Z
Merged at: 

Implement https://github.com/sgl-project/sglang/issues/26066
## Summary
- add `--dp-cache-affinity routing_key` for data-parallel controller routing
- keep requests with the same routing key on the same active DP rank after the first assignment
- make PD prefill `auto` load balancing use `total_tokens` when cache affinity is enabled, and reject the incompatible `follow_bootstrap_room` combination
- add unit coverage for sticky routing, remapping unavailable ranks, direct DP-rank overrides, and server args validation

This can increase cache hit rate on Artificial Analysis Agent workload from about 70% to 96%
 
## Test
- `PYTHONPATH=python python3 -m pytest test/registered/unit/managers/test_dp_cache_affinity.py test/registered/unit/server_args/test_server_args.py -q` (60 passed, Lyris GB300 container)















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #26281458181](https://github.com/sgl-project/sglang/actions/runs/26281458181)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #26281458050](https://github.com/sgl-project/sglang/actions/runs/26281458050)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
