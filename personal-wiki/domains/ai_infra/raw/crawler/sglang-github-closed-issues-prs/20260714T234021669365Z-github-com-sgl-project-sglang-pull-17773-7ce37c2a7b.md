---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Fuse Q FP8 cast into KV buffer kernel for TRTLLM MHA backend'
canonical_url: https://github.com/sgl-project/sglang/pull/17773
captured_at: '2026-07-14T23:40:21.669365+00:00'
content_hash: 7ce37c2a7b034105c1d577b06d7670b7c6c954a011776faafdb1268033261303
---
# [Kernel] Fuse Q FP8 cast into KV buffer kernel for TRTLLM MHA backend

URL: https://github.com/sgl-project/sglang/pull/17773
State: closed
Labels: blackwell, run-ci
Closed at: 2026-07-14T15:21:57Z
Merged at: 

## Summary                                                                              
  - Fuse the FP8 cast operation for Q tensor into the existing KV buffer kernel for TRTLLM
   MHA backend                                                                            
  - This eliminates a separate `q.to(fp8)` kernel launch, reducing kernel launch overhead 
  and improving memory bandwidth utilization                                              
  - Part of #17526 (Blackwell performance optimization)                                   
                                                                                          
  ## Motivation                                                                           
  In the original implementation, FP8 attention requires two separate operations:         
  1. `_fused_fp8_set_kv_buffer_kernel`: quantize K/V to FP8 and write to paged KV cache   
  2. `q.to(torch.float8_e4m3fn)`: cast Q to FP8 (via PyTorch elementwise kernel)          
                                                                                          
  This PR fuses both operations into a single Triton kernel, eliminating the extra kernel 
  launch overhead.                                                                        
                                                                                          
  ## Changes                                                                              
                                                                                          
  ### Kernel Design (`trtllm_fp8_kv_kernel.py`)                                           
  - Added `_fused_fp8_set_qkv_buffer_kernel` with precise block mapping to avoid empty    
  thread blocks in GQA models:                                                            
    - Grid: `(num_tokens, 2 * Bkv + Bq)` where `Bkv = ceil(num_kv_heads / BLOCK_HEAD)`,   
  `Bq = ceil(num_q_heads / BLOCK_HEAD)`                                                   
    - Block mapping: `[0, Bkv)` → K, `[Bkv, 2*Bkv)` → V, `[2*Bkv, 2*Bkv+Bq)` → Q          
  - Added `_process_q_tensor` helper for Q FP8 cast (equivalent to `q.to(fp8)`)           
  - Q cast produces bitwise-identical results to `q.to(torch.float8_e4m3fn)`              
                                                                                          
  ### Backend Changes (`trtllm_mha_backend.py`)                                           
  - Added `q_fp8_buffer` for pre-allocated Q output buffer                                
  - Added `_inv_scale_cache` to cache pre-computed inverse scale tensors per layer        
  - Added `_ensure_q_fp8_buffer()` for lazy allocation in non-CUDA-graph mode             
  - Added `_get_inv_scale_tensors()` to avoid tensor allocation during CUDA graph capture 
  - Modified `forward_decode` and `forward_extend` to use fused QKV path when FP8         
  attention is enabled                                                                    
                                                                                          
  ### CUDA Graph Compatibility                                                            
  - `q_fp8_buffer` is pre-allocated in `init_cuda_graph_state()`                          
  - Inverse scale tensors are computed once and cached in `_inv_scale_cache`              
  - No tensor allocation occurs during forward pass, ensuring CUDA graph capture works    
  correctly                                                                               
                                                                                          
  ## Performance                                                                          
  Tested on GLM-4.7 with 4xB300, FP8 attention, TP=4:                                     
                                                                                          
  | Metric | Before | After | Improvement |                                               
  |--------|--------|-------|-------------|                                               
  | Output throughput | 990 tok/s | 1019 tok/s | +2.9% |                                  
  | Q+KV kernel time | 4262 us | 1483 us | -65% |                                         
                                                                                          
  Profile comparison (920 calls per decode step on TP0):                                  
  - **Before**: `_fused_fp8_set_kv_buffer_kernel` (1432us) + `q.to(fp8)` elementwise      
  (2830us) = 4262us                                                                       
  - **After**: `_fused_fp8_set_qkv_buffer_kernel` (1483us)                                
                                                                                          
  ### Before                                                                              
  <img width="1096" height="755" alt="beforechange" src="https://github.com/user-attachments/assets/b986639a-b081-450e-aed9-a29d64357478" />                                                        
                                                                                          
  ### After                                                                               
   <img width="1397" height="864" alt="afterchange" src="https://github.com/user-attachments/assets/da65c0cb-ed7c-4d3f-bdce-8ad27a9994d2" />
