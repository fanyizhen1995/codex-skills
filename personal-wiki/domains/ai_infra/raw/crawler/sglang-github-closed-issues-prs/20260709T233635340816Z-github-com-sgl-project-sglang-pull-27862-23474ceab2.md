---
source_id: sglang-github-closed-issues-prs
title: Support speculative decoding on CPU
canonical_url: https://github.com/sgl-project/sglang/pull/27862
captured_at: '2026-07-09T23:36:35.340816+00:00'
content_hash: 23474ceab28df9c32716a69b464b1565d6c30c4f424fb49824fc80d7d512b8c7
---
# Support speculative decoding on CPU

URL: https://github.com/sgl-project/sglang/pull/27862
State: closed
Labels: speculative-decoding, sgl-kernel, intel, cpu, run-ci
Closed at: 2026-07-09T02:27:10Z
Merged at: 2026-07-09T02:27:10Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

Add initial speculative decoding support to the CPU backend. `EAGLE2`, `MTP`, `N-Gram` and `Standalone` algorithm are supported in this initial MVP PR.

## Modifications

<!-- Detail the changes made in this pull request. -->

- New CPU kernels in sgl-kernel (mainly `sgl-kernel/csrc/cpu/spec.cpp`) to support tree build/verify, cache-location management, draft-decode metadata, etc.
- TARGET_VERIFY / DRAFT_EXTEND support in the Intel AMX attention backend; CPU dispatch in the EAGLE V2 worker paths (GPU launches unchanged).
- Server-arg guards for unsupported CPU combinations (radix cache with mamba `no_buffer`, `topk > 1` for hybrid GDN models).
- Small device-guard crash fixes in model files.
- Unit tests: `test/srt/cpu/test_spec_kernels.py`.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

MMLU tested on a GNR-AP Q42E (2S x 120 cores) machine shows no regression:

| Model | upstream baseline | PR baseline | SD |
|---|---|---|---|
| Llama-2-7b-chat + EAGLE2 | 0.408 | 0.408 | 0.411 |
| Qwen3-Next-80B + MTP | 0.855 | 0.858 | 0.858 |

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

Configuration:
- CPU machine: GNR-AP Q42E (2S x 120 cores), DDR5 64GB x 24 (1,229 GB/s theoretical bandwidth)
- 
| Algorithm | Model | Draft | Config | Decode tok/s | Speedup | Accept len |
|---|---|---|---|---|---|---|
| Baseline | Llama-2-7b | - | - | 42.3 | 1.00 | - |
| **EAGLE2** | Llama-2-7b | sglang-EAGLE-llama2-chat-7B | topk=4, steps=3, dt=16 | 63.3 | 1.50 | 2.80 |
| Baseline | Qwen2.5-7B | - | - | 42.6 | 1.00 | - |
| **N-Gram** | Qwen2.5-7B | - | dt=16, bfs=10 | 47.3 | 1.11 | 1.57 |
| Baseline | MiMo-7B | - | - | 36.6 | 1.00 | - |
| **MTP** | MiMo-7B | - | steps=1, dt=2 | 42.9 | 1.17 | 1.55 |
| Baseline | Qwen2.5-3B | - | - | 53.2 | 1.00 | - |
| **Standalone** | Qwen2.5-3B | Qwen2.5-0.5B-Instruct | steps=4, dt=5 | 53.6 | 1.01 | 3.42 |

All benchmarks use a constant seed=42 for reproducible SD behavior.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.













































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28927557622](https://github.com/sgl-project/sglang/actions/runs/28927557622)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28927557317](https://github.com/sgl-project/sglang/actions/runs/28927557317)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
