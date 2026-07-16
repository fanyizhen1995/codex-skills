---
source_id: sglang-github-closed-issues-prs
title: Make the mxfp8 MoE runner backend list extensible
canonical_url: https://github.com/sgl-project/sglang/pull/30828
captured_at: '2026-07-12T23:38:53.056069+00:00'
content_hash: 29af97289c91ae257bf83448f3275fbaa06a4e1b733a5834ca26fff8850038fa
---
# Make the mxfp8 MoE runner backend list extensible

URL: https://github.com/sgl-project/sglang/pull/30828
State: closed
Labels: run-ci
Closed at: 2026-07-12T08:28:11Z
Merged at: 2026-07-12T08:28:11Z

## Motivation

The mxfp8 quantization → MoE runner-backend allowlist is hardcoded inline in `_moe_runner_backend_quant_constraints` (`arg_groups/overrides.py`). Downstream forks that add their own mxfp8-compatible MoE runner backend currently have to patch that constraint logic to avoid the "Overriding ..." warning + fallback.

This mirrors the existing extension hooks (`add_moe_runner_backend_choices`, `add_linear_attn_kernel_backend_choices`, etc.): extract the list into a module-level global and add a registration helper, so external code can extend it without touching OSS constraint logic.

## Changes

- `server_args.py`: add `MXFP8_MOE_RUNNER_BACKEND_CHOICES` (`cutlass`, `flashinfer_trtllm`, `flashinfer_trtllm_routed`) and `add_mxfp8_moe_runner_backend_choices()`.
- `arg_groups/overrides.py`: the mxfp8 branch checks membership against the global and derives its warning message from it (so the message can't drift). Uses the same lazy `from sglang.srt.server_args import ...` pattern already used there for `DETERMINISTIC_ATTENTION_BACKEND_CHOICES`.

No behavior change for the built-in backends.

## Test

`python -m py_compile` on both files; existing arg-resolution tests cover the mxfp8 constraint path. No numerics touched.

## Original commits

- `eec153054`















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29185047580](https://github.com/sgl-project/sglang/actions/runs/29185047580)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29185047507](https://github.com/sgl-project/sglang/actions/runs/29185047507)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
