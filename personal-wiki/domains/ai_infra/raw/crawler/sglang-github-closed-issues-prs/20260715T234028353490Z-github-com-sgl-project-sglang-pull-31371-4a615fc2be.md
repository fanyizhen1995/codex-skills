---
source_id: sglang-github-closed-issues-prs
title: '[CI] Remove nightly registrations redundant with scheduled stage runs'
canonical_url: https://github.com/sgl-project/sglang/pull/31371
captured_at: '2026-07-15T23:40:28.353490+00:00'
content_hash: 4a615fc2beb35ac50fbb4ad62391eff06d369f3bc11e8a55d88c2aa9f5fae03f
---
# [CI] Remove nightly registrations redundant with scheduled stage runs

URL: https://github.com/sgl-project/sglang/pull/31371
State: closed
Labels: quant, lora, hicache
Closed at: 2026-07-15T21:12:08Z
Merged at: 2026-07-15T21:12:08Z

Tests registered in a PR stage already run in the 2x-daily scheduled full runs (`run_all_tests=true` dispatches every base/extra/jit stage, and `call-pr-test-extra` fires on schedule), so a `nightly=True` registration in the same file runs the same test on the same runner class a third time.

This removes the 32 registrations where the nightly run is an exact duplicate. Kept: nightly registrations in the 19 files using `get_ci_test_range` / `SGLANG_JIT_KERNEL_RUN_FULL_TESTS` (the nightly-kernel jobs set that env to expand parameter sweeps, so their nightly pass is the only full-range coverage), nightly-only tests, and AMD/NPU registrations.























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29450917664](https://github.com/sgl-project/sglang/actions/runs/29450917664)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29450917311](https://github.com/sgl-project/sglang/actions/runs/29450917311)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
