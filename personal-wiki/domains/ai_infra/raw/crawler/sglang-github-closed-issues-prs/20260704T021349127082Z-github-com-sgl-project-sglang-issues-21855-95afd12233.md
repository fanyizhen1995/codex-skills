---
source_id: sglang-github-closed-issues-prs
title: '[Feature] Replace memory-bound custom CUDA kernels with torch.compile generated
  fusions'
canonical_url: https://github.com/sgl-project/sglang/issues/21855
captured_at: '2026-07-04T02:13:49.127082+00:00'
content_hash: 95afd12233b443b40ad9229d7f66651a64f9d19abcaaf4b1e7ca42233ce8d812
---
# [Feature] Replace memory-bound custom CUDA kernels with torch.compile generated fusions

URL: https://github.com/sgl-project/sglang/issues/21855
State: closed
Labels: inactive, performance, nvidia
Closed at: 2026-07-04T00:38:23Z
Merged at: 

## Motivation

A portion of decode latency in SGLang today comes from **memory-bound pointwise operations** — RMSNorm, rotary embedding, q/k normalization, KV-cache stores — that sit between compute-bound kernels (GEMMs, attention, MoE). Even on the decode path under CUDA graphs, these regions remain good optimization targets because performance is still shaped by kernel quality, fusion boundaries, and avoidable memory traffic.

We have been experimenting with `torch.compile` to **fuse these memory-bound regions** into fewer compiler-generated Triton kernels. The approach is strictly opt-in, targets only the decode path inside CUDA graphs, and requires no changes to the serving pipeline or model weights. Across five models spanning two architecture families, we observe **consistent end-to-end throughput improvements of +0.5 % to +8.2 %**.

### Why a compiler-first approach

These results show that **compiler-generated kernels** can be on par with, and in several cases better than, hand-written CUDA/Triton kernels on real decode workloads. That matters not only for the measured speedups, but because it offers SGLang a more scalable path to broaden **optimization coverage** across model patterns, reduce bespoke kernel **maintenance**, and track future hardware, dtype, and backend **evolution** with less model-specific work.
For example, instead of carrying separate custom kernels for `RMSNorm` and `GemmaRMSNorm`, or different rope implementations, improving the **native PyTorch implementation** is enough for the compiler to optimize them through the same infrastructure.

---

## Approach

We use `torch.compile` with **local scope** (`--torch-compile-scope local`) to compile individual layers or sub-modules within the decoder stack. This avoids graph breaks at attention/MoE boundaries and composes cleanly with SGLang's existing CUDA graph capture. The opportunities we found are better described as a few reusable optimization patterns rather than a fixed list of hand-picked kernels:

| Optimization pattern | Representative examples | Why compiler helps | Shape behavior |
|----------------------|-------------------------|--------------------|----------------|
| **Memory-bound normalization / epilogue work** | RMSNorm, GemmaRMSNorm, lightweight reshapes and pointwise cleanup around attention/MLP boundaries | These ops are dominated by data movement rather than heavy math. Compiling them reduces launch count and avoids extra reads/writes through intermediate tensors, which matters in decode where the same short regions repeat every token. | Static within a CUDA-graph batch bucket, so Inductor can specialize well. |
| **Horizontal fusion across sibling tensors** | q/k normalization, or other same-shape work applied independently to multiple projections | When similar work is performed on several tensors with the same shape and layout, the compiler can fuse that work into fewer kernels or fewer graphs, instead of requiring a bespoke manually fused implementation. | Static within a CUDA-graph batch bucket, so Inductor can specialize well. |
| **Automatic multi-mode cache-write fusion** | Rotary embedding fused with KV-cache stores, including SWA and non-SWA address modes | Expressing cache update logic in PyTorch gives the compiler visibility into both the transform and the store path, so it can fuse them even when the cache writer has multiple addressing modes that would otherwise force separate kernels. | Dynamic because `cache_loc` and write destinations vary at runtime. |

Key technical details:

- **Static-shape regions are the easiest wins.** Normalization, q/k preprocessing, and many reshapes naturally specialize to the fixed decode batch sizes used by CUDA-graph buckets.
- **Dynamic-shape regions can still be worthwhile.** Rope + KV-cache update has less room for specialization because `cache_loc` changes at runtime, but it can still win by collapsing several launches and memory passes into a single compiled kernel.
- **SWA is one concrete example of the broader cache-write fusion pattern.** `SWAKVPool` uses dual addressing — SWA layers write to `out_cache_loc_swa`, non-SWA layers to `out_cache_loc` — which the current JIT rope path cannot fuse. In the pure-PyTorch path this logic is expressed as `index_put_`-style updates, giving Inductor enough visibility to fold the transform and the write into the same compiled graph.

---

## Results

All benchmarks use `bench_offline_throughput` with ShareGPT dataset on **NVIDIA GB200**, measured against the SGLang baseline at commit `cb8105fe` with `sgl_kernel 0.3.21` and PyTorch nightly 2.12.

In each subsection title, the layers listed after the model name denote the local decode region targeted by `torch.compile` in that experiment.

### `openai/gpt-oss-120b` (mxfp4, TP=4) — RotaryEmbedding / KVCacheWrite

Inductor-compiled RotaryEmbedding with fused KV-cache writes delivers **+5 % to +8 %** across all batch sizes.

<details>
<summary><b>Full benchmark table</b></summary>

| Batch size | Config | Output tok/s | Total tok/s | Total tok/s vs Baseline |
|------------|--------|--------------|-------------|-------------------------|
| 1 | Baseline | 448 | 449 | — |
| 1 | Inductor — RopeKV | 471 | 472 | **+5.1 %** |
| 32 | Baseline | 8,844 | 9,178 | — |
| 32 | Inductor — RopeKV | 9,467 | 9,826 | **+7.1 %** |
| 128 | Baseline | 20,150 | 21,046 | — |
| 128 | Inductor — RopeKV | 21,810 | 22,780 | **+8.2 %** |

</details>

<details>
<summary><b>Nsys kernel trace — gpt-oss-120b baseline vs. Inductor</b></summary>

**Baseline:** Multiple separate kernels per layer — `fused_rope_kernel`, ATen `index_put_` kernels for SWA addressing, `store_kvcache`, then the attention kernel.

<img width="2186" height="153" alt="Image" src="https://github.com/user-attachments/assets/67918ad1-d764-4116-b1d3-e209e09d9b58" />

**Inductor — RotaryEmbedding:** All of the above replaced by a single fused Triton kernel (`triton_poi_fused_0`) that performs rope and KV-cache write in one pass.

<img width="1855" height="131" alt="Image" src="https://github.com/user-attachments/assets/90696f17-fd79-46b3-a19b-ac79f2261d8c" />

</details>

---

### `lmsys/gpt-oss-20b-bf16` (bf16, TP=1) — RotaryEmbedding / KVCacheWrite / RMSNorm

> **Note:** Enabling `torch.compile` currently disables piecewise CUDA graphs. The fair baseline is therefore `Baseline (no piecewise CG)`. The `with piecewise CG` rows below show the current production default; once piecewise CG works alongside `torch.compile`, Inductor configs should also benefit from it.

Relative to the fair baseline without piecewise CUDA graphs, Inductor reaches up to **+4.7 %** total throughput at B=128.

<details>
<summary><b>Full benchmark table</b></summary>

| Batch size | Config | Output tok/s | Total tok/s | Total tok/s vs Baseline |
|------------|--------|--------------|-------------|-------------------------|
| 1 | with piecewise CG | 181 | 181 | — |
| 1 | Baseline (no piecewise CG) | 179 | 179 | — |
| 1 | Inductor — RopeKV + RMSNorm | 176 | 176 | −1.7 % |
| 1 | Inductor — RopeKV | 182 | 182 | **+1.7 %** |
| 1 | Inductor — RMSNorm | 182 | 182 | **+1.4 %** |
| 32 | with piecewise CG | 4,793 | 4,974 | — |
| 32 | Baseline (no piecewise CG) | 4,644 | 4,820 | — |
| 32 | Inductor — RopeKV + RMSNorm | 4,864 | 5,048 | **+4.7 %** |
| 32 | Inductor — RopeKV | 4,854 | 5,038 | **+4.5 %** |
| 32 | Inductor — RMSNorm | 4,851 | 5,035 | **+4.5 %** |
| 128 | with piecewise CG | 12,229 | 12,773 | — |
| 128 | Baseline (no piecewise CG) | 11,711 | 12,232 | — |
| 128 | Inductor — RopeKV + RMSNorm | 11,763 | 12,286 | **+0.4 %** |
| 128 | Inductor — RopeKV | 12,234 | 12,778 | **+4.5 %** |
| 128 | Inductor — RMSNorm | 12,110 | 12,649 | **+3.4 %** |

</details>

---

### `Qwen/Qwen3-30B-A3B` (bf16, TP=1) — RotaryEmbedding / KVCacheWrite / RMSNorm / QKNorm

Gains of **+1 % to +3.3 %** at medium-to-high concurrency.

<details>
<summary><b>Full benchmark table</b></summary>

| Batch size | Config | Output tok/s | Output tok/s vs Baseline | Total tok/s | Total tok/s vs Baseline |
|------------|--------|--------------|---------------------------|-------------|-------------------------|
| 1 | Baseline | 358 | — | 359 | — |
| 1 | Inductor — QKNormRopeKV + RMSNorm | 338 | −5.6 % | 339 | −5.6 % |
| 1 | Inductor — QKNorm + RopeKV + RMSNorm | 351 | −2.0 % | 351 | −2.0 % |
| 1 | Inductor — RopeKV + RMSNorm | 348 | −2.8 % | 348 | −2.8 % |
| 1 | Inductor — RopeKV | 360 | **+0.6 %** | 361 | **+0.5 %** |
| 1 | Inductor — RMSNorm | 346 | −3.4 % | 347 | −3.3 % |
| 32 | Baseline | 3,319 | — | 3,447 | — |
| 32 | Inductor — QKNormRopeKV + RMSNorm | 3,297 | −0.7 % | 3,424 | −0.7 % |
| 32 | Inductor — QKNorm + RopeKV + RMSNorm | 3,377 | **+1.7 %** | 3,507 | **+1.7 %** |
| 32 | Inductor — RopeKV + RMSNorm | 3,427 | **+3.3 %** | 3,558 | **+3.2 %** |
| 32 | Inductor — RopeKV | 3,401 | **+2.5 %** | 3,532 | **+2.5 %** |
| 32 | Inductor — RMSNorm | 3,368 | **+1.5 %** | 3,497 | **+1.5 %** |
| 128 | Baseline | 6,963 | — | 7,280 | — |
| 128 | Inductor — QKNormRopeKV + RMSNorm | 7,019 | **+0.8 %** | 7,338 | **+0.8 %** |
| 128 | Inductor — QKNorm + RopeKV + RMSNorm | 7,111 | **+2.1 %** | 7,435 | **+2.1 %** |
| 128 | Inductor — RopeKV + RMSNorm | 7,048 | **+1.2 %** | 7,368 | **+1.2 %** |
| 128 | Inductor — RopeKV | 7,030 | **+1.0 %** | 7,350 | **+1.0 %** |
| 128 | Inductor — RMSNorm | 6,958 | −0.1 % | 7,274 | −0.1 % |
| 256 | Baseline | 7,316 | — | 7,589 | — |
| 256 | Inductor — RopeKV + RMSNorm | 7,366 | **+0.7 %** | 7,640 | **+0.7 %** |
| 256 | Inductor — QKNorm + RopeKV + RMSNorm | 7,353 | **+0.5 %** | 7,627 | **+0.5 %** |
| 512 | Baseline | 7,450 | — | 7,736 | — |
| 512 | Inductor — QKNorm + RopeKV + RMSNorm | 7,566 | **+1.6 %** | 7,857 | **+1.6 %** |
| 512 | Inductor — RopeKV + RMSNorm | 7,521 | **+1.0 %** | 7,810 | **+1.0 %** |

</details>

Splitting q/k normalization into a separate static-shape graph (`QKNorm + RopeKV`) substantially improves over the fully-fused variant (`QKNormRopeKV`): at B=1 the regression drops from −5.6 % to −2.0 %, at B=32 it flips from −0.7 % to **+1.7 %**, and at B≥128 it consistently leads.

<details>
<summary><b>Nsys kernel trace — Qwen3-30B-A3B baseline vs. Inductor</b></summary>

**Baseline:** 3 kernels between the projection GEMM and attention — fused q/k normalization, then two kernels for rope + KV-cache store (split by an intermediate `contiguous` call).

**Inductor:** Compiles this region into only 2 kernels, eliminating the extra launch.

<!-- Attach: Qwen3-30B-A3B baseline vs inductor nsys side-by-side -->
| Baseline | Inductor |
|---|---|
| <img width="988" height="185" alt="Image" src="https://github.com/user-attachments/assets/f477930c-3256-4293-b245-bbfdde430d38" /> | <img width="599" height="158" alt="Image" src="https://github.com/user-attachments/assets/1fc948e5-8d71-4fdb-829a-003eb448c591" /> |

</details>

---

### `Qwen/Qwen3.5-35B-A3B-FP8` (FP8, TP=1) — Reshape / QKNorm / RotaryEmbedding /KVCacheWrite / GemmaRMSNorm

Consistent gains of **+0.5 % to +2.9 %** across most batch sizes, with the broadest compilation scope tested.

<details>
<summary><b>Full benchmark table</b></summary>

| OSL | Batch size | Config | Output tok/s | Output tok/s vs Baseline | Total tok/s | Total tok/s vs Baseline |
|-----|------------|--------|--------------|---------------------------|-------------|-------------------------|
| 8192 | 1 | Baseline | 289 | — | 289 | — |
| 8192 | 1 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 294 | **+1.8 %** | 294 | **+1.8 %** |
| 8192 | 4 | Baseline | 886 | — | 911 | — |
| 8192 | 4 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 911 | **+2.9 %** | 937 | **+2.9 %** |
| 8192 | 8 | Baseline | 1,572 | — | 1,607 | — |
| 8192 | 8 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 1,594 | **+1.4 %** | 1,629 | **+1.4 %** |
| 8192 | 16 | Baseline | 2,567 | — | 2,722 | — |
| 8192 | 16 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 2,616 | **+1.9 %** | 2,774 | **+1.9 %** |
| 8192 | 32 | Baseline | 3,992 | — | 4,151 | — |
| 8192 | 32 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 3,914 | −2.0 % | 4,069 | −2.0 % |
| 8192 | 64 | Baseline | 6,269 | — | 6,513 | — |
| 8192 | 64 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 6,303 | **+0.5 %** | 6,548 | **+0.5 %** |
| 8192 | 128 | Baseline | 9,478 | — | 9,920 | — |
| 8192 | 128 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 9,549 | **+0.7 %** | 9,994 | **+0.7 %** |
| 8192 | 256 | Baseline | 13,603 | — | 14,125 | — |
| 8192 | 256 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 13,702 | **+0.7 %** | 14,227 | **+0.7 %** |
| 8192 | 512 | Baseline | 11,176 | — | 11,619 | — |
| 8192 | 512 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 11,233 | **+0.5 %** | 11,678 | **+0.5 %** |
| 1024 | 1 | Baseline | 282 | — | 287 | — |
| 1024 | 1 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 287 | **+1.9 %** | 292 | **+1.9 %** |
| 1024 | 4 | Baseline | 868 | — | 1,066 | — |
| 1024 | 4 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 884 | **+1.9 %** | 1,086 | **+1.9 %** |
| 1024 | 8 | Baseline | 1,533 | — | 1,802 | — |
| 1024 | 8 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 1,565 | **+2.1 %** | 1,839 | **+2.1 %** |
| 1024 | 16 | Baseline | 2,550 | — | 3,779 | — |
| 1024 | 16 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 2,443 | −4.2 % | 3,621 | −4.2 % |
| 1024 | 32 | Baseline | 3,968 | — | 5,226 | — |
| 1024 | 32 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 3,906 | −1.6 % | 5,145 | −1.6 % |
| 1024 | 64 | Baseline | 6,371 | — | 8,351 | — |
| 1024 | 64 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 6,335 | −0.6 % | 8,304 | −0.6 % |
| 1024 | 128 | Baseline | 9,798 | — | 13,453 | — |
| 1024 | 128 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 9,892 | **+1.0 %** | 13,582 | **+1.0 %** |
| 1024 | 256 | Baseline | 14,601 | — | 19,081 | — |
| 1024 | 256 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 14,723 | **+0.8 %** | 19,240 | **+0.8 %** |
| 1024 | 512 | Baseline | 18,256 | — | 24,045 | — |
| 1024 | 512 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 18,419 | **+0.9 %** | 24,259 | **+0.9 %** |

</details>

> Qwen3.5 is a hybrid architecture: only 10 of 40 layers use full attention (`full_attention_interval=4`); Inductor targets only those layers, so the optimized region covers just 25 % of the decoder stack.

<details>
<summary><b>Nsys kernel trace — Qwen3.5-35B-A3B-FP8 baseline vs. Inductor</b></summary>

The latency of the targeted region between the projection GEMM (`deep_gemm`) and the attention kernel (`fmhaSm100fKernel`) drops by **~50 %** (11,077 μs → 5,231 μs) with B=32.

<!-- Attach: Qwen3.5-35B-A3B-FP8 baseline vs inductor nsys screenshots -->
| Baseline | Inductor |
|---|---|
|<img width="1313" height="165" alt="Image" src="https://github.com/user-attachments/assets/7e999cba-8849-4ee4-8f7e-cddef576d8d8" /> | <img width="1311" height="167" alt="Image" src="https://github.com/user-attachments/assets/6ce503ef-a5c4-4835-9d5f-fb3e1d361061" /> |

</details>

---

### `Qwen/Qwen3.5-397B-A17B-FP8` (FP8, TP=4, dummy weights) - Reshape / QKNorm / RotaryEmbedding /KVCacheWrite / GemmaRMSNorm

Steady **+0.2 % to +1.3 %** across all batch sizes, confirming the approach scales to large multi-GPU models.

<details>
<summary><b>Full benchmark table</b></summary>

| Batch size | Config | Output tok/s | Output tok/s vs Baseline | Total tok/s | Total tok/s vs Baseline |
|------------|--------|--------------|---------------------------|-------------|-------------------------|
| 1 | Baseline | 155 | — | 155 | — |
| 1 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 157 | **+1.3 %** | 157 | **+1.3 %** |
| 4 | Baseline | 583 | — | 600 | — |
| 4 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 590 | **+1.2 %** | 607 | **+1.2 %** |
| 8 | Baseline | 1,124 | — | 1,148 | — |
| 8 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 1,138 | **+1.3 %** | 1,163 | **+1.3 %** |
| 16 | Baseline | 2,096 | — | 2,222 | — |
| 16 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 2,109 | **+0.6 %** | 2,236 | **+0.6 %** |
| 32 | Baseline | 3,398 | — | 3,533 | — |
| 32 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 3,432 | **+1.0 %** | 3,568 | **+1.0 %** |
| 64 | Baseline | 5,480 | — | 5,693 | — |
| 64 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 5,535 | **+1.0 %** | 5,750 | **+1.0 %** |
| 128 | Baseline | 8,092 | — | 8,469 | — |
| 128 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 8,114 | **+0.3 %** | 8,492 | **+0.3 %** |
| 256 | Baseline | 6,296 | — | 6,537 | — |
| 256 | Inductor — Reshape + QKNorm + RopeKV + GemmaRMSNorm | 6,310 | **+0.2 %** | 6,552 | **+0.2 %** |

</details>

---

## Summary of gains across all models

| Model | Precision | TP | Best gain | Batch size range tested |
|-------|-----------|---:|----------:|:-----------------------:|
| gpt-oss-120b | mxfp4 | 4 | **+8.2 %** | 1–128 |
| gpt-oss-20b-bf16 | bf16 | 1 | **+4.7 %** | 1–128 |
| Qwen3-30B-A3B | bf16 | 1 | **+3.3 %** | 1–512 |
| Qwen3.5-35B-A3B-FP8 | FP8 | 1 | **+2.9 %** | 1–512 |
| Qwen3.5-397B-A17B-FP8 | FP8 | 4 | **+1.3 %** | 1–256 |

---

## Portability

The compiled regions use standard PyTorch modules (RMSNorm, RotaryEmbedding, etc.), so **any model using the same layer types benefits with zero code changes**.

---

## Benchmark environment

| Component | Version |
|-----------|---------|
| Device | NVIDIA GB200 |
| SGLang | commit `cb8105fe` |
| sgl_kernel | 0.3.21 |
| PyTorch | nightly 2.12 |
| Dataset | ShareGPT |
| Benchmark | `bench_offline_throughput` |

---

## Next steps

We plan to open a follow-up PR demonstrating `torch.compile` integration for the compiled regions, the `--torch-compile-override-layers` and `--torch-compile-scope local` opt-in flags, and composition with existing CUDA graph capture.

We welcome feedback on:

- Which models / batch size regimes are highest priority for the SGLang community
- Whether the opt-in flag design (`--enable-torch-compile --torch-compile-override-layers <layers> --torch-compile-scope local`) fits the project's configuration philosophy

cc @nvpohanh @IvanYashchuk

### Related resources

_No response_
