---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Release Mamba cache after PP dynamic chunk profiling'
canonical_url: https://github.com/sgl-project/sglang/pull/31321
captured_at: '2026-07-15T23:40:28.355369+00:00'
content_hash: d4c52a31fbfa9b3e0bb268467c8a528dfb002091af89c8c2751492278c759b15
---
# [Bugfix] Release Mamba cache after PP dynamic chunk profiling

URL: https://github.com/sgl-project/sglang/pull/31321
State: closed
Labels: 
Closed at: 2026-07-15T18:32:08Z
Merged at: 2026-07-15T18:32:08Z

## Motivation

PP dynamic chunking profiles up to 128 synthetic prefill requests during initialization. On hybrid Mamba models, `ScheduleBatch.prepare_for_extend()` allocates both KV cache and a Mamba cache slot for each profiling request.

The profiler cleanup released the KV cache and request-pool entry, but not `req.mamba_pool_idx`. As a result, profiling could exhaust `--max-mamba-cache-size` and disable dynamic chunking or fail warmup.

## Modifications

Release the profiling request's Mamba cache through `free_mamba_cache(req)` before freeing its request-pool entry.

## Reproduction

Launch it with TP1 + PP2 and a deliberately small Mamba cache:

```bash
CUDA_VISIBLE_DEVICES=0,1 \
python3 -m sglang.launch_server \
  --model-path /workspace/models/Qwen3.5-0.8B \
  --tp-size 1 \
  --pp-size 2 \
  --enable-dynamic-chunking \
  --chunked-prefill-size 1024 \
  --mamba-radix-cache-strategy extra_buffer \
  --max-mamba-cache-size 64
```

Before this fix, profiling fails at sample 32/128 after exhausting all Mamba slots:

```text
Profiling prefill latency for dynamic chunking: 25%|██▌| 32/128
[PP Dynamic Chunk] Failed to profile prefill latency: Not enough space for mamba cache
self.mamba_pool.size=64
self.mamba_allocator.available_size()=0
Dynamic chunking will be disabled.
```

With this fix, the same configuration completes all 128/128 profiling samples without a Mamba cache allocation error, and the server starts successfully.

## Accuracy Tests

Not applicable. This change only releases temporary cache state after a profiling forward has completed and does not modify model outputs.

## Speed Tests and Profiling

Not applicable to steady-state inference. The new conditional cleanup only runs during dynamic chunking initialization profiling.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). A targeted end-to-end regression requires a hybrid Mamba model with multi-GPU PP; the current registered dynamic chunking tests use dense models.
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). No user-facing behavior or configuration changed.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). Not applicable to this post-profiling resource cleanup.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29409824682](https://github.com/sgl-project/sglang/actions/runs/29409824682)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29409824446](https://github.com/sgl-project/sglang/actions/runs/29409824446)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
