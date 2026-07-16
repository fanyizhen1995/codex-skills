---
source_id: sglang-github-closed-issues-prs
title: Support scheduler_recv_interval (recv skipper) under DP-attention
canonical_url: https://github.com/sgl-project/sglang/pull/30457
captured_at: '2026-07-14T23:40:21.666327+00:00'
content_hash: 59df9d512c516aa21847b8daf8f51e73842c6d43fa5c00bf3dc889e2f7e2ce51
---
# Support scheduler_recv_interval (recv skipper) under DP-attention

URL: https://github.com/sgl-project/sglang/pull/30457
State: closed
Labels: amd, deepseek, run-ci
Closed at: 2026-07-14T21:02:59Z
Merged at: 2026-07-14T21:02:59Z

## Motivation

`SchedulerRecvSkipper` (added in #8947) lets the scheduler run ~N decode
steps before re-polling for new requests (`--scheduler-recv-interval N`),
reducing recv/scheduling overhead — the modern replacement for the removed
`num_continuous_decode_steps`. However its constructor hard-asserts
`not server_args.enable_dp_attention`, so `--scheduler-recv-interval > 1`
crashes at startup whenever DP-attention is enabled (the original PR left a
note: *"Can be supported if needed, but may need e.g. `global_forward_mode`"*).

This PR implements that: it enables `scheduler_recv_interval > 1` under
DP-attention.

## Modifications

The skip decision must be **identical on every rank** that participates in
the request-broadcast collective. Under DP-attention a rank's *local*
`forward_mode` can diverge across ranks (e.g. `IDLE` on an idle DP rank vs
`DECODE` on a busy one), which would desync the per-rank counter and the
broadcast → hang.

- Feed the skipper the **DP-synchronized `global_forward_mode`** (produced by
  the existing per-step all-gather; identical on all ranks) instead of the
  local forward mode, via a small `Scheduler._recv_skipper_last_forward_mode`
  helper. No extra communication.
- Remove the `assert not server_args.enable_dp_attention` guard.

Non-DP behavior is unchanged (helper falls back to the local forward mode).

## Accuracy

GSM8K (DeepSeek-R1-MXFP4, 8xMI355X), server run with the patch active
(`--enable-dp-attention --scheduler-recv-interval 30`), 3 runs:

| run | accuracy | invalid |
|-----|----------|---------|
| 1   | 0.950    | 0.000   |
| 2   | 0.954    | 0.000   |
| 3   | 0.954    | 0.000   |

mean **0.953**, 0% invalid — no accuracy impact.

Command:
```
python3 -m sglang.launch_server --model-path <DeepSeek-R1-MXFP4> --model-impl sglang \
  --tp 8 --dp 8 --enable-dp-attention --enable-dp-lm-head --ep-size 8 \
  --scheduler-recv-interval 30 --mem-fraction-static 0.85 \
  --cuda-graph-max-bs-decode 256 --max-running-requests 256 --stream-interval 10

python3 benchmark/gsm8k/bench_sglang.py --num-questions 2000 --parallel 1200
```

## Benchmark & Profiling

Total token throughput (tok/s), baseline `--scheduler-recv-interval 1` vs
`50`; random dataset, `--random-range-ratio 0.8`, `num_prompts = 2 x conc`;
DeepSeek-R1-MXFP4 on 8xMI355X.

| Shape | conc | No-DP (TP8) 1 -> 50 | uplift | DP (TP8+DP8) 1 -> 50 | uplift |
|-------|------|---------------------|--------|----------------------|--------|
| 1k/1k | 4    | 703 -> 771          | +9.7%  | 541 -> 551           | +1.9%  |
| 1k/1k | 16   | 2110 -> 2301        | +9.1%  | 1722 -> 1712         | -0.6%  |
| 1k/1k | 64   | 5464 -> 5627        | +3.0%  | 4861 -> 5194         | +6.8%  |
| 8k/1k | 4    | 3275 -> 3372        | +2.9%  | 2001 -> 1986         | -0.7%  |
| 8k/1k | 16   | 8999 -> 9423        | +4.7%  | 5942 -> 6242         | +5.1%  |
| 8k/1k | 64   | 16859 -> 17602      | +4.4%  | 13768 -> 15768       | +14.5% |

The DP column is only runnable with this patch (baseline asserts at startup).
Largest gains at high concurrency + heavy prefill (fewer prefill
interruptions). Low-load points are within noise.

Command (per topology, interval in {1,50}):
```
# server (DP example)
python3 -m sglang.launch_server --model-path <DeepSeek-R1-MXFP4> --model-impl sglang \
  --tp 8 --dp 8 --enable-dp-attention --enable-dp-lm-head --ep-size 8 \
  --scheduler-recv-interval <1|50> --mem-fraction-static 0.85 --stream-interval 10

# benchmark (per shape/conc)
python3 -m sglang.benchmark.serving --backend sglang --dataset-name random \
  --random-input-len <1024|8192> --random-output-len 1024 --random-range-ratio 0.8 \
  --num-prompts $((conc*2)) --max-concurrency <conc>
```

## Checklist

- [x] Provide throughput/latency benchmark results and accuracy evaluation results.



























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29363627492](https://github.com/sgl-project/sglang/actions/runs/29363627492)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29363626859](https://github.com/sgl-project/sglang/actions/runs/29363626859)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
