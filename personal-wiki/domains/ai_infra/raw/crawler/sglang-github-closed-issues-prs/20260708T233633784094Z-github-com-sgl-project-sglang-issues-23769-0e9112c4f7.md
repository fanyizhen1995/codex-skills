---
source_id: sglang-github-closed-issues-prs
title: '[Bug] DeepSeek-V4-Pro-FP8 official serving config OOM during CUDA Graph capture'
canonical_url: https://github.com/sgl-project/sglang/issues/23769
captured_at: '2026-07-08T23:36:33.784094+00:00'
content_hash: 0e9112c4f724f54cd479c693c4cf887411605a3b99e21ec453710ae440dfdcf8
---
# [Bug] DeepSeek-V4-Pro-FP8 official serving config OOM during CUDA Graph capture

URL: https://github.com/sgl-project/sglang/issues/23769
State: closed
Labels: inactive
Closed at: 2026-07-08T00:34:31Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug

## [Bug] DeepSeek-V4-Pro-FP8 OOM during CUDA Graph capture with official recommended config

### Description

When following the official recommended configuration to serve `DeepSeek-V4-Pro-FP8` on H200 GPUs (multi-node setup), the server consistently fails during CUDA Graph capture with an out-of-memory error.

This happens even with `--cuda-graph-max-bs 8`, which is already a relatively small batch size. The failure occurs before the server becomes usable.

### Reproduction Command

```bash
SGLANG_DSV4_FP4_EXPERTS=0 \
SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=128 \
SGLANG_JIT_DEEPGEMM_PRECOMPILE=0 \
sglang serve \
  --trust-remote-code \
  --model-path sgl-project/DeepSeek-V4-Pro-FP8 \
  --tp 16 \
  --dp 16 \
  --enable-dp-attention \
  --nnodes 2 \
  --node-rank <node-rank> \
  --dist-init-addr <node0-ip>:20000 \
  --moe-a2a-backend deepep \
  --cuda-graph-max-bs 8 \
  --max-running-requests 32 \
  --speculative-algo EAGLE \
  --speculative-num-steps 3 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 4 \
  --mem-fraction-static 0.88 \
  --host 0.0.0.0 \
  --port 30000
```

<img width="870" height="644" alt="Image" src="https://github.com/user-attachments/assets/0c77820c-424f-4ef3-b869-bc0e88fa8204" />

## Error log

<details>
<summary>Click to expand full log</summary>

```text
Exception: Capture cuda graph failed: CUDA out of memory.
Tried to allocate 672.00 MiB.

GPU 0 has a total capacity of 140.06 GiB of which 200.75 MiB is free.
Process 1939284 has 139.86 GiB memory in use.
Of the allocated memory 128.50 GiB is allocated by PyTorch,
with 3.23 GiB allocated in private pools (e.g., CUDA Graphs),
and 1.01 GiB is reserved by PyTorch but unallocated.

Possible solutions:
1. set --mem-fraction-static to a smaller value (e.g., 0.8 or 0.7)
2. set --cuda-graph-max-bs to a smaller value (e.g., 16)
3. disable torch compile by not using --enable-torch-compile
4. disable CUDA graph by --disable-cuda-graph. (Not recommended. Huge performance loss)

[2026-04-26 14:38:11] Rank 0 scheduler is dead. Please check if there are relevant logs.
[2026-04-26 14:38:11] Exit code: -3
```

</details>

## Environment

- GPU: NVIDIA H200, about 140 GB VRAM per GPU
- Number of GPUs: 16, 2 nodes × 8 GPUs
- Model: `sgl-project/DeepSeek-V4-Pro-FP8`
- TP: 16
- DP: 16
- CUDA Graph: enabled, `--cuda-graph-max-bs 8`
- Speculative decoding: EAGLE enabled
- `--mem-fraction-static`: 0.88

## Observations

- GPU memory is almost fully occupied before CUDA Graph capture.
- Only about 200 MB is free, but CUDA Graph capture tries to allocate another 672 MB.
- This suggests the official config leaves insufficient memory headroom for CUDA Graph private pools.

## Expected Behavior

The official recommended configuration should start successfully on 16× H200 GPUs.

## Actual Behavior

The server crashes during CUDA Graph capture and the scheduler exits with code `-3`.

## Questions

1. Is this official configuration expected to fit on 16× H200 GPUs?
2. Is `--mem-fraction-static 0.88` too aggressive for DeepSeek-V4-Pro-FP8 with EAGLE enabled?
3. Should the recommended config reduce `--mem-fraction-static`, `--cuda-graph-max-bs`, or `--max-running-requests`?
4. Is there a recommended H200-specific configuration?

### Reproduction

SGLANG_DSV4_FP4_EXPERTS=0 \
SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=128 \
SGLANG_JIT_DEEPGEMM_PRECOMPILE=0 \
sglang serve \
  --trust-remote-code \
  --model-path sgl-project/DeepSeek-V4-Pro-FP8 \
  --tp 16 \
  --dp 16 \
  --enable-dp-attention \
  --nnodes 2 \
  --node-rank <node-rank> \
  --dist-init-addr <node0-ip>:20000 \
  --moe-a2a-backend deepep \
  --cuda-graph-max-bs 8 \
  --max-running-requests 32 \
  --speculative-algo EAGLE \
  --speculative-num-steps 3 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 4 \
  --mem-fraction-static 0.88 \
  --host 0.0.0.0 \
  --port 30000

### Environment

GPU: NVIDIA H200, about 140 GB VRAM per GPU
Number of GPUs: 16, 2 nodes × 8 GPUs
Model: sgl-project/DeepSeek-V4-Pro-FP8
TP: 16
DP: 16
CUDA Graph: enabled, --cuda-graph-max-bs 8
Speculative decoding: EAGLE enabled
--mem-fraction-static: 0.88
