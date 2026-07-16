---
source_id: sglang-github-closed-issues-prs
title: Fix DSV4 HiSparse SWA tail allocation forwarding
canonical_url: https://github.com/sgl-project/sglang/pull/30408
captured_at: '2026-07-10T23:37:20.326828+00:00'
content_hash: c104ab42df407d787839529a9993d2c2d9073f274495a2b6dc2eeae269fe901e
---
# Fix DSV4 HiSparse SWA tail allocation forwarding

URL: https://github.com/sgl-project/sglang/pull/30408
State: closed
Labels: run-ci
Closed at: 2026-07-10T07:27:02Z
Merged at: 2026-07-10T07:27:02Z

﻿## Motivation

Fixes #30401.

`DeepSeekV4HiSparseTokenToKVPoolAllocator` wraps the hybrid SWA allocator, but it did not expose `alloc_extend_swa_tail`. Decode checks for that method before using SWA tail preallocation.

The HiSparse direct-to-host decode path also needs to keep the same SWA-tail allocation behavior. Otherwise admission can still be limited by the smaller SWA pool, and prealloc can reserve SWA pages for the whole prompt instead of only the sliding-window tail.

## Modifications

- Forward `alloc_extend_swa_tail` from `DeepSeekV4HiSparseTokenToKVPoolAllocator` to the wrapped logical allocator.
- Use full logical allocator availability for HiSparse admission when SWA tail preallocation is enabled.
- Use `alloc_extend_swa_tail` in the HiSparse direct-to-host prealloc path and set `swa_evicted_seqlen` for the evicted prefix.
- Add unit coverage for the forwarding contract, admission budgeting, and direct-host SWA tail allocation.

## Accuracy Tests

N/A. This does not change model math.

## Speed Tests and Profiling

Not run. This is an allocation/bookkeeping fix.

## Checklist

- [x] Format your code according to the code style guidance.
- [x] Add unit tests according to the unit test guidance.
- [ ] Update documentation according to documentation guidance. N/A.
- [ ] Provide accuracy and speed benchmark results. N/A for this allocation fix.
- [x] Follow the SGLang code style guidance.

## Tests

- `python -m py_compile python/sglang/srt/disaggregation/decode.py python/sglang/srt/mem_cache/allocator/hisparse.py test/registered/unit/mem_cache/test_hisparse_allocator.py`
- `python -m ruff check --select=F401,F821,UP037 python/sglang/srt/disaggregation/decode.py python/sglang/srt/mem_cache/allocator/hisparse.py test/registered/unit/mem_cache/test_hisparse_allocator.py`
- `python -m black --check python/sglang/srt/disaggregation/decode.py python/sglang/srt/mem_cache/allocator/hisparse.py test/registered/unit/mem_cache/test_hisparse_allocator.py`
- `python -m isort --check-only python/sglang/srt/disaggregation/decode.py python/sglang/srt/mem_cache/allocator/hisparse.py test/registered/unit/mem_cache/test_hisparse_allocator.py`
- `git diff --check`
- Not run locally: `python -m pytest test/registered/unit/mem_cache/test_hisparse_allocator.py -q` (torch is unavailable in the local Python environment).















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29004349572](https://github.com/sgl-project/sglang/actions/runs/29004349572)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29004349453](https://github.com/sgl-project/sglang/actions/runs/29004349453)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
