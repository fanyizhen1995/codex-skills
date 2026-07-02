---
source_id: sglang-github-closed-issues-prs
title: '[AMD] Cover DeepSeek-R1 MXFP4 TP4 MTP nightly CI'
canonical_url: https://github.com/sgl-project/sglang/pull/29290
captured_at: '2026-07-02T02:12:27.262991+00:00'
content_hash: 4f7b34b2eb0ef9ec063d2d9d15a2592311a33729c3f61c212ca6601205257667
---
# [AMD] Cover DeepSeek-R1 MXFP4 TP4 MTP nightly CI

URL: https://github.com/sgl-project/sglang/pull/29290
State: closed
Labels: amd, deepseek
Closed at: 2026-07-01T08:21:18Z
Merged at: 2026-07-01T08:21:18Z

## Summary
- Add a MI35x nightly accuracy regression for the reported DeepSeek-R1-MXFP4 TP=4 + EAGLE/MTP GSM8K use case.
- Mirror the production launch shape: AITER backend/envs, overlap plan stream, FP8 KV cache, long context, max-running-requests=32, and multithreaded model load.
- Run full GSM8K 5-shot pressure: 1319 questions, parallel=1319, accuracy gate >= 0.944.
- Split TP4 baseline and TP4+MTP into separate workflow steps in both ROCm 7.0 and ROCm 7.2 MI35x nightly jobs.

## Use Case Covered
DeepSeek-R1-MXFP4 on MI35x with TP=4, AITER attention/MoE paths, EAGLE speculative decoding (3 steps, topk=1, 4 draft tokens), FP8 KV cache, and full GSM8K 5-shot accuracy validation.

## Testing
- Pre-commit hooks passed, including YAML validation and duplicate workflow job-name check.
- Local YAML parse and registered-test AST parse passed.
- GPU accuracy is validated by targeted MI35x nightly runs; not run locally.

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28429782492](https://github.com/sgl-project/sglang/actions/runs/28429782492)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28429782291](https://github.com/sgl-project/sglang/actions/runs/28429782291)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
