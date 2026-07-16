---
source_id: sglang-github-closed-issues-prs
title: '[PP] Fix proxy tensor buffer sizing and refresh for speculative verify'
canonical_url: https://github.com/sgl-project/sglang/pull/30774
captured_at: '2026-07-15T23:40:28.370752+00:00'
content_hash: d009a9776fc984103d8fc366c2c8030921377ae2c24e3565e9bb70ffdea2da7b
---
# [PP] Fix proxy tensor buffer sizing and refresh for speculative verify

URL: https://github.com/sgl-project/sglang/pull/30774
State: closed
Labels: 
Closed at: 2026-07-15T10:08:59Z
Merged at: 

## Motivation

While enabling pipeline parallelism together with speculative decoding (EAGLE/MTP) on GLM-5.2 (see companion RFC PR), we found four latent bugs in the PP proxy-tensor plumbing. They only manifest when a PP model runs multi-token forwards through the decode CUDA-graph path (`TARGET_VERIFY`, num_tokens_per_bs > 1); plain PP decode is bit-identical before/after this change, because there num_tokens_per_bs == 1 and every fix degenerates to the current behavior.

Although upstream currently rejects PP+spec at argument-parsing time, these are correctness bugs in shared infrastructure and make the invariants consistent (the same dict already sizes `topk_indices` by tokens).

## Modifications

1. **`_allocate_decode_buffers` / `DecodeInputBuffers.create`** — `hidden_states` / `residual` proxy buffers were sized `(max_bs, hidden)` while every other token-axis buffer (`input_ids`, `positions`, and `topk_indices` in the same dict) uses `max_num_token = max_bs * num_tokens_per_bs`. Under verify the `[:num_tokens]` slice silently returns fewer rows; warmup crashes in rotary with `shape '[384, -1, 64]' is invalid for input of size 131072` (bs=128 x 3 draft tokens vs 128 rows).

2. **`DecodeCudaGraphRunner.load_batch`** — the pre-planned early-return path (metadata already initialized by `eagle_prepare_for_verify`) copies `input_ids`/`positions` but never refreshes the `pp_proxy_tensors` input buffers, so the last PP stage replays verify graphs against **stale hidden states** from the previous round.

3. **`DecodeCudaGraphRunner.execute`** — the `PPProxyTensors` output was sliced `[:self.bs]` (request rows) instead of `[:self.bs * self.num_tokens_per_bs]` (token rows). With 3 verify tokens per request only the first `bs` rows reach the next stage: request 0's rows happen to be fresh, every later request in the microbatch reads stale hidden states. Single-request runs look healthy, which makes this one particularly deceptive.

4. **`cuda_graph_buffer_registry`** — the pp-proxy slot source indexed `ppx.tensors[key]` unconditionally; an entry can legitimately be absent (e.g. `topk_indices` when a DSA-family model runs a dense attention backend). Use `.get()` so the documented "source_fn returns None → skip copy" contract applies.

## Validation

Validated on 8x RTX PRO 6000 (SM120), GLM-5.2-NVFP4, TP4xPP2 + EAGLE(2 steps / topk 1 / 3 draft tokens) behind an env-flag build:
- greedy decode identical to non-spec output; GSM8K 20q accuracy 0.900 (matches TP8 baseline)
- concurrent (4-16 requests, staggered arrivals) outputs correct — previously half of each microbatch degenerated to repeated tokens (fix 3)
- without fix 2, single-stream verify output was corrupted after the first token

Happy to split this into separate PRs if preferred.

🤖 Generated with [Claude Code](https://claude.com/claude-code)







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29088148860](https://github.com/sgl-project/sglang/actions/runs/29088148860)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29088148583](https://github.com/sgl-project/sglang/actions/runs/29088148583)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
