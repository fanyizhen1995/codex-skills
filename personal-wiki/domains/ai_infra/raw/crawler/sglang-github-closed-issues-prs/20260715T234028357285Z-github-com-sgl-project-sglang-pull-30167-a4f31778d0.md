---
source_id: sglang-github-closed-issues-prs
title: 'Fix MiMo-V2 on Blackwell: FA3 fallback and auto-select attention backend'
canonical_url: https://github.com/sgl-project/sglang/pull/30167
captured_at: '2026-07-15T23:40:28.357285+00:00'
content_hash: a4f31778d0cb9a58162485e922bc56fe9abbc8e198e9c8c69d7dd802756ce6c3
---
# Fix MiMo-V2 on Blackwell: FA3 fallback and auto-select attention backend

URL: https://github.com/sgl-project/sglang/pull/30167
State: closed
Labels: 
Closed at: 2026-07-15T14:40:35Z
Merged at: 

## Summary
- **mimo_audio.py**: Fall back to triton `context_attention_fwd` when `sgl_kernel.flash_attn` is unavailable (e.g. sm103/Blackwell where FA3 is not supported)
- **overrides.py**: Auto-select `fa4` (Blackwell) or `flashinfer` (Hopper) attention backend for MiMoV2 since `trtllm_mha` lacks the `headDimQk=192` kernel

MiMo-V2 uses a non-standard `head_dim=192` for QK, which `trtllm_mha` does not have a precompiled kernel for. Without this fix, launching MiMo-V2.5-Pro on GB300 fails at model import (FA3 not available on sm103) and at attention kernel dispatch (missing trtllm_mha kernel for headDimQk=192).

Tested with MiMo-V2.5-Pro on 2-node TP8 GB300 (cross-node MNNVL).







































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28745588001](https://github.com/sgl-project/sglang/actions/runs/28745588001)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28745587913](https://github.com/sgl-project/sglang/actions/runs/28745587913)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
