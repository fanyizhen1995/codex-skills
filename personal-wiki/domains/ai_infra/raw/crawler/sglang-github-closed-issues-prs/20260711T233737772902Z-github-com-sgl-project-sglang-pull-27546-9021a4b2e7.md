---
source_id: sglang-github-closed-issues-prs
title: 'fix(pd): do not abort when req.disagg_prefill_dp_rank is used'
canonical_url: https://github.com/sgl-project/sglang/pull/27546
captured_at: '2026-07-11T23:37:37.772902+00:00'
content_hash: 9021a4b2e787658b206e64a84888a1e4769f262aace41bd129eb5f56a0cda259
---
# fix(pd): do not abort when req.disagg_prefill_dp_rank is used

URL: https://github.com/sgl-project/sglang/pull/27546
State: closed
Labels: run-ci
Closed at: 2026-07-11T04:08:02Z
Merged at: 2026-07-11T04:08:02Z

Commit 3600465 assumes that there are two possibilities:
* follow_bootstrap_room is used, the dp rank should match the bootstrap dp rank, and no register is needed
* follow_bootstrap_room is not used, and register is not needed

There is a third possibility from commit 539f772:
* req.disagg_prefill_dp_rank is used, and register is not needed

Currently, if we try to explicit load balance using req.disagg_prefill_dp_rank, it will abort due to not matching bootstrap dp rank.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29058295349](https://github.com/sgl-project/sglang/actions/runs/29058295349)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29058295232](https://github.com/sgl-project/sglang/actions/runs/29058295232)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
