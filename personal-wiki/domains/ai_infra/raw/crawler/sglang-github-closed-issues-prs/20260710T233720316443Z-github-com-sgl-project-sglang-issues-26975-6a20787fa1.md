---
source_id: sglang-github-closed-issues-prs
title: HiCache host hits return incorrect routed_experts rows
canonical_url: https://github.com/sgl-project/sglang/issues/26975
captured_at: '2026-07-10T23:37:20.316443+00:00'
content_hash: 6a20787fa118ed9bce09cca43fb44073dc1e6bb580e7411d8ca1b2e9bd9fd646
---
# HiCache host hits return incorrect routed_experts rows

URL: https://github.com/sgl-project/sglang/issues/26975
State: closed
Labels: 
Closed at: 2026-07-10T01:24:08Z
Merged at: 

## Summary

When `--enable-return-routed-experts` is used with HiCache, routed expert rows for prompt tokens restored from the HiCache host tier appear to be stale or misaligned.

For the same prompt, a cold run and an immediate device-cache hit return identical routed expert rows for the cached prompt prefix. After evicting the prefix from device cache and restoring it from host cache, the generated output is still identical, but every cached prefix row in `meta_info.routed_experts` differs from the cold/device-cache result.

## Environment

- SGLang commit: `2fdae94e462a080bbde0b768c01075de8b38e3ec`
- Package: `sglang 0.5.12.post2.dev725+g2fdae94e4`
- Model: `Qwen/Qwen3-30B-A3B`
- Hardware: GCP `a2-ultragpu-1g`, 1x NVIDIA A100 80GB
- Torch/CUDA: `torch 2.11.0+cu130`
- Probe decoded `meta_info.routed_experts` from base64 int32 and reshaped to `(rows, 48, 8)`.
- I added logging instrumentation around routed-expert capture and HiCache load scheduling only; no cache or routing logic was changed.

Server command:

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-30B-A3B \
  --trust-remote-code \
  --enable-return-routed-experts \
  --enable-hierarchical-cache \
  --hicache-size 32 \
  --hicache-write-policy write_through \
  --hicache-mem-layout page_first_direct \
  --hicache-io-backend direct \
  --enable-cache-report \
  --mem-fraction-static 0.88 \
  --context-length 16384 \
  --max-total-tokens 32768 \
  --disable-cuda-graph \
  --host 127.0.0.1 \
  --port 30000
```

Startup confirmed the routed-expert cache allocation:

```text
KV Cache is allocated. dtype: torch.bfloat16, #tokens: 32768
HostCache[routed_experts] allocated: shape=(32769, 48, 8), size=0.05 GB
DeviceCache[routed_experts] allocated: shape=(8192, 48, 8), size=12.00 MB
```

## Reproduction

1. Send prompt `Q2` with a stable 4096-token prefix and `return_routed_experts=true`.
2. Send the same prompt `Q2` again immediately. This is the device-cache control.
3. Send another prompt `Q1` sharing most of the same prefix.
4. Send five decoy prompts of 8192 tokens each to evict the original prefix from the device tier.
5. Send the same prompt `Q2` again. This is the host-cache validation.

The prompt was 4109 prompt tokens locally, and the returned routed expert tensor shape was `(4112, 48, 8)` for the `Q2` runs.

## Observed result

The generated output ids for cold, device-cache, and host-cache `Q2` were identical:

```text
[21806, 25, 4710, 32313]
```

The cold and device-cache runs match for all cached prompt prefix rows. Only the generated rows differ, which is expected:

```json
"baseline_vs_device_control": {
  "common_rows": 4112,
  "mismatch_count": 3,
  "mismatch_first20": [4109, 4110, 4111],
  "prefix_rows_checked": 4108,
  "prefix_mismatch_count": 0,
  "prefix_mismatch_first20": []
}
```

After eviction, the validation run reports a pure host hit for the same cached prompt prefix:

```json
"validation_cached": {
  "device": 0,
  "host": 4108
}
```

But every cached prefix routed-expert row differs from the cold result:

```json
"baseline_vs_validation": {
  "common_rows": 4112,
  "mismatch_count": 4112,
  "mismatch_first20": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
  "prefix_rows_checked": 4108,
  "prefix_mismatch_count": 4108,
  "prefix_mismatch_first20": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
}
```

Neither run returned zero rows:

```text
baseline_zero_rows=0
validation_zero_rows=0
```

Instrumentation from `collect_routed_experts` shows the key cache state:

```text
# cold Q2
cached_tokens=0 cached_tokens_device=0 cached_tokens_host=0 host_hit_length=0
req_to_token_slots_first16=[19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]
row_checksums.first=[23429, 24350, 25834, 25022, 24213, 24893, 23637, 24231]

# immediate device-cache Q2
cached_tokens=4108 cached_tokens_device=4108 cached_tokens_host=0 host_hit_length=0
req_to_token_slots_first16=[19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]
row_checksums.first=[23429, 24350, 25834, 25022, 24213, 24893, 23637, 24231]

# validation Q2 after eviction
cached_tokens=4108 cached_tokens_device=0 cached_tokens_host=4108 host_hit_length=4108
req_to_token_slots_first16=[12337, 12338, 12339, 12340, 12341, 12342, 12343, 12344, 12345, 12346, 12347, 12348, 12349, 12350, 12351, 12352]
row_checksums.first=[24830, 24043, 24400, 23613, 23237, 24900, 24885, 23186]
```

The HiCache load path did load 4108 host tokens into new device slots:

```text
hicache_load_enqueue host_len=4108 device_len=4108
host_sample.first=[16, 17, 18, 19, ...]
device_sample.first=[12337, 12338, 12339, 12340, ...]
schedule_hicache_load rid=<validation> prefix_indices_len=4108 host_hit_length=4108 extend_input_len=1
```

## Expected result

For the identical prompt and identical generated output, `return_routed_experts` should return the same routed expert rows for cached prompt tokens regardless of whether those rows are still in device cache or restored from HiCache host cache.

The device-cache control suggests the capture path is correct when `cached_tokens_device > 0`. The all-prefix mismatch only when `cached_tokens_host > 0` suggests the `routed_experts` side cache/load path is returning stale or misaligned rows for host-restored tokens.
