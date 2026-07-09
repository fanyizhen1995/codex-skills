---
source_id: sglang-github-closed-issues-prs
title: '[DSA] Fix IMA in fused top-k v2: write all output slots on tie overflow'
canonical_url: https://github.com/sgl-project/sglang/pull/30512
captured_at: '2026-07-08T23:36:33.789649+00:00'
content_hash: 971e7b927d9b0c091f256b7e403588b41638d9a29a45a4ff104404817416930e
---
# [DSA] Fix IMA in fused top-k v2: write all output slots on tie overflow

URL: https://github.com/sgl-project/sglang/pull/30512
State: closed
Labels: high priority, run-ci, jit-kernel, bypass-fastfail, run-ci-extra
Closed at: 2026-07-08T11:49:27Z
Merged at: 2026-07-08T11:49:27Z

## Motivation

Serving GLM-5.2 with MTP (EAGLE) and the fused DSA top-k v2 path (`SGLANG_OPT_USE_TOPK_V2=1`, default) hits a CUDA illegal memory access within ~1 min of decode once sequences exceed `index_topk` (2048), under CUDA graphs with long `--context-length` (TP-only; `--disable-cuda-graph` does not reproduce). A GPU coredump pins the fault to the sparse-MLA decode FMHA's `UTMALDG.2D.GATHER4` consuming a garbage paged-KV index produced by top-k v2.

Root cause: `collect` keeps at most `kMaxNumTie = 1024` threshold-bin ties, so when `above_count < topk − 1024`, `handle_tie` fills fewer than `topk` output slots. The transform pass page-translates **all** `topk` slots, and the unwritten ones hold uninitialized staging memory → garbage KV index → IMA downstream. Verified two ways: a direct kernel test (scores with 500 above-threshold elements + a large tie set → exactly `500 + 1024` slots written, the rest stale), and a device-side printf diagnostic under live graph replay on the crash workload: 41 rows with `equal_count > 1024` (up to 1536) in a ~9-min bench, of which 4 had `above_count < 1024` — i.e. 70–135 unwritten slots each pre-fix. Reproduced with `enable_smem_spilling()` disabled, ruling out smem spilling as a factor. Note the "ties" are same-coarse-bin (fp16 top-bits), not exact equality — the indexer score distribution routinely concentrates >1024 elements in the bin straddling the top-k boundary.

## Modifications

In `handle_tie` (shared by all sub-kernels), pad the uncoverable slots `[num_ties, topk)` with `-1` — the existing "no token" sentinel, same as the trivial path — so every output slot is written. 9 lines, ≤2 loop iterations per thread once per row.

## Accuracy Tests

GLM-5.2-NVFP4, 4×GB300, TP4, EAGLE 5-1-6, fp8 KV, same sgl-eval harness:

| config | GSM8K (greedy, full) | AIME25 (avg@16, temp 1.0, thinking) |
|---|---|---|
| legacy top-k (`SGLANG_OPT_USE_TOPK_V2=0`) | 0.9500 | — |
| fused v2 + this fix | 0.9545 | 0.9208 ± 0.005 (majority@16 0.933, 0.2% truncated) |

## Speed Tests and Profiling

Fused v2 kernel otherwise untouched; accept length (~5.5–5.9) and gen throughput (~2400–2670 tok/s) unchanged. The previously-crashing repro (context 90000, random input 8192, conc 16, graphs ON) runs clean with the fix; without it, IMA in <1 min on the same config.

Full agentic sweep (OpenHands/swe_smith, 2 TP4 configs × concurrency {1,2,4,8,16}, real acceptance, graphs ON): **0 IMA** — this workload reliably crashed at the concurrency-16 step without the fix.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

🤖 Generated with [Claude Code](https://claude.com/claude-code)



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28935925182](https://github.com/sgl-project/sglang/actions/runs/28935925182)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28937016749](https://github.com/sgl-project/sglang/actions/runs/28937016749)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
