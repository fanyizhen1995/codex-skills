---
source_id: sglang-github-closed-issues-prs
title: Warm DeepGEMM MHC prenorm split buckets
canonical_url: https://github.com/sgl-project/sglang/pull/27729
captured_at: '2026-07-14T23:40:21.665230+00:00'
content_hash: 24947f5de8152c804e6308ec356503e8601b9179dc4049ba628d8cb0430b12cd
---
# Warm DeepGEMM MHC prenorm split buckets

URL: https://github.com/sgl-project/sglang/pull/27729
State: closed
Labels: 
Closed at: 2026-07-14T22:13:50Z
Merged at: 

## Summary
- Treat split-mode `TF32_HC_PRENORM_GEMM` warmup as one auto-split session instead of keying full warmup by the first observed `num_splits`.
- Recompute the MHC prenorm `num_splits` for each warmup `m`, so non-fast warmup covers the real `(m, num_splits=f(m))` buckets.
- Add representative `m` values for all split buckets to fast warmup so sparse sampling does not miss a `num_splits` variant.

## Motivation
After routing MHC prenorm through the DeepGEMM wrapper, the previous warmup loop iterated all selected `m` values with a fixed `num_splits` from the first real call. This could leave other MHC split buckets cold until the first benchmark request hit them.

## Tests


<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27244295645](https://github.com/sgl-project/sglang/actions/runs/27244295645)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27244295518](https://github.com/sgl-project/sglang/actions/runs/27244295518)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
