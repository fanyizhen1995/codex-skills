---
source_id: sglang-github-closed-issues-prs
title: '[SM120] Add FlashInfer sparse MLA decode for DSv4-Flash'
canonical_url: https://github.com/sgl-project/sglang/pull/27455
captured_at: '2026-07-01T02:12:08.971905+00:00'
content_hash: 89d943d2f6b8c7207459d7c2c56aa522117a74373eaf64befbc030c0a9ee91fd
---
# [SM120] Add FlashInfer sparse MLA decode for DSv4-Flash

URL: https://github.com/sgl-project/sglang/pull/27455
State: closed
Labels: deepseek, run-ci, run-ci-extra
Closed at: 2026-06-29T23:27:16Z
Merged at: 2026-06-29T23:27:16Z

## Summary

- Integrate FlashInfer SM120 `sparse_mla_sm120_decode_dsv4` decode kernel for DeepSeek-V4-Flash on RTX PRO 6000 (SM120)
- **Decode TPOT 2.2-3.7x faster** vs Triton kernel across batch sizes (ISL=8K, TP=4)
- Default FlashInfer when available, falls back to Triton seamlessly
- No changes to KV cache pool, compressor, or any non-SM120 code paths

## Motivation

The existing Triton FlashMLA decode kernel (merged in #24692) works but leaves performance on the table. FlashInfer's native SM120 `decode_dsv4` kernel uses CUTLASS with block-scaled MXFP8 MMA, achieving 2.2-3.7x decode speedup.

## Approach

**Challenge**: SGLang SWA KV cache uses `page_size=256` with footer layout (scales stored at page end), but FlashInfer's `decode_dsv4` hardcodes `page_block_size=64` as a CUDA template parameter.

**Solution**: Fused Triton page-split kernel at call site — before each FlashInfer call, converts 256-token pages into 4 virtual 64-token pages with correct footer layout in a single kernel launch (replaces 8 separate copy kernels = 344 launches/step saved). Index remapping is not needed since the page-split preserves linear token ordering. No changes to the KV cache pool or compressor.

Reference: vLLM PR vllm-project/vllm#43477 (same FlashInfer kernel, different integration approach — vLLM uses block_size=64 natively).

## Changes (3 files)

**flash_mla_sm120.py**:
- Default FlashInfer backend, override via `SGLANG_SM120_FLASHMLA_BACKEND=triton|torch`
- `_page_split_kernel`: Fused Triton kernel converting pbs=256 footer to pbs=64 footer in 1 launch
- `_split_kv_pages_to_64()`: Page-split driver with lazy per-device buffer allocation
- `_flash_mla_flashinfer()`: Direct call to `sparse_mla_sm120_decode_dsv4()` with page-split for SWA cache, extra cache (C4/C128) passed as-is
- Pre-allocated `mid_out`/`mid_lse`/`output`/`out_lse` scratch buffers passed explicitly

**deepseek_v4_backend.py** (3 lines):
- Read `swa_page_size` from pool instead of hardcoded 128
- Relax assertion to `swa_page_size % SWA_WINDOW == 0`

**environ.py** (2 lines):
- Add `SGLANG_SM120_FLASHMLA_BACKEND` env var (default: `"flashinfer"`)

## Performance

### FlashInfer vs Triton MLA Decode (TP=4, 4x RTX PRO 6000 96GB, triton MoE, CUDA graph, ISL=8K OSL=32)

| BS | Backend | TTFT (s) | TPOT (ms) | Throughput (tok/s) |
|----|---------|----------|-----------|-------------------|
| 1  | **FlashInfer** | **0.92** | **22.2** | **17.71** |
| 1  | Triton  | 6.17     | 82.7      | 3.21              |
| 4  | **FlashInfer** | **0.56** | **64.0** | **45.77** |
| 4  | Triton  | 2.58     | 148.8     | 14.87             |
| 8  | **FlashInfer** | **0.91** | **114.4** | **52.61** |
| 8  | Triton  | 3.39     | 253.8     | 19.83             |

**Speedup (FlashInfer over Triton):**

| BS | TTFT | TPOT | Throughput |
|----|------|------|-----------|
| 1  | 6.7x | 3.7x | 5.5x     |
| 4  | 4.6x | 2.3x | 3.1x     |
| 8  | 3.7x | 2.2x | 2.7x     |

### Correctness

| Test | Result |
|------|--------|
| GSM8K 10q (0-shot, TP=4, FlashInfer) | 10/10 = 100% |
| Unit test: FlashInfer vs Triton cosine similarity | pass (atol=5e-2) |
| CUDA graph capture BS=1,2,4,8,12,16 | All pass |

## Dependencies

Requires FlashInfer 0.6.13 from GitHub main with SM120 sparse MLA support:
```bash
pip install flashinfer-python @ git+https://github.com/flashinfer-ai/flashinfer.git@main --no-deps
```
- FlashInfer PR: flashinfer-ai/flashinfer#3395 (merged)
- PyPI 0.6.13rc2 does NOT include `_sparse_mla_sm120.py` yet
- JIT compilation on first call: FlashInfer builds SM120 CUDA kernels (~2 min)
- When FlashInfer is not available, falls back to the existing Triton kernel (zero regression)

## Backend selection

```bash
# Default: FlashInfer (requires flashinfer with sparse_mla_sm120)
# Override with env var:
export SGLANG_SM120_FLASHMLA_BACKEND=triton   # force Triton
export SGLANG_SM120_FLASHMLA_BACKEND=torch    # force PyTorch fallback
```

## Test plan

- [x] Unit test: FlashInfer vs Triton cosine similarity pass
- [x] E2E: GSM8K 10q 0-shot = 100% (TP=4, FlashInfer)
- [x] CUDA graph capture BS=1,2,4,8,12,16
- [x] FlashInfer vs Triton A/B comparison (2.2-3.7x TPOT speedup)
- [ ] CI (SM120 not available in CI — SM120-only code path, guarded by `is_sm120_supported()` + try-import)

🤖 Generated with [Claude Code](https://claude.com/claude-code)



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28322389060](https://github.com/sgl-project/sglang/actions/runs/28322389060)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28322388997](https://github.com/sgl-project/sglang/actions/runs/28322388997)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
