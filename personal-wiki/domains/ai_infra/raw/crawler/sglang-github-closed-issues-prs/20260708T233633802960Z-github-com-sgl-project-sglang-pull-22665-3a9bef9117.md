---
source_id: sglang-github-closed-issues-prs
title: '[PD] MORI-IO: Add state transfer, inline transfer model, and high-concurrency
  fixes'
canonical_url: https://github.com/sgl-project/sglang/pull/22665
captured_at: '2026-07-08T23:36:33.802960+00:00'
content_hash: 3a9bef91176d8961672a743fee19cf6d910163cd4828a1a7b2056e5d1704518f
---
# [PD] MORI-IO: Add state transfer, inline transfer model, and high-concurrency fixes

URL: https://github.com/sgl-project/sglang/pull/22665
State: closed
Labels: lora, deepseek, blackwell, run-ci, diffusion
Closed at: 2026-05-08T23:07:22Z
Merged at: 2026-05-08T23:07:22Z

## Motivation

Follow-up to #14626 which introduced MORI-IO as the RDMA-based KV transfer backend for PD disaggregation on AMD hardware. This PR addresses the known limitation (no state transfer) and resolves several performance bottlenecks and correctness issues discovered under high-concurrency workloads:

1. State data transfer was not implemented for hybrid models (Mamba, SWA, NSA).
2. TP slice head mapping was incorrect for `prefill_tp_size > decode_tp_size` with GQA/MQA.
3. ZMQ-based auxiliary data transfer caused message flooding and transfer queue hangs under high concurrency (AUX RDMA path added as opt-in alternative).
4. The `_connect()` function does not reuse connections, resulting in all available ports being occupied.

## Modifications

All changes are confined to `python/sglang/srt/disaggregation/mori/conn.py`.

### 1. State Transfer Support (Mamba, SWA, NSA)

- Added `send_state()` method on `MoriKVManager` that dispatches to `_send_mamba_state()` or `_send_swa_nsa_state()` based on `state_type`.
- `_send_mamba_state()`: Single-index Mamba SSM state transfer with TP-mismatch slice support (computes per-dimension offsets when prefill TP != decode TP).
- `_send_swa_nsa_state()`: Multi-token SWA/NSA state transfer using `group_concurrent_contiguous()` and batched RDMA writes.
- Extended `TransferInfo` with `dst_state_indices` and `KVArgsRegisterInfo` with `dst_state_item_lens` / `dst_state_dim_per_tensor`.

### 2. Inline Transfer Model with Caller-Driven Polling

Refined the inline transfer architecture (no worker threads):

- **`add_transfer_request()`**: Inline execution with reduced lock scope — RDMA posting happens outside `transfer_lock`, allowing bootstrap thread to register new requests concurrently.
- **`MoriKVSender.poll()`**: Caller-driven RDMA completion checking via `_all_transfers_finished()`, with decode notification fired immediately on completion.
- **Transfer plan precomputation**: `GroupedIndexPlan` / `BatchTransferPlan` dataclasses compute offsets once and reuse across all layers, eliminating redundant per-layer list comprehensions.
- **Error resilience**: Transfer submission failures are caught and recorded without crashing the scheduler; `_maybe_finalize_if_room_failed()` bridges manager-side errors to sender lifecycle.

### 3. AUX Data Transfer

- Default path remains ZMQ TCP (`send_aux_tcp()`), which is stable under all concurrency levels.
- Added `send_aux_rdma()` as opt-in alternative via `SGLANG_MORI_SEND_AUX_RDMA=1` env var, with automatic fallback to TCP when remote AUX descriptors are unavailable.
- Added `_connect_threadsafe()` with thread-local ZMQ sockets for thread-safe TCP communication.

### 4. Bug Fixes

- **TP slice fix**: Corrected head mapping for `prefill_tp_size > decode_tp_size` with GQA/MQA. Introduced `src_replication` and `unique_head_idx` for correct replicated head mapping.
- **Stale metadata guard**: `_handle_transfer_message()` now acquires `transfer_lock` and rejects metadata when room status is past Bootstrapping, preventing race conditions.
- **`update_status()` state machine guard**: `Failed` is terminal and never overwritten by non-Failed states.
- **CP rank support**: `_compute_prefill_unique_rank()` now correctly encodes TP/PP/CP ranks for decode notification.
- **TCP connection reuse**: The new `_connect thread-safe()` function can reuse TCP connections, resolving the issue of the original `_connect()` potentially causing too many connections in high-concurrency scenarios.

### 5. Default Parallelism Tuning

| Parameter | Before | After |
|-----------|--------|-------|
| `SGLANG_MORI_QP_PER_TRANSFER` | 1 | 4 |
| `SGLANG_MORI_NUM_WORKERS` | 1 | 4 |

## Benchmarking

### Hardware Configuration
- **GPUs**: 8x AMD Instinct MI355X per node
- **Network**: 8x AMD Pensando Pollara 400 AI-NIC per node (`ionic_0` ~ `ionic_7`)
- **Model**: DeepSeek-R1 (671B, FP8) with TP=8, `--kv-cache-dtype fp8_e4m3`
- **Setup**: 2-node PD disaggregation (1 prefill + 1 decode) + router
- **Software**: `--attention-backend aiter --fp8-gemm-backend aiter`, `SGLANG_USE_AITER=1`

### Single-Request Latency (MORI vs Mooncake)

`--num-prompts 1 --max-concurrency 1 --random-output-len 16`, each input length run twice:

| Input Tokens | MORI TTFT (ms) | MORI TPOT (ms) | MORI E2E (ms) | Mooncake TTFT (ms) | Mooncake TPOT (ms) | Mooncake E2E (ms) |
|---|---|---|---|---|---|---|
| 1024 | 77 | 6.92 | 153 | 68 | 7.03 | 146 |
| 2048 | 81 | 7.26 | 162 | 73 | 7.40 | 154 |
| 4096 | 82 | 7.29 | 162 | 73 | 7.40 | 154 |
| 8192 | 196 | 7.56 | 280 | 196 | 7.79 | 281 |


### High-Concurrency Throughput (MORI vs Mooncake)

`--num-prompts 2048 --max-concurrency 2048 --random-input-len 8192 --random-output-len 1024`:

| Metric | MORI | Mooncake |
|---|---|---|
| Successful requests | 2048 | 2048 |
| Request throughput (req/s) | **7.49** | 6.80 |
| Input token throughput (tok/s) | **31,111** | 28,257 |
| Output token throughput (tok/s) | **3,775** | 3,428 |
| Total token throughput (tok/s) | **34,886** | 31,685 |
| Mean TPOT (ms) | 29.96 | 27.81 |
| Mean ITL (ms) | 29.92 | 29.08 |

### State Transfer Verification (Qwen3.5-397B-A17B)

Tested with TP=8 same-TP:

- Model uses `HybridLinearKVPool` with Mamba Cache
- State transfer (`_send_mamba_state`) confirmed active via `state_type="mamba"` path
- Multiple curl requests: correct output, no garbled text

| Mode | GSM8K Accuracy | Invalid |
|---|---|---|
| Single-machine TP=8 (baseline) | 0.955 | 0.025 |
| **MORI Disaggregation TP=8** | **0.970** | **0.005** |


### Accuracy Test (DeepSeek-R1)

```bash
python3 -m sglang.test.few_shot_gsm8k \
    --host http://127.0.0.1 --port 30000 \
    --num-questions 200 --parallel 128 --num-shots 5
```

| Metric | Result |
|---|---|
| Accuracy | 0.970 |
| Invalid | 0.000 |

## Known Limitations

- SWA/NSA state transfer does not yet support TP-mismatch with non-MLA attention (consistent with Mooncake and NIXL backends).
- AUX RDMA path (`SGLANG_MORI_SEND_AUX_RDMA=1`) is experimental and may cause decode stalls(AINIC) under high concurrency due to RDMA completion ordering. TCP default is recommended.

cc @Duyi-Wang @ZhaiFeiyue
