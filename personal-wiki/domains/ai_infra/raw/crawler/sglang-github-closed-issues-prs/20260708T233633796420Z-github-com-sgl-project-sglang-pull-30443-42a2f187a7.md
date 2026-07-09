---
source_id: sglang-github-closed-issues-prs
title: '[NVIDIA] Allow modelopt_mixed quantization with flashinfer_cutedsl MoE runner'
canonical_url: https://github.com/sgl-project/sglang/pull/30443
captured_at: '2026-07-08T23:36:33.796420+00:00'
content_hash: 42a2f187a72d0e3cc2eeb83534c988f8d3c42006a9389752eb952c8de75732c0
---
# [NVIDIA] Allow modelopt_mixed quantization with flashinfer_cutedsl MoE runner

URL: https://github.com/sgl-project/sglang/pull/30443
State: closed
Labels: run-ci
Closed at: 2026-07-08T06:50:53Z
Merged at: 2026-07-08T06:50:53Z

## Motivation

ModelOpt MIXED_PRECISION checkpoints with NVFP4 MoE layers — e.g. [nvidia/Qwen3.5-397B-A17B-NVFP4-V2](https://huggingface.co/nvidia/Qwen3.5-397B-A17B-NVFP4-V2) (NVFP4 routed experts, FP8 attention/shared experts) — resolve to `quantization=modelopt_mixed` and fail to launch with `--moe-runner-backend flashinfer_cutedsl`:

```
AssertionError: Invalid quantization 'modelopt_mixed'.
FlashInfer CuteDSL MOE currently supports only: 'modelopt_fp4' or hybrid NVFP4 models.
```

This is an allowlist gap, not a kernel limitation: `modelopt_mixed` dispatches NVFP4 MoE layers to the same `ModelOptNvFp4FusedMoEMethod` (with an embedded `ModelOptFp4Config`) as `modelopt_fp4`, which the cutedsl runner already supports, and the adjacent `flashinfer_cutlass` / `flashinfer_trtllm` asserts already accept `modelopt_mixed`.

The assert's other escape, `nvfp4_moe_meta` (the "hybrid NVFP4 models" case), does not help here because it detects a different config format. Mixed-precision ModelOpt checkpoints come in two shapes (abridged):

```jsonc
// shape 1 — detected by nvfp4_moe_meta (e.g. DeepSeek-V4-Pro-NVFP4):
// a single top-level key declares "MoE is NVFP4"
"quantization_config": {
  "quant_algo": "MIXED_PRECISION",
  "moe_quant_algo": "NVFP4",
  "group_size": 16
}

// shape 2 — per-layer map (e.g. Qwen3.5-397B-A17B-NVFP4-V2):
// no top-level moe_quant_algo, so nvfp4_moe_meta stays None
"quantization_config": {
  "quant_method": "modelopt_mixed",
  "quant_algo": "MIXED_PRECISION",
  "quantized_layers": {
    "model.layers.*.mlp.experts.*": {"quant_algo": "NVFP4", "group_size": 16},
    "model.layers.*.self_attn.*":   {"quant_algo": "FP8"},
    ...
  }
}
```

Checkpoints of the second shape resolve to `quantization=modelopt_mixed` and currently have no way through the cutedsl gate.

## Modifications

`modelopt_mixed` now takes the same path as `modelopt_fp4` in the two places that gate the cutedsl runner:

1. `python/sglang/srt/server_args.py`: accept `modelopt_mixed` in the `flashinfer_cutedsl` quantization assert.
2. `python/sglang/srt/layers/moe/ep_moe/layer.py`: accept it in the `DeepEPMoE` `deprecate_flag` check, so cutedsl + `--moe-a2a-backend deepep` uses the FusedMoE runner path instead of the legacy `DeepEPMoE` initialization, which has no branch for the mixed config.

Mixed checkpoints whose MoE layers are not NVFP4 still pass this arg-level gate and are rejected at load time by the per-layer quant method — same behavior as the existing cutlass allowlist. Follow-up (not included): the `SGLANG_MOE_NVFP4_DISPATCH` auto-enable and the cutlass FP4-allgather heuristic still key on `modelopt_fp4` only; mixed deployments can set the env var explicitly.

## Verification

All on GB200 (sm_100) with `nvidia/Qwen3.5-397B-A17B-NVFP4-V2` (TP4, `--quantization modelopt_mixed --mamba-ssm-dtype bfloat16 --trust-remote-code`):

- **Argument-resolution A/B**: the parent commit reproduces the assertion verbatim; with this PR, args resolve to `quantization=modelopt_mixed runner=flashinfer_cutedsl` and cutedsl-specific handling applies (`--disable-shared-experts-fusion` auto-set).
- **TP4 + cutedsl serving, full weights**: all ranks report `(moe_runner_backend=flashinfer_cutedsl, quant_method=ModelOptNvFp4FusedMoEMethod)`; deterministic greedy outputs are correct.
- **DEP4 + `--moe-a2a-backend deepep --deepep-mode low_latency` + cutedsl** (exercises modification 2): serves correctly; greedy outputs identical to the TP4 run. Needed `--cuda-graph-max-bs-decode 32` to stay within DeepEP LL's dispatch-token bound — a pre-existing sizing constraint orthogonal to this PR.
- **GSM8K**, 200 examples via `sglang.test.run_eval` (temperature 0, max_tokens 16384), identical args except the runner:

| MoE runner | GSM8K score |
|---|---|
| `flashinfer_cutedsl` (this PR) | 0.985 |
| `flashinfer_cutlass` (control) | 0.990 |

Parity within noise (0.5 pp, 1 of 200 questions).

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).










<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28918596123](https://github.com/sgl-project/sglang/actions/runs/28918596123)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28918596045](https://github.com/sgl-project/sglang/actions/runs/28918596045)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
