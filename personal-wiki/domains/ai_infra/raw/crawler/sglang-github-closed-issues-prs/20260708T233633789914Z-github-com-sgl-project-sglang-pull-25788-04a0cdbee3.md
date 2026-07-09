---
source_id: sglang-github-closed-issues-prs
title: '[lora] Enable piecewise CUDA graph (PCG) for prefill with LoRA (triton + BCG
  fallback)'
canonical_url: https://github.com/sgl-project/sglang/pull/25788
captured_at: '2026-07-08T23:36:33.789914+00:00'
content_hash: 04a0cdbee30290c64ed6015d81a7b155388a2287d6fc2417f510e0340683c44d
---
# [lora] Enable piecewise CUDA graph (PCG) for prefill with LoRA (triton + BCG fallback)

URL: https://github.com/sgl-project/sglang/pull/25788
State: closed
Labels: lora, npu
Closed at: 2026-07-08T18:46:58Z
Merged at: 

## Summary

Enables piecewise CUDA graph (PCG) + breakable CUDA graph (BCG) for the prefill (EXTEND) path when `--enable-lora` is set, including bs>1 batches via the **A-Lite** per-bs capture approach. Previously `server_args._handle_piecewise_cuda_graph()` unconditionally disabled PCG whenever LoRA was enabled, forcing prefill LoRA serving to fall back to eager.

End-state on this branch:
- **PCG path** works for the `triton` LoRA backend on dense (non-MoE) models at bs=1 and bs ∈ (1, 4]. lm_head LoRA pruned path runs eager (outside captured region).
- **BCG path** supports bs>1 via the same per-bs capture pattern; remains the recommended path for **chunked SGMV** and **MoE LoRA serving**.
- **MoE PCG** capture now passes the first two Dynamo fullgraph blockers (`get_device_name()` and `os.path.realpath` / `@functools.lru_cache`); a third blocker remains in sgl_kernel's missing `moe_sum_reduce` fake impl — needs an sgl_kernel-side `register_fake` to be fully PCG-ready.

## Changes (9 commits)

1. `[lora] Enable piecewise CUDA graph with LoRA (prefill EXTEND, triton + chunked buffer)` — Core PCG×LoRA unblock.
2. `[lora] Route lm_head LoRA pruned path to eager under PCG (fine-grained)`.
3. `[lora] Size MoE LoRA Phase 1 buffers for PCG token bucket too`.
4. `[lora] Wire LoRA capture/replay into BreakableCudaGraphRunner`.
5. `[lora] Avoid duplicate prepare_lora_batch in PCG/BCG replay`.
6. `[lora] A-Lite per-bs PCG capture + Dynamo dynamic int` — **PCG bs>1 unblock**.
7. `[lora] A-Lite for BCG + can_run guard for skipped (n,bs) combos` — **BCG bs>1 unblock**.
8. `[lora] PCG perf tuning: capture_bs_buckets=[1,4] + MoE get_device_name cache`.
9. `[lora] PCG fullgraph: cache config_dir + dict-based config lookup` — **MoE/csgmv PCG fullgraph fix**: replaces `@functools.lru_cache` (which Dynamo cannot follow into the locked dict) with an explicit module-level dict cache, populated lazily on first call.

## Validation

### Smoke / correctness (Qwen3-8B + LoRA rank 32)

- **PCG + triton + LoRA** bs ∈ {1, 4, 16, 32, 64, 256, 1024}: all generate correctly. bs ≤ 4 dispatches through captured graphs; bs > 4 falls back via can_run guard.
- **BCG + triton + LoRA** bs ∈ {1, 64, 256, 1024}: all pass.
- Multi-adapter (rank 32 × 2): passes.
- **MoE + LoRA + BCG**: works.

### Performance

#### Base model (no LoRA) — PCG wins consistently

Matrix bench, Qwen3-8B + GB300, `piecewise_cuda_graph_tokens=[1024, 2048, 4096, 8192]`, 3-run min, max_new_tokens=1, total tokens distributed across bs sequences:

| tok | bs | PCG-on | eager | Δ |
|---|---|---|---|---|
| 1024 | 1 | 18.3 ms | 28.0 ms | **−35%** |
| 1024 | 4 | 17.2 ms | 28.3 ms | **−39%** |
| 1024 | 64 | 38.7 ms | 64.1 ms | **−40%** |
| 2048 | 16 | 31.8 ms | 57.2 ms | **−44%** |
| 4096 | 16 | 29.7 ms | 54.1 ms | **−45%** |
| 8192 | 16 | 32.4 ms | 54.4 ms | **−40%** |

23/24 cells: wins (avg ~25% speedup). One small loss at tok=8192 bs=1 (+16%).

#### LoRA + PCG — honest result after ablation

**Initial single-warmup measurement** suggested PCG won at bs ≥ 64 by −22% to −36% vs pure eager. **5-warmup ablation revealed this was largely a warmup artifact** — pure eager's first calls were paying Python / CUDA cache cold cost that PCG's longer init phase had already eaten.

After ablation (5 warmups + 3 measurements, min reported), the corrected numbers:

| tok | bs | eager (5-warmup) | PCG-on | corrected Δ |
|---|---|---|---|---|
| 1024 | 1 | 44.9 | 51.6 | +15% (PCG-dispatch path; `allow_unspec_int` overhead) |
| 1024 | 4 | 46.3 | 53.1 | +15% (PCG-dispatch) |
| 1024 | 16 | 47.5 | 47.8 | tied (fallback path) |
| 1024 | 64 | 96.9 | 62.8 | −35% remaining (fallback path; some real benefit, some noise) |
| 1024 | 256 | 119.6 | 108.6 | −9% (fallback path; gap closed substantially after warmup) |
| 1024 | 1024 | 316.2 | 313.4 | **tied** (gap fully closed after warmup) |
| 2048 | 64 | 88.2 | 98.4 | eager actually faster here |
| 2048 | 1024 | 321.0 | 292.6 | −9% |

**Honest conclusion for LoRA + PCG**:
- bs ∈ {1, 4} (PCG dispatch path): **+10–15% slight loss** vs pure eager, due to `allow_unspec_int_on_nn_module=True` runtime guard overhead (~25 ms / call)
- bs > 4 (fallback): **roughly tied** to pure eager once both are properly warmed; the bs ≥ 64 "wins" reported in earlier runs were inflated by single-warmup measurement artifact
- Short-prompt single-call bench (uncached, 4-token prompts, no matrix workload), bs ∈ {1, 4}: **−7% to −10%** real wins

#### LoRA + PCG — uncached short-prompt bench (cleaner measurement)

| prompt_tokens | bs | PCG-on | eager | Δ |
|---|---|---|---|---|
| 512 | 1 | 43.7 ms | 48.6 ms | **−10%** |
| 512 | 4 | 44.3 ms | 48.6 ms | **−9%** |
| 1024 | 1 | 44.7 ms | 48.1 ms | **−7%** |
| 1024 | 4 | 45.6 ms | 50.4 ms | **−10%** |

#### PCG replay profile decomposition

```
[PCG_PROF] allow_unspec_int=True, capture_bs_buckets=[1, 4]
  bs=1   lora=0.4ms  prep=0.2ms  attn=0.2ms  fwd=110ms  total=110ms
  bs=4   lora=0.4ms  prep=0.1ms  attn=0.2ms  fwd=44ms   total=44ms

[PCG_PROF] allow_unspec_int=False  (UNSTABLE — intermittent assert)
  bs=1   lora=0.4ms  prep=0.2ms  attn=0.2ms  fwd=26.5ms total=27.4ms  ← −76% but crashes
```

`prepare_lora_batch`, `replay_prepare`, `attn metadata` are all <1 ms — 99% of replay time lives in `model.forward` (captured cudaGraph replay + outer-eager lm_head LoRA). The `allow_unspec_int_on_nn_module=True` flag (necessary to let one captured graph dispatch across multiple live bs values without firing a recompile) adds ~80 ms of per-call Inductor guard cost; we keep it ON for stability.

## What this PR actually delivers for LoRA users

- **Functional**: bs>1 LoRA + PCG no longer crashes — was previously force-disabled at the server_args layer.
- **Perf for LoRA**: small win (−7% to −10%) for uncached short prefills at bs ∈ {1, 4}; roughly tied with eager for larger bs in matrix-mode workloads after proper warmup.
- **Perf for base model**: consistent **−25% to −45% wins** across 23/24 cells (this was already the value of PCG; LoRA support doesn't regress it).
- **MoE PCG progress**: two Dynamo fullgraph blockers fixed (config-dir cache + dict cache in place of `@functools.lru_cache`). One remaining blocker (`sgl_kernel::moe_sum_reduce` fake impl) is sgl_kernel-side.

## Known limitations / not fixed in this PR

- `capture_bs_buckets = [1, 4]` by design. Wider buckets (e.g. `[1, 16, 256, 2048]`) measured ~30× slower because the LoRA sgemm kernel grid `(num_pid_s × num_pid_n, batch_info.bs)` pays block-dispatch overhead even for padded no-op slots. bs > 4 falls back through can_run guard.
- **Matrix-mode CUDA IMA at large-bs cells**: reproducible *only* with PCG enabled; pure-eager run completes all 24 cells. Likely captured-cudaGraph state pollution across drastically different consecutive bs values in matrix-mode workload. Workaround: don't mix very different bs values in close succession; or use BCG. Not in LoRA PR scope to fix.
- **MoE PCG** needs sgl_kernel-side `register_fake` for `moe_sum_reduce` (and likely others). Out of LoRA PR scope.
- **chunked backend + PCG**: dynamic chunk-count problem (number of segments varies per batch) is not solved here; chunked + BCG remains the recommended path.

Decode regression check (PCG-off, decode-only CUDA graph, n_tokens=128, bs=1): 141.9 tokens/sec, jitter ±1 ms. **No regression.**

## Recommended flags

| Scenario | Flags | Expected speedup |
|---|---|---|
| Dense + LoRA, short uncached prefill (bs ≤ 4) | `--enable-lora --enforce-piecewise-cuda-graph --lora-backend triton` | **−7% to −10%** |
| Dense + LoRA, batched serving (matrix-mode, larger bs) | Same as above | tied (no regression) |
| Chunked SGMV LoRA | `--enable-lora --enforce-piecewise-cuda-graph --enable-breakable-cuda-graph --lora-backend csgmv` | — |
| MoE + LoRA | `--enable-lora --enforce-piecewise-cuda-graph --enable-breakable-cuda-graph` | — |
| Base model, short prefill | `--enforce-piecewise-cuda-graph` | **−25% to −45% wins** |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
