---
source_id: sglang-github-closed-issues-prs
title: '[CI] Flaky low GSM8K score in disaggregation hybrid attention Mamba test'
canonical_url: https://github.com/sgl-project/sglang/issues/30946
captured_at: '2026-07-13T23:40:05.149879+00:00'
content_hash: 2a77726f0a04dc0bf16518f297c1f43dc16c2c66d5c6bd28bf96f4067ec2da04
---
# [CI] Flaky low GSM8K score in disaggregation hybrid attention Mamba test

URL: https://github.com/sgl-project/sglang/issues/30946
State: closed
Labels: 
Closed at: 2026-07-13T05:10:25Z
Merged at: 

## Summary

`test/registered/disaggregation/test_disaggregation_hybrid_attention.py` intermittently fails on scheduled `main` runs in `extra-b-test-8-gpu-h200`, specifically:

```text
TestDisaggregationHybridAttentionMamba.test_gsm8k
AssertionError: <score> not greater than 0.87
model: nvidia/NVIDIA-Nemotron-Nano-9B-v2
```

This test is flaky / low-margin, so please do not treat the most recent 8-commit window as the only possible regression range. There are passing scheduled runs between low-score failures, and many passes are only slightly above the threshold (`0.88`-`0.90`).

## Evidence

Recent recurrence:

| Date | Run | SHA | Runner | Result |
| --- | --- | --- | --- | --- |
| 2026-07-11 | [29171938366 / job 86620456655](https://github.com/sgl-project/sglang/actions/runs/29171938366/job/86620456655) | `4884f6fbee` | `h200-gmi-wk01` | PASS, Mamba scores `0.895`, `0.900` |
| 2026-07-12 | [29190816712 / job 86645077403](https://github.com/sgl-project/sglang/actions/runs/29190816712/job/86645077403) | `80856aba85` | `h200-rdxa-51-3` | FAIL, scores `0.630`, retry/final `0.605` |

Older matching hard failure:

| Date | Run | SHA | Runner | Result |
| --- | --- | --- | --- | --- |
| 2026-06-22 | [27991231551 / job 82867931208](https://github.com/sgl-project/sglang/actions/runs/27991231551/job/82867931208) | `e00703bb2a` | `h200-gmi-wk03` | PASS, Mamba scores `0.925`, `0.920` |
| 2026-06-23 | [28024716824 / job 82949553346](https://github.com/sgl-project/sglang/actions/runs/28024716824/job/82949553346) | `0460f277b7` | `h200-rdxa-51-3` | FAIL, scores `0.845`, retry/final `0.720` |

Additional context from scheduled runs:

- 2026-06-24 to 2026-07-11 contains many passing runs, often with Mamba scores around `0.89`-`0.93`.
- A low-margin pass was observed at [27346429443 / job 80796287174](https://github.com/sgl-project/sglang/actions/runs/27346429443/job/80796287174) with score `0.880`.
- Passes and failures are both seen on H200 runners; this is not obviously isolated to one runner name.

## Commit Ranges

Because the test is flaky, use the larger range for investigation:

```text
e00703bb2a6346e3188fffef7bb77c60db9a0ddc..80856aba85c60eb8a5ffe294132cc76acf7af67f
```

Compare link:
https://github.com/sgl-project/sglang/compare/e00703bb2a6346e3188fffef7bb77c60db9a0ddc...80856aba85c60eb8a5ffe294132cc76acf7af67f

This broad range is about 745 commits and intentionally includes the older matching failure plus the latest recurrence.

First observed hard-fail subrange:

```text
e00703bb2a6346e3188fffef7bb77c60db9a0ddc..0460f277b770f8b5a404da2e50e7a9573ef8db40
```

Compare link:
https://github.com/sgl-project/sglang/compare/e00703bb2a6346e3188fffef7bb77c60db9a0ddc...0460f277b770f8b5a404da2e50e7a9573ef8db40

Latest recurrence tight subrange:

```text
4884f6fbee196f7846b82dbb59db5a4135a4f778..80856aba85c60eb8a5ffe294132cc76acf7af67f
```

Compare link:
https://github.com/sgl-project/sglang/compare/4884f6fbee196f7846b82dbb59db5a4135a4f778...80856aba85c60eb8a5ffe294132cc76acf7af67f

## Possible Candidate Commits

From the first hard-fail subrange, these commits touch areas that could plausibly affect disaggregation, radix/cache state, scheduling, CUDA graph, or TP/allreduce behavior:

```text
0460f277b7 2026-06-23 Fix manual chunked-prefill test to use req.fill_len after fill_ids refactor (#29032)
e67b228d4c 2026-06-23 feat: session radix cache (#27058)
349a6af6b8 2026-06-23 [HiCache] Fix hicache host memory leak by bounding PP-sync work_list (#28916)
7b1a20344c 2026-06-23 Re-enable SM90 FlashInfer allreduce fusion with safe backend defaults (#28789)
854c688121 2026-06-23 [Spec] Unify decode KV-commit bookkeeping across spec-v2 workers (#28754)
c4376aaa88 2026-06-23 [Refactor] Remove dead out_cache_loc_swa buffers (#28968)
62f7ffc492 2026-06-22 feat: add Mooncake group semantics (#26574)
de3ec2c437 2026-06-22 [server_args] compute mem_fraction_static after dp chunked-prefill division (#28884)
4740f23e1f 2026-06-22 Revert "[server_args] compute mem_fraction_static after dp chunked-prefill division" (#28991)
```

From the latest recurrence subrange, the runtime-ish candidates are:

```text
80856aba85 2026-07-12 Make the mxfp8 MoE runner backend list extensible (#30828)
81d273f73b 2026-07-12 Handle coredump dirs and cache hit updates (#30897)
f1c247edf9 2026-07-12 profile: add vlm prefill profiler ranges (#30871)
bce3fc987d 2026-07-12 perf: reuse MoonViT FA3 max-seqlen metadata (#30878)
```

The latest recurrence could be unrelated to these commits because the same signature appeared earlier and then passed many times afterward.

## Suggested Next Steps

1. Reproduce `TestDisaggregationHybridAttentionMamba.test_gsm8k` repeatedly on an H200 runner with the same CI command/env.
2. Compare TP=1 vs TP=4, and disable prefill/decode CUDA graph as controls.
3. Check whether output degradation correlates with radix/Mamba state reuse, disaggregated KV transfer, or FlashInfer allreduce fusion.
4. Consider marking the test flaky or raising diagnostic logging around Nemotron-Nano Mamba state transfer until root cause is found.
