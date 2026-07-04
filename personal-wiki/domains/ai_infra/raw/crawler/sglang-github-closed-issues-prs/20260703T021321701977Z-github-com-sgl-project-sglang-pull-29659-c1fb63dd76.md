---
source_id: sglang-github-closed-issues-prs
title: '[LFM2-MoE] Support Transformers v5 packed MoE expert weights'
canonical_url: https://github.com/sgl-project/sglang/pull/29659
captured_at: '2026-07-03T02:13:21.701977+00:00'
content_hash: c1fb63dd765d6b199361318900d5a709ea5f92d2ba1990d863472c2ed7b78f88
---
# [LFM2-MoE] Support Transformers v5 packed MoE expert weights

URL: https://github.com/sgl-project/sglang/pull/29659
State: closed
Labels: run-ci
Closed at: 2026-07-02T09:13:02Z
Merged at: 2026-07-02T09:13:02Z

## What

Adds support for loading **LFM2-MoE** expert weights in the **Transformers ≥ v5.0 packed format** to `lfm2_moe.py`'s `load_weights`.

Transformers ≥ 5.0 ([huggingface/transformers#41580](https://github.com/huggingface/transformers/pull/41580), shipped in v5.0.0) packs MoE expert weights into a single 3D tensor per projection:

| | per-expert (pre-v5, on disk) | packed (Transformers v5 in-memory) |
|---|---|---|
| gate/up | `…experts.{i}.w1.weight`, `…experts.{i}.w3.weight` | `…experts.gate_up_proj` `[E, 2·I, H]` |
| down | `…experts.{i}.w2.weight` | `…experts.down_proj` `[E, H, I]` |

## Why we need this

The current loader only understands the per-expert names. When weights arrive in the **packed layout** — which is what an **in-memory Transformers v5 model** exposes in its `state_dict`, i.e. the **`update_weights_from_tensor` / RLHF (verl) weight-sync path** — the packed expert tensors match no name in the loader and are **silently dropped**. The experts stay uninitialised and the model emits garbage, with no error raised.

This is increasingly common: anyone doing RL / online weight updates on LFM2-MoE with a Transformers ≥ 5 training stack hits it. Plain on-disk inference is unaffected (pre-v5 checkpoints are still per-expert), which is why it slips through until the weight-sync path is exercised.

## Fix

Map the packed tensors onto the fused `FusedMoE` params per expert: `gate_up_proj → w13_weight` (split into w1/w3 halves), `down_proj → w2_weight`. The existing per-expert path is untouched, so pre-v5 on-disk checkpoints load exactly as before; the new block only triggers on the packed `experts.gate_up_proj` / `experts.down_proj` names.

LFM2-MoE packs **out-features-major** (`gate_up_proj` as `[E, 2·I, H]`), which already matches the `FusedMoE` `w13_weight`/`w2_weight` layout, so **no transpose** is needed (unlike GPT-OSS). Per-expert loading with an explicit integer `expert_id` is used because the whole-tensor `expert_id=None` fused path is gated to mxfp4-quantised models only — it would not work for unquantised bf16 LFM2-MoE.

## How to reproduce

A public fixture is provided: [`tugot17/LFM2-8B-A1B-5.2-packed`](https://huggingface.co/tugot17/LFM2-8B-A1B-5.2-packed) — `LFM2-8B-A1B` converted to the Transformers v5 packed format (authentic packed shapes: `gate_up_proj (32, 3584, 2048)`, `down_proj (32, 2048, 1792)`).

```bash
python -c "
import sglang as sgl
e = sgl.Engine(model_path='tugot17/LFM2-8B-A1B-5.2-packed', tp_size=1)
print(e.generate(['The capital of France is'], {'temperature': 0, 'max_new_tokens': 16}))
"
```

- **Without this patch:** `" – – – – – – – – – – …"` (garbage — experts dropped)
- **With this patch:** `" Paris. It is located in the northern part of the country, along the Seine"` — identical to loading the original per-expert `LiquidAI/LFM2-8B-A1B`.

### Backward compatibility

The old per-expert on-disk format was tested to confirm no regression — loading `LiquidAI/LFM2-8B-A1B` (per-expert) produces **byte-identical** output with and without this patch (the new block only fires on the packed `gate_up_proj`/`down_proj` names, so per-expert checkpoints take the unchanged path):

| loader | old per-expert ckpt | v5 packed ckpt |
|---|---|---|
| unpatched `main` | ✅ correct | 🔴 garbage |
| **patched (this PR)** | ✅ correct (identical) | ✅ correct |

Verified on MI325X / ROCm 7.2 against this branch (`sglang 0.5.15.dev`). The change itself is device/backend-agnostic — it only remaps weight names during loading.

Co-Authored-By: Changyi Yang <changyiyang2023@gmail.com>



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28386441288](https://github.com/sgl-project/sglang/actions/runs/28386441288)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28386441152](https://github.com/sgl-project/sglang/actions/runs/28386441152)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
