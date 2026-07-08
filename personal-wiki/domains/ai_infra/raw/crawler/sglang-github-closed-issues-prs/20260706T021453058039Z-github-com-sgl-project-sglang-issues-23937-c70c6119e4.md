---
source_id: sglang-github-closed-issues-prs
title: '[Bug] KV cache transfer metrics use wrong time window, reporting much slower
  speed than actual'
canonical_url: https://github.com/sgl-project/sglang/issues/23937
captured_at: '2026-07-06T02:14:53.058039+00:00'
content_hash: c70c6119e459414e516c75bd9eee5dd5c18ce0539497514cdb5b6d1eb3e565d2
---
# [Bug] KV cache transfer metrics use wrong time window, reporting much slower speed than actual

URL: https://github.com/sgl-project/sglang/issues/23937
State: closed
Labels: inactive
Closed at: 2026-07-06T00:41:17Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

The current computation of KV cache transfer metrics in `SchedulerReqTimeStats.compute_and_observe_kv_transfer_metrics` is inaccurate. The field `transfer_latency_s` is computed as `self.completion_time - self.prefill_transfer_queue_entry_time`. However, `self.completion_time` marks the request's completion (after decoding), not the end of the prefill KV cache transfer. Therefore, the reported KV cache transfer time is much longer than the actual data transfer, causing the derived speed (GB/s) to be far lower than the hardware or network's actual capabilities.

**Expected:**
KV cache transfer metrics (`transfer_latency_s`, `latency_ms`, `speed_gb_s`) should be measured between the actual start and end of the KV cache transfer, not including decode time. The most natural end timestamp is probably `prefill_kv_transfer_finish_time`, matching the logic of `set_prefill_kv_transfer_finish_time()`.

**Reference:**
[compute_and_observe_kv_transfer_metrics implementation](https://github.com/sgl-project/sglang/blob/7824903417b7398ffaf9befe8a221080627e152f/python/sglang/srt/observability/req_time_stats.py#L865-L878)

**Suggested fix:**
Use (`prefill_kv_transfer_finish_time` - `prefill_transfer_queue_entry_time`) rather than (`completion_time` - `prefill_transfer_queue_entry_time`) to compute transfer latency.

### Reproduction

1. Run SGLang with prefill KV cache transfer enabled (any model, any hardware backend)
2. Inject logging to print both `prefill_transfer_queue_entry_time`, `prefill_kv_transfer_finish_time`, and `completion_time` timestamps
3. Observe reported transfer_latency_s and actual duration between queue-entry and kv-transfer-finish
4. Compare logs and validate the negative bias/error in observed speed_gb_s

### Environment

Python: 3.12.12 (main, Oct 10 2025, 08:52:57) [GCC 11.4.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA L20X
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 570.148.08
PyTorch: 2.8.0+cu129
sglang: 0.5.5
sgl_kernel: 0.3.16.post5
flashinfer_python: 0.5.0
flashinfer_cubin: 0.5.0
flashinfer_jit_cache: Module Not Found
triton: 3.4.0
transformers: 4.57.1
torchao: 0.9.0
numpy: 2.3.4
aiohttp: 3.13.2
fastapi: 0.121.0
hf_transfer: 0.1.9
huggingface_hub: 0.36.0
interegular: 0.3.3
modelscope: 1.31.0
orjson: 3.11.4
outlines: 0.1.11
packaging: 25.0
psutil: 7.1.3
pydantic: 2.12.4
python-multipart: 0.0.20
pyzmq: 27.1.0
uvicorn: 0.38.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.25
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.72.0
litellm: Module Not Found
decord2: 2.0.0
ulimit soft: 204800
(Note: Network and host/ip info has been omitted.)
