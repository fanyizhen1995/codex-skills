---
source_id: sglang-github-closed-issues-prs
title: '[Experimental] Full Cuda Graph Support for Prefill'
canonical_url: https://github.com/sgl-project/sglang/pull/27988
captured_at: '2026-07-07T23:35:30.920969+00:00'
content_hash: b6f66f7a117ea5f08ba8d3edbfc68f252c613c3a480737df43b6e1fe2e5557df
---
# [Experimental] Full Cuda Graph Support for Prefill

URL: https://github.com/sgl-project/sglang/pull/27988
State: closed
Labels: run-ci, bypass-fastfail, run-ci-extra, release-highlight
Closed at: 2026-07-07T01:13:04Z
Merged at: 2026-07-07T01:13:04Z

Adds "full" as a prefill cuda-graph backend (previously decode-only): one whole-forward torch.cuda.CUDAGraph per num_tokens bucket, reusing the existing FullCudaGraphBackend unchanged. Targets small prefills on fast GPUs where per-forward launch/python overhead dominates.

Design:
- Token axis: replay pads num_tokens up to the nearest captured bucket (same ladder as the other prefill backends).
- Request axis: each graph is captured with a fixed slot count (FULL_CG_PREFILL_REQ_SLOTS=16); real batches with bs <= slots reuse the graph by padding the metadata with zero-length sentinel requests (zeroed every replay), so one graph serves bs in [1, 16]. Larger batches fall back to eager via can_run.
- Attention metadata follows the decode-style 2-step contract (init_forward_metadata_out_graph before capture/replay). Implemented for flashinfer (dedicated use_cuda_graph wrappers, one set shared across buckets, 2GB dedicated workspace; split-kv must stay enabled in cudagraph mode -- its block_valid_mask is what lets padded/stale tiles of the fixed captured grid exit early, measured 165x) and for the FlashAttention backend (fa4; dedicated buffers, cu_seqlens_q never aliased to cu_seqlens_k, max_seq_len_q/k baked as upper bounds; page_size=1 only for now). Other attention backends fail loudly at capture during startup.
- disable_split_kv threaded through FlashInferIndicesUpdaterPrefill for parity with the decode updater.

Results (Qwen3-8B, B200, mgsm_en 1319 examples, threshold 0.80): flashinfer 0.836-0.84, fa4 0.852; no default-config regression (0.848). Small-prefill forward (30 tok): fa4 4.07 ms / flashinfer 4.41 ms vs BCG 7.35 ms (1.7x), identical GPU busy -- the win is launch overhead.

Test: test/registered/cuda_graph/full_prefill/ mirrors the breakable integration test with --cuda-graph-backend-prefill=full.

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->

## Modifications

<!-- Detail the changes made in this pull request. -->

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28691874062](https://github.com/sgl-project/sglang/actions/runs/28691874062)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28820099167](https://github.com/sgl-project/sglang/actions/runs/28820099167)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
