---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Reject DSpark speculators-convention checkpoints instead of silently
  degrading accept length'
canonical_url: https://github.com/sgl-project/sglang/pull/30852
captured_at: '2026-07-12T23:38:53.051636+00:00'
content_hash: 0ad9a57b474a36ff2f116d267c11476b2827c6dc04e8580a43caf51c32f9b486
---
# [Spec] Reject DSpark speculators-convention checkpoints instead of silently degrading accept length

URL: https://github.com/sgl-project/sglang/pull/30852
State: closed
Labels: 
Closed at: 2026-07-12T22:25:33Z
Merged at: 

## Motivation

`speculators` (github.com/vllm-project/speculators)-trained DSpark checkpoints use a different block-slot convention than the DeepSpec-trained ones. `run_markov_block` (`dspark.py`) was originally written against:

- **DeepSpec convention**: block slot k is trained to predict `anchor+k+1`. The anchor itself (slot 0) is also a real, trained prediction -- the draft block is exactly `gamma` slots wide, anchor-first.
- **speculators convention**: the anchor is a separate, untrained conditioning token, and slot j (j=1..gamma) predicts `anchor+j`. The draft block is `gamma + 1` slots wide, with slot 0 excluded from both sampling and verification.

Loading a speculators-trained checkpoint through the DeepSpec-width path reads every real slot one position early, degrading accept length to ~1 regardless of the underlying model's real speculative quality, with no error or crash -- it just
silently produces near-zero speedup.

Diagnosed and confirmed by @jessiewei7 in a comment on this PR (2026-07-09):
validated against `RedHatAI/GLM-5.2-speculator.dspark` and `mgoin/GLM-5.2-speculator.dspark-block16`, both showing the ~1.1 accept-length symptom (vs. ~4.05 for the same weights on vLLM).

### Update

The first version of this PR only detected the convention and rejected it with a clear error (the safer of the two fixes @jessiewei7 offered: "conditional shift on load, or a clear reject-with-error"). It's since been upgraded to the actual fix,
informed by two independent reference implementations that appeared after the safety net went in:

- **tanth47/sglang#2** (fork PR, stacked on this branch): restructures the draft block to `gamma+1`-wide, separating the anchor from the `gamma` real draft slots. Confirms the right *shape* of the fix -- but applies it unconditionally to every DSpark checkpoint, which is an unverified risk to the DeepSpec-trained checkpoints @jessiewei7's own diagnosis says currently work correctly (nothing in that PR's test evidence confirms they still do at the new width).
- **vllm-project/vllm#47093** (merged, validated against real checkpoints - `Qwen3-8B`, `GLM-5.2-DSpark`): the same `gamma+1`-wide restructuring, but gated by a `dspark_bonus_anchor` config flag. DeepSpec checkpoints keep exactly the
  behavior they had before the flag existed; only speculators-format checkpoints get the wider block. This resolves the regression risk in tanth47's version, and is the design this PR ports (mirroring `vllm/v1/worker/gpu/spec_decode/dspark/speculator.py`'s `sample_from_anchor` flag and `vllm/transformers_utils/configs/speculators/algos.py`).

## Modifications

- `dspark_config.py`: `_resolve_speculators_proposal_gamma` reads the checkpoint's own authoritative draft length from
  `speculators_config.proposal_methods[i].speculative_tokens`, instead of deriving it from `block_size - 1` and hoping the convention holds universally (ground-truthed against `RedHatAI/GLM-5.2-speculator.dspark`: `block_size=8`,
  `speculative_tokens=7` -- these are **not** the same number. `gamma` resolution priority: explicit `dspark_block_size` override > `speculators_config`'s stated value > plain `block_size` fallback (unchanged DeepSpec path).
- `models/dspark.py`: removed the earlier reject-`ValueError` guard. `DSparkDraftMixin`/`run_markov_block` no longer need to know about this at all -- they always receive exactly `gamma` real draft-hidden slots regardless of which convention produced them.
- `dspark_draft.py`: `DraftBlockProposer` and `DsparkDraftSampler` both gain a `bonus_anchor` flag (from `speculators_convention`) and a `draft_width` property (`gamma`, or `gamma + 1` when `bonus_anchor`). Only the draft forward pass's own block construction changes width -- `gamma` itself, and everything downstream that reads it (verify window sizing, KV commit, accept-length accounting), is completely unaffected. This is deliberately the surgical, low-blast-radius version, not a codebase-wide `gamma` redefinition.
- `dspark_worker_v2.py`: threads `speculators_convention` from `DSparkRuntimeConfig` into `self._bonus_anchor`, passed to both the eager (`DraftBlockProposer`) and CUDA-graph-folded (`DsparkDraftSampler`) construction sites. Confirmed DSpark has no separate CUDA-graph-capture runner class (unlike a P-EAGLE bug I found and fixed earlier this week in a different PR) - `_run_forward` is the single source of truth for both eager and graph-replay
  shapes, so there's no second capture-time site that could silently diverge.

## Accuracy Tests

Not hardware-validated end-to-end -- I don't have GPU access to the actual checkpoints this fixes. What's verified:

- The shape/config-resolution logic is unit-tested (8 new tests: gamma resolution from `speculators_config` vs `block_size` fallback vs explicit `default_proposal_method` selection; `draft_width` for both conventions on both `DraftBlockProposer` and `DsparkDraftSampler`), 16/16 passing total.
- Caught and fixed a real bug during implementation, not just theorized: slicing out the anchor's hidden state (`[:, 1:, :]`) produces a non-contiguous tensor; downstream `.view()` calls would have raised on it. Added `.contiguous()` after both slice sites.

The real accept-length improvement (@jessiewei7's reported 1.1 → ~4.05) needs confirmation against a real speculators-format DSpark checkpoint before this should be treated as fully proven -- happy to help validate, or for a maintainer with hardware access to confirm before merge.

## Speed Tests and Profiling

Not applicable to the config/shape-resolution changes here. No hot-path code is touched beyond the one-time `draft_width` branch already present in the block construction; real speedup validation is the accuracy-test gap above.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations) -- not applicable; internal config-resolution/draft-block-construction fix, no user-facing docs describe DSpark checkpoint-loading behavior to update.
- [ ] Provide accuracy and speed benchmark results -- see the caveat above; not hardware-validated end-to-end.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## AI Assistance Disclosure

Implementation assisted by Claude Sonnet 4.6 (Claude Code). I reviewed the diagnosis, the diff, the checkpoint-config verification, and the two reference implementations this ports from, and can explain any part of it.
