---
source_id: sglang-github-closed-issues-prs
title: Add DeepGEMM MXFP8 MoE backend
canonical_url: https://github.com/sgl-project/sglang/pull/26342
captured_at: '2026-07-13T23:40:05.166903+00:00'
content_hash: 3f9dac7f9b6c987cb01a890f826804eb0a0507024cc9b14f15e9378c1566468d
---
# Add DeepGEMM MXFP8 MoE backend

URL: https://github.com/sgl-project/sglang/pull/26342
State: closed
Labels: quant
Closed at: 2026-07-13T19:57:07Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->
@humansand
## Motivation

Add DeepGEMM support for MXFP8 dense GEMM and MXFP8 MoE execution on Blackwell.

This is needed for MXFP8 checkpoints where the dense layers and routed expert weights use MXFP8 E4M3 data with MXFP-style scale layouts. Those scale contracts are different from block-scaled FP8 and per-tensor/per-expert FP8, so this PR adds explicit DeepGEMM MXFP8 packing, swizzling, validation, and load/update handling instead of reusing the existing FP8 paths interchangeably.

The MoE path supports `--moe-runner-backend deep_gemm` with the standard local routed path and the DeepEP normal all-to-all path. DeepEP low-latency remains unsupported for this backend because its current scale layout contract differs from the normal DeepEP path.

## Modifications

- Add DeepGEMM MXFP8 dense linear support behind `--fp8-gemm-backend deep_gemm`.
- Add DeepGEMM MXFP8 MoE support behind `--moe-runner-backend deep_gemm`.
- Add MXFP8 weight/scale packing helpers for DeepGEMM dense and grouped MoE kernels.
- Add DeepGEMM JIT warmup/cache handling for MXFP8 dense, grouped, and masked grouped kernels.
- Wire MXFP8 scale packing/swizzling into model load and `/update_weights_from_disk`, so reloaded weights keep the DeepGEMM backend layout contract.
- Support DeepEP normal dispatch for the DeepGEMM MXFP8 MoE backend via `--moe-a2a-backend deepep` without requiring users to manually set `--deepep-mode normal`.
- Raise a clear error for DeepEP low-latency with this backend for now.
- Keep older DeepGEMM BF16 grouped-GEMM compatibility inside `deep_gemm_wrapper` rather than in the MoE runner, so the runner calls wrapper APIs and backend-version details stay localized.
- Add B200 manual tests for DeepGEMM MXFP8 dense and masked grouped MoE paths.
- Add registered `/update_weights_from_disk` coverage for the DeepGEMM MXFP8 MoE DeepEP configuration.

## Accuracy Tests

Local/static checks:

```bash
python3 -m py_compile \
  python/sglang/srt/layers/deep_gemm_wrapper/entrypoint.py \
  python/sglang/srt/layers/moe/moe_runner/deep_gemm.py \
  python/sglang/srt/layers/quantization/fp8_utils.py

git diff --check upstream/main..HEAD
pre-commit run --all-files
```

B200 manual kernel tests:

```bash
python3 test/manual/quant/test_block_fp8_deep_gemm_blackwell.py \
  TestDeepGemmBlackwell.test_deep_gemm_mxfp8_linear \
  TestDeepGemmBlackwell.test_deep_gemm_mxfp8_masked_grouped_moe \
  -v
```

Result:

```text
test_deep_gemm_mxfp8_linear ... ok
test_deep_gemm_mxfp8_masked_grouped_moe ... ok
Ran 2 tests in 0.492s
OK
```

B200 SGLang smoke on the rebased branch:

```bash
python3 -m sglang.launch_server \
  --model-path zianglih/Qwen3-30B-A3B-Instruct-2507-MXFP8-last-8-BF16 \
  --host 127.0.0.1 --port 30000 \
  --base-gpu-id 0 --tp-size 4 \
  --fp8-gemm-backend deep_gemm \
  --moe-runner-backend deep_gemm \
  --moe-a2a-backend deepep
```

Result:

- Server reached `/health_generate` and `/model_info` readiness.
- Baseline deterministic generation succeeded.
- `/update_weights_from_disk` succeeded with `flush_cache=true`.
- Generation after `flush_cache=true` matched baseline text, token ids, and output logprobs.
- `/update_weights_from_disk` succeeded with `flush_cache=false`.
- Generation after `flush_cache=false` matched baseline text, token ids, and output logprobs.
- This launch intentionally did not set `--deepep-mode`; the backend used the default DeepEP mode normalization.

Local log copies from the B200 runs are retained under:

- `/Users/ziangli/playground/mxfp8-deepgemm/logs/deepgemm_mxfp8_moe_manual_20260525_202727/run.log`
- `/Users/ziangli/playground/mxfp8-deepgemm/logs/deepgemm_mxfp8_deepep_upstream_20260526_041834/`

## Speed Tests and Profiling

Dedicated throughput benchmarks and profiling have not been run yet. This PR is still draft and currently reports correctness/smoke validation only; no speedup claim is made in this PR description.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations). Not updated yet; this PR is draft.
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). Accuracy/smoke results are included above; speed benchmarks are pending.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.
