---
source_id: sglang-github-closed-issues-prs
title: 'amd/deepseek_v4: register _DeepseekV4ConfigAlias (sync from main)'
canonical_url: https://github.com/sgl-project/sglang/pull/25296
captured_at: '2026-07-11T23:37:37.775126+00:00'
content_hash: c7f6c8568c4d1d2c28b152a915881d783fee225b0af11b8ec33d8d54648bb9f9
---
# amd/deepseek_v4: register _DeepseekV4ConfigAlias (sync from main)

URL: https://github.com/sgl-project/sglang/pull/25296
State: closed
Labels: 
Closed at: 2026-05-20T06:37:14Z
Merged at: 

## Problem

On `amd/deepseek_v4`, `hf_transformers/common.py` only registers `_DeepseekV32ConfigAlias`. With a recent transformers (v5.6+), `AutoTokenizer.from_pretrained` for a DSv4 checkpoint falls back to a generic `PreTrainedConfig` and raises:

```
AttributeError: 'PreTrainedConfig' object has no attribute 'max_position_embeddings'
  at transformers/modeling_rope_utils.py:standardize_rope_params
  <- AutoTokenizer.from_pretrained
  <- sglang/srt/utils/hf_transformers/tokenizer.py:_auto_tokenizer_from_pretrained
```

`_load_deepseek_v4_model` already handles the model-loading AutoConfig path, but tokenizer init does not go through it — it calls `AutoTokenizer.from_pretrained` directly, which internally re-resolves AutoConfig and trips the rope normalization branch when `deepseek_v4` is not in the registry.

## Fix

Register `_DeepseekV4ConfigAlias` (subclass of `DeepseekV3Config`) under `model_type = "deepseek_v4"`, exactly like upstream main does (added in #23882, plus `kimi_k2` in the same hunk). Mirrors the existing V3.2 alias on this branch — smallest possible diff, +5 lines.

V4-specific default-value divergences continue to be handled in `model_config.py` post-load (same as on main).

## Repro

`rocm/sgl-dev:rocm720-mi35x-721f045-20260513-DSv4` image serving `DeepSeek-V4-Flash` via sglang on 8x MI350X — without this patch, server fails during tokenizer init; with this patch, tokenizer succeeds and the server boots end-to-end.

## Test plan

- [x] `python -c "import sglang"` still imports cleanly
- [x] DSv4-Flash boot on 8x MI350X passes tokenizer init
- [x] End-to-end `/v1/completions` returns correct output
