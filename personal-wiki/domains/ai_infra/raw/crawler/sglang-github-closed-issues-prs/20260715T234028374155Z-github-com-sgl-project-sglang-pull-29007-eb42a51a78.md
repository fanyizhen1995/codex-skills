---
source_id: sglang-github-closed-issues-prs
title: Fix MoE TP allreduce to use NCCL symmetric memory via in-pool output allocation
canonical_url: https://github.com/sgl-project/sglang/pull/29007
captured_at: '2026-07-15T23:40:28.374155+00:00'
content_hash: eb42a51a78c4c7c086913cdae64d065e30188a60f2589fbb4eaffebdd68fcf43
---
# Fix MoE TP allreduce to use NCCL symmetric memory via in-pool output allocation

URL: https://github.com/sgl-project/sglang/pull/29007
State: closed
Labels: deepseek, run-ci, bypass-fastfail
Closed at: 2026-07-15T07:06:38Z
Merged at: 2026-07-15T07:06:38Z

cc @yizhang2077 @ShangmingCai @nvcastet @ispobock   @Fridge003 @merrymercy PTAL, thx.

  ## Motivation

When `--enable-symm-mem` is set, SGLang's MoE layer should ensure the tensor passed to `tensor_model_parallel_all_reduce` resides in the NCCL symmetric memory pool so the fast path is taken. However, two issues prevented this from working:

  1. MoE runners allocated their own output buffers outside the symm pool. The forward_impl previously wrapped the entire MoE compute in a single `use_symmetric_memory` context, but individual runners (DeepGemm, Triton, etc.) called torch.empty for their output, which did not reuse the pre-allocated symmetric buffer. The first commit fixes this by introducing moe_output_buffer_ctx — a contextvars-based mechanism that passes a pre-allocated symm_output buffer down to runners, allowing cooperating runners to write directly into it instead of allocating new memory.
  2. The MoE output may still fall outside the symm pool even with the buffer context, because: (a) upstream hidden_states (e.g. from hc_pre in DeepSeek-V4) may not reside in the symm pool, causing the entire dispatch→experts→combine pipeline to produce output outside the pool; (b) some quant methods/runners ignore the buffer context and allocate their own output. The second commit adds a data_ptr comparison after combine — if the result is not backed by symm_output, it copies the data into the symm buffer so the downstream allreduce can use the low-latency NCCL symmetric memory path. The copy overhead is negligible (a single small memcpy on decode-scale batch sizes) compared to the latency saving.

  Result: On DeepSeek-V4-Flash-FP8 with `--enable-symm-mem`, under 4K input / 1.5K output benchmark, TPOT drops 6.55% (11.44 → 10.69 ms) and average per-call allreduce latency drops 50% (20 → 10 μs).


  ## Modifications

  - `python/sglang/srt/layers/moe/moe_runner/deep_gemm.py` (5 sites):
    Wrap the final `down_output` / `output` allocation in
    `use_symmetric_memory(get_tp_group(), disabled=not is_allocation_symmetric())`
    so the MoE output enters the symm pool. Intermediate buffers stay on the
    default allocator to bound pool occupancy. Affected:
    `_gemm_nt_f8f8bf16_contig`, `_run_bf16_contiguous_gemm`,
    `_gemm_nt_bf16_masked`, `_run_bf16_masked_gemm`,
    `post_permute_deep_gemm_to_standard`.

  - `python/sglang/srt/layers/moe/moe_runner/triton_utils/fused_moe.py`:
    Wrap the non-inplace `out_hidden_states = torch.empty_like(...)` allocation in
    `_fused_moe_kernel_sequence` with the same symm-mem context.

  - `python/sglang/srt/layers/mhc.py`:
    Allocate `layer_input` (`_mhc_pre_impl`) and `layer_input_cur`
    (`mhc_fused_post_pre`) — the post-norm activation fed into the MoE on the
    TileLang mHC path — in the symm pool, so the inplace Triton MoE runner yields
    a symmetric allreduce input.

  - `python/sglang/srt/models/deepseek_v4.py`:
    Mirror the above on the non-TileLang hc_pre path: allocate `y` (the post-norm
    activation) in the symm pool, gated by `is_allocation_symmetric()`. Only one
    of the TileLang / non-TileLang paths runs per forward.

  - `test/registered/kernels/test_mhc_kernels.py`:
    Single-process kernel unit test has no TP group initialized; monkeypatch
    `use_symmetric_memory`→`nullcontext()`, `is_allocation_symmetric`→`False`,
    `get_tp_group`→`None` so the kernel allocates via plain `torch.empty`. Mirrors
    the existing workaround in `test_mxfp4_sm90_cutlass.py`.

## Accuracy Tests

before：
```
Accuracy: 0.954
Invalid: 0.000
Latency: 158.093 s
Output throughput: 560.387 token/s
```

after fix moe symm allreduce：
```
Accuracy: 0.952
Invalid: 0.000
Latency: 144.824 s
Output throughput: 611.551 token/s
```

## Speed Tests and Profiling

With --enable-symm-mem enabled on DeepSeek-V4-Flash-FP8, under a benchmark of 4K input / 1.5K output tokens, this PR reduces TPOT by 6.55% (11.44 → 10.69 ms) and cuts average per-call allreduce latency by 50% (20 → 10 μs).


```
export TORCHINDUCTOR_CACHE_DIR=/home/fakang/dsv4/inductor_root_cache
export SGLANG_TORCH_PROFILER_DIR=/home/fakang/dsv4/pro
export SGLANG_DSV4_FP4_EXPERTS=0 
export SGLANG_OPT_USE_JIT_INDEXER_METADATA=1 
export SGLANG_JIT_DEEPGEMM_PRECOMPILE=0 
export SGLANG_OPT_SWA_SPLIT_LEAF_ON_INSERT=1 
#export SGLANG_DEBUG_SYMM_MEM=1

 python -m sglang.launch_server \
  --model-path /home/fakang.wfk/models/DeepSeek-V4-Flash-FP8 \
  --host 0.0.0.0 --port 8188 \
  --trust-remote-code --enable-cache-report --log-level info --enable-metrics \
  --page-size 64 --cuda-graph-max-bs 64 --max-running-requests 64 \
  --mem-fraction-static 0.92 --swa-full-tokens-ratio 0.02 \
  --tp-size 8 \
  --enable-nsa-prefill-context-parallel --nsa-prefill-cp-mode round-robin-split \
  --tool-call-parser deepseekv4 --reasoning-parser deepseek-v4 \
  --disable-radix-cache \
  --enable-symm-mem 


bs=1
request_rate=inf
nohup python -m sglang.bench_serving --model /home/fakang.wfk/models/DeepSeek-V4-Flash-FP8/  --random-range-ratio 1.0 \
        --request-rate ${request_rate} --max-concurrency $bs \
        --dataset-name random-ids --random-input-len 4096 --random-output-len 1536 \
        --dataset-path /home/fakang/dsv3/ShareGPT_V3_unfiltered_cleaned_split.json \
        --num-prompts 50 --host 0.0.0.0 --port 8188 
```

before:
<img width="1920" height="871" alt="image" src="https://github.com/user-attachments/assets/ee3e5bea-c3bd-43b4-8b48-fcd7a2310278" />

after fix moe symm allreduce:
<img width="1920" height="862" alt="image" src="https://github.com/user-attachments/assets/84ab135d-222c-45ed-b4ae-5c5e6de09b55" />

before:
```
#Input tokens: 204800
#Output tokens: 76800
Starting warmup with 1 sequences...
Warmup completed with 1 sequences. Starting main benchmark run...
100%|██████████| 50/50 [14:50<00:00, 17.81s/it]

============ Serving Benchmark Result ============
Backend:                                 sglang    
Traffic request rate:                    inf       
Max request concurrency:                 1         
Successful requests:                     50        
Benchmark duration (s):                  890.81    
Total input tokens:                      204800    
Total input text tokens:                 204800    
Total generated tokens:                  76800     
Total generated tokens (retokenized):    76436     
Request throughput (req/s):              0.06      
Input token throughput (tok/s):          229.90    
Output token throughput (tok/s):         86.21     
Peak output token throughput (tok/s):    96.00     
Peak concurrent requests:                2         
Total token throughput (tok/s):          316.12    
Concurrency:                             1.00      
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   17813.70  
Median E2E Latency (ms):                 17755.02  
P90 E2E Latency (ms):                    18381.57  
P95 E2E Latency (ms):                    18551.06  
P99 E2E Latency (ms):                    20518.64  
---------------Time to First Token----------------
Mean TTFT (ms):                          249.77    
Median TTFT (ms):                        218.59    
P90 TTFT (ms):                           361.41    
P95 TTFT (ms):                           362.67    
P99 TTFT (ms):                           405.75    
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          11.44     
Median TPOT (ms):                        11.36     
P90 TPOT (ms):                           11.83     
P95 TPOT (ms):                           11.86     
P99 TPOT (ms):                           13.18     
---------------Inter-Token Latency----------------
Mean ITL (ms):                           11.44     
Median ITL (ms):                         10.54     
P90 ITL (ms):                            10.69     
P95 ITL (ms):                            10.80     
P99 ITL (ms):                            57.67     
Max ITL (ms):                            2235.31   
==================================================

```

after fix moe symm allreduce: 
```
#Input tokens: 204800
#Output tokens: 76800
Starting warmup with 1 sequences...
Warmup completed with 1 sequences. Starting main benchmark run...
100%|██████████| 50/50 [13:52<00:00, 16.64s/it]

============ Serving Benchmark Result ============
Backend:                                 sglang    
Traffic request rate:                    inf       
Max request concurrency:                 1         
Successful requests:                     50        
Benchmark duration (s):                  832.18    
Total input tokens:                      204800    
Total input text tokens:                 204800    
Total generated tokens:                  76800     
Total generated tokens (retokenized):    76567     
Request throughput (req/s):              0.06      
Input token throughput (tok/s):          246.10    
Output token throughput (tok/s):         92.29     
Peak output token throughput (tok/s):    102.00    
Peak concurrent requests:                2         
Total token throughput (tok/s):          338.39    
Concurrency:                             1.00      
----------------End-to-End Latency----------------
Mean E2E Latency (ms):                   16641.41  
Median E2E Latency (ms):                 16517.41  
P90 E2E Latency (ms):                    17168.32  
P95 E2E Latency (ms):                    17423.70  
P99 E2E Latency (ms):                    19625.03  
---------------Time to First Token----------------
Mean TTFT (ms):                          237.28    
Median TTFT (ms):                        215.28    
P90 TTFT (ms):                           347.30    
P95 TTFT (ms):                           367.20    
P99 TTFT (ms):                           399.26    
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          10.69     
Median TPOT (ms):                        10.58     
P90 TPOT (ms):                           11.04     
P95 TPOT (ms):                           11.19     
P99 TPOT (ms):                           12.60     
---------------Inter-Token Latency----------------
Mean ITL (ms):                           10.69     
Median ITL (ms):                         9.84      
P90 ITL (ms):                            9.94      
P95 ITL (ms):                            10.05     
P99 ITL (ms):                            52.94     
Max ITL (ms):                            2424.72   
==================================================
```


## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29323734587](https://github.com/sgl-project/sglang/actions/runs/29323734587)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29323734351](https://github.com/sgl-project/sglang/actions/runs/29323734351)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
