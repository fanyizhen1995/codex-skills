---
source_id: sglang-github-closed-issues-prs
title: '[Spec] DSpark support PD and DeepEP'
canonical_url: https://github.com/sgl-project/sglang/pull/30513
captured_at: '2026-07-12T23:38:53.052921+00:00'
content_hash: da5e78ad75f050f98f008b2c0d06b5af0de5b8faabe16ae20ce6c632ee939782
---
# [Spec] DSpark support PD and DeepEP

URL: https://github.com/sgl-project/sglang/pull/30513
State: closed
Labels: deepseek, speculative-decoding
Closed at: 2026-07-12T22:25:30Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Reference PR: https://github.com/sgl-project/sglang/pull/29705

upstream PR: https://github.com/sgl-project/sglang/pull/30261

This PR improves DSpark support for DeepSeek-V4 in two deployment scenarios:

1. Enable DSpark to run with `deepep + deep_gemm` MoE backend.
2. Add DSpark support for prefill/decode disaggregation by bootstrapping the draft-side cache on the decode node.

Previously, DSpark with DP attention was restricted to the built-in TP MoE path (`moe_a2a_backend=none`). In addition, the disaggregated decode path did not initialize DSpark draft state from the prefill result, so decode could enter speculative decoding with missing `spec_info`.

<!-- Describe the purpose and goals of this pull request. -->

Modifications

- Allow DSpark + DP attention to use moe_a2a_backend=deepep with moe_runner_backend=deep_gemm .
- Add speculative MoE backend / A2A backend context handling for DSpark draft execution.
- Initialize DSpark draft input for disaggregated decode using the prefill output token as the first decode anchor.
- Add DSpark target hidden-state transfer through disaggregation metadata.
- Add DSparkHiddenTransferPlan to describe row-chunk hidden transfer plans.
- Add DSparkHiddenPagePool to reuse registered decode-side hidden receive buffers.
- Transfer DSpark hidden states through Mooncake/NIXL as row-addressed page/chunk blocks instead of one large request-level buffer.
- Trim DSpark hidden transfer windows according to prefill-side cached prefix while preserving absolute row offsets.
- Assemble all received hidden pages on decode before committing them to prefill_tail_hidden_states .
- Bootstrap DSpark draft KV cache on the decode node by injecting transferred target hidden states before the first draft step.
- Add PP-aware hidden slice metadata so target layers can be transferred from the PP rank that owns them.
- Match PP last-rank outputs by microbatch id to avoid FIFO output mismatch.
- Use PP output rid hashes to handle compact disaggregated prefill outputs correctly.
- Drain failed PP prefill bootstrap requests consistently across all PP ranks.
- Add non-padded token count metadata for DSpark draft forward batches, required by DeepEP/DeepGEMM CUDA graph replay.
- Make Mooncake/NIXL auxiliary metadata transfer handle DSpark hidden dynamic destination buffers.
- Keep existing non-disaggregated DSpark behavior unchanged.

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

Transfer is OK
```
PD：
[2026-07-08 11:37:43 DP2 TP2 EP2] DSPARK_PARITY draft_anchor rids=['e3badd86e67d4d4491f3b9b04bc667b5'] prefix_lens=[9] bonus_tokens=[5979] draft_block_ids=[5979, 128799, 128799, 128799, 128799] draft_positions=[9, 10, 11, 12, 13] draft_cache_loc=[2313, 2314, 2315, 2316, 2317]

Non-PD：
[2026-07-08 11:50:01 DP0 TP0 EP0] DSPARK_PARITY draft_anchor rids=['9e5e1e9374ff426caa86660e97f0790b'] prefix_lens=[9] bonus_tokens=[5979] draft_block_ids=[5979, 128799, 128799, 128799, 128799] draft_positions=[9, 10, 11, 12, 13] draft_cache_loc=[265, 266, 267, 268, 269]
```

```
Prefill
SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT=600 SGLANG_DISAGGREGATION_QUEUE_SIZE=4 NCCL_SOCKET_IFNAME=eth0  NCCL_IB_DISABLE=0 SGLANG_DSV4_FP4_EXPERTS=1 GLOO_SOCKET_IFNAME=eth0 python3 -m sglang.launch_server --model-path /data00/models/DeepSeek-V4-Flash-DSpark --host 0.0.0.0 --port 30000 --trust-remote-code --kv-cache-dtype fp8_e4m3 --mem-fraction-static 0.9 --max-running-requests 64 --chunked-prefill-size 8192 --max-prefill-tokens 16384 --tp-size 2 --pp-size 4 --attn-cp-size 2 --attention-backend dsv4 --reasoning-parser deepseek-v4 --tool-call-parser deepseekv4 --disable-overlap-schedule --disable-piecewise-cuda-graph --enable-nsa-prefill-context-parallel --disaggregation-mode prefill --disaggregation-transfer-backend mooncake --nsa-prefill-cp-mode round-robin-split --enable-metrics --disaggregation-ib-device mlx5_1,mlx5_2,mlx5_3,mlx5_4 --moe-runner-backend flashinfer_mxfp4

Decode
SGLANG_DSV4_FP4_EXPERTS=1 SGLANG_JIT_DEEPGEMM_PRECOMPILE=1 SGLANG_OPT_DEEPGEMM_HC_PRENORM=1 SGLANG_OPT_USE_TILELANG_MHC_PRE=1 GLOO_SOCKET_IFNAME=eth0 NCCL_MIN_NCHANNELS=24 NCCL_IB_QPS_PER_CONNECTION=8 sglang serve --trust-remote-code --model-path /data00/models/DeepSeek-V4-Flash-DSpark --tp 8 --dp-size 8 --enable-dp-attention --cuda-graph-max-bs 32 --max-running-requests 256 --enable-metrics --host 0.0.0.0 --port 30000 --mem-fraction-static 0.9 --tool-call-parser deepseekv4 --reasoning-parser deepseek-v4 --moe-runner-backend flashinfer_mxfp4 --disaggregation-mode decode --disaggregation-ib-device "mlx5_1,mlx5_2,mlx5_3,mlx5_4" --speculative-algo DSPARK --tokenizer-worker-num 8 --enable-dp-lm-head --load-balance-method round_robin
```

 Hardward | MMLU | GSM8K | QPQA  | aime25 repeats 24 | status
-- | -- | -- | -- | -- | -- 
H20 | 0.886  |  0.945 | 0.930 | 93.96 | PD
H20 |  |  | 0.9068 | 93.54 | non-PD

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
