---
source_id: sglang-github-closed-issues-prs
title: Fix Mamba CUDA graph padding outputs
canonical_url: https://github.com/sgl-project/sglang/pull/30974
captured_at: '2026-07-13T23:40:05.161878+00:00'
content_hash: 28b1b6db95cd11ff153507ffb6e7116de140c2b82622dbd2f817ea82b7be0b9e
---
# Fix Mamba CUDA graph padding outputs

URL: https://github.com/sgl-project/sglang/pull/30974
State: closed
Labels: 
Closed at: 2026-07-13T22:11:40Z
Merged at: 

This fixes Mamba CUDA graph padding by zeroing convolution outputs for `PAD_SLOT_ID` rows before they enter the SSM; `causal_conv1d_update_triton` skips those rows and otherwise leaves `torch.empty` data uninitialized. A CPU regression test is included, and the fix completed two two-node GB200 OPD runs with power-of-two captures through 512, including the previously hanging second padded rollout.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29225148097](https://github.com/sgl-project/sglang/actions/runs/29225148097)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29225147952](https://github.com/sgl-project/sglang/actions/runs/29225147952)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
