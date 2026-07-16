---
source_id: sglang-github-closed-issues-prs
title: Fix kv_b_proj channel scale broadcast when reshape hasn't run yet
canonical_url: https://github.com/sgl-project/sglang/pull/30029
captured_at: '2026-07-14T23:40:21.673327+00:00'
content_hash: 11593c08cf88ee351e20be49d2e43a53043cba42bea1e839be68dbef95f185cd
---
# Fix kv_b_proj channel scale broadcast when reshape hasn't run yet

URL: https://github.com/sgl-project/sglang/pull/30029
State: closed
Labels: 
Closed at: 2026-07-14T11:17:10Z
Merged at: 

## Motivation

Loading a Quark FP8 per-channel quantized MLA model (DeepSeek V2/V3, Kimi-K2.5, LongCat-Flash, Bailing MoE) crashes during weight loading with:

```
RuntimeError: The size of tensor a (512) must match the size of tensor b (4096) at non-singleton dimension 1
```

`post_load_weights()` calls `channel_quant_to_tensor_quant(weight, weight_scale)` on `kv_b_proj` at the end of `load_weights()`, before `quant_method.process_weights_after_loading()` has reshaped `weight_scale` from 1-D `[N]` to `[N, 1]`. The 1-D scale then broadcasts against the `[N, K]` weight along the wrong dimension.

## Modifications

- `channel_quant_to_tensor_quant` (`fp8_utils.py`): unsqueeze `x_s` to `[N, 1]` if still 1-D before the multiply. No-op if already 2-D, so no behavior change elsewhere.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28649213945](https://github.com/sgl-project/sglang/actions/runs/28649213945)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28649213714](https://github.com/sgl-project/sglang/actions/runs/28649213714)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
