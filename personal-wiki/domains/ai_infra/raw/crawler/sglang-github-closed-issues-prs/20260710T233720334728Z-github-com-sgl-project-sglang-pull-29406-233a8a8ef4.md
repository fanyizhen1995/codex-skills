---
source_id: sglang-github-closed-issues-prs
title: Stop reading cur_batch in is_fully_idle and abort_request
canonical_url: https://github.com/sgl-project/sglang/pull/29406
captured_at: '2026-07-10T23:37:20.334728+00:00'
content_hash: 233a8a8ef438e00322f4e3b8e72eaf5bb902090172321284fbb1c9993289dcf7
---
# Stop reading cur_batch in is_fully_idle and abort_request

URL: https://github.com/sgl-project/sglang/pull/29406
State: closed
Labels: 
Closed at: 2026-07-10T00:54:32Z
Merged at: 2026-07-10T00:54:32Z

This PR removes every load-bearing read of `self.cur_batch` outside the PP microbatch slot arrays, in three steps. Two are behavior-preserving; one is an intentional, disclosed narrowing.

The enabling invariant it establishes: **`abort_request` only ever runs at the top of the event loop**, where `self.cur_batch` and `self.last_batch` both hold the previous iteration's batch (or are both `None`) and are therefore equal.

## 1. Grammar-failure aborts mark the request directly (intentional narrowing)

`_apply_prefill_grammar` / `_accept_grammar_tokens` previously aborted a grammar-rejected request by building `AbortReq(rid=req.rid)` and re-dispatching through the full `abort_request` machinery — even though they already hold the `req`. They now set `req.to_finish = FINISH_ABORT()` directly, which is exactly what `abort_request`'s in-flight scan ("method 3") does to that req.

This is the only site that invoked `abort_request` *mid-iteration* (inside `process_batch_result`, between `self.cur_batch = batch` and `self.last_batch = batch`). Removing it is what establishes the invariant above, and is what makes steps 2–3 below exact.

**Behavior change (intentional).** For the failing request the effect is identical (only "method 3" can apply to an in-flight request, and the trailing `req.grammar.finished = req.finished()` is unaffected because `finished()` reads `finished_reason`, not the deferred `to_finish`). But the old call also aborted *other* requests whose rid is a prefix-match of the failing rid (`other.rid.startswith(req.rid)`) — e.g. an unrelated in-flight request `r_child` when request `r` fails, or sibling samples in `n>1` parallel sampling (rids `f"{rid}_{i}"`, so `r_3` would also match `r_30`). Since each request owns its own grammar, one request's grammar failure does not affect the others, so that prefix-fan-out abort was unintended collateral. The new code aborts exactly the failing request.

## 2. `abort_request` reads `last_batch` instead of `cur_batch` (equivalent)

Given the invariant, the non-PP in-flight scan reading `self.last_batch` is identical to reading `self.cur_batch`: at every point `abort_request` runs, the two are equal (or both `None`). PP is unchanged — it scans `running_mbs` + `mbs`.

## 3. `is_fully_idle` drops the redundant `cur_batch` term (equivalent)

The `self.cur_batch is None or self.cur_batch.is_empty()` term never changes the result of `is_fully_idle`:

- **Under PP**, it is a subset of `_pp_microbatches_drained()` (which scans every `running_mbs` and `mbs` slot).
- **Without PP**, every `is_fully_idle` caller runs at the top of the loop where `cur_batch == last_batch`, so the adjacent `last_batch` term already covers it; and `on_idle()` is only reached after `cur_batch` has just been set to `None`.

Together, steps 2–3 remove every load-bearing read of `cur_batch` outside the PP slot arrays, which lets a following PR localize the field cleanly.

## Equivalence audit

An independent read-only Codex audit reviewed all three changes: steps 2 and 3 PROVEN behavior-preserving, and step 1 flagged as exactly the intentional narrowing described above (the prefix-match collateral abort). Concretely, with `running_batch` holding two unfinished decode requests `r` and `r_child` and `r` failing grammar acceptance, the old code aborted both `r` and `r_child` (via `"r_child".startswith("r")`) while the new code aborts only `r`.





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29061092747](https://github.com/sgl-project/sglang/actions/runs/29061092747)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29061092644](https://github.com/sgl-project/sglang/actions/runs/29061092644)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
