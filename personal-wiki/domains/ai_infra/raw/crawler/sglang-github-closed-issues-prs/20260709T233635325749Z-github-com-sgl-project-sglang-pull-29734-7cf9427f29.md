---
source_id: sglang-github-closed-issues-prs
title: '[GDN] Auto-select FlashInfer GDN prefill on validated SM100 configs'
canonical_url: https://github.com/sgl-project/sglang/pull/29734
captured_at: '2026-07-09T23:36:35.325749+00:00'
content_hash: 7cf9427f29f506e63a5fb117febc24b65c27e4dd72e9c7ddfce4238b8ca530af
---
# [GDN] Auto-select FlashInfer GDN prefill on validated SM100 configs

URL: https://github.com/sgl-project/sglang/pull/29734
State: closed
Labels: documentation, speculative-decoding, run-ci, bypass-fastfail, run-ci-extra
Closed at: 2026-07-09T16:26:01Z
Merged at: 2026-07-09T16:26:01Z

## Motivation

SGLang ships the FlashInfer GDN prefill kernel, but GDN prefill still defaults to Triton when no per-phase backend is specified.

On B200, FlashInfer 0.6.12 provides repeatable prefill gains when static chunking is limited to 8192 tokens. This PR enables it by default only for that validated domain, including the `no_buffer` radix-cache strategy. Follow-up #29735 adds checkpoint support for the two extra-buffer strategies.

## Modifications

- Auto-select FlashInfer GDN prefill when the override is unset, the device is SM100 with CUDA 13+, the GDN key/value head dimensions are 128, recurrent state is BF16, and static chunk size is in `[1, 8192]`.
- Support radix disabled and `no_buffer`; keep Triton for extra-buffer strategies in this PR.
- Keep Triton for dynamic chunking and page-major KV layout.
- Preserve explicit backend selections.
- Retain Triton for tree verification; FlashInfer handles linear-chain verification.
- Add one focused selector-policy test file, including a small tree-verify dispatcher regression.

## Accuracy Tests

### Setup

Hardware/runtime: 4× NVIDIA B200, TP4, CUDA 13.0, FlashInfer 0.6.12,
Qwen3-Next-80B-A3B-Instruct, PR head `4eae486374255a3f393677a3b689e0136f683d09`.
Both arms use `no_buffer`, page size 1, overlap disabled, static chunk size 2048
(maximum 8192), and Triton decode. Only GDN prefill selection differs.

### GSM8K

Full 1,319-question, single-shot evaluation with `--num-threads 64`,
`temperature=0`, `top_p=0.95`, no thinking, and maximum 4,096 output tokens.

| Arm | GDN prefill selection | Correct | Accuracy | Stop rate | Truncated | Errors |
|---|---|---:|---:|---:|---:|---:|
| Before | Explicit Triton | 1,269 / 1,319 | 96.20925% | 99.84837% | 2 | 0 |
| After | Auto FlashInfer (no prefill override) | 1,268 / 1,319 | 96.13343% | 99.77255% | 3 | 0 |

The paired outcomes were 1,264 both-correct, 46 both-wrong, 5 Triton-only
correct, and 4 FlashInfer-only correct; 1,302 / 1,319 extracted answers were
identical. The net difference was one question (-0.07582 percentage points).
The After command omitted `--linear-attn-prefill-backend`, and the server
resolved to `prefill=flashinfer` and `extend=FlashInferGDNKernel`.

### `no_buffer` radix-cache consistency

This gate compares cache-hit logprobs with a fresh full recomputation within each arm;
it does not compute KL directly between FlashInfer and Triton. The measurements used
the same model, TP4, BF16 Mamba state, and static chunk size 2048 on B200.

| Arm | Prefill cache-hit KL | Decode cache-hit KL | Threshold |
|---|---:|---:|---:|
| Before: explicit Triton | `0.0006410874` | `0.0002616577` | `<0.002` |
| After: auto FlashInfer | `0.0006703623` | `0.0006884400` | `<0.002` |

Both arms had real prefill and decode cache hits. The before arm logged
`extend=TritonGDNKernel`; the after arm logged `extend=FlashInferGDNKernel`.
Selector/unit coverage is tracked by CI rather than reported as model accuracy.

## Speed Tests and Profiling

### Setup

```bash
python -m sglang.launch_server --model-path Qwen/Qwen3.5-397B-A17B-FP8 --tp-size 8 --quantization fp8 --kv-cache-dtype fp8_e4m3 --mamba-ssm-dtype bfloat16 --attention-backend trtllm_mha --moe-runner-backend flashinfer_trtllm --chunked-prefill-size 8192 --max-prefill-tokens 8192 --disable-radix-cache
```

Hardware: 8× NVIDIA B200, CUDA 13.0, TP8, FlashInfer 0.6.12. Each result is the median of two balanced cold-server passes. Higher input TPS and lower TTFT are better.

| Run | Workload | Input TPS, Triton → FlashInfer | Change | Mean TTFT ms, Triton → FlashInfer | Change | P90 TTFT ms, Triton → FlashInfer | Change |
|---|---|---:|---:|---:|---:|---:|---:|
| Primary | 1K input / 1 output | 12,789.37 → 15,022.99 | +17.46% | 323.888 → 272.071 | -16.00% | 343.539 → 274.644 | -20.05% |
| Primary | 8K input / 1 output | 57,350.45 → 66,626.20 | +16.17% | 565.685 → 486.904 | -13.93% | 859.832 → 565.604 | -34.22% |
| Primary | 16K input / 1 output, single chunk | 75,600.85 → 73,595.04 | -2.65% | 823.898 → 847.839 | +2.91% | 855.013 → 1,017.605 | +19.02% |
| Primary | 1K input / 1K output | 752.12 → 759.23 | +0.95% | 305.530 → 265.620 | -13.06% | 309.558 → 280.416 | -9.41% |
| Replication | 1K input / 1 output | 14,114.52 → 15,040.94 | +6.56% | 289.781 → 271.356 | -6.36% | 294.524 → 277.040 | -5.94% |
| Replication | 8K input / 1 output | 60,663.37 → 65,291.01 | +7.63% | 536.248 → 498.764 | -6.99% | 773.661 → 618.762 | -20.02% |
| Replication | 16K input / 1 output, single chunk | 75,463.18 → 73,203.37 | -2.99% | 824.996 → 852.799 | +3.37% | 857.365 → 1,028.085 | +19.91% |
| Replication | 1K input / 1K output | 748.46 → 751.96 | +0.47% | 297.878 → 284.550 | -4.47% | 302.071 → 288.728 | -4.42% |

The 16K single-chunk regression motivates the 8192-token selection ceiling. A separate 16K-prompt/8K-chunk gate produced:

| FlashInfer boot | Input TPS, Triton reference → FlashInfer | Change | Mean TTFT change | P90 TTFT change |
|---|---:|---:|---:|---:|
| Boot 1 | 47,966.25 → 50,557.74 | +5.403% | -5.165% | -5.072% |
| Boot 2 | 48,606.85 → 51,272.00 | +5.483% | -5.232% | -3.732% |
| Two-boot center | 48,286.55 → 50,914.87 | +5.443% | -5.198% | -4.407% |

Each boot used 3 rounds × 12 measured 16K-input/1-output requests at concurrency 1.

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
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.





































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28993171109](https://github.com/sgl-project/sglang/actions/runs/28993171109)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28993171002](https://github.com/sgl-project/sglang/actions/runs/28993171002)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
