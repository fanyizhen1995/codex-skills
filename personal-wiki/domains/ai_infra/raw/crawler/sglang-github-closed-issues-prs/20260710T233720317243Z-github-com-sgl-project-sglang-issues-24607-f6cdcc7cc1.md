---
source_id: sglang-github-closed-issues-prs
title: '[Bug] MiMo-V2.5-Pro fails to load with TP=16 on 2 nodes with 8 Nvidia H200
  card in each: fused qkv_proj shard shape mismatch when tp_size > num_key_value_heads'
canonical_url: https://github.com/sgl-project/sglang/issues/24607
captured_at: '2026-07-10T23:37:20.317243+00:00'
content_hash: f6cdcc7cc14ff863ad05898fde2030416dea300d646f25f7a4147594ab20ae32
---
# [Bug] MiMo-V2.5-Pro fails to load with TP=16 on 2 nodes with 8 Nvidia H200 card in each: fused qkv_proj shard shape mismatch when tp_size > num_key_value_heads

URL: https://github.com/sgl-project/sglang/issues/24607
State: closed
Labels: inactive
Closed at: 2026-07-10T00:39:38Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

## Summary

We are trying to run `XiaomiMiMo/MiMo-V2.5-Pro` with SGLang on 2 nodes × 8 NVIDIA H200 GPUs, using `tp_size=16`.

The model fails during weight loading with a shape mismatch in `mimo_v2.py`:

```text
File "/sgl-workspace/sglang/python/sglang/srt/model_loader/loader.py", line 713, in load_weights_and_postprocess model.load_weights(weights) File "/sgl-workspace/sglang/python/sglang/srt/models/mimo_v2.py", line 1113, in load_weights default_weight_loader(param, loaded_weight) File "/sgl-workspace/sglang/python/sglang/srt/model_loader/weight_utils.py", line 1210, in default_weight_loader assert param.size() == loaded_weight.size(), ( ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

AssertionError: Attempted to load weight (torch.Size([1696, 6144])) into parameter (torch.Size([1856, 6144]))
```
## Launch command

```text
sglang serve \
  --trust-remote-code \
  --model-path /data/MiMo-V2.5-Pro \
  --served-model-name MiMo-V2.5-Pro \
  --tp 16 \
  --nnodes 2 \
  --node-rank <node-rank> \
  --dist-init-addr <node0-host>:29500 \
  --mem-fraction-static 0.7 \
  --max-running-requests 128 \
  --chunked-prefill-size 32768 \
  --cuda-graph-max-bs 64 \
  --page-size 64 \
  --swa-full-tokens-ratio 0.3 \
  --model-loader-extra-config '{"enable_multithread_load": "true", "num_threads": 64}' \
  --reasoning-parser mimo \
  --tool-call-parser mimo \
  --host 0.0.0.0 \
  --port 8080
```

## What happens

Distributed initialization succeeds:

```text
[Gloo] Rank 0 is connected to 15 peer ranks. Expected number of connected peer ranks is : 15
...
NCCL INFO ncclCommInitRank ... nranks 16 ... Init COMPLETE
...
Init torch distributed ends.
```
Then weight loading starts:
```text
Load weight begin. avail mem=138.09 GB
Detected fp8 checkpoint.
Skipping block quantization checks for weight partition.
```
After several minutes, one of the TP workers fails during model weight loading:
```text
File "/sgl-workspace/sglang/python/sglang/srt/models/mimo_v2.py", line 1113, in load_weights
    default_weight_loader(param, loaded_weight)

File "/sgl-workspace/sglang/python/sglang/srt/model_loader/weight_utils.py", line 1210, in default_weight_loader
    assert param.size() == loaded_weight.size(), (

AssertionError: Attempted to load weight (torch.Size([1696, 6144])) into parameter (torch.Size([1856, 6144]))
```
After that, the process exits:
```text
Received sigquit from a child process. It usually means the child failed.
```
## Relevant code path

The crash happens in the fused qkv_proj loading path:
```text
# Support fused qkv_proj checkpoint (Pro format)
if "qkv_proj" in name:
    if name in params_dict:
        tp_size = get_attention_tp_size()
        tp_rank = get_attention_tp_rank()
        param = params_dict[name]
        loaded_weight = loaded_weight.chunk(tp_size, dim=0)[tp_rank]
        default_weight_loader(param, loaded_weight)
    continue
```
This appears to split the whole fused qkv_proj checkpoint tensor directly by tp_size.

## Model config

The model config has:
```text
hidden_size = 6144
num_attention_heads = 128
num_key_value_heads = 8
head_dim = 192
v_head_dim = 128
```
The SWA config also uses 8 KV heads:
```text
swa_num_attention_heads = 128
swa_num_key_value_heads = 8
swa_head_dim = 192
swa_v_head_dim = 128
```
## Possible root cause
The model stores qkv_proj as one fused checkpoint tensor containing Q + K + V.

For this config, the global fused QKV size is:
```text
Q = 128 * 192 = 24576
K =   8 * 192 = 1536
V =   8 * 128 = 1024
QKV total = 27136
```
If the full fused QKV tensor is naively split by tp_size=16, each shard has:
```text
27136 / 16 = 1696
```
This matches the loaded weight shape from the error:
```text
torch.Size([1696, 6144])
```
However, since:
```text
tp_size = 16
num_key_value_heads = 8
```
The runtime QKVParallelLinear layout appears to expect KV heads to be handled differently, because KV heads cannot be evenly split across 16 TP ranks.

The expected local parameter shape appears to be:
```text
local Q = 24576 / 16 = 1536
local K = 1 * 192 = 192
local V = 1 * 128 = 128
local QKV = 1536 + 192 + 128 = 1856
```
This matches the parameter shape from the error:
```text
torch.Size([1856, 6144])
```
So the mismatch seems to be:
```text
loaded shard from naive fused qkv split: [1696, 6144]
runtime expected local qkv layout:       [1856, 6144]
```
This suggests that the current fused qkv_proj loader path may not correctly handle tp_size > num_key_value_heads.

A possible fix may be to avoid slicing the fused qkv_proj tensor as one matrix. Instead, the loader may need to:

split the checkpoint tensor into Q, K, and V;
load each part through the shard-aware QKV loader logic;
let the existing QKV loader handle KV replication/grouping when tp_size > num_key_value_heads.

## Additional notes
The same model can progress further when using tp=8, pp=2, which also supports the hypothesis that the failure is related to the tp_size=16 > num_key_value_heads=8 case.

### Reproduction

### Launch model with config below with tp size 16 on 16 H200 Cards: 

sglang serve \
  --trust-remote-code \
  --model-path /data/MiMo-V2.5-Pro \
  --served-model-name MiMo-V2.5-Pro \
  --tp 16 \
  --nnodes 2 \
  --node-rank <node-rank> \
  --dist-init-addr <node0-host>:29500 \
  --mem-fraction-static 0.7 \
  --max-running-requests 128 \
  --chunked-prefill-size 32768 \
  --cuda-graph-max-bs 64 \
  --page-size 64 \
  --swa-full-tokens-ratio 0.3 \
  --model-loader-extra-config '{"enable_multithread_load": "true", "num_threads": 64}' \
  --reasoning-parser mimo \
  --tool-call-parser mimo \
  --host 0.0.0.0 \
  --port 8080

### Environment

## Enviroment

### Hardware
2 nodes
8 × NVIDIA H200 per node
16 GPUs total
IB Net with GDRDMA enabled between 2 nodes (8 port 400Gbit/s per node)

### Runtime
**2 nodes with config:**
SGLang image: lmsysorg/sglang:dev-mimo-v2.5-pro
Python: 3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H200
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 580.105.08
PyTorch: 2.9.1+cu129
sglang: 0.0.0.dev1+gfb2e0b2ae
sglang-kernel: 0.4.1.post1
flashinfer_python: 0.6.8.post1
flashinfer_cubin: 0.6.8.post1
flashinfer_jit_cache: 0.6.8.post1+cu129
triton: 3.5.1
transformers: 5.6.0
torchao: 0.17.0+cu129
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.12.0
interegular: 0.3.3
modelscope: 1.36.2
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.3
python-multipart: 0.0.27
pyzmq: 27.1.0
uvicorn: 0.46.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.97.0
litellm: Module Not Found
torchcodec: 0.9.1
