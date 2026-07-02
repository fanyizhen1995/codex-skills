---
source_id: sglang-github-closed-issues-prs
title: Add --mamba-ssm-enable-stochastic-rounding for GDN and Mamba1/2 decode
canonical_url: https://github.com/sgl-project/sglang/pull/27975
captured_at: '2026-07-01T02:12:08.973158+00:00'
content_hash: 23ae823e74babb9b64a0c03785df91dd6e1d8dacf292009e1b1ed8a89d727c30
---
# Add --mamba-ssm-enable-stochastic-rounding for GDN and Mamba1/2 decode

URL: https://github.com/sgl-project/sglang/pull/27975
State: closed
Labels: 
Closed at: 2026-06-29T22:32:18Z
Merged at: 

Add hardware stochastic rounding (PTX cvt.rs, SM100+/Blackwell) for the recurrent state store in GDN (gated delta network) and Mamba1/Mamba2 decode kernels. When --mamba-ssm-dtype is float16 or bfloat16, the fp32 accumulated state is rounded stochastically instead of round-to-nearest, reducing systematic quantization bias in the recurrent state cache.

## Motivation

Enable stochastic rounding for GDN and Mamaba1/Mamba2 float16/bfloat16 state cache to improve model accuracy.

## Modifications

New module stochastic_round.py: Triton inline-asm helpers for cvt.rs.{f16x2,bf16x2}.f32 + rs_round_state wrapper. Seed loaded from device memory for CUDA-graph capturability.

Kernel changes (decode store epilogue):
- fused_recurrent.py: GDN packed decode
- chunk_delta_h.py: GDN prefill (INPLACE_UPDATE epilogue)
- gdn_triton.py: GDN decode dispatch (seed generation)
- mamba_ssm.py: Mamba1/Mamba2 selective_state_update
- ssu_dispatch.py: SR params threaded through dispatch layer
- mamba.py: seed generation in Mamba decode path

Flags: --mamba-ssm-enable-stochastic-rounding (store_true), --mamba-ssm-philox-rounds (default 10). Guards: requires SM100+, Triton, --mamba-ssm-dtype float16/bfloat16, no speculative decoding.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #27383212210](https://github.com/sgl-project/sglang/actions/runs/27383212210)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27383212128](https://github.com/sgl-project/sglang/actions/runs/27383212128)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
