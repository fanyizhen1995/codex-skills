---
source_id: sglang-github-closed-issues-prs
title: Fix large index overflow in topk and concat MLA
canonical_url: https://github.com/sgl-project/sglang/pull/29614
captured_at: '2026-07-01T02:12:08.971136+00:00'
content_hash: fa2aa72453cbe0488e5e48a9c7b71a5f6cde93d5d394eb2e42384a0f71009885
---
# Fix large index overflow in topk and concat MLA

URL: https://github.com/sgl-project/sglang/pull/29614
State: closed
Labels: sgl-kernel, jit-kernel
Closed at: 2026-06-30T00:04:16Z
Merged at: 

## Motivation

Fixes #29605.
Fixes #29606.

Both reports point to flattened CUDA index arithmetic overflowing before it is
used for pointer arithmetic:

- `topk_sigmoid` / `topk_softmax`: the row id still fits in `int`, but
  `thread_row * ELTS_PER_ROW` can exceed `INT_MAX` for large `(tokens, experts)`
  shapes.
- `concat_mla_absorb_q`: `blockIdx.x * blockDim.x + threadIdx.x` can exceed
  32-bit range before converting to a warp id. The sibling `concat_mla_k`
  kernel has the same flat-warp pattern, so this patch covers both.

The same patterns exist in the mirrored JIT kernel headers, so the PR updates
AOT and JIT sources together.

## Modifications

- Widen topk CTA/warp/thread row calculations to `int64_t` before row-pointer
  offset multiplication.
- Widen concat MLA flat-warp, token, and index calculations to `int64_t`.
- Keep bounded chunk/lane indexes narrow after explicit casts.
- Compute host grid sizes in `int64_t`, guard against `uint32_t` `dim3.x`
  overflow, and cast only after the guard passes.

## Accuracy Tests

No model-level accuracy benchmark was run. The patch only changes index
arithmetic and launch-size checks; the math for in-range shapes is unchanged.

Focused H200 correctness tests passed:

```text
PYTHONPATH=/workspace/sglang/sgl-kernel/python:/workspace/sglang/python \
pytest -q \
  sgl-kernel/tests/test_moe_topk_sigmoid.py \
  sgl-kernel/tests/test_moe_topk_softmax.py \
  test/registered/jit/test_concat_mla.py

1612 passed, 6 warnings in 12.61s
```

## Speed Tests and Profiling

No speed benchmark was run. This widens scalar index arithmetic on address and
launch calculations; it does not change the kernel algorithms or memory layout.

## Validation

- `git diff --check`: passed.
- `pre-commit run clang-format --files` on the six changed files: passed.
- H200, `lmsysorg/sglang:latest`, PyTorch `2.11.0+cu130`, CUDA `13.0`: rebuilt
  the SM90 `common_ops` extension containing the affected AOT kernels.
- H200 focused pytest listed above: `1612 passed, 6 warnings in 12.61s`.
- Baseline image `sgl_kernel` reproduced #29605 with the report-sized boundary
  (`rows = 128 * 65537`, `experts = 256`): `topk_sigmoid` hit `CUDA error: an
  illegal memory access was encountered`.
- Patched build passed the same boundary smoke:

```text
topk_sigmoid ok sample 0.5 0
topk_softmax ok sample 0.00390625 0
```

- JIT `topk_softmax_pack` smoke passed:

```text
topk_softmax_pack jit ok 0.25 0 16000
```

Validation gap: I did not allocate the exact #29606 `concat_mla_absorb_q`
reporter tensor shape. With the fixed last dimensions, `a`, `b`, and `out`
together exceed single-H200 memory. The existing concat MLA AOT/JIT correctness
tests passed.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28348167459](https://github.com/sgl-project/sglang/actions/runs/28348167459)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28348167428](https://github.com/sgl-project/sglang/actions/runs/28348167428)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
