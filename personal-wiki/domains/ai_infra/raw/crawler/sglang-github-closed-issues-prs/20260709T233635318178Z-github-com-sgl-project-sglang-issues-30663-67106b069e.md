---
source_id: sglang-github-closed-issues-prs
title: 'GLM-5.2 FP8 DP-attention serve crashes during KV pool init: missing get_attention_cp_size
  import'
canonical_url: https://github.com/sgl-project/sglang/issues/30663
captured_at: '2026-07-09T23:36:35.318178+00:00'
content_hash: 67106b069e793fb8b42208e7d9b46cd77ff1c6c9ea1902e05c9a12cdd8089320
---
# GLM-5.2 FP8 DP-attention serve crashes during KV pool init: missing get_attention_cp_size import

URL: https://github.com/sgl-project/sglang/issues/30663
State: closed
Labels: 
Closed at: 2026-07-09T18:22:36Z
Merged at: 

### Summary

Serving `zai-org/GLM-5.2-FP8` with the single-node high-throughput cookbook shape crashes during scheduler initialization while sizing the KV pool.

This appears independent of speculative decoding: I reproduced it with all speculative decoding flags removed (`speculative_algorithm=None`).

### Public recipe used

From the GLM-5.2 cookbook high-throughput single-node recipe:

https://docs.sglang.io/cookbook/autoregressive/GLM/GLM-5.2#hw=h200&variant=default&quant=fp8&strategy=high-throughput&nodes=single

The relevant serve shape is:

```bash
sglang serve \
  --model-path zai-org/GLM-5.2-FP8 \
  --tp 8 \
  --dp 8 \
  --enable-dp-attention \
  --moe-a2a-backend deepep \
  --mem-fraction-static 0.85 \
  --max-running-requests 256 \
  --host 0.0.0.0 \
  --port 30000
```

### Observed result

All scheduler ranks die during initialization, after weights load and before the server becomes ready. The failing path is KV pool sizing:

```text
Scheduler hit an exception: Traceback (most recent call last):
  File "python/sglang/srt/managers/scheduler.py", line 4339, in run_scheduler_process
    scheduler = Scheduler(...)
  File "python/sglang/srt/managers/scheduler.py", line 421, in __init__
    self.init_model_worker()
  File "python/sglang/srt/managers/scheduler.py", line 848, in init_model_worker
    self.init_memory_pools()
  File "python/sglang/srt/managers/scheduler.py", line 821, in init_memory_pools
    self.init_target_memory_pool()
  File "python/sglang/srt/managers/tp_worker.py", line 335, in alloc_memory_pool
    self.model_runner.alloc_memory_pool(memory_pool_config)
  File "python/sglang/srt/model_executor/model_runner.py", line 845, in alloc_memory_pool
    self.init_memory_pool(self.pre_model_load_memory)
  File "python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 1463, in init_memory_pool
    self.memory_pool_config = self._resolve_memory_pool_config(...)
  File "python/sglang/srt/model_executor/model_runner_kv_cache_mixin.py", line 1428, in _config_from_budget
    configurator = create_memory_pool_configurator(self)
  File "python/sglang/srt/model_executor/pool_configurator.py", line 794, in create_memory_pool_configurator
    return DefaultPoolConfigurator(mr)
  File "python/sglang/srt/model_executor/pool_configurator.py", line 137, in __init__
    self._cell_size = self._compute_cell_size(mr, num_layers)
  File "python/sglang/srt/model_executor/pool_configurator.py", line 184, in _compute_cell_size
    effective_num_layers = get_glm_dsa_layer_split_effective_num_layers(mr, num_layers)
  File "python/sglang/srt/layers/cp/utils.py", line 91, in get_glm_dsa_layer_split_effective_num_layers
    from sglang.srt.layers.dp_attention import get_attention_cp_size
ImportError: cannot import name 'get_attention_cp_size' from 'sglang.srt.layers.dp_attention'
```

The top-level process then reports:

```text
RuntimeError: Rank 0 scheduler died during initialization (exit code: -3)
```

### Relevant logged args

The run had CP/layer-split disabled, so this import should not be required for this config:

```text
tp_size=8
dp_size=8
enable_dp_attention=True
attn_cp_size=1
enable_prefill_cp=False
cp_strategy=None
enable_dsa_cache_layer_split=False
speculative_algorithm=None
```

### Expected result

The cookbook high-throughput command should initialize successfully, or fail with a clear supported/unsupported configuration error. It should not crash on an internal missing import while CP and DSA cache layer split are disabled.

### Suspected cause

`python/sglang/srt/layers/cp/utils.py` imports `get_attention_cp_size` from `sglang.srt.layers.dp_attention` before checking `is_glm_dsa_cache_layer_split_enabled(model_runner)`.

In this checkout, `dp_attention.py` exposes `get_attention_dp_rank()` / `get_attention_dp_size()`, but not `get_attention_cp_size()`. The CP helpers appear to be represented by the attention CP group APIs in `distributed/parallel_state.py`, e.g. `get_attn_context_model_parallel_world_size()` and `get_attn_context_model_parallel_rank()`.

A likely fix is to return early before importing CP helpers when layer split is disabled, and/or update the import to the current CP helper API.

### Version

Observed on main commit:

```text
1df97bccc888411f043c2cde9eab890814e6e1a6
```

Python version in the trace: 3.12.
