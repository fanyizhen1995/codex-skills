---
source_id: sglang-github-closed-issues-prs
title: Cleanup IDLE replay branch and `alloc_extend_swa_tail` mapping
canonical_url: https://github.com/sgl-project/sglang/pull/26297
captured_at: '2026-07-08T23:36:33.786458+00:00'
content_hash: 828fac0b97941c354f1d158df2c93245e2e943a84788bb609fabd68c26fa6a5d
---
# Cleanup IDLE replay branch and `alloc_extend_swa_tail` mapping

URL: https://github.com/sgl-project/sglang/pull/26297
State: closed
Labels: deepseek, run-ci, run-ci-extra
Closed at: 2026-06-25T03:15:11Z
Merged at: 

Two small cleanups following up on #26292:

1. **dsv4 backend IDLE replay branch** — the local re-assignments to `seq_lens`/`req_pool_indices`/`out_cache_loc` allocated fresh tensors that never reached the captured graph (which reads from the original buffer slices). After #26292 paired `req_pool_indices.zero_()` with `seq_lens.fill_()` in `populate_from_forward_batch`, those GPU buffers are already filled with safe IDLE defaults. Drop the dead writes and keep only the CPU-side / Python-int fix-up.

2. **`alloc_extend_swa_tail` `swa_tail_len == 0`** — the non-zero branch explicitly resets the prefix portion of `full_to_swa_index_mapping` to 0. Mirror that on the early-return path so every slot the function hands back has its SWA mapping reset, regardless of `tail_len`.

## Test plan
- [ ] CI green



























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #26396575386](https://github.com/sgl-project/sglang/actions/runs/26396575386)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #26396575213](https://github.com/sgl-project/sglang/actions/runs/26396575213)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
