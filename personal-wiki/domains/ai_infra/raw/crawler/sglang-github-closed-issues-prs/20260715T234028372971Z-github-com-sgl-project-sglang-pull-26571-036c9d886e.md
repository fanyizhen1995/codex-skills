---
source_id: sglang-github-closed-issues-prs
title: '[WIP] FP4 KV Cache Support'
canonical_url: https://github.com/sgl-project/sglang/pull/26571
captured_at: '2026-07-15T23:40:28.372971+00:00'
content_hash: 036c9d886e5da3778a4c4a2673fa3e7e7df730a9529e0551bcdf5ec8599e5219
---
# [WIP] FP4 KV Cache Support

URL: https://github.com/sgl-project/sglang/pull/26571
State: closed
Labels: 
Closed at: 2026-07-15T07:28:36Z
Merged at: 

## Motivation

This draft PR tracks the FP4 KV Cache Support item from #15194 . Resolve the **runtime failure** of FP4 KV Cache caused by the missing `KVFP4QuantizeUtil` component, and **unify the fragmented quantization code paths** to achieve production readiness.

**Detailed Background:**
- **Critical Runtime Failure**: `MHATokenToKVPoolFP4` and `MLATokenToKVPoolFP4` in `memory_pool.py` reference a non-existent `KVFP4QuantizeUtil` class, causing **immediate startup failure** for any FP4 KV Cache attempt.
- **Architectural Fragmentation (Technical Debt)**: The codebase maintains two parallel FP4 logic paths:
  - **Broken Legacy Path**: `MHATokenToKVPoolFP4` directly invokes non-functional utility classes.
  - **Unused Modern Path**: A fully implemented strategy pattern (`FP4KVCacheQuantMethod` → `NVFP4KVMethod`/`BlockFP4KVMethod`) in `fp4_kv_cache_quant_method.py` remains **completely disconnected** (dead code).
- **Critical Feature Gaps**: Even if import errors were fixed, the legacy path:
  - Cannot support Blackwell-architectural NVFP4 (two-level scaling)
  - Lacks CLI-based quantization recipe selection
  
## Planned Scope

1. **[Refactor] Migrate to Strategy Pattern**
   - Modify `MHATokenToKVPoolFP4` and `MLATokenToKVPoolFP4` to **eliminate hard-coded quantization logic**.
   - Route all quantization operations through the `FP4KVCacheQuantMethod` interface (replacing direct utility calls).

2. **[Feature] Introduce Recipe Selection Mechanism**
   - Add `--fp4-kv-cache-recipe` CLI parameter in `server_args.py` with options:
     - `blockfp4` (default): Standard block-wise 4-bit quantization
     - `nvfp4`: NVIDIA’s two-level scaling format (global FP32 + block FP8) for Blackwell (SM100+)

## Modifications

TBD

## Accuracy Tests

TBD

## Speed Tests and Profiling

TBD

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28441351482](https://github.com/sgl-project/sglang/actions/runs/28441351482)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28441351322](https://github.com/sgl-project/sglang/actions/runs/28441351322)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
