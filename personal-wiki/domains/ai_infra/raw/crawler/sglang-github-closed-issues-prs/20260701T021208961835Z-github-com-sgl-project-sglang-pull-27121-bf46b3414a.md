---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Shard QwenImage cross-attention and FFN across TP ranks'
canonical_url: https://github.com/sgl-project/sglang/pull/27121
captured_at: '2026-07-01T02:12:08.961835+00:00'
content_hash: bf46b3414ae7f8d74996b6c1718618dc0197f13a8a518c9c842f025808e0a90c
---
# [diffusion] Shard QwenImage cross-attention and FFN across TP ranks

URL: https://github.com/sgl-project/sglang/pull/27121
State: closed
Labels: diffusion
Closed at: 2026-06-22T01:52:12Z
Merged at: 

## Motivation

`QwenImageCrossAttention`, `QwenImageGELU`, and `QwenImageFeedForward` use `ReplicatedLinear` for the per-modality q/k/v and output projections. That means launching `sglang serve --tp-size N` does not actually shard the DiT — every TP rank stores the full projection weights and re-computes the same matmul. On a 2× RTX 5090 box running `FireRed-Image-Edit-1.1` (The structure is the same as `Qwen-Image-Edit-2509`, so it exercises the exact `QwenImageTransformer2DModel` modules touched by this fix) with the Lightning-8steps LoRA and `--tp-size 2 --dit-layerwise-offload`:

- **Per-step denoising is ~32 % slower than it should be**: 2.15 s/step average vs 1.46 s/step after sharding.
- **Host memory is wasted by ~138 GB**: each TP rank pins the full DiT shard for layerwise prefetch (2× duplication), 369 GB PSS before vs 231 GB PSS after (PSS = proportional set size, attributes shared memory pages to the processes that map them, so multi-process pinned buffers don't double-count).
- **Sharded paths elsewhere can mis-shape attention**: any code path that assumes `local_num_heads = num_heads // tp_size` (for example, when the QKV-fused branch via `MergedColumnParallelLinear` is selected on neighboring layers) sees inconsistent head counts between fused and non-fused linears.

The fix switches the same linear-class pattern used by the rest of the model (and by the already-correct QKV-fused branch in this file) onto the non-fused branch.

## Modifications

`python/sglang/multimodal_gen/runtime/models/dits/qwen_image.py` (+39 / −18):

- `to_q` / `to_k` / `to_v` and `add_q_proj` / `add_k_proj` / `add_v_proj` → `ColumnParallelLinear(gather_output=False)`.
- `to_add_out`, `to_out.0`, and `QwenImageFeedForward.net.2` → `RowParallelLinear(input_is_parallel=True)`. `QwenImageGELU.proj` → `ColumnParallelLinear(gather_output=False)` so the matched `FFN.net.2` RowParallel sees a sharded input.
- New `tp_size = get_tp_world_size()` and `local_num_heads = num_heads // tp_size` in `QwenImageCrossAttention.__init__`, with a divisibility assert (`num_heads % tp_size == 0`).
- The QKV `unflatten(-1, (self.num_heads, -1))` becomes `unflatten(-1, (self.local_num_heads, self.head_dim))` so each rank reshapes only its own heads.
- Imports: add `get_tp_world_size`, `ColumnParallelLinear`, `RowParallelLinear` next to the existing parallel-linear imports.
- At `--tp-size 1` the change is mathematically a no-op (`local_num_heads == num_heads`, no all-reduce), so the single-GPU and non-TP paths are unaffected.

The QKV-fused branch (`use_fused_qkv` via `MergedColumnParallelLinear`) is unchanged — it already sharded correctly.

## Accuracy Tests

10 image-edit test cases were each run twice — once with CFG off (`--guidance-scale 0`) and once with CFG on (`--guidance-scale 1.2`) — for **20 paired generations per branch**. All 20 outputs on each branch were manually inspected on the bench. Outputs on `before` and `after` are visually indistinguishable at production quality — no perceptible degradation, no structural artifacts, no color shifts visible to the eye.

The fix is a `ReplicatedLinear → ColumnParallelLinear / RowParallelLinear` swap, so the math changes only in *which order* the matmul reductions happen (each `RowParallel` now ends with an all-reduce instead of a single matmul on a full weight tensor).

LoRA also works transparently: the Lightning-8steps adapter (720 / 846 LoRA layers) loads and applies cleanly to the new sharded linears, with no warnings on either branch.

## Speed Tests and Profiling

The same 20 generations (10 cases × {CFG off, CFG on}, 8 inference steps each, 810×1440 or 1440×810 per case) were timed on each branch with identical `sglang serve` command, identical LoRA, identical seed, identical hardware. The only thing that differed was the branch checkout (`main` vs `fix/qwen-image-tp-sharding`). Per-step time is `[DenoisingStage] average time per step` from the server log; host memory is per-process PSS summed across the sglang process tree only (via `/proc/<pid>/smaps_rollup`), so unrelated processes on the box are excluded.

Headline (across all 20 paired requests):

| Metric | before (`main`) | after (TP fix) | Δ (mean per-pair) |
| --- | ---: | ---: | ---: |
| **DenoisingStage per-step (avg)** | **2.1500 s** | **1.4598 s** | **−32.06 %** (range −30.85 % ~ −32.62 %) |
| **Inference E2E per request (avg)** | **19.223 s** | **13.398 s** | **−30.26 %** (range −29.39 % ~ −31.27 %) |
| Benchmark total wall (20 generations) | 391 s | 276 s | −115 s / −29.4 % |
| Boot → server ready | 226 s | 175 s | −51 s / −22.6 % |
| Peak GPU per card (sampled) | 17 515 MiB | 15 511 MiB | ≈ −2 GiB |
| Mean per-request `Peak memory usage` (server-logged) | 12 487 MB | 10 738 MB | −1 749 MB (−14 %) |
| **Peak host PSS (sglang process tree)** | **378 423 MiB (369 GB)** | **236 270 MiB (231 GB)** | **−138 GB (−37.4 %)** |

By guidance scale (the fix's per-step speedup is the same in both regimes):

| Scale | before per-step | after per-step | Δ | before E2E | after E2E | Δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (single forward) | 1.4021 s | 0.9543 s | **−31.94 %** | 12.95 s | 9.04 s | −30.15 % |
| 1.2 (CFG on, 2× batch) | 2.8980 s | 1.9654 s | **−32.18 %** | 25.50 s | 17.75 s | −30.38 % |

The per-pair speedup is consistent across all 20 cases — per-pair standard deviation ≈ 0.5 percentage points on per-step, ≈ 0.6 pp on E2E — and is reproducible across two separately-booted runs of the same benchmark (cross-run difference < 0.2 pp), so the deltas are well outside measurement noise.

Why the host-memory delta is so large: with `ReplicatedLinear` each TP rank pins the full DiT-shard parameters to host memory so layerwise offload can H2D-prefetch them; on a 2-rank server that means the q/k/v + output + FFN weights are duplicated across ranks. After the fix each rank pins only its column / row shard, recovering ~138 GB of host PSS for `Qwen-Image-Edit`-class DiTs at TP=2.

### Repro command (same on both branches, only the checkout differs)

```bash
CUDA_VISIBLE_DEVICES=0,1 sglang serve \
  --model-path /path/to/FireRed-Image-Edit-1.1 \
  --num-gpus 2 --tp-size 2 --port 30000 \
  --dit-layerwise-offload --dit-offload-prefetch-size 4 \
  --text-encoder-cpu-offload true \
  --lora-path /path/to/FireRed-Image-Edit-1.0-Lightning-8steps-v1.1.stripped.safetensors \
  --lora-scale 1 \
  --host 0.0.0.0
```

## Checklist

- [x] Format your code according to [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit). `black --check`, `isort --check`, and `ruff --select=F401,F821` all clean against `qwen_image.py` (versions pinned by `.pre-commit-config.yaml`: black 26.1.0, isort 7.0.0, ruff 0.15.1).
- [x] Add unit tests according to [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). The change is a model-construction-time swap of `ReplicatedLinear → ColumnParallelLinear / RowParallelLinear`; correctness at TP > 1 requires a real multi-GPU run, which is covered by the 20-pair benchmark above (the divisibility assert in `QwenImageCrossAttention.__init__` guards the per-rank reshape at construction). `python -m unittest python.sglang.multimodal_gen.test.unit.test_server_args` still passes 74 / 74 on this branch. 
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). No user-facing flag changes; `--tp-size N` now behaves as advertised on this DiT. No documentation page describes the per-attention-class parallelism choice.
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). 20 paired generations (10 cases × {CFG off, CFG on}) manually verified for quality and timed for speed; all numbers above were collected from those runs.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance). Code style preserved; passes the repo's pre-commit-config-pinned `black` / `isort` / `ruff` versions.




























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27006216734](https://github.com/sgl-project/sglang/actions/runs/27006216734)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27006216574](https://github.com/sgl-project/sglang/actions/runs/27006216574)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
