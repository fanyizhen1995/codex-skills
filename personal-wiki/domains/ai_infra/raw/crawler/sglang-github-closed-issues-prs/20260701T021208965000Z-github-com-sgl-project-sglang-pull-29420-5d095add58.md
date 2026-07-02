---
source_id: sglang-github-closed-issues-prs
title: '[AMD][DSV4] Remove per-batch D2H syncs in MTP to avoid bubbles between 2 batches'
canonical_url: https://github.com/sgl-project/sglang/pull/29420
captured_at: '2026-07-01T02:12:08.965000+00:00'
content_hash: 5d095add580ab781bf726c73fd0262dfe77e093592583004dce772d13c376483
---
# [AMD][DSV4] Remove per-batch D2H syncs in MTP to avoid bubbles between 2 batches

URL: https://github.com/sgl-project/sglang/pull/29420
State: closed
Labels: amd, deepseek, run-ci
Closed at: 2026-06-30T05:40:00Z
Merged at: 2026-06-30T05:40:00Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation

<!-- Describe the purpose and goals of this pull request. -->
With MTP (EAGLE) enabled, DSV4 decode on the HIP backend showed periodic **2–xx ms gaps between consecutive batches** — scheduling and execution could not overlap. Profiling traced the stalls to two per-batch device→host syncs in the target-verify metadata build, which block the host launch thread and serialize batch N execution with batch N+1 scheduling.
<img width="602" height="162" alt="image" src="https://github.com/user-attachments/assets/753fc7fa-1e1e-4b94-ba6c-b4033ad4a601" />


## Modifications

<!-- Detail the changes made in this pull request. -->
1. `_attach_unified_kv_prefill_meta`: the token→req map was built with `torch.repeat_interleave(arange, extend_seq_lens)` where the repeats are a GPU tensor, forcing a D2H readback of `sum(extend_seq_lens)` to size the output. Pass `output_size` (from the host-side `extend_seq_lens_cpu`) so the output is sized without the readback — same approach the CUDA backend already uses in `_expand_prefill_casually_vectorized`. 
—— Update: we left this change to #29202 to avoid overlap, since we are targeting the same `bid = torch.repeat_interleave(...)` D2H sync in `_attach_unified_kv_prefill_meta`.
2. `init_forward_metadata_target_verify`: it recomputed `seq_lens.tolist()` from the GPU tensor every batch. Thread the ready-maintained CPU mirror `seq_lens_cpu` through both the eager and cuda-graph-replay (`init_forward_metadata_out_graph`) entry points. 
—— Update: Trim this PR down to its unique change: removing the per-batch `seq_lens.tolist()` D2H sync in `init_forward_metadata_target_verify` by threading the already-maintained CPU mirror seq_lens_cpu through both the eager and the cuda-graph-replay entry points.

Both changes are behavior-preserving (CPU values mirror the GPU tensors). ROCm-only; the CUDA backend already avoids both syncs.

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->
gsm8k shows accuracy 0.947 which seems to be compatible with before modification 0.945.

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->
**Trace below**: captured under a decode-heavy load to visualize the per-batch gaps before/after.
After removing the D2H syncs in MTP, the trace looks more reasonable with no bubbles.
<img width="513" height="68" alt="image" src="https://github.com/user-attachments/assets/e16bd631-9ec6-4e73-9e24-1933eaa8b6b1" />

**TPOT table below**: Measured on MI355X ×8, TP8 + DP8 Attn, DeepSeek-V4-Pro, EAGLE (`steps3 / draft4 / topk1`). Customer-representative decode-heavy workload (long ~50k input + MTP), input 51.2k/54.1k, local bs 16/32 per DP rank, 32 output tokens, 3 repeats — decode step time saves 8%–13%. 
**Decode step time / TPOT (lower is better):**
Batch (local/DP) | Input | BEFORE(ms) | AFTER(ms) | Time saved | SpeedUp
-- | -- | -- | -- | -- | --
16 | 51.2k | 52.96 | 46.44 | −6.5 ms | −12.3% (≈+14% tput)
16 | 54.1k | 53.29 | 46.31 | −7.0 ms | −13.1% (≈+15% tput)
32 | 51.2k | 68.90 | 62.95 | −6.0 ms | −8.6% (≈+9.4% tput)
32 | 54.1k | 68.30 | 62.77 | −5.5 ms | −8.1% (≈+8.8% tput)
*throughput is derived from step time (1/(1−Δ)), not separately measured.

Pls note that the gain is from both Modifications-1 and Modifications-2, where Modifications-1 is the main factor.

## Checklist

- [ ] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
5. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
6. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.









































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #28345899253](https://github.com/sgl-project/sglang/actions/runs/28345899253)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28345899136](https://github.com/sgl-project/sglang/actions/runs/28345899136)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
