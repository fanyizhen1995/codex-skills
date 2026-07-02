---
source_id: sglang-github-closed-issues-prs
title: '[DeepSeek V4] Enable FlashMLA sparse prefill by default'
canonical_url: https://github.com/sgl-project/sglang/pull/29775
captured_at: '2026-07-02T02:12:27.253733+00:00'
content_hash: 7facec98231b7268132b86ca495ab64c3c976f279d6737f49844053ac4b82106
---
# [DeepSeek V4] Enable FlashMLA sparse prefill by default

URL: https://github.com/sgl-project/sglang/pull/29775
State: closed
Labels: deepseek, release-highlight
Closed at: 2026-07-01T20:50:05Z
Merged at: 2026-07-01T20:50:05Z

## Motivation

FlashMLA sparse prefill improves DeepSeek V4 server-side prefill throughput across the tested input lengths under saturated serving load. Enable the existing path by default while preserving the existing size-based selection policy when the flag is explicitly disabled.

## Modifications

Change the default value of `SGLANG_OPT_FLASHMLA_SPARSE_PREFILL` from `false` to `true`. Setting it to `0` restores the existing size-based selector; queries above the existing threshold continue to select sparse prefill as before.

## Accuracy Tests

No kernel or model-forward implementation is changed. Verified that the flag resolves to `true` when unset and still resolves to `false` when explicitly disabled.

## Speed Tests and Profiling

Measured on GB300 with TP4 / DP4 / EP4 prefill, DP attention, FP8 KV cache, an 8,192-token prefill chunk per rank, and persistent request backlog. Each 1K–16K arm uses a fixed 300-second measurement window with zero failed requests and zero cached tokens.

| Nominal ISL | Global concurrency | OFF TPS/rank | ON TPS/rank | Gain | Replay gain |
|---:|---:|---:|---:|---:|---:|
| 1K | 128 | 15,818.18 | 16,485.28 | **+4.217%** | +4.242% |
| 8K | 64 | 13,870.58 | 14,813.02 | **+6.795%** | +6.883% |
| 16K | 64 | 13,464.29 | 14,545.99 | **+8.034%** | +7.914% |
| 128K | 8 | 10,493 | 11,792 | **+12.4%** | — |

The maximum difference between the primary and replay gains for the 1K–16K measurements is 0.12 percentage points. The performance claim is scoped to the validated GB300 serving configurations shown above. This remains a draft while underfilled batches, SM120, and prefill context parallelism are outside the current safety-validation scope.

## Checklist

- [x] `pre-commit run --files python/sglang/srt/environ.py`
- [x] Verified default-on and explicit-false flag behavior.
- [x] No documentation update is required; the existing flag remains unchanged.



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28544931569](https://github.com/sgl-project/sglang/actions/runs/28544931569)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #28546902349](https://github.com/sgl-project/sglang/actions/runs/28546902349)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
