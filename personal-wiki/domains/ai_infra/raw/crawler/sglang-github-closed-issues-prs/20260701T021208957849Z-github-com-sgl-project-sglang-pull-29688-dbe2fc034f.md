---
source_id: sglang-github-closed-issues-prs
title: '[diffusion][cache-dit] support Krea-2 + run-driven `has_separate_cfg`'
canonical_url: https://github.com/sgl-project/sglang/pull/29688
captured_at: '2026-07-01T02:12:08.957849+00:00'
content_hash: dbe2fc034fa3767b791003ad1bdda6a46e23ce23234fb5a607c0644c73a767ea
---
# [diffusion][cache-dit] support Krea-2 + run-driven `has_separate_cfg`

URL: https://github.com/sgl-project/sglang/pull/29688
State: closed
Labels: documentation, run-ci, diffusion
Closed at: 2026-06-30T15:22:06Z
Merged at: 2026-06-30T15:22:06Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

1. Support Cache-DiT for Krea-2 (Turbo and Raw)
2. If a model is not registered in Cache-DiT, we need to build a custom `BlockAdapter` in SGLang. The previous design forced a hardcoded `has_separate_cfg` for each model in `_CUSTOM_BLOCK_ADAPTER_SPECS`, which apply to all model variants within a families. This can lead to a misalignment for models like [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) / [baidu/ERNIE-Image-Turbo](baidu/ERNIE-Image-Turbo) and [krea/Krea-2-Raw](https://huggingface.co/krea/Krea-2-Raw) / [krea/Krea-2-Turbo](https://huggingface.co/krea/Krea-2-Turbo), where raw models are using CFG, while distilled turbo models are not. As a result, enabling `SGLANG_CACHE_DIT_ENABLED=true` for turbo model with hardcoded `has_separate_cfg=True` becomes a no-op.

## Modifications

<!-- Detail the changes made in this pull request. -->

- Add `Krea2Transformer2DModel` to the custom `BlockAdapter` specs (the #28266 path).
- `has_separate_cfg` now follows `batch.do_classifier_free_guidance` instead of a per-model hardcode, and the static spec field is dropped.
- Rename Krea-2 SingleStreamBlock forward arg x -> hidden_states (Pattern_3).

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

| Variant | Inference steps | Denoise time (no cache → cache) | Speedup | MAE/255 |
| :--- | :--- | :--- | :--- | :--- |
| Krea-2-Raw (CFG 4.5) | 50 | 18.0s → 6.3s | ~2.9x | 13.19 |
| Krea-2-Turbo (no CFG) | 8 | 1.27s → 0.92s | ~1.4x | 4.63 |
| ERNIE-Image (CFG 4.0) | 50 | 14.9s → 5.33s | ~2.8x | 7.55 |
| ERNIE-Image-Turbo (no CFG) | 8 | 1.11s → 0.79s | ~1.4x | 3.65 |
| ERNIE-Image-Turbo (no CFG, **before fix**) | 8 | 1.11s → 1.10s | ~1.01x | **0** |

---

- Krea-2-Raw

<table>
  <tr>
    <td align="center">w/o cache-dit</td>
    <td align="center">w/ cache-dit</td>
  </tr>
  <tr>
    <td><img alt="krea_raw_nocache" src="https://github.com/user-attachments/assets/e717b392-5e9f-420b-8761-dbbdf43816fa" width="400"></td>
    <td><img alt="krea_raw_cache" src="https://github.com/user-attachments/assets/cdc75a03-58f2-4ec3-93bd-12171c2a2039" width="400"></td>
  </tr>
</table>

- Krea-2-Turbo

<table>
  <tr>
    <td align="center">w/o cache-dit</td>
    <td align="center">w/ cache-dit</td>
  </tr>
  <tr>
    <td><img alt="krea_turbo_nocache" src="https://github.com/user-attachments/assets/3a87c54f-e7f6-4063-93cf-258a139aff07" width="400"></td>
    <td><img alt="krea_turbo_cache" src="https://github.com/user-attachments/assets/31d74071-bc67-4e16-98a6-e15c86f50438" width="400"></td>
  </tr>
</table>

- ERNIE-Image

<table>
  <tr>
    <td align="center">w/o cache-dit</td>
    <td align="center">w/ cache-dit</td>
  </tr>
  <tr>
    <td><img alt="ernie_nope_nocache" src="https://github.com/user-attachments/assets/3817cf4d-b486-48f1-8a0d-50728f3508f6" width="400"></td>
    <td><img alt="ernie_nope_cache" src="https://github.com/user-attachments/assets/c7695b0a-399f-4ce5-b75e-f092dfa3df9c" width="400"></td>
  </tr>
</table>

- ERNIE-Image-Turbo

<table>
  <tr>
    <td align="center">w/o cache-dit</td>
    <td align="center">w/ cache-dit</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/a3f4a78b-fe8f-4f3d-aef0-0b566fe66cc4" alt="ernie_turbo_nope_nocache" width="400"></td>
    <td><img src="https://github.com/user-attachments/assets/33c46747-2da5-482e-810e-bc5b415f6a91" alt="ernie_turbo_nope_cache" width="400"></td>
  </tr>
</table>


## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

2. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
4. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
5. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
6. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.











<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28409302758](https://github.com/sgl-project/sglang/actions/runs/28409302758)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28409302600](https://github.com/sgl-project/sglang/actions/runs/28409302600)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
