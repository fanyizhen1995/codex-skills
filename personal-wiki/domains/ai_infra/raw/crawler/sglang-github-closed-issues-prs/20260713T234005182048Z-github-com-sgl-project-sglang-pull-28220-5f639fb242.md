---
source_id: sglang-github-closed-issues-prs
title: '[FlashInfer v0.6.13] Use CuTe DSL backend for FlashInfer per-token NVFP4 quantization'
canonical_url: https://github.com/sgl-project/sglang/pull/28220
captured_at: '2026-07-13T23:40:05.182048+00:00'
content_hash: 5f639fb242d8f42345b32e7be73932daeef88da4d11e49dfbc96057e6c1c49ab
---
# [FlashInfer v0.6.13] Use CuTe DSL backend for FlashInfer per-token NVFP4 quantization

URL: https://github.com/sgl-project/sglang/pull/28220
State: closed
Labels: blackwell, run-ci
Closed at: 2026-07-13T14:37:47Z
Merged at: 2026-07-13T14:37:47Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

@humansand

FlashInfer now has merged CuTe DSL support for per-token NVFP4 quantization and NVFP4 4over6 in flashinfer-ai/flashinfer#3448. The SGLang integration originally landed while some CuTe DSL NVFP4 support was still incomplete, so the per-token activation and online NVFP4 load-time conversion paths either relied on FlashInfer defaults or explicitly selected the CUDA backend.

This PR updates those existing integration points to explicitly use the CuTe DSL backend now that it supports the needed NVFP4 modes.

Related SGLang integration PRs:
- sgl-project/sglang#22918
- sgl-project/sglang#25239
- sgl-project/sglang#26083

FlashInfer support PR:
- flashinfer-ai/flashinfer#3448

## Modifications

- Pass `backend="cute-dsl"` to FlashInfer `nvfp4_quantize` for FlashInfer TRTLLM per-token NVFP4 activation quantization.
- Use `backend="cute-dsl"` for `--quantization nvfp4_online` load-time expert weight conversion.
- Scope online NVFP4 exact quantization math with `FLASHINFER_DISABLE_FP4_QUANT_FAST_MATH=1`, matching the FlashInfer Python/CuTe DSL environment variable used by the selected backend.

## Accuracy Tests

Not run. This PR only changes FlashInfer backend selection for existing NVFP4 quantization paths and does not add new numerics coverage.

## Speed Tests and Profiling

SGLang end-to-end benchmarks were not rerun for this small integration PR. FlashInfer backend microbenchmarks from flashinfer-ai/flashinfer#3448 show the CuTe DSL quantizer performance for the same NVFP4 modes used here.

Common config from the FlashInfer benchmark:
- dtype: `bfloat16`
- scale-factor layout: `swizzled_128x4`
- `FLASHINFER_NVFP4_4OVER6=1`
- `FLASHINFER_NVFP4_4OVER6_ERR_MODE=MSE`
- `FLASHINFER_NVFP4_4OVER6_E4M3_USE_256=1`
- `FLASHINFER_DISABLE_FP4_QUANT_FAST_MATH=1`
- CUDA graph disabled, CUPTI timing enabled, cold L2 cache enabled

| Activation scale | CUDA no fast math | CUDA fast math | CuTe DSL no fast math | CuTe DSL fast math |
| --- | ---: | ---: | ---: | ---: |
| Per-tensor | 2.83x / 1.65x / 5.81x | 3.22x / 1.67x / 7.25x | 2.17x / 1.21x / 8.26x | 4.12x / 2.45x / 20.92x |
| Per-token | 0.89x / 0.71x / 0.98x | 1.41x / 1.05x / 3.40x | 2.05x / 1.03x / 2.89x | 3.00x / 1.80x / 4.17x |

Pure per-token NVFP4 without 4over6:

| Mode | CuTe DSL vs CUDA geomean/min/max |
| --- | ---: |
| Pure per-token no 4over6 | 2.24x / 1.04x / 3.76x |

![NVFP4 4over6 MSE per-tensor speedup heat map](https://gist.githubusercontent.com/zianglih/1e1fdd42d27244692d66cd6a5b2b904f/raw/2f4f7965c0b57e7b148acdde64a632daa11072a6/nvfp4_4over6_mse_speedup_vs_baseline_per_tensor.svg)

![NVFP4 4over6 MSE per-token speedup heat map](https://gist.githubusercontent.com/zianglih/1e1fdd42d27244692d66cd6a5b2b904f/raw/23fc9c84605795b9c17febac47f0175fc14c3a07/nvfp4_4over6_mse_speedup_vs_baseline_per_token.svg)

![NVFP4 pure per-token no-4over6 CuTe DSL vs CUDA heat map](https://gist.githubusercontent.com/zianglih/1e1fdd42d27244692d66cd6a5b2b904f/raw/34e161c89dc0a23378c5d23041567953b8f7c9b2/nvfp4_pure_per_token_no_4over6_cute_vs_cuda.svg)

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29061331120](https://github.com/sgl-project/sglang/actions/runs/29061331120)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29061330993](https://github.com/sgl-project/sglang/actions/runs/29061330993)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
