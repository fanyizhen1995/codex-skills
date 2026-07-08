---
source_id: sglang-github-closed-issues-prs
title: '[Bug] TVM-FFI incorrectly detects ROCm on CUDA systems if /opt/rocm exists,
  causing JIT compilation to use hipcc instead of nvcc'
canonical_url: https://github.com/sgl-project/sglang/issues/30120
captured_at: '2026-07-05T02:14:10.233528+00:00'
content_hash: 26d535fa972aaae8f90747b5efe92bdde6411a4efdc1db4e58ecf6ac734a5ac9
---
# [Bug] TVM-FFI incorrectly detects ROCm on CUDA systems if /opt/rocm exists, causing JIT compilation to use hipcc instead of nvcc

URL: https://github.com/sgl-project/sglang/issues/30120
State: closed
Labels: 
Closed at: 2026-07-04T15:20:18Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

## Summary

On a CUDA-only system with an NVIDIA GPU, `tvm_ffi` incorrectly selects the ROCm backend if the `/opt/rocm` directory exists, even when:

* PyTorch is a CUDA build
* `torch.version.hip is None`
* `hipcc` is not installed
* `nvcc` is available

As a result, SGLang fails during JIT compilation because `build.ninja` invokes `/opt/rocm/bin/hipcc`.

---

## Reproduction

Start SGLang with an AWQ model that requires JIT kernel compilation, as given in command section.


During AWQ Marlin repacking, TVM-FFI generates a `build.ninja`.

The generated file contains:

```ninja
nvcc = /opt/rocm/bin/hipcc
```

and

```ninja
cuda_cflags = \
    -D__HIP_PLATFORM_AMD__=1 \
    --offload-arch=gfx1036
```

Compilation then fails because `hipcc` is not installed:

```bash
model.safetensors.index.json: 100%|██████| 82.3k/82.3k [00:00<00:00, 200MB/s]
Multi-thread loading shards: 100% Completed | 2/2 [00:00<00:00,  2.03it/s]
[2026-07-04 20:09:29] Scheduler hit an exception: Traceback (most recent call last):
  File "/sglang/sglang-src/python/sglang/srt/managers/scheduler.py", line 4211, in run_scheduler_process
    scheduler = Scheduler(
                ^^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/srt/managers/scheduler.py", line 436, in __init__
    self.init_model_worker()
  File "/sglang/sglang-src/python/sglang/srt/managers/scheduler.py", line 861, in init_model_worker
    self.init_tp_model_worker()
  File "/sglang/sglang-src/python/sglang/srt/managers/scheduler.py", line 782, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/srt/managers/tp_worker.py", line 269, in __init__
    self._init_model_runner()
  File "/sglang/sglang-src/python/sglang/srt/managers/tp_worker.py", line 378, in _init_model_runner
    self._model_runner = ModelRunner(
                         ^^^^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/srt/model_executor/model_runner.py", line 572, in __init__
    self.initialize()
  File "/sglang/sglang-src/python/sglang/srt/model_executor/model_runner.py", line 693, in initialize
    self.load_model()
  File "/sglang/sglang-src/python/sglang/srt/model_executor/model_runner.py", line 1423, in load_model
    self.model = self.loader.load_model(
                 ^^^^^^^^^^^^^^^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/srt/model_loader/loader.py", line 764, in load_model
    self.load_weights_and_postprocess(
  File "/sglang/sglang-src/python/sglang/srt/model_loader/loader.py", line 820, in load_weights_and_postprocess
    quant_method.process_weights_after_loading(module)
  File "/sglang/sglang-src/python/sglang/srt/layers/quantization/awq/awq.py", line 428, in process_weights_after_loading
    layer.scheme.process_weights_after_loading(layer)
  File "/sglang/sglang-src/python/sglang/srt/layers/quantization/awq/schemes/awq_marlin.py", line 104, in process_weights_after_loading
    self.kernel.process_weights_after_loading(layer)
  File "/sglang/sglang-src/python/sglang/srt/hardware_backend/gpu/quantization/awq_kernels.py", line 120, in process_weights_after_loading
    marlin_qweight = awq_marlin_repack(
                     ^^^^^^^^^^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/jit_kernel/awq_marlin_repack.py", line 37, in awq_marlin_repack
    module = _jit_awq_marlin_repack_module()
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/jit_kernel/utils.py", line 59, in wrapper
    result_map[key] = fn(*args, **kwargs)
                      ^^^^^^^^^^^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/jit_kernel/awq_marlin_repack.py", line 16, in _jit_awq_marlin_repack_module
    return load_jit(
           ^^^^^^^^^
  File "/sglang/sglang-src/python/sglang/jit_kernel/utils.py", line 307, in load_jit
    return load_inline(
           ^^^^^^^^^^^^
  File "/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/cpp/extension.py", line 1035, in load_inline
    build_inline(
  File "/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/cpp/extension.py", line 877, in build_inline
    return _build_impl(
           ^^^^^^^^^^^^
  File "/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/cpp/extension.py", line 672, in _build_impl
    build_ninja(str(build_dir))
  File "/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/cpp/extension.py", line 542, in build_ninja
    raise RuntimeError("\n".join(msg))
RuntimeError: ninja exited with status 127
stdout:
[1/2] /opt/rocm/bin/hipcc -std=c++17 -O2 -fPIC -D__HIP_PLATFORM_AMD__=1 -fno-gpu-rdc --offload-arch=gfx1036 -DSGL_CUDA_ARCH=1200 -std=c++20 -O3 --expt-relaxed-constexpr -I/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/include -I/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/include -I/opt/rocm/include -I/sglang/sglang-src/python/sglang/jit_kernel/include -c ~/.cache/tvm-ffi/sgl_kernel_jit_awq_marlin_repack_1c86fcd698c4eb1b__arch_12.0__tvmffi_0.1.9/cuda.cu -o cuda_0.o
FAILED: [code=127] cuda_0.o 
/opt/rocm/bin/hipcc -std=c++17 -O2 -fPIC -D__HIP_PLATFORM_AMD__=1 -fno-gpu-rdc --offload-arch=gfx1036 -DSGL_CUDA_ARCH=1200 -std=c++20 -O3 --expt-relaxed-constexpr -I/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/include -I/sglang/sglang-env/lib/python3.11/site-packages/tvm_ffi/include -I/opt/rocm/include -I/sglang/sglang-src/python/sglang/jit_kernel/include -c ~/.cache/tvm-ffi/sgl_kernel_jit_awq_marlin_repack_1c86fcd698c4eb1b__arch_12.0__tvmffi_0.1.9/cuda.cu -o cuda_0.o
/bin/sh: line 1: /opt/rocm/bin/hipcc: No such file or directory
ninja: build stopped: subcommand failed.


[2026-07-04 20:09:29] Received sigquit from a child process. It usually means the child failed.

[2026-07-04 20:09:29] kill_process_tree called: parent_pid=13293, include_parent=True, pid=13293
./serve.sh: line 33: 13293 Killed                     sglang serve --model-path Qwen/Qwen3-14B-AWQ --json-model-override-args '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}' --reasoning-parser qwen3 --tool-call-parser qwen3_coder --quantization awq_marlin --dtype float16 --host 127.0.0.1 --port 8000 --attention-backend flashinfer --context-length 40960 --kv-cache-dtype fp8_e5m2 --max-running-requests 12 --chunked-prefill-size 1024 --cuda-graph-max-bs-decode 32 --tp-size 1 --mem-fraction-static 0.94
```

---


## Expected behavior

Backend detection should select CUDA when:

* `torch.version.cuda is not None`, or
* `torch.version.hip is None`, or
* `hipcc` is not available.

The mere existence of `/opt/rocm` should not force the HIP backend.

---

### Reproduction

sglang serve --model-path Qwen/Qwen3-14B-AWQ --json-model-override-args '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}' --reasoning-parser qwen3 --tool-call-parser qwen3_coder --quantization awq_marlin --dtype float16 --host 127.0.0.1 --port 8000 --attention-backend flashinfer --context-length 40960 --kv-cache-dtype fp8_e5m2 --max-running-requests 12 --chunked-prefill-size 1024 --cuda-graph-max-bs-decode 32 --tp-size 1 --mem-fraction-static 0.94

### Environment

## Environment

* OS: EndeavourOS (Arch Linux)
* GPU: NVIDIA GeForce RTX 5080 (Blackwell)
* CUDA: 13.0
* PyTorch: 2.11.0+cu130
* SGLang: v0.5.14
* apache-tvm-ffi: 0.1.9

Python reports:

```python
>>> import torch
>>> torch.version.cuda
'13.0'

>>> torch.version.hip
None

>>> torch.cuda.is_available()
True
```

Compiler availability:

```bash
$ which nvcc
/opt/cuda/bin/nvcc

$ which hipcc
# not found
```

Environment variables:

```text
CUDA_HOME=
ROCM_HOME=
HIP_PATH=
HIP_PLATFORM=
TVM_FFI_USE_CUDA=
TVM_FFI_USE_ROCM=
```

All unset.

---
