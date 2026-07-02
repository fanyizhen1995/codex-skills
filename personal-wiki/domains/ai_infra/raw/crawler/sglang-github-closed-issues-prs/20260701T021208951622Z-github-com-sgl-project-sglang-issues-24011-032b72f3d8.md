---
source_id: sglang-github-closed-issues-prs
title: '[Bug] qwen3-235b-mxfp4 nightly CI on MI35x crashes with hipErrorCapturedEvent
  during CUDA Graph capture (ROCm 7.2.0 HIP runtime bug)'
canonical_url: https://github.com/sgl-project/sglang/issues/24011
captured_at: '2026-07-01T02:12:08.951622+00:00'
content_hash: 032b72f3d842b50ee0b9035124709b218f40c9aa75d9759a15c4e632261908a9
---
# [Bug] qwen3-235b-mxfp4 nightly CI on MI35x crashes with hipErrorCapturedEvent during CUDA Graph capture (ROCm 7.2.0 HIP runtime bug)

URL: https://github.com/sgl-project/sglang/issues/24011
State: closed
Labels: inactive
Closed at: 2026-06-30T00:48:46Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

The `nightly-8-gpu-mi35x-qwen3-235b-mxfp4` CI job has been failing on the rocm720 image. The root cause is a HIP runtime bug in **ROCm ≤ 7.2.0**, not in sglang or aiter. The fix is a base-image bump to ROCm 7.2.2, which is already in flight as **#21839**. Filing this so the failure has a citable record and to surface the broader latent risk.

**Symptom**

During CUDA Graph capture inside `AiterCustomAllreduce.flush_graph_buffers`:

```
Process group watchdog thread terminated with exception:
HIP error: operation not permitted on an event last recorded in a capturing stream
→ scheduler aborts (SIGABRT, exit code -6)
```

Reproduces deterministically on `Qwen3-235B-A22B-Instruct-2507-MXFP4` with `--tp 4 --ep 2` during the first warmup forward pass on the rocm720 base image (ROCm 7.2.0).

**Root cause (short version)**

1. PyTorch's NCCL watchdog runs on a background thread and calls `hipEventQuery` to detect collective hangs. Before each query it sets `cudaStreamCaptureModeThreadLocal` so it shouldn't disturb the main thread's active CUDA Graph capture.
2. **ROCm ≤ 7.2.0 silently ignores `THREAD_LOCAL`**. The HIP runtime treats the cross-thread query as if it were on the capturing thread itself: it fails the watchdog's query AND — the destructive part — **marks the main thread's capture state as `INVALIDATED`** (cross-thread invalidation).
3. When the main thread later calls `cudaStreamEndCapture`, it sees `INVALIDATED` and aborts the whole process.

Why now (and only on Qwen3-235B-MXFP4): aiter v0.1.12.post1 widened the host-busy time inside the active capture window (TCPStore-based IPC handshake instead of gloo broadcast, 2N IPC bookkeeping per allreduce for input + output buffers, 1 GB `max_size`). The combination of (a) Qwen3-235B's ~150 allreduces × 52 captured batch sizes worth of host-side IPC bookkeeping, and (b) `--tp 4 --ep 2` running 3-4 NCCL-bearing process groups (TP/MoE_EP/MoE_TP/WORLD), each with its own watchdog poller, is enough to push the race from "occasionally fires" to "deterministic crash". It's the only CI workload combining heavy AR + multiple NCCL-bearing PGs.

> **Important**: this race is a *latent risk for any future model* with sufficiently long capture windows on ROCm ≤ 7.2.0 — Qwen3-235B-MXFP4 just happens to be the first to hit it deterministically in CI. The runtime upgrade isn't just a CI fix, it removes a class of crashes.

Upstream context:
- [pytorch/pytorch#177309](https://github.com/pytorch/pytorch/issues/177309) — HIP runtime bug
- [pytorch/pytorch#176251](https://github.com/pytorch/pytorch/pull/176251) — earlier PyTorch-side workaround (merged twice, reverted twice)
- [pytorch/pytorch#179780](https://github.com/pytorch/pytorch/pull/179780) — version guard

**Fix**

**Bump the rocm720 base image to ROCm 7.2.2.** ROCm 7.2.1+ correctly honors `THREAD_LOCAL` capture mode, so cross-thread `hipEventQuery` no longer touches the main thread's capture state.

This is exactly what **#21839** does (current head, after the 6e4b960 update):

```dockerfile
- ARG BASE_IMAGE_950_ROCM720="rocm/pytorch:rocm7.2_ubuntu22.04_py3.10_pytorch_release_2.9.1"
+ ARG BASE_IMAGE_950_ROCM720="rocm/pytorch:rocm7.2.2_ubuntu22.04_py3.10_pytorch_release_2.9.1"
```

Verified locally on MI35x with this single base-image bump:
- Server boots successfully
- All 52/52 captured batch sizes complete cleanly
- Qwen3-235B-MXFP4 `--tp 4 --ep 2` inference works end-to-end

torch 2.9.1 ABI is unchanged, so `aiter` / `sgl-kernel` / `fast-hadamard` / `triton-custom` extensions do not need to be rebuilt.

**Why sglang-side / aiter-side workarounds aren't enough**

I attempted partial mitigations on the aiter side (reverting v0.1.12's TCPStore handshake to v0.1.11's gloo broadcast, i.e. shrinking the capture-exit flush phase). **The race still fires**, only earlier — typically inside `forward_pass` instead of `flush_graph_buffers`. The race window is the **entire active capture state**, not just the flush phase. CA-bearing PGs cannot be eliminated either (TP needs CustomAllreduce). The runtime is the only viable fix point.

### Reproduction

Failing CI run: https://github.com/sgl-project/sglang/actions/runs/24737667212/job/72454269669

Workflow: `.github/workflows/nightly-test-amd-rocm720.yml` → job `nightly-8-gpu-mi35x-qwen3-235b-mxfp4`.

Docker image: `rocm/sgl-dev:v0.5.10.post1-rocm720-mi35x-20260426` (the rocm720 nightly build, currently based on `rocm/pytorch:rocm7.2_ubuntu22.04_py3.10_pytorch_release_2.9.1`, i.e. ROCm 7.2.0).

Model: `Qwen3-235B-A22B-Instruct-2507-MXFP4` with `--tp 4 --ep 2` on 8× MI35x.

### Environment

```
Python: 3.10.12 (main, Jan  8 2026, 06:52:19) [GCC 11.4.0]
ROCM available: True
GPU 0,1,2,3,4,5,6,7: AMD Instinct MI355X
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.5
ROCM_HOME: /opt/rocm-7.2.0
HIPCC: HIP version: 7.2.26015-fc0010cf6a
ROCM Driver Version: 6.16.13
PyTorch: 2.9.1+rocm7.2.0.git7e1940d4
sglang: 0.5.10.post1.dev20260426+gc7878dbb6
sglang-kernel: 0.4.1.post1
flashinfer_python: Module Not Found
flashinfer_cubin: Module Not Found
flashinfer_jit_cache: Module Not Found
triton: 3.6.0+git42270451
transformers: 5.5.4
torchao: 0.9.0
numpy: 2.2.6
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.12.0
interegular: 0.3.3
modelscope: 1.36.2
orjson: 3.11.8
outlines: 0.1.11
packaging: 25.0
psutil: 7.2.2
pydantic: 2.13.3
python-multipart: 0.0.26
pyzmq: 27.1.0
uvicorn: 0.46.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.97.0
litellm: Module Not Found
torchcodec: Module Not Found
AMD Topology:


============================ ROCm System Management Interface ============================
=============================== Link Type between two GPUs ===============================
       GPU0         GPU1         GPU2         GPU3         GPU4         GPU5         GPU6         GPU7
GPU0   0            XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         XGMI
GPU1   XGMI         0            XGMI         XGMI         XGMI         XGMI         XGMI         XGMI
GPU2   XGMI         XGMI         0            XGMI         XGMI         XGMI         XGMI         XGMI
GPU3   XGMI         XGMI         XGMI         0            XGMI         XGMI         XGMI         XGMI
GPU4   XGMI         XGMI         XGMI         XGMI         0            XGMI         XGMI         XGMI
GPU5   XGMI         XGMI         XGMI         XGMI         XGMI         0            XGMI         XGMI
GPU6   XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         0            XGMI
GPU7   XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         XGMI         0
================================== End of ROCm SMI Log ===================================

ulimit soft: 1024
```

Key fields confirming the failure mode:
- `ROCM_HOME: /opt/rocm-7.2.0` — affected version
- `PyTorch: 2.9.1+rocm7.2.0.git7e1940d4` — built against ROCm 7.2.0
- `GPU: AMD Instinct MI355X` (gfx950) — MI35x family
- `sglang: 0.5.10.post1.dev20260426+gc7878dbb6` — recent main, post-aiter-v0.1.12 bump
