---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Register 5 CI-verified 1-GPU kernel/attention unit tests for AMD PR
  CI'
canonical_url: https://github.com/sgl-project/sglang/pull/30290
captured_at: '2026-07-07T23:35:30.902107+00:00'
content_hash: b913feab42316e474d473e468bd290ec5360ed443fe231abf249cbd3b573546d
---
# [AMD] Register 5 CI-verified 1-GPU kernel/attention unit tests for AMD PR CI

URL: https://github.com/sgl-project/sglang/pull/30290
State: closed
Labels: run-ci
Closed at: 2026-07-07T21:44:45Z
Merged at: 2026-07-07T21:44:45Z

## Motivation

Extends AMD per-commit (PR-tier) test coverage tracked on the ROCm CI
dashboard. All 5 tests already run on NVIDIA per-commit CI (`base-b` 1-GPU) and
were **verified green on the AMD (MI325) lane**, so the standard
`register_amd_ci(...)` 2-line edit is sufficient — no ROCm-specific code changes.

## Modifications

`register_amd_ci(...)` added next to the existing `register_cuda_ci(...)`
(CUDA `base-b` → AMD `stage-b`):

| File | AMD suite | est | Verified on AMD | What it covers |
|---|---|---|---|---|
| [kernels/test_dsa_metadata.py](https://github.com/sgl-project/sglang/blob/main/test/registered/kernels/test_dsa_metadata.py) | `stage-b-test-1-gpu-large-amd` | 15 | ✅ | Triton DSA metadata kernels (`fused_dsa_*_metadata`) + torch reference |
| [unit/mem_cache/test_unified_mamba_views.py](https://github.com/sgl-project/sglang/blob/main/test/registered/unit/mem_cache/test_unified_mamba_views.py) | `stage-b-test-1-gpu-small-amd` | 30 | ✅ | Plain-torch view/stride round-trip for `UnifiedKVPool._build_mamba_views` (no Mamba kernel) |
| [attention/test_trtllm_mha_page_table.py](https://github.com/sgl-project/sglang/blob/main/test/registered/attention/test_trtllm_mha_page_table.py) | `stage-b-test-1-gpu-small-amd` | 14 | ✅ | Triton device-side page-table build + torch reference |
| [attention/test_gdn_noncontiguous_stride.py](https://github.com/sgl-project/sglang/blob/main/test/registered/attention/test_gdn_noncontiguous_stride.py) | `stage-b-test-1-gpu-large-amd` | 7 | ✅ | FLA gated-delta-net Triton kernels (non-contiguous stride) |
| [attention/test_kda_kernels.py](https://github.com/sgl-project/sglang/blob/main/test/registered/attention/test_kda_kernels.py) | `stage-b-test-1-gpu-large-amd` | 12 | ✅ | KDA (Kimi delta attention) FLA Triton kernels |

## Test plan

All 5 files confirmed **PASS** on the AMD MI325 lane (per-file result lines
pulled from the partition logs). Dispatched AMD runs:
- `stage-b-test-1-gpu-small-amd` — https://github.com/sgl-project/sglang/actions/runs/28832853806 (`test_unified_mamba_views` ✅, `test_trtllm_mha_page_table` ✅)
- `stage-b-test-1-gpu-large-amd` — https://github.com/sgl-project/sglang/actions/runs/28832854912 (`test_dsa_metadata` ✅, `test_kda_kernels` ✅, `test_gdn_noncontiguous_stride` ✅)

The `stage-b-*-amd` suites show a run-level failure only from pre-existing,
unrelated partition-mates (fail-fast); none of the files in this PR failed.

- [x] AMD CI passes on the registered files (all 5 verified PASS on MI325)
- [ ] NVIDIA CI still green (registration-only change; no CUDA edits)
