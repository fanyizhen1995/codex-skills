---
source_id: sglang-github-closed-issues-prs
title: '[EPD] Optimize multimodal global cache with paged embedding pool'
canonical_url: https://github.com/sgl-project/sglang/pull/28441
captured_at: '2026-07-07T23:35:30.918528+00:00'
content_hash: c1b08fea4b78d92f0d23cdc452cc04e50e9c51db7654b51a2bba4665df02b928
---
# [EPD] Optimize multimodal global cache with paged embedding pool

URL: https://github.com/sgl-project/sglang/pull/28441
State: closed
Labels: run-ci
Closed at: 2026-07-07T04:05:52Z
Merged at: 2026-07-07T04:05:52Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
The original multimodal global embedding cache stores all embeddings in one flat CPU pinned buffer and uses a first-fit contiguous allocator for variable-sized embedding blocks. This works when the pool has large contiguous free regions, but multimodal embeddings can have different token lengths, and repeated insert/evict cycles can split the free space into many small holes.

In that case, allocation can fail even when the total free cache memory is still large, because each new embedding requires one contiguous CPU block. Eviction does not fully solve this: evicted entries only merge with adjacent free blocks, and entries protected by in-flight RDMA transfers or active CPU views cannot be evicted. As a result, fragmentation can reduce the effective usable cache capacity and cause cache insert/prefetch skips.

This PR changes the embedding cache to use a paged host pool. Each embedding can be stored across one or more physical page runs, so the cache can reuse fragmented free pages instead of requiring a single contiguous allocation. Together with Mooncake multi-buffer scatter/gather APIs, the paged layout can be transferred without flattening into a temporary contiguous buffer. The goal is to improve cache memory utilization and robustness under fragmentation while keeping transfer and end-to-end performance comparable to the original path.

## Modifications

<!-- Detail the changes made in this pull request. -->
- Replace contiguous embedding allocation with a paged host pool.
  - Add `RangePageAllocator` and `PageRun` to allocate embeddings across one or more page ranges.
  - Store cache metadata as page runs instead of a single `(offset, size)` CPU block.
  - Prefer contiguous page runs when available, but fall back to scattered page runs when the pool is fragmented.

- Split the embedding pool by modality.
  - Use a vision pool for image/video embeddings.
  - Use an audio pool for audio embeddings.
  - Maintain independent allocation and eviction state for each pool.

- Add explicit cache entry state and pinning.
  - Track entries as `FILLING` or `READY` so readers never consume partially written embeddings.
  - Pin entries during Mooncake transfer, host/device copy, or pool-view usage.
  - Only allow READY entries with no active pins to be evicted.

- Integrate Mooncake multi-buffer APIs.
  - Add wrappers for `batch_get_into_multi_buffers`.
  - Add wrappers for `batch_put_from_multi_buffers`.
  - Build one pointer/size list per embedding from its physical page runs.

- Update encoder assembly paths for paged embeddings.
  - Use async host-to-device copies for cached embeddings in the Mooncake path.
  - Keep newly computed miss/fallback embeddings usable while async D2H cache storage proceeds.
  - Push newly stored embeddings to Mooncake in the background when possible.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->
This PR does not change model forward computation or model outputs. It only changes multimodal embedding cache storage, transfer, and assembly.

Unit tests added/updated for cache-controller behavior:
```bash
python -m pytest test/registered/unit/mem_cache/test_embedding_cache_controller.py -v
```

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->
### Mooncake multi-buffer API benchmark

Environment:
- RDMA: RoCE v2
- Protocol: `rdma + P2PHANDSHAKE`
- Segment size: 32GB
- Memory allocator: `MooncakeHostMemAllocator`

The benchmark compares single-buffer `batch_get` / `batch_put` with multi-buffer `batch_get_into_multi_buffers` / `batch_put_from_multi_buffers`. Each multi-buffer embedding is split into independently allocated non-contiguous buffers to match the paged-pool cache path.

| API | Batch | Emb Size | Page Size | Pages/Emb | Latency (ms) | Throughput (GB/s) |
|-----|-------|----------|-----------|-----------|--------------|-------------------|
| PUT single | 1 | 64MB | - | 1 | 1.699 | 35.9 |
| PUT multi | 1 | 64MB | 128KB | 512 | 1.873 | 32.6 |
| GET single | 1 | 64MB | - | 1 | 1.758 | 34.7 |
| GET multi | 1 | 64MB | 128KB | 512 | 1.913 | 31.9 |
| PUT single | 2 | 64MB | - | 1 | 3.105 | 39.3 |
| PUT multi | 2 | 64MB | 128KB | 512 | 3.352 | 36.4 |
| GET single | 2 | 64MB | - | 1 | 3.250 | 37.6 |
| GET multi | 2 | 64MB | 128KB | 512 | 3.570 | 34.2 |
| PUT single | 1 | 128MB | - | 1 | 3.282 | 37.2 |
| PUT multi | 1 | 128MB | 256KB | 512 | 3.516 | 34.7 |
| GET single | 1 | 128MB | - | 1 | 3.434 | 35.6 |
| GET multi | 1 | 128MB | 256KB | 512 | 3.630 | 33.6 |
| PUT single | 2 | 128MB | - | 1 | 6.080 | 40.1 |
| PUT multi | 2 | 128MB | 256KB | 512 | 6.386 | 38.2 |
| GET single | 2 | 128MB | - | 1 | 6.445 | 37.9 |
| GET multi | 2 | 128MB | 256KB | 512 | 6.824 | 35.8 |
| PUT single | 1 | 256MB | - | 1 | 6.564 | 37.2 |
| PUT multi | 1 | 256MB | 512KB | 512 | 6.786 | 36.0 |
| GET single | 1 | 256MB | - | 1 | 6.785 | 36.0 |
| GET multi | 1 | 256MB | 512KB | 512 | 7.038 | 34.7 |
| PUT single | 2 | 256MB | - | 1 | 12.531 | 38.9 |
| PUT multi | 2 | 256MB | 512KB | 512 | 12.819 | 38.1 |
| GET single | 2 | 256MB | - | 1 | 13.402 | 36.4 |
| GET multi | 2 | 256MB | 512KB | 512 | 13.359 | 36.5 |
| PUT single | 4 | 256MB | - | 1 | 24.646 | 39.6 |
| PUT multi | 4 | 256MB | 1MB | 256 | 25.227 | 38.7 |
| GET single | 4 | 256MB | - | 1 | 26.032 | 37.5 |
| GET multi | 4 | 256MB | 1MB | 256 | 26.390 | 37.0 |

Conclusion: Mooncake multi-buffer scatter/gather throughput is close to the single-buffer API. The overhead is around 8-10% with 512 pages of 128KB buffers, drops below 4% with page sizes >= 512KB, and is close to zero with 1MB pages.

### End-to-end performance benchmark

Environment and setup:
- Model: `Qwen3.5-9B`
- Request size: 4 images of 2560x1440 per request
- Samples: 3 warmup runs + 10 measured runs per scenario
- TTFT: time from `/generate` streaming request start to the first valid chunk
- Embedding cache time: temporary `BENCH_EMBED_MS` markers from encoder logs
- Global cache path: image batching was temporarily disabled to force per-request global cache path for image requests

| Code | Interface | Type | N | Avg Embed (ms) | Avg TTFT (ms) |
|------|-----------|------|---:|---------------:|--------------:|
| new | `encode_with_global_cache_mooncake` | miss | 10 | 1876.8 | 3687.9 |
| new | `encode_with_global_cache_mooncake` | hit | 10 | 382.2 | 1221.6 |
| new | `encode_with_global_cache` | miss | 10 | 1886.9 | 3860.8 |
| new | `encode_with_global_cache` | hit | 10 | 466.4 | 1903.5 |
| old | `encode_with_global_cache_mooncake` | miss | 10 | 1889.2 | 3777.8 |
| old | `encode_with_global_cache_mooncake` | hit | 10 | 379.5 | 1212.8 |
| old | `encode_with_global_cache` | miss | 10 | 1952.2 | 3938.4 |
| old | `encode_with_global_cache` | hit | 10 | 454.7 | 1761.8 |

New vs old, positive means the new code is faster by average latency:

| Interface | Type | Embed | TTFT |
|-----------|------|------:|-----:|
| `encode_with_global_cache_mooncake` | miss | +0.7% | +2.4% |
| `encode_with_global_cache_mooncake` | hit | -0.7% | -0.7% |
| `encode_with_global_cache` | miss | +3.3% | +2.0% |
| `encode_with_global_cache` | hit | -2.6% | -8.0% |

Observations:
- The new code shows a small improvement on miss paths: `encode_with_global_cache_mooncake` TTFT is about 2.4% faster, and `encode_with_global_cache` TTFT is about 2.0% faster.
- Hit paths do not show a stable improvement in this run. Mooncake hit is roughly flat, while non-Mooncake hit regresses by about 8% on average TTFT.
- Encoder logs confirmed that hit scenarios reached the global cache hit path with `Misses (GPU Work): 0`.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28529463884](https://github.com/sgl-project/sglang/actions/runs/28529463884)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28529463286](https://github.com/sgl-project/sglang/actions/runs/28529463286)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
