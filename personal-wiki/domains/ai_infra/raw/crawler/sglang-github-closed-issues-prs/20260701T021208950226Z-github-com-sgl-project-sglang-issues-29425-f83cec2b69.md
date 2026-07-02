---
source_id: sglang-github-closed-issues-prs
title: '[Bug] CUDA 12 installation instructions pull in CUDA 13 packages'
canonical_url: https://github.com/sgl-project/sglang/issues/29425
captured_at: '2026-07-01T02:12:08.950226+00:00'
content_hash: f83cec2b696c2ef270be85e320a11a20c86ebe9b8f0ea47a459d947c1155bd27
---
# [Bug] CUDA 12 installation instructions pull in CUDA 13 packages

URL: https://github.com/sgl-project/sglang/issues/29425
State: closed
Labels: 
Closed at: 2026-06-30T05:04:28Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Following the CUDA 12 installation guide from the official documentation does not result in a working SGLang installation on a clean environment.

While trying to install SGLang, I noticed that the CUDA 12 installation instructions eventually pull in a large number of CUDA 13 packages, for example:

```
cuda-python                  13.3.1
flashinfer-jit-cache         0.6.13+cu129
nvidia-cublas                13.1.0.3
nvidia-cuda-crt              13.3.33
nvidia-cuda-cupti            13.0.85
nvidia-cuda-nvcc             13.2.78
nvidia-cuda-nvrtc            13.0.88
nvidia-cuda-runtime          13.0.96
nvidia-cuda-tileiras         13.2.78
nvidia-cudnn-cu13            9.19.0.56
nvidia-cusparselt-cu13       0.8.0
nvidia-cutlass-dsl-libs-cu13 4.5.2
nvidia-nccl-cu13             2.28.9
nvidia-nvjitlink             13.0.88
nvidia-nvshmem-cu13          3.4.5
nvidia-nvtx                  13.0.85
nvidia-nvvm                  13.2.78
```

As a result, the environment contains a mixture of CUDA 12 and CUDA 13 components, which eventually leads to installation/runtime issues.

Could you provide a complete, officially recommended installation command (or installation script) for a clean CUDA 12 environment, including all required dependencies and version constraints, so that users can install SGLang without pulling in incompatible CUDA 13 packages?

Additional context

If needed, I can provide the complete installation logs and error messages.

### Reproduction

```
pip install --upgrade pip
pip install uv
uv pip install sglang
uv pip install --force-reinstall  torch==2.11.0 torchaudio==2.11.0 torchvision --index-url https://download.pytorch.org/whl/cu129
uv pip install --force-reinstall sglang-kernel --index-url https://docs.sglang.ai/whl/cu129/
uv pip install --force-reinstall sgl-deep-gemm --index-url https://docs.sglang.ai/whl/cu129/ --no-deps
```

### Environment

* OS: Ubuntu 24.04
* CUDA: 12.x
* Python: 3.10
* SGLang version: Latest
* Installation method: pip
* GPU: H20
