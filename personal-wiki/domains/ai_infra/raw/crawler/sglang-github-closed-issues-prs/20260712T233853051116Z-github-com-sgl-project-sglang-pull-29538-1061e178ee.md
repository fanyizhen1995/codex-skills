---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Add DSpark speculative decoding for DeepSeek-V4'
canonical_url: https://github.com/sgl-project/sglang/pull/29538
captured_at: '2026-07-12T23:38:53.051116+00:00'
content_hash: 1061e178eeb715c456461781fc78b306fd149b47277ad06a567278b1894ead5a
---
# [Spec] Add DSpark speculative decoding for DeepSeek-V4

URL: https://github.com/sgl-project/sglang/pull/29538
State: closed
Labels: documentation, deepseek, speculative-decoding
Closed at: 2026-07-12T22:48:42Z
Merged at: 

Closes #29488

## Motivation

DeepSeek-V4 ships a native block speculative drafter (DSpark): a 3-stage MTP stack with a Markov refinement head and a confidence head that drafts a whole block per step off the target's fused hidden states (reference: [deepseek-ai/DeepSpec](https://github.com/deepseek-ai/DeepSpec)). This PR adds the full serving integration for DSpark in SGLang so DeepSeek-V4 users get lossless speculative speedups out of the box, at temperature 0 and above.

## Modifications

### Core integration

- `speculative/dspark_worker_v2.py`: DSpark worker (block draft, Markov refine, confidence cap, block verify), draft `embed_tokens` and `lm_head` tied to the target's loaded weights.
- `models/deepseek_v4_dspark.py`: `DeepseekV4ForCausalLMDSpark` (3-stage MTP model, target-layer capture, heads read from config so Flash and Pro both work).
- `speculative/dspark_info.py`: `DSparkVerifyInput` and `DSparkDraftInputV2`.
- Draft CUDA-graph capture of the block forward (draft returns `LogitsProcessorOutput`, spec-info gated on `is_draft_worker`).
- Registration and dispatch: `spec_info.py`, `spec_registry.py`, `speculative_hook.py`, `spec_utils.py`.
- Config: `--speculative-algorithm DSPARK`, `--speculative-dspark-block-size`, `--speculative-dspark-confidence-threshold`.

### Temperature > 0 support

- `temperature > 0` is verified with the shared target-only speculative rejection sampling primitive (the same one DFLASH uses) instead of falling back to greedy, honoring per-request `temperature`, `top_k`, and `top_p` at verify time. On builds without the required `sgl_kernel` ops, sampled requests fall back to greedy verification with a one-time server-log warning.
- TP consistency: the sampled-verify results (accept length and bonus token) are broadcast from TP rank 0 after the sampling kernel, so every rank commits the same block under `temperature > 0` (mirrors EAGLE's post-kernel broadcast).
- Per-request validation: requests DSpark cannot verify are rejected up front rather than silently degraded (`return_logprob`, grammar-constrained decoding via JSON schema / regex / EBNF / structural tags, and `return_hidden_states`).

### Performance optimizations

- **Collective-free Markov refine.** The refine loop previously issued 11 NCCL collectives per decode step (6 full-vocab all-gathers plus 5 embedding all-reduces). The Markov embedding is now replicated per rank (about 66 MB), the refined logits stay vocab-sharded, and the global argmax is resolved with one tiny packed int64 MAX all-reduce per block position. The packing reproduces `torch.argmax`'s first-index tie-break exactly (unit-tested against `torch.argmax` over 1M+ rows with forced ties), so drafts are bit-identical and greedy losslessness is untouched by construction.
- **Markov refine captured in the draft CUDA graph.** A `dspark_draft_sampler` hook (mirroring the DFLASH one, but tensor-parallel capable since the captured MAX all-reduce replays like the model's own TP collectives) folds the whole refine loop into the draft decode graph, removing roughly 30 eager kernel launches and a Python loop from every decode step. Eager fallback is kept for uncaptured batches.
- **Fixed-shape draft-KV materialization.** Draft KV is written for all block positions unconditionally (matching the target verify's own unconditional KV write), removing the last data-dependent host syncs from the decode step.
- **Dead-code elimination at the default confidence threshold.** At `confidence_threshold = 0` (the default, and the fastest configuration in our measurements) the confidence head provably cannot truncate, so its computation is skipped entirely.
- **Pooled commit buffers.** Per-step commit tensors use growable two-slot ping-pong device buffers instead of per-step allocations.
- Removed the `verify_done` device-event barrier from the draft-input path; the scheduler's generic WAR fallback already covers the DSpark target-verify path (same cleanup upstream applied to DFLASH in #29556).
- KV bookkeeping tightening: the draft block forward uses the committed sequence lengths as its host bound (the attention backend adds the block itself), and `prepare_for_decode` reads the authoritative `req.kv_allocated_len` instead of a carried CPU copy.

Measured impact of the optimization set (same-pod A/B on 4xB200, tp4/ep4): +31% output throughput at c=1, +23% at c=8, +9% at c=32 on random 256/512; single-stream median TPOT 2.91 ms to 2.05 ms; accept length and accuracy unchanged.

### Docs and tests

- Docs under `docs_new`: DSpark section plus a "Sampling" subsection covering greedy losslessness, target-only sampled verify, the confidence-threshold guarantee, the kernel fallback, and the rejected request features.
- Unit tests `test/registered/unit/spec/test_dspark.py`: registration/arg handling, batch merge/filter, request validation, greedy and sampled block-verify commit math (accept length, confidence truncation, bonus selection, out-token assembly), confident-prefix semantics, and shard-argmax pack exactness (forced ties, signed zeros, vocab padding, tp 1/4/8).

## Accuracy Tests

DeepSeek-V4-Flash-DSpark (284B, FP4 MoE) on 8x B200, `--tp 8 --ep-size 8`, 200 examples each, same session as the speed tests below. FP4 MoE is not bit-exact run to run, so an accuracy match against no spec is the correctness signal.

| Eval | Temperature | No spec | DSpark |
|---|---|---|---|
| GSM8K | 0 | 0.985 | 0.980 |
| MMLU | 0 | 0.895 | 0.895 |
| GSM8K | 0.6 | 0.980 | 0.980 |
| GSM8K | 1.0 | 0.970 | 0.990 |

DSpark matches no spec at every temperature. Sampled verification demonstrably takes effect (identical prompts at temperature 1.0 produce distinct completions) and ran a sustained multi-request load through the captured graphs at TP 8 without desync, exercising the rank-0 broadcast path.

## Speed Tests and Profiling

DeepSeek-V4-Flash-DSpark (284B, FP4 MoE) on 8x B200, `--tp 8 --ep-size 8`, draft CUDA graph and captured Markov refine on, greedy unless noted. Speedup is DSpark over no spec, same session.

At a glance:

| Workload | Speedup (c=1 to c=32) | DSpark best TPOT |
|---|---|---|
| Random 256/512 | 2.08x / 1.68x / 1.51x / 1.24x / 1.28x | 2.52 ms (c=1) |
| ShareGPT | 1.84x / 1.29x / 1.29x / 1.28x / 1.35x | 2.80 ms (c=1) |
| Single stream 512/256 | 1.97x | 1.93 ms |
| Single stream 1024/1024 | 2.31x | 1.88 ms |
| Random c=8, temperature 1.0 | within noise of greedy | 6.52 ms |

Commands:

```
# server (no spec)
python -m sglang.launch_server --model-path <DeepSeek-V4-Flash-DSpark> --tp 8 --ep-size 8 \
  --moe-runner-backend flashinfer_mxfp4 --mem-fraction-static 0.85 --cuda-graph-max-bs 32 \
  --max-running-requests 32 --context-length 4096 --trust-remote-code
# server (DSpark) adds:
  --speculative-moe-runner-backend flashinfer_mxfp4 --speculative-algorithm DSPARK \
  --speculative-eagle-topk 1 --speculative-num-steps 1

python -m sglang.test.run_eval --eval-name gsm8k --num-examples 200 --port 30000 --temperature <T>
python -m sglang.test.run_eval --eval-name mmlu  --num-examples 200 --port 30000
python -m sglang.bench_serving --backend sglang --dataset-name random \
  --random-input-len 256 --random-output-len 512 --num-prompts <N> --max-concurrency <C>
python -m sglang.bench_serving --backend sglang --dataset-name sharegpt \
  --num-prompts <N> --max-concurrency <C>
```

### Random (input 256, output 512)

| Metric | Config | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| Output throughput (tok/s) | No spec | 148.3 | 428.5 | 663.1 | 910.6 | 1216.0 |
| Output throughput (tok/s) | DSpark | 308.6 | 720.7 | 1000.9 | 1128.2 | 1554.7 |
| Total throughput (tok/s) | No spec | 211.9 | 635.5 | 979.0 | 1380.6 | 1815.2 |
| Total throughput (tok/s) | DSpark | 440.9 | 1069.0 | 1477.7 | 1710.4 | 2320.8 |
| Request throughput (req/s) | No spec | 0.53 | 1.57 | 2.48 | 3.61 | 4.55 |
| Request throughput (req/s) | DSpark | 1.11 | 2.65 | 3.74 | 4.47 | 5.82 |
| Accept length | DSpark | 3.72 | 3.69 | 3.71 | 3.74 | 3.73 |
| **Speedup** | - | **2.08x** | **1.68x** | **1.51x** | **1.24x** | **1.28x** |

| Metric | Config | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| Median TPOT (ms) | No spec | 5.98 | 8.30 | 11.03 | 16.52 | 25.65 |
| Median TPOT (ms) | DSpark | 2.52 | 4.57 | 6.25 | 11.28 | 17.59 |
| Mean TPOT (ms) | No spec | 5.97 | 8.32 | 11.26 | 16.40 | 24.40 |
| Mean TPOT (ms) | DSpark | 2.59 | 4.92 | 7.24 | 12.45 | 18.33 |
| Mean TTFT (ms) | No spec | 219.6 | 194.1 | 215.8 | 219.9 | 219.6 |
| Mean TTFT (ms) | DSpark | 176.8 | 190.2 | 207.8 | 445.7 | 509.3 |
| Median E2E (ms) | No spec | 1879.4 | 2809.8 | 2944.5 | 4065.5 | 6438.6 |
| Median E2E (ms) | DSpark | 798.1 | 1433.8 | 1986.0 | 3138.3 | 4881.3 |

(DSpark mean TTFT at c=16/32 reflects the initial prefill burst of the infinite-request-rate benchmark; median E2E is uniformly better.)

### ShareGPT

| Metric | Config | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| Output throughput (tok/s) | No spec | 152.6 | 372.0 | 614.8 | 861.4 | 983.0 |
| Output throughput (tok/s) | DSpark | 280.0 | 479.6 | 794.7 | 1100.2 | 1327.1 |
| Total throughput (tok/s) | No spec | 315.6 | 1127.5 | 1541.2 | 2082.1 | 2485.7 |
| Total throughput (tok/s) | DSpark | 579.2 | 1453.7 | 1992.3 | 2659.3 | 3355.8 |
| Request throughput (req/s) | No spec | 0.47 | 1.59 | 2.56 | 3.81 | 4.70 |
| Request throughput (req/s) | DSpark | 0.86 | 2.04 | 3.32 | 4.86 | 6.35 |
| Accept length | DSpark | 3.72 | 3.71 | 3.68 | 3.65 | 3.58 |
| **Speedup** | - | **1.84x** | **1.29x** | **1.29x** | **1.28x** | **1.35x** |

| Metric | Config | c=1 | c=4 | c=8 | c=16 | c=32 |
|---|---|---|---|---|---|---|
| Median TPOT (ms) | No spec | 5.98 | 8.35 | 11.23 | 16.86 | 29.25 |
| Median TPOT (ms) | DSpark | 2.80 | 5.17 | 8.16 | 13.38 | 23.80 |
| Mean TPOT (ms) | No spec | 6.00 | 9.67 | 11.93 | 15.93 | 30.10 |
| Mean TPOT (ms) | DSpark | 2.97 | 8.53 | 9.96 | 14.26 | 24.05 |
| Mean TTFT (ms) | No spec | 190.2 | 214.8 | 207.2 | 210.2 | 259.1 |
| Mean TTFT (ms) | DSpark | 319.7 | 325.9 | 242.8 | 216.8 | 249.8 |
| Median E2E (ms) | No spec | 2204.4 | 1624.3 | 2376.0 | 2837.2 | 4397.6 |
| Median E2E (ms) | DSpark | 1045.3 | 1339.8 | 1641.6 | 2168.7 | 3564.8 |

### Single stream, by input/output shape

| Input / output | No spec (tok/s) | DSpark (tok/s) | Speedup | DSpark median TPOT (ms) | Accept len |
|---|---|---|---|---|---|
| 512 / 256 | 139.5 | 274.9 | 1.97x | 1.93 | 3.58 |
| 1024 / 1024 | 153.9 | 354.8 | **2.31x** | 1.88 | 3.58 |

### Sampled decoding throughput

Random 256/512, c=8, `temperature 1.0`: 1027.7 tok/s output, median TPOT 6.52 ms, accept length 3.59. Sampled verification runs within noise of greedy at the same concurrency (1027.7 vs 1000.9 tok/s).

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28680768310](https://github.com/sgl-project/sglang/actions/runs/28680768310)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28680768225](https://github.com/sgl-project/sglang/actions/runs/28680768225)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
