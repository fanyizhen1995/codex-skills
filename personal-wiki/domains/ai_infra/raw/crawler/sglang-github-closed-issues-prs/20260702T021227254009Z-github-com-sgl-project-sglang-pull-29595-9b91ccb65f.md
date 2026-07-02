---
source_id: sglang-github-closed-issues-prs
title: '[Spec] Enable FlashInfer autotune for spec draft'
canonical_url: https://github.com/sgl-project/sglang/pull/29595
captured_at: '2026-07-02T02:12:27.254009+00:00'
content_hash: 9b91ccb65fb6c8730bb07ade152b5eb12a20de3541bc0fa36acbd9db674f329a
---
# [Spec] Enable FlashInfer autotune for spec draft

URL: https://github.com/sgl-project/sglang/pull/29595
State: closed
Labels: run-ci
Closed at: 2026-07-01T20:36:08Z
Merged at: 2026-07-01T20:36:08Z

## Summary

Enable FlashInfer autotuning for speculative decoding draft graph paths

## Validation

Checked on GB300 with `auto` picking `flashinfer_trtllm` for both target and draft MoE runner backends:

```bash
sglang serve \
  --model-path nvidia/GLM-5.2-NVFP4 \
  --tensor-parallel-size 4 \
  --speculative-algorithm EAGLE \
  --speculative-num-steps 5 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 6
```

In this setup, the target model was already autotuned before this change:

Target:

```text
[2026-06-29 01:38:08 TP3] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp3_pp0_dp0.json
[2026-06-29 01:38:08 TP0] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp0_pp0_dp0.json
[2026-06-29 01:38:08 TP1] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp1_pp0_dp0.json
[2026-06-29 01:38:08 TP2] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp2_pp0_dp0.json
[AutoTuner]: Tuning flashinfer::trtllm_fp4_block_scale_moe: 100%|███████████████████████████████████████████████████████████████████| 10/10 [01:29<00:00,  8.92s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_fp4_block_scale_moe: 100%|███████████████████████████████████████████████████████████████████| 10/10 [01:29<00:00,  8.97s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_fp4_block_scale_moe: 100%|███████████████████████████████████████████████████████████████████| 10/10 [01:29<00:00,  8.99s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_fp4_block_scale_moe: 100%|███████████████████████████████████████████████████████████████████| 10/10 [01:30<00:00,  9.03s/profile]
```

With this change, the same run also autotunes both speculative draft phases:

Draft decode:

```text
[2026-06-29 01:45:38 TP2] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp2_pp0_dp0.json
[2026-06-29 01:45:38 TP0] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp0_pp0_dp0.json
[2026-06-29 01:45:38 TP1] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp1_pp0_dp0.json
[2026-06-29 01:45:38 TP3] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp3_pp0_dp0.json
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|████████████████████████████████████████████████████████████████████████████████| 7/7 [00:46<00:00,  6.62s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|████████████████████████████████████████████████████████████████████████████████| 7/7 [00:46<00:00,  6.64s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|████████████████████████████████████████████████████████████████████████████████| 7/7 [00:46<00:00,  6.71s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|████████████████████████████████████████████████████████████████████████████████| 7/7 [00:46<00:00,  6.71s/profile]
```

Draft extend:

```text
[2026-06-29 01:46:29 TP1] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp1_pp0_dp0.json
[2026-06-29 01:46:29 TP3] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp3_pp0_dp0.json
[2026-06-29 01:46:29 TP2] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp2_pp0_dp0.json
[2026-06-29 01:46:29 TP0] Running FlashInfer autotune with cache: /root/.cache/sglang/flashinfer/autotune/0.6.12/sm103/15fc7a2edb371f48/rank_tp0_pp0_dp0.json
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|██████████████████████████████████████████████████████████████████████████████| 10/10 [00:28<00:00,  9.39s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|██████████████████████████████████████████████████████████████████████████████| 10/10 [00:28<00:00,  9.39s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|██████████████████████████████████████████████████████████████████████████████| 10/10 [00:28<00:00,  9.55s/profile]
[AutoTuner]: Tuning flashinfer::trtllm_bf16_moe: 100%|██████████████████████████████████████████████████████████████████████████████| 10/10 [00:28<00:00,  9.55s/profile]
```

## Speed Test

```bash
python -m sglang.benchmark.serving \
  --backend sglang \
  --host 127.0.0.1 --port 30000 \
  --model nvidia/GLM-5.2-NVFP4 \
  --dataset-name random \
  --random-input-len 8192 --random-output-len 1024 \
  --num-prompts 8 --max-concurrency 1 \
  --warmup-requests 64 --flush-cache \
  --random-range-ratio 1.0
```

```text
Interactivity: 465.1 -> 485.4 tok/s (+4.4%)
```















































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28506915247](https://github.com/sgl-project/sglang/actions/runs/28506915247)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28506914972](https://github.com/sgl-project/sglang/actions/runs/28506914972)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
