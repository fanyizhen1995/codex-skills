---
source_id: sglang-github-closed-issues-prs
title: Fix large tensor index overflow in CUDA kernels
canonical_url: https://github.com/sgl-project/sglang/pull/29608
captured_at: '2026-07-01T02:12:08.971668+00:00'
content_hash: 183cde4f263fe5be6a1aea8996238337f9488b0b9c294ae30fe8e1500a3c2689
---
# Fix large tensor index overflow in CUDA kernels

URL: https://github.com/sgl-project/sglang/pull/29608
State: closed
Labels: sgl-kernel
Closed at: 2026-06-29T23:44:50Z
Merged at: 

## Motivation

Fixes #29597.
Fixes #29602.
Fixes #29603.

These reports all point to 32-bit intermediate arithmetic overflowing while
computing flattened CUDA offsets or launch sizes:

- `merge_state_v2`: `token_idx * num_heads * head_size` and
  `num_tokens * num_heads * threads_per_head`.
- `causal_conv1d_fwd`: `channel_id * params.x_c_stride`.
- `fused_qk_norm_rope`: `tokenIdx * num_heads * head_dim` and host-side total
  warp/grid calculations.

When those products exceed `INT_MAX`/`UINT_MAX`, the resulting offset can wrap
before it is used for pointer arithmetic or launch sizing.

## Modifications

- Widen the affected flattened offset and total-thread/warp calculations to
  64-bit integer arithmetic.
- Keep bounded per-head/per-pack indexes in their existing narrow types after
  explicit casts.
- Add host-side `dim3.x` upper-bound checks before casting grid sizes back to
  `uint32_t`.
- Widen `ConvParamsBase::index_t` from `uint32_t` to `int64_t` so causal-conv
  tensor strides do not truncate before device pointer offset arithmetic.

## Accuracy Tests

No model-level accuracy benchmark was run. The change is intended to preserve
the same math for in-range shapes and only changes index arithmetic so large
flattened offsets do not wrap.

Focused H200 kernel correctness tests passed:

```text
python3 -m pytest -q \
  sgl-kernel/tests/test_merge_state_v2.py::test_merge_attn_states \
  sgl-kernel/tests/test_fused_qk_norm_rope.py::test_fused_qk_norm_rope \
  sgl-kernel/tests/test_causal_conv1d.py::test_causal_conv1d_varlen \
  --tb=short --disable-warnings -x

398 passed, 21 warnings in 37.07s
```

## Speed Tests and Profiling

No speed benchmark was run. This only widens scalar index/stride arithmetic on
the affected address and launch calculations; it does not change the kernel
algorithm or memory layout.

## Validation

- `git diff --check`: passed.
- Docker `clang-format` 16 over the three changed files: passed.
- H200, `lmsysorg/sglang:latest`, PyTorch `2.11.0+cu130`, CUDA `13.0`: rebuilt
  the SM90 `common_ops` extension containing the affected kernels.
- H200 focused pytest listed above: `398 passed, 21 warnings in 37.07s`.

Validation gap: I did not allocate the exact huge boundary tensors from the
issue examples; some of those shapes would require very large memory and long
kernel runtimes. The validation covers compileability and the existing focused
correctness paths on H200.

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28346940641](https://github.com/sgl-project/sglang/actions/runs/28346940641)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28346940518](https://github.com/sgl-project/sglang/actions/runs/28346940518)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
