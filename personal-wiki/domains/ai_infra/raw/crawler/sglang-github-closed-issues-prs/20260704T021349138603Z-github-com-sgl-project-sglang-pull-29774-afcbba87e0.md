---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] Shard QwenImage DiT across TP ranks'
canonical_url: https://github.com/sgl-project/sglang/pull/29774
captured_at: '2026-07-04T02:13:49.138603+00:00'
content_hash: afcbba87e0f343f7876e6c05c69b6852d769780922f3adbd50e943ef7a26677f
---
# [diffusion] Shard QwenImage DiT across TP ranks

URL: https://github.com/sgl-project/sglang/pull/29774
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-03T05:17:53Z
Merged at: 2026-07-03T05:17:53Z

## Motivation

`QwenImageTransformer2DModel` used `ReplicatedLinear` for all of its attention and feed-forward projections. Under tensor parallelism every rank therefore held a **full** copy of the DiT and recomputed the **entire** forward pass redundantly, so `--tp-size > 1` gave **no** memory saving and **negative** speedup (pure communication/sync overhead). On 32 GB GPUs the 38 GB DiT does not fit resident on a single card, so the only way to run multi-GPU was layer-wise CPU offload, which is slow.

This PR shards the DiT across TP ranks so tensor parallelism actually reduces per-GPU memory and speeds up denoising.

## Modifications

In `python/sglang/multimodal_gen/runtime/models/dits/qwen_image.py`:

- **Attention (`QwenImageCrossAttention`)**
  - `to_q/to_k/to_v` and `add_q_proj/add_k_proj/add_v_proj`: `ReplicatedLinear` → `ColumnParallelLinear(gather_output=False)`.
  - `to_out` and `to_add_out`: `ReplicatedLinear` → `RowParallelLinear(input_is_parallel=True)` (all-reduce on output).
  - Added `local_num_heads = num_heads // tp_size` with an assert that `num_heads % tp_size == 0`; `USPAttention` and the per-head `unflatten` now use `local_num_heads`.
- **Feed-forward**: `QwenImageGELU.proj` → `ColumnParallelLinear(gather_output=False)`; `QwenImageFeedForward.net.2` → `RowParallelLinear(input_is_parallel=True)`.
- **Embeddings / head**: `img_in`, `txt_in`, `proj_out` → `ColumnParallelLinear(gather_output=True)` (compute sharded, output gathered to full dim).
- The AdaLN modulation layers (`img_mod`/`txt_mod`) remain `ReplicatedLinear` (they operate on the full-dim conditioning).

At `tp_size == 1` the parallel layers degrade to plain linears, so the change is a no-op for single-GPU.

## Consistency with other DiTs

QwenImage was the only DiT in `runtime/models/dits/` still using `ReplicatedLinear` for its attention/FFN. The other TP-enabled DiTs already shard these with `ColumnParallelLinear` / `RowParallelLinear`, for example:

- **FLUX** (`flux.py`): `to_q/to_k/to_v` → `ColumnParallelLinear`, `to_out` → `RowParallelLinear`.
- **Wan** (`wanvideo.py`): `to_q/to_k/to_v` → `ColumnParallelLinear`, `to_out` → `RowParallelLinear`.
- **HunyuanVideo** (`hunyuanvideo.py`): `*_attn_qkv` → `MergedColumnParallelLinear`, `*_attn_proj` → `RowParallelLinear`.

This PR brings QwenImage in line with that convention (shard attention QKV/output + FFN, keep only the AdaLN modulation replicated).

## Environment & Test Parameters

**Environment**
- GPU: NVIDIA RTX 5090 32 GB (sm_120); driver 595.58.03 / CUDA 13.2, CUDA toolkit 13.0
- PyTorch 2.11.0+cu130, Python 3.12

**Test parameters**
- Model: `Qwen/Qwen-Image-Edit-2511` (DiT = `QwenImageTransformer2DModel`, bf16)
- Workload: 10 production image-edit (i2i) samples
- Resolutions: 810×1440 (portrait) and 1440×810 (landscape)
- `num_inference_steps = 40`, `seed = 42`, `guidance_scale = 0`, `strength = 1`
- Attention backend: Torch SDPA (auto-selected on sm_120); dtype bf16
- Latency = mean over the 10 samples excluding the warmup request

## Accuracy Tests

"Before" = parent commit (`ReplicatedLinear`); "after" = this PR.

| # | Comparison | Result | Meaning |
|---|------------|--------|---------|
| C1 | before TP=1 vs after TP=1 | **10/10 bit-identical** (max pixel Δ = 0) | Decisive: with no satically equivalent — a lossless refactor. |
| C2 | after TP=2 run twice | **10/10 bit-identical** | Pipeline is deterministic, so the C3 deltas are real, not run-to-run noise. |
| C3 | before TP=2 vs after TP=2 | avg PSNR 33.97 dB (27.2–44.5), 0/10 bit-identical; **manual review of all 10 pairs: equivalent quality** | At TP > 1, sharding changes only the floating-point all-reduce **reduction order**; the diffusion sampler amplifies this into fine-detail pixel differences. A side-by-side review of all 10 before/after pairs confirms identical scene/composition/subject and **no quality change** (no artifacts or degradation) — the residual PSNR is reduction-order numerical noise, not a quality regression. |

## Speed Tests and Profiling

Same TP degree and same offload mode are compared side by side.

**Denoising / E2E latency (s):**

| Config | before (denoise / E2E) | after (denoise / E2E) |
|--------|------------------------|-----------------------|
| TP=1 (CPU offload) | 41.82 / 42.90 | 41.81 / 42.90 |
| TP=2 (layer-wise offload, both sides) | 58.02 / 59.28 | 38.90 / 39.93 |
| TP=4 (resident, `--dit-cpu-offload false`) | **OOM at load (cannot start)** | **19.05 / 20.74**

- **Same-config speedup**: at TP=2, **1.49× denoising** (58.0 → 38.9 s); both sides use layer-wise is DiT sharding. Before the fix each rank redundantly computes the whole DiT and streams the full
38 GB of weights, so TP is pure overhead (TP=2 is even slower than TP=1); after the fix each rank rd.
- **Enables TP=4**: the DiT is 38 GB/rank. Before the fix it cannot produce output at TP=4 — OOM at load with `--dit-cpu-offload false`, or OOM during the denoise step under the default full CPU offload. After the fix it shards to 19 GB/rank, runs resident, **19.05 s denoise / 20.74 s E2E**.


**Per-rank DiT weight memory (`model size`, GB):**

| TP | before | after |
|----|-------:|------:|
| 1 | 38.05 | 38.05 |
| 2 | **38.05** | **25.39** (−33%) |
| 4 | OOM | **19.05** (−50%) |

Before the fix the per-rank DiT is 38.05 GB regardless of TP (no sharding)

## Checklist

- [x] Provided accuracy and speed benchmark results (above).
- [ ] Format code with pre-commit.
- [ ] Add unit tests.
- [ ] Update documentation.
- [x] Follow the SGLang code style guidance.





















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28638267986](https://github.com/sgl-project/sglang/actions/runs/28638267986)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28638267940](https://github.com/sgl-project/sglang/actions/runs/28638267940)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
