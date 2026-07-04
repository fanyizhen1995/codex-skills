---
source_id: sglang-github-closed-issues-prs
title: '[Bug] CP+PP Occur RuntimeError: The size of tensor a (4) must match the size
  of tensor b (8) at non-singleton dimension 0'
canonical_url: https://github.com/sgl-project/sglang/issues/25887
captured_at: '2026-07-03T02:13:21.690467+00:00'
content_hash: b8b4be924d08297109e0ca68b66c7264ab67395a23d180d8153a25e02d825903
---
# [Bug] CP+PP Occur RuntimeError: The size of tensor a (4) must match the size of tensor b (8) at non-singleton dimension 0

URL: https://github.com/sgl-project/sglang/issues/25887
State: closed
Labels: 
Closed at: 2026-07-02T08:13:48Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug
GLM-5.1 deployed on H100 with CP+PP. A few instances began throwing the errors shown below after running for a while(about 17h):
```
1779264164496	2026-05-20T08:02:44.496Z	[2026-05-20 08:02:44 PP0 ATTN_CP0 TP0] Decode batch, #running-req: 4, #token: 477376, token usage: 0.90, cuda graph: True, gen throughput (token/s): 199.95, #queue-req: 6

1779264164565	2026-05-20T08:02:44.565Z	Finish: obj=GenerateReqInput(rid='bf890d9ca8ce4008bef7ef25d97f8fba', http_worker_ipc=None, video_data=None, sampling_params={'temperature': 1.0, 'max_new_tokens': 32000, 'min_new_tokens': 0, 'stop': None, 'stop_token_ids': None, 'stop_regex': None, 'top_p': 0.95, 'top_k': -1, 'min_p': 0.0, 'presence_penalty': 0.0, 'frequency_penalty': 0.0, 'repetition_penalty': 1.0, 'regex': None, 'ebnf': None, 'n': 1, 'no_stop_trim': False, 'ignore_eos': False, 'skip_special_tokens': False, 'logit_bias': None, 'custom_params': None, 'sampling_seed': None, 'spaces_between_special_tokens': True}, return_logprob=False, logprob_start_len=-1, top_logprobs_num=0, token_ids_logprob=None, return_text_in_logprobs=True, stream=True, log_metrics=True, return_hidden_states=False, return_routed_experts=False, routed_experts_start_len=0, modalities=[], session_params=None, lora_id=None, custom_logit_processor=None, bootstrap_host=None, bootstrap_port=None, bootstrap_room=None, bootstrap_pair_key=None, decode_tp_size=None, require_reasoning=True, routed_dp_rank=None, disagg_prefill_dp_rank=None, data_parallel_rank=None, background=False, conversation_id=None, priority=None, extra_key=None, routing_key=None, no_logs=False, custom_labels=None, return_bytes=False, return_entropy=False, external_trace_header=None, received_time=26519772.456564333, need_wait_for_mm_inputs=None, num_items_assigned=None, max_dynamic_patch=None, min_dynamic_patch=None, image_max_dynamic_patch=None, video_max_dynamic_patch=None), out={'meta_info': {'id': 'bf890d9ca8ce4008bef7ef25d97f8fba', 'finish_reason': {'type': 'abort', 'message': 'Request running timeout reached.', 'status_code': 503, 'err_type': None}, 'prompt_tokens': 32472, 'weight_version': 'default', 'total_retractions': 0, 'queue_time': 0.0, 'prefill_waiting_latency': None, 'prefill_launch_latency': None, 'reasoning_tokens': 23297, 'completion_tokens': 23297, 'cached_tokens': 32320, 'cached_tokens_details': {'device': 32320, 'host': 0}, 'dp_rank': None, 'e2e_latency': 1201.9242150001228, 'request_received_ts': 1779262962.6408873, 'api_server_dispatch_finish_ts': 1779262962.8541057, 'response_sent_to_client_ts': 1779262965.4523866, 'request_finished_ts': 1779264164.565102, 'inference_time': 26520974.380779333, 'decode_throughput': 19.428522417494694}}

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP7 TP7] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.68

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP2 TP2] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.59

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP3 TP3] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.67

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP5 TP5] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.67

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP0 TP0] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.68

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP6 TP6] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.69

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP1 TP1] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.62

1779264164792	2026-05-20T08:02:44.792Z	[2026-05-20 08:02:44 PP0 ATTN_CP4 TP4] Prefill batch, #new-seq: 1, #new-token: 128, #cached-token: 57856, token usage: 0.97, #running-req: 3, #queue-req: 5, cuda graph: False, input throughput (token/s): 1732.69

1779264164793	2026-05-20T08:02:44.793Z	[2026-05-20 08:02:44] INFO:     10.42.0.190:54466 - "POST /v1/chat/completions HTTP/1.1" 200 OK

1779264164797	2026-05-20T08:02:44.797Z	[2026-05-20 08:02:44 PP0 ATTN_CP7 TP7] Scheduler hit an exception: Traceback (most recent call last):

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3616, in run_scheduler_process

1779264164797	2026-05-20T08:02:44.797Z	    scheduler.run_event_loop()

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 1300, in run_event_loop

1779264164797	2026-05-20T08:02:44.797Z	    dispatch_event_loop(self)

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3495, in dispatch_event_loop

1779264164797	2026-05-20T08:02:44.797Z	    scheduler.event_loop_pp()

1779264164797	2026-05-20T08:02:44.797Z	  File "/usr/local/lib/python3.12/dist-packages/torch/utils/_contextlib.py", line 120, in decorate_context

1779264164797	2026-05-20T08:02:44.797Z	    return func(*args, **kwargs)

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler_pp_mixin.py", line 108, in event_loop_pp

1779264164797	2026-05-20T08:02:44.797Z	    result, self.launch_event = self._pp_launch_batch(

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler_pp_mixin.py", line 1128, in _pp_launch_batch

1779264164797	2026-05-20T08:02:44.797Z	    result = self.run_batch(self.cur_batch, pp_proxy_tensors)

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 2724, in run_batch

1779264164797	2026-05-20T08:02:44.797Z	    batch_result = self.model_worker.forward_batch_generation(

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 524, in forward_batch_generation

1779264164797	2026-05-20T08:02:44.797Z	    out = self.model_runner.forward(

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 2739, in forward

1779264164797	2026-05-20T08:02:44.797Z	    output = self._forward_raw(

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 2804, in _forward_raw

1779264164797	2026-05-20T08:02:44.797Z	    ret = self.graph_runner.replay(

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 1150, in replay

1779264164797	2026-05-20T08:02:44.797Z	    self.replay_prepare(forward_batch, pp_proxy_tensors)

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 1093, in replay_prepare

1779264164797	2026-05-20T08:02:44.797Z	    buffers.populate_from_forward_batch(

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 348, in populate_from_forward_batch

1779264164797	2026-05-20T08:02:44.797Z	    _grouped_foreach_copy_(dsts, srcs)

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 117, in _grouped_foreach_copy_

1779264164797	2026-05-20T08:02:44.797Z	    foreach_copy(group_dsts, group_srcs)

1779264164797	2026-05-20T08:02:44.797Z	  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 104, in foreach_copy

1779264164797	2026-05-20T08:02:44.797Z	    torch._foreach_copy_(dsts, srcs)

1779264164797	2026-05-20T08:02:44.797Z	RuntimeError: The size of tensor a (4) must match the size of tensor b (8) at non-singleton dimension 0
```

### Reproduction

```
              python3 -m sglang.launch_server \
              --model /models/ZhipuAI/GLM-5.1-FP8  \
              --dist-init-addr $LWS_LEADER_ADDRESS:20000 \
              --tp 8 --pp-size 2 \
              --dp-size 1 --moe-dense-tp-size 1 \
              --attn-cp-size 8 \
              --enable-nsa-prefill-context-parallel \
              --nsa-prefill-cp-mode round-robin-split  \
              --nnodes $LWS_GROUP_SIZE  \
              --node-rank $LWS_WORKER_INDEX \
              --trust-remote-code \
              --host 0.0.0.0 \
              --port 8000 \
              --dist-timeout 7200 \
              --enable-metrics \
              --reasoning-parser glm45 \
              --tool-call-parser glm47 \
              --log-requests --log-requests-level 1 \
              --kv-cache-dtype fp8_e4m3 \
              --watchdog-timeout 1800 \
              --mem-fraction-static 0.85 \
              --max-running-requests 64 \
              --chunked-prefill-size 16384 \
              --cuda-graph-max-bs 64 \
              --page-size 64 \
              --preferred-sampling-params '{"max_new_tokens": 8192}' \
              --enable-hierarchical-cache \
              --hicache-ratio 2.0 \
              --hicache-write-policy write_through
```

### Environment

```
Python: 3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H100 80GB HBM3
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 570.124.06
PyTorch: 2.9.1+cu129
sglang: 0.5.10
sglang-kernel: 0.4.1
flashinfer_python: 0.6.7.post2
flashinfer_cubin: 0.6.7.post2
flashinfer_jit_cache: 0.6.7.post2+cu129
triton: 3.5.1
transformers: 5.3.0
torchao: 0.9.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.135.3
huggingface_hub: 1.9.0
interegular: 0.3.3
modelscope: 1.35.3
orjson: 3.11.8
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.12.5
python-multipart: 0.0.22
pyzmq: 27.1.0
uvicorn: 0.43.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.32
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.89.0
litellm: Module Not Found
torchcodec: 0.9.1
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3    NIC4    NIC5    NIC6    NIC7    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX     NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    PIX     PIX     SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE    SYS     SYS     SYS     SYS     0-47,96-143     0               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS     PIX     PIX     NODE    NODE    48-95,144-191   1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    48-95,144-191   1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS     NODE    NODE    PIX     PIX     48-95,144-191   1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS     NODE    NODE    NODE    NODE    48-95,144-191   1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     NODE    NODE    SYS     SYS     SYS     SYS
NIC1    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      NODE    NODE    SYS     SYS     SYS     SYS
NIC2    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      PIX     SYS     SYS     SYS     SYS
NIC3    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    PIX      X      SYS     SYS     SYS     SYS
NIC4    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     NODE    NODE
NIC5    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      NODE    NODE
NIC6    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      PIX
NIC7    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    PIX      X 

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

NIC Legend:

  NIC0: mlx5_0
  NIC1: mlx5_1
  NIC2: mlx5_2
  NIC3: mlx5_3
  NIC4: mlx5_4
  NIC5: mlx5_5
  NIC6: mlx5_6
  NIC7: mlx5_7


ulimit soft: 1048576

```
