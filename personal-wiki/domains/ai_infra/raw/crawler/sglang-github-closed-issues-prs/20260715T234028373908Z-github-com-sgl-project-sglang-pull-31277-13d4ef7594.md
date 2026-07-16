---
source_id: sglang-github-closed-issues-prs
title: '[DO NOT MERGE] Revert #31001 to test GLM-5.2-NVFP4 bs_1_speed regression'
canonical_url: https://github.com/sgl-project/sglang/pull/31277
captured_at: '2026-07-15T23:40:28.373908+00:00'
content_hash: 13d4ef7594f1349f52d55dedef41682572baaf63ee5ac65857d39eb874b66e91
---
# [DO NOT MERGE] Revert #31001 to test GLM-5.2-NVFP4 bs_1_speed regression

URL: https://github.com/sgl-project/sglang/pull/31277
State: closed
Labels: deepseek
Closed at: 2026-07-15T07:20:21Z
Merged at: 

## ⚠️ DO NOT MERGE — CI experiment only

This reverts #31001 ("Fix GLM/DeepSeek NVFP4 + flashinfer_trtllm long-context `!!!!` collapse (NaN routing)", commit `f49cbbd`) **solely to confirm on CI** that it is the source of the `test_dsa_glm52_nvfp4_tp_mtp.py` `test_bs_1_speed` failure in the scheduled full runs.

## Background
The `base-c-test-4-gpu-b200` scheduled runs started failing at `test_bs_1_speed` beginning with the run that tested `cfc3d05` (first red), while `eb31b531` (previous scheduled run) was green.

CI symptom: the `bs=1` greedy generation collapsed from **1182 tokens → 347 tokens** (accept length **4.599 → 4.284**). Since the metric is `speed = completion_tokens / e2e_latency`, the much shorter output is dominated by fixed prefill/warmup overhead and falls under the `300 tok/s` gate (~295 on the runner).

## Local A/B (revert-on-`cfc3d05`, exact fixture args)
| Config | Acc length | Speed (tok/s) | Latency (s) | Tokens |
|--------|-----------:|--------------:|------------:|-------:|
| `cfc3d05` as-is | 4.284 | 341 | 1.02 | 347 |
| `cfc3d05` − revert #29151 | 4.284 | 340 | 1.02 | 347 (no change) |
| `cfc3d05` − revert **#31001** | **4.599** | 392 | 3.02 | **1182** (restored) |

Reverting **#31001** restores the pre-regression generation exactly; reverting #29151 (ModelOpt NVFP4 merged-linear scales) does nothing.

## Why not just merge this
#31001 is a genuine fix — without it, `modelopt_fp4` + `flashinfer_trtllm` hits NaN routing on exact ties and produces `!!!!` collapse in long context. The bf16 routing-bias cast has the *side effect* of changing this short-prompt greedy generation length. The real follow-up is to decide whether that routing change is expected and/or make the `bs_1_speed` check robust to output length. This PR is only to validate the root cause on CI.

Made with [Cursor](https://cursor.com)









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29389687076](https://github.com/sgl-project/sglang/actions/runs/29389687076)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29389686960](https://github.com/sgl-project/sglang/actions/runs/29389686960)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
