---
source_id: sglang-github-closed-issues-prs
title: '[Fix] mm processor double bos'
canonical_url: https://github.com/sgl-project/sglang/pull/26505
captured_at: '2026-07-11T23:37:37.774422+00:00'
content_hash: 523db47a238588627019b6e0d539ed27973bda609922a68bbaf1cd36fb24d2f4
---
# [Fix] mm processor double bos

URL: https://github.com/sgl-project/sglang/pull/26505
State: closed
Labels: run-ci
Closed at: 2026-07-10T23:53:09Z
Merged at: 2026-07-10T23:53:09Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

For multimodal requests where the chat template renders a literal BOS string (e.g. `<BOS_TOKEN>` for Cohere2, `<|begin_of_text|>` for Llama3-LLaVA-Next) and the tokenizer also auto-adds BOS on encode, `BaseMultimodalProcessor.process_mm_data` was producing 2 leading BOS tokens vs the HF reference's 1. 

We mirror the existing guard in `serving_chat.py`, detect the auto-add behavior in `__init__` and pass `add_special_tokens=False` to the inner processor call when the rendered input already starts with the BOS literal.

Note that, the existing guard in `serving_chat.py` only covers its own tokenize step; the multimodal path forwards the rendered prompt string to `BaseMultimodalProcessor` (discarding `prompt_ids`), which re-tokenizes via `processor.__call__` with no guard, so the fix has to live at the multimodal processor layer.

A unit test is added for this fix.

## Modifications

<!-- Detail the changes made in this pull request. -->

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

Before fix:

```
[text-only OpenAI chat]
  [A] HF ref     len=120  BOS=1  first5=[2, 255000, 255004, 255012, 8928]
  [B] sglang     len=120  BOS=1  first5=[2, 255000, 255004, 255012, 8928]

[multimodal OpenAI chat (with image)]
  [A] HF ref     len=377  BOS=1  first5=[2, 255000, 255004, 255012, 8928]
  [B] sglang     len=378  BOS=2  first5=[2, 2, 255000, 255004, 255012]
```

After fix:

```
[text-only OpenAI chat]
  [A] HF ref     len=120  BOS=1  first5=[2, 255000, 255004, 255012, 8928]
  [B] sglang     len=120  BOS=1  first5=[2, 255000, 255004, 255012, 8928]

[multimodal OpenAI chat (with image)]
  [A] HF ref     len=377  BOS=1  first5=[2, 255000, 255004, 255012, 8928]
  [B] sglang     len=377  BOS=1  first5=[2, 255000, 255004, 255012, 8928]
```

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #26540140252](https://github.com/sgl-project/sglang/actions/runs/26540140252)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #26540140213](https://github.com/sgl-project/sglang/actions/runs/26540140213)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
