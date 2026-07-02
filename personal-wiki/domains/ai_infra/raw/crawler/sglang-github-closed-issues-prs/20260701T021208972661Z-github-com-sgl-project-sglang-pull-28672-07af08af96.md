---
source_id: sglang-github-closed-issues-prs
title: Skip custom all-reduce v2 CUDA graph capture with torch memory saver
canonical_url: https://github.com/sgl-project/sglang/pull/28672
captured_at: '2026-07-01T02:12:08.972661+00:00'
content_hash: 07af08af96ef4bbc87736701b307a50517ede5a71f11f6f9ab4b70f78aa84a07
---
# Skip custom all-reduce v2 CUDA graph capture with torch memory saver

URL: https://github.com/sgl-project/sglang/pull/28672
State: closed
Labels: jit-kernel
Closed at: 2026-06-29T22:44:31Z
Merged at: 

## Motivation

Port of #27948 (which targets the internal `sglang-miles` branch) onto `main`. Same fix as #19162, which handled the v1 custom all-reduce path; this extends the same `torch_memory_saver` (TMS) handling to the v2 (jit_kernel) path.

### Root Cause
1. `--colocate` enables `torch_memory_saver` (TMS) for the rollout engine.
2. Custom all-reduce v2 captured graph inputs without using the unregistered graph-input path.
3. The kernel expected runtime-allocated IPC handles, but TMS hooked them to driver IPC handles during capture.
4. `custom_all_reduce.cuh` then received invalid graph input metadata and failed at the runtime check:
```
Exception: Capture cuda graph failed: Runtime check failed at .../sgl_kernel/distributed/custom_all_reduce.cuh:37: CUDA error: invalid argument
```

## Modifications

When `SGLANG_MEMORY_SAVER_CUDA_GRAPH=true`, custom all-reduce v2 treats graph inputs as unregistered:
- New `set_cuda_graph_register_inputs` toggle + `m_register_graph_inputs` flag on the kernel object; the pull kernel only routes through `allocate_graph_capture_input` when registration is enabled.
- `CustomAllReduceV2.capture()` disables registration during capture under TMS and skips the entire post-capture registration (both the VMM and the IPC branch present on `main`).

Adapted to `main`'s structure: `main` added the VMM graph-input path (`get_graph_capture_ptrs` / `register_peer_mapped_inputs` / `VmmGraphInputManager`) that the `sglang-miles` branch lacks, so the TMS skip is gated above both the VMM and IPC branches.

## Accuracy Tests

- Original #27948: 8-GPU Miles Megatron colocate passed step0 end-to-end, with v2 init and CUDA graph capture.
- This port: jit_kernel was **not** recompiled locally (no GPU build env); kernel-level verification relies on CI and a colocate run.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27783209748](https://github.com/sgl-project/sglang/actions/runs/27783209748)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27783209457](https://github.com/sgl-project/sglang/actions/runs/27783209457)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
