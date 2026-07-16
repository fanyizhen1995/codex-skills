---
source_id: sglang-github-closed-issues-prs
title: '[Bugfix] Stamp capture-time num_tokens_per_req in multi-layer EAGLE; close
  jit_kernel CI filter gaps'
canonical_url: https://github.com/sgl-project/sglang/pull/31367
captured_at: '2026-07-15T23:40:28.351638+00:00'
content_hash: 91b6ef1cd60c8c7f344bedf32c9a6acfc3ba6309a62586b11bf32b4141b37b0a
---
# [Bugfix] Stamp capture-time num_tokens_per_req in multi-layer EAGLE; close jit_kernel CI filter gaps

URL: https://github.com/sgl-project/sglang/pull/31367
State: closed
Labels: quant, lora, hicache, blackwell
Closed at: 2026-07-15T22:24:32Z
Merged at: 2026-07-15T22:24:32Z

## Motivation

Two follow-ups to the #31013 draft_extend_v2 regression (the backend/test contract itself was settled by #31332):

1. **A capture site still violates the new contract.** Since #31013 the attention backends read
   `spec_info.num_tokens_per_req` when building capture-time cuda-graph metadata
   (`trtllm_mha_backend._build_cuda_graph_metadata`; the flashattention backend capture path).
   The multi-layer EAGLE runner stamps that field on its **replay** spec_info (`prepare()`), but
   the **capture** spec_info built in `get_forward_batch()` leaves it at the dataclass default —
   `EagleDraftExtendInput` defaults to `-1` with no auto-fill (unlike `EagleVerifyInput`) — so `-1`
   is baked into the captured metadata and the in-graph rebuild runs with `q_stride=-1`.
2. **The regression merged green** because the `jit_kernel` paths-filter doesn't cover what the
   base-b-kernel suites actually test: membership is self-registered via `register_cuda_ci`
   (4 tests live under `test/registered/attention/`, exercising `srt/layers/attention` backends),
   and the migrated `sglang.kernels` namespace (#30044) is in no filter at all. It only surfaced
   on #31279, fast-failing 24 jobs.

## Modifications

- `multi_layer_eagle_draft_extend_cuda_graph_runner.py`: stamp `num_tokens_per_req` on the
  capture-time spec_info in `get_forward_batch()`, mirroring the existing `prepare()` stamp.
- `_pr-test-check-changes.yml`: add `python/sglang/kernels/**`, `test/registered/attention/**`,
  `python/sglang/srt/layers/attention/**` to the `jit_kernel` filter (all existing entries kept).
  If the last glob is too broad, it can be narrowed to `linear/kernels/**` +
  `trtllm_mha_backend.py`, at the cost of re-opening the gap for the next backend file.

## Accuracy Tests

- `test/registered/attention/test_trtllm_mha_graph_metadata.py`: 149 passed on this branch
  (latest main with #31332 merged in).
- Filter change replayed against real changed-file sets (parsed from the actual workflow YAML):
  #31013 now triggers, #31279 still triggers, jit-only / kernels-only / attention-test-only edits
  trigger, unrelated docs edit does not.

## Speed Tests and Profiling

N/A — a capture-time metadata seeding fix plus a CI filter change; no kernel math touched.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29451819815](https://github.com/sgl-project/sglang/actions/runs/29451819815)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29451819452](https://github.com/sgl-project/sglang/actions/runs/29451819452)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
