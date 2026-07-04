---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] refactor: refactor cuda attention backend resolver'
canonical_url: https://github.com/sgl-project/sglang/pull/29852
captured_at: '2026-07-03T02:13:21.700042+00:00'
content_hash: 4ba87ad965dca97d5fbdec47c486dbcbb8152282fbc67c1f2073d5ba646d2307
---
# [diffusion] refactor: refactor cuda attention backend resolver

URL: https://github.com/sgl-project/sglang/pull/29852
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-02T13:34:54Z
Merged at: 2026-07-02T13:34:54Z

## Motivation
`CudaPlatformBase.get_attn_backend_cls_str` had accumulated backend class paths, optional import probes, requested/default backend selection, SM120 fallback, Blackwell FA4 setup, and FlashAttention validation in one long branch chain. This makes future backend changes hard to review and easy to regress.

## Changes
- Extract CUDA attention backend class path constants and direct backend mapping.
- Split resolver logic into helpers for import-checked special backends, requested/default FlashAttention selection, Blackwell FA4 setup, and FlashAttention fallback validation.
- Preserve the existing selection behavior, including SM120 -> Torch SDPA fallback and Blackwell FlashAttention v4 setup.
- Add focused unit coverage for direct backend selection, SM120 FA/default fallback, dtype/capability fallback, and invalid backend rejection.

## Validation
- `pre-commit run --files python/sglang/multimodal_gen/runtime/platforms/cuda.py python/sglang/multimodal_gen/test/unit/test_cuda_attention_backend.py`











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28560796958](https://github.com/sgl-project/sglang/actions/runs/28560796958)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28560796853](https://github.com/sgl-project/sglang/actions/runs/28560796853)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
