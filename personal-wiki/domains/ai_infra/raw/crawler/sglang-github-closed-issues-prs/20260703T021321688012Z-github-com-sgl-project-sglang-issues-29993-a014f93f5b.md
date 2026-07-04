---
source_id: sglang-github-closed-issues-prs
title: GLM-5.2-FP8 crashes at weight load on 8×B200 since sgl-deep-gemm 0.1.4 (UE8M0
  scale-pack assert)
canonical_url: https://github.com/sgl-project/sglang/issues/29993
captured_at: '2026-07-03T02:13:21.688012+00:00'
content_hash: a014f93f5b314ae769cf7660c154275035c0a63df80c7143d2c2a0013de33c68
---
# GLM-5.2-FP8 crashes at weight load on 8×B200 since sgl-deep-gemm 0.1.4 (UE8M0 scale-pack assert)

URL: https://github.com/sgl-project/sglang/issues/29993
State: closed
Labels: 
Closed at: 2026-07-03T01:17:28Z
Merged at: 

`test/registered/8-gpu-models/test_glm52_fp8.py` has failed every 8-GPU B200 nightly since the sgl-deep-gemm 0.1.3 → 0.1.4 bump in #29554 (merged Jul 1). All three variants (TP8, TP8+DP8, TP8+DP8+MTP) die during weight loading; it passed the night before on 0.1.3 with the same checkpoint.

Failing job: https://github.com/sgl-project/sglang/actions/runs/28558138686/job/84736504503 (commit a3f6680874).

### Symptom

~2000 device asserts across the 8 ranks during load, then the scheduler dies:

```
Assertion failed: deep_gemm/include/deep_gemm/impls/smxx_layout.cuh:131, condition: (values[j] & 0x807fffffu) == 0
tvm.error.InternalError: CUDA driver error (jit_kernels/impls/smxx_layout.hpp:72): 719 (CUDA_ERROR_LAUNCH_FAILED)
```

### Where

`process_weights_after_loading_block_quant` → `requant_block_scale_ue8m0_for_deepgemm` → `requant_weight_ue8m0` → `transform_scale_ue8m0` (`python/sglang/srt/layers/quantization/fp8_utils.py`), which calls deep_gemm's `get_mn_major_tma_aligned_packed_ue8m0_tensor`:

```python
sf = sf.index_select(-2, torch.arange(mn, device=sf.device) // 128)
sf = get_mn_major_tma_aligned_packed_ue8m0_tensor(sf)   # asserts here
```

### Cause

deep_gemm 0.1.4 added a device assert in the UE8M0 pack kernel (`smxx_layout.cuh:131`) requiring every FP32 scale to be exponent-only — sign and mantissa bits zero, i.e. an exact power of two. 0.1.3 had no such check; it just shifted out the mantissa (`values[j] >> 23`), silently accepting non-power-of-two input. GLM-5.2-FP8 stores block scales as plain floats (`scale_fmt: null`), and the scales `transform_scale_ue8m0` hands to the pack kernel are not all exponent-only, so 0.1.4 aborts where 0.1.3 truncated.

### Reproduce

8×B200 + the checkpoint + the CI-pinned deps. The one that matters is `transformers==5.12.1`; an older transformers hits an unrelated weight-shape error during load and never reaches this point.

```
python3 -m sglang.launch_server --model zai-org/GLM-5.2-FP8 --trust-remote-code \
  --tp 8 --quantization fp8 --kv-cache-dtype fp8_e4m3 --attention-backend dsa \
  --mem-fraction-static 0.85
```

Run with `CUDA_LAUNCH_BLOCKING=1` to surface the assert at the launching line.

### Options

- Immediate unblock: pin sgl-deep-gemm back to 0.1.3 (keep the tvm-ffi/tilelang parts of #29554 if separable), or gate the GLM-5.2 B200 nightly.
- Fix: make `transform_scale_ue8m0` pass exponent-only scales to the pack kernel under 0.1.4 (mask sign+mantissa, or route through the casting path with `disable_ue8m0_cast=False`).
- Upstream: decide whether `get_mn_major_tma_aligned_packed_ue8m0_tensor` should round/cast instead of hard-asserting on non-power-of-two input.

cc @Fridge003
