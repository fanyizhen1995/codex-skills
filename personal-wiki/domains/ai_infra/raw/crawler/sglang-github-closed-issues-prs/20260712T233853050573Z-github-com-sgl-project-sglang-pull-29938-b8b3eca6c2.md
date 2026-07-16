---
source_id: sglang-github-closed-issues-prs
title: '[Spec]Support Temperature Sampling（target-only and rejection sampling）for
  DSpark'
canonical_url: https://github.com/sgl-project/sglang/pull/29938
captured_at: '2026-07-12T23:38:53.050573+00:00'
content_hash: b8b3eca6c2f971654d95b5c6c70fc3a3e4b92c85ec8cba186c701ad8ed88c42e
---
# [Spec]Support Temperature Sampling（target-only and rejection sampling）for DSpark

URL: https://github.com/sgl-project/sglang/pull/29938
State: closed
Labels: documentation, deepseek, speculative-decoding
Closed at: 2026-07-12T22:51:18Z
Merged at: 

## Summary

This PR extends DeepSeek-V4 DSpark speculative decoding beyond the original greedy-only path.

- Keep the existing greedy/lossless behavior for `temperature=0`.
- Add target-only temperature sampling for `temperature>0` as the default DSpark sampled-decoding path.
- Add optional speculative rejection sampling for DSpark via `--speculative-use-rejection-sampling`.
- Reuse the existing speculative sampling utilities so DSpark follows the same acceptance semantics as the sampled speculative decoding path.
- Update DSpark documentation to describe greedy, target-only sampling, and rejection-sampling modes.

## Motivation

The original DSpark path from #29705 only supported greedy verification. That is correct for `temperature=0`, but sampled generation requests should let the target distribution control generation. DSpark checkpoints are trained with TV loss, so sampled decoding should support both a conservative target-only sampling path and a rejection-sampling path.

## Implementation

- `dspark_worker_v2.py`
  - Keeps the old greedy verifier for all-greedy requests.
  - Uses target-only sampling when requests are non-greedy and `--speculative-use-rejection-sampling` is not set.
  - Uses speculative rejection sampling when requests are non-greedy and `--speculative-use-rejection-sampling` is set.
  - Samples draft tokens from draft probabilities for RS and computes target probabilities for verifier acceptance.

- `spec_utils.py`
  - Temperature-scales draft probabilities when rejection sampling is enabled.

- `arg_groups/speculative_hook.py`
  - Allows `--speculative-use-rejection-sampling` for DSpark.
  - Validates DSpark RS constraints: `topk=1`, no custom accept thresholds, and no deterministic inference mode.

- Docs
  - Updates DSpark docs from greedy-only to greedy + sampled decoding.
  - Documents target-only sampling and `--speculative-use-rejection-sampling`.

## Validation

DeepSeek-V4-Flash-DSpark, TP=8, EP=8, block size=5, batch size=32, max output=1024.

### temp=0.6

| data | target-only acc_len | RS acc_len | target-only out_tps | RS out_tps |
|---|---:|---:|---:|---:|
| gsm8k | 3.962 | 4.008 | 1673.1 | 1732.0 |
| humaneval | 3.393 | 3.600 | 1918.4 | 1966.4 |
| math500 | 3.833 | 3.897 | 2513.7 | 2490.7 |
| mbpp | 3.268 | 3.448 | 2478.9 | 2500.9 |
| mtbench | 3.313 | 3.346 | 2178.9 | 2139.2 |

### temp=1.0

| data | target-only acc_len | RS acc_len | target-only out_tps | RS out_tps |
|---|---:|---:|---:|---:|
| gsm8k | 3.796 | 3.947 | 1718.4 | 1714.4 |
| humaneval | 3.177 | 3.519 | 1725.5 | 1910.0 |
| math500 | 3.671 | 3.892 | 2326.4 | 2322.2 |
| mbpp | 3.071 | 3.382 | 2277.2 | 2463.3 |
| mtbench | 3.054 | 3.279 | 2025.6 | 2087.4 |

GSM8K accuracy, compared with AR/no-spec under the same sampling temperatures:

| mode | temp | score | latency_s | output_tps |
|---|---:|---:|---:|---:|
| AR/no-spec | 0.6 | 0.985 | 29.900 | 756.759 |
| DSpark RS | 0.6 | 0.985 | 18.429 | 1215.772 |

Accuracy setup: standard GSM8K test split, 200 examples, chat API, `top_p=1.0`, `max_tokens=1024`, `num_threads=32`, `context_length=131072`, DeepSeek-V4-Flash-DSpark TP=8 EP=8.

## Notes

For `temperature=0`, DSpark remains equivalent to the original greedy target decoding path. For `temperature>0`, target-only sampling is the safer default because the verifier's target distribution controls sampled tokens. Rejection sampling is available when users want a fully speculative sampled path.









<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28589887119](https://github.com/sgl-project/sglang/actions/runs/28589887119)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28589886883](https://github.com/sgl-project/sglang/actions/runs/28589886883)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
