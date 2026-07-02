---
source_id: sglang-github-closed-issues-prs
title: 'docs(cookbook): document GB300 trtllm allreduce fusion backend tuning for
  GLM-5.2'
canonical_url: https://github.com/sgl-project/sglang/pull/28946
captured_at: '2026-07-01T02:12:08.959092+00:00'
content_hash: 9d90ab2124c8f344fd5ac91a55ee1961b481055342d4527e6cd494888499766f
---
# docs(cookbook): document GB300 trtllm allreduce fusion backend tuning for GLM-5.2

URL: https://github.com/sgl-project/sglang/pull/28946
State: closed
Labels: documentation, run-ci
Closed at: 2026-06-30T10:45:59Z
Merged at: 

## What

Adds a Configuration Tips note to the GLM-5.2 cookbook (`docs_new/cookbook/autoregressive/GLM/GLM-5.2.mdx`) documenting `--flashinfer-allreduce-fusion-backend trtllm` as a deployment-tuning flag for **GLM-5.2-FP8 on 4×GB300 (SM10X, TP4)**, benchmarked against the default backend (`auto`→`mnnvl`).

**Docs-only change. No runtime code modified.**

## Why

On 4×GB300 the FlashInfer allreduce fusion backend defaults to `mnnvl` (`auto`→`mnnvl` on SM10X). Switching to the `trtllm` backend variant improved on the default across the two gap metrics for GLM-5.2:

| scenario | metric | default (`auto`/mnnvl) | `trtllm` | delta |
|---|---|---|---|---|
| chat (1K-in/1K-out) | throughput tok/s | 1257.2 | 1358.9 | +8.1% |
| chat | mean TTFT ms | 6172.8 | 5415.5 | −12.3% |
| chat | mean TPOT ms | 32.60 | 31.26 | −4.1% |
| summarization (8K-in/1K-out) | throughput tok/s | 1013.2 | 1022.1 | +0.9% |
| summarization | mean TTFT ms | 7402.3 | 8008.2 | +8.2% (regression) |
| summarization | mean TPOT ms | 91.57 | 52.63 | −42.5% |

Benchmarked on a clean non-speculative TP4 baseline (`--tp 4 --mem-fraction-static 0.88 --context-length 32768`, no EAGLE/DP/DeepEP), 80 prompts, `--flush-cache` + varied seed.

## Correctness gate

`sgl-eval run gsm8k` (full 1319 examples, `--max-tokens 8192`, thinking on) on both backends:

| metric | `trtllm` | default | notes |
|---|---|---|---|
| score (symbolic_correct/1319) | 1255/1319 = 95.15% | 1255/1319 = 95.15% | same aggregate |
| stop-rate | 97.19% | 97.19% | same |
| truncation rate | 2.81% (37) | 2.81% (37) | same |
| stopped-only accuracy | 1255/1282 = 97.89% | 1255/1282 = 97.89% | same |
| runaway / errors | 0 / 0 | 0 / 0 | — |

**Aggregate-safe, no correctness regression.** The lower-than-baseline overall score (95.15% vs cookbook 98.2%) is a `max_tokens=8192` cap artifact (37 truncated examples scored wrong) affecting both backends identically — not a fusion effect.

**Important:** the two backends are **not** token-equivalent. Per-problem `num_generated_tokens` differs on 1281/1319 examples, generation text on 168, predicted answer on 71, finish_reason on 38, and individual correctness on 36. The fusion backends shift allreduce numerics (different token streams); the result is only that the shifts cancel at the aggregate level → identical score/stop/truncation.

## Scope & limitations

- **GLM-5.2-FP8 / 4×GB300 only.** This is benchmarked on this environment; it is **not** a generic default change. The same `trtllm` swap **regressed** on a cross-check with Qwen3-30B-A3B (bf16) on 8×H200 (there `mnnvl` was better — mnnvl > trtllm > fusion_off on chat), so this flag should not be carried over to other model/hardware combinations without re-benchmarking.
- The GB300 cookbook recipes (low-latency/balanced/high-throughput) use EAGLE/DP/DeepEP, under which this flag has **not** been re-verified. The note makes this explicit: treat `trtllm` on top of a speculative recipe as unverified.
- The summarization-TTFT regression (+8.2%) is the one metric that did not improve with `trtllm`; documented as such.
- No runtime code is changed — the default backend is still `auto`. This PR only documents the tuning option for users who want to opt in on GLM-5.2/4×GB300.

## Checklist

- [x] Docs-only change (one `.mdx` file, +14 lines)
- [x] No runtime code modified
- [x] Before/after benchmark table included
- [x] Correctness gate (sgl-eval GSM8K full) included
- [x] Scope/limitations explicit (GLM-5.2/GB300 only, not generic, not verified under spec)
- [x] Honest about non-token-equivalence and the summ-TTFT regression









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #27962174096](https://github.com/sgl-project/sglang/actions/runs/27962174096)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27962172606](https://github.com/sgl-project/sglang/actions/runs/27962172606)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
