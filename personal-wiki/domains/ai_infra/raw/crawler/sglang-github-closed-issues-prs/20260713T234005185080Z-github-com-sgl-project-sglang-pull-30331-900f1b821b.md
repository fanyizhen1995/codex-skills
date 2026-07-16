---
source_id: sglang-github-closed-issues-prs
title: '[Fix] Load HunyuanV3 NextN final_layernorm into the draft head''s output norm'
canonical_url: https://github.com/sgl-project/sglang/pull/30331
captured_at: '2026-07-13T23:40:05.185080+00:00'
content_hash: 900f1b821b98e7c6fa2d167119df5ada3717f723509405c89700ce31ada14698
---
# [Fix] Load HunyuanV3 NextN final_layernorm into the draft head's output norm

URL: https://github.com/sgl-project/sglang/pull/30331
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-13T12:37:37Z
Merged at: 2026-07-13T12:37:37Z

## Motivation

On released `tencent/Hy3` checkpoints, MTP speculative decoding is slower than plain decode. Root cause: the checkpoint stores the draft layer's output norm as `model.layers.80.final_layernorm.weight`, but `HYV3ForCausalLMNextN.load_weights` remaps every non-spec key under the NextN prefix to `model.decoder.<subname>`. `model.decoder.final_layernorm.weight` exists on no module, so the key is silently dropped by the `name not in params_dict` guard — and `shared_head.norm`, the RMSNorm applied immediately before the draft `lm_head`, only loads from a literal `model.shared_head.norm.weight` key that the released checkpoint does not contain. The draft head therefore runs a default-initialized output norm. The real tensor is materially non-identity (mean 1.16, range 0.81–1.23), so every draft logit is skewed and acceptance collapses.

## Modifications

- One `elif` in the NextN key remap routes `final_layernorm.*` to `model.shared_head.norm.weight`. The existing bare-key branch is kept for preview-era checkpoints.
- New unit test `test/registered/unit/models/test_hunyuan_v3_nextn_weight_loading.py` (CPU-only, mirrors the Nemotron-H exemplar) asserting the four mapping classes: `final_layernorm` → `shared_head.norm`, spec weights → `model.*`, decoder-layer keys → `model.decoder.*`, embed/lm_head skipped. The regression test fails against the unfixed source.

## Accuracy Tests

Output distribution is unchanged by construction — the fix touches only the draft model, and speculative verification is lossless. Unit tests: 4/4 pass.

## Speed Tests and Profiling

`tencent/Hy3-FP8`, TP4 on 4× RTX PRO 6000 Blackwell (SM120), SGLang 0.5.14, fp8 KV.

| Configuration | accept | decode tok/s (bs=1) |
|---|---|---|
| Plain decode (no speculation) | — | 81–86 |
| MTP before fix (EAGLE 2-1-3) | rate 0.575 | 54–56 (slower than plain) |
| MTP after fix (EAGLE 3-1-4) | length 2.3–2.6 | 87–89 (332 tok/s aggregate @ 8 streams) |

The dropped-tensor mechanism is configuration-independent.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

🤖 Generated with [Claude Code](https://claude.com/claude-code)























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29249862209](https://github.com/sgl-project/sglang/actions/runs/29249862209)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:hourglass_flowing_sand: [Run #29249862255](https://github.com/sgl-project/sglang/actions/runs/29249862255)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
