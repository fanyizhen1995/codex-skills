---
source_id: sglang-github-closed-issues-prs
title: '[Apple Silicon] [MLX] MLX decode partial overlap scheduling for generation
  (async eval)'
canonical_url: https://github.com/sgl-project/sglang/pull/22416
captured_at: '2026-07-09T23:36:35.342737+00:00'
content_hash: a9b8cd567cb21138324d8cf6f0a9b678f6a5fa484d51e002909b1549643dec1f
---
# [Apple Silicon] [MLX] MLX decode partial overlap scheduling for generation (async eval)

URL: https://github.com/sgl-project/sglang/pull/22416
State: closed
Labels: documentation, run-ci
Closed at: 2026-04-29T19:21:15Z
Merged at: 2026-04-29T19:21:15Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Fixes #22114 
Fixes #22466 (indirectly -> see comment in issue)

The MLX backend implementation was written in a way that caused the CPU to synchronize with the GPU on every decode pass as seen in this picture. These idle gaps in the GPU led to lower throughput and could be optimized in way done in the CUDA version seen [here](https://www.lmsys.org/blog/2024-12-04-sglang-v0-4/).
<img width="2072" height="280" alt="image" src="https://github.com/user-attachments/assets/474af1c3-68d3-474f-9c55-9947a984afb8" />

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

The `scheduler` has a new _event_loop_overlap_mlx that only runs when MLX is available (and is turned on by default). It introduces a new mechanism where up to 2 MLX computational graphs are maintained (if decoding workloads can be chained). It takes advantage of MLX's lazy evaluation as seen in [MLX-LM](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/generate.py#L429). 

The `MlxTpModelWorker` was also updated with new functions that support async evaluation of MLX arrays.

The `MlxModelRunner` was also updated to support creation of MLX arrays without evaluating them (just to build the computational graph).

The arrays are evaluated when they are needed in `MlxModelRunner.prefill_finalize()`, `MlxModelRunner.extend_finalize()`, and `MlxModelRunner.decode_batch_finalize()` .

### How the chain works                                                                                                                                                                                                 
                  
At steady state the scheduler holds two pending MLX graphs: `pending_curr` (about to be finalised for tokens + bookkeeping) and `pending_next` (built on top of `pending_curr`'s still-lazy output via `decode_batch_start_chained`, already handed to `mx.async_eval`). `pending_next` reuses `pending_curr.batch_cache` in place, so KV writes from both steps land in shared tensors and MLX tracks the full dependency graph. The GPU runs them back-to-back with no scheduling gap. CPU-side bookkeeping for step N (`process_batch_result`, `recv_requests`, building step N+2's graph in the next iteration) happens in parallel with the GPU executing step N+1.

CPU:
   iter0:  build+launch J0 ................................. curr=J0
   iter1:  build+launch J1(chains J0); block J0; process J0; curr=J1
   iter2:  build+launch J2(chains J1); block J1; process J1; curr=J2
   iter3:  build+launch J3(chains J2); block J2; process J2; curr=J3

GPU:   [ J0 ][ J1 ][ J2 ][ J3 ] ...   (contiguous)
                  
### When the chain breaks

The chain falls back to the standard `get_next_batch_to_run` → `_launch_fresh` path whenever:                                                                                                                           
  
1. `pending_curr` is not a pure decode (prefill / extend).                                                                                                                                                              
2. `self.waiting_queue` has new requests needing prefill (we prioritise serving them).
3. Any req in `pending_curr` just finished (composition for `pending_next` would need to shrink).                                                                                                                       
                                                                                                                                                                                                                          
When case 2 or 3 fires mid-flight, the already-launched `pending_next` is NOT discarded — it's finalized normally. The chain then re-forms with one non-chained warmup step on the next iteration.                                                                                                                                                                          
                                                                                                                                                                                                                                        
## Limitations / Follow-ups   
- Only **decode → decode** is chained. Prefill and batch composition changes break the chain.                                                                                                                           
- Up to **one wasted decode step** per EOS: when a req finishes, `pending_next` was speculatively launched for it; its extra token is discarded downstream.
- Scheduler-side preemption / KV pressure checks only run at chain breaks, not on every chained iteration. Fine at 2-deep; revisit if we ever grow the pipeline depth.

<!-- Detail the changes made in this pull request. -->

## Functional Test
```
(sglang) changminbark@wifi161-005:~/Desktop/OpenSource/sglang/sglang% curl http://localhost:43440/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Tell me a short joke."}
    ],
    "max_tokens": 10
  }'
{"id":"d58a05ccf1ac4e66ab5f0b6a271de97e","object":"chat.completion","created":1776731078,"model":"Qwen/Qwen3-0.6B","choices":[{"index":0,"message":{"role":"assistant","content":"<think>\nOkay, the user asked for a short","reasoning_content":null,"tool_calls":null},"logprobs":null,"finish_reason":"length","matched_stop":null}],"usage":{"prompt_tokens":25,"total_tokens":35,"completion_tokens":10,"prompt_tokens_details":null,"reasoning_tokens":0},"metadata":{"weight_version":"default"}}%    
```
```
(sglang) changminbark@wifi187-099:~/Desktop/OpenSource/sglang/sglang% SGLANG_USE_MLX=1 python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B \
  --port 43440
...
[2026-04-20 20:24:26] INFO:     Started server process [14342]
[2026-04-20 20:24:26] INFO:     Waiting for application startup.
[2026-04-20 20:24:26] Using default chat sampling params from model generation config: {'temperature': 0.6, 'top_k': 20, 'top_p': 0.95}
[2026-04-20 20:24:26] INFO:     Application startup complete.
[2026-04-20 20:24:26] INFO:     Uvicorn running on http://127.0.0.1:43440 (Press CTRL+C to quit)
[2026-04-20 20:24:27] INFO:     127.0.0.1:63737 - "GET /model_info HTTP/1.1" 200 OK
[2026-04-20 20:24:27] MlxKVPool: 42032 slots × 28 layers × 8 heads × 128 dim, dtype=mlx.core.bfloat16, ~4597.2 MB
[2026-04-20 20:24:27] KV pool initialized: pool_size=42031 (buffer size 42032 incl. padding slot 0), 28 layers, 8 kv_heads, 128 head_dim
[2026-04-20 20:24:27] Prefill batch, #new-seq: 1, #new-token: 6, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, cuda graph: False, input throughput (token/s): 1.37
[2026-04-20 20:24:27] INFO:     127.0.0.1:63738 - "POST /generate HTTP/1.1" 200 OK
[2026-04-20 20:24:27] The server is fired up and ready to roll!
[2026-04-20 20:24:37] Prefill batch, #new-seq: 1, #new-token: 25, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, cuda graph: False, input throughput (token/s): 2.35
[2026-04-20 20:24:38] INFO:     127.0.0.1:63742 - "POST /v1/chat/completions HTTP/1.1" 200 OK
```

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

### Radix Cache Support (made in #21509)
```
(sglang) changminbark@wifi161-005:~/Desktop/OpenSource/sglang/sglang% SGLANG_USE_MLX=1 uv run python -m sglang.bench_one_batch --model-path Qwen/Qwen3-0.6B --trust-remote-code --disable-cuda-graph --tp-size 1 --batch-size 1 --input-len 60 --output-len 10 --port 43440

Warmup ...
Prefill. latency: 0.06075 s, throughput:    987.71 token/s
Decode 0. Batch size: 1, latency: 0.00807 s, throughput:    123.90 token/s
Decode 1. Batch size: 1, latency: 0.00758 s, throughput:    131.85 token/s
Decode 2. Batch size: 1, latency: 0.00743 s, throughput:    134.57 token/s
Decode 3. Batch size: 1, latency: 0.00729 s, throughput:    137.11 token/s
Decode 4. Batch size: 1, latency: 0.00717 s, throughput:    139.55 token/s
Decode.  median latency: 0.00717 s, median throughput:    139.55 token/s
Total. latency:  0.126 s, throughput:    556.05 token/s
Benchmark ...
Prefill. latency: 0.01788 s, throughput:   3355.60 token/s
Decode 0. Batch size: 1, latency: 0.00695 s, throughput:    143.98 token/s
Decode 1. Batch size: 1, latency: 0.00693 s, throughput:    144.24 token/s
Decode 2. Batch size: 1, latency: 0.00680 s, throughput:    147.16 token/s
Decode 3. Batch size: 1, latency: 0.00678 s, throughput:    147.39 token/s
Decode 4. Batch size: 1, latency: 0.00676 s, throughput:    147.86 token/s
Decode.  median latency: 0.00689 s, median throughput:    145.10 token/s
Total. latency:  0.080 s, throughput:    877.74 token/s
```

### Before
```
(sglang) changminbark@wifi161-005:~/Desktop/OpenSource/sglang/sglang% SGLANG_USE_MLX=1 uv run python -m sglang.bench_offline_throughput --model-path Qwen/Qwen3-0.6B --num-prompts 1 --port 43440 --disable-overlap-schedule
...
====== Offline Throughput Benchmark Result =======
Backend:                                 engine    
Successful requests:                     1         
Benchmark duration (s):                  1.76      
Total input tokens:                      17        
Total generated tokens:                  244       
Last generation throughput (tok/s):      142.07    
Request throughput (req/s):              0.57      
Input token throughput (tok/s):          9.65      
Output token throughput (tok/s):         138.48    
Total token throughput (tok/s):          148.13    
==================================================
```
<img width="1483" height="722" alt="image" src="https://github.com/user-attachments/assets/b0daaae5-fe88-4089-a4ac-2f3b100208c4" />


### After
```
(sglang) changminbark@wifi161-005:~/Desktop/OpenSource/sglang/sglang% SGLANG_USE_MLX=1 uv run python -m sglang.bench_offline_throughput --model-path Qwen/Qwen3-0.6B --num-prompts 1 --port 43440
...
====== Offline Throughput Benchmark Result =======
Backend:                                 engine    
Successful requests:                     1         
Benchmark duration (s):                  1.52      
Total input tokens:                      17        
Total generated tokens:                  244       
Last generation throughput (tok/s):      166.69    
Request throughput (req/s):              0.66      
Input token throughput (tok/s):          11.16     
Output token throughput (tok/s):         160.13    
Total token throughput (tok/s):          171.29    
==================================================
```
<img width="1485" height="738" alt="image" src="https://github.com/user-attachments/assets/4e2ef664-b036-4c20-9b6a-fe0bbbe70cdf" />

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.

## AI Usage
The main code logic was written by me. Claude Code was used to polish the code and write comments/docstrings in the code (as well as parts of the PR description). Everything was verified and understood by me.
