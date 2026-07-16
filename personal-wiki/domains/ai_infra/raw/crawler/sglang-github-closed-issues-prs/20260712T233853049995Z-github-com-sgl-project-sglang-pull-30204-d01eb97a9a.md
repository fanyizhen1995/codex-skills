---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Add Qwen3-family DSpark draft model (extends #29538) + fix DeepSeek-V4
  import crash for non-V4 DSpark targets'
canonical_url: https://github.com/sgl-project/sglang/pull/30204
captured_at: '2026-07-12T23:38:53.049995+00:00'
content_hash: d01eb97a9a6164e2da947ea230b0aada767e9d99b4f037096d066db8ea7769df
---
# [Spec] Add Qwen3-family DSpark draft model (extends #29538) + fix DeepSeek-V4 import crash for non-V4 DSpark targets

URL: https://github.com/sgl-project/sglang/pull/30204
State: closed
Labels: documentation, deepseek, speculative-decoding
Closed at: 2026-07-12T22:52:00Z
Merged at: 

## Motivation

Adds Qwen3-family support to DSpark speculative decoding by extending the architecture landed in #29538 (DeepSeek-V4-only). One new model class, `Qwen3DSparkModel` (`python/sglang/srt/models/qwen3_dspark.py`), serves both released Qwen3 DSpark checkpoints — `deepseek-ai/dspark_qwen3_4b_block7` (Markov head + confidence head) and `deepseek-ai/dflash_qwen3_4b_block7` (neither) — through the existing `DSparkWorkerV2`, gated purely by checkpoint config. Also included: a fix for a pre-existing bug in #29538 that crashes any non-DeepSeek-V4 target the instant `--speculative-algorithm DSPARK` is selected, a one-line test-fixture fix that turns #29538's own 33-test suite green, and a block-size config-field fallback for the Qwen3 checkpoint family's naming convention.

Validated end-to-end on a single RTX A6000 (48GB, SM86/Ampere, bf16, `--attention-backend triton`): GSM8K-200 5-shot greedy accuracy holds at parity with the non-speculative baseline (0.875-0.885 vs 0.880), with a measured ~1.9-2x single-stream decode speedup and 3.9-4.8 accepted tokens/round.

## How to read this diff

Branch `dspark-qwen3` starts with a squash-import of #29538 @ `f6320807` (commit `b5ea3053`, full implementation credit to @adityakamat24 — see "Relationship to #29538" below) because #29538 hasn't merged yet and we needed something to build against locally. **We are not proposing that squashed commit as our own contribution, and we are not asking for it to be re-reviewed here.** Once #29538 merges, the actual delta we'd want reviewed is just the commits on top of it:

| Commit | What |
|---|---|
| `91adffc7` | Test-fixture fix: `_make_server_args()` in `test_dspark.py` was missing `disable_overlap_schedule`, failing 3/33 tests in #29538's own suite as submitted |
| `f751af66` | `models/qwen3_dspark.py` (new) + the `ModelRunner` / `speculative_hook.py` / `dspark_worker_v2.py` adjustments described below |
| `f082480e` | CPU-only weight-mapping + component-parity script vs. the DeepSpec reference implementation |
| `a1cfcfab` | `qwen3.py`: `set_dspark_layers_to_capture` aux-hidden-state capture hook |
| `2dd29f7b` | Lint/format pass (isort/black) on the three files above that fail `pre-commit run --all-files`; whitespace/import-order only, no semantic change |
| `d49c85c2` | Registered GPU server-integration test, `test/registered/spec/dspark/test_dspark.py` (see Test plan) |
| `51e63059` | `docs_new` update: corrects the "DeepSeek-V4 only" / "no separate draft model" language and adds a Qwen3-family subsection |
| `1e43baab` | Audit fixes: greedy-determinism test compares two warm (same-kernel-path) requests instead of cold-vs-warm, removing a latent bf16 tie-flip CI flake; docs corrected — the `dflash_qwen3_4b_block7` sibling is not currently servable under DFLASH (flat-vs-nested worker-shape conflict, tracked as an open question) |

If maintainers would rather review the import-gate fix and the fixture fix as small standalone patches directly against #29538 (they're useful independent of whether Qwen3 support lands at all), we're happy to split them out — see "Open questions" below.

## Relationship to #29538 and #29488

- **#29538** ("[Spec] Add DSpark speculative decoding for DeepSeek-V4", @adityakamat24): this PR *extends*, and does not compete with, #29538. #29538 introduces the real architectural machinery this depends on — the `DSPARK` `SpeculativeAlgorithm` enum member, `DSparkWorkerV2(BaseSpecWorker)`, the CLI surface (`--speculative-dspark-block-size`, `--speculative-dspark-confidence-threshold`), and the DeepSeek-V4 draft model. All of that is @adityakamat24's design and implementation; we did not reimplement or duplicate any of it. #29538 should be reviewed and merged on its own merits for DeepSeek-V4 regardless of this PR's outcome. (For orientation: #29705 and #29938 also build on #29538, adding PD/dp-attention support and temperature-sampling respectively — both orthogonal to this PR's Qwen3 addition, not touched here.)
- **#29488**: the DSpark tracking issue. A validation summary (what we measured on single-GPU Ampere, cross-referencing this PR) is prepared and can follow as a comment there.

## Modifications

### What this adds

1. **`python/sglang/srt/models/qwen3_dspark.py`** (new): `Qwen3DSparkModel`, the Qwen3-family analog of `DeepseekV4ForCausalLMDSpark`, served through the same `DSparkWorkerV2`.
2. **`model_runner.py`**: gates the `deepseek_v4_dspark` import (and its `dspark_num_layers`/`dspark_target_layer_ids` field reads) on the target actually being DeepSeek-V4 family, instead of firing unconditionally whenever `is_dspark()`. This is the one change here that's useful independent of Qwen3 support — see "Bug fix" below.
3. **`qwen3.py`**: `set_dspark_layers_to_capture`, the aux-hidden-state capture hook DSpark needs on a Qwen3 target (delegates to the existing DFLASH hook — see design notes).
4. **`speculative_hook.py`**: `_handle_dspark`'s block-size auto-inference now also checks the bare `block_size` config field (the Qwen3 checkpoint family's spelling), not just DeepSeek-V4's `dspark_block_size`.
5. **`dspark_worker_v2.py`**: target-weight tying (`embed_tokens`/`lm_head`) is now conditional on a new `draft_model.owns_vocab_weights` flag, so a draft that ships its own vocab weights (Qwen3 DSpark, `tie_word_embeddings=false`) isn't force-tied to the target's.
6. **Test-fixture fix** (`test_dspark.py`): `disable_overlap_schedule` added to `_make_server_args()`, fixing 3 pre-existing failures in #29538's own CPU test suite (unrelated to Qwen3 — a gap in the original PR's fixture).
7. **CPU parity script** (`scripts/playground/dspark_qwen3_weight_parity.py`, new): validates weight mapping and small-component math against the DeepSpec reference implementation, no GPU required.
8. **Registered GPU integration test** (`test/registered/spec/dspark/test_dspark.py`, new): mirrors `test/registered/spec/dflash/test_dflash.py`'s structure — see Test plan.
9. **Docs** (`docs_new/docs/advanced_features/speculative_decoding.mdx`): corrects the DeepSeek-V4-only language and adds a Qwen3-family subsection (checkpoints, launch example, measured numbers).

### Design notes

**One class, two checkpoints, config-gated.** `deepseek-ai/dspark_qwen3_4b_block7` and `deepseek-ai/dflash_qwen3_4b_block7` both ship `"architectures": ["Qwen3DSparkModel"]`; they differ only in `markov_rank` (256 vs. 0) and `enable_confidence_head` (true vs. false). `Qwen3DSparkModel` builds `markov_head`/`confidence_head` iff those config values are set, so one class and one `EntryClass` registration serves both checkpoints with zero config rewriting. This also matters concretely: `EntryClass = [Qwen3DSparkModel]` matches the checkpoint's actual `architectures` string exactly, which is where #29917 runs into trouble (its detection keys on a `Draft`-suffixed class name that no released checkpoint declares).

**Subclasses DFlash, not DeepSeek-V4.** A DSpark draft block for a Qwen3-family target is architecturally DFlash's parallel, non-causal, context-KV-fed block drafter (plain GQA + per-head q/k RMSNorm + RoPE + `RadixAttention` over a paged KV cache pre-seeded with the projected target-context feature), not DeepSeek-V4's MLA/hybrid-compression-specific block. `Qwen3DSparkAttention`/`Qwen3DSparkDecoderLayer` subclass `dflash.py`'s attention/decoder-layer classes directly, adding only a `kv_from_hidden` method (the plain-MHA/GQA analog of `DeepseekV4Attention.kv_from_hidden`, since `DSparkWorkerV2` calls it directly). The Markov head is a small self-contained copy of `deepseek_v4_dspark.py`'s `DSparkMarkovHead` rather than an import, deliberately — see the bug-fix note below for why importing anything from `deepseek_v4.py`'s module chain is unsafe for a non-V4 deployment.

**Capture-hook convention, and why it isn't a copy-paste of V4's.** `model_runner.py`'s aux-hidden-state capture requires the target model to implement `set_dspark_layers_to_capture()`; `qwen3.py` only had the DFLASH-named analog. We delegate to the existing `set_dflash_layers_to_capture()` rather than duplicating it, because on this architecture (`Qwen3Model` -> `Qwen2Model.forward`) capture is mechanically identical for DFLASH and DSpark: same flag, same `layers_to_capture` list, same **+1 offset** (the forward loop checks `layers_to_capture` *before* running each layer, so capturing HF-style layer `k`'s output requires listing `k+1`). `deepseek_v4.py`'s `set_dspark_layers_to_capture` has *no* offset — correct there only because that file's forward loop checks the list *after* running each layer. Copying V4's version verbatim into `qwen3.py` would have silently captured the wrong layers while still "running" (no crash, just silently wrong hidden states). Verified directly: `target_layer_ids=[1,9,17,25,33]` (the checkpoint's own value) maps to `model.layers_to_capture=[2,10,18,26,34]`, matching the DFLASH hook's existing, already-correct convention.

**`owns_vocab_weights`.** `DeepseekV4ForCausalLMDSpark`'s draft doesn't ship its own `embed_tokens`/`lm_head` — `DSparkWorkerV2.__init__` ties them directly to the target's live weights. Qwen3 DSpark checkpoints are the opposite: `tie_word_embeddings=false`, and both `embed_tokens.weight` and `lm_head.weight` are present and trained in the checkpoint (confirmed against the real safetensors header). We added `owns_vocab_weights: bool` on the draft model class (`False` on the V4 class, unchanged behavior; `True` on `Qwen3DSparkModel`) and made the worker's tying step conditional on it, so neither checkpoint family silently ends up with the wrong vocab weights.

**Bug fix — unconditional DeepSeek-V4 import crashes non-V4 targets.** Choosing `--speculative-algorithm DSPARK` for *any* target unconditionally imports `deepseek_v4_dspark` -> `deepseek_v4` -> `deepseek_v2`'s DSA indexer -> `deep_gemm` at module level, inside `ModelRunner.__init__` (`model_runner.py:528` on #29538's tip). On any host without DeepSeek-V4's exact `deep_gemm`/CUDA build, this crashes — reproduced live on our box:

```
$ python -m sglang.launch_server --model-path Qwen/Qwen3-4B \
    --speculative-algorithm DSPARK \
    --speculative-draft-model-path deepseek-ai/dspark_qwen3_4b_block7 \
    --speculative-dspark-block-size 7 --attention-backend triton --port 30000
...
  File ".../model_executor/model_runner.py", line 528, in __init__
    from sglang.srt.models.deepseek_v4_dspark import get_dspark_num_layers
  File ".../models/deepseek_v4_dspark.py", line 20, in <module>
    from sglang.srt.models.deepseek_v4 import DeepseekV4DecoderLayer, DeepseekV4ForCausalLM
  File ".../models/deepseek_v4.py", line 22, in <module>
    import sglang.srt.models.deepseek_v2 as deepseek_v2
  File ".../models/deepseek_v2.py", line 61, in <module>
    from sglang.srt.layers.attention.dsa.dsa_indexer import Indexer
  File ".../layers/attention/dsa/dsa_indexer.py", line 74, in <module>
    import deep_gemm
  ...
RuntimeError: Check failed: (lib_handle_ != nullptr) is false: Failed to load dynamic
shared library .../deep_gemm/_C.so libcudart.so.13: cannot open shared object file
```

Two-layered root cause: (1) `deep_gemm`'s compiled extension wants `libcudart.so.13`, which a CUDA-12.x-pinned box doesn't have; (2) `dsa_indexer.py`'s own `import deep_gemm` is wrapped in `except ImportError`, which doesn't catch the `RuntimeError` a broken native `.so` actually raises (pre-existing, not part of #29538's diff). No flag works around it — the import fires unconditionally as soon as `spec_algorithm.is_dspark()` is true, with no gate on the target's actual architecture. Our fix threads the existing `is_dspark()` check through an additional check on target arch, so a non-DeepSeek-V4 target reads the generic HF config fields (`num_hidden_layers`, `target_layer_ids`) directly instead of importing V4's module chain at all.

**A note on `getattr` usage.** The diff reads several optional fields off third-party HuggingFace `PretrainedConfig`-style objects with `getattr(config, "field", default)` (`block_size`, `markov_rank`, `mask_token_id`, etc.). This resembles the pattern the repo's `no-getattr-defensive.md` house rule warns against, but it's a different situation: those fields genuinely vary by checkpoint family (DeepSeek-V4 vs. Qwen3-family config schemas differ), so there's no single "always present" field to access directly the way the rule's own example (an sglang-internal `server_args.revision`) has. The one remaining `getattr(param, "weight_loader", default_weight_loader)` call is the standard repo-wide `load_weights` idiom for `torch.nn.Parameter`, not something specific to this PR.

## Accuracy Tests

GSM8K 5-shot/200q/greedy holds at parity with the non-speculative baseline across every configuration we measured: 0.875-0.885 (DSpark, confidence threshold off) vs. 0.880 (target-only), and 0.875-0.880 across confidence thresholds 0.3-0.8 — all within the ≈0.023 binomial-noise band at n=200. See [Measurements](#measurements) below for the full breakdown, including the confidence-threshold sweep and the bench-trio comparison against an existing DFlash checkpoint.

## Speed Tests and Profiling

Single-stream decode latency improves ~1.95x (13.15 -> 6.76 ms/tok) with 3.9-4.8 accepted tokens per verify round during GSM8K; batched GSM8K throughput and the confidence-truncation mechanism's measured cost/benefit are covered in [Measurements](#measurements) below.

## Measurements

All single-GPU, RTX A6000 48GB SM86, bf16, `--attention-backend triton`, GSM8K 5-shot/200q/greedy unless noted (`python -m sglang.test.few_shot_gsm8k`, all defaults). Session-to-session batched throughput varies roughly ±10% on this box; single-request latency and accept-length are the more stable signals.

**Baseline vs. DSpark (confidence threshold off, the shipped default):**

| Config | GSM8K acc. (n=200) | Batched GSM8K throughput | Single-stream latency | Accept length |
|---|---|---|---|---|
| Target-only (no spec) | 0.880 | ~1865 tok/s | 13.15 ms/tok | n/a |
| DSpark block7, τ=0 | 0.875-0.885 across runs (binomial noise at n=200 ≈ 0.023) | 1347-1543 tok/s (session variance ±10%) | 6.76 ms/tok (**~1.95x**) | 3.94-4.84 during GSM8K |

**Confidence-threshold (τ) sweep — accuracy** (separate measurement session from the row above):

| τ | GSM8K acc. |
|---|---|
| 0.3 | 0.880 |
| 0.5 | 0.880 |
| 0.8 | 0.875 |

All within the ≈0.023 noise band of the 0.880 baseline — truncation is lossless as designed, at every τ we tried.

**Confidence-truncation mechanism — fixed 128-token single-stream probe, same session:**

| τ | Accept length | Verify rounds |
|---|---|---|
| 0 (off) | 2.844 | 45 |
| 0.3 | 2.510 | 51 |
| 0.5 | 2.510 | 51 |
| 0.8 | 2.510 | 51 |

Accuracy is flat across τ — but the probe shows the gate is doing real work, and not for free: it fires and saturates by τ=0.3 (the confidence distribution is bimodal), and costs ~13% *more* verify rounds at every τ>0 than τ off, while committing *fewer* tokens per round. That's because `dspark_worker_v2.py` applies the confidence prefix as `min(kernel_accept_len, confident_prefix)` **after** the full-block target-verify forward already ran (confidence computed at `dspark_worker_v2.py:770-771`, applied via `torch.minimum` at line 806 in the sampling-verify branch and line 833 in the greedy branch) — the full `block_size`-length candidate tensor is always shipped to the target, so truncation can only shrink what gets *committed*, never what gets *verified*. a design sketch of moving truncation before the verify forward is written up and available on request.

**Bench trio vs. an existing DFLASH checkpoint** (z-lab's DFlash block16, same target, same box):

| | DSpark block7 | DFlash block16 |
|---|---|---|
| GSM8K acc. | 0.875 | 0.870 |
| Single-stream latency | 6.758 ms/tok | 8.899 ms/tok |
| Batch-8 throughput | 887 tok/s | 632 tok/s |
| Accept **rate** during GSM8K | 0.49-0.61 | 0.19-0.21 |

(Accept *rate*, not accept length, is the fair comparison here — block sizes differ, 7 vs. 16.)

## Test plan

**Automated, CPU-only, no GPU needed:**
```
pytest test/registered/unit/spec/test_dspark.py -q
```
33/33 passing on this branch (30/33 on #29538's own tip before the fixture fix in `91adffc7` — see that commit for the one-line diagnosis). Also CPU-only:
```
python scripts/playground/dspark_qwen3_weight_parity.py
```
maps all 64 real checkpoint tensors to a destination parameter (0 unmapped) and checks the Markov-bias, previous-token-embedding, `fc`-then-`hidden_norm` combine, and confidence-head math against a pure-Torch reproduction of the DeepSpec reference — all four come back `max_abs_diff = 0.000e+00` against the real trained weights.

**Automated, GPU required (registered CI test, `1-gpu-small` runner):**
```
pytest test/registered/spec/dspark/test_dspark.py -v -s
```
8/8 passing, run locally on a single RTX A6000 (`--attention-backend triton`): GSM8K score 0.880 (n=200), `avg_spec_accept_length` 4.0035, plus early-stop / EOS-handling / greedy-determinism / matched-stop checks (`CustomTestCase` + `MatchedStopMixin` + `GSM8KMixin`, mirroring `test/registered/spec/dflash/test_dflash.py`). `gsm8k_accuracy_thres=0.84` and `gsm8k_accept_length_thres=3.0` sit below our measured floor (0.875-0.885 / 3.94-4.84) with margin, mirroring `test_dflash.py`'s own below-measured-floor convention (0.75 acc. / 2.8 accept length against a documented "roughly 3.2-3.6"). `MatchedStopMixin.test_finish_stop_eos` is overridden with a Qwen3-correct prompt/token-id version — the inherited one hardcodes Llama-3 special tokens from `test_dflash.py`'s Llama-3.1 target. Registered CUDA-only for now; we have no AMD hardware to validate against, unlike `test_dflash.py`'s dual CUDA+AMD registration.

A methodology note, since it affects how any future correctness test should be written: we initially compared DSpark's greedy output against target-only token-for-token and got 3/5 exact matches on a small prompt set. Both divergences turned out to be positions where the target's own top-2 logprobs are tied at *exactly* 0.000000 (bf16), with the next-nearest logit 1.6-5.9 away — i.e., genuine ties, not an accept/reject logic bug. Target-only's own multi-token verify-extend kernel path and its single-token decode path are free to (and do) break an exact tie differently; separately, target-only output by itself is not reproducible warm-RadixCache-vs-cold on this box (2/5 self-match, pre-existing and DSpark-unrelated). That's why the registered test above gates DSpark correctness on GSM8K accuracy + accept-length rather than exact-match, matching `test_dflash.py`'s own convention — exactness isn't a reachable bar across kernel paths even for target-only alone.

## Explicitly NOT covered by this PR

- **Pre-verify confidence truncation** (moving truncation before the target-verify forward so it actually saves compute) — design sketch written up (available on request), not implemented.
- **Real load-aware scheduling** (the paper's Algorithm 1, a hardware-aware prefix scheduler against a profiled throughput table) — not implemented anywhere we could find, including the DeepSpec reference, vLLM, or TRT-LLM.
- **Large-batch validation** — everything above was measured up to batch 8 on a single GPU; we have no data at production batch sizes.
- **Hopper/FP8** — developed and tested entirely on Ampere/bf16; no coverage of FP8 paths or SM90+-specific kernels.
- **CUDA-graph coverage for variable-length verify** — today's graphs (both the target's verify graph and the draft's own decode graph) assume a fixed per-round token count; a pre-verify-truncation future would need to address this.
- **The EAGLE3-Qwen3 gap** — unrelated to DSpark directly, but hit while gathering the bench trio: neither `AngelSlim/Qwen3-4B_eagle3` (`Eagle3LlamaForCausalLM`) nor `deepseek-ai/eagle3_qwen3_4b_ttt7` (`Qwen3Eagle3Model`) resolves against any registered model class — no `qwen3_eagle3.py` exists. Flagged separately as a small side-item.

## Open questions for maintainers

1. Would you rather the `ModelRunner` import-gate fix and the test-fixture fix land as small standalone commits directly against #29538 (useful regardless of Qwen3 support), separate from the Qwen3 model addition? We bundled them on one branch purely for our own validation convenience.
2. Given #29538 and #29917 are two independent, architecturally-divergent implementations of Qwen3/DeepSeek-V4 DSpark support (dedicated `DSparkWorkerV2` vs. aliasing into `DFlashWorkerV2`), is there an intended convergence point, or is the plan to let both mature and pick one later? This PR assumes #29538's `DSparkWorkerV2` design; if the intended direction turns out to be closer to #29917's DFLASH-alias approach, most of this would need to be re-targeted.
3. ~~Is a GPU server-integration test (mirroring `test/registered/spec/dflash/test_dflash.py`'s `GSM8KMixin`-based `TestDFlashServerBase`) wanted for DSpark?~~ **Resolved**: added `test/registered/spec/dspark/test_dspark.py` (see Test plan). Open sub-question: worth also adding a stage-a `test_basic_sanity_dspark.py` companion (mirroring `test_basic_sanity_dflash.py`) and/or the page-size / chunked-prefill / no-cuda-graph subclass variants `test_dflash.py` has? We scoped this draft to the single base-class GSM8K/matched-stop suite.
4. `dflash_qwen3_4b_block7` (the `markov_rank=0` sibling checkpoint) is architecturally servable by this same class but is meant to run under plain DFLASH, not DSpark — is routing it through `DFlashWorkerV2` instead (same checkpoint, different worker) in scope for this PR, or a separate follow-up?

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28766391378](https://github.com/sgl-project/sglang/actions/runs/28766391378)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28766391279](https://github.com/sgl-project/sglang/actions/runs/28766391279)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
