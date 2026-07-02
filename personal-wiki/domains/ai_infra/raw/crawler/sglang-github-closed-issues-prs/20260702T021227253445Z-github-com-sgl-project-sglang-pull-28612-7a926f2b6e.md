---
source_id: sglang-github-closed-issues-prs
title: Optimize C128 state pool allocation using request state pool
canonical_url: https://github.com/sgl-project/sglang/pull/28612
captured_at: '2026-07-02T02:12:27.253445+00:00'
content_hash: 7a926f2b6e56236aafed98fa39165ca6cc6c9110a96fed9bf11fa2538ea3f6a2
---
# Optimize C128 state pool allocation using request state pool

URL: https://github.com/sgl-project/sglang/pull/28612
State: closed
Labels: high priority, deepseek, run-ci, jit-kernel, run-ci-extra, release-highlight
Closed at: 2026-07-01T02:11:30Z
Merged at: 2026-07-01T02:11:30Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Co-authored-by: [shiyu7](https://github.com/shiyu7)

This PR optimizes the C128 state slot lookup path.

The issue was introduced when the online C128/MTP path started deriving C128 state slots through SWA mapping. Before this change, `full_to_swa_index_mapping` was only a temporary translation table for SWA attention KV slots. The original radix/SWA cache lifecycle allows radix cache to keep the full KV prefix alive while the SWA sidecar KV for the same prefix may be tombstoned or freed earlier, such as through SWA-only eviction or `dec_swa_lock_only()`.

With online C128 + MTP, the state lookup path used logic equivalent to:

```python
full_loc = req_to_token[rid][chunk_start]
swa_loc = full_to_swa[full_loc]
main_slot = swa_loc / swa_page_size
```

This made `full_to_swa_index_mapping` part of the C128 state indexing path. When a multi-turn request hit a radix-cached prefix, the full KV prefix could still be alive in the radix tree while the corresponding SWA mapping had already been cleared or reused. The online C128/MTP path could then read slot 0, an old slot, or a reused slot, causing accuracy degradation.

## Modifications

1. Decoupled C128 state from SWA mapping. C128 no longer uses `full_to_swa` or `swa_page_size` to locate state slots.

2. Changed C128 state indexing to request-scoped layout. Online C128 uses `req_pool_idx`; offline C128 uses a per-request ring: `req_pool_idx * ring_size + position % ring_size`.

3. Kept C4 unchanged on the SWA-based sliding-window path.

4. Changed C128 state pool allocation from token-proportional sizing to request-scoped sizing, and accounted for this fixed memory in DSV4 pool capacity estimation.

5. Updated online C128 MTP and PD disaggregation transfer paths to follow the new request-scoped C128 state layout.

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

PD:
```
SGLANG_OPT_USE_ONLINE_COMPRESS=1 SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT=600  SGLANG_DSV4_FP4_EXPERTS=0 GLOO_SOCKET_IFNAME=eth0 python3 -m sglang.launch_server --model-path /data00/models/DeepSeek-V4-Flash-FP8 --tokenizer-path /data00/models/DeepSeek-V4-Flash-FP8 --host 0.0.0.0 --port 30000 --trust-remote-code --kv-cache-dtype fp8_e4m3 --mem-fraction-static 0.9 --max-running-requests 64 --chunked-prefill-size 8192 --max-prefill-tokens 16384 --tp-size 2 --pp-size 4 --attn-cp-size 2 --attention-backend dsv4 --reasoning-parser deepseek-v4 --tool-call-parser deepseekv4 --disable-overlap-schedule --disable-piecewise-cuda-graph --enable-nsa-prefill-context-parallel --disaggregation-mode prefill --disaggregation-transfer-backend mooncake --nsa-prefill-cp-mode round-robin-split --enable-metrics --disaggregation-ib-device mlx5_1,mlx5_2,mlx5_3,mlx5_4


SGLANG_EXPERIMENTAL_ONLINE_C128_MTP=1 SGLANG_OPT_USE_ONLINE_COMPRESS=1 SGLANG_DISAGGREGATION_WAITING_TIMEOUT=600 SGLANG_DSV4_FP4_EXPERTS=0 SGLANG_OPT_DEEPGEMM_HC_PRENORM=1 SGLANG_OPT_USE_TILELANG_MHC_PRE=1 SGLANG_JIT_DEEPGEMM_PRECOMPILE=1 GLOO_SOCKET_IFNAME=eth0 NCCL_MIN_NCHANNELS=24 NCCL_IB_QPS_PER_CONNECTION=8 SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=300 sglang serve --trust-remote-code --model-path /data00/models/DeepSeek-V4-Flash-FP8 --tp 8 --dp-size 8 --enable-dp-attention --cuda-graph-max-bs 80 --max-running-requests 640 --enable-metrics --host 0.0.0.0 --port 30000 --mem-fraction-static 0.8 --tool-call-parser deepseekv4 --reasoning-parser deepseek-v4 --moe-runner-backend deep_gemm --moe-a2a-backend deepep --deepep-mode low_latency --disaggregation-mode decode  --disaggregation-ib-device "mlx5_1,mlx5_2,mlx5_3,mlx5_4" --speculative-algo EAGLE --speculative-num-steps 2 --speculative-eagle-topk 1 --speculative-num-draft-tokens 3 --tokenizer-worker-num 8 
```
PR | Hardward | MMLU | GSM8K | QPQA  | pinchbench-10 | aime25 repeats 24
-- | -- | -- | -- | -- | --  | -- 
online MTP c128 | H20 | 0.885  |  0.952 | 0.895 | 0.94 | pass@1[avg-of-24]  =  96.39% +/- 2.77% (SEM 0.56%)
online c128 | H20 |  0.885 | 0.951 | 0.895 | 0.94 | pass@1[avg-of-24]  = 97.08% +/- 2.27% (SEM 0.46%)
normal MTP | H20 | 0.885 |  0.954 | 0.906  | 0.95 | pass@1[avg-of-24]  =  95.56% +/- 3.36% (SEM 0.69%)

Non PD:
```
SGLANG_EXPERIMENTAL_ONLINE_C128_MTP=1 SGLANG_OPT_USE_ONLINE_COMPRESS=1 SGLANG_DSV4_FP4_EXPERTS=0 SGLANG_OPT_DEEPGEMM_HC_PRENORM=1 SGLANG_OPT_USE_TILELANG_MHC_PRE=1 SGLANG_JIT_DEEPGEMM_PRECOMPILE=1 GLOO_SOCKET_IFNAME=eth0 NCCL_MIN_NCHANNELS=24 NCCL_IB_QPS_PER_CONNECTION=8 SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=300 sglang serve --trust-remote-code --model-path /data00/models/DeepSeek-V4-Flash-FP8 --tp 8 --dp-size 8 --enable-dp-attention --cuda-graph-max-bs 32 --max-running-requests 256 --enable-metrics --host 0.0.0.0 --port 8090 --mem-fraction-static 0.8 --tool-call-parser deepseekv4 --reasoning-parser deepseek-v4 --moe-runner-backend deep_gemm --moe-a2a-backend deepep --deepep-mode auto --speculative-algo EAGLE --speculative-num-steps 2 --speculative-eagle-topk 1 --speculative-num-draft-tokens 3 --tokenizer-worker-num 8 
```
PR | Hardward | MMLU | GSM8K | QPQA  | pinchbench-10 | aime25 repeats 24
-- | -- | -- | -- | -- | --  | -- 
online MTP c128 | H20 | 0.884 | 0.952 | 0.898 | 0.94  | 96.94% +/- 2.39% (SEM 0.49%)
online c128 | H20 | 0.884 | 0.951 | 0.891 | 0.96  | 97.64% +/- 2.86% (SEM 0.58%)
normal MTP | H20 | 0.886 | 0.958 | 0.914 | 0.92  | 95.83% +/- 2.99% (SEM 0.61%)

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28432147498](https://github.com/sgl-project/sglang/actions/runs/28432147498)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28547079380](https://github.com/sgl-project/sglang/actions/runs/28547079380)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
