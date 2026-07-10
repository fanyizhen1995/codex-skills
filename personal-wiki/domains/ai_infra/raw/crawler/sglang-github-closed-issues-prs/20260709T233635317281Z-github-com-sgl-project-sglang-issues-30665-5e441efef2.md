---
source_id: sglang-github-closed-issues-prs
title: '[Bug] ImportError: cannot import name ''get_attention_cp_size'' from dp_attention
  when using GLM-5.2 with speculative decoding'
canonical_url: https://github.com/sgl-project/sglang/issues/30665
captured_at: '2026-07-09T23:36:35.317281+00:00'
content_hash: 5e441efef2a0007a8b6744a6eaecfb0472e2c5a603f24bdf9043178b753f851d
---
# [Bug] ImportError: cannot import name 'get_attention_cp_size' from dp_attention when using GLM-5.2 with speculative decoding

URL: https://github.com/sgl-project/sglang/issues/30665
State: closed
Labels: 
Closed at: 2026-07-09T18:22:36Z
Merged at: 

## Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

## Describe the bug

Launching the server with GLM-5.2-NVFP4 crashes during scheduler initialization with:

```
ImportError: cannot import name 'get_attention_cp_size' from 'sglang.srt.layers.dp_attention'
```

The function `get_attention_cp_size` was removed from `dp_attention.py` in PR #30492, but the import in `python/sglang/srt/layers/cp/utils.py:91` (inside `get_glm_dsa_layer_split_effective_num_layers`) was not migrated to use `get_parallel().attn_cp_size`.

## Reproduction

```bash
sglang serve \
  --model nvidia/GLM-5.2-NVFP4 \
  --tp 8 \
  --quantization modelopt_fp4 \
  --speculative-algo EAGLE \
  --speculative-num-steps 5 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 6 \
  --trust-remote-code
```

Full traceback:

```
[2026-07-09 12:41:15 TP0] Scheduler hit an exception: Traceback (most recent call last):
  File "python/sglang/srt/managers/scheduler.py", line 4345, in run_scheduler_process
    scheduler = Scheduler(
  File "python/sglang/srt/managers/scheduler.py", line 422, in __init__
    self.init_model_worker()
  File "python/sglang/srt/managers/scheduler.py", line 853, in init_model_worker
    self.init_memory_pools()
  File "python/sglang/srt/managers/scheduler.py", line 826, in init_memory_pools
    self.init_target_memory_pool()
  File "python/sglang/srt/managers/scheduler.py", line 822, in init_target_memory_pool
    self.tp_worker.alloc_memory_pool()
  File "python/sglang/srt/managers/tp_worker.py", line 335, in alloc_memory_pool
    self.model_runner.alloc_memory_pool(memory_pool_config)
  File "python/sglang/srt/model_executor/model_runner.py", line 845, in alloc_memory_pool
    self.init_memory_pool(self.pre_model_load_memory)
  File "python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 1463, in init_memory_pool
    self.memory_pool_config = self._resolve_memory_pool_config(
  File "python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 1448, in _resolve_memory_pool_config
    config = self._config_from_budget(available_bytes)
  File "python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 1428, in _config_from_budget
    configurator = create_memory_pool_configurator(self)
  File "python/sglang/srt/model_executor/pool_configurator.py", line 794, in create_memory_pool_configurator
    return DefaultPoolConfigurator(mr)
  File "python/sglang/srt/model_executor/pool_configurator.py", line 137, in __init__
    self._cell_size = self._compute_cell_size(mr, num_layers)
  File "python/sglang/srt/model_executor/pool_configurator.py", line 184, in _compute_cell_size
    effective_num_layers = get_glm_dsa_layer_split_effective_num_layers(
  File "python/sglang/srt/layers/cp/utils.py", line 91, in get_glm_dsa_layer_split_effective_num_layers
    from sglang.srt.layers.dp_attention import get_attention_cp_size
ImportError: cannot import name 'get_attention_cp_size' from 'sglang.srt.layers.dp_attention'
```

## Environment

8xB200
