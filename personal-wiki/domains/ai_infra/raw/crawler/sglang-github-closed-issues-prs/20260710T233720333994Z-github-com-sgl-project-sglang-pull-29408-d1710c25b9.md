---
source_id: sglang-github-closed-issues-prs
title: Avoid implicit field-based side channel in Scheduler planning
canonical_url: https://github.com/sgl-project/sglang/pull/29408
captured_at: '2026-07-10T23:37:20.333994+00:00'
content_hash: d1710c25b917375cfc42f4f9dfb2676d46c5cfb94f6110aa22bf0155e31d4079
---
# Avoid implicit field-based side channel in Scheduler planning

URL: https://github.com/sgl-project/sglang/pull/29408
State: closed
Labels: apple-silicon
Closed at: 2026-07-10T00:55:52Z
Merged at: 2026-07-10T00:55:52Z

`get_next_batch_to_run` and its callee tree (plus the disaggregation analogues `get_next_disagg_prefill_batch_to_run` / `get_next_disagg_decode_batch_to_run` and their trees) used `self.cur_batch` / `self.last_batch` / `self.running_batch` as an implicit in/out side channel. This PR makes those reads and writes explicit: the batch state is passed in as parameters and returned out via a `NextBatchPlan` struct. The fields stay on `self` (they have legitimate readers elsewhere), but the planning methods no longer touch them.

- `get_next_batch_to_run(running_batch, last_batch) -> NextBatchPlan`; callers store `plan.running_batch` back and run `plan.batch_to_run`.
- The leaf builders (`get_new_batch_prefill`, the disagg roots) thread `running_batch` in and out the same way; `get_new_batch_prefill` returns a `NextBatchPlan` like the others.
- A guard test (`test_scheduler_decision_batch_params.py`) asserts via `inspect.getsource` that these methods take the batches as explicit parameters and contain no `self.running_batch` / `self.last_batch` / `self.cur_batch` token — turning "no hidden channel" into an executable invariant.

**Mental model:** the scheduler's core will eventually be split out (e.g. a stateless `SchedulerPlanner`); this removes the hidden coupling that would make such a split leak `self.*` access.

No behavior change: the event loops still own the fields and update them every iteration from the returned plan.

## Equivalence audit

Verified behavior-preserving by an independent read-only Codex audit (verdict: PROVEN). It confirmed that for every changed signature the caller passes the same value previously read from `self.*` and writes the returned `running_batch` back to the same field at the same point in the loop — including the PP `running_mbs[mb_id]` slots, the disagg prefill/decode trees, and the MLX/pd-mux paths — and that no returned plan is dropped.

Known residual (not a behavior change): the DLLM prefill helpers (`dllm/mixin/scheduler.py`) still read `self.running_batch` internally after assigning it, so that branch is outside the guard test's scope. Codex confirmed it mutates the same `ScheduleBatch` object without rebinding, so behavior is unchanged; fully threading it is a follow-up.











































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29061151142](https://github.com/sgl-project/sglang/actions/runs/29061151142)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29061150984](https://github.com/sgl-project/sglang/actions/runs/29061150984)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
