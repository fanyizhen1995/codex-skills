---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Run MI355X disaggregation Nightly Test with runtime checkout code mechanism'
canonical_url: https://github.com/sgl-project/sglang/pull/30386
captured_at: '2026-07-08T23:36:33.803213+00:00'
content_hash: 1d6fb61eedacd3eb88d726455a1df84142b3195e3de1d31dba5d2a56587245f7
---
# [AMD] Run MI355X disaggregation Nightly Test with runtime checkout code mechanism

URL: https://github.com/sgl-project/sglang/pull/30386
State: closed
Labels: amd
Closed at: 2026-07-08T01:27:50Z
Merged at: 2026-07-08T01:27:50Z

## Summary

- Run the MI355X disagg nightly against the workflow checkout instead of image-baked `sglang` / `sglang-router` packages.
- Stage the checkout on shared NFS, mount it read-only into Slurm containers, and reinstall checkout `sglang` for prefill/decode/bench.
- Build and reinstall checkout `sglang-router` in the bench container before launching the router.
- Add `SGLANG_USE_CHECKOUT_RUNTIME=0` opt-out to use image-baked packages.
- Clean per-run MI355X scratch state and avoid staging `.git/config`.
- Support recipe-driven `max_total_tokens`; cap DSV4 Flash MI355X 1k/1k configs at `8551168`.

## Tests

- Accuracy test: passed.

<img width="328" height="99" alt="image" src="https://github.com/user-attachments/assets/e8546038-c596-464e-b41f-cd4b20800447" />

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28873717185](https://github.com/sgl-project/sglang/actions/runs/28873717185)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28873716286](https://github.com/sgl-project/sglang/actions/runs/28873716286)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
