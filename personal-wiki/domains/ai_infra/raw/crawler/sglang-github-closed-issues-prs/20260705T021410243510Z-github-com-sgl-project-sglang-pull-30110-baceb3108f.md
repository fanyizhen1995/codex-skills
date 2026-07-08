---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] fix: shut down diffusion workers on serve exit'
canonical_url: https://github.com/sgl-project/sglang/pull/30110
captured_at: '2026-07-05T02:14:10.243510+00:00'
content_hash: baceb3108f0709a4979fee93a1fbe04ab7b85c685f5adc5b7364b323d68319f6
---
# [diffusion] fix: shut down diffusion workers on serve exit

URL: https://github.com/sgl-project/sglang/pull/30110
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-04T12:42:40Z
Merged at: 2026-07-04T12:42:40Z

## Summary
- Add a bounded diffusion launcher shutdown helper that sends ShutdownReq to the monolithic scheduler, waits for workers to exit, then falls back to terminate/kill.
- Run the cleanup when uvicorn exits, when local pool-disagg serving exits, and when a standalone disagg role is interrupted.
- Stop the local DiffusionServer thread on head-server shutdown and add unit coverage for the shutdown helper.

## Context
In the SGLang Office Hour 7/2 talk, the serving feedback was that Ctrl-C often leaves the background scheduler process alive, requiring manual kill and sometimes leaving enough GPU memory occupied to OOM a large model. The protocol-level ShutdownReq path applies to monolithic serving, including multi-GPU monolithic serving. Disaggregated role workers use bounded process cleanup here because they receive work through the disagg PULL protocol rather than the monolithic scheduler request protocol.

## Testing
- ruff check python/sglang/multimodal_gen/runtime/launch_server.py python/sglang/multimodal_gen/test/unit/test_launch_server_shutdown.py
- ruff format --check python/sglang/multimodal_gen/runtime/launch_server.py python/sglang/multimodal_gen/test/unit/test_launch_server_shutdown.py
- python -m py_compile python/sglang/multimodal_gen/runtime/launch_server.py python/sglang/multimodal_gen/test/unit/test_launch_server_shutdown.py
- git diff --check

Blocked locally:
- PYTHONPATH=python python -m unittest python/sglang/multimodal_gen/test/unit/test_launch_server_shutdown.py python/sglang/multimodal_gen/test/unit/test_diffusion_generator_shutdown.py fails while importing SGLang because the local torch package does not expose _cuda_beginAllocateCurrentThreadToPool from torch.cuda.memory.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28703502959](https://github.com/sgl-project/sglang/actions/runs/28703502959)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28703502908](https://github.com/sgl-project/sglang/actions/runs/28703502908)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
