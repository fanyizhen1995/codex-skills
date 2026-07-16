---
source_id: sglang-github-closed-issues-prs
title: '[HiCache & HybridModel] nixl hicache backend support hybrid models'
canonical_url: https://github.com/sgl-project/sglang/pull/29191
captured_at: '2026-07-13T23:40:05.180797+00:00'
content_hash: 07eed58afff1874e306585b90315d2046f703089a31439bd6f4fa7d43d076832
---
# [HiCache & HybridModel] nixl hicache backend support hybrid models

URL: https://github.com/sgl-project/sglang/pull/29191
State: closed
Labels: documentation, hicache, run-ci
Closed at: 2026-07-13T16:09:37Z
Merged at: 2026-07-13T16:09:37Z

## Motivation

Previously, PR #25538 was created to add support for the HiCache NIXL backend to store hybrid models. However, HiCache NIXL backend has been refactored.
After the HiCache NIXL backend refactor, the previous hybrid-storage change became stale because NIXL now has its own registry, pre-registered host memory path, O_DIRECT alignment handling, and persistent bounce-buffer flow. This PR reworks NIXL hybrid HiCache support on top of the new backend structure, so hybrid models like Qwen3.5/Mamba and DSA-style side pools can use NIXL as the HiCacheHybrid controller storage backend.

## Modifications

- Implement real `register_mem_host_pool_v2` in `HiCacheNixl`.
  It now registers each side-pool with NIXL using a per-pool context, instead of only saving the pool reference. If a side pool supports zero-copy and passes alignment check, its host buffers are pre-registered with the NIXL agent.

- Add zero-copy selection for aligned side pools.
  NIXL checks `get_hybrid_pool_buffer()`, `get_page_buffer_meta()`, and `is_stride_page_aligned()` before enabling side-pool zero-copy. This directly addresses the feedback that zero-copy should be guarded by alignment and real NIXL registration.

- Add persistent per-pool GET/SET bounce buffers for fallback path.
  When zero-copy is not safe, each registered side-pool gets its own persistent `bounce_get` and `bounce_set` buffers. This avoids sharing one bounce buffer across pools or directions, so tensor bookkeeping stays simple and follows the existing GET/SET thread model.

- Make `batch_get_v2` and `batch_set_v2` use the host-pool-specific transfer context.
  v2 transfers now either use registered zero-copy buffer metadata or the pool-specific bounce buffers. They also emit debug transfer stats like v1, e.g. `batch_set_v2[mamba] transferred: ...`, making side-pool storage traffic easier to verify.

- Keep `batch_exists_v2` simple and pool-aware.
  It formats the sidecar object names and queries NIXL storage similarly to v1. For multi-object side pools, it folds object-level existence results back to page-level hit counts and still respects `ALL_PAGES` and `TRAILING_PAGES` policies.

- Add consistent sidecar key naming.
  Sidecar objects use suffixes after the normal NIXL base key, for example `_mamba_temporal`, `_mamba_conv_0`, and pool-specific `_k` / `_v` names when a side pool expands into multiple objects.

- Add `is_stride_page_aligned()` support for side-pool host classes.
  `MambaPoolHost`, `DeepSeekV4PagedHostPool`, `DeepSeekV4StateHostPool`, `DSAIndexerPoolHost`, and `HostPoolGroup` now expose alignment checks needed by the NIXL zero-copy decision.

- Add unit coverage for NIXL hybrid v2 behavior.
  Tests cover zero-copy side-pool registration, bounce-buffer fallback registration, expanded Mamba sidecar keys, and v2 GET/SET behavior through the per-pool transfer path.

- Update NIXL README and add an e2e validation script.
  The README now includes the Qwen3.5 hybrid NIXL serve command and the expected sidecar file naming. The local script `~/TestEnv/nixl_hicache_hybrid_e2e.py` starts SGLang with NIXL HiCache storage, sends a long request, and checks that NIXL is selected by the hybrid controller and that Mamba sidecar files are written.

After this change, cache objects are distributed in subdirectories (for POSIX backend) like:
```
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_0_2_v
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_0_2_mamba_conv_0
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_1_2_mamba_temporal
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_1_2_v
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_1_2_mamba_conv_0
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_1_2_k
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_0_2_k
c41f2e1b1bdad16596d5901ce236ce6a32bd8e0d8d6cfcdda5c3924342cf92ad_Qwen-Qwen3.5-9B_0_2_mamba_temporal
```

## Accuracy Tests

will append later

## Speed Tests and Profiling

will append later

## Checklist

- [X] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [X] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [X] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



















































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29244425711](https://github.com/sgl-project/sglang/actions/runs/29244425711)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29244425701](https://github.com/sgl-project/sglang/actions/runs/29244425701)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
