---
source_id: sglang-github-closed-issues-prs
title: 'test(disagg): set MC_GID_INDEX on RoCE hosts so mooncake KV transfer works'
canonical_url: https://github.com/sgl-project/sglang/pull/30737
captured_at: '2026-07-11T23:37:37.773406+00:00'
content_hash: 906576a6cdfa590573fbca6d5088ce5254db2e011c28a69991b995cd7398019d
---
# test(disagg): set MC_GID_INDEX on RoCE hosts so mooncake KV transfer works

URL: https://github.com/sgl-project/sglang/pull/30737
State: closed
Labels: 
Closed at: 2026-07-11T03:29:22Z
Merged at: 2026-07-11T03:29:22Z

## Problem

On RoCE-only `8-gpu-h200` runners, the PD disaggregation tests in `test_disaggregation_hybrid_attention.py` (`TestDisaggregationHybridAttention*`) fail with a GSM8K score of **0.0**. Every prefill→decode KV transfer errors out:

```
Decode transfer failed ... KVTransferError: Failed to get kvcache from prefill instance, it might be dead
Prefill transfer failed ... KVTransferError: Decode instance could be dead, remote mooncake session <ip>:<port> is not alive
```

so all `/v1/completions` return 500 and the eval scores 0.0.

## Root cause

Mooncake's automatic RDMA GID selection returns NULL on the host's bonded RoCE NIC and logs:

```
GID is NULL, please check your GID index by specifying MC_GID_INDEX
```

The transfer endpoint then has no GID, so the session never establishes. The `8-gpu-h200` hosts where these tests pass today are native **InfiniBand**, where auto GID selection works — the failure only appeared once a RoCE-only host joined the pool.

## Fix

The PD fixture now auto-detects a RoCE fabric (`link_layer == Ethernet`) for the selected IB devices and exports `MC_GID_INDEX` to a RoCEv2 GID index shared by those devices, preferring a global (routable) GID over a link-local (`fe80::`) one. It is a no-op on InfiniBand, when the selected devices disagree on the index (`MC_GID_INDEX` is a single global value), or when the user has already set `MC_GID_INDEX`. It is cleared in teardown only if this fixture set it.

## Validation

Reproduced and fixed on a RoCE-only H200 host (`Qwen/Qwen3-Next-80B-A3B-Instruct`, prefill tp2 + decode tp2/dp2):

- Before: KV transfer fails on every request, score **0.0**.
- After (fixture auto-sets `MC_GID_INDEX=3`, no manual env): `Ran 1 test ... OK`, score **0.955** (threshold 0.90).

Independent checks on the host: `ib_write_bw` RoCEv2 loopback (same-NIC and cross-NIC) works, and RoCEv2 GID index 3 is present and identical on both selected NICs. The GID auto-detection helper is unit-tested (RoCE → index, InfiniBand → None, divergent devices → None).











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29067918358](https://github.com/sgl-project/sglang/actions/runs/29067918358)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29067918313](https://github.com/sgl-project/sglang/actions/runs/29067918313)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
