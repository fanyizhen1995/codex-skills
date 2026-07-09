---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Llama model crashes with `CUDA Error: cudaErrorMisalignedAddress`'
canonical_url: https://github.com/sgl-project/sglang/issues/24714
captured_at: '2026-07-08T23:36:33.783073+00:00'
content_hash: c9b78c1ddd35316668fec1ae5dfa788601ee4759deec112806316b26864db3f7
---
# [Bug] Llama model crashes with `CUDA Error: cudaErrorMisalignedAddress`

URL: https://github.com/sgl-project/sglang/issues/24714
State: closed
Labels: inactive
Closed at: 2026-07-08T00:34:35Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When attempting to load [this](https://huggingface.co/inferno-project/sglang-llama-1/tree/main) Llama model, CUDA graph capture fails with the following error:

```
Exception: Capture cuda graph failed: Error in function 'VariableLengthMergeStates' at /home/jlj/dev/inferno/.venv/lib/python3.12/site-packages/flashinfer/data/include/flashinfer/attention/cascade.cuh:697: Unsupported head_dim: 106
Possible solutions:
1. set --mem-fraction-static to a smaller value (e.g., 0.8 or 0.7)
2. set --cuda-graph-max-bs to a smaller value (e.g., 16)
3. disable torch compile by not using --enable-torch-compile
4. disable CUDA graph by --disable-cuda-graph. (Not recommended. Huge performance loss)
Open an issue on GitHub https://github.com/sgl-project/sglang/issues/new/choose 
```

Full traceback: [traceback.log](https://github.com/user-attachments/files/27533170/traceback.log)

As suggested in the error above, I tried disabling CUDA graph with `disable_cuda_graph=True`, which caused the crash to instead presents with the following error: `Piecewise CUDA Graph failed with error: CUDA Error: cudaErrorMisalignedAddress`.

Full traceback: [misaligned_traceback.log](https://github.com/user-attachments/files/27533226/misaligned_traceback.log)

### Reproduction

```python3
import sglang    

llm = sglang.Engine(
    model_path="inferno-project/sglang-llama-1",
    # Presents differently when disable_cuda_graph is True
    # disable_cuda_graph=True,
)

sampling_params = {"temperature": 0}

engine.generate(["token_0"], sampling_params=sampling_params)
```

### Environment

```text
Python: 3.12.11 (main, Sep  2 2025, 14:20:58) [Clang 20.1.4 ]
CUDA available: True
GPU 0: NVIDIA GeForce RTX 4060 Laptop GPU
GPU 0 Compute Capability: 8.9
CUDA_HOME: /usr/local/cuda-12.9
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 590.48.01
PyTorch: 2.11.0+cu130
sglang: 0.5.11
sglang-kernel: 0.4.2+cu130
flashinfer_python: 0.6.8.post1
flashinfer_cubin: 0.6.8.post1
flashinfer_jit_cache: Module Not Found
triton: 3.6.0
transformers: 5.8.0
torchao: 0.17.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.14.0
interegular: 0.3.3
modelscope: 1.36.3
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.27
pyzmq: 27.1.0
uvicorn: 0.46.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.100.0
litellm: Module Not Found
torchcodec: 0.11.1
NVIDIA Topology: 
        GPU0    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      0-21    0               N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

ulimit soft: 524288
```
