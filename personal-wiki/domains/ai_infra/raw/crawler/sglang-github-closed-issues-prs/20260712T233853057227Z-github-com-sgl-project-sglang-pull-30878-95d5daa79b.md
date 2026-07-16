---
source_id: sglang-github-closed-issues-prs
title: 'perf: reuse MoonViT FA3 max-seqlen metadata'
canonical_url: https://github.com/sgl-project/sglang/pull/30878
captured_at: '2026-07-12T23:38:53.057227+00:00'
content_hash: 95d5daa79bd11e467901367f6a50449e112a82f02740d7d500ff5012c6f613af
---
# perf: reuse MoonViT FA3 max-seqlen metadata

URL: https://github.com/sgl-project/sglang/pull/30878
State: closed
Labels: Multi-modal, run-ci
Closed at: 2026-07-12T06:05:21Z
Merged at: 2026-07-12T06:05:21Z

## Summary

- compute Kimi K2.5/K2.6/K2.7 MoonViT max sequence length once per encoder forward
- pass the scalar to every FA3 vision-attention block, eliminating repeated GPU-to-host synchronizations
- add a CPU regression test for both the generic FA3 path and Kimi MoonViT forwarding

## Performance (before → after)

Isolated ViT microbenchmark using the official Kimi-K2.7-Code MoonViT config (27 layers; 2 images × 64×64 patch grid), H100 80GB, TP1, BF16, `--mm-attention-backend fa3`, 5 warmup + 20 measured iterations:

| Metric | main | this PR | Change |
| --- | ---: | ---: | ---: |
| ViT median | 32.13 ms | 31.08 ms | -3.27% |
| ViT mean | 32.14 ms | 31.07 ms | -3.35% |

This is an encoder-only measurement with random weights, intended to isolate the removed per-block synchronization. It is not an end-to-end serving claim. The H200 TP8 K2.7 random-image serving matrix is now available separately; it is not included here because this PR does not have a matching unoptimized end-to-end A/B run.





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29154504620](https://github.com/sgl-project/sglang/actions/runs/29154504620)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29154504579](https://github.com/sgl-project/sglang/actions/runs/29154504579)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
