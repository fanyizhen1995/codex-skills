---
source_id: sglang-github-closed-issues-prs
title: Fix gfx95 bpreshuffle FP8 activation scale layout
canonical_url: https://github.com/sgl-project/sglang/pull/29275
captured_at: '2026-07-08T23:36:33.790192+00:00'
content_hash: 0d8d946a0b5b11174b5ace1706c5877cb2a20ddc09624fd6b586aeada8d488f0
---
# Fix gfx95 bpreshuffle FP8 activation scale layout

URL: https://github.com/sgl-project/sglang/pull/29275
State: closed
Labels: amd, deepseek, run-ci, run-ci-extra
Closed at: 2026-07-08T17:55:09Z
Merged at: 2026-07-08T17:55:09Z

## Motivation

On gfx950/ROCm 7.2, the AITER/CK `gemm_a8w8_blockscale_bpreshuffle` path consumes block-FP8 activation scales with a physical layout requirement that is not the same as the logical `(M, K / 128)` scale values. GLM-5.2-FP8 routes many real linear shapes through this bpreshuffle path, and with the current producer/consumer contract the model can silently generate corrupted outputs even when the logical scale values are correct.

This PR fixes the SGLang-side scale-layout contract for gfx95 bpreshuffle consumers. It is intended to pair with the CK-side bpreshuffle kernel fix in ROCm/rocm-libraries#8639; the two fixes cover different parts of the same GLM-5.2 gfx950 block-FP8 failure mode.

Relevant links:

- sgl-project/sglang#28685
- sgl-project/sglang#28471
- ROCm/rocm-libraries#8639
- ROCm/aiter#3261

## Modifications

- Add helpers in `fp8_utils.py` to materialize 2D FP8 activation-scale tensors into the physical storage layout consumed by gfx95 bpreshuffle GEMM while preserving logical scale values.
- Keep quant producers emitting normal logical scale values with `transpose_scale=False`, then materialize only at gfx95 bpreshuffle consumer boundaries.
- Apply the helper to shared DeepSeekV2/common GLM-5.2 paths:
  - communicator FP8 quantized hidden-state handoff
  - MHA/MLA q projection handoff
  - MLA attention output to `o_proj`
  - generic `aiter_w8a8_block_fp8_linear`
- Add a registered CPU unit test for the materialization helper and tuple helper.

The change is gated by `_use_aiter_bpreshuffle_gfx95`, so non-gfx95, non-HIP, non-AITER, non-bpreshuffle paths should not be affected.

Thought on why DeepSeek-V4 FP8 doesn't have the issue:

- The DSv4 cookbook route uses DSv4-specific attention/indexer/compressor/cache paths with additional contiguous packed-layout boundaries. In other words, DSv4’s indexer path already normalizes/owns that physical layout with .contiguous() and packed cache writers
- On the other hands, GLM-5.2 subclasses/uses the DeepSeekV2/common runtime paths and those paths pass `(q_input, x_scale)` tuples directly into generic block-FP8 linear consumers.

## Accuracy Tests

GLM-5.2-FP8, TP4 on 4xMI350, GSM8K 200Q / 5-shot:

- CK PR https://github.com/ROCm/rocm-libraries/pull/8639 without scale materialization: 0/82 (aborted after decisive failure).
- CK PR https://github.com/ROCm/rocm-libraries/pull/8639 + scale materialization + SGLANG_FP8_PAGED_MQA_LOGITS_TORCH=1: 192/200, accuracy 0.96.
- CK PR https://github.com/ROCm/rocm-libraries/pull/8639 + scale materialization + SGLANG_FP8_PAGED_MQA_LOGITS_TORCH=0: 186/200, accuracy 0.93.
bpreshuffle-off: 184/200, accuracy 0.92.

DeepSeek-V4 FP8 TP8 on 8xMI350 GSM8K 200Q / 5-shot:

- cookbook: 197/200
- CK PR https://github.com/ROCm/rocm-libraries/pull/8639: 198/200
- CK PR https://github.com/ROCm/rocm-libraries/pull/8639 + scale materialization: 196/200

## Speed Tests and Profiling

Short TP4, GLM-5.2-FP8 prompts:

- Materialized bpreshuffle route tool-call prompts: 54/54, average 3.022s.
- Bpreshuffle-off tool-call prompts: 54/54, average 3.489s.
- Materialized bpreshuffle route factual prompts: 9/9, average 1.446s.
- Bpreshuffle-off factual prompts: 9/9, average 1.706s.

No materialization slowdown was observed.

## Checklist

- [x] Format your code according to the pre-commit guide: `pre-commit run --all-files` passed.
- [x] Add unit tests: added `test/registered/unit/layers/test_fp8_bpreshuffle_scale.py`.
- [x] Update documentation: no user-facing docs are changed in this runtime PR; GLM cookbook/docs are tracked separately in sgl-project/sglang#28471.
- [x] Provide accuracy and speed benchmark results: included above.
- [x] Follow the SGLang code style guidance.













































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28904230703](https://github.com/sgl-project/sglang/actions/runs/28904230703)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28904230605](https://github.com/sgl-project/sglang/actions/runs/28904230605)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
