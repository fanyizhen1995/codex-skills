---
source_id: sglang-github-closed-issues-prs
title: '[diffusion] perf: add unified SP shard helpers and zero-copy tail-pad attention'
canonical_url: https://github.com/sgl-project/sglang/pull/30107
captured_at: '2026-07-05T02:14:10.240416+00:00'
content_hash: e0331ac08d013e6d694c8bb2f1e26c59c95c7fc69b3d9d7660cfbc67c7911e02
---
# [diffusion] perf: add unified SP shard helpers and zero-copy tail-pad attention

URL: https://github.com/sgl-project/sglang/pull/30107
State: closed
Labels: run-ci, diffusion
Closed at: 2026-07-04T15:57:40Z
Merged at: 2026-07-04T15:57:40Z

## Motivation

Every SP (ulysses) sequence must be padded to a multiple of the SP degree before the all-to-all. The repo had four independent pad implementations with three different semantics, and two of them were wrong:

- **flux / flux_2 / qwen_image**: pad + gap mask (correct), but three copy-pasted helpers with a byte-identical `gap_start/gap_end` formula, and the attention-side gap path repacks q/k/v with full-sequence `torch.cat`s per call.
- **mova (video+audio towers)**: zero-pads and calls `self.attn(q, k, v)` with **no mask** — pad tokens enter softmax as K/V and corrupt every real token. Measured corruption scales as ~pad/seq_len: **1.2e-2 MAE at 1 pad in 16 tokens**, 2.4e-5 at 1 in 1024 (never exact).
- **`base.shard_latents_for_sp`**: same unmasked-pad regime on non-divisible video time dims (rare fallback; the post-gather trim removes pad rows but cannot un-corrupt real ones).
- **ernie_image**: joint `[image, text]` stream is fully replicated, but attention still ran the ulysses all-to-all, duplicating the sequence.

## Change

**One invariant, one module** (`runtime/distributed/sp_shard.py`): padding always sits at the end of the LAST rank's local chunk, so the gathered sequence carries a single pad block at its **global tail**. Then attention skips it for free:

- **Zero-copy tail path in USPAttention**: the padded layout is handed to varlen FA directly, with each batch row split into `[valid | pad]` segments via a per-request cached `cu_seqlens` — contiguous reshapes only, no repacking cats, no index gather. Legacy `gap_start/gap_end` keys still work (aliased); the old repack path remains as fallback for non-tail spans.
- **Joint `[text, image]` models** relocate the last rank's text tail-pad behind the image at the attention cat (same copy volume as the existing cat), keeping the invariant. flux single blocks get a matching reordered RoPE cache, built once.
- **Dynamic replicate-vs-shard** (`plan_text_strategy`): measured result is that sharding wins at every text length (below), so the default is always-shard; ring>1 with a non-divisible text falls back to replicated (the masked path does not support ring), and `SGLANG_SP_TEXT_SHARD_MIN` remains as an env escape hatch.
- **Fixes**: mova threads the tail meta into both towers (bug fix); `base.shard_latents_for_sp` stops sharding non-divisible time dims until models consume the meta (correctness over the rare fallback); ernie skips SP in attention until its stream is actually sharded; `shard_rotary_emb_for_sp` folds into `shard_seq(pad_mode="repeat_last")`.

## Measurements (2×H100, sp=2 ulysses, bf16, FA backend)

**Attention-level pad-path comparison** (B=1, H=24, D=128; `unmask` shown as the corruption regime, not a valid option):

| case | new tail (ms) | old gap-cat (ms) | unmasked (ms) | divisible baseline (ms) |
|---|---|---|---|---|
| txt=77 img=2048/rank | **0.483** | 0.526 | 0.463 | 0.460 |
| txt=511 img=2048/rank | **0.562** | 0.614 | 0.547 | 0.551 |
| txt=77 img=8192/rank | **3.290** | 3.443 | 3.209 | 3.356 |
| txt=513 img=8192/rank | **3.718** | 3.745 | 3.466 | 3.501 |

Tail path ≈ divisible baseline (pad cost eliminated) and 4–8% faster than the old gap-cat. MAE vs an sp=1 dense reference: tail/gap ≈ 1e-5–3e-6 (backend noise, exact); unmasked is measurably worse and scales with pad fraction.

**Replicate-vs-shard sweep** (attention-level; the microbench favors replicate since it does not count the (sp-1)/sp per-block text QKV/MLP savings of sharding):

| txt | img/rank | replicate (ms) | shard (ms) |
|---|---|---|---|
| 64 | 2048 | 0.537 | **0.461** |
| 256 | 2048 | 0.645 | **0.546** |
| 1024 | 2048 | 0.712 | **0.612** |
| 2048 | 8192 | 4.135 | **4.076** |

Shard wins at every length once the pad cost is zero → default strategy is always-shard.

**End-to-end QwenImage DiT** (real transformer forward, 4 layers, txt=77 → tail-pad path, img=1024, identical random weights): rel MAE vs sp=1 is **bit-identical to main** (5.075e-3 on both; the residual is the ulysses FP-reorder on random bf16 weights — a divisible-text control at txt=80, main's production even-shard path, shows the same 5.03e-3, i.e. the pad path adds zero extra error). Forward latency is parity within run-to-run noise (ABAB ×3: branch 6.45/6.10/5.91 ms vs main 6.10/6.03/6.27 ms — the attention-level table above is the controlled perf evidence).

Unit tests: `test_sp_shard.py` (17 cases: shard math, tail meta vs the legacy gap formula, strategy gates, gather/trim).

## Notes

- Custom kernel considered and rejected: with the tail layout the data movement around FA is already ~zero, so a from-scratch attention kernel would trade FA's tuned performance for nothing.
- Follow-ups: hunyuan3d/hunyuanvideo use LocalAttention (no USP) — proper text-SP needs an attention-backend migration; ernie full sharding via `num_replicated_suffix` once its latents shard.











































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28710126185](https://github.com/sgl-project/sglang/actions/runs/28710126185)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28710126154](https://github.com/sgl-project/sglang/actions/runs/28710126154)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
