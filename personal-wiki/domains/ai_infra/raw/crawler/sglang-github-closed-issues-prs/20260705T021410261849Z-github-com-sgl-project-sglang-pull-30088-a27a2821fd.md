---
source_id: sglang-github-closed-issues-prs
title: '[DSA] Disable indexer fusion by default to restore DeepSeek-V3.2 accuracy'
canonical_url: https://github.com/sgl-project/sglang/pull/30088
captured_at: '2026-07-05T02:14:10.261849+00:00'
content_hash: a27a2821fd24d8a079a1afc7a14d78d6b8697bd3a3d674970960df55c525f082
---
# [DSA] Disable indexer fusion by default to restore DeepSeek-V3.2 accuracy

URL: https://github.com/sgl-project/sglang/pull/30088
State: closed
Labels: 
Closed at: 2026-07-04T03:50:37Z
Merged at: 2026-07-04T03:50:37Z

## Problem

`test/registered/8-gpu-models/test_deepseek_v32_indexcache.py::TestDeepseekV32IndexTopkPattern` is red on the scheduled full run: gsm8k accuracy 0.9295 / 0.9249 (threshold 0.93).

## Root cause

The DSA indexer Q/K fusion (introduced in #27705) degrades DeepSeek-V3.2 accuracy. The failing test's score tracks the `SGLANG_DISABLE_DSA_INDEXER_FUSION` default exactly:

| Scheduled run | flag | fusion | IndexTopkPattern (thr 0.93) | result |
|---|---|---|---|---|
| 0702_23 (`17cce6a85f`) | `False` | ON | ~0.938 | pass (barely) |
| 0703_11 (`42acfd1550`) | `True` | OFF | **0.9545** | pass |
| 0703_23 (`6ce02b95ad`, HEAD) | `False` | ON | **0.9295 / 0.9249** | **FAIL** |

`#30018` ("[Fix] Turn off dsa indexer fusion by default") disabled the fusion for exactly this reason. `#30025` ("reorder DSA indexer dual-stream ops…") then re-enabled it as a **bundled one-line env change**, regressing the test. The `dsa_indexer.py` stream reorder in #30025 is numerically neutral (same ops, reordered issue on the alt stream), so the accuracy delta is entirely from the env flip.

## Fix

Restore #30018's fusion-off default (revert only #30025's env flip; #30025's stream reorder stays in place and is unaffected). This returns the test to its 0.9545 passing state.

The fusion can be turned back on once its accuracy gap on DeepSeek-V3.2 is resolved. cc the #30025 / #30018 authors to confirm the stream-explosion fix does not depend on the fusion being enabled.

## Empirical validation (local, 8×H200)

Ran the exact failing config (DeepSeek-V3.2, tp8, `--enable-dp-attention`, same `index_topk_pattern` override), full 1319-question / 20-shot gsm8k, with `/flush_cache` before every run, 5 runs per setting:

| Run | fusion OFF (`DISABLE=1`) | fusion ON (`DISABLE=0`) |
|---|---|---|
| 1 | 0.9553 | 0.9310 |
| 2 | 0.9568 | 0.9303 |
| 3 | 0.9530 | 0.9287 |
| 4 | 0.9583 | 0.9295 |
| 5 | 0.9530 | 0.9333 |
| **mean** | **0.9553** | **0.9306** |
| min–max | 0.9530–0.9583 | 0.9287–0.9333 |

Fusion OFF clears the 0.93 threshold every time (min 0.9530); fusion ON straddles it (3/5 barely pass at 0.930–0.933, 2/5 fail at 0.9287 / 0.9295) — reproducing the flaky CI history. The ~2.5-point gap is consistent and the two ranges do not overlap, so this is a real accuracy regression from the fusion, not eval noise.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
