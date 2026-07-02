---
source_id: sglang-github-closed-issues-prs
title: '[KDA-Pilot] Add LTX2 QKNorm split-RoPE CUDA fast path'
canonical_url: https://github.com/sgl-project/sglang/pull/29708
captured_at: '2026-07-02T02:12:27.266585+00:00'
content_hash: 2f3ab900abebca8e1114b845c6961834779d7a2944218c3ca2c8a3c03c303f14
---
# [KDA-Pilot] Add LTX2 QKNorm split-RoPE CUDA fast path

URL: https://github.com/sgl-project/sglang/pull/29708
State: closed
Labels: run-ci, diffusion, jit-kernel, run-ci-extra
Closed at: 2026-07-01T06:42:07Z
Merged at: 2026-07-01T06:42:07Z

## Motivation

Add a native CUDA JIT fast path for the LTX-2.3 Q/K RMSNorm + split-RoPE attention preprocessing pattern from KDA-Pilot task `b200_ltx2_qknorm_split_rope__bitwise`.

The hot pattern is equivalent to:

```python
q = apply_split_rotary_emb(q_norm(q), (q_cos, q_sin)).to(torch.bfloat16)
k = apply_split_rotary_emb(k_norm(k), (k_cos, k_sin)).to(torch.bfloat16)
```

for BF16 contiguous `[B, S, H]` Q/K tensors and 4D split-RoPE cos/sin tensors with production LTX-2.3 layouts. The KDA final candidate preserves bitwise equality to this BF16 attention-input contract while avoiding the separate eager RMSNorm/RoPE materialization path.

## Modifications

- Add `diffusion_ltx2_qknorm_split_rope` lightweight JIT CUDA custom op.
- Mark the CUDA csrc file with the MIT HAN Lab Kernel Design Agents provenance comment.
- Register the op eagerly with a fake impl so direct `torch.compile(fullgraph=True)` sees an opaque custom op instead of tracing JIT/module loading.
- Support the LTX-2.3 production split-RoPE rows with `head_dim in {64, 128}`, BF16 inputs/weights/cos/sin, real non-contiguous cos/sin strides, and independent Q/K sequence lengths.
- Wire `LTX2Attention` to try this CUDA path by default for TP=1, `torch.nn.RMSNorm`, 4D split-RoPE inputs, then fall back to the existing RMSNorm + RoPE implementation if unsupported or if JIT load/launch fails once.
- Add a B200 correctness test covering bitwise equality, unsupported input rejection, and `torch.compile(fullgraph=True)` custom-op coverage.
- Add a standalone benchmark over the LTX-2.3 production shape set plus CI-small shapes.

## Accuracy Tests

```bash
python3 -m py_compile \
  python/sglang/jit_kernel/diffusion/ltx2_qknorm_split_rope.py \
  python/sglang/multimodal_gen/runtime/models/dits/ltx_2.py \
  test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py \
  test/registered/jit/benchmark/diffusion/bench_ltx2_qknorm_split_rope.py
python3 -m ruff format --check ...
python3 -m ruff check ...
git diff --check
```

Result: local syntax/format/lint/diff checks passed.

B200 unit test:

```bash
CUDA_VISIBLE_DEVICES=5 \
PYTHONPATH=python:. \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
TVM_FFI_CACHE_DIR=/tmp/tvm-ffi-ltx2-k22-pr \
python3 -m pytest -q test/registered/jit/diffusion/test_ltx2_qknorm_split_rope.py -s
```

Result: `5 passed`.

## Speed Tests and Profiling

KDA-Pilot task `b200_ltx2_qknorm_split_rope__bitwise`, final k22 run on an idle B200:

- Correctness: all 14 production rows passed with `torch.equal` / zero tolerance for both Q and K outputs.
- Production shape coverage: LTX-2.3 two-stage and HQ rows, `head_dim in {64, 128}`, video/audio/cross rows, sequence lengths from 126 to 32640.
- Kernel benchmark: equal-weight geometric mean speedup **5.84x** over the task-local destination-passing PyTorch baseline; min **4.22x**, max **7.34x**; no production row regressed.
- The final candidate had `fallback_count == 0` across the production grid.

Integrated benchmark script CI-small check on B200:

```bash
CUDA_VISIBLE_DEVICES=5 \
PYTHONPATH=python:. \
FLASHINFER_DISABLE_VERSION_CHECK=1 \
TVM_FFI_CACHE_DIR=/tmp/tvm-ffi-ltx2-k22-pr \
SGLANG_IS_IN_CI=1 \
python3 test/registered/jit/benchmark/diffusion/bench_ltx2_qknorm_split_rope.py
```

| Workload | Torch us | CUDA us | Speedup |
| --- | ---: | ---: | ---: |
| stage1_video_self_q16_k16_d4096 | 191.15 | 33.98 | 5.625x |
| stage1_audio_to_video_q16_k8_d2048 | 176.30 | 32.34 | 5.451x |

B200 LTX-2.3 HQ end-to-end A/B with the same k22 fused path, no `torch.compile`:

| Implementation | E2E ms | Avg denoise ms | Median denoise ms | Denoise stage ms | Refinement stage ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 17022.27 | 867.16 | 888.05 | 12941.22 | 2674.02 |
| k22 fused | 15462.38 | 780.02 | 802.26 | 11679.22 | 2367.35 |
| Delta | -9.16% | -10.05% | -9.66% | -9.75% | -11.47% |

The fused run recorded `hit=16384, fallback=0` for this path.

## B200 Fused-vs-Unfused Accuracy

The fused CUDA path was validated on B200 against the original unfused PyTorch implementation for the exact Q/K attention-preprocessing contract it replaces:

```python
q_ref = apply_split_rotary_emb(q_norm(q), (q_cos, q_sin)).to(torch.bfloat16)
k_ref = apply_split_rotary_emb(k_norm(k), (k_cos, k_sin)).to(torch.bfloat16)
```

For the supported LTX-2.3 production shapes, the CUDA output is bitwise-identical to the unfused PyTorch output before attention consumes Q/K, so this optimization does not change model accuracy relative to the original non-fused path.

| B200 check | Shape coverage | Comparison | Result |
| --- | --- | --- | --- |
| KDA production oracle | 14 LTX-2.3 production rows, `head_dim in {64, 128}`, video/audio/cross rows, sequence lengths 126 to 32640 | fused Q/K vs unfused PyTorch Q/K | `torch.equal` for both Q and K on every row |
| SGLang unit test | supported B200 rows, unsupported-input rejection, `torch.compile(fullgraph=True)` custom-op coverage | fused Q/K vs unfused PyTorch Q/K | `5 passed` |
| Integrated fast-path dispatch | LTX-2.3 HQ path with supported B200 shapes | fast path hit count and fallback count | `hit=16384`, `fallback=0` |

Accuracy conclusion: on B200, the optimization produces the same Q/K tensors as the original non-fused PyTorch path for all covered production inputs; precision is unchanged.

### Result Image Comparison

B200 LTX-2.3 HQ A/B output sample (`seed=42`, `1920x1088`, 121 frames). The figure compares the original unfused path against the fused CUDA QKNorm + split-RoPE path at frames 0, 60, and 120.

![pr29708_ltx2_qknorm_result_compare.png](https://github.com/user-attachments/assets/36e6ad7d-0395-4303-a5ee-c3701e6aa760)

Video-level decode comparison: `SSIM All=1.000000`, `PSNR=inf`.

## Checklist

- [x] Default LTX2 path tries CUDA first and falls back to the existing PyTorch implementation on unsupported inputs or one-time runtime failure.
- [x] No environment variable is required to enable the CUDA kernel.
- [x] Direct custom op registration is eager and has a fake impl for `torch.compile` compatibility.
- [x] B200 bitwise unit test included.
- [x] Standalone benchmark script included for LTX-2.3 production shapes.
- [x] B200 kernel benchmark and LTX-2.3 HQ A/B evidence included.

## Review and Merge Process

This is a focused KDA-Pilot kernel integration PR. The expected useful effect is the faster LTX-2.3 Q/K normalization + split-RoPE preprocessing group; whole-model speedup is visible but remains bounded because attention, MLP, and decode still dominate full video generation runtime.





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28491339822](https://github.com/sgl-project/sglang/actions/runs/28491339822)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28491339740](https://github.com/sgl-project/sglang/actions/runs/28491339740)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
