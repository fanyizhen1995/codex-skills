---
source_id: sglang-github-closed-issues-prs
title: '[BUG] Fix HiSparse preallocation for hybrid SWA decode'
canonical_url: https://github.com/sgl-project/sglang/pull/30601
captured_at: '2026-07-10T23:37:20.325146+00:00'
content_hash: 782b801ed974c41f1e5af64d0dc79bc2436b15731e169cd2ce20b4333b0a1686
---
# [BUG] Fix HiSparse preallocation for hybrid SWA decode

URL: https://github.com/sgl-project/sglang/pull/30601
State: closed
Labels: 
Closed at: 2026-07-10T09:17:11Z
Merged at: 

## Motivation

HiSparse decode preallocation did not correctly handle hybrid SWA models. The existing path allocated logical indices with the generic HiSparse logic, which could incorrectly clamp admission control by SWA availability and allocate full logical KV for SWA layers instead of only the sliding-window tail.


## Changes

- Use full logical allocator availability for HiSparse admission control when SWA tail preallocation is enabled.
- Add `alloc_extend_swa_tail` support to the HiSparse KV pool allocator.
- Update the HiSparse direct-to-host decode path to preserve the normal hybrid SWA allocation behavior:
  - allocate full logical KV for full-attention layers
  - allocate only the SWA tail for sliding-window layers
  - track `swa_evicted_seqlen` accordingly
 
## test res
befor-deepseekv4-hisparse：
<img width="2780" height="122" alt="image" src="https://github.com/user-attachments/assets/0bc90060-5db6-4303-abe0-39123338cb56" />


after-deepseekv4-fix_bug-hisparse：
<img width="3240" height="104" alt="image" src="https://github.com/user-attachments/assets/9bb2f4f0-8fd6-4094-90e9-dea8d0706c30" />







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28995858064](https://github.com/sgl-project/sglang/actions/runs/28995858064)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28995857971](https://github.com/sgl-project/sglang/actions/runs/28995857971)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
