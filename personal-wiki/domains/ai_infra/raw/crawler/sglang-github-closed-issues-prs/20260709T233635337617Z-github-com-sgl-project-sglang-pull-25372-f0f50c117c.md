---
source_id: sglang-github-closed-issues-prs
title: '[PDD] Add true request retraction for PDD'
canonical_url: https://github.com/sgl-project/sglang/pull/25372
captured_at: '2026-07-09T23:36:35.337617+00:00'
content_hash: f0f50c117cfaa16e6c84d8b6964fef81bd1c72f803e8c18dabaa9255f2f7f2a4
---
# [PDD] Add true request retraction for PDD

URL: https://github.com/sgl-project/sglang/pull/25372
State: closed
Labels: run-ci, model-gateway, run-ci-extra
Closed at: 2026-07-09T07:33:02Z
Merged at: 2026-07-09T07:33:02Z


## Motivation
More context here in `sglang-miles` branch: [scheduler.py:L3756-L3763](https://github.com/sgl-project/sglang/blob/sglang-miles/python/sglang/srt/managers/scheduler.py#L3756-L3763
)

Currently we can't do true request retraction in PDD mode. This PR adds it: on retract, the decode worker drops the KV cache and, on  continue_generation , asks the  original prefill worker to recompute the prefix KV under the current weights (replaying the last emitted token). This makes retract →  update_weights  → continue  correct in PDD mode.

## Modifications
- `decode.py` : stage retracted reqs ( hold_rebootstrap ) during the pause and enqueue them on resume ( release_held_rebootstrap ) so the prealloc queue stays empty and    the  update_weights  cache flush succeeds. Rebootstrap reqs preallocate fresh KV and bypass the decode radix cache.
 -  `disaggregation/conn.py` : the  /generate  recompute dispatch lives on  CommonKVReceiver.dispatch_prefill_recompute  + a shared executor on  CommonKVManager ; a failed  /generate     routes through  abort()  →  KVPoll.Failed , reusing the standard transfer-failure path.
 -  `prefill.py` : at the final-chunk commit, force the next token to  pd_rebootstrap_forced_output_id .
 - `plumbing`: new  pd_rebootstrap_prefill_url  /  pd_rebootstrap_forced_output_id  through io_struct, schedule_batch, scheduler, tokenizer_manager.
 - `router`: inject  pd_rebootstrap_prefill_url  ( mini_lb.py  +  pd_router.rs ).

## Tests

-  **Unit (CPU):**  test_scheduler_pause_generation.py  (retract stages via  hold_rebootstrap , continue releases);  test_priority_scheduling_disaggregation.py  (rebootstrap    payload build, receiver→manager dispatch, abort-on-failure routing).

- **E2E:**  test_disaggregation_basic.py::TestDisaggregationPauseResumeDecodeRetract  — retract pause/continue and retract +  update_weights  (both assert  num_retractions    > 0 ).



























































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28964152496](https://github.com/sgl-project/sglang/actions/runs/28964152496)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28964152195](https://github.com/sgl-project/sglang/actions/runs/28964152195)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
