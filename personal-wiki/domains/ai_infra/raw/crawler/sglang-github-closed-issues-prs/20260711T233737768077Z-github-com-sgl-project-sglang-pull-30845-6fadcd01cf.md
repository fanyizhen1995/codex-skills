---
source_id: sglang-github-closed-issues-prs
title: Fix unfinished SWA boundary in legacy radix cache
canonical_url: https://github.com/sgl-project/sglang/pull/30845
captured_at: '2026-07-11T23:37:37.768077+00:00'
content_hash: 6fadcd01cf036b1f34f6c1c883a01aaf9f00feed81aeded755887f8e761c2c57
---
# Fix unfinished SWA boundary in legacy radix cache

URL: https://github.com/sgl-project/sglang/pull/30845
State: closed
Labels: 
Closed at: 2026-07-11T17:38:53Z
Merged at: 

## Motivation

During chunked prefill, SWA eviction can release KV pages before an unfinished
request is inserted into the radix tree. The eviction boundary is tracked by
`req.swa_evicted_seqlen`, and `SWARadixCache.insert()` uses it to distinguish
released SWA KV from live reusable KV.

`cache_finished_req()` already forwards this boundary, but the legacy
`SWARadixCache.cache_unfinished_req()` path leaves it at the default value of
zero. Released SWA pages can therefore be represented as reusable cached KV
instead of tombstones.

#29350 fixed the corresponding bookkeeping path for `UnifiedRadixCache`. This
PR applies the same correctness fix to `SWARadixCache`, which remains the
default while `SGLANG_ENABLE_UNIFIED_RADIX_TREE` is disabled.

## Modifications

- Forward `req.swa_evicted_seqlen` through `InsertParams` when caching an
  unfinished request.
- Add a CPU regression test covering boundary propagation and cache lock state.
- Register the regression test in the CPU CI suite.

#30013 also touches this call site as part of a broader SWA-island optimization.
This PR is limited to the unconditional correctness fix and does not introduce
its allocation or decode behavior.

## Accuracy Tests

This change fixes cache bookkeeping and does not modify model forward code or
kernels.

The regression test fails on the unpatched `main` branch:

- `AssertionError: 0 != 2`
- `Ran 1 test in 0.002s`
- `FAILED (failures=1)`

With this fix:

- `Ran 1 test in 0.001s`
- `OK`

## Speed Tests and Profiling

No performance impact is expected. The change only forwards metadata already
maintained by the request and adds no model work, allocation, or KV copy.

## Checklist

- [x] Code formatting and applicable pre-commit checks pass.
- [x] Added a CPU unit test for the regression.
- [x] Documentation is not required because there is no user-facing API or
      configuration change.
- [x] Accuracy implications and performance impact are documented above.
- [x] The change follows the existing SGLang code style.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29143867438](https://github.com/sgl-project/sglang/actions/runs/29143867438)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29143867336](https://github.com/sgl-project/sglang/actions/runs/29143867336)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
