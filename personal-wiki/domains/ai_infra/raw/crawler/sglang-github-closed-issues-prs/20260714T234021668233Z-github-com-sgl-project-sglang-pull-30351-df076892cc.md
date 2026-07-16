---
source_id: sglang-github-closed-issues-prs
title: '[Bug fix] Account for KV replication fan-out in transfer-byte metrics'
canonical_url: https://github.com/sgl-project/sglang/pull/30351
captured_at: '2026-07-14T23:40:21.668233+00:00'
content_hash: df076892ccd840e64127f6ae823e2225ef436c6aa63ce00f7602f031529706a0
---
# [Bug fix] Account for KV replication fan-out in transfer-byte metrics

URL: https://github.com/sgl-project/sglang/pull/30351
State: closed
Labels: run-ci
Closed at: 2026-07-14T17:08:25Z
Merged at: 2026-07-14T17:08:25Z

## Motivation
When using PD disaggregation for **MLA models**, KV cache transfer metrics can be incorrectly reported, whenever one prefill sender replicates its KV cache to multiple decode destinations (e.g. **Prefill-CP + Decode-TP**). 

For example, with Prefill-CP4, Decode TP-4, CP0 sends the (full) KV cache to all the 4 TP ranks of the decode side. So, it sends the same KV cache 4 times. In the current implementation, latency metric is measured to be 4 times of a single transfer but the amount of data transfer in bytes stays the same (x1), not x4.

As a result, the `kv_transfer_speed_gb_s` metric appears very low (in this case, 1/4 of the real value, if TP8, would be 1/8), making diagnostics unreliable.

## Modifications

### Details
In MLA models, latent KV states are not naturally sharded along the head dimension as they are for MHA. Instead, they are replicated across the TP ranks.

When one prefill sender fans out to multiple decode ranks, it transfers the full KV cache to each of them. For example, with Prefill-CP4 and Decode-TP4, prefill rank 0 replicates the same (full) KV cache 4 times.

This is not reflected in the current implementation. Metrics such as `sglang:kv_transfer_total_mb` and `sglang:kv_transfer_speed_gb_s` are calculated based on a single KV cache transfer, giving only the x1 value instead of the x4 value for the TP4 case.

This gives incorrect information when monitoring KV transfer metrics, since one would find 1/4 of the expected KV cache transfer speed, 1/8 if it is TP8, which may misleadingly imply a network problem.

This only affects fan-out topologies. For example, for a case where tp_size is the same for both prefill and decode, each Prefill TP rank transfers the (full) KV cache to its corresponding Decode TP rank, so the factor stays 1.

### Approach
`CommonKVSender.get_transfer_metric()` calculates `transfer_total_bytes` from the number of KV and state indices transferred. Currently, it does not account for how many replications are done.

We derive a replication factor using `required_dst_info_num`, which is produced during the bootstrap phase. This factor is then applied to `transfer_total_bytes`.

The resolver (`CommonKVManager.resolve_kv_replica_factor`) is hooked into each backend's registration barrier — the point where all decode destinations for a room have reported — so it is wired for all three connectors (**mooncake**, **nixl**, **mori**).

### Tests
#### Unit tests
- factor resolution from `required_dst_info_num` (MLA scaled by fan-out; non-MLA pinned to 1)
- scaling applied to both KV and state indices
- unresolved factor (empty room or missing `required_dst_info_num`) does not crash the metric — bytes are never multiplied by `None`

#### Integration tests
- GPU: NVIDIA H100
- Prefill-CP4 / Decode-TP4
- Model: DeepSeek-V2-Lite, Qwen3-8B
- Transfer engine: Mooncake

Observed from Prometheus metrics, compared before and after the patch.

| Model | Prompt tokens | Bytes transferred (before) | Bytes transferred (after) |
| --------- | ---------- |  ------- | ----- |
| DeepSeek-V2-Lite (MLA) | 819 | 24.3 MiB | 97.2 MiB = 24.3 x 4 |
| Qwen3-8B (MHA) | 779 |  110 MiB | 110 MiB = 110 x 1|

For an MLA model, DeepSeek-V2-Lite, the patch correctly recognizes the number of bytes transferred, which should be 4 times the full KV cache. The non-MLA model Qwen3-8B is not affected by the patch.


## Accuracy Tests

This is not related to model accuracy.

## Speed Tests and Profiling

The impact is expected to be negligible to inference speed.**





























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29308715234](https://github.com/sgl-project/sglang/actions/runs/29308715234)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29308715028](https://github.com/sgl-project/sglang/actions/runs/29308715028)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
