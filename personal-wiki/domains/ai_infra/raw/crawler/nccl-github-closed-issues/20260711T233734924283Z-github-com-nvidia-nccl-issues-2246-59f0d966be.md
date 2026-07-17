---
source_id: nccl-github-closed-issues
title: '[Question]: How does the CuTeDSL device API legally dereference the host-side
  `ncclDevComm` on the device?'
canonical_url: https://github.com/NVIDIA/nccl/issues/2246
captured_at: '2026-07-11T23:37:34.924283+00:00'
content_hash: 59f0d966be2aa02cae518373a605c811eab65080177741f167aaada5aeeb1b83
---
# [Question]: How does the CuTeDSL device API legally dereference the host-side `ncclDevComm` on the device?

URL: https://github.com/NVIDIA/nccl/issues/2246
State: closed
Labels: question
Closed at: 2026-07-11T02:09:03Z
Merged at: 

### Question

## Summary

I'm trying to understand the memory model behind the CuTeDSL NCCL device-API bindings (`nccl.core.device.cute`). A host-created `ncclDevComm` is passed by value into the kernel as a raw 64-bit pointer and then dereferenced on the device:

```python
# host side
dev_comm = nccl_comm.create_dev_comm(requirements=reqs)   # dev_comm.ptr is a host VA (Python int)
lsa_test(dev_comm.ptr, win.handle)                         # dev_comm.ptr passed as a plain integer
```

```python
@cute.jit
def lsa_test(dev_comm: cutlass.Int64, buf_win: cutlass.Int64):
    lsa_read_kernel(dev_comm, buf_win).launch(grid=[1,1,1], block=[WARP_SIZE,1,1])

@cute.kernel
def lsa_read_kernel(dev_comm, buf_win):
    dev_comm = nccl_cute.DevComm(dev_comm)   # int -> inttoptr -> !llvm.ptr (no deref yet)
    buf_win  = nccl_cute.Window(buf_win)
    lsa_rank = dev_comm.lsa_rank             # <-- first DEVICE deref of ncclDevComm; faults here
    lsa_size = dev_comm.lsa_size
    ...
```

On **H20** this fails at runtime with:

```
cuda.core._utils.cuda_utils.CUDAError: cudaErrorIllegalAddress:
The device encountered a load or store instruction on an invalid memory address.
```

The first device-side dereference is `dev_comm.lsa_rank` (an `ncclDevComm` field accessor), which runs before any window access — so the failure is about `ncclDevComm`, not the window. (The registered window is a symmetric resource that is device-accessible by construction, so it's out of scope here.)

The disassembly confirms `dev_comm` is passed in **as a plain `.u64` scalar value** (no struct marshaling, no by-value copy of the struct) and is used directly as an address inside the kernel:

```
.visible .entry kernel_..._kernel____0(
    .param .u64 ..._param_0,   // dev_comm.ptr  (just a 64-bit value)
    .param .u64 ..._param_1,   // win.handle
)
.reqntid 32, 1, 1
{ ... }
```

## What I think is happening (please correct me)

- `dev_comm.ptr` is the **host virtual address** of the `ncclDevComm` struct created by `ncclDevCommCreate` (the Python binding allocates it on the host heap).
- It is passed by value as a `u64` kernel parameter, then `inttoptr`-ed inside the kernel. The PTX `.param .u64` above confirms only the raw pointer value is handed to the kernel — nothing about the pointed-to struct is copied in.
- The public fields are read through `__device__` accessor functions linked from `libnccl_device.bc` (`ncclDevComm_Rank`, `ncclDevComm_LsaRank`, ...), i.e. the **device** dereferences that host pointer.
- On a discrete x86 + Hopper (H20) system there is no Grace-style cache coherence, so the device cannot dereference a plain host pointer → `cudaErrorIllegalAddress`.

## Questions

1. **How is dereferencing the host-side `ncclDevComm` pointer on the device intended to be legal?** Does the device API require a platform with unified/coherent addressing (Grace-Hopper coherence / HMM / ATS), or is the struct expected to be placed in device-accessible (pinned-mapped / managed / device) memory? Is `dev_comm.ptr` supposed to already be a device-dereferenceable address on supported platforms?

2. **Is the CuTeDSL example expected to work on a plain discrete x86 + H20 (Hopper) system at all**, or is it gated to coherent platforms (e.g. via `comm->symmetricSupport`)? If it's gated, what is the supported configuration for H20-class systems?

3. **If it relies on coherence / unified addressing, what is the performance overhead of reading `ncclDevComm` fields on the device?** Is the struct read once at kernel entry and cached in registers (one-time cost), or re-read on the hot path? What is the expected latency impact of the host-pointer-dereference design vs. passing `ncclDevComm` by value into the kernel?

Thanks in advance, looking forward to your reply!
