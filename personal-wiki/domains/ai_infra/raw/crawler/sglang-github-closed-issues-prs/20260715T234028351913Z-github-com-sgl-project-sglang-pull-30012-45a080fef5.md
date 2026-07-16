---
source_id: sglang-github-closed-issues-prs
title: '[DSv4] Use BF16 instead of FP32 for indexer score computation'
canonical_url: https://github.com/sgl-project/sglang/pull/30012
captured_at: '2026-07-15T23:40:28.351913+00:00'
content_hash: 45a080fef5f17c335ff85e9a4b79fd278a3716016824dcf93fb14a9e2897d3a9
---
# [DSv4] Use BF16 instead of FP32 for indexer score computation

URL: https://github.com/sgl-project/sglang/pull/30012
State: closed
Labels: 
Closed at: 2026-07-15T22:06:56Z
Merged at: 2026-07-15T22:06:56Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

Switch the sparse MLA indexer's QK score BMM from FP32 to BF16, enabling Tensor Core (WMMA) dispatch instead of FP32 SIMT SGEMM.

    This eliminates:
    - FP32 SIMT SGEMM (cutlass_80_simt_sgemm): 408ms -> 95ms via Tensor Core
    - Associated BF16<->FP32 dtype conversion copies: ~190ms -> 0ms
    
    Benchmarks on 8x RTX PRO 5000 72GB (DeepSeek-V4 Flash, TP8):
    - E2E serving (cc=8, in=4096, out=150): +19% output throughput
    - E2E serving (cc=16): +24% output throughput, -21% TPOT latency
    - Math/reasoning accuracy verified: no degradation

## Modifications



## Accuracy Tests
Use bench_serving to test E2E performance.
<img width="1284" height="248" alt="image" src="https://github.com/user-attachments/assets/56d1f142-ea4d-41d2-8960-ab7afad6d314" />



## Speed Tests and Profiling

Profile clearly display different kernel when changing FP32 to BF16
<img width="1602" height="172" alt="image" src="https://github.com/user-attachments/assets/4cb9cd4c-e07f-45c1-925a-94da188cb070" />

Precision is tested via aime 2026 Math test with fixed seed and temperature.
<img width="2174" height="938" alt="image" src="https://github.com/user-attachments/assets/93784f55-f16e-4621-9e0e-a18801602627" />



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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28642682834](https://github.com/sgl-project/sglang/actions/runs/28642682834)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28642682736](https://github.com/sgl-project/sglang/actions/runs/28642682736)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
