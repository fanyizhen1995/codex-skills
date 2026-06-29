---
source_id: sglang-github-closed-issues-prs
title: '[weight checker] refactor: add precision branch; allow ULP quant err; used
  chunked compare'
canonical_url: https://github.com/sgl-project/sglang/pull/28974
captured_at: '2026-06-29T04:09:41.028067+00:00'
content_hash: ad959a33037c41e1a10ddc6f675e1e78bf3fc7bfcc5eedeb40d5b91b7920e32c
---
# [weight checker] refactor: add precision branch; allow ULP quant err; used chunked compare

URL: https://github.com/sgl-project/sglang/pull/28974
State: closed
Labels: quant, run-ci
Closed at: 2026-06-29T01:44:06Z
Merged at: 2026-06-29T01:44:06Z

## Motivation

The weight checker's `compare`/`checksum` actions require two block-quantized weights to be **bit-identical** after dequant. But two independent yet faithful quantizations of the same source weight — e.g. before vs. after a weight update that requantizes — can legitimately differ per element. Tolerating that with a hand-tuned mean-error threshold is both too loose (a mean lets per-element corruption hide in a large tensor) and arbitrary per model/precision.

This replaces it with a principled, per-element tolerance: each side of a block-quant pair is one faithful quantization of the same source weight, so each may deviate from it by up to 1 ULP of its own representation — i.e. the two may differ by at most `expect_ulp + actual_ulp` per element in dequantized space. Opt in via `allow_quant_error`; the default stays exact-equality (no behavior change).

## Modifications

- `CheckWeightsReqInput` gains `allow_quant_error: bool = False`, plumbed through scheduler / `model_runner.check_weights` into the weight checker.
- New `weight_checker_quant.py` holds the quantization-aware comparison behind a small `ReferenceWeight` seam (`Fp8BlockReference` today). Adding a precision is a new subclass.
- `select_quantization_method` dispatches on `module.quant_method` (not param names — robust to swizzled scales / per-format naming) and raises `NotImplementedError` for formats with no `ReferenceWeight`, so mxfp8 / nvfp4 / int4 fail loudly instead of being silently mis-compared.
- Comparison/dequant is chunked to bound GPU memory; NaN counts as exceeding tolerance (`~(diff <= tol)`); block size is inferred from weight/scale shapes (handles partial last blocks and non-128 block formats).

## Tests

`test/registered/unit/utils/test_weight_checker.py` (CUDA-gated):
- `TestQuantUlp` — `_quant_ulp` brute-force verified against the true spacing of all 256 bit patterns of `float8_e4m3fn` / `float8_e5m2` (exact match).
- `TestCompareQuantPair` — two quantizations within tolerance pass; bit-flip corruption and fp8 NaN exceed; chunked == unchunked; partial last block; 3D expert tensors; ue8m0-packed scales.
- `TestSelectQuantizationMethod` — unsupported quant method raises.

































































































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #28343424880](https://github.com/sgl-project/sglang/actions/runs/28343424880)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28343424787](https://github.com/sgl-project/sglang/actions/runs/28343424787)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
