---
source_id: sglang-github-closed-issues-prs
title: '[HiCache]fix draft host pool allocator type'
canonical_url: https://github.com/sgl-project/sglang/pull/29823
captured_at: '2026-07-02T02:12:27.260512+00:00'
content_hash: 99b61728bfdaf5f56aeabad2e7369a128a46828a712a2764976bb7e2f8072fb9
---
# [HiCache]fix draft host pool allocator type

URL: https://github.com/sgl-project/sglang/pull/29823
State: closed
Labels: run-ci
Closed at: 2026-07-01T11:31:17Z
Merged at: 2026-07-01T11:31:17Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
Fix EAGLE draft KV HiCache registration with Mooncake standalone storage by creating the draft host KV pool with the same storage-backed allocator as the target host pool.
```
INFO:sglang.srt.mem_cache.memory_pool:KV Cache is allocated. dtype: torch.bfloat16, #tokens: 64, K size: 0.00 GB, V size: 0.00 GB
INFO:sglang.srt.mem_cache.memory_pool_host:Allocating 0.00 GB host memory for hierarchical KV cache.
PRIMARY_ALLOCATOR MooncakeHostTensorAllocator True
WARNING:sglang.jit_kernel.hicache:Unsupported element_size = 16 for JIT HiCache kernel
INFO:sglang.srt.mem_cache.storage.mooncake_store.mooncake_store:Mooncake Configuration loaded from extra_config successfully.
WARNING: Logging before InitGoogleLogging() is written to STDERR
I20260701 17:08:48.287503 12054 client_metric.cpp:114] Client metrics enabled (default enabled)
I20260701 17:08:48.287521 12054 client_metric.cpp:115] Client bandwidth summary enabled via MC_STORE_CLIENT_METRIC_BANDWIDTH
I20260701 17:08:51.687362 12054 dummy_client.cpp:401] Connecting to IPC socket: @mooncake_client_50052.sock
I20260701 17:08:51.688673 12054 dummy_client.cpp:447] Successfully registered SHM via IPC, base: 0x7f0308000000
E20260701 17:08:51.688711 12054 dummy_client.cpp:1430] Failed to receive hot cache fd, status=-1
I20260701 17:08:51.688715 12054 dummy_client.cpp:524] Hot cache shm not available (real client may not have it)
INFO:sglang.srt.mem_cache.storage.mooncake_store.mooncake_store:Mooncake store setup successfully.
INFO:sglang.srt.mem_cache.storage.mooncake_store.mooncake_store:Mooncake store warmup successfully.
I20260701 17:08:51.690459 12054 dummy_client.cpp:401] Connecting to IPC socket: @mooncake_client_50052.sock
I20260701 17:08:51.690519 12054 dummy_client.cpp:447] Successfully registered SHM via IPC, base: 0x7f09abc21000
PRIMARY_REGISTER_OK
DRAFT_ALLOCATOR default HostTensorAllocator False
DRAFT_REGISTER_RESULT default FAIL RuntimeError Failed to register buffer to Mooncake Store, error code: -1
INFO:sglang.srt.mem_cache.memory_pool:KV Cache is allocated. dtype: torch.bfloat16, #tokens: 64, K size: 0.00 GB, V size: 0.00 GB
INFO:sglang.srt.mem_cache.memory_pool_host:Allocating 0.00 GB host memory for hierarchical KV cache.
WARNING:sglang.jit_kernel.hicache:Unsupported element_size = 16 for JIT HiCache kernel
E20260701 17:08:51.691900 12054 dummy_client.cpp:678] Buffer is not in any registered shared memory
ERROR:sglang.srt.mem_cache.storage.mooncake_store.mooncake_store:Failed to register buffer, error code: -1
I20260701 17:08:52.209097 12054 dummy_client.cpp:566] [unregister_shm] client_id=2327241771551537217-9561845296310794662
```
## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28502323595](https://github.com/sgl-project/sglang/actions/runs/28502323595)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28502323500](https://github.com/sgl-project/sglang/actions/runs/28502323500)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
