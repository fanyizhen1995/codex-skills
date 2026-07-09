---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix GLM-5.2 MTP Quark excludes'
canonical_url: https://github.com/sgl-project/sglang/pull/30265
captured_at: '2026-07-08T23:36:33.785940+00:00'
content_hash: b7bd0b9838cf19cbb5e4d50fc0bf3d169298f6c64b9d17f23e74f1b092b647f8
---
# [AMD] Fix GLM-5.2 MTP Quark excludes

URL: https://github.com/sgl-project/sglang/pull/30265
State: closed
Labels: amd, deepseek, run-ci
Closed at: 2026-07-08T21:57:11Z
Merged at: 2026-07-08T21:57:11Z

Co-author: @Raiden-Makoto 

## Summary

This PR fixes GLM-5.2 MXFP4 MTP/NextN loading with Quark quantization.

GLM-5.2 uses `GlmMoeDsaForCausalLM`, but its draft/MTP path currently reuses the DeepSeek NextN implementation. Quark records MTP excluded weights under the checkpoint prefix `model.layers.78.*`, while SGLang builds the draft runtime modules under `model.*`, `model.decoder.*`, and the fused MoE prefix `model.decoder.mlp.experts`.

Because of this prefix and granularity mismatch, Quark `exclude_layers` can fail to match bf16 MTP weights. Some MTP modules may then be incorrectly built as MXFP4 parameters, causing shape mismatches when loading bf16 weights.

This issue matches the MTP prefix mismatch described in Wafer's GLM-5.2 AMD writeup: https://www.wafer.ai/blog/glm52-amd.

## What Changed

- Added a GLM-specific NextN class: `GlmMoeDsaForCausalLMNextN`.
- Routed GLM DSA draft models from `GlmMoeDsaForCausalLM` to `GlmMoeDsaForCausalLMNextN` instead of `DeepseekV3ForCausalLMNextN`.
- Extracted DeepSeek NextN quant-config handling into `_resolve_nextn_quant_config()` so GLM can override the behavior cleanly.
- Expanded Quark `exclude_layers` at runtime for GLM-5.2 MTP:
  - `model.layers.78.eh_proj` -> `model.eh_proj`
  - `model.layers.78.enorm` -> `model.enorm`
  - `model.layers.78.hnorm` -> `model.hnorm`
  - `model.layers.78.shared_head.norm` -> `model.shared_head.norm`
  - decoder block weights -> `model.decoder.*`
  - routed expert leaf excludes also add the coarse fused-MoE prefix `model.decoder.mlp.experts`

This keeps mixed quantization behavior: excluded MTP modules remain bf16, while non-excluded draft modules can still use their Quark quant config.

## Why This Is Needed

The existing DeepSeek NextN mapper only handles:

```text
model.layers.61 -> model.decoder
```

GLM-5.2 MTP uses:

```text
model.layers.78
```

Also, the fused routed experts module is queried by SGLang using the coarse runtime prefix:

```text
model.decoder.mlp.experts
```

but Quark may record expanded leaf names such as:

```text
model.layers.78.mlp.experts.0.gate_proj
model.layers.78.mlp.experts.0.up_proj
model.layers.78.mlp.experts.0.down_proj
```

Mapping only the leaf names is not enough, because the fused MoE module checks the coarse module prefix. This PR adds the runtime names that SGLang actually queries.

## Validation

Tested with GLM-5.2 MXFP4 on 4 AMD GPUs.

Without MTP:

```text
Output throughput: 49.15 tok/s
Mean TPOT:         19.58 ms
Mean E2E latency:  30515.29 ms
```

With MTP:

```text
Output throughput: 180.70 tok/s
Mean TPOT:         4.75 ms
Mean E2E latency:  8297.65 ms
Accept length:     5.94
```

Observed improvement:

```text
Output throughput: ~3.68x higher
TPOT:              ~4.12x lower
E2E latency:       ~3.68x lower
```

TTFT remains roughly unchanged, which is expected because MTP primarily accelerates the decode phase rather than prefill.

## Test Commands

Server without MTP:

```bash
HIP_VISIBLE_DEVICES=0,1,2,3 sglang serve \
  --model-path amd/GLM-5.2-MXFP4 \
  --trust-remote-code \
  --tensor-parallel-size 4 \
  --host 0.0.0.0 \
  --port 30000
```

Server with MTP:

```bash
HIP_VISIBLE_DEVICES=0,1,2,3 sglang serve \
  --model-path amd/GLM-5.2-MXFP4 \
  --trust-remote-code \
  --tensor-parallel-size 4 \
  --speculative-algorithm EAGLE \
  --speculative-num-steps 5 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 6 \
  --host 0.0.0.0 \
  --port 30001
```

Benchmark command:

```bash
python -m sglang.bench_serving \
  --backend sglang \
  --host 127.0.0.1 \
  --port <PORT> \
  --model amd/GLM-5.2-MXFP4 \
  --tokenizer amd/GLM-5.2-MXFP4 \
  --dataset-name random \
  --random-input-len 10000 \
  --random-output-len 1500 \
  --random-range-ratio 1.0 \
  --num-prompts 8 \
  --request-rate inf \
  --max-concurrency 1 \
  --warmup-requests 1
```

## Reference

Wafer GLM-5.2 AMD performance writeup:

https://www.wafer.ai/blog/glm52-amd

## Related Work

Part of the generic DeepSeek NextN quant-config handling overlaps with the earlier fix proposed in #29781. This PR builds on that direction and extends it for GLM-5.2 by adding `GlmMoeDsaForCausalLMNextN`, GLM-specific runtime prefix remapping, fused MoE exclude handling, and `layer_quant_config` key remapping.

The ROCm draft-depth `cuda_runtime.h` guard mentioned in the Wafer writeup was already addressed by #29373.








































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28928760909](https://github.com/sgl-project/sglang/actions/runs/28928760909)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28929421551](https://github.com/sgl-project/sglang/actions/runs/28929421551)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
