---
source_id: sglang-github-closed-issues-prs
title: '[CP] Fix FP8 MLA RoPE for CP prefill on Blackwell'
canonical_url: https://github.com/sgl-project/sglang/pull/29721
captured_at: '2026-07-01T02:12:08.952176+00:00'
content_hash: 325e3fab50dbc7d91e8f926e59ffee7b2d25e151969145a11e0ca15c1423d838
---
# [CP] Fix FP8 MLA RoPE for CP prefill on Blackwell

URL: https://github.com/sgl-project/sglang/pull/29721
State: closed
Labels: 
Closed at: 2026-07-01T02:01:46Z
Merged at: 

## Summary

Fix the FP8 MLA RoPE+quantize path when prefill context parallelism makes Q rank-local while K has been all-gathered back to the global/padded token layout.

The FlashInfer `mla_rope_quantize_fp8` fused path assumes Q and K have the same token count. With CP prefill, that assumption breaks: Q uses CP-split local positions while K is rebuilt from the gathered KV cache. This PR keeps the fused fast path for matching Q/K lengths and adds Triton kernels for the mismatched CP case with separate Q and K position tensors, using the old torch implementation as the unit-test reference.

## Changes

- Add an optional `k_pos_ids` path to `mla_quantize_and_rope_for_fp8`.
- Replace the CP fallback with Triton copy/RoPE kernels that write FP8 outputs directly.
- Thread CP-split Q positions from `forward_mla.py` into the DSA TRT-LLM FP8 extend path only.
- Build gathered-K RoPE positions in `dsa_backend.py` with `compute_position_triton` and derive local Q positions for CP.
- Add a CUDA regression test for mismatched Q/K token counts, with torch eager RoPE as the reference.

## Validation

- `python3 -m py_compile python/sglang/srt/layers/attention/utils.py python/sglang/srt/layers/attention/dsa_backend.py python/sglang/srt/models/deepseek_common/attention_forward_methods/forward_mla.py test/registered/unit/layers/test_mla_fp8_rope.py && git diff --check`
- On `baizhou-dev` / B300: `PYTHONPATH=/tmp/sglang-glm-opt-triton/python python3 -m pytest -q test/registered/unit/layers/test_mla_fp8_rope.py` -> `1 passed, 21 warnings, 2 subtests passed in 11.77s`.
- On `baizhou-dev` / B300 microbenchmark, shape `q_len=1024`, `k_len=8192`, `heads=16`, `nope=512`, `rope=64`: Triton `0.044 ms`, torch reference `0.117 ms`, `2.64x` speedup; no-RoPE FP8 copy exact, RoPE max diff `0.25` FP8-bin-adjacent.
- On `baizhou-dev` / 8xB300, launched `nvidia/GLM-5.2-NVFP4` with `--kv-cache-dtype fp8_e4m3`, `--tp 8`, prefill CP interleave, and `flashinfer_trtllm`.
- Short `/v1/completions` probe returned HTTP 200 with `prompt_tokens=1`; long repro prompt (`"Hello " * 12000`, `max_tokens=1`) returned HTTP 200 with `prompt_tokens=12001`.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28437454174](https://github.com/sgl-project/sglang/actions/runs/28437454174)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28437454079](https://github.com/sgl-project/sglang/actions/runs/28437454079)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
