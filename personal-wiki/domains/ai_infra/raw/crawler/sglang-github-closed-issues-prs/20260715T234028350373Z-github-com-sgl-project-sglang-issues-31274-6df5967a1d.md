---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Gemma-4 with modelopt_fp4: tuple index out of range'
canonical_url: https://github.com/sgl-project/sglang/issues/31274
captured_at: '2026-07-15T23:40:28.350373+00:00'
content_hash: 6df5967a1dd8c858e30262322a07eae9a360836ed422882736bca1b9d1830dfb
---
# [Bug] Gemma-4 with modelopt_fp4: tuple index out of range

URL: https://github.com/sgl-project/sglang/issues/31274
State: closed
Labels: 
Closed at: 2026-07-15T04:35:31Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

- Specifying the `--quantization modelopt_fp4` argument with `gemma-4-26B-A4B-it` results in the following error.
- It runs successfully if the argument is not specified.
```
[2026-07-15 04:07:05] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4325, in run_scheduler_process
    scheduler = Scheduler(
                ^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 424, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 875, in init_model_worker
    self.init_all_cuda_graphs()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 861, in init_all_cuda_graphs
    self.tp_worker.init_cuda_graphs()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 357, in init_cuda_graphs
    self.model_runner.init_cuda_graphs(
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 938, in init_cuda_graphs
    self.eager_runner = EagerRunner(self)
                        ^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/runner/eager_runner.py", line 139, in __init__
    self.warmup()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/runner/base_runner.py", line 222, in warmup
    self._flashinfer_autotune(buffers=buffers, batch_size=batch_size)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/runner/base_runner.py", line 266, in _flashinfer_autotune
    run_flashinfer_autotune_forward(self.model_runner, forward_fn, skip_logits=True)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/runner/flashinfer_autotune.py", line 192, in run_flashinfer_autotune_forward
    forward_fn()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/runner/base_runner.py", line 264, in forward_fn
    self._dummy_run(batch_size=batch_size, buffers=buffers)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/runner/base_runner.py", line 566, in _dummy_run
    run_once()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/runner/base_runner.py", line 554, in run_once
    logits_output_or_pp_proxy_tensors = mr.model.forward(
                                        ^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/utils/generic.py", line 903, in wrapper
    output = func(self, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/models/gemma4/modeling_gemma4.py", line 2482, in forward
    outputs = self.model(
              ^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/utils/generic.py", line 1032, in wrapper
    output = func(self, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/utils/generic.py", line 903, in wrapper
    output = func(self, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/models/gemma4/modeling_gemma4.py", line 2251, in forward
    image_features = self.get_image_features(pixel_values, image_position_ids, return_dict=True).pooler_output
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/utils/generic.py", line 903, in wrapper
    output = func(self, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/models/gemma4/modeling_gemma4.py", line 2136, in get_image_features
    vision_outputs = self.vision_tower(
                     ^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/utils/generic.py", line 1032, in wrapper
    output = func(self, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/utils/output_capturing.py", line 252, in wrapper
    outputs = func(self, *args, **kwargs)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/dist-packages/transformers/models/gemma4/modeling_gemma4.py", line 2027, in forward
    output_length = pixel_values.shape[-2] // (pooling_kernel_size * pooling_kernel_size)
                    ~~~~~~~~~~~~~~~~~~^^^^
IndexError: tuple index out of range

[2026-07-15 04:07:05] Received sigquit from a child process. It usually means the child failed.
[2026-07-15 04:07:05] kill_process_tree called: parent_pid=1457, include_parent=True, pid=1457
```

### Reproduction

```
# docker run --rm --gpus all --ipc=host --shm-size 32g --ulimit memlock=-1 --ulimit stack=67108864 --ulimit nofile=65536:65536 --cap-add CAP_SYS_PTRACE --name sglang -p 30000:30000 -v sglang:/root/.cache -it lmsysorg/sglang:v0.5.15.post1-cu130 bash
# pip install accelerate
# sglang serve --model-path google/gemma-4-26B-A4B-it-qat-q4_0-unquantized --reasoning-parser gemma4 --tool-call-parser gemma4 --quantization modelopt_fp4 --kv-cache-dtype fp8_e4m3 --attention-backend triton --mem-fraction-static 0.9 --host 0.0.0.0 --port 30000
```

### Environment

```
Python: 3.12.3 (main, Jun 19 2026, 12:46:00) [GCC 13.3.0]
CUDA available: True
GPU 0: NVIDIA GB10
GPU 0 Compute Capability: 12.1
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 13.0, V13.0.88
CUDA Driver Version: 580.159.03
PyTorch: 2.11.0+cu130
sglang: 0.5.15.post1
sglang-kernel: 0.4.4
flashinfer_python: 0.6.12
flashinfer_cubin: 0.6.12
flashinfer_jit_cache: 0.6.12+cu130
triton: 3.6.0
transformers: 5.9.0
torchao: 0.17.0
numpy: 2.3.5
aiohttp: 3.14.1
fastapi: 0.139.0
huggingface_hub: 1.23.0
interegular: 0.3.3
modelscope: 1.38.1
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.32
pyzmq: 27.1.0
uvicorn: 0.51.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.1
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.116.0
litellm: Module Not Found
torchcodec: Module Not Found
NVIDIA Topology:
        GPU0    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      0-19    0               N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

ulimit soft: 65536
```
