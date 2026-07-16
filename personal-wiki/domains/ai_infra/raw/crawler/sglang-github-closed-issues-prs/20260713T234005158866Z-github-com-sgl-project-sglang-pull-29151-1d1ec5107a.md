---
source_id: sglang-github-closed-issues-prs
title: Fix ModelOpt NVFP4 scalar scales for merged linears
canonical_url: https://github.com/sgl-project/sglang/pull/29151
captured_at: '2026-07-13T23:40:05.158866+00:00'
content_hash: 1d1ec5107a6aa42221e3546d9465e04b1f31c256658dfc044551b1db0f340866
---
# Fix ModelOpt NVFP4 scalar scales for merged linears

URL: https://github.com/sgl-project/sglang/pull/29151
State: closed
Labels: quant, blackwell, run-ci
Closed at: 2026-07-13T23:14:21Z
Merged at: 2026-07-13T23:14:21Z

## Summary

**TL;DR `nvidia/Phi-4-reasoning-plus-NVFP4` GSM8K score was `0.005` before this PR, and `0.945` after this PR.**

Fix fused-in-checkpoint scalar scale loading for `PerTensorScaleParameter` in QKV and merged-column linears.

ModelOpt NVFP4 dense checkpoints store `input_scale` and `weight_scale_2` as scalar tensors. SGLang still represents these scale parameters as one slot per logical output partition so split checkpoint tensors such as `gate_proj` and `up_proj` can load independent shard scales.

The bug is in the fused checkpoint path. For models like `nvidia/Phi-4-reasoning-plus-NVFP4`, the checkpoint stores fused tensors such as `qkv_proj.input_scale` and `gate_up_proj.input_scale`. In that case `loaded_shard_id is None`, and the scalar applies to the whole fused matrix. The old v2 loaders wrote that scalar only into slot 0, leaving the other slots uninitialized. Later, the shared ModelOpt NVFP4 post-load path reduced all slots with `.max()`, so an uninitialized slot could become the runtime global scale.

This PR keeps `ModelOptFp4LinearMethod` unchanged. Instead, it fixes the caller/loader behavior:

- For fused-in-checkpoint `MergedColumnParallelLinear` scalar scales, copy the scalar into every logical MLP slot.
- For fused-in-checkpoint `QKVParallelLinear` scalar scales, copy the scalar into q/k/v scale slots.
- For split checkpoint tensors loaded with explicit shard IDs, keep the existing independent per-shard behavior.

This matches vLLM's current handling: when a fused checkpoint scale is loaded into a `PerTensorScaleParameter`, vLLM fills all logical scale slots with the same scalar before later reduction.

## Root Cause

For `nvidia/Phi-4-reasoning-plus-NVFP4`, the checkpoint has scalar scales:

```text
model.layers.0.self_attn.qkv_proj.input_scale []
model.layers.0.self_attn.qkv_proj.weight_scale_2 []
model.layers.0.mlp.gate_up_proj.input_scale []
model.layers.0.mlp.gate_up_proj.weight_scale_2 []
```

Before this fix, SGLang loaded layer-0 `mlp.gate_up_proj` as:

```text
input_scale    = [0.0004650298, 0.8146172]
weight_scale_2 = [0.0005783808, 1.0]
```

Only the first value came from the checkpoint. The second value was an uninitialized logical slot. The shared ModelOpt NVFP4 code then computed:

```python
input_scale_2 = layer.input_scale.max().to(torch.float32)
weight_scale_2 = layer.weight_scale_2.max().to(torch.float32)
```

That produced `alpha = 0.8146172`, while vLLM and the checkpoint scalar imply `alpha = 2.6896427e-7`. The incorrect scale inflated the first layer MLP projection from RMS `0.10578` in vLLM to RMS `183.32649` in SGLang and caused garbage outputs.

For split-checkpoint models, the scale layout is different. For example, `nvidia/Llama-3.1-8B-Instruct-NVFP4` stores separate scalar MLP scales:

```text
model.layers.0.mlp.gate_proj.input_scale []
model.layers.0.mlp.gate_proj.weight_scale_2 []
model.layers.0.mlp.up_proj.input_scale []
model.layers.0.mlp.up_proj.weight_scale_2 []
```

Those tensors are loaded through explicit shard IDs (`0` for gate, `1` for up), so this PR intentionally leaves that path independent.

## Repro

Environment:

- GPU: B200
- Image: `lmsysorg/sglang:dev-cu13`
- SGLang base commit: `8e1988b746f7ee3072ea2b0199efb01d8273c2eb`
- Models:
  - `nvidia/Phi-4-reasoning-plus-NVFP4` (fused `gate_up_proj` scales)
  - `nvidia/Llama-3.1-8B-Instruct-NVFP4` (split `gate_proj` / `up_proj` scales)
- Server args:

```bash
python3 -m sglang.launch_server \
  --model <model> \
  --tp 1 \
  --trust-remote-code \
  --host 127.0.0.1 \
  --port 33841 \
  --random-seed 1234 \
  --disable-cuda-graph \
  --disable-piecewise-cuda-graph \
  --disable-flashinfer-autotune \
  --skip-server-warmup
```

Request:

```bash
curl -sS http://127.0.0.1:33841/generate \
  -H 'Content-Type: application/json' \
  -d '{"text":"The capital of France is","sampling_params":{"temperature":0,"max_new_tokens":1}}'
```

Before:

```json
{"text":" the","output_ids":[279]}
```

After:

```json
{"text":" Paris","output_ids":[12366]}
```

## GSM8K

Command:

```bash
python3 -m sglang.test.run_eval \
  --base-url http://127.0.0.1:<port> \
  --model <model> \
  --eval-name gsm8k \
  --api completion \
  --max-tokens 512 \
  --num-examples 200 \
  --num-threads 64 \
  --temperature 0
```

Results:

| model | scale layout | version | prompt output | GSM8K score | latency | output throughput |
|---|---|---:|---:|---:|---:|---:|
| `nvidia/Phi-4-reasoning-plus-NVFP4` | fused `gate_up_proj` | before | ` the` | `0.005` | `91.377 s` | `1120.638 tok/s` |
| `nvidia/Phi-4-reasoning-plus-NVFP4` | fused `gate_up_proj` | after | ` Paris` | `0.945` | `43.056 s` | `411.141 tok/s` |
| `nvidia/Llama-3.1-8B-Instruct-NVFP4` | split `gate_proj` / `up_proj` | before | ` a` | `0.615` | `32.691 s` | `536.901 tok/s` |
| `nvidia/Llama-3.1-8B-Instruct-NVFP4` | split `gate_proj` / `up_proj` | after | ` a` | `0.615` | `32.612 s` | `535.105 tok/s` |

For the Phi fused-scale model, the fix recovers accuracy. For the Llama split-scale model, accuracy and prompt output are unchanged, which verifies the explicit shard-load path is not collapsed by this change.

Current-head rerun after review updates (`ba79b7f1693f93c86ae947e5c2fd628f69a3cd30`):

| model | prompt output | GSM8K score | latency | output throughput |
|---|---:|---:|---:|---:|
| `nvidia/Phi-4-reasoning-plus-NVFP4` | ` Paris` | `0.945` | `42.212 s` | `419.357 tok/s` |
| `nvidia/Llama-3.1-8B-Instruct-NVFP4` | ` a` | `0.615` | `32.085 s` | `543.989 tok/s` |

## Testing

Added unit coverage for:

- Fused MLP scalar scale loads filling all logical slots.
- Fused QKV scalar scale loads filling all q/k/v slots.
- Explicit split-shard scale loads staying independent.

Local checks:

```bash
venv/bin/python -m py_compile \
  python/sglang/srt/layers/linear.py \
  test/registered/unit/layers/quantization/test_modelopt_nvfp4.py
```

```text
direct PerTensorScaleParameter slot checks passed
```


































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28940820581](https://github.com/sgl-project/sglang/actions/runs/28940820581)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28940820261](https://github.com/sgl-project/sglang/actions/runs/28940820261)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
