---
source_id: sglang-github-closed-issues-prs
title: 'fix: make write_token dynamic'
canonical_url: https://github.com/sgl-project/sglang/pull/29271
captured_at: '2026-07-02T02:12:27.266869+00:00'
content_hash: 831d6f373ef0676e3bda78d3eba347ddcef70bed7eef524c7b0941a4ecf03290
---
# fix: make write_token dynamic

URL: https://github.com/sgl-project/sglang/pull/29271
State: closed
Labels: 
Closed at: 2026-07-01T05:55:58Z
Merged at: 2026-07-01T05:55:58Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
The MLX backend's ContiguousAttentionKVCache stores per-request, per-layer attention KV in a pre-allocated (1, n_kv_heads, max_seq_len, head_dim) buffer (default max_seq_len = 4096). It has two write paths:

  - update_and_fetch (prefill) — correctly grows the buffer on overflow via _grow.
  - write_token (decode, one token at a time) — did not check capacity or grow.

  As a result, once a request decoded past max_seq_len tokens, write_token performed an out-of-bounds slice assignment into the fixed-size buffer, corrupting/dropping KV for long generations on the batched and chained decode paths. This resolves the existing TODO (changminbark) in model_runner.py.

## Modifications

<!-- Detail the changes made in this pull request. -->
  - kv_cache/attention_kv_cache.py — ContiguousAttentionKVCache.write_token now checks self.offset + 1 > self.max_seq_len and calls the existing _grow helper before writing, mirroring update_and_fetch. Reuses the same growth routine (doubling + valid-prefix copy) so both write paths stay consistent. The in-place buffer swap preserves object identity, so the chained-decode path that reuses prev.caches transparently sees the grown buffer, and copying the still-lazy prefix just extends the MLX compute graph.
  - model_runner.py — removed the now-resolved TODO comment in decode_batch_start_chained (kept the still-accurate offset explanation below it).
  - test/.../mlx/test_attention_patching.py — added test_write_token_grows_buffer_past_max_seq_len, which writes 2 * max_seq_len + 1 tokens through write_token and asserts the buffer grew, offset is correct, and every token (including those written before the grow) is preserved at its original position.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

```
(sglang) changminbark@Chang-Mins-MacBook-Pro-M4-Pro-7:~/Desktop/OpenSource/sglang/sglang% uv run python -m unittest test/registered/unit/hardware_backend/mlx/test_attention_patching.py        

/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/attention/fla/utils.py:223: UserWarning: Triton is not supported on current platform, roll back to CPU.
  warnings.warn(
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/quantization/awq/awq.py:52: UserWarning: Only CUDA, HIP and XPU support AWQ currently.
  warnings.warn(f"Only CUDA, HIP and XPU support AWQ currently.")
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/quantization/gguf.py:64: UserWarning: Only CUDA, MUSA and NPU support GGUF quantization currently.
  warnings.warn(f"Only CUDA, MUSA and NPU support GGUF quantization currently.")
.......................................
----------------------------------------------------------------------
Ran 39 tests in 0.245s

OK
```

Regular bench_one_batch
```
(sglang) changminbark@Chang-Mins-MacBook-Pro-M4-Pro-7:~/Desktop/OpenSource/sglang/sglang% SGLANG_USE_MLX=1 uv run python -m sglang.bench_one_batch --model-path Qwen/Qwen3-0.6B --trust-remote-code --disable-cuda-graph --tp-size 1 --batch-size 1 --input-len 60 --output-len 10 --port 43440
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/attention/fla/utils.py:223: UserWarning: Triton is not supported on current platform, roll back to CPU.
  warnings.warn(
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/quantization/awq/awq.py:52: UserWarning: Only CUDA, HIP and XPU support AWQ currently.
  warnings.warn(f"Only CUDA, HIP and XPU support AWQ currently.")
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/quantization/gguf.py:64: UserWarning: Only CUDA, MUSA and NPU support GGUF quantization currently.
  warnings.warn(f"Only CUDA, MUSA and NPU support GGUF quantization currently.")
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/bench_one_batch.py:13: FutureWarning: `sglang.bench_one_batch` is deprecated and will be removed in a future release; use `sglang.benchmark.one_batch` instead (e.g. `python -m sglang.benchmark.one_batch`).
  warnings.warn(
'--disable-cuda-graph' is deprecated and will be removed in a future release. Use '--cuda-graph-backend-{decode,prefill}=disabled' instead.
Cuda graph is disabled because of using torch native attention backend
Fail to set RLIMIT_STACK: current limit exceeds maximum limit
[2026-06-24 23:04:51 TP0] Init torch distributed begin.
[2026-06-24 23:04:51 TP0] Init torch distributed ends. elapsed=0.05 s, mem usage=0.01 GB
[2026-06-24 23:04:51 TP0] MLX stub: skipping PyTorch model weight loading (inference runs through MLX)
[2026-06-24 23:04:51 TP0] MLX stub: initialized minimal pools (max_total_num_tokens=40960, max_running_requests=4096, zero GPU KV cache allocation)
max_total_num_tokens=40960
[2026-06-24 23:04:52 TP0] Loading MLX model: Qwen/Qwen3-0.6B
Fetching 7 files: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7/7 [00:00<00:00, 32878.08it/s]
Download complete: : 0.00B [00:00, ?B/s]                                                                                                                 | 0/7 [00:00<?, ?it/s]
[2026-06-24 23:04:53 TP0] MLX model loaded in 0.89s
[2026-06-24 23:04:53 TP0] Wired memory limit set to 17.8 GB
[2026-06-24 23:04:53 TP0] Auto-sized attention KV pool: sys_available=4.83 GB, mlx_limit=17.8 GB, mlx_used=1.11 GB, kv_budget=4.25 GB, bytes_per_slot=114688, pool_size=39833
Warmup ...
Prefill. latency: 0.16383 s, throughput:    366.23 token/s
Decode 0. Batch size: 1, latency: 0.00825 s, throughput:    121.26 token/s
Decode 1. Batch size: 1, latency: 0.00716 s, throughput:    139.65 token/s
Decode 2. Batch size: 1, latency: 0.00733 s, throughput:    136.47 token/s
Decode 3. Batch size: 1, latency: 0.00821 s, throughput:    121.85 token/s
Decode 4. Batch size: 1, latency: 0.00799 s, throughput:    125.18 token/s
Decode.  median latency: 0.00752 s, median throughput:    133.06 token/s
Total. latency:  0.233 s, throughput:    301.00 token/s
Benchmark ...
Prefill. latency: 0.01878 s, throughput:   3195.28 token/s
Decode 0. Batch size: 1, latency: 0.00735 s, throughput:    136.01 token/s
Decode 1. Batch size: 1, latency: 0.00720 s, throughput:    138.94 token/s
Decode 2. Batch size: 1, latency: 0.00709 s, throughput:    141.05 token/s
Decode 3. Batch size: 1, latency: 0.00709 s, throughput:    141.09 token/s
Decode 4. Batch size: 1, latency: 0.00717 s, throughput:    139.43 token/s
Decode.  median latency: 0.00717 s, median throughput:    139.45 token/s
Total. latency:  0.083 s, throughput:    843.11 token/s
```

Temporarily set MlxModelRunner._max_seq_len = 8
<img width="684" height="566" alt="image" src="https://github.com/user-attachments/assets/70874cbb-5f83-4b04-b3ff-798aa0173a3f" />
```
(sglang) changminbark@Chang-Mins-MacBook-Pro-M4-Pro-7:~/Desktop/OpenSource/sglang/sglang% SGLANG_USE_MLX=1 uv run python -m sglang.bench_one_batch --model-path Qwen/Qwen3-0.6B --trust-remote-code --disable-cuda-graph --tp-size 1 --batch-size 1 --input-len 60 --output-len 10 --port 43440
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/attention/fla/utils.py:223: UserWarning: Triton is not supported on current platform, roll back to CPU.
  warnings.warn(
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/quantization/awq/awq.py:52: UserWarning: Only CUDA, HIP and XPU support AWQ currently.
  warnings.warn(f"Only CUDA, HIP and XPU support AWQ currently.")
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/srt/layers/quantization/gguf.py:64: UserWarning: Only CUDA, MUSA and NPU support GGUF quantization currently.
  warnings.warn(f"Only CUDA, MUSA and NPU support GGUF quantization currently.")
/Users/changminbark/Desktop/OpenSource/sglang/sglang/python/sglang/bench_one_batch.py:13: FutureWarning: `sglang.bench_one_batch` is deprecated and will be removed in a future release; use `sglang.benchmark.one_batch` instead (e.g. `python -m sglang.benchmark.one_batch`).
  warnings.warn(
'--disable-cuda-graph' is deprecated and will be removed in a future release. Use '--cuda-graph-backend-{decode,prefill}=disabled' instead.
Cuda graph is disabled because of using torch native attention backend
Fail to set RLIMIT_STACK: current limit exceeds maximum limit
[2026-06-24 23:08:31 TP0] Init torch distributed begin.
[2026-06-24 23:08:31 TP0] Init torch distributed ends. elapsed=0.04 s, mem usage=0.00 GB
[2026-06-24 23:08:31 TP0] MLX stub: skipping PyTorch model weight loading (inference runs through MLX)
[2026-06-24 23:08:31 TP0] MLX stub: initialized minimal pools (max_total_num_tokens=40960, max_running_requests=4096, zero GPU KV cache allocation)
max_total_num_tokens=40960
[2026-06-24 23:08:32 TP0] Loading MLX model: Qwen/Qwen3-0.6B
Fetching 7 files: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7/7 [00:00<00:00, 23734.95it/s]
Download complete: : 0.00B [00:00, ?B/s]                                                                                                                 | 0/7 [00:00<?, ?it/s]
[2026-06-24 23:08:33 TP0] MLX model loaded in 0.94s
[2026-06-24 23:08:33 TP0] Wired memory limit set to 17.8 GB
[2026-06-24 23:08:33 TP0] Auto-sized attention KV pool: sys_available=5.07 GB, mlx_limit=17.8 GB, mlx_used=1.11 GB, kv_budget=4.46 GB, bytes_per_slot=114688, pool_size=41733
Warmup ...
Prefill. latency: 0.15965 s, throughput:    375.82 token/s
Decode 0. Batch size: 1, latency: 0.00799 s, throughput:    125.12 token/s
Decode 1. Batch size: 1, latency: 0.00769 s, throughput:    130.12 token/s
Decode 2. Batch size: 1, latency: 0.00759 s, throughput:    131.70 token/s
Decode 3. Batch size: 1, latency: 0.00736 s, throughput:    135.90 token/s
Decode 4. Batch size: 1, latency: 0.00798 s, throughput:    125.25 token/s
Decode.  median latency: 0.00748 s, median throughput:    133.60 token/s
Total. latency:  0.228 s, throughput:    307.44 token/s
Benchmark ...
Prefill. latency: 0.01803 s, throughput:   3328.18 token/s
Decode 0. Batch size: 1, latency: 0.00751 s, throughput:    133.15 token/s
Decode 1. Batch size: 1, latency: 0.00707 s, throughput:    141.45 token/s
Decode 2. Batch size: 1, latency: 0.00717 s, throughput:    139.47 token/s
Decode 3. Batch size: 1, latency: 0.00745 s, throughput:    134.19 token/s
Decode 4. Batch size: 1, latency: 0.00827 s, throughput:    120.87 token/s
Decode.  median latency: 0.00771 s, median throughput:    129.64 token/s
Total. latency:  0.087 s, throughput:    804.27 token/s
```

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28348539982](https://github.com/sgl-project/sglang/actions/runs/28348539982)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28348539925](https://github.com/sgl-project/sglang/actions/runs/28348539925)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
