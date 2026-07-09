---
source_id: sglang-github-closed-issues-prs
title: 'feat(mem_cache): add client-side metadata cache for HiCacheFile storage'
canonical_url: https://github.com/sgl-project/sglang/pull/29716
captured_at: '2026-07-08T23:36:33.803455+00:00'
content_hash: b6242f612e827c2576f9b0d78344c93f4cb80e143ab2f5eed7e2d245cd730572
---
# feat(mem_cache): add client-side metadata cache for HiCacheFile storage

URL: https://github.com/sgl-project/sglang/pull/29716
State: closed
Labels: hicache, run-ci, bypass-fastfail
Closed at: 2026-07-08T01:21:47Z
Merged at: 2026-07-08T01:21:47Z

## Motivation

This PR resolves the filesystem metadata bottleneck in multi-tier offloading when using the file backend by introducing an in-memory client-side positive metadata cache in SGLang. Bypassing directory traversals via the in-memory cache directly resolves the MDS bottleneck, avoiding event loop blockage warnings when listing a large number of cache files, and reducing latency.

## Modifications

We modified three main components in the codebase:

* **Environment Configuration** ([environ.py](file:///usr/local/google/home/tyuchn/sglang/python/sglang/srt/environ.py#L423)): Added `SGLANG_HICACHE_FILE_BACKEND_ENABLE_METADATA_CACHE` (EnvBool, defaults to `False`) to make the metadata cache optional, and `SGLANG_HICACHE_FILE_BACKEND_METADATA_TTL` (defaulting to `5.0` seconds) to control expiration.
* **Eviction Hook Callback** ([lru_file_evictor.py](file:///usr/local/google/home/tyuchn/sglang/python/sglang/srt/mem_cache/storage/file/lru_file_evictor.py#L66)): Updated `LRUFileEvictor` to accept an `on_evict` callback. Whenever a file is deleted from disk to satisfy space bounds, the callback invalidates the evicted key in SGLang's client-side metadata cache.
* **MetadataCache & HiCacheFile Integration** ([hicache_storage.py](file:///usr/local/google/home/tyuchn/sglang/python/sglang/srt/mem_cache/hicache_storage.py#L319)):
  - Implemented `MetadataCache` with thread-safety and hard TTL logic.
  - Added a startup directory scan to pre-populate the cache.
  - Integrated the cache with `HiCacheFile`'s `exists()`, `get()`, `set()`, and eviction hook when enabled, falling back to original direct filesystem paths when disabled.

## Accuracy Tests

We integrated unit tests into SGLang's official `test_hicache_file_lru_unit.py` suite:
- Added `TestHiCacheFileMetadataIntegration` to verify:
  - Startup scanning.
  - Write backfill.
  - Cache hits bypassing `os.path.exists`.
  - Batch lookups bypassing `os.scandir`.
  - Disk evictions automatically invalidating metadata cache entries.
- All 35 tests passed successfully, verifying correctness and zero regressions.

## Speed Tests and Profiling

We evaluated SGLang on a shared Lustre filesystem populated with **157,195 cache files** under a synthetic shared-prefix workload:
- P99 TTFT dropped by **22.1%** and P99.9 TTFT dropped by **19.1%**, effectively removing the 1-second tail latency spikes.
- Bypassing `os.scandir` prevented event loop blockage warnings when listing 157k files, ensuring smooth scheduling steps.

Benchmarking details:

| Metric | Scenario A (Metadata Cache Disabled) | Scenario B (Metadata Cache Enabled) | Delta (%) |
| :--- | :---: | :---: | :---: |
| **Total / Successful Requests** | 60 / 60 | 60 / 60 | - |
| **P50 TTFT** | 455.10 ms | 454.12 ms | -0.2% |
| **P90 TTFT** | 520.15 ms | 480.20 ms | -7.7% |
| **P99 TTFT** | 584.21 ms | 455.05 ms | **-22.1%** |
| **P99.9 TTFT** | 995.12 ms | 805.50 ms | **-19.1%** |

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28899997114](https://github.com/sgl-project/sglang/actions/runs/28899997114)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28899996914](https://github.com/sgl-project/sglang/actions/runs/28899996914)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
