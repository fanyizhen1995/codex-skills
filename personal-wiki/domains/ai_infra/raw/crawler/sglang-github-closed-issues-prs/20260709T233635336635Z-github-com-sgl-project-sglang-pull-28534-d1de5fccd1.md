---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Enable JIT staged HiCache write-back and fix CPU-index crash'
canonical_url: https://github.com/sgl-project/sglang/pull/28534
captured_at: '2026-07-09T23:36:35.336635+00:00'
content_hash: d1de5fccd193c6afcaef991ebdb88244a7ba7763c08d1327efda7644e3530ba7
---
# [AMD] Enable JIT staged HiCache write-back and fix CPU-index crash

URL: https://github.com/sgl-project/sglang/pull/28534
State: closed
Labels: hicache, run-ci, jit-kernel, bypass-fastfail, run-ci-extra
Closed at: 2026-07-09T08:22:38Z
Merged at: 2026-07-09T08:22:38Z

On ROCm, `page_first` + `kernel` HiCache write-back crashes on the first prefill with `RuntimeError: Destination indices must be a CUDA tensor`. This PR fixes the underlying cause so ROCm runs the **same** `page_first` + `kernel` JIT staged write-back path as CUDA, instead of the #28473 `layer_first` fallback.

## Root cause

`HiCacheController.start_writing()` keeps `host_indices` on the CPU for the `kernel` io-backend + `page_first` layout, assuming the staged JIT write-back kernel (which stages through device memory and accepts a CPU destination index) will consume them. That JIT path is gated behind `_is_cuda`, so on ROCm it is disabled and the code falls back to the plain `transfer_kv_all_layer_mla_lf_pf` C++ kernel, whose launcher asserts `dst_indices.is_cuda()`. CPU `host_indices` -> assert -> all TP scheduler ranks crash -> prefill dies.

## Why fix the cause instead of the #28473 `layer_first` fallback

#28473 works around the same crash by forcing `hicache_mem_layout = "layer_first"` on ROCm whenever `page_first` + `kernel` is requested. That keeps CI green, but it:

- **disables the JIT staged write-back path on AMD entirely** — ROCm permanently runs the older `layer_first` path and never benefits from the staged kernel that CUDA uses;
- **diverges ROCm from CUDA** at the config layer, so the two platforms exercise different layouts/kernels and have to be maintained separately;
- leaves the actual `page_first` + `kernel` ROCm path broken.

This PR fixes the underlying cause so ROCm keeps the *same* path as CUDA: platform parity, retained staged write-back bandwidth, vectorized non-temporal device transfers, and no second code path to maintain.

**Once this lands, #28473 should be reverted** — its ROCm `layer_first` fallback in `ServerArgs._resolve_layout_io_compatibility()` is no longer needed (and would otherwise keep short-circuiting ROCm away from the now-correct `page_first` + `kernel` JIT path).

## Modifications

- **`hicache.cuh`**: guard the NVIDIA-only PTX `ld/st.global.L1::no_allocate` helpers (`load_nc`/`store_nc`) behind `#ifndef USE_ROCM` and provide ROCm equivalents using non-temporal loads/stores, so the JIT HiCache module also builds with hipcc. The ROCm paths use a single `__builtin_nontemporal_{load,store}` over Clang `ext_vector_type(2/4)` (with `__builtin_bit_cast`) so the vectorized `global_{load,store}_dwordx{2,4}` non-temporal ops are deterministic instead of relying on the LoadStoreVectorizer.
- **`memory_pool_host.py`**: allow `can_use_jit` on HIP, not only CUDA, so ROCm uses the same staged write-back path as CUDA.
- **`cache_controller.py`**: only keep `host_indices` on CPU when the staged JIT kernel is actually available (`can_use_jit`); otherwise move them to the device. This makes the `kernel` io-backend correct on any backend where the JIT kernel is unavailable.
- **`staged_write_back.cuh` / `hicache.cuh` device matchers**: accept `kDLROCM` (device) / `kDLROCMHost` (pinned host) alongside `kDLCUDA`/`kDLCUDAHost`, mirroring the other JIT kernels (`clamp_position`, `kvcache`, `resolve_future_token_ids`).

## Reproduction

> **Note:** main currently contains #28473's ROCm `page_first` + `kernel` -> `layer_first` fallback in `ServerArgs._resolve_layout_io_compatibility()`. Revert it first; otherwise ROCm silently switches to `layer_first` and this path is never exercised.

2P1D ROCm deployment with `page_first` + `kernel` HiCache write-back (`--hicache-io-backend` defaults to `kernel`, the JIT staged write-back path this PR fixes). Core launch commands (TP=8, Kimi-K2.6-MXFP4):

### Prefill

```bash
SGLANG_USE_AITER=1 SGLANG_AITER_MLA_PERSIST=1 AITER_MXFP4_MOE_SF=1 \
python3 -m sglang.launch_server \
  --model-path /models/amd/Kimi-K2.6-MXFP4 \
  --served-model-name Kimi-K2.6-MXFP4 \
  --tool-call-parser kimi_k2 --reasoning-parser kimi_k2 \
  --chat-template /models/amd/Kimi-K2.6-MXFP4/chat_template.jinja \
  --tp-size 8 --page-size 64 \
  --context-length 262144 --kv-cache-dtype bf16 \
  --attention-backend aiter \
  --mem-fraction-static 0.8 --max-running-requests 128 \
  --chunked-prefill-size 16384 \
  --cuda-graph-bs $(seq 1 128) --cuda-graph-max-bs 128 \
  --trust-remote-code \
  --disaggregation-mode prefill \
  --disaggregation-transfer-backend mori \
  --disaggregation-bootstrap-port 8998 \
  --disaggregation-ib-device ionic_0,ionic_1,ionic_2,ionic_3,ionic_4,ionic_5,ionic_6,ionic_7 \
  --enable-hierarchical-cache --hicache-size 192 \
  --hicache-mem-layout page_first --hicache-write-policy write_through \
  --enable-metrics --enable-cache-report \
  --host 0.0.0.0 --port 30020
```

### Decode

```bash
SGLANG_USE_AITER=1 SGLANG_AITER_MLA_PERSIST=1 AITER_MXFP4_MOE_SF=1 \
python3 -m sglang.launch_server \
  --model-path /models/amd/Kimi-K2.6-MXFP4 \
  --served-model-name Kimi-K2.6-MXFP4 \
  --tool-call-parser kimi_k2 --reasoning-parser kimi_k2 \
  --chat-template /models/amd/Kimi-K2.6-MXFP4/chat_template.jinja \
  --tp-size 8 --page-size 64 \
  --context-length 262144 --kv-cache-dtype bf16 \
  --attention-backend aiter \
  --mem-fraction-static 0.85 --max-running-requests 128 \
  --chunked-prefill-size 8192 \
  --cuda-graph-bs $(seq 1 128) --cuda-graph-max-bs 128 \
  --num-continuous-decode-steps 4 \
  --trust-remote-code \
  --disaggregation-mode decode \
  --disaggregation-transfer-backend mori \
  --disaggregation-bootstrap-port 19100 \
  --disaggregation-ib-device ionic_0,ionic_1,ionic_2,ionic_3,ionic_4,ionic_5,ionic_6,ionic_7 \
  --enable-metrics --enable-cache-report \
  --host 0.0.0.0 --port 30030
```

### Router (native PD-disaggregation router)

```bash
python3 -m sglang_router.launch_router \
  --pd-disaggregation \
  --prefill http://<PREFILL_IP>:30020 8998 \
  --decode  http://<DECODE_IP>:30030 \
  --prefill-policy cache_aware --decode-policy round_robin \
  --disable-circuit-breaker \
  --host 0.0.0.0 --port 8100
```

Then send multi-turn / prefix-reusing traffic at the router (`:8100`). Before this PR, on ROCm the first prefill HiCache write-back crashes with `RuntimeError: Destination indices must be a CUDA tensor`, and the first prefix-cache hit crashes with `Tensor match failed ... device=rocm:N`. With this PR both paths run cleanly.

## Accuracy / functional tests

- JIT HiCache module compiles and loads with hipcc on gfx942 and gfx950 (ROCm 7.2).
- ISA check on gfx950: the ROCm `load_nc`/`store_nc` emit single `global_load_dwordx2/x4` and `global_store_dwordx2/x4` with the non-temporal (`nt`) flag.
- End-to-end on a 2P1D Kimi-K2.6-MXFP4 disaggregated deployment (TP=8, HiCache `page_first` + `kernel`, `write_through`) running the AgentX v0.3 agentic trace replay at concurrency 64: warmup + 900s profiling complete (328 requests, 0 errors) with no `Destination indices must be a CUDA tensor` and no `Tensor match failed ... device=rocm:N` crashes (both crashed pre-fix on the first write-back / first prefix-cache-hit load).

## Speed tests and profiling

To check that the staged write-back path is worth keeping on ROCm (rather than degrading to `layer_first` per #28473), I ran the equivalent of the #21631 write-back micro-benchmark on **AMD MI355X / gfx950, ROCm 7.2**, comparing the installed `sgl_kernel` LF->PF kernels against the JIT staged LF->PF kernels on the same host-destination write-back workload.

Setup mirrors #21631: `dtype=bf16`, `page_size=64`, `batch_pages=64`, `total_pages=128`, timing via `triton.testing.do_bench(warmup=5, rep=25)`. Each kernel is fed indices in the residency it requires (baseline `*_lf_pf`: device `dst_indices`; staged: pinned-host `dst_indices`); correctness is verified with `torch.testing.assert_close` for every row before timing. MHA bandwidth counts `K + V`; MLA counts a single buffer. `speedup = staged_jit / sgl_kernel_lf_pf`. ROCm has no `cudaMemcpyBatchAsync` equivalent, so `staged_write_back.cuh` uses the non-batch ROCm fallback (device relayout into staging + per-page async H2D copies).

<details>
<summary>Per-shape write-back microbenchmark (MHA / MLA)</summary>

### MHA (`batch_pages=64`)

| num_layers | element_dim | item_bytes | `sgl_kernel *_lf_pf` GiB/s | `jit *_staged_lf_pf` GiB/s | speedup |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 256 | 512 | 21.12 | 25.59 | 1.21x |
| 16 | 512 | 1024 | 15.43 | 34.15 | 2.21x |
| 16 | 1024 | 2048 | 21.82 | 39.42 | 1.81x |
| 16 | 2048 | 4096 | 24.15 | 42.01 | 1.74x |
| 24 | 256 | 512 | 15.73 | 30.63 | 1.95x |
| 24 | 512 | 1024 | 18.67 | 36.83 | 1.97x |
| 24 | 1024 | 2048 | 18.45 | 42.05 | 2.28x |
| 24 | 2048 | 4096 | 23.75 | 47.85 | 2.02x |
| 32 | 256 | 512 | 18.14 | 34.14 | 1.88x |
| 32 | 512 | 1024 | 20.76 | 41.45 | 2.00x |
| 32 | 1024 | 2048 | 24.36 | 45.08 | 1.85x |
| 32 | 2048 | 4096 | 23.24 | 48.85 | 2.10x |
| 40 | 256 | 512 | 17.68 | 36.90 | 2.09x |
| 40 | 512 | 1024 | 18.92 | 43.06 | 2.28x |
| 40 | 1024 | 2048 | 24.32 | 47.20 | 1.94x |
| 40 | 2048 | 4096 | 25.28 | 49.67 | 1.96x |
| 48 | 256 | 512 | 20.20 | 38.79 | 1.92x |
| 48 | 512 | 1024 | 22.60 | 44.16 | 1.95x |
| 48 | 1024 | 2048 | 20.72 | 47.99 | 2.32x |
| 48 | 2048 | 4096 | 23.36 | 49.98 | 2.14x |
| 56 | 256 | 512 | 19.73 | 40.25 | 2.04x |
| 56 | 512 | 1024 | 21.87 | 45.11 | 2.06x |
| 56 | 1024 | 2048 | 24.10 | 48.48 | 2.01x |
| 56 | 2048 | 4096 | 25.97 | 50.39 | 1.94x |
| 64 | 256 | 512 | 16.90 | 41.41 | 2.45x |
| 64 | 512 | 1024 | 22.47 | 45.55 | 2.03x |
| 64 | 1024 | 2048 | 17.16 | 48.87 | 2.85x |
| 64 | 2048 | 4096 | 23.00 | 50.46 | 2.19x |
| 72 | 256 | 512 | 16.50 | 42.33 | 2.56x |
| 72 | 512 | 1024 | 23.52 | 46.78 | 1.99x |
| 72 | 1024 | 2048 | 24.36 | 49.49 | 2.03x |
| 72 | 2048 | 4096 | 25.00 | 50.78 | 2.03x |
| 80 | 256 | 512 | 20.55 | 43.25 | 2.10x |
| 80 | 512 | 1024 | 17.14 | 47.45 | 2.77x |
| 80 | 1024 | 2048 | 22.13 | 49.73 | 2.25x |
| 80 | 2048 | 4096 | 23.53 | 48.88 | 2.08x |

### MLA (`batch_pages=64`)

| num_layers | element_dim | item_bytes | `sgl_kernel *_lf_pf` GiB/s | `jit *_staged_lf_pf` GiB/s | speedup |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 256 | 512 | 24.03 | 25.68 | 1.07x |
| 16 | 512 | 1024 | 26.65 | 34.33 | 1.29x |
| 16 | 1024 | 2048 | 26.32 | 41.56 | 1.58x |
| 16 | 2048 | 4096 | 27.37 | 45.65 | 1.67x |
| 24 | 256 | 512 | 24.34 | 30.86 | 1.27x |
| 24 | 512 | 1024 | 25.63 | 38.98 | 1.52x |
| 24 | 1024 | 2048 | 27.63 | 44.16 | 1.60x |
| 24 | 2048 | 4096 | 29.27 | 48.12 | 1.64x |
| 32 | 256 | 512 | 24.95 | 34.31 | 1.38x |
| 32 | 512 | 1024 | 25.86 | 41.59 | 1.61x |
| 32 | 1024 | 2048 | 27.12 | 45.47 | 1.68x |
| 32 | 2048 | 4096 | 30.48 | 48.90 | 1.60x |
| 40 | 256 | 512 | 24.60 | 37.03 | 1.51x |
| 40 | 512 | 1024 | 26.59 | 43.11 | 1.62x |
| 40 | 1024 | 2048 | 28.56 | 47.08 | 1.65x |
| 40 | 2048 | 4096 | 28.22 | 49.57 | 1.76x |
| 48 | 256 | 512 | 23.51 | 38.96 | 1.66x |
| 48 | 512 | 1024 | 25.18 | 44.20 | 1.76x |
| 48 | 1024 | 2048 | 29.75 | 47.89 | 1.61x |
| 48 | 2048 | 4096 | 28.92 | 49.90 | 1.73x |
| 56 | 256 | 512 | 24.16 | 40.42 | 1.67x |
| 56 | 512 | 1024 | 26.59 | 44.80 | 1.68x |
| 56 | 1024 | 2048 | 28.29 | 48.44 | 1.71x |
| 56 | 2048 | 4096 | 28.57 | 50.31 | 1.76x |
| 64 | 256 | 512 | 24.46 | 41.56 | 1.70x |
| 64 | 512 | 1024 | 25.73 | 45.25 | 1.76x |
| 64 | 1024 | 2048 | 29.66 | 48.71 | 1.64x |
| 64 | 2048 | 4096 | 29.34 | 50.45 | 1.72x |
| 72 | 256 | 512 | 24.15 | 42.29 | 1.75x |
| 72 | 512 | 1024 | 26.93 | 46.53 | 1.73x |
| 72 | 1024 | 2048 | 27.08 | 49.21 | 1.82x |
| 72 | 2048 | 4096 | 27.22 | 50.69 | 1.86x |
| 80 | 256 | 512 | 23.32 | 43.10 | 1.85x |
| 80 | 512 | 1024 | 27.90 | 47.00 | 1.68x |
| 80 | 1024 | 2048 | 27.94 | 49.71 | 1.78x |
| 80 | 2048 | 4096 | 29.98 | 46.94 | 1.57x |

</details>

**Takeaway:** on gfx950 the `*_lf_pf` kernels top out around 15-30 GiB/s, while the staged JIT path reaches ~25-50 GiB/s (close to the same peak CUDA achieves). That is a **1.21x-2.85x** speedup for MHA and **1.07x-1.86x** for MLA. The gap is larger than on CUDA (where #21631 reported roughly parity, ~0.87-1.25x, because the CUDA `*_lf_pf` baseline already runs near peak), so keeping ROCm on the staged `page_first` + `kernel` path is a clear win over the `layer_first` fallback.




















































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28997089073](https://github.com/sgl-project/sglang/actions/runs/28997089073)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28997088947](https://github.com/sgl-project/sglang/actions/runs/28997088947)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
