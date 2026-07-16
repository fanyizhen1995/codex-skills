---
source_id: sglang-github-closed-issues-prs
title: '[DeepSeek V2] Reorder dual-stream MoE to main-first to avoid CUDA graph stream
  explosion'
canonical_url: https://github.com/sgl-project/sglang/pull/30460
captured_at: '2026-07-10T23:37:20.336462+00:00'
content_hash: fa0195b24e7d70baf0a5da9f2aec19a8a5aaf5a5634e577d31a470fcc6328c81
---
# [DeepSeek V2] Reorder dual-stream MoE to main-first to avoid CUDA graph stream explosion

URL: https://github.com/sgl-project/sglang/pull/30460
State: closed
Labels: deepseek, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-09T23:59:40Z
Merged at: 2026-07-09T23:59:40Z

## Motivation

Profiling **Kimi-K2.5-NVFP4** (TP8, EAGLE3 spec decode, `flashinfer_trtllm` MoE) showed the target-verify decode CUDA graph fanning out across **~61 streams** — one per model layer — instead of the intended 2 (main + alt).

Root cause is in `DeepseekV2MoE.forward_normal_dual_stream`: the shared-expert branch was enqueued on the alt stream **before** the main (routed) branch. During CUDA graph capture this alt-first, per-layer ordering makes `cudaGraphInstantiate` allocate a fresh side stream for every layer — the same "stream explosion" mechanism fixed for the DSA indexer in #30025.

Alt-first was originally required by #29463: the routed `deep_gemm` pre-permute calls `dispose_tensor(hidden_states)`, which `set_()`s the storage to empty. A shared-expert kernel reading `hidden_states` afterward would capture `data_ptr() == 0` into the decode graph and replay from null.

## Change

Issue the **main (routed) branch first**, then the shared expert on the alt stream. To keep `deep_gemm` correct, take a storage alias `shared_in = hidden_states[:]` **before** the routed call runs `dispose_tensor`, so the shared expert reads live storage. This satisfies all three constraints simultaneously:

- **No stream explosion** — main issued before the alt block, so capture reuses a single alt stream.
- **PDL overlap preserved** — routed is the last main-stream kernel and still fuses with the residual add.
- **`deep_gemm` `dispose_tensor` hazard avoided** — shared reads `shared_in`, a reference taken pre-dispose.

The alias keeps the buffer alive past `dispose_tensor`, but decode/verify `hidden_states` is tiny (`bs * num_draft_tokens` rows vs thousands in prefill), so the lost early free is negligible.

Since `shared_output` is now computed after the deferred-finalize decision, that decision is gated on a precomputed `has_shared_output` flag instead of `shared_output is not None`.

## Results

Re-profiled with the same TP8 Kimi-K2.5 config + client. Per full `TARGET_VERIFY` forward, TP-0:

| | before (alt-first) | after (main-first + alias) |
|---|---|---|
| streams per verify forward | 61-62 | 2-3 |
| stream-count histogram | `{2:78, 3:4462, 4:140, 61:63, 62:15}` | `{2:124, 3:32}` |
| total distinct kernel streams in trace | ~61 | 3 |

Perf/correctness unchanged (within noise), confirming the alias preserves shared-expert input:

| metric | before | after |
|---|---|---|
| Accept length | 2.42 | 2.40 |
| Mean TPOT | 3.33 ms | 3.30 ms |
| Benchmark duration | 42.10 s | 41.53 s |

## Test plan

- [x] Profile Kimi-K2.5-NVFP4 TP8 (EAGLE3) — verify stream count collapses 61 -> 2-3, accept length unchanged.
- [ ] `deep_gemm` EP gsm8k (`test_moe_ep_extra.py`) to validate the alias against the #29463 path.

Refs #29463, #30025.

Made with [Cursor](https://cursor.com)

## Profile

Before
<img width="867" height="415" alt="Screenshot 2026-07-07 at 7 49 57 PM" src="https://github.com/user-attachments/assets/c5e1c20a-1abf-4376-ad64-c074dcf538c2" />

After

<img width="620" height="415" alt="Screenshot 2026-07-07 at 7 49 44 PM" src="https://github.com/user-attachments/assets/163b0238-95e8-4f63-881c-104254730281" />























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29049292993](https://github.com/sgl-project/sglang/actions/runs/29049292993)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29049292883](https://github.com/sgl-project/sglang/actions/runs/29049292883)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
