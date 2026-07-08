---
source_id: sglang-github-closed-issues-prs
title: '[Cherry pick to release/v0.5.15] Fix NVFP4 online quantization'
canonical_url: https://github.com/sgl-project/sglang/pull/30397
captured_at: '2026-07-07T23:35:30.904552+00:00'
content_hash: 738afb3742e44a5a016d5780766c61ed121961cc03ad47d762444debd6fe7356
---
# [Cherry pick to release/v0.5.15] Fix NVFP4 online quantization

URL: https://github.com/sgl-project/sglang/pull/30397
State: closed
Labels: blackwell, cherry-pick
Closed at: 2026-07-07T20:20:37Z
Merged at: 2026-07-07T20:20:37Z

`test/registered/backends/test_flashinfer_trtllm_gen_moe_backend.py`
`AttributeError: 'NvFp4OnlineConfig' object has no attribute 'dequant_fp4_to_fp8'`

It's broken by https://github.com/sgl-project/sglang/pull/27867















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28869009529](https://github.com/sgl-project/sglang/actions/runs/28869009529)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28869008915](https://github.com/sgl-project/sglang/actions/runs/28869008915)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
