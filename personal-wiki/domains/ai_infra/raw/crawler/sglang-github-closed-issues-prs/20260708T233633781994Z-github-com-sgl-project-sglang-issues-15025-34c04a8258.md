---
source_id: sglang-github-closed-issues-prs
title: '[Roadmap] DeepSeek v3.2 (GLM 5) Optimization'
canonical_url: https://github.com/sgl-project/sglang/issues/15025
captured_at: '2026-07-08T23:36:33.781994+00:00'
content_hash: 34c04a82582f5abc93ac5c12f887b37ea0b4af0eb17a65a64f220c159b1c3552
---
# [Roadmap] DeepSeek v3.2 (GLM 5) Optimization

URL: https://github.com/sgl-project/sglang/issues/15025
State: closed
Labels: high priority, deepseek, Good Pro Issue, good second issue, nvidia
Closed at: 2026-07-08T05:56:15Z
Merged at: 

## Background
There has been an increasing need of deployment for [DeepSeek V3.2](https://huggingface.co/deepseek-ai/DeepSeek-V3.2) and [DeepSeek V3.2 Speciale](https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Speciale) since their release. However, there are still some functionality/performance gap between DeepSeek V3.2 and DeepSeek V3.1.

For GLM-5, it's reusing the structure of DeepSeek v3.2, with only small modification (like shape sizes). So most of the V32 optimization can be reused on GLM-5. 


## Optimization Items

### Parallelism
- [x] Initial support for Pure TP & Partial DP Attention #13646
- [x] Initial support for CP (CP + DP + EP, not compatible with TP)  #12065
- [x] CP optimization with fused moe/multi-batch/fp8 kvcache #13959 
- [x] TBO support  #14901
- [x] PP support & Optimization #15086 
- [x] CP+PP+TP https://github.com/sgl-project/sglang/issues/15358 #16380 
- [x]  Support TP for Indexer when DP is not enabled #19609 

### Kernel Optimization (Prior roadmap #11989)
- [x] DeepGeMM fp8_mqa_logits upgrade #13402
- [x]  Update flashmla to latest version #18902 (or nv_dev branch: #15211)
- [x] Update DeepGemm to latest version (or include nv_dev branch #13402)
- [x] Integrate FP8 per tensor sparse MLA kernel from trtllm(flashinfer) #18389 
- [x] Integrate BF16 per tensor sparse MLA kernel from trtllm(flashinfer) #16758 
- [ ] [Decode] Optimize dual stream in Indexer #13546 #16637
- [x] [Decode] Move deep_gemm.get_paged_mqa_logits_metadata to init time as metadata #15040
- [x] [Decode] Optimize _get_topk_paged where there are a lot of small kernels #15104 #17647
- [x] [Prefill] Optimize _get_topk_ragged where there are a lot of small kernels.  #19148 #19319
- [ ] [Prefill] Optimize with masked MHA kernels for sequence with ISL > 2k #14498 https://github.com/sgl-project/sgl-flash-attn/pull/24
- [x]  Allreduce+norm fusion #22390
- [ ]  Optimize Top-k kernel #16858 #17747
- [x]  Integrate BF16 in FP32 out DeepGemm kernel #19041 


### MTP
- [x] MTP (spec-v1) initial support #11652
- [x] Support pure TP+MTP #15088
- [x] Support Spec-V2 with overlap scheduler #15307
- [x] Reuse metadata for multi-step MTP #14781
- [x] Enable nextn = 2/4 in deep_gemm.fp8_paged_mqa_logits, which is faster than the current implementation which uses the kernel with nextn = 1 regardless of mtp size.
- [x] Apply decode dsa kernels in target verify and draft extend #16961
- [ ]  Support cuda graph for draft extend batch in Spec V2
- [x]  Kernel fusion in metadata preparation #19536


### GLM-5
- [ ] GLM-5 (G)B200 support tracker #19380
- [x] Apply trtllm sparse MLA kernel for GLM-5 model https://github.com/flashinfer-ai/flashinfer/pull/2607 #21783
- [x] Implement index cache #21286 
- [x] Support MHA for prefill batches #21332
- [x] Repetition Penalty #21258
- [x] Interleave Rope for GLM #21671


### Additional Features
- [x] Hi-cache support #17415
- [x] Piecewise cudagraph #23351 

### Others
- [x] Support of fp4 checkpoint after its release (on Blackwell) #17655
- [ ] Compatibility with PD disagg (MTP, TP, DP, EP) #14496
- [ ] ROCM optimization
- [ ] NPU optimization



## Related resources

- Model link: [DeepSeek V3.2](https://huggingface.co/deepseek-ai/DeepSeek-V3.2), [DeepSeek V3.2 Speciale](https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Speciale)
- Official document for DeepSeek V3.2 usage on SGLang: https://docs.sglang.io/basic_usage/deepseek_v32.html
- Bug tracking issue #14511
- Initial tracking issues for DeepSeek V3.2: #11060 #11100
- Prior issue for DSA kernel optimization: #11989


## Profiling command example

```
export SGLANG_TORCH_PROFILER_DIR=/sgl-workspace/sglang/profile/
python3 -m sglang.launch_server   --model-path deepseek-ai/DeepSeek-V3.2   --trust-remote-code   --tp-size 8 --dp-size 8 --enable-dp-attention   --tool-call-parser deepseekv32   --reasoning-parser deepseek-v3
# bs1
python3 -m sglang.bench_serving --model deepseek-ai/DeepSeek-V3.2 --dataset-name random --backend sglang-oai --random-range-ratio 1 --random-input-len 1200 --random-output-len 20 --max-concurrency 1 --num-prompts 5 --profile
# bs32
python3 -m sglang.bench_serving --model deepseek-ai/DeepSeek-V3.2  --dataset-name random --backend sglang-oai --random-range-ratio 1 --random-input-len 1200 --random-output-len 20 --max-concurrency 32 --num-prompts 32 --profile
```

## Long context performance 

Here is the performance comparison between DeepSeek V3.1 and V3.2 on long context lengths. (Collected by @XucSh)

<img width="719" height="305" alt="Image" src="https://github.com/user-attachments/assets/7b071688-ed8c-4c9b-aee5-489fca41af87" />

<img width="3442" height="1398" alt="Image" src="https://github.com/user-attachments/assets/127ef471-eb4d-4c0e-9d60-bd2c62dcd979" />

From the figure, we can see that DeepSeek V3.2 shows advantage under long context like 32k, and PP helps a lot with latency.


## Benchmark data (Updated on 02/13)

Here is the nightly performance data collected on 02/13, 8*B200 (https://github.com/sgl-project/sglang/actions/runs/21970073988)

<img width="1258" height="852" alt="Image" src="https://github.com/user-attachments/assets/93c099ab-8485-4b3b-97a5-5ab9c09e96ce" />

<img width="1303" height="600" alt="Image" src="https://github.com/user-attachments/assets/e7944a36-a98e-4479-b162-78470be617a5" />
