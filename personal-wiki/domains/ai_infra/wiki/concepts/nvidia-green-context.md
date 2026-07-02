---
type: Concept
title: NVIDIA Green Context
description: CUDA Green Context evidence in local AI infrastructure sources, centered on SGLang spatial multiplexing and CUDA compatibility issues.
domain: ai_infra
status: reviewed
tags:
  - cuda
  - nvidia
  - green-context
  - sglang
  - pd-multiplexing
  - gpu-scheduling
source_refs:
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json
  - ../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json
updated: 2026-07-02
aliases:
  - CUDA Green Context
  - Green Contexts
  - greenctx
  - CUgreenCtx
related:
  - ../projects/sglang.md
  - ../references/sglang-github-closed-issues-prs.md
  - ../references/nccl-release-notes.md
---
# Summary

The local `ai_infra` evidence contains concrete CUDA Green Context material in the SGLang GitHub corpus. SGLang added CUDA Green Context support in PR #7649 for PD-Multiplexing: the PR says PD kernels launch to two Green Context streams with different SM counts so they can execute via spatial multiplexing. Later SGLang work reused Green Context streams for PD-Multiplexing communication and explored Green Context SM partitioning for an overlap-scheduler stream.

Treat this page as a local evidence index, not a general NVIDIA API manual. The raw evidence currently comes from SGLang issues and PRs, while the local NCCL release-note corpus mostly uses the separate term GIN contexts.

# Evidence In SGLang

| Item | Status | Local signal |
| --- | --- | --- |
| PR #7649, `[Feature] CUDA Green Context Support` | Merged 2025-07-14 | Added Green Context stream creation with specified SM counts, available-SM lookup, and `test_greenctx_stream.py` for SGLang's `sgl-kernel`; tied the feature to PD-Multiplexing. |
| PR #8090, `fix greenctx stream compability` | Merged 2025-07-16 | Recorded that `cuGreenCtxStreamCreate` was introduced in CUDA 12.5 and caused CUDA 12.4 compile compatibility trouble. |
| Issue #8131, `cuda 12.4 encounter undefined symbol: cuGreenCtxStreamCreate` | Closed 2025-07-18 | User hit `undefined symbol: cuGreenCtxStreamCreate` when running a wheel compiled with CUDA 12.8 on a CUDA 12.4 runtime; the reporter closed after confirming matching CUDA 12.4 compile/runtime worked. |
| PR #8136, `enhance green context stream creation robust with backward compatibility` | Merged 2025-07-18 | Follow-up robustness work for Green Context stream creation and backward compatibility. |
| Issue #8432, `undefined symbol: cuGreenCtxDestroy` | Closed 2025-08-12 | A800 deployment with CUDA 12.2 driver/toolkit stack failed to start because `cuGreenCtxDestroy` was unavailable; comments identify it as CUDA driver API availability and discuss deferring symbol resolution. |
| Issue #8566, `ImportError ... undefined symbol: cuGreenCtxDestroy` | Closed duplicate 2025-07-30 | Duplicate field report of `cuGreenCtxDestroy` import failure; comments include CUDA 12.2/A100 reproduction and CUDA 12.9 working environment. |
| PR #8701, `fix green context's incompatibility with cuda < 12.4` | Merged 2025-08-02 | Added an explicit compatibility fix for `cuGreenCtxDestroy` import failures on older CUDA stacks. |
| PR #9021, `Runtime check CUDA driver version to avoid unresolved green context symbols` | Merged 2025-08-12 | Follow-up to #8701 and #8432; reviewers flagged that all Green Context-specific CUDA functions need runtime resolution to fully avoid older-driver link/runtime failures. |
| PR #9231, `Optional extension for green context` | Merged 2025-08-15 | Followed #9021; review comments emphasized that driver compatibility checks still matter because toolkit and driver versions can differ. |
| PR #9512, `failed to find greenctx related symbols when CUDA_VERSION < 12040` | Closed unmerged 2025-11-17 | Captured CUDA 12.0 compile errors where `CUgreenCtx`, `cuCtxFromGreenCtx`, and `cuGreenCtxDestroy` identifiers were unavailable; comments say the problem was later fixed. |
| Issue #10298, `test_greenctx_stream.py ... CUBLAS_STATUS_INTERNAL_ERROR` | Closed inactive 2025-11-11 | Field report that the Green Context stream test failed at cuBLAS SGEMM time, showing the feature also had runtime validation risk beyond import/link errors. |
| PR #11594, `Use current greenctx stream to communicate in PD-Multiplexing` | Merged 2025-10-20 | Enabled communication on the correct stream with specified SM resources for PD-Multiplexing via PyNCCL communicator stream resolution. |
| PR #22827, `Use Green Context SM partitioning for overlap schedule stream` | Closed unmerged 2026-04-14 | PoC proposed using Green Context SM partitioning to keep an overlap schedule stream from being blocked by CLC-persistent GEMM on Blackwell, with fallback to plain streams. |

# Operational Takeaways

- In the local evidence, "NVIDIA Green Context" is best understood as CUDA Green Context usage exposed through `CUgreenCtx` and `cuGreenCtx*` driver APIs, not as an NCCL feature.
- SGLang used it for SM partitioning and stream separation in PD-Multiplexing, where prefill/decode or scheduling work can be placed on streams with specified SM resources.
- The main integration hazard was binary compatibility: code compiled against newer CUDA headers or drivers could reference Green Context symbols that are absent on older runtime drivers or toolkits.
- The robust implementation pattern in the SGLang trail is to guard Green Context code by CUDA version and resolve Green Context driver symbols at runtime where needed, while keeping clear fallback or error paths for unsupported environments.

# Citations

- [SGLang raw index](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-index.json)
- [SGLang joined raw corpus manifest](../../raw/github/sgl-project-sglang-closed-issues-prs/sgl-project-sglang-closed-issues-prs-with-comments.split-manifest.json)
- [SGLang GitHub Closed Issues And PRs](../references/sglang-github-closed-issues-prs.md)
