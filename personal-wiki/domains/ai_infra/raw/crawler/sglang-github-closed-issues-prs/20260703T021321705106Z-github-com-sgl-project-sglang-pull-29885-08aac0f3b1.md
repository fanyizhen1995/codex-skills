---
source_id: sglang-github-closed-issues-prs
title: '[DeepSeek V4] Cover both dense and sparse prefill paths in the compress attention
  unittest'
canonical_url: https://github.com/sgl-project/sglang/pull/29885
captured_at: '2026-07-03T02:13:21.705106+00:00'
content_hash: 08aac0f3b1c58909cf66771f68003f0027b1ac207b8b8d15b8db44132e3507bf
---
# [DeepSeek V4] Cover both dense and sparse prefill paths in the compress attention unittest

URL: https://github.com/sgl-project/sglang/pull/29885
State: closed
Labels: deepseek
Closed at: 2026-07-02T04:20:12Z
Merged at: 2026-07-02T04:20:12Z

## Motivation

`test_compress_attention_cases` fails on `dsv4_c4_extend` since `SGLANG_OPT_FLASHMLA_SPARSE_PREFILL` became default-true (#29775). This is a test-fixture gap, not a kernel issue: the smoke fixture skips the C4 indexer and only seeds the dense-path metadata (`c4_sparse_page_indices` / `c4_sparse_topk_lengths`), which only the dense `flash_mla_with_kvcache` extend path consumes. The sparse prefill path instead consumes `c4_sparse_raw_indices` (normally written by the indexer) and derives per-query lengths as `(pos + 1) // 4` — so once the default flipped, the case silently rerouted onto a path attending uninitialized indices and deterministically mismatched the reference (~23% of elements).

The sparse c4 extend path had no unit coverage at all: with 16 query tokens (far below `_LARGE_INDEXER_QUERY_THRESHOLD`), the case always took the dense path before the flip.

## Modifications

Test-only; no production code changes.

- `run_dsv4_compress_attention_case` gains a `sparse_prefill` knob that pins `SGLANG_OPT_FLASHMLA_SPARSE_PREFILL` via `envs.…override(...)`. `test_compress_attention_cases` pins the dense path, so future default flips cannot reroute it again.
- New `test_compress_attention_cases_sparse_prefill` covers the c4/c128 extend cases on the sparse path (decode never reaches sparse prefill). For c4, `_seed_c4_sparse_prefill_indices` writes the indexer's short-sequence sequential output (`[0..len)`, `-1` beyond) into `c4_sparse_raw_indices` and mirrors the same causal set into `c4_sparse_page_indices` / `c4_sparse_topk_lengths`, so the existing pure-torch reference attends identical entries unchanged; the raw==physical identity this relies on is asserted.
- Both modes assert the exercised path via `forward_metadata.sparse_prefill_cache`, so a selector change fails loudly instead of silently testing the wrong path.

## Accuracy Tests

GB200 (sm100), source `main` @ 70df09b833:

- Unpatched baseline: `dsv4_c4_extend` fails with 22.9% mismatched elements (matches the CI failure signature); the other 15 tests pass.
- Patched: `Ran 17 tests ... OK`. The new sparse c4 case passes within the same 8e-2 tolerance as the dense case once fed properly seeded indices.

## Speed Tests and Profiling

n/a (test-only).

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation (n/a — test-only).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

cc @Fridge003





























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28564065348](https://github.com/sgl-project/sglang/actions/runs/28564065348)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28564065336](https://github.com/sgl-project/sglang/actions/runs/28564065336)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
