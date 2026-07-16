---
source_id: sglang-github-closed-issues-prs
title: '[Playground] Verified cell: b300 / default / fp8 / high-throughput / single'
canonical_url: https://github.com/sgl-project/sglang/issues/30718
captured_at: '2026-07-10T23:37:20.316693+00:00'
content_hash: 954c26b6abf3cdd516d07ee05614dfcf2110fbd41206499b84d7f45f07219ea0
---
# [Playground] Verified cell: b300 / default / fp8 / high-throughput / single

URL: https://github.com/sgl-project/sglang/issues/30718
State: closed
Labels: 
Closed at: 2026-07-10T01:09:40Z
Merged at: 

### Cookbook model

zai-org/glm-5.2

### Combination

b300 / default / fp8 / high-throughput / single

### Proposed cell snippet

```javascript
{
      match: { hw: "b300", variant: "default", quant: "fp8", strategy: "high-throughput", nodes: "single" },
      verified: true,
      env: [],
      flags: [
        "--model-path {{MODEL_NAME}}",
        "--tp 8",
        "--dp 8",
        "--enable-dp-attention",
        "--moe-a2a-backend deepep",
        "--ep 4",
        "--mem-fraction-static 0.85",
        "--max-running-requests 256",
        "--reasoning-parser glm45",
        "--tool-call-parser glm47",
        "--host {{HOST_IP}}",
        "--port {{PORT}}",
      ],
    },
```

### Existing cell at this match (for diff)

```javascript
{
      match: { hw: "b300", variant: "default", quant: "fp8", strategy: "high-throughput", nodes: "single" },
      verified: true,
      env: [],
      flags: [
        "--model-path {{MODEL_NAME}}",
        "--tp 8",
        "--dp 8",
        "--enable-dp-attention",
        "--moe-a2a-backend deepep",
        "--mem-fraction-static 0.85",
        "--max-running-requests 256",
        "--host {{HOST_IP}}",
        "--port {{PORT}}",
      ],
    },
```

### SGLang version

sglang=0.5.4

### Benchmark result (optional but encouraged)

_No response_

### Notes / caveats

_No response_

### Attestation

- [x] I ran this exact command on the listed hardware.
- [x] The server reached READY and answered a cURL request successfully.
- [x] Output looked correct on at least one prompt.
