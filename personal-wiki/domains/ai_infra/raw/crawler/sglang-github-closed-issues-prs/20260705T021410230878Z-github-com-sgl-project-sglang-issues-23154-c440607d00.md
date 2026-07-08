---
source_id: sglang-github-closed-issues-prs
title: '[Bug]Retracted request + tokenizer_manager‘s recv_obj.input_top_logprobs_val=[None]'
canonical_url: https://github.com/sgl-project/sglang/issues/23154
captured_at: '2026-07-05T02:14:10.230878+00:00'
content_hash: c440607d00eeecab510a21e0361c4ea09245fb85cd221661e8ec85a3bb930cad
---
# [Bug]Retracted request + tokenizer_manager‘s recv_obj.input_top_logprobs_val=[None]

URL: https://github.com/sgl-project/sglang/issues/23154
State: closed
Labels: inactive
Closed at: 2026-07-05T00:41:33Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

**Retracted request + tokenizer_manager‘s recv_obj.input_top_logprobs_val=[None]**
When the KV cache is full, there is a certain probability that the following error will occur in the tokenizer_manager.

```
 TokenizerManager hit an exception: Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/sglang/srt/managers/tokenizer_manager.py", line 2449, in print_exception_wrapper
    await func()
  File "/usr/local/lib/python3.11/site-packages/sglang/srt/managers/tokenizer_manager.py", line 1472, in handle_loop
    self._result_dispatcher(recv_obj)
  File "/usr/local/lib/python3.11/site-packages/sglang/utils.py", line 573, in __call__
    return cached_fn(obj)
           ^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/sglang/srt/managers/tokenizer_manager.py", line 1515, in _handle_batch_output
    self.convert_logprob_style(
  File "/usr/local/lib/python3.11/site-packages/sglang/srt/managers/tokenizer_manager.py", line 1753, in convert_logprob_style
    state.input_top_logprobs_val.extend(
TypeError: 'NoneType' object is not iterable
```


### Reproduction

NCCL_DEBUG=INFO NCCL_IB_DISABLE=0 CUDA_VISIBLE_DEVICES=0,1  python -m sglang.launch_server --host 0.0.0.0   --tp-size 2 --trust-remote-code --model-path /mnt/tibox/jishen_v0331_v1_ck1334 --context-length 2560 --enable-multimodal --skip-server-warmup --mem-fraction-static 0.9 --max-running-requests 16 --chunked-prefill-size 12000 --max-prefill-tokens 12000 --tensor-parallel-size 2  --chat-template qwen2-vl --data-parallel-size 1 --attention-backend triton --disable-custom-all-reduce --log-level info

### Environment

Python: 3.11.11 (main, Aug 21 2025, 00:00:00) [GCC 11.5.0 20240719 (Red Hat 11.5.0-5)]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H800
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda-12.8
NVCC: Cuda compilation tools, release 12.8, V12.8.61
CUDA Driver Version: 535.261.03
PyTorch: 2.9.1+cu128
sglang: 0.5.9
sgl_kernel: 0.3.21
flashinfer_python: 0.6.3
flashinfer_cubin: 0.6.3
flashinfer_jit_cache: Module Not Found
triton: 3.5.1
transformers: 4.57.1
torchao: 0.9.0
numpy: 2.4.2
aiohttp: 3.13.3
fastapi: 0.133.1
hf_transfer: 0.1.9
huggingface_hub: 0.36.2
interegular: 0.3.3
modelscope: 1.34.0
orjson: 3.11.7
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.13.0b2
python-multipart: 0.0.22
pyzmq: 27.1.0
uvicorn: 0.41.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.27
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.84.0
litellm: Module Not Found
decord2: 3.0.0
