---
source_id: sglang-github-closed-issues-prs
title: '[Kernel] Add SM90 Q8KV8 FP8 Sparse MLA Prefill JIT Kernel with Tests and Benchmark'
canonical_url: https://github.com/sgl-project/sglang/pull/25751
captured_at: '2026-07-01T02:12:08.969222+00:00'
content_hash: 0512ee634cb551c9acd0c2acb681bfd190b87594ba162193a518cd87ee947bc4
---
# [Kernel] Add SM90 Q8KV8 FP8 Sparse MLA Prefill JIT Kernel with Tests and Benchmark

URL: https://github.com/sgl-project/sglang/pull/25751
State: closed
Labels: run-ci, jit-kernel, run-ci-extra
Closed at: 2026-06-30T01:00:11Z
Merged at: 2026-06-30T01:00:11Z

# Summary
This PR adds a Q8KV8 FP8 sparse MLA prefill JIT kernel for SM90, together with its Python wrapper, correctness/accuracy tests, and performance benchmark.

This PR is part of the roadmap tracked in #25746 (PR1 of 2).

# Takeaways
- **Performance**: Q8KV8 is **1.15x - 1.31x faster** than the Q16/BF16 FlashMLA sparse prefill baseline on representative long-context sparse MLA shapes.
- **Kernel correctness**: Q8KV8 matches the dequantized-FP8 FP32 reference with **~0.7% rel_mean error**, validating the intended FP8 computation path.
- **Precision tradeoff**: Compared with the Q16/KV16 sparse prefill path, Q8KV8 shows an expected **~2.8% accuracy drop**, mainly from BF16-to-FP8 Q/K/V quantization.


# Motivation
<!-- Describe the purpose and goals of this pull request. -->
Sparse MLA prefill becomes a major contributor to long-context latency. FlashMLA already lowers KV to FP8 for this kernel while keeping Q in BF16/FP16; promoting Q to FP8 (Q8KV8) closes the remaining precision gap, unlocking full FP8 tensor-core throughput and halving Q-side memory traffic at long context.

The kernel is kept under `sglang.jit_kernel` so it can be reviewed, tested, and benchmarked as a standalone kernel before any future runtime integration.

# Context
See the project roadmap and tracking issue: #25746. This PR delivers **PR1** of that roadmap — a standalone, independently reviewable kernel building block. PR2 will build on the merged kernel API to wire it into the NSA prefill backend and report end-to-end serving gains.

# Modifications
<!-- Detail the changes made in this pull request. -->
Included in this PR:
- An SM90 Q8KV8 sparse MLA prefill CUDA C++ kernel using CUTLASS/CuTe primitives and native Hopper FP8 GMMA
- Python JIT wrapper under `sglang.jit_kernel`
- Accuracy & correctness tests under `python/sglang/jit_kernel/tests`
- Performance benchmark under `python/sglang/jit_kernel/benchmark`

## Kernel Implementation
The kernel is a SM90 implementation of FP8 sparse MLA prefill, with an algorithm inspired by DeepSeek FlashMLA but rewritten for the Q8KV8 path.
- **Native FP8 attention on Hopper.** Both QK and PV are issued as native FP8 GMMA on SM90. There is no on-the-fly BF16 dequant on the inner loop, so the kernel benefits directly from Hopper's higher FP8 throughput and lower KV memory traffic.
- **Producer / consumer pipeline.** A producer stage streams FP8 KV from gmem into shared memory and prepares it for the PV GMMA, while consumer stages run QK, online softmax, and PV. This keeps memory movement and compute overlapped on the critical path.
- **Specialized for the sparse MLA prefill shape.** The kernel is built around `d_v = 512`, `h_kv = 1`, and the two query/key head dimensions used in practice (`d_qk = 512` and `d_qk = 576`, the latter matching the V3.2-style `nope + rope` layout). Sparse indexing is aligned to the kernel's tile granularity.
- **Compile-time specialization for optional features.** `d_qk`, `attn_sink`, and per-row `topk_length` are compile-time switches, so the common no-sink path stays branch-free while the full path still supports `attn_sink` and `topk_length` when callers need them.
- **BF16 output with FP32 softmax metadata.** The kernel returns the BF16 attention output together with per-row `max_logits` and `lse`, matching the sparse MLA prefill API and preserving the softmax metadata needed for correctness checks and numerically stable merging of partial attention results in downstream attention paths.
- **Python integration.** The kernel is exposed via a JIT-loaded wrapper under `sglang.jit_kernel`. The wrapper caches the resolved entry points and output buffers, and registers each dispatch path as a `custom_op` so calls integrate with `torch.library` / `torch.compile` and the existing kernel API logging.

# Experimental Results
## Performance Benchmark
<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->
The benchmark checks CI regressions and real NSA serving throughput gains. Cases are split into two groups. The CI-sized group provides a lightweight end-to-end smoke check that runs quickly in CI and confirms the kernel produces a measurable result without requiring a full-scale context. The long-context group targets the actual NSA prefill scenario — large batch size, long KV sequence, and substantial topk — where native FP8 GMMA throughput and reduced KV bandwidth are expected to have the largest impact. All cases `d_v = 512`, `h_kv = 1`, and both `d_qk` variants (`512` and `576`) are covered.

The baseline is the existing Q16/BF16 FlashMLA sparse prefill path (`sgl_kernel.flash_mla.flash_mla_sparse_fwd`), representing a production NSA deployment, and all speedup numbers reflect the direct like-for-like latency improvement from switching to the Q8KV8 path on the same hardware.

**Reproduction:**
```
PYTHONPATH=python python3 python/sglang/jit_kernel/tests/test_sparse_mla_q8kv8_prefill_sm90.py
```

**CI-sized (regression smoke) results:**
CI-sized cases (`s_q = 2`) are small enough for fast regression smoke runs and verify the kernel produces a measurable result without the full context. 



Shape `(s_q, s_kv, h_q, d_qk, topk)` | Q16/BF16 FlashMLA | Q8KV8 FP8 JIT | Speedup
-- | -- | -- | --
`(2, 1024, 64, 512, 128)` | 16.576 us | 11.776 us | 1.407x
`(2, 1024, 64, 576, 128)` | 15.072 us | 12.000 us | 1.256x

**Representative long-context results:**
The larger long-context cases (`s_q = 4096`, `s_kv` up to 65536, `topk` up to 2048) represent the actual NSA prefill workload where reduced KV bandwidth and native FP8 execution are expected to matter most; these shapes cover both the `d_qk = 576` (V3.2-style nope+rope) and `d_qk = 512` head dimension variants.


Shape `(s_q, s_kv, h_q, d_qk, topk)` | Q16/BF16 FlashMLA | Q8KV8 FP8 JIT | Speedup
-- | -- | -- | --
`(4096, 8192, 128, 576, 2048)` | 3489.74 us | 3039.23 us | 1.148x
`(4096, 32768, 128, 576, 2048)` | 4138.08 us | 3162.14 us | 1.309x
`(4096, 65536, 128, 576, 2048)` | 4385.41 us | 3372.99 us | 1.300x
`(4096, 8192, 64, 512, 512)` | 602.82 us | 487.97 us | 1.235x
`(4096, 32768, 64, 512, 512)` | 602.46 us | 518.16 us | 1.163x

The Q8KV8 kernel is consistently faster across all tested configurations, with speedups ranging from **1.15x** to **1.41x**. The gains grow with sequence length and topk size, which is the expected pattern: at longer context the kernel spends more time in the inner loop where native FP8 GMMA throughput and reduced KV traffic have the largest impact. This aligns with the primary motivation for this kernel — improving sparse MLA prefill latency in long-context NSA workloads.

## Correctness and Accuracy Tests
<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->
The correctness and accuracy tests are designed to validate two things: first, that the CUDA kernel correctly implements the intended Q8KV8 sparse MLA computation; second, that the expected numerical tradeoff versus the existing Q16/KV16 path is understood and bounded.

For kernel correctness, the Q8KV8 output is compared against a PyTorch FP32 sparse-attention reference that dequantizes the same FP8 Q/K/V tensors. This isolates kernel implementation error from the BF16-to-FP8 quantization error.

All cases use `d_v = 512` and `h_kv = 1`, matching the sparse MLA layout targeted by this PR.


Group | Cases | What It Covers
-- | -- | --
Basic no-sink correctness | 2 | Both supported head dimensions, `d_qk = 512` and `d_qk = 576`, through the common no-sink path used as the current NSA E2E proxy
Sink / topk_length feature coverage | 4 | The full dispatch path with `attn_sink` and per-row `topk_length`, including minimal query count, multiple query rows, and larger topk/KV sizes
Cross-shape corner coverage | 2 | Non-trivial query counts and larger sparse shapes for both `d_qk = 512` and `d_qk = 576`, including non-small `s_q` cases that exercise more CTA scheduling patterns
Precision-focused no-sink coverage | 4 | Larger no-sink cases for both head dimensions, used to report aggregate precision metrics on the path closest to current NSA serving behavior

**Reproduction and results:**
```
$ PYTHONPATH=python python3 python/sglang/jit_kernel/tests/test_sparse_mla_q8kv8_prefill_sm90.py
12 / 12 passed

max_diff   ≤ 1.80e-04
p99_diff   ≤ 8.14e-05
mean_diff  ~  2e-05
rel_mean   ~  0.71% - 0.73%
cos_diff   ~  2.7e-05
fail_rate  = 0%
```

**Q8KV8 kernel vs dequantized-FP8 FP32 reference results:**
The **~0.7% relative mean error** measures the kernel implementation error for the intended FP8 path: both the CUDA kernel and the PyTorch reference consume the same FP8 inputs, with the reference dequantizing them to FP32 before computing sparse attention. This shows the CUDA kernel closely matches the expected Q8KV8 computation.

### Accuracy Test: Q8KV8 vs. Q16/KV16 Sparse Prefill Precision Tradeoff
We compare the Q8KV8 path against the existing Q16/KV16 sparse prefill kernel to quantify the expected precision tradeoff when switching from the BF16/Q16 path to the FP8 Q8KV8 path. The observed accuracy drop is about **2.8%**, which is expected for an FP8 attention path.
This gap is mainly introduced by BF16-to-FP8 quantization of Q/K/V before attention, then amplified through QK softmax and PV accumulation. The Q8KV8 kernel therefore trades a small numerical drop for consistent latency gains on the sparse MLA prefill workloads targeted by this PR, and the result should be interpreted together with the latency gains reported in the benchmark section.


## Checklist
- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28278400416](https://github.com/sgl-project/sglang/actions/runs/28278400416)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28344823072](https://github.com/sgl-project/sglang/actions/runs/28344823072)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
