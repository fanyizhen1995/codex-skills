---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Support DeepSeek V4 Flash MTP on Ascend'
canonical_url: https://github.com/sgl-project/sglang/pull/28980
captured_at: '2026-07-01T02:12:08.959882+00:00'
content_hash: a0b0e978745e0286fcacac2fe6a11dfa7b7929a395b939116e9ab696aca00197
---
# [NPU] Support DeepSeek V4 Flash MTP on Ascend

URL: https://github.com/sgl-project/sglang/pull/28980
State: closed
Labels: deepseek, npu, run-ci
Closed at: 2026-06-30T08:22:14Z
Merged at: 2026-06-30T08:22:14Z

## Motivation

Enable DeepSeek V4 Flash ModelSlim NEXTN/MTP inference on Ascend NPU.

## Modifications

- Add DSV4 compressed KV/state allocation and metadata handling for MTP target verify and graph replay.
- Route DeepSeek V4 speculative draft backends through the Ascend DSV4 backend and adapt the current spec-v2/Frozen-KV flow.
- Improve ModelSlim/compressed-tensors weight mapping and NEXTN weight loading.

## Accuracy Tests
<img width="1592" height="616" alt="gpqa-thinking-0624" src="https://github.com/user-attachments/assets/34ddbade-6bc8-4ad9-a098-dcd31dfcca97" />



Local validation completed:
- Ruff (`F401,F821,UP037`), Black, and isort passed.
- Python compilation passed.
- CPU-targeted DSV4 verify-bundle test passed.

## Speed Tests and Profiling
<img width="437" height="640" alt="benmarkResult-0624" src="https://github.com/user-attachments/assets/6a170456-3a64-4d22-a31c-b61e4efeb032" />





## Checklist

- [x] Format code with the repository-pinned Ruff, Black, and isort versions.
- [ ] Add/complete NPU unit and end-to-end tests.
- [ ] Add accuracy results.
- [ ] Add speed and profiling results.
- [x] Follow the SGLang code style guidance.







































































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28424421463](https://github.com/sgl-project/sglang/actions/runs/28424421463)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28424421259](https://github.com/sgl-project/sglang/actions/runs/28424421259)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
