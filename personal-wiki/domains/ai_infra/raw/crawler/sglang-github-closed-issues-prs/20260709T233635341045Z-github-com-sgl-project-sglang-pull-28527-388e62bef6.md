---
source_id: sglang-github-closed-issues-prs
title: '[Diffusion][CPU] Adding AMX optimizations for CPU platform'
canonical_url: https://github.com/sgl-project/sglang/pull/28527
captured_at: '2026-07-09T23:36:35.341045+00:00'
content_hash: 388e62bef650bfe623165c28f98d5298dc4f6222c82156fc8ce4756344f2ade1
---
# [Diffusion][CPU] Adding AMX optimizations for CPU platform

URL: https://github.com/sgl-project/sglang/pull/28527
State: closed
Labels: Multi-modal, sgl-kernel, intel, cpu, run-ci, diffusion
Closed at: 2026-07-09T02:26:22Z
Merged at: 2026-07-09T02:26:22Z

This pr takes parts of follow-ups (mentioned in https://github.com/sgl-project/sglang/pull/20816) to bring key AMX based optimizations (scoping from LLM models) for CPU platforms, including:

- Adding CPU AMX backend, replace SDPA to bring best attention perf.
- Similar like for LLM models, adding replacement for amx weight packed linear. 
- Apply channel last 3d for VAE model

With above take Wan-AI/Wan2.2-TI2V-5B-Diffusers model as an example, the main stages show:

- TextEncodingStage speedup by 10x (bf16 encoding, if fp32 stays no change)
- DenoisingStage speedup by  2x
- DecodingStage speedup by 1.57x (bf16, enable channel last)


Besides, we still find more chance to bring more speedup (but with small ratio), by adding fusions (compile or kernel based) like rmsnorm/layernorm and newGELUs, will make this in followup PRs.

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28929873450](https://github.com/sgl-project/sglang/actions/runs/28929873450)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28929873154](https://github.com/sgl-project/sglang/actions/runs/28929873154)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
