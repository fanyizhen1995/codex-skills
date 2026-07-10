---
source_id: sglang-github-closed-issues-prs
title: '[Bug Fix] Fix NSATokenToKVPool.get_cpu_copy/load_cpu_copy missing mamba_indices
  param'
canonical_url: https://github.com/sgl-project/sglang/pull/25833
captured_at: '2026-07-09T23:36:35.337129+00:00'
content_hash: 4757bcf16a195854e8dc211b37e7ba5721ad2ed84617a8cefc9fac4c829e001e
---
# [Bug Fix] Fix NSATokenToKVPool.get_cpu_copy/load_cpu_copy missing mamba_indices param

URL: https://github.com/sgl-project/sglang/pull/25833
State: closed
Labels: run-ci
Closed at: 2026-07-09T07:51:27Z
Merged at: 

## Motivation

Fixes #25828

`NSATokenToKVPool` overrides `get_cpu_copy()` and `load_cpu_copy()` from its parent `MLATokenToKVPool` but drops the `mamba_indices=None` parameter that the base class `KVCache` defines. This causes a `TypeError` when `retract_decode()` tries to offload KV cache in PD disaggregation mode under KV memory pressure, crashing the scheduler.

```
KVCache (base)                            ← defines interface
├── get_cpu_copy(self, indices, mamba_indices=None)
└── load_cpu_copy(self, kv, indices, mamba_indices=None)

MLATokenToKVPool(KVCache)                 ✓ (indices, mamba_indices=None)
  └── NSATokenToKVPool(MLATokenToKVPool)  ✗ (indices)  ← was missing mamba_indices
```

## Modifications

Add `mamba_indices=None` to both method signatures in `NSATokenToKVPool` and pass through to `super()`:

- `get_cpu_copy(self, indices)` → `get_cpu_copy(self, indices, mamba_indices=None)`
- `load_cpu_copy(self, kv_cache_cpu_dict, indices)` → `load_cpu_copy(self, kv_cache_cpu_dict, indices, mamba_indices=None)`

This is safe — `mamba_indices` is only consumed by `HybridLinearKVPool` (Mamba hybrid models). All other subclasses including `MLATokenToKVPool` accept and ignore it.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29002801888](https://github.com/sgl-project/sglang/actions/runs/29002801888)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29002801797](https://github.com/sgl-project/sglang/actions/runs/29002801797)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
