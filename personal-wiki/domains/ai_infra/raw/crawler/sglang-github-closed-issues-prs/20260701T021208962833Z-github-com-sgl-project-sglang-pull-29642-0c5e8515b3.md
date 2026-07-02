---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Copy decode result on forward_stream instead of copy_stream'
canonical_url: https://github.com/sgl-project/sglang/pull/29642
captured_at: '2026-07-01T02:12:08.962833+00:00'
content_hash: 0c5e8515b3ead1c2e130de8c3bbfadd6990edda41b573f7ff0e4bf3634aff287
---
# [AMD] Copy decode result on forward_stream instead of copy_stream

URL: https://github.com/sgl-project/sglang/pull/29642
State: closed
Labels: amd, run-ci
Closed at: 2026-06-30T06:53:49Z
Merged at: 2026-06-30T06:53:49Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

[#29075](https://github.com/sgl-project/sglang/pull/29075) moved the decode result D2H copy from `forward_stream` onto a dedicated `copy_stream` to overlap it with the next forward. On ROCm, however, every decode step now pays a cross-stream sync (`copy_stream.wait_stream(forward_stream)` + event gating), and that fixed cost outweighs the tiny copy it overlaps.

This scheduler change is general. It regresses decode performance across models (e.g. ~10–20% on DeepSeek-V4-Pro and Qwen-3.5-MXFP4).

## Modifications

<!-- Detail the changes made in this pull request. -->

On the HIP path, skip `copy_stream` and the extra event wait. Perform the result D2H copy directly on `forward_stream`.
The CUDA path is unchanged.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

GSM8k, 1319:
- DeepSeek-V4-Pro: 0.951
- Qwen3.5-397B-A17B-MXFP4: 0.898

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

<details>
<summary>Server cmd</summary>
DeepSeek-V4-Pro

```
DP_MODE="${DP_MODE:-tp8}"
MODEL="${MODEL:-/data/deepseek-ai/DeepSeek-V4-Pro}"
PORT="${PORT:-8000}"

export SGLANG_DEFAULT_THINKING=1
export SGLANG_DSV4_REASONING_EFFORT=max
export SGLANG_USE_ROCM700A=0
export SGLANG_DP_USE_GATHERV=1
export SGLANG_HACK_FLASHMLA_BACKEND=unified_kv_triton
export AITER_BF16_FP8_MOE_BOUND=0

DP_ARGS=""
if [ "$DP_MODE" = "tp8dp8" ]; then
    DP_ARGS="--dp 8 --enable-dp-attention --enable-prefill-delayer --prefill-delayer-max-delay-ms 5000"
fi
set -x
exec sglang serve \
    --model-path "${MODEL}" \
    --trust-remote-code \
    --tp 8 \
    ${DP_ARGS} \
    --attention-backend dsv4 \
    --page-size 256 \
    --mem-fraction-static 0.90 \
    --swa-full-tokens-ratio 0.15 \
    --disable-shared-experts-fusion \
    --tool-call-parser deepseekv4 \
    --reasoning-parser deepseek-v4 \
    --chunked-prefill-size 8192 \
    --cuda-graph-max-bs 512 \
    --max-running-requests 512 \
    --disable-radix-cache \
    --kv-cache-dtype fp8_e4m3 \
    --port "${PORT}"
```

Qwen3.5-397B-A17B-MXFP4

```
MODEL="/data/amd/Qwen3.5-397B-A17B-MXFP4"
AITER_FLYDSL_FORCE=1 \
SGLANG_USE_AITER_UNIFIED_ATTN=1 SGLANG_USE_AITER=1 \
python3 -m sglang.launch_server \
  --model-path "${MODEL}" --tp 2 \
  --attention-backend aiter --trust-remote-code \
  --chunked-prefill-size 32768 \
  --model-loader-extra-config '{"enable_multithread_load": true}' \
  --watchdog-timeout 1200 --mem-fraction-static 0.9 \
  --host 0.0.0.0 --port "${PORT:-9000}" --disable-radix-cache \
  --enable-aiter-allreduce-fusion --max-running-requests 512 \
  --page-size 16  
```

</details>

Measured on AMD MI355X (input 8192 / output 1024, concurrency 4):

  | Model | Metric | non-fix | fix | Improvement |
  |---|---|---:|---:|---:|
  | DeepSeek-V4-Pro | TTT (tok/s) | 1979.76 | 2328.57 | +17.6% |
  | | ITL (ms) | 16.94 | 14.19 | −16.2% |
  | Qwen3.5-397B-A17B-MXFP4 | TTT (tok/s) | 2987.74 | 3366.77 | +12.7% |
  |  | ITL (ms) | 10.92 | 9.58 | −12.3% |uv,

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.



<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28362113433](https://github.com/sgl-project/sglang/actions/runs/28362113433)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28362112979](https://github.com/sgl-project/sglang/actions/runs/28362112979)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
