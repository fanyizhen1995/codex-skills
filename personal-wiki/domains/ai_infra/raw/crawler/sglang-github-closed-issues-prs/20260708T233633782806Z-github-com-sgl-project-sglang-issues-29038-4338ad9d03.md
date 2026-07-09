---
source_id: sglang-github-closed-issues-prs
title: '[BUG] DeepSeek-V4 FP8 wo_a DeepGEMM path can lower accuracy on Blackwell'
canonical_url: https://github.com/sgl-project/sglang/issues/29038
captured_at: '2026-07-08T23:36:33.782806+00:00'
content_hash: 4338ad9d03df0230e9924ea4c537afc80aee9a2ee1f46b44a58e4188f2c10d86
---
# [BUG] DeepSeek-V4 FP8 wo_a DeepGEMM path can lower accuracy on Blackwell

URL: https://github.com/sgl-project/sglang/issues/29038
State: closed
Labels: deepseek
Closed at: 2026-07-08T00:41:01Z
Merged at: 

## Summary

SGLang can show lower benchmark accuracy than vLLM for DeepSeek-V4-Flash W4A8 on Blackwell / SM100. This issue uses GPQA Diamond as the concrete reproducer, but the problem is not GPQA-specific.

The suspected cause is the FP8 `wo_a` activation scale layout passed to `deep_gemm.fp8_einsum` in `python/sglang/srt/models/deepseek_v4.py`. Since this path can change model logits during inference, the bug causes low accuracy across downstream evaluations. We have confirmed this on GPQA, AIME25, and SWE-Bench; after applying the layout fix, accuracy recovered on these evaluations.

Fix PR: https://github.com/sgl-project/sglang/pull/29036

## Suspected Root Cause

The current FP8 `wo_a` path quantizes `o: [T, G, D]` by flattening it into `[T * G, D]`, then views the packed UE8M0 scales back as `[T, G, -1]`.

On the SM100 DeepGEMM FP8 einsum path, this can mismatch activation scales with groups and cause early logit divergence. PR #29036 changes the quantization/scale layout to preserve group-major semantics.

## Impact

This is an inference correctness issue, not only a GPQA-specific regression. The incorrect FP8 `wo_a` scale layout introduces logit divergence in the DeepGEMM path, so benchmarks and workloads that depend on stable reasoning, code generation, or action generation can be affected.

GPQA is used here because it is a small and repeatable benchmark where we observed a clear accuracy gap and recovery after the layout fix. We have also reproduced low-accuracy symptoms on AIME25 and SWE-Bench, and after applying the same layout fix, accuracy recovered on those evaluations as well.

Confirmed affected evaluations include:

- GPQA
- AIME25
- SWE-Bench

Other math, reasoning, coding, and agentic benchmarks may also be affected by the same inference correctness issue.

## Environment

- Model: DeepSeek-V4-Flash W4A8
- Hardware: Blackwell / SM100
- SGLang baseline: `v0.5.12.post1`
- Reproducer dataset: GPQA Diamond, 198 examples

## Server Command

Baseline and patched SGLang used the same server arguments. The patched build used `PYTHONPATH=/path/to/sglang-pr/python:$PYTHONPATH`.

```bash
export SGLANG_OPT_DEEPGEMM_MEGA_MOE_NUM_MAX_TOKENS_PER_RANK=8320

sglang serve \
  --trust-remote-code \
  --model-path /path/to/DeepSeek-V4-Flash \
  --tp 2 \
  --dp 1 \
  --enable-dp-attention \
  --moe-a2a-backend megamoe \
  --host 0.0.0.0 \
  --port 31000
```

## Reproducer Test Command (GPQA)

Full GPQA was run three times for each build/server:

```bash
sgl-eval run gpqa \
  --model /path/to/DeepSeek-V4-Flash \
  --api-key EMPTY \
  --base-url http://localhost:31000/v1 \
  --from-dataset /path/to/gpqa_diamond.jsonl \
  --num-threads 16 \
  --n-repeats 1 \
  --max-tokens 200000 \
  --temperature 0.0 \
  --top-p 1.0 \
  --thinking
```

## GPQA Reproducer Results

The following GPQA numbers are one concrete reproducer for the broader inference-accuracy issue.

| System | GPQA scores from 3 runs | Mean |
| --- | --- | ---: |
| vLLM baseline | 0.863636, 0.858586, 0.873737 | 0.865320 |
| SGLang before fix | 0.843434, 0.828283, 0.833333 | 0.835017 |
| SGLang after PR #29036 | 0.883838, 0.863636, 0.863636 | 0.870370 |

After the layout fix, SGLang recovered to the vLLM baseline range on this GPQA reproducer. We have also confirmed recovery on AIME25 and SWE-Bench after the same fix.
