---
source_id: sglang-github-closed-issues-prs
title: Fix disaggregation receiver ZMQ cleanup
canonical_url: https://github.com/sgl-project/sglang/pull/29570
captured_at: '2026-07-08T23:36:33.791164+00:00'
content_hash: ee99940fcd7c26a7ac8644da7076bb0aba6a9b8c7b2cb0f8d7f3d36351b2dbd7
---
# Fix disaggregation receiver ZMQ cleanup

URL: https://github.com/sgl-project/sglang/pull/29570
State: closed
Labels: 
Closed at: 2026-06-29T08:22:30Z
Merged at: 2026-06-29T08:22:30Z

## Motivation

Addresses the stale receiver ZMQ socket cleanup part of #28596.

On current main, decode-side heartbeat failure handling already removes stale
prefill metadata and calls `CommonKVReceiver.disconnect_endpoint()` for cached
receiver endpoints. The remaining receiver-side cached ZMQ PUSH socket gap is
that newly created sockets still use ZeroMQ's default reconnect and linger
behavior.

## Modifications

- Configure `CommonKVReceiver._connect()` sockets with `RECONNECT_IVL=-1` to
  avoid keeping dead prefill endpoints in ZeroMQ's reconnect loop.
- Configure the same sockets with `LINGER=0`, so cached receiver socket cleanup
  does not wait on queued messages when the stale endpoint is discarded.
- Keep `CommonKVReceiver.disconnect_endpoint()` on the existing per-endpoint
  lock and let normal `sock.close()` use the socket-level zero-linger policy.

## Accuracy Tests

Not applicable. This only changes ZMQ socket lifecycle behavior after
disaggregation endpoint failure and does not change model execution or outputs.

## Speed Tests and Profiling

Not run. The steady-state path still reuses the same cached socket per endpoint;
the new options are socket configuration and failure cleanup behavior.

## Validation

After the maintainer-requested scope reduction:

- `git diff --check`: passed
- `PYTHONPATH=python python3 -m py_compile python/sglang/srt/disaggregation/common/conn.py`: passed
- `pre-commit run --files python/sglang/srt/disaggregation/common/conn.py`: passed via a temporary local venv

Previously run on this PR branch before the review-scope reduction:

- H200 PD smoke on upstream main + this patch branch:
  - Hardware: 2 x NVIDIA H200
  - Image/runtime: `lmsysorg/sglang:latest`, PyTorch `2.11.0+cu130`, CUDA `13.0`
  - Model: `Qwen/Qwen2.5-0.5B-Instruct`
  - Transfer backend: `mooncake_tcp`
  - Shape: prefill on GPU 0, decode on GPU 1, generate once through the PD load balancer, kill prefill, wait for heartbeat failure handling, then verify decode `/health`.
  - Result: `1 passed`; decode logged `Lost connection with prefill instance ...` and remained healthy.

Validation gaps:

- I did not reproduce the probabilistic NCCL-port collision from the issue.
- I did not rerun the H200 PD smoke after the maintainer-requested scope
  reduction; static, compile, and changed-file pre-commit checks were rerun on
  the final patch.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28354886696](https://github.com/sgl-project/sglang/actions/runs/28354886696)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28354886470](https://github.com/sgl-project/sglang/actions/runs/28354886470)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
