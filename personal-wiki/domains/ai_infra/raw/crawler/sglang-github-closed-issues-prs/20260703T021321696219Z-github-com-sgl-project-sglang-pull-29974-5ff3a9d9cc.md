---
source_id: sglang-github-closed-issues-prs
title: '[Doc] Cookbook Laguna-XS-2.1: add AIME25 accuracy (B300 + GB300)'
canonical_url: https://github.com/sgl-project/sglang/pull/29974
captured_at: '2026-07-03T02:13:21.696219+00:00'
content_hash: 5ff3a9d9cc7a141e56dfed9a7259ca9b9666d87b73777d3b057f425f67ec2f2c
---
# [Doc] Cookbook Laguna-XS-2.1: add AIME25 accuracy (B300 + GB300)

URL: https://github.com/sgl-project/sglang/pull/29974
State: closed
Labels: documentation
Closed at: 2026-07-02T20:15:01Z
Merged at: 2026-07-02T20:15:01Z

## Motivation

Follow-up to #29884: adds measured **AIME25** accuracy to the Laguna-XS-2.1 cookbook's B300 and GB300 columns, next to the existing GSM8K numbers.

## Modifications

- `laguna-xs21-benchmarks.jsx`: `aime25_pct` added to all 16 verified B300/GB300 cells (H200 unchanged — not measured there), with a provenance header.
- `laguna-xs21.jsx`: `AIME25` accuracy label + reproduction command (`sgl-eval run aime25 --n-repeats 16 --max-tokens 64000 --temperature 1.0 --top-p 0.95 --thinking`). The command documents Laguna's thinking gotcha: the template gates on `enable_thinking` and ignores the generic `thinking` key sgl-eval sets, so thinking is enabled by serving with a template copy whose `enable_thinking` default is true.

## Measurements

sgl-eval `run aime25`, 30 problems × 16 repeats (480 samples/cell, SEM ~1.4pt), pass@1[avg-of-16], sglang main @ `0543246184`. B300 measured as 2×(4×GB300) tp8 over MNNVL — same GPU and shard math as one 8-GPU B300 node, matching the provenance of the existing B300 GSM8K numbers. GB300 on a 4-GPU single node at tp 4.

| quant | B300 dense | B300 DFlash | GB300 dense | GB300 DFlash |
|---|---|---|---|---|
| BF16 | 65.21 | 65.62 | 62.50 | 65.83 |
| FP8 | 61.67 | 62.50 | 63.12 | 63.12 |
| NVFP4 | 57.92 | 60.21 | 60.00 | 60.00 |
| INT4 | 63.54 | 62.92 | 64.79 | 61.04 |

DFlash is accuracy-neutral on AIME25 in every quantization (|dense−spec| ≤ 2.7pt ≈ 1–2 SEM); accept-length ~2.9 on long thinking traces. Truncation ~0% at the 64k cap.

## Checklist

- [x] Format your code with the [code formatting guide](https://github.com/sgl-project/sglang/blob/main/docs/developer_guide/contribution_guide.md#format-your-code)
- [x] Add unit tests (n/a — docs only)
- [x] Update documentation as needed

🤖 Generated with [Claude Code](https://claude.com/claude-code)





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28618460138](https://github.com/sgl-project/sglang/actions/runs/28618460138)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28618460040](https://github.com/sgl-project/sglang/actions/runs/28618460040)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
