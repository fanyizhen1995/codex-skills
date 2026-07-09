---
source_id: sglang-github-closed-issues-prs
title: 'feat(srt): add phase-1 INT8 KV cache for Triton MHA'
canonical_url: https://github.com/sgl-project/sglang/pull/22004
captured_at: '2026-07-08T23:36:33.799840+00:00'
content_hash: ea449670d1448a2a009c3a8610ac38a3fb93085acec2f73d3263d1af39aba487
---
# feat(srt): add phase-1 INT8 KV cache for Triton MHA

URL: https://github.com/sgl-project/sglang/pull/22004
State: closed
Labels: documentation, quant
Closed at: 2026-07-08T04:01:22Z
Merged at: 

## Motivation

This PR adds phase-1 INT8 KV cache support for MHA models on the Triton attention backend.

The goal is to reduce KV-cache memory footprint and improve throughput in memory-constrained serving scenarios, while keeping the first upstream version intentionally small in scope and explicit about its current limitations.

## Modifications

- add `--int8-kv-cache` as a new server argument
- add phase-1 compatibility validation for INT8 KV cache
- add an INT8 KV memory pool for MHA KV storage
- add Triton quantize/dequantize helpers for INT8 KV cache storage and gather
- add Triton INT8 decode attention path
- wire INT8 KV cache into Triton extend/decode attention flow
- add unit tests for server-args validation and INT8 KV quant/dequant helpers
- update quantized KV cache documentation

Phase-1 supported scope:
- MHA only
- Triton attention backend only
- `--kv-cache-dtype auto`
- `--page-size 1`

Phase-1 unsupported scope:
- MLA
- hybrid SWA memory pools
- double sparsity
- PD disaggregation
- hierarchical cache
- deterministic inference
- Ascend attention backend

Behavior notes:
- radix cache is disabled automatically in phase-1
- this PR is intentionally scoped as a first upstream step before broader backend/model coverage

## Accuracy Tests

Local validation was performed on Qwen3-32B INT8 KV cache experiments.

Added unit tests:
- INT8 KV cache server-args validation
- INT8 KV quant/dequant helper tests

Passed locally:
- `python3 -m pytest test/registered/core/test_server_args.py -k Int8KVCacheServerArgs -q`
- `python3 -m pytest test/registered/core/test_int8_kv_kernels.py -q`

I can attach representative local evaluation screenshots in PR comments if helpful.

## Benchmarking and Profiling

Local benchmark snapshot on Qwen3-32B:

BF16 KV cache:
- output throughput: `111.61 tok/s`
- median TTFT: `767.39 ms`
- mean ITL: `49.23 ms`

INT8 KV cache:
- output throughput: `139.43 tok/s`
- median TTFT: `978.13 ms`
- mean ITL: `52.68 ms`

Observed result:
- output throughput improved by about `24.9%`
- TTFT and ITL were not improved in this local snapshot
- this phase-1 implementation should therefore be viewed primarily as a capacity / throughput oriented optimization rather than a universal latency optimization

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review Process

This PR is currently kept as Draft for early feedback on scope and implementation direction.
