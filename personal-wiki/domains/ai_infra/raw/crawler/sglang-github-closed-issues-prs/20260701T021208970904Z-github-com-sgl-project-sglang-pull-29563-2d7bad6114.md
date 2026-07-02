---
source_id: sglang-github-closed-issues-prs
title: Delay Frozen-KV MTP target pool binding
canonical_url: https://github.com/sgl-project/sglang/pull/29563
captured_at: '2026-07-01T02:12:08.970904+00:00'
content_hash: 2d7bad6114b0d44be70cafef169e90ec872a0acd60b1caf8f88acfcba0b69e12
---
# Delay Frozen-KV MTP target pool binding

URL: https://github.com/sgl-project/sglang/pull/29563
State: closed
Labels: 
Closed at: 2026-06-30T00:04:18Z
Merged at: 

## Motivation

Fixes #29021.

Frozen-KV MTP currently has a scheduler-level special case that allocates the
target KV pool before constructing the draft worker. That ordering is only
needed because the draft worker constructor eagerly reads target memory pools
and binds its frozen-KV context before target memory profiling has completed.

The draft attention backend does need read-only target KV access at runtime, but
draft worker construction should not depend on target KV pools.

## Modifications

- Stop reading target memory pools in `FrozenKVMTPDraftWorker.__init__`.
- Move target pool assignment, dummy draft pool config construction, and
  frozen-KV context binding into `FrozenKVMTPDraftWorker.alloc_memory_pool()`.
- Remove the scheduler special case that eagerly initializes target memory pools
  for Frozen-KV MTP before draft worker construction.
- Add focused unit coverage that Frozen-KV MTP can be constructed before target
  pool allocation and then bound through the normal allocation path.

## Accuracy Tests

This change is intended to be output-neutral. It changes when the Frozen-KV MTP
draft worker receives the target KV pool references, not the draft/verify math.

H200 smoke validation generated successfully with the same prompt before and
after the change. The patched run returned HTTP 200 with speculative accept
metrics present (`spec_accept_rate=0.8`, `spec_accept_length=4.0`).

## Speed Tests and Profiling

No speed benchmark was run. This is an initialization-order change; steady-state
decode kernels and scheduler policy are unchanged.

The H200 patched smoke kept CUDA graph enabled (`disable_cuda_graph=false`).

## Validation

```bash
git diff --check
```

```bash
python3 -m py_compile \
  python/sglang/srt/managers/scheduler.py \
  python/sglang/srt/speculative/frozen_kv_mtp_worker_v2.py \
  test/registered/unit/spec/test_frozen_kv_mtp_pool_init.py
```

```bash
pre-commit run --files \
  python/sglang/srt/managers/scheduler.py \
  python/sglang/srt/speculative/frozen_kv_mtp_worker_v2.py \
  test/registered/unit/spec/test_frozen_kv_mtp_pool_init.py
```

```bash
PYTHONPATH=python python3 -m pytest \
  test/registered/unit/spec/test_frozen_kv_mtp_pool_init.py -q
```

Focused pytest result: `3 passed`.

H200 runtime validation on `lmsysorg/sglang:latest`, base commit `828411e`, one
NVIDIA H200 GPU, model `google/gemma-4-E4B-it`, draft model
`google/gemma-4-E4B-it-assistant`:

- Current main control: server ready; `/generate` returned HTTP 200 with
  speculative accept metrics and CUDA graph enabled.
- Negative control with only the scheduler special case removed: exited before
  readiness at the old construction-time dependency
  (`memory_pool_config` was still `None` when the draft constructor read
  `max_running_requests`).
- Full patch: server ready; `/generate` returned HTTP 200 with
  `spec_accept_rate=0.8`, `spec_accept_length=4.0`, and CUDA graph enabled.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). N/A: no documentation change.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). Accuracy/speed are not expected to change; H200 runtime smoke is included above.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28342303729](https://github.com/sgl-project/sglang/actions/runs/28342303729)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28342303614](https://github.com/sgl-project/sglang/actions/runs/28342303614)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
