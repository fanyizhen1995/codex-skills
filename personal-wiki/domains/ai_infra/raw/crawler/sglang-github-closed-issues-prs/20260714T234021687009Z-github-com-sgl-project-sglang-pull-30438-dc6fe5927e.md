---
source_id: sglang-github-closed-issues-prs
title: Delete CUTLASS FP8 blockwise for SM90 and SM100, move SM120 to JIT and add
  SwapAB
canonical_url: https://github.com/sgl-project/sglang/pull/30438
captured_at: '2026-07-14T23:40:21.687009+00:00'
content_hash: dc6fe5927e60a6e24557897b43ac8eef88ec7eaab73770bb0d7207957c8184d2
---
# Delete CUTLASS FP8 blockwise for SM90 and SM100, move SM120 to JIT and add SwapAB

URL: https://github.com/sgl-project/sglang/pull/30438
State: closed
Labels: quant, sgl-kernel, blackwell, run-ci, jit-kernel, bypass-fastfail
Closed at: 2026-07-14T01:31:33Z
Merged at: 2026-07-14T01:31:33Z

## **Recommended migration plan**

- SM90 has DeepGEMM, which has better perf, more tile sizes
- SM100 has DeepGEMM (which has a lot better perf, more tile sizes) and also trtllm-gen.

Only SM120 needs this for now. Also, there has been no development on this kernel for 1 year+.

For future development (Rubin, etc), we'd use **Cute-DSL**. Ideally, some kernel experts can also help us migrate this one to Cute-DSL (as long as the perf is the same)

For M = 1 on `Qwen/Qwen3.6-27B-FP8`, speed increase from 42 to 46.76 TPS.

<img width="983" height="788" alt="Screenshot 2026-07-07 at 4 07 01 PM" src="https://github.com/user-attachments/assets/bd16ffb7-6495-4548-98d7-866506a0b025" />

And here is the difference of using StreamK scheduler on M >= 64 (when below this threshold, we currently use SwapAB to transpose the A and B operand for better MMA utilization)
<img width="1900" height="1900" alt="image" src="https://github.com/user-attachments/assets/74e77e28-8e2f-4f0d-9e33-049e3a27cda6" />















































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29298468640](https://github.com/sgl-project/sglang/actions/runs/29298468640)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29298468570](https://github.com/sgl-project/sglang/actions/runs/29298468570)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
