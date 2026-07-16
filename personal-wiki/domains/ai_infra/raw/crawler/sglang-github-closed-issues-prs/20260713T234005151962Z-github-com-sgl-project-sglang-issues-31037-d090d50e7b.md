---
source_id: sglang-github-closed-issues-prs
title: 'Bug: DSV4 NVFP4 serving crashes - _DeepseekV4ConfigAlias not registered with
  HuggingFace CONFIG_MAPPING'
canonical_url: https://github.com/sgl-project/sglang/issues/31037
captured_at: '2026-07-13T23:40:05.151962+00:00'
content_hash: d090d50e7b42018e0e989d83de5855024555bd5e894135b60015bbd20f266aef
---
# Bug: DSV4 NVFP4 serving crashes - _DeepseekV4ConfigAlias not registered with HuggingFace CONFIG_MAPPING

URL: https://github.com/sgl-project/sglang/issues/31037
State: closed
Labels: 
Closed at: 2026-07-13T13:27:21Z
Merged at: 

### Bug: DSV4 NVFP4 serving crashes on SM121 — `_DeepseekV4ConfigAlias` not registered with HuggingFace `CONFIG_MAPPING`

**SGLang**: v0.5.15 (tagged)
**Transformers**: 5.12.1
**Hardware**: NVIDIA GB10 / SM121 / DGX Spark / CUDA 13.2

## Crash

```
[2026-07-13] DeepseekV4ForCausalLM has no SGLang implementation, falling back to Transformers implementation.
[2026-07-13] Using Transformers backend.
[2026-07-13] Scheduler hit an exception:
  File "sglang/srt/models/transformers.py", line 617, in __init__
    self.model: PreTrainedModel = AutoModel.from_config(...)
  File "transformers/models/auto/auto_factory.py", line 252, in from_config
    raise ValueError("Unrecognized configuration class ... _DeepseekV4ConfigAlias ... for this kind of AutoModel")
ValueError: Unrecognized configuration class ...
```

## Root Cause

`sglang/srt/utils/common.py` line 144-148 creates `_DeepseekV4ConfigAlias` and registers it in SGLang's internal `_CONFIG_REGISTRY`:

```python
class _DeepseekV4ConfigAlias(_HFDeepseekV3Config):
    model_type = "deepseek_v4"

_CONFIG_REGISTRY["deepseek_v32"] = _DeepseekV32ConfigAlias
_CONFIG_REGISTRY["deepseek_v4"] = _DeepseekV4ConfigAlias
```

However, `_CONFIG_REGISTRY` is **never synced to HuggingFace's `CONFIG_MAPPING`**. When SGLang falls back to the `Transformers` backend (`sglang/srt/models/transformers.py:617`), it calls `AutoModel.from_config(self.config, ...)`. The config is a `_DeepseekV4ConfigAlias` instance with `model_type="deepseek_v4"`, but transformers 5.12.1's `CONFIG_MAPPING` has no entry for `"deepseek_v4"`.

## Fix

Either:
1. Register `_DeepseekV4ConfigAlias` with `AutoConfig.register("deepseek_v4", _DeepseekV4ConfigAlias)` in addition to `_CONFIG_REGISTRY`
2. Or set `config.model_type = "deepseek_v3"` (which IS in CONFIG_MAPPING) and override defaults in `model_config.py` post-load (as the comment at line 137 already says)

## Reproduction

```bash
docker run --rm --gpus all --network host --privileged \
  xomoxcc/dgx-spark-sglang:0.5.15-sm121 \
  sglang serve --model-path /path/to/DeepSeek-V4-Flash-NVFP4
```

Works on B200/SM100 (upstream-validated) but crashes on GB10/SM121.
