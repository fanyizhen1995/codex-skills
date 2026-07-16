---
source_id: sglang-github-closed-issues-prs
title: '[Playground] Verified cell: mi355x / pro / fp4 / high-throughput / single'
canonical_url: https://github.com/sgl-project/sglang/issues/31010
captured_at: '2026-07-14T23:40:21.661530+00:00'
content_hash: 4877bb97fd42ccd3ab9534190b30d6a3fa2b44929f69a05297320ac691139be5
---
# [Playground] Verified cell: mi355x / pro / fp4 / high-throughput / single

URL: https://github.com/sgl-project/sglang/issues/31010
State: closed
Labels: 
Closed at: 2026-07-14T05:29:30Z
Merged at: 

### Cookbook model

deepseek-ai/deepseek-v4

### Combination

mi355x / pro / fp4 / high-throughput / single

### Proposed cell snippet

```javascript
{
      match: { hw: "mi355x", variant: "pro", quant: "fp4", strategy: "high-throughput", nodes: "single" },
      verified: true,
      env: [
        "SGLANG_USE_ROCM700A=0",
        "SGLANG_DP_USE_GATHERV=1",
        "SGLANG_HACK_FLASHMLA_BACKEND=unified_kv_triton",
        "AITER_BF16_FP8_MOE_BOUND=0",
      ],
      flags: [
        "--trust-remote-code",
        "--model-path {{MODEL_NAME}}",
        "--tp 8",
        "--dp 8",
        "--enable-dp-attention",
        "--enable-prefill-delayer",
        "--prefill-delayer-max-delay-ms 5000",
        "--attention-backend dsv4",
        "--page-size 256",
        "--mem-fraction-static 0.90",
        "--swa-full-tokens-ratio 0.1",
        "--disable-shared-experts-fusion",
        "--kv-cache-dtype fp8_e4m3",
        "--chunked-prefill-size 65536",
        "--speculative-algorithm EAGLE",
        "--speculative-num-steps 3",
        "--speculative-eagle-topk 1",
        "--speculative-num-draft-tokens 4",
        "--enable-hierarchical-cache",
        "--hicache-ratio 4",
        "--hicache-write-policy write_through",
        "--hicache-io-backend direct",
        "--hicache-mem-layout page_first_direct",
        "--host {{HOST_IP}}",
        "--port {{PORT}}",
      ],
    },
```

### Existing cell at this match (for diff)

```javascript
{
      match: { hw: "mi355x", variant: "pro", quant: "fp4", strategy: "high-throughput", nodes: "single" },
      verified: true,
      env: [
        "SGLANG_USE_ROCM700A=0",
        "SGLANG_DP_USE_GATHERV=1",
        "SGLANG_HACK_FLASHMLA_BACKEND=unified_kv_triton",
        "AITER_BF16_FP8_MOE_BOUND=0",
      ],
      flags: [
        "--trust-remote-code",
        "--model-path {{MODEL_NAME}}",
        "--tp 8",
        "--dp 8",
        "--enable-dp-attention",
        "--enable-prefill-delayer",
        "--prefill-delayer-max-delay-ms 5000",
        "--attention-backend dsv4",
        "--page-size 256",
        "--mem-fraction-static 0.90",
        "--swa-full-tokens-ratio 0.1",
        "--disable-shared-experts-fusion",
        "--kv-cache-dtype fp8_e4m3",
        "--chunked-prefill-size 65536",
        "--speculative-algorithm EAGLE",
        "--speculative-num-steps 3",
        "--speculative-eagle-topk 1",
        "--speculative-num-draft-tokens 4",
        "--host {{HOST_IP}}",
        "--port {{PORT}}",
      ],
    },
```

### SGLang version

sglang-rocm:v0.5.14-rocm720-mi35x-20260710

### Benchmark result (optional but encouraged)

_No response_

### Notes / caveats

--enable-hierarchical-cache \
--hicache-ratio 4 \
--hicache-write-policy write_through \
--hicache-io-backend direct \
--hicache-mem-layout page_first_direct

### Attestation

- [x] I ran this exact command on the listed hardware.
- [x] The server reached READY and answered a cURL request successfully.
- [x] Output looked correct on at least one prompt.
