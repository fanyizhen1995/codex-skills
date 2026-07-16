---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Add LFM2 / LFM2-MoE DSpark draft-model support'
canonical_url: https://github.com/sgl-project/sglang/pull/30776
captured_at: '2026-07-12T23:38:53.051906+00:00'
content_hash: 91bd7c236868697e5729b811add88cee544edd210635c4ef48a903352737dc0e
---
# [Spec] Add LFM2 / LFM2-MoE DSpark draft-model support

URL: https://github.com/sgl-project/sglang/pull/30776
State: closed
Labels: 
Closed at: 2026-07-12T22:25:32Z
Merged at: 

### What

Adds DSpark speculative-decoding support for the LFM2 hybrid (ShortConv + attention) family: both the dense **LFM2** and MoE **LFM2-MoE** targets. Stacked on top of this PR (#30261); base is `sglang-dspark`.

Two commits:

1. **Interleaved RoPE in the fused-KV kernel** - the fused RMSNorm+RoPE materialization only handled neox rotation. Adds an `IS_NEOX` constexpr selecting the pairing (neox: `(i, i+rotary/2)`; interleaved/GPT-J: `(2i, 2i+1)`); no change for existing neox drafts. LFM2 draft exports rotate interleaved and need this.
2. **LFM2 / LFM2-MoE target support** - the draft is a DSpark checkpoint (Qwen3-style GQA backbone, markov + confidence heads) exported with interleaved RoPE. It registers as its own `Lfm2DSparkDraftModel` arch (a thin `DSparkDraftModel` subclass, mirroring `Qwen3DSparkModel`) so the LFM2 draft can gain LFM2-specific layers - e.g. ShortConv/conv1d - later without touching the shared classes. Interleaved RoPE and the confidence head come from the checkpoint config; the kernel change handles the rotation. Only the target side needs code beyond that: aux-hidden capture + ShortConv block verify/rollback in `lfm2.py`/`lfm2_moe.py`, hybrid-state commit after verify in the DSpark worker (mirrors the DFlash worker so decoding stays lossless), routing the draft KV injector through the fused-KV path, and marking the LFM2 archs eligible for the `extra_buffer` mamba radix strategy that spec-v2 rollback needs.

Net: 7 files, +422/-23, no changes to existing DSpark behavior.

Base LFM2-MoE serving parity (the attention-backend / radix-cache override tables for `Lfm2MoeForCausalLM`) is independent of DSpark and is split into its own PR: #30780. Pair with it for the 8B target's serving defaults.

### Speedup

1xH100 80GB, bs=1, temperature 0, block size 7, accept length / speedup vs the same server minus spec flags:

| dataset | LFM2.5-1.2B + 5L | LFM2.5-8B-A1B + 3L |
|---|---|---|
| math500 (chat math) | 4.82 / **2.10x** | 5.42 / **2.21x** |
| aime (competition math) | 4.36 / 1.95x | 6.20 / **2.42x** |
| humaneval (code) | 4.41 / 1.93x | - |
| mbpp (code) | 4.45 / 1.95x | 4.80 / 1.96x |
| gsm8k (grade-school math) | 3.73 / 1.49x | 3.51 / 1.24x |
| mtbench (multi-turn chat) | 2.35 / 1.05x | 5.87 / **2.32x** |

Floor is short chat on the small dense target (~1.05x); ceiling is long reasoning on the MoE (2.3-2.4x, accept near the block-7 limit). Accuracy at parity with baseline on every scoreable bench.

Note: interleaved RoPE (commit 1) is not optional for these drafts. Serving them neox collapses accept length to ~1.9 vs ~5.1 interleaved.

### Status / testing

Validated in serving on 1xH100 across the benches above (dense + MoE, draft depths 2L/3L/5L): 1.2B math500 accept 5.09, 8B math500 accept 5.94, unchanged whether the draft registers as `Lfm2DSparkDraftModel` or the generic `Qwen3DSparkModel`. The MoE ShortConv decode uses the same CUDA conv1d_update kernel as dense (an earlier triton swap was removed after confirming it gave identical accept, 5.936 both ways).

Public draft checkpoints for testing:
- dense: https://huggingface.co/tugot17/LFM2.5-1.2B-Instruct-DSpark-5L (target `LiquidAI/LFM2.5-1.2B-Instruct`)
- MoE: https://huggingface.co/tugot17/LFM2.5-8B-A1B-DSpark-3L (target `LiquidAI/LFM2.5-8B-A1B`)

```bash
python -m sglang.launch_server \
  --model-path LiquidAI/LFM2.5-1.2B-Instruct \
  --speculative-algorithm DSPARK \
  --speculative-draft-model-path tugot17/LFM2.5-1.2B-Instruct-DSpark-5L \
  --speculative-draft-attention-backend flashinfer
```

Happy to add a CI test against these.

Opening this to gauge whether you'd want LFM2 support folded into #30261 before it merges, or taken as a fast-follow after. Either works for us.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29102692229](https://github.com/sgl-project/sglang/actions/runs/29102692229)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29102692022](https://github.com/sgl-project/sglang/actions/runs/29102692022)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
