---
source_id: sglang-github-closed-issues-prs
title: Fix immediate profiler step range boundary
canonical_url: https://github.com/sgl-project/sglang/pull/30215
captured_at: '2026-07-10T23:37:20.326343+00:00'
content_hash: c4aa0014a2a1f782aa0dbe81238fcd50523a26a3444b125702db246fb35ce29e
---
# Fix immediate profiler step range boundary

URL: https://github.com/sgl-project/sglang/pull/30215
State: closed
Labels: 
Closed at: 2026-07-10T02:47:24Z
Merged at: 2026-07-10T02:47:24Z

## Summary

- capture all requested batch steps when profiling starts immediately
- preserve the existing explicit start_step range behavior

## Root cause

The scheduler increments the forward counter and checks profiler boundaries before executing each batch. The delayed-start path already accounts for this ordering by clamping profiler_start_forward_ct to get_forward_ct() + 1. The immediate-start target calculation omitted the corresponding +1, so a target of current plus num_steps stopped before the final requested batch and captured only num_steps minus one batches.

For the minimal case where the current forward count is 0 and num_steps is 1, the old target is 1. The first run_batch increments the counter to 1 and triggers profiler stop before that batch executes, so the trace contains zero batch steps.

## Fix

Add the missing analogous +1 to the immediate-profile exclusive stop boundary so all requested batch steps execute before profiling stops. Explicit start_step ranges remain unchanged.

## Validation

- uvx --from pre-commit pre-commit run --all-files --show-diff-on-failure

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28769677263](https://github.com/sgl-project/sglang/actions/runs/28769677263)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28769677215](https://github.com/sgl-project/sglang/actions/runs/28769677215)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
