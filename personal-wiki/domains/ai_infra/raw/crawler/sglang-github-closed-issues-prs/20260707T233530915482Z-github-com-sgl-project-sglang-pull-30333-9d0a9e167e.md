---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Fix DeepSeek V4 MTP accuracy issue'
canonical_url: https://github.com/sgl-project/sglang/pull/30333
captured_at: '2026-07-07T23:35:30.915482+00:00'
content_hash: 9d0a9e167e47cf14ec57591085c64b61f535b123020b56a2de72e184b23b6171
---
# [AMD] Fix DeepSeek V4 MTP accuracy issue

URL: https://github.com/sgl-project/sglang/pull/30333
State: closed
Labels: amd, deepseek, run-ci
Closed at: 2026-07-07T06:57:58Z
Merged at: 2026-07-07T06:57:58Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

After PR #28612, C128 state became request-scoped instead of SWA-slot-scoped. On cold server startup, only the sentinel row was initialized, while normal request-scoped C128 rows could still contain `torch.empty()` garbage. MTP target-verify writes draft-token C128 states based on the committed request state, so an uninitialized committed row can corrupt draft verification and cause first-run GSM8K accuracy drops which metioned in https://github.com/sgl-project/sglang/pull/30238#issuecomment-4891010577.

## Modifications

- Initialize the **full** non-online C128 `kv_score_buffer` to the empty-state sentinel during pool creation. Keep the existing last-row-only initialization for C4 to avoid unnecessary behavior changes.
- Add `is_hip` guard so the change only applies on AMD/ROCm platforms and remains a no-op on other platforms.

## Accuracy Tests

root@smci355-ccs-aus-n12-13:/sgl-workspace/sglang# python3 /sgl-workspace/sglang/benchmark/gsm8k/bench_sglang.py --port 8000 --num-questions 1319
100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1319/1319 [01:09<00:00, 19.07it/s]
Accuracy: 0.952
Invalid: 0.000
Latency: 69.184 s
Output throughput: 1712.156 token/s

## Speed Tests and Profiling

This PR has almost no impact on performance.

TP8 DP8, 8k/1k, concurrency = 256, num prompts = 4 × concurrency | Total token throughput (tok/s) | Mean TTFT (ms)| Mean TPOT (ms)|
-- | -- | -- | -- |
Main branch | 29615.05| 18381.47| 59.22 |
This PR | 29587.03| 18463.91| 59.25 |


### Server cmd
```
export SGLANG_DEFAULT_THINKING=1
export SGLANG_DSV4_REASONING_EFFORT=max
export SGLANG_OPT_DEEPGEMM_HC_PRENORM=false
export SGLANG_USE_AITER=1
export SGLANG_USE_ROCM700A=${SGLANG_USE_ROCM700A:-0}
export SGLANG_OPT_USE_FUSED_COMPRESS=true
export SGLANG_HACK_FLASHMLA_BACKEND=${SGLANG_HACK_FLASHMLA_BACKEND:-unified_kv_triton}
export SGLANG_OPT_FP8_WO_A_GEMM=false
export SGLANG_OPT_USE_JIT_INDEXER_METADATA=false
export SGLANG_OPT_USE_TOPK_V2=false
export SGLANG_OPT_USE_AITER_INDEXER=${SGLANG_OPT_USE_AITER_INDEXER:-true}
export SGLANG_OPT_USE_TILELANG_INDEXER=false
export SGLANG_OPT_USE_TILELANG_MHC_PRE=false
export SGLANG_OPT_USE_TILELANG_MHC_POST=false
export SGLANG_FP8_PAGED_MQA_LOGITS_TORCH=1
export SGLANG_OPT_USE_FUSED_COMPRESS_TRITON=true
export SGLANG_OPT_USE_MULTI_STREAM_OVERLAP=false
export SGLANG_ROCM_USE_MULTI_STREAM=false
export AITER_BF16_FP8_MOE_BOUND=0
export SGLANG_EAGER_INPUT_NO_COPY=true
export SGLANG_SHARED_EXPERT_TP1=1
export SGLANG_DP_SHARED_EXPERT_LOCAL=1
export SGLANG_DP_USE_GATHERV=1
export SGLANG_DP_USE_REDUCE_SCATTER=1
export GPU_MAX_HW_QUEUES=5
# export SGLANG_ENABLE_DP_TBO=1
MODEL=/mnt/data/pretrained_model/deepseek-ai/DeepSeek-V4-Pro
sglang serve \
    --model-path ${MODEL} \
    --trust-remote-code \
    --tp 8 \
    --dp 8 \
    --enable-dp-attention \
    --enable-prefill-delayer \
    --disable-radix-cache \
    --attention-backend dsv4 \
    --page-size 256 \
    --mem-fraction-static 0.9 \
    --swa-full-tokens-ratio 0.15 \
    --disable-shared-experts-fusion \
    --tool-call-parser deepseekv4 \
    --reasoning-parser deepseek-v4 \
    --kv-cache-dtype fp8_e4m3 \
    --chunked-prefill-size 65536 \
    --cuda-graph-max-bs 512 \
    --max-running-requests 512 \
    --port 8000 \
```
### Client cmd
```
#!/bin/bash

# ===== Default parameters =====
INPUT_LEN=${1:-8192}
OUTPUT_LEN=${2:-1024}
ENABLE_PROFILE=${3:-1}   # 1 = enable profile, 0 = disable

# ===== Timestamp =====
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "INPUT_LEN=${INPUT_LEN}"
echo "OUTPUT_LEN=${OUTPUT_LEN}"
echo "PROFILE=${ENABLE_PROFILE}"
echo "TIMESTAMP=${TIMESTAMP}"

for concurrency in 256
do
    prompt=$((concurrency * 4))
    warmup=$((concurrency * 2))
    LOG_FILE="mi355_${INPUT_LEN}_${OUTPUT_LEN}_tp8_c-${concurrency}_${TIMESTAMP}.log"

    CMD="python3 -m sglang.bench_serving \
        --port 8000 \
        --dataset-name random \
        --random-input ${INPUT_LEN} \
        --random-output ${OUTPUT_LEN} \
        --random-range-ratio 1 \
        --max-concurrency ${concurrency} \
        --num-prompt ${prompt} \
        --warmup-requests ${warmup}"

    # ===== Optional profile =====
    if [ "${ENABLE_PROFILE}" -eq 1 ]; then
        CMD="${CMD} --profile --profile-num-steps 4 --profile-by-stage"
    fi

    echo "Running: ${CMD}"
    echo "Log: ${LOG_FILE}"

    eval ${CMD} 2>&1 | tee ${LOG_FILE}
done
```
<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28840802173](https://github.com/sgl-project/sglang/actions/runs/28840802173)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28840802089](https://github.com/sgl-project/sglang/actions/runs/28840802089)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
