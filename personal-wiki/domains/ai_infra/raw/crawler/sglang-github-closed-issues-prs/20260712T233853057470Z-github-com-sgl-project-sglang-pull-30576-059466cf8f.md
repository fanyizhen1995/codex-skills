---
source_id: sglang-github-closed-issues-prs
title: Fix ROCm/HIP silently attempting real CUDA-IPC reconstruction (#29687)
canonical_url: https://github.com/sgl-project/sglang/pull/30576
captured_at: '2026-07-12T23:38:53.057470+00:00'
content_hash: 059466cf8fcc4f58b9c65d299bda07dd60468ecc0c2339eb2644b776d89b53c2
---
# Fix ROCm/HIP silently attempting real CUDA-IPC reconstruction (#29687)

URL: https://github.com/sgl-project/sglang/pull/30576
State: closed
Labels: amd
Closed at: 2026-07-12T05:17:49Z
Merged at: 

Fixes #29687

# Fix ROCm/HIP silently attempting real CUDA-IPC reconstruction (#29687)

## The bug

PyTorch doesn't have a separate device type for HIP — ROCm tensors report
`tensor.is_cuda == True` and live on `torch.device("cuda:N")` just like real
CUDA tensors do. The multimodal CUDA-IPC transport
(`SGLANG_USE_CUDA_IPC_TRANSPORT=1`, opt-in, default off) was gating every
call site on either the raw env var or `tensor.is_cuda`, and neither of those
actually excludes ROCm. So on a ROCm build with this feature turned on, the
raw IPC handle reconstruction in
`CudaIpcTensorTransportProxy.reconstruct_on_target_device` gets attempted
anyway, and it crashes with `HIP error: invalid device pointer` — a
device-redirected IPC handle just isn't something HIP's IPC implementation
can reopen the same way real CUDA does it. That's exactly what's reported in
this issue (and the predecessor, #29227, which worked around it with an env
var rather than fixing the actual gate).

## What I did and why

The obvious quick fix is to wrap the two crash sites in an `is_hip()` check
and call it done. I didn't do that, for one reason: `MmItemMemoryPool`
already has a log line that says *"falling back to non-IPC transport"* when
the pool overflows — which means there's already a working, backend-agnostic
fallback path in this codebase (`reconstruct_on_target_device`'s
`tensor_data` branch, an ordinary `Tensor.to(device)` copy, no raw pointer
handles involved at all). A narrow `is_hip()` guard at the crash site would
have just turned a hardware crash into a Python exception — it wouldn't
actually make multimodal inference *work* on ROCm with this feature enabled.
That felt like the wrong bar to stop at.

So instead, I moved the gate to where the decision is actually made — the
producer side, in `base_processor.py`. I derived
`CUDA_IPC_TRANSPORT_SUPPORTED = SGL_USE_CUDA_IPC and not is_hip()` and swapped
every call site that would construct a `CudaIpcTensorTransportProxy` with a
real IPC handle attached (pool construction, the tensor-wrap helper, the
post-process step) over to that flag instead of the raw env var. On ROCm this
means the code never builds an IPC-bearing proxy in the first place — it just
falls through to the passthrough that's already there, already correct, and
already exercised on every platform. That's a real behavioral fix, not a
crash-to-error swap.

While tracing this I found `ernie45_vl.py` had its own copy of the same bug —
it re-derives the raw env var independently via its own `get_bool_env_var()`
call, with zero ROCm awareness, instead of importing the shared flag. Fixing
`base_processor.py` alone wouldn't have touched it. Updated it to import
`CUDA_IPC_TRANSPORT_SUPPORTED` from `base_processor.py` instead, so it can't
drift out of sync again. `moss_vl.py` had the same pattern and got the same
fix.

I also kept the `is_hip()` assertions at the two raw-reconstruction call
sites in `cuda_ipc_transport_utils.py`, on top of the producer-side fix — not
because I think they're reachable anymore (the producer-side gate should
make sure they never fire), but because if someone adds a new call site down
the line without going through that gate, I'd rather it die with a clear
Python assertion naming this issue than reproduce the original opaque HIP
crash for someone else to debug from scratch.

## Two smaller refactors, done for real reasons, not just to make tests pass

- Extracted the `CUDA_IPC_TRANSPORT_SUPPORTED` derivation into a small pure
  function, `_compute_cuda_ipc_transport_supported(use_ipc_env, is_hip_platform)`.
  It's a genuinely simpler thing to reason about and test as an isolated
  function of two booleans than as a module-level expression tangled up with
  import-time `is_hip()` calls.
- `reconstruct_on_target_device` had `torch.device(f"cuda:{idx}")` hardcoded
  inline in two places. Pulled that into `_cuda_device_for_index()` (one
  source of truth) and added a keyword-only `_rebuild_device_override`
  parameter to the method itself, defaulting to `None`. Every real caller is
  completely unaffected — they only ever pass the positional index, same as
  before. The reason for the seam: the `tensor_data` passthrough branch is
  the one part of this method that's genuinely backend-agnostic (it's just
  `.to(device)`), so it's the one branch that can honestly be tested against
  a real `torch.device("cpu")` without needing a GPU at all. I didn't want to
  prove that by monkeypatching `torch` itself inside the test — that tests
  the mock, not the code.

## Testing

Two new test files, 21 tests total, no GPU required:
- `test/registered/unit/multimodal/test_cuda_ipc_rocm_gate.py`
- `test/registered/unit/utils/test_cuda_ipc_transport_rocm_gate.py`

Coverage: the platform-gate derivation as a pure function over real booleans
(no mocking), the two `is_hip()` assertion guards firing correctly, and a
real (non-mocked) round-trip through the `tensor_data` passthrough that ROCm
now uses unconditionally. The existing `test/registered/unit/multimodal/`
suite (the pre-existing image-decode tests) still passes unchanged.

**What I couldn't verify, and want to be upfront about:** I don't have real
ROCm hardware to run this against. Everything here is verified by tracing the
actual code paths and testing the platform-gating logic directly, not by
reproducing the original `hipErrorInvalidDevicePointer` crash and confirming
it's gone. The raw CUDA-IPC branches themselves are untouched aside from the
extracted device-index helper, so the real-CUDA path should carry zero risk,
but I'd genuinely appreciate a sanity check from someone with an MI300-class
box before this merges.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28987303646](https://github.com/sgl-project/sglang/actions/runs/28987303646)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28987303490](https://github.com/sgl-project/sglang/actions/runs/28987303490)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
