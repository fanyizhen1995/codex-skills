---
source_id: sglang-github-closed-issues-prs
title: '[AMD] fix dsv4 indexer dtype dispatch on gfx950'
canonical_url: https://github.com/sgl-project/sglang/pull/29479
captured_at: '2026-07-09T23:36:35.330587+00:00'
content_hash: 7cb05b4d5ca57df709e4c5918d0b4c4db95cba6500fa69b8b790ed1b612d0e35
---
# [AMD] fix dsv4 indexer dtype dispatch on gfx950

URL: https://github.com/sgl-project/sglang/pull/29479
State: closed
Labels: 
Closed at: 2026-07-09T09:54:01Z
Merged at: 2026-07-09T09:54:01Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
The DeepSeek-V4 indexer and the unified-KV paged-decode kernel selected their FP8 data type with `is_hip()`, which hardcodes `torch.float8_e4m3fnuz` for **all** AMD GPUs. This is only correct on CDNA3 (gfx942).  This PR aligns the dtype so the dispatch is correct on gfx950 (and unchanged on gfx942 / NVIDIA).

<!-- Describe the purpose and goals of this pull request. -->

## Modifications
- `python/sglang/srt/layers/attention/dsv4/indexer.py`
  - Select `FP8_DTYPE` / `FP8_MAX` via `is_fp8_fnuz()` instead of `is_hip()`.
  - Import `is_fp8_fnuz` from `sglang.srt.layers.quantization.fp8_kernel`; drop the
    now-unused `is_hip` import.
- `python/sglang/srt/layers/attention/dsv4/unified_kv_kernels/paged_decode.py`
  - Select `_FP8_DTYPE` via `is_fp8_fnuz()` instead of the hardcoded
    `torch.float8_e4m3fnuz`; add the import and update the storage comment.
<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

GSM8K on gfx950 (MI355) with DeepSeek-V4-Pro, `tp=8`, `--kv-cache-dtype fp8_e4m3`, `--attention-backend dsv4`:

```bash
lm_eval --model local-completions \
  --model_args model=/models/DeepSeek-V4-Pro,base_url=http://localhost:8000/v1/completions,num_concurrent=16,max_retries=3,tokenized_requests=False \
  --tasks gsm8k --num_fewshot 5
```

```
|Tasks|Version|     Filter     |n-shot|  Metric   |   |Value |   |Stderr|
|gsm8k|      3|flexible-extract|     5|exact_match|↑  |0.9507|±  |0.0060|
|     |       |strict-match    |     5|exact_match|↑  |0.9515|±  |0.0059|
```

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29009248782](https://github.com/sgl-project/sglang/actions/runs/29009248782)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29009248687](https://github.com/sgl-project/sglang/actions/runs/29009248687)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
