---
source_id: sglang-github-closed-issues-prs
title: '[NPU]Add support --pre-warm-nccl'
canonical_url: https://github.com/sgl-project/sglang/pull/30312
captured_at: '2026-07-07T23:35:30.912566+00:00'
content_hash: 78f15bbad5cd6b92b0e0343e35f71b0229193c429a58790671c6ec80a230c37a
---
# [NPU]Add support --pre-warm-nccl

URL: https://github.com/sgl-project/sglang/pull/30312
State: closed
Labels: run-ci
Closed at: 2026-07-07T09:17:30Z
Merged at: 2026-07-07T09:17:30Z

> Motivation



> ## Motivation
> When using multi-GPU tensor parallelism (TP > 1), the first collective communication operation triggers HCCL communicator initialization, causing **severe P99 TTFT degradation** for the first 2-3 requests.
> 
> This PR implements **HCCL pre-warming** during server startup to eliminate cold-start latency.

> **Measured Impact on Ascend A3**:
> 
> * **P99 TTFT improvement**: 61.4% (4197.49ms → 1620.13ms)
> 
> ## Accuracy Tests
> **No accuracy impact** - latency optimization only, does not affect model outputs.
> 
> Validated with GSM8K (100 questions):
> 
> * Without pre-warm: 93.0%
> * With pre-warm: 92.0%
> 
> ## Benchmarking
> ### Test Environment
> * **Platform**: Ascend A3
> * **Model**: Qwen3-30B-A3B
> * **Configuration**: TP=4, random-input-len=3500,  random-output-len=1500
> 
### Results
**Without pre-warm**
<img width="547" height="711" alt="1" src="https://github.com/user-attachments/assets/035d864d-a029-4f7e-b8a4-8f939302f268" />

**With pre-warm**  
<img width="566" height="703" alt="2" src="https://github.com/user-attachments/assets/716b69b8-8697-4075-8851-77a48d4015f8" />


































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28836831631](https://github.com/sgl-project/sglang/actions/runs/28836831631)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28836831571](https://github.com/sgl-project/sglang/actions/runs/28836831571)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
