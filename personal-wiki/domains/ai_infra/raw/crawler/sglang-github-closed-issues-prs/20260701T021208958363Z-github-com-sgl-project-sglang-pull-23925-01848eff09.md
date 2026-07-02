---
source_id: sglang-github-closed-issues-prs
title: '[NPU]use triton split_qkvgate_gemma_rmsnorm_rope for Qwen3.5 and Qwen3_next'
canonical_url: https://github.com/sgl-project/sglang/pull/23925
captured_at: '2026-07-01T02:12:08.958363+00:00'
content_hash: 01848eff09eb989641d2412460b05c42c6764ece1ef34aa604dd87e2ec413f7e
---
# [NPU]use triton split_qkvgate_gemma_rmsnorm_rope for Qwen3.5 and Qwen3_next

URL: https://github.com/sgl-project/sglang/pull/23925
State: closed
Labels: run-ci
Closed at: 2026-05-20T12:22:11Z
Merged at: 2026-05-20T12:22:11Z

## Motivation

For Qwen3.5(3.6) and Qwen3_Next, we implemented a kernel fusion for the attention layer's split_qkv, norm, and embedding_rope operations into a single Triton kernel to boost performance.

## Modifications

For Qwen3.5 and Qwen3_Next, we implemented a kernel fusion for the attention layer's split_qkv, norm, and embedding_rope operations into a single Triton kernel to boost performance.

## Accuracy Tests

qwen3.6-35b:
<img width="963" height="395" alt="image" src="https://github.com/user-attachments/assets/d3ac825d-2aee-43f9-8462-e837aee85fbd" />

## Speed Tests and Profiling
qwen3.6-35b:
before:
<img width="1942" height="442" alt="image" src="https://github.com/user-attachments/assets/9d9ae4a3-9116-4e65-a00b-022f3459ce31" />

after:
1st attn layer:
<img width="1436" height="462" alt="image" src="https://github.com/user-attachments/assets/bd9c2d5d-32b9-4d15-b62c-70640fb72918" />


other attn layers:
<img width="618" height="304" alt="image" src="https://github.com/user-attachments/assets/e120301a-96d1-4938-83f7-450ea9ef0b9f" />



Only the first attention layer requires the additional get_cos_sin_with_position computation; all subsequent layers can simply reuse the previous cache. The performance gain is shown above.

gpu kernel test:
<img width="1720" height="277" alt="image" src="https://github.com/user-attachments/assets/b15c00ae-0e63-491a-b718-6364664a5f86" />
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #26074692794](https://github.com/sgl-project/sglang/actions/runs/26074692794)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:warning: **Not enabled** -- add `run-ci-extra` label to opt in.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
