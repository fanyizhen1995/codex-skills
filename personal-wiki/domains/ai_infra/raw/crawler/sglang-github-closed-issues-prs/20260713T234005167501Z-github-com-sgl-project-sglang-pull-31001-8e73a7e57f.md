---
source_id: sglang-github-closed-issues-prs
title: Fix GLM/DeepSeek NVFP4 + flashinfer_trtllm long-context "!!!!" collapse (NaN
  routing)
canonical_url: https://github.com/sgl-project/sglang/pull/31001
captured_at: '2026-07-13T23:40:05.167501+00:00'
content_hash: 8e73a7e57fd59112d5d19ac1415547a29b07199ff8d9f9e6f84c90efbf106887
---
# Fix GLM/DeepSeek NVFP4 + flashinfer_trtllm long-context "!!!!" collapse (NaN routing)

URL: https://github.com/sgl-project/sglang/pull/31001
State: closed
Labels: high priority, deepseek, post version patch
Closed at: 2026-07-13T19:54:39Z
Merged at: 2026-07-13T19:54:39Z

## Motivation

Fixes #30989.

Serving `nvidia/GLM-5.2-NVFP4` with `--quantization modelopt_fp4 --moe-runner-backend flashinfer_trtllm`, long-context requests return nothing but `!!!!!!...` (every output-token logprob is `null`, i.e. NaN). Short requests and FP8 checkpoints are unaffected.

### Root cause

`MoEGate.__init__` creates `e_score_correction_bias` as **fp32** for `modelopt_fp4`, and the FP4 moe_runner passes it **unconverted** to flashinfer's `trtllm_fp4_block_scale_moe` as `routing_bias` — whose documented contract requires `bfloat16` (the kernel does not validate the dtype). With an fp32 bias, flashinfer's DeepSeekV3 routing kernel emits NaN expert weights when several experts' selection keys `sigmoid(logit) + bias` are bitwise-equal and the tie group straddles the top-k boundary.

GLM-5.2-NVFP4 makes such exact ties inevitable: its bias has only 196/256 unique values (all ≈ 11.13–11.32), and on long-context tokens whose 256 router logits are all very negative, the tiny `sigmoid` contributions fall below the fp32 ulp of the ~11.3 bias and vanish in the addition — so the key collapses to a duplicated bias value → bitwise tie at the top-8 boundary → NaN. The NaN propagates to all logits; greedy argmax degenerates to token id 0, which is `!` in GLM's vocab.

This is a regression from #29783, which removed the bf16 cast for `modelopt_fp4 + flashinfer_trtllm`. The FP8 path already casts the bias to bf16 in `moe_runner/flashinfer_trtllm.py`; the FP4 path passes it raw.

### Fix

Restore the bf16 dtype for the correction bias on `modelopt_fp4 + flashinfer_trtllm` (mirrors the FP8 path). The coarse bf16 quantization (ulp 0.0625 at 11.3) spaces bias values far wider than any sigmoid contribution, so no exact tie can form. The root defect (tie-handling + missing dtype validation) belongs in flashinfer's `routingCustom`.

## Reproduction & verification

Reproduced on 4×B300 (SM 10.3), flashinfer 0.6.12, torch 2.11.0+cu130, with the exact launch command and the issue's pinned `openai/graphwalks` probe.

**Before (buggy `main`):**
```
chars=  10000  COLLAPSED  out='!!!!...!'  null_logprobs=40/40
chars=  20000  COLLAPSED  out='!!!!...!'  null_logprobs=40/40
chars=  40000  COLLAPSED  out='!!!!...!'  null_logprobs=40/40
chars=  80000  COLLAPSED  out='!!!!...!'  null_logprobs=40/40
RESULT: reproduced
```

**After (this PR):**
```
chars=  10000  ok  out='1.  **Analyze the Request:**...'  null_logprobs=0/40
chars=  20000  ok  out='The user wants me to reply with the sing'  null_logprobs=0/16
chars=  40000  ok  out='The user is asking me to reply with the ' null_logprobs=0/17
chars=  80000  ok  out='The user is asking me to reply with the ' null_logprobs=0/17
RESULT: not reproduced
```

## Checklist

- [x] Reproduced the bug and verified the fix on real hardware (4×B300, `nvidia/GLM-5.2-NVFP4`).
- [x] Change is minimal and mirrors the existing FP8 path.

🤖 Generated with [Claude Code](https://claude.com/claude-code)





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29234847866](https://github.com/sgl-project/sglang/actions/runs/29234847866)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #29236132036](https://github.com/sgl-project/sglang/actions/runs/29236132036)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
