---
source_id: sglang-github-closed-issues-prs
title: '[Bug] v0.5.15-cu129 Docker image is missing nvidia-cutlass-dsl, causing Qwen3.6
  EAGLE startup failure'
canonical_url: https://github.com/sgl-project/sglang/issues/30856
captured_at: '2026-07-12T23:38:53.044772+00:00'
content_hash: 3708fce29509eeaed4183b8b82c7b13b15c2b4ad79031561ac4872cb9a38a3bd
---
# [Bug] v0.5.15-cu129 Docker image is missing nvidia-cutlass-dsl, causing Qwen3.6 EAGLE startup failure

URL: https://github.com/sgl-project/sglang/issues/30856
State: closed
Labels: 
Closed at: 2026-07-12T20:50:42Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

The official Docker image `lmsysorg/sglang:v0.5.15-cu129` does not include the Python `cutlass` module.

When launching `Qwen3.6-27B-FP8` with EAGLE speculative decoding, the server fails during draft CUDA graph initialization:

```text
ModuleNotFoundError: No module named 'cutlass'
```

The failing import path is:

```text
eagle_worker_v2.py
  -> dsa_backend.py
  -> dsa_indexer.py
  -> sglang.jit_kernel.dsa
  -> cutedsl_paged_mqa_logits.py
  -> import cutlass
```

Installing the following packages allows the server to start successfully:

```bash
python3 -m pip install \
  --no-deps \
  nvidia-cutlass-dsl-libs-base==4.5.2 \
  nvidia-cutlass-dsl==4.5.2
```

### Expected behavior

The official CUDA 12.9 Docker image should include the dependencies required to launch supported EAGLE configurations without installing additional packages at container startup.





### Reproduction


Verify that `cutlass` is missing from the official image:

```bash
docker run --rm \
  lmsysorg/sglang:v0.5.15-cu129 \
  python3 -c "import cutlass"
```

Output:

```text
==========
== CUDA ==
==========

CUDA Version 12.9.1

Container image Copyright (c) 2016-2023, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

This container image and its contents are governed by the NVIDIA Deep Learning Container License.
By pulling and using the container, you accept the terms and conditions of this license:
https://developer.nvidia.com/ngc/nvidia-deep-learning-container-license

A copy of this license is made available in this container at /NGC-DL-CONTAINER-LICENSE for your convenience.

WARNING: The NVIDIA Driver was not detected.  GPU functionality will not be available.
   Use the NVIDIA Container Toolkit to start this container with GPU support; see
   https://docs.nvidia.com/datacenter/cloud-native/ .

Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'cutlass'
```

Launch the model with EAGLE:

```bash
docker run --rm \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /ai/llm_models:/models:ro \
  lmsysorg/sglang:v0.5.15-cu129 \
  sglang serve \
    --model-path /models/Qwen/Qwen3.6-27B-FP8 \
    --tp-size 1 \
    --context-length 65536 \
    --mem-fraction-static 0.92 \
    --max-running-requests 4 \
    --cuda-graph-max-bs-decode 4 \
    --speculative-algo EAGLE \
    --speculative-num-steps 3 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 4
```

Relevant traceback:

```text
[2026-07-11 04:14:06] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4313, in run_scheduler_process
    scheduler = Scheduler(
                ^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 423, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 874, in init_model_worker
    self.init_all_cuda_graphs()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 862, in init_all_cuda_graphs
    self.draft_worker.init_cuda_graphs()
  File "/sgl-workspace/sglang/python/sglang/srt/speculative/eagle_worker_v2.py", line 1130, in init_cuda_graphs
    self._draft_worker.init_cuda_graphs()
  File "/sgl-workspace/sglang/python/sglang/srt/speculative/eagle_worker_v2.py", line 256, in init_cuda_graphs
    self._capture_cuda_graphs()
  File "/sgl-workspace/sglang/python/sglang/srt/speculative/eagle_worker_v2.py", line 462, in _capture_cuda_graphs
    from sglang.srt.layers.attention.dsa_backend import (
  File "/sgl-workspace/sglang/python/sglang/srt/layers/attention/dsa_backend.py", line 29, in <module>
    from sglang.srt.layers.attention.dsa.dsa_indexer import BaseIndexerMetadata
  File "/sgl-workspace/sglang/python/sglang/srt/layers/attention/dsa/dsa_indexer.py", line 11, in <module>
    from sglang.jit_kernel.dsa import (
  File "/sgl-workspace/sglang/python/sglang/jit_kernel/dsa/__init__.py", line 12, in <module>
    from .cutedsl_paged_mqa_logits import CuteDSLPagedMQALogitsRunner, pick_dsl_expand
  File "/sgl-workspace/sglang/python/sglang/jit_kernel/dsa/cutedsl_paged_mqa_logits.py", line 15, in <module>
    import cutlass
ModuleNotFoundError: No module named 'cutlass'
```

### Environment

* Image: `lmsysorg/sglang:v0.5.15-cu129`
* Image digest: `sha256:cf821c60ddc04db0e0c7f92b3612a344a08f78136968a40122eb5ba67bb69910`
* GPU: NVIDIA L20 48 GB
* NVIDIA driver: `550.163.01`
* Compute capability: `8.9`
* Host OS: Ubuntu 22.04
* Model: `Qwen3.6-27B-FP8`
* Tensor parallel size: `1`
* Speculative decoding: EAGLE
