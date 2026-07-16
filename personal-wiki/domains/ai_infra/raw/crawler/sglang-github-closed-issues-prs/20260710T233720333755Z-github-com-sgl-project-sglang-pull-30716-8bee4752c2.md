---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion] Revert CPU AMX optimizations'
canonical_url: https://github.com/sgl-project/sglang/pull/30716
captured_at: '2026-07-10T23:37:20.333755+00:00'
content_hash: 8bee4752c2df4197ac4e36faa3f91d9388c9436bd352c4c727693e4d546cd34d
---
# [Diffusion] Revert CPU AMX optimizations

URL: https://github.com/sgl-project/sglang/pull/30716
State: closed
Labels: Multi-modal, sgl-kernel, run-ci, diffusion
Closed at: 2026-07-10T01:09:38Z
Merged at: 2026-07-10T01:09:38Z

Reverts #28527 (`177c048c68`).

That change adds a second unconditional `process_weights_after_loading()` pass in the diffusion FSDP loader. The hook is not idempotent for quantized weights, and the added `device_loading_context` also breaks FSDP inference by attempting to restore CUDA-backed parameters to CPU storage.

CI evidence: [`multimodal-gen-test-2-gpu (2)`](https://github.com/sgl-project/sglang/actions/runs/29029534843/job/86158408321), where `fsdp-inference` fails in `device_loading_context` with a CPU/CUDA storage mismatch.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29061437164](https://github.com/sgl-project/sglang/actions/runs/29061437164)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29061437106](https://github.com/sgl-project/sglang/actions/runs/29061437106)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
