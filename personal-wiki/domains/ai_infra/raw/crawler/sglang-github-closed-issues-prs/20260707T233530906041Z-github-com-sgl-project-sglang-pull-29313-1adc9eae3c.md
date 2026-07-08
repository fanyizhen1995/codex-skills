---
source_id: sglang-github-closed-issues-prs
title: '[AMD] [GLM5] Mark EAGLE verified on MI300X/MI325X (gfx942) in GLM-5.1 cookbook'
canonical_url: https://github.com/sgl-project/sglang/pull/29313
captured_at: '2026-07-07T23:35:30.906041+00:00'
content_hash: 1adc9eae3c708fc289430b2fb474d1e1a9e251f3aaa56259aa49e558088e6545
---
# [AMD] [GLM5] Mark EAGLE verified on MI300X/MI325X (gfx942) in GLM-5.1 cookbook

URL: https://github.com/sgl-project/sglang/pull/29313
State: closed
Labels: documentation
Closed at: 2026-06-26T02:49:58Z
Merged at: 2026-06-26T02:49:58Z

## Motivation

Follow-up to #29194, which enabled EAGLE for gfx950 (MI355X) in the GLM-5.1
cookbook but left gfx942 (MI300X/MI325X) marked "unverified" — both in the
prose and in the deploy generator, which excluded the EAGLE flags for those
GPUs. EAGLE speculative decoding has since been verified on gfx942.

## Modifications

- `GLM-5.1.mdx`: AMD note now states EAGLE is supported on all AMD GPUs
  (MI300X/MI325X (gfx942) and MI355X (gfx950)). Added the EAGLE flags to the
  static AMD FP8 and BF16 server-command blocks.
- `glm-51-deployment.jsx`: the deploy generator now emits the EAGLE flags on
  MI300X/MI325X as well (removed the gfx942 exclusion).

## Important: EAGLE on AMD requires `--disable-custom-all-reduce`

EAGLE on AMD GPUs **must** be run with `--disable-custom-all-reduce`. The aiter
custom all-reduce kernel (`aiter::cross_device_reduce_2stage`) deadlocks during
the EAGLE target-verify step at high concurrency (reproduced hanging at c>=16
for the (4,1,5) config and c>=32 for (3,1,4) on gfx950/MI355X). The GPU kernel
busy-waits forever on cross-device signal flags and the server hangs with no
recovery. Disabling the custom all-reduce falls back to RCCL, which resolves the
hang with negligible performance impact. This was diagnosed via py-spy + rocgdb,
correlating stuck host-to-device copies with the spinning all-reduce kernel.

Accordingly:
- `GLM-5.1.mdx`: the AMD GPU note now documents that EAGLE requires
  `--disable-custom-all-reduce` or the server will hang at high concurrency, and
  the flag was added to all three AMD EAGLE server-command blocks (MXFP4 / FP8 / BF16).
- `glm-51-deployment.jsx`: the deploy generator now emits
  `--disable-custom-all-reduce` whenever AMD hardware is selected with EAGLE.

## Checklist

- [x] Format with pre-commit
- [x] Documentation builds (Mintlify)

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28208347566](https://github.com/sgl-project/sglang/actions/runs/28208347566)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28208347497](https://github.com/sgl-project/sglang/actions/runs/28208347497)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
