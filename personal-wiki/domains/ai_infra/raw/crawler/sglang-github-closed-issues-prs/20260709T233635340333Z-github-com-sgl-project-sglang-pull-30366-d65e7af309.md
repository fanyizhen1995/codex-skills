---
source_id: sglang-github-closed-issues-prs
title: '[RL] Add /pull_weights: engine-side pull of published weights into a host-local
  checkpoint (sglang-miles)'
canonical_url: https://github.com/sgl-project/sglang/pull/30366
captured_at: '2026-07-09T23:36:35.340333+00:00'
content_hash: d65e7af309a11670b365e34dd087f16802bb8a8d9e3622c81bea79a7cee0890b
---
# [RL] Add /pull_weights: engine-side pull of published weights into a host-local checkpoint (sglang-miles)

URL: https://github.com/sgl-project/sglang/pull/30366
State: closed
Labels: dependencies, lora, Multi-modal, deepseek, blackwell, npu, model-gateway, mthreads, jit-kernel
Closed at: 2026-07-09T03:06:48Z
Merged at: 2026-07-09T03:06:48Z

## Motivation

RL trainers with disaggregated rollout publish each weight sync as a version dir `weight_v{N:06d}/` on a shared filesystem — a full HF checkpoint, or zstd-compressed per-tensor byte deltas (xor/overwrite) with per-tensor checksums, packaged as a canonical HF checkpoint dir. This adds the engine-side receiver: `POST /pull_weights` brings a host-local checkpoint up to a target version on every host the deployment spans, so the trainer talks to one endpoint per engine.

Trainer PR: radixark/miles#1235 · `main` variant: #30367 · Refs: THUDM/slime#2181

## Behavior

`POST /pull_weights {local_checkpoint_dir, source_dir, target_version}` fans out to every scheduler rank on every node. Each host seeds from the newest full version ≤ target (or the server's own `model_path` — version 0 is the engine's base), then applies the delta chain in place via mmap, parallelized across tensors. A checksum mismatch or out-of-order apply raises — never serve bad weights; a per-host flock + applied-version marker collapse co-located ranks to one pull. Success is gathered across the TP group, so the reply covers every host. The trainer then reloads via the ordinary `/update_weights_from_disk` — weight loading never sees the delta format.

`--custom-pull-weights-pre-read-hook <import.path>`: refresh hook for object-store-backed mounts without cross-host read-after-write consistency (POSIX shared FS needs none).

## Notes

- Deps: `xxhash` + `zstandard` added to pyproject; `blake3` stays an optional lazy import. The module is imported only inside the handler.
- Validated e2e with radixark/miles#1235: tp16 engine spanning 2 nodes, 3/3 delta syncs (~0.4% density, ~0.7–0.8 GB wire), all applies checksum-verified on both hosts.



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28888974230](https://github.com/sgl-project/sglang/actions/runs/28888974230)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28888973534](https://github.com/sgl-project/sglang/actions/runs/28888973534)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
