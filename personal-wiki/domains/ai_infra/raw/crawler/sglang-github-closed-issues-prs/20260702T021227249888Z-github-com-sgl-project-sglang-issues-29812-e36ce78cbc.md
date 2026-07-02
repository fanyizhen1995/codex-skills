---
source_id: sglang-github-closed-issues-prs
title: '[Bug] Decode server hangs at warmup with UnifiedRadixCache + HiCache + enable
  decode radix cache'
canonical_url: https://github.com/sgl-project/sglang/issues/29812
captured_at: '2026-07-02T02:12:27.249888+00:00'
content_hash: e36ce78cbc16731b1c6498518a68038c8b83816a571df907e115b3bdd6cd77af
---
# [Bug] Decode server hangs at warmup with UnifiedRadixCache + HiCache + enable decode radix cache

URL: https://github.com/sgl-project/sglang/issues/29812
State: closed
Labels: 
Closed at: 2026-07-01T07:36:38Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When launching a **decode-mode** server (`--disaggregation-mode decode`) that uses `UnifiedRadixCache` (env `SGLANG_ENABLE_UNIFIED_RADIX_TREE=1`) together with `--enable-hierarchical-cache` and `--disaggregation-decode-enable-radix-cache`, the server never becomes ready. The `disaggregation warmup` request enqueues onto the decode prealloc queue, is admitted, but then stays stuck in `KVPoll.Success + hicache_restore_status=PENDING` forever, so the request never migrates from the transfer queue to the running batch. The server's `/health` endpoint returns 503 for the whole 30-minute `HEALTH_CHECK_TIMEOUT` window and the launcher eventually gives up.

Root cause: `decode_hicache_mixin._process_hicache_local_restores` uses `hasattr(tree_cache, "is_load_back_event_done")` as a guard. `HiRadixCache` implements this method, but `UnifiedRadixCache` does not. Because the guard fails, the mixin early-returns without ever advancing `hicache_restore_status` from `PENDING → READY`. The upstream `HiCacheRestoreGatedKVReceiver.poll()` then keeps returning `KVPoll.Transferring` (not `KVPoll.Success`) as long as `restore_status == PENDING`, so the request never gets committed by `_commit_transfer_to_req`. The FAKE-bootstrap warmup req deadlocks; every real disagg-decode request that needs an L2 host restore would deadlock the same way in production.

Fix: implement `UnifiedRadixCache.is_load_back_event_done(consumer_index)` mirroring `HiRadixCache.is_load_back_event_done`. It queries the current layer's `finish_event` and calls `loading_check()` when done.

```python
def is_load_back_event_done(self, consumer_index: int) -> bool:
    if self.cache_controller is None or consumer_index < 0:
        return True
    finish_event = self.cache_controller.layer_done_counter.events[
        consumer_index
    ].finish_event
    if not finish_event.query():
        return False
    self.loading_check()
    return True
```

### Reproduction

```bash
# Decode server with UnifiedRadixCache + HiCache + decode-radix
SGLANG_ENABLE_UNIFIED_RADIX_TREE=1 \
SGLANG_ENABLE_DSV4_DECODE_RADIX=1 \
SGLANG_DSV4_FP4_EXPERTS=0 \
python3 -m sglang.launch_server \
  --model-path /path/to/DeepSeek-V4-Flash-Base/ --trust-remote-code \
  --tp 8 --dp 8 --ep-size 8 --enable-dp-attention --enable-dp-lm-head \
  --nnodes 1 --node-rank 0 --dist-init-addr <addr>:20001 \
  --moe-a2a-backend deepep --deepep-mode low_latency \
  --disaggregation-mode decode --disaggregation-transfer-backend mooncake \
  --disaggregation-ib-device mlx5_0,mlx5_1,mlx5_2,mlx5_3 \
  --disaggregation-decode-enable-radix-cache \
  --enable-hierarchical-cache --hicache-ratio 1.2 \
  --mem-fraction-static 0.83 \
  --host 0.0.0.0 --port 8000
```

Expected: server prints `The server is fired up and ready to roll!` within ~7 min after DeepGEMM JIT.

Observed: server progresses through all init phases, disaggregation warmup starts, but the fake generation request never completes. `curl http://localhost:8000/health` returns 503 for 30 min. Log shows `Disaggregation warmup request` sent but no `End of disaggregation warmup` line ever appears.

### Environment

```
sglang v0.5.13
Model: DeepSeek-V4-Flash
GPUs: 8×H20
Backend: mooncake, deepep low_latency
--enable-hierarchical-cache with SGLANG_ENABLE_UNIFIED_RADIX_TREE=1
```
