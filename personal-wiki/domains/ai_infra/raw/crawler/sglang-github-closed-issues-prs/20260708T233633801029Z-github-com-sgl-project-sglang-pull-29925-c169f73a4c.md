---
source_id: sglang-github-closed-issues-prs
title: 'ci: make multi-GPU jit test hangs attributable from the CI log'
canonical_url: https://github.com/sgl-project/sglang/pull/29925
captured_at: '2026-07-08T23:36:33.801029+00:00'
content_hash: c169f73a4c17bdf3f722489bfdf4aac002053f0f234aec4678101ee0258b9e84
---
# ci: make multi-GPU jit test hangs attributable from the CI log

URL: https://github.com/sgl-project/sglang/pull/29925
State: closed
Labels: jit-kernel
Closed at: 2026-07-08T02:56:32Z
Merged at: 2026-07-08T02:56:32Z

## Motivation

The 2026-07-02 `nightly-test-kernel-8-gpu-h200` run ([28558138686](https://github.com/sgl-project/sglang/actions/runs/28558138686)) hung in `test_custom_all_reduce.py` at nproc=2: 23/24 tests passed, then the last test blocked until the 600s harness timeout killed the process group (baseline for the full sweep on the previous night's pass: ~33s).

Investigation points to a transient machine-level glitch on the H200 host that picked up the job, not a code regression — the job passed the 4 preceding nightlies on 4 different runners, the only commit in the window touching the all-reduce path (#29621) is a behavior-preserving refactor of the VMM path (not exercised in this test config), and the host shows no kernel/GPU errors in the failure window.

What the failure did expose is a diagnostics gap: the CI log carried **no evidence of which test hung or where**. pytest's block-buffered progress dots flushed out of order into the next test's output, and no stack was captured before the kill.

## Modifications

- `multigpu_launch`: set `PYTHONUNBUFFERED=1` for torchrun children so per-test progress output reaches the CI log in real time instead of being lost or reordered when a timed-out worker is killed.
- `multigpu_pytest_main`: enable pytest's built-in `faulthandler_timeout` at half the harness budget (300s at the default 600s). A test stuck past the threshold dumps all thread stacks on every rank (stderr is not redirected in non-rank-0 workers) without killing the run, so a hung collective shows exactly which rank is blocked and where, before the outer timeout fires.

Verified locally that the dump fires non-fatally with the hung test's name and full stack.

## Checklist

- [x] Format your code with pre-commit
- [ ] Add unit tests
- [x] Update documentation as needed











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28580125326](https://github.com/sgl-project/sglang/actions/runs/28580125326)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28580125064](https://github.com/sgl-project/sglang/actions/runs/28580125064)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
