---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Enable unified-KV HiCache on DeepSeek-V4'
canonical_url: https://github.com/sgl-project/sglang/pull/29417
captured_at: '2026-07-09T23:36:35.323711+00:00'
content_hash: 4d9f99faf8b5fed7a3cfb9d2039ab841aa3b7321ae28ca0a8b43a43b2ad72e3b
---
# [AMD] Enable unified-KV HiCache on DeepSeek-V4

URL: https://github.com/sgl-project/sglang/pull/29417
State: closed
Labels: amd, deepseek, run-ci
Closed at: 2026-07-09T19:58:48Z
Merged at: 2026-07-09T19:58:48Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

On DeepSeek-V4, HiCache already works with the separate KV layout used by the standalone attention backends (e.g. `triton`, `tilelang`). However, the `unified_kv_triton` backend uses a different KV layout — SWA ring, C4, and C128 packed into a single unified pool — which is incompatible with the existing HiCache path.

This PR enables L2 (host) and L3 (storage) HiCache for DeepSeek-V4 with the unified KV layout, while keeping the separate-layout backends unaffected. 

Related to sglang issue https://github.com/sgl-project/sglang/issues/28704.

**The way to run HiCache.**

L2 hicache args:
```
export SGLANG_ENABLE_UNIFIED_RADIX_TREE=true
sglang serve \
  ... \
  --enable-hierarchical-cache --hicache-io-backend direct --hicache-mem-layout layer_first
```

L2+L3 hicache args:
```
export SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR={SSD folder path}
export SGLANG_ENABLE_UNIFIED_RADIX_TREE=true
sglang serve \
  ... \
  --enable-hierarchical-cache --hicache-io-backend direct --hicache-mem-layout layer_first \
  --hicache-storage-backend file --hicache-storage-prefetch-policy wait_complete
```

## Modifications

<!-- Detail the changes made in this pull request. -->

DeepSeek-V4 under `unified_kv_triton` keeps three KV families in one pool: the SWA ring, and the compressed KV (C4, C128).

The SWA part is stored as a ring buffer — newly generated tokens overwrite the oldest ones — so unlike the page-based layout it cannot be preserved for reuse, and its length is fixed rather than growing with context. We therefore only HiCache the dominant part, the compressed KV (C4/C128). This is consistent with how `unified_kv_triton` already handles SWA in radix-cache-only mode (no HiCache).

**Compressed KV (C4/C128) part**: The compressed region is packed inside the unified pool, so we first pull it out and convert it into the format HiCache expects.
- `deepseek_v4_memory_pool.py`: add `unified_region_buffers`, which extracts the compressed region from the unified pool and converts it into per-layer, page-aligned views so the host/storage transfer can treat it as ordinary KV; load-back is synchronized with a per-layer barrier.
- `hybrid_pool_assembler.py`: build the C4/C128 host pools for the unified layout (no SWA host pool or compress-state pools).

**SWA part**: Since the SWA ring is not stored in HiCache, a reused prefix would carry a stale SWA window, so the last window must be reprefilled.
- `unified_radix_cache.py`: add `swa_reprefill_tail_tokens()`, returning the trailing window length that must be recomputed.
- `schedule_batch.py`, `schedule_policy.py`: cap the prefix match by this length so the trailing window is extended.

**Enable HiCache:**
- `server_args.py`: remove the compatibility guard that previously blocked the unified KV layout from using L2, L3 HiCache.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

gsm8k has very few hot prompts, so running it twice with HiCache on simply reuses the KV from device, and the host/storage path is never exercised. To actually verify the load-back path, we instead:

1. Run gsm8k with HiCache (L2 + L3) as run 1.
2. Stop the server, so the KV is persisted to L3 (storage).
3. Restart and run gsm8k again. On this run the KV is fetched back from storage.

| Backend | run 1 | run 2 (after restart, from storage) |
| --- | --- | --- |
| `triton` | 0.943 | 0.942 |
| `unified_kv_triton` | 0.945 | 0.942 |

In server log, may see following msg.
```
[2026-06-26 09:14:59 TP3] HiCache prefetch success req=14bcc75583724e10993a9a1d8c3ea080 completed_local=256 completed_synced=256 matched=256 loaded=0 tail_release=0 occupied=11008
```
  
<details>
<summary>Server cmd</summary>

```
export SGLANG_DEFAULT_THINKING=1
export SGLANG_DSV4_REASONING_EFFORT=max
export SGLANG_USE_ROCM700A=0
export SGLANG_DP_USE_GATHERV=1
export SGLANG_HACK_FLASHMLA_BACKEND=unified_kv_triton
export AITER_BF16_FP8_MOE_BOUND=0
export SGLANG_ENABLE_UNIFIED_RADIX_TREE=true
export CUDA_VISIBLE_DEVICES=0,1,2,3

export SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR=/data/hicache_l3

sglang serve \
  --model-path /data/deepseek-ai/DeepSeek-V4-Pro --trust-remote-code \
  --tp 4 \
  --attention-backend dsv4 \
  --page-size 256 \
  --mem-fraction-static 0.90 \
  --swa-full-tokens-ratio 0.1 \
  --disable-shared-experts-fusion \
  --tool-call-parser deepseekv4 --reasoning-parser deepseek-v4 \
  --chunked-prefill-size 131072 \
  --max-running-requests 512 \
  --enable-metrics \
  --port 8000 \
  --enable-hierarchical-cache --hicache-io-backend direct --hicache-mem-layout layer_first \
  --hicache-storage-backend file --hicache-storage-prefetch-policy wait_complete
```

</details>

<details>
<summary>Client cmd</summary>

```
python3 benchmark/gsm8k/bench_sglang.py --num-questions 2000 --parallel 2000 --port 8000
```

</details>

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

Tested on:
- machine: tp4,
- input / output length:  50k / 200
- conc: 64, 

comparing radix-cache with and without HiCache. For each config we report a cold run (first pass, no reuse) and a warm run (second pass, prefix reused).

A fixed random seed is used so both runs send identical inputs, ensuring the warm run actually reuses the cold run's prefix.
```
python3 -m sglang.bench_serving --backend sglang --dataset-name random --random-input-len 50000 --random-output-len 200 --random-range-ratio 1 --num-prompts 64 --max-concurrency 64 --seed 42 --port 8000
```

| Config | Run | Output Token throughput (tok/s) | Median TTFT (ms) |
| --- | --- | --- | --- |
| radix-cache (w/o HiCache) | cold | 66 | 91800 |
| radix-cache (w/o HiCache) | warm | 66 | 91128 |
| radix-cache + HiCache | cold | 66 | 91690 |
| radix-cache + HiCache | warm | 789 | 3982 |

Without HiCache the warm run shows no gain, since 50k x 64 exceeds device cache capacity and the prefix is evicted before reuse. With HiCache the reused prefix is served from the host pool, giving about 12x token throughput and 23x lower TTFT on the warm run.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29045772396](https://github.com/sgl-project/sglang/actions/runs/29045772396)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29045772324](https://github.com/sgl-project/sglang/actions/runs/29045772324)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
