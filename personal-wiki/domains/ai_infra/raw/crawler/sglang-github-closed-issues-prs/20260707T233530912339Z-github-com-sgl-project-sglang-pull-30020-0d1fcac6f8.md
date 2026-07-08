---
source_id: sglang-github-closed-issues-prs
title: '[Not merge] Support CUDA 12.2 source builds'
canonical_url: https://github.com/sgl-project/sglang/pull/30020
captured_at: '2026-07-07T23:35:30.912339+00:00'
content_hash: 0d1fcac6f894f92abaa79c32739ca2ed0d62c351ea484520336ce58308dbffa2
---
# [Not merge] Support CUDA 12.2 source builds

URL: https://github.com/sgl-project/sglang/pull/30020
State: closed
Labels: quant, sgl-kernel, blackwell, npu, jit-kernel
Closed at: 2026-07-07T09:24:39Z
Merged at: 

## Summary

This draft PR makes current upstream `main` build and run from source in a CUDA 12.2 / older-driver environment without pinning SGLang back to an older tag or old dependency set.

The current patch is the pruned version of the earlier broader compatibility patch:

- 50 files changed total.
- 15 `sgl-kernel` files changed.
- Python changes are mostly lazy imports / compatibility guards so unavailable newer Torch, Triton, FlashInfer, or optional model dependencies are not imported on a standard Qwen serving path.
- `sgl-kernel` changes are limited to CUDA 12.2 source-build blockers and symbols needed for runtime dynamic loading.

## Minimality Notes

I separately removed and rebuilt the `sgl-kernel` changes that were not required for the CUDA 12.2 validation path. These files were dropped from the final PR diff because the AOT wheel build and runtime smoke still passed without changing them:

```text
sgl-kernel/csrc/allreduce/quick_all_reduce.cu
sgl-kernel/csrc/allreduce/quick_all_reduce.h
sgl-kernel/csrc/cutlass_extensions/epilogue/scaled_mm_epilogues_c3x.hpp
sgl-kernel/csrc/flashmla_extension.cc
```

One file was re-added after testing:

```text
sgl-kernel/csrc/kvcacheio/transfer.cu
```

Leaving that file unchanged allowed the wheel to build, but dynamic import failed with an unresolved `TensorBase::data_ptr<unsigned long>()` symbol in the CUDA 12.2 / torch 2.1 container. So it is kept in the minimal patch.

`flashmla_ops` and `spatial_ops` are intentionally skipped when building with CUDA < 12.4, because those paths require newer CUDA headers/toolchain support.

## Validation

Base upstream main SHA:

```text
d364cd8ead47086e9f83fc51cebc0cbe48d5ed9b
```

Head SHA:

```text
cf8ad0535c79b7e8c4920fd8f00d2c3ec0c51d99
```

Environment:

```text
GPU: H100
Image: nvcr.io/nvidia/pytorch:23.10-py3
Python: 3.10.12
Torch: 2.1.0a0+32f93b1
CUDA runtime: 12.2
Triton: 2.1.0
TORCH_CUDA_ARCH_LIST: 9.0
```

Local checks:

```bash
git diff --check origin/main
python3 -m py_compile \
  python/sglang/srt/utils/common.py \
  python/sglang/srt/layers/attention/torch_native_backend.py \
  python/sglang/srt/model_executor/model_runner.py \
  python/sglang/srt/layers/quantization/__init__.py
```

CUDA 12.2 AOT wheel build:

```bash
cd /tmp/sglang_cuda122_pruned_15/sgl-kernel
rm -rf build_cuda122_pruned_16 dist
TORCH_CUDA_ARCH_LIST="9.0" uv build --no-build-isolation --wheel -Cbuild-dir=build_cuda122_pruned_16
python3 -m pip install --force-reinstall --no-deps dist/sglang_kernel-0.4.4-cp310-abi3-linux_x86_64.whl
```

Build artifact:

```text
/tmp/sglang_cuda122_pruned_15/sgl-kernel/dist/sglang_kernel-0.4.4-cp310-abi3-linux_x86_64.whl
```

Runtime smokes passed in the CUDA 12.2 container:

- `sgl_kernel` import smoke.
- `sgl_per_token_quant_fp8` AOT kernel smoke.
- rmsnorm custom-op smoke.
- `sglang.srt.model_executor.model_runner.ModelRunner` import smoke.
- `sglang.srt.models.qwen2.Qwen2ForCausalLM` import smoke.

Qwen2.5-32B serving smoke passed:

```bash
CUDA_VISIBLE_DEVICES=GPU-7cea2752-34c7-f9c2-cd45-79163c61c398 \
PYTHONPATH=/tmp/sglang_cuda122_pruned_15/python \
python3 -m sglang.launch_server \
  --model-path /data/bbuf/.cache/huggingface/hub/models--Qwen--Qwen2.5-32B-Instruct/snapshots/5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd \
  --served-model-name Qwen/Qwen2.5-32B-Instruct \
  --host 127.0.0.1 \
  --port 31026 \
  --tp-size 1 \
  --dtype bfloat16 \
  --attention-backend torch_native \
  --sampling-backend pytorch \
  --grammar-backend none \
  --disable-cuda-graph \
  --disable-radix-cache \
  --trust-remote-code \
  --mem-fraction-static 0.82 \
  --context-length 2048
```

Observed:

```text
GET /model_info 200 OK
POST /v1/chat/completions 200 OK
```

The chat completion returned a normal Chinese response from `Qwen/Qwen2.5-32B-Instruct`.

## Known Limits

- The model serving validation used `torch_native` attention, `pytorch` sampling, `grammar-backend none`, and disabled CUDA graph to keep the CUDA 12.2 environment focused and reproducible.
- Some optional latest-main features still require newer CUDA/Torch/Triton/FlashInfer stacks. This PR guards or skips those paths instead of downgrading mainline dependencies.
- `flashmla_ops` and `spatial_ops` are not built under CUDA 12.2.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28646182238](https://github.com/sgl-project/sglang/actions/runs/28646182238)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28646182100](https://github.com/sgl-project/sglang/actions/runs/28646182100)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
