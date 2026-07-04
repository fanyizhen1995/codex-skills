---
source_id: sglang-github-closed-issues-prs
title: Support DSV4 shared expert fusion for DeepEP and MegaMOE
canonical_url: https://github.com/sgl-project/sglang/pull/27349
captured_at: '2026-07-04T02:13:49.137859+00:00'
content_hash: 8a4103a6a5340fb341e058b651295e34e24f4d52b9c7cb8d27e10c33c1bc2f40
---
# Support DSV4 shared expert fusion for DeepEP and MegaMOE

URL: https://github.com/sgl-project/sglang/pull/27349
State: closed
Labels: documentation, deepseek, run-ci, bypass-fastfail
Closed at: 2026-07-03T06:18:25Z
Merged at: 2026-07-03T06:18:25Z

## Summary
- support DeepSeek V4 shared expert fusion with per-rank shared expert slots for both DeepEP-class and MegaMOE backends
- extend TopK/HashTopK post-processing and fused MoE weight loading to handle the shared expert physical slot layout
- add shared expert FP8-to-FP4 load-time quantization for fused FP4 MoE weights

## Scope
This PR focuses on DeepSeek V4 shared expert fusion compatibility for DeepEP and MegaMOE backends, including the shared expert quantization needed by the fused path. It does not change Waterfill backend selection and does not add DeepSeek V3 MegaMOE shared expert fusion support.

## Testing
- python -m compileall -q python/sglang/srt/layers/moe/fused_moe_triton/layer.py python/sglang/srt/layers/moe/hash_topk.py python/sglang/srt/layers/moe/topk.py python/sglang/srt/layers/moe/utils.py python/sglang/srt/models/deepseek_v2.py python/sglang/srt/models/deepseek_v4.py python/sglang/srt/layers/quantization/mxfp4_tensor.py
- git diff --check

### Accuracy validation: DSV4 MMLU

| Case | Requests | Accuracy |
|---|---:|---:|
| MegaMOE unfused | 14042 | 0.858 |
| MegaMOE fused | 14042 | 0.860 |
| DeepEP unfused | 14042 | 0.859 |
| DeepEP fused | 14042 | 0.861 |
| DeepEP waterfill | 14042 | 0.857 |
| MegaMOE waterfill | 14042 | 0.858 |



































































































































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28586581745](https://github.com/sgl-project/sglang/actions/runs/28586581745)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28586581628](https://github.com/sgl-project/sglang/actions/runs/28586581628)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
