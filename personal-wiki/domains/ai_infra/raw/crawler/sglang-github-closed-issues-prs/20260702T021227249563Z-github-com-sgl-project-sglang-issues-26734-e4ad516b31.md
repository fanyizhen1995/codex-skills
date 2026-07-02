---
source_id: sglang-github-closed-issues-prs
title: '[Bug] MiMo V2.5 + HiCache crashes with full/SWA KV geometry mismatch'
canonical_url: https://github.com/sgl-project/sglang/issues/26734
captured_at: '2026-07-02T02:12:27.249563+00:00'
content_hash: e4ad516b310ff4618455a2a6f65e39f622fee9d70c0a84f7f276fff58cf31fa4
---
# [Bug] MiMo V2.5 + HiCache crashes with full/SWA KV geometry mismatch

URL: https://github.com/sgl-project/sglang/issues/26734
State: closed
Labels: 
Closed at: 2026-07-01T07:59:29Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

Two bugs prevent MiMo V2 / V2.5 from working with `--enable-hierarchical-cache`.

---

#### Bug 1: Asymmetric K/V dimensions crash in device KV pool

MiMo uses `head_dim=128, v_head_dim=64`. The device KV pool allocates both K and V with `head_dim`, so V buffer is too small. This crashes at the first prefill when `set_kv_buffer` writes K data into the undersized V slot.

Full traceback (no MTP, `--hicache-io-backend kernel`):
```
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4025, in run_scheduler_process
    scheduler = Scheduler(...)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 437, in __init__
    self.init_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 718, in init_model_worker
    self.init_tp_model_worker()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 673, in init_tp_model_worker
    self.tp_worker = TpModelWorker(**worker_kwargs)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 262, in __init__
    self._init_model_runner()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 347, in _init_model_runner
    self._model_runner = ModelRunner(...)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 535, in __init__
    self.initialize(pre_model_load_memory)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 791, in initialize
    self.init_device_graphs()
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 738, in __init__
    raise Exception(
Exception: Capture cuda graph failed: shape mismatch: value tensor of shape [512, 2, 192] cannot be broadcast to indexing result of shape [512, 1, 192]
```

The immediate error is in `memory_pool.py`:
```
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/memory_pool.py", line 1073, in set_kv_buffer
    _set_kv_buffer_impl(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/memory_pool.py", line 119, in _set_kv_buffer_impl
    k_cache[indices] = k
RuntimeError: shape mismatch: value tensor of shape [512, 2, 192] cannot be broadcast to indexing result of shape [512, 1, 192]
```

`k_cache` was allocated with `v_head_dim=64` (1 head) but the actual K tensor has `head_dim=128` (2 heads). The root cause: `get_size_per_token()` computes `head_dim * head_num * layer_num * 2`, assuming K and V share the same dimension.

- `--hicache-io-backend kernel` and `direct` both crash identically (bug is in device KV pool allocation, not IO backend)
- `--disable-cuda-graph` lets initialization pass (HiCache D↔H initialized succeeds) but crashes on the first inference request with the same `set_kv_buffer` error: `[40, 2, 192] → [40, 1, 192]`
- The host KV pool (`memory_pool_host.py`) has the same symmetric assumption: `element_dim = head_num * head_dim`

Fix: `get_size_per_token()`, `init_kv_buffer()`, and host pool allocation must use `v_head_dim` for V.

---

#### Bug 2: MTP routes KV to wrong HiCache layer

`mimo_v2_nextn.py` hardcodes `layer_id=0` for the MTP block, but MTP uses SWA geometry while layer 0 in `hybrid_layer_pattern` is full-attention. When Bug 1 is patched, this causes a crash in `swa_memory_pool.py`:

```
  File "/sgl-workspace/sglang/python/sglang/srt/models/mimo_v2.py", line XXX, in forward
    hidden_states, residual = self.mtp_block(
  File "/sgl-workspace/sglang/python/sglang/srt/mem_cache/swa_memory_pool.py", line 183, in set_kv_buffer
    layer_id_pool, is_swa_layer = self.layers_mapping[layer_id]
```

MTP's KV write targets the full-attention pool (layer 0) instead of the SWA pool, and `layers_mapping` has no valid entry for this misrouted write.

**Note:** Bug 2 is not observable on unpatched upstream because Bug 1 crashes first. It was verified by applying a Bug-1-only patch ([gist](https://gist.github.com/junliu-mde/86826e3a8a21f6b1c2c4cc1cec1937b1)) that fixes the asymmetric K/V allocation but does **not** fix the MTP `layer_id`, then running with `--speculative-algo EAGLE`.

Fix: derive MTP's `layer_id` from `hybrid_layer_pattern` (first SWA layer index) instead of hardcoding 0.

---

### Reproduction

**Bug 1 only (no MTP):**
```bash
SGLANG_ENABLE_UNIFIED_RADIX_TREE=1 \
python3 -m sglang.launch_server \
  --model-path <path-to-MiMo-V2.5> \
  --tp 8 --trust-remote-code \
  --dp-size 2 --enable-dp-attention --enable-dp-lm-head \
  --mem-fraction-static 0.65 \
  --enable-hierarchical-cache --hicache-size 100 \
  --hicache-io-backend kernel --hicache-mem-layout layer_first \
  --hicache-write-policy write_through
```

**Bug 2 (requires Bug 1 patch first, then add EAGLE):**
```bash
# Apply Bug-1-only patch, then:
SGLANG_ENABLE_UNIFIED_RADIX_TREE=1 \
python3 -m sglang.launch_server \
  --model-path <path-to-MiMo-V2.5> \
  --tp 8 --trust-remote-code \
  --dp-size 2 --enable-dp-attention --enable-dp-lm-head \
  --mem-fraction-static 0.65 \
  --enable-hierarchical-cache --hicache-size 100 \
  --hicache-io-backend direct --hicache-mem-layout layer_first \
  --hicache-write-policy write_through \
  --speculative-algo EAGLE --speculative-num-steps 3 \
  --speculative-eagle-topk 1 --speculative-num-draft-tokens 4 \
  --enable-multi-layer-eagle
```

### Environment

```
SGLang version: v0.5.12.post1 / main
GPU: 8× H100 80GB
```
