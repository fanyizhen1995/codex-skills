---
source_id: sglang-github-closed-issues-prs
title: Add H200 FP8 MoE config for GLM
canonical_url: https://github.com/sgl-project/sglang/pull/29652
captured_at: '2026-07-03T02:13:21.700277+00:00'
content_hash: 6ca880b8d064d8462029b6bce5f719dafa08ab808f4585a22c7d547f0b85abfd
---
# Add H200 FP8 MoE config for GLM

URL: https://github.com/sgl-project/sglang/pull/29652
State: closed
Labels: 
Closed at: 2026-07-02T12:40:51Z
Merged at: 

## Summary

Adds the Triton 3.6.0 H200 FP8 MoE config for the GLM/Titan shape:

- `E=257,N=256,device_name=NVIDIA_H200,dtype=fp8_w8a8,block_shape=[128, 128].json`

The config is based on tuning with Triton 3.6.0, with bucket `1` kept from the existing Triton 3.5.1 fallback because it benchmarked faster for single-token MoE launches.

## Validation

- Reproduced the missing-config fallback on latest main before adding the file.
- Tuned with `benchmark/kernels/fused_moe_triton/tuning_fused_moe_triton.py --model /mnt/data/shared/docker/models/GLM-5.1-lora-nova-c371-FP8 --tp-size 8 --dtype fp8_w8a8 --tune` on H200, Triton 3.6.0.
- Verified `get_moe_configs(257, 256, "fp8_w8a8", 128, 128)` loads 18 buckets from `triton_3_6_0` without fallback.
- Ran a full non-tuning benchmark against the old fallback config; new config improved geomean kernel time by about 1.07x overall.
- Rechecked bucket `1` with the fallback bucket: repeated runs reported `31.65 us`, `35.04 us`, and `31.89 us`, with no fallback warning.
- Ran a smoke benchmark for `--batch-size 4096`; it selected the new config and reported `Kernel time: 1020.99 us` without the fallback warning.





<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28368569273](https://github.com/sgl-project/sglang/actions/runs/28368569273)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28368569116](https://github.com/sgl-project/sglang/actions/runs/28368569116)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
