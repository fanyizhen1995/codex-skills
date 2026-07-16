---
source_id: sglang-github-closed-issues-prs
title: '[DSV4][Perf] Use native DeepGEMM next-n layout on SM100'
canonical_url: https://github.com/sgl-project/sglang/pull/28892
captured_at: '2026-07-15T23:40:28.372248+00:00'
content_hash: c6c264023b31b7e4a6e7d60876e75e229184980d60411a96b27e03f2b0b6a297
---
# [DSV4][Perf] Use native DeepGEMM next-n layout on SM100

URL: https://github.com/sgl-project/sglang/pull/28892
State: closed
Labels: deepseek, run-ci, run-ci-extra
Closed at: 2026-07-15T07:54:09Z
Merged at: 

## Motivation

DeepGEMM's SM100 paged MQA logits kernels can consume the native `next_n` dimension directly. For DSV4 speculative target verify, SGLang already supported `next_n=4`, but the DeepGEMM indexer call was still flattened from `(B, next_n)` into `(B * next_n, 1)`. This PR keeps the target verify layout as `(B, next_n)` for the DeepGEMM FP8 and FP4 indexer paths on SM100-family GPUs.

| Version | DeepGEMM input layout |
| --- | --- |
| Before | `(B * next_n, 1, ...)` |
| After | `(B, next_n, ...)` |

## Modifications

- Add DSV4 C4 indexer metadata for the native speculative target verify DeepGEMM path on SM100-family GPUs.
- Reshape FP8 and FP4 indexer queries from `(B * next_n, ...)` back to `(B, next_n, ...)` before calling DeepGEMM when `next_n >= 2`.
- Build DeepGEMM schedule metadata from the matching `(B, next_n)` C4 context lengths for this path.
- Keep the flattened page table for the top-k transform, and pass the matching native page table to the DeepGEMM logits call.
- Keep the existing flattened path for non-SM100-family GPUs and for FP8 TileLang/AITER/torch fallback indexers.

## Accuracy Tests

GSM8K:

| Indexer | Before | After |
| --- | ---: | ---: |
| FP8 | 96.51% | 96.97% |
| FP4 | 96.36% | 96.66% |

## Speed Tests and Profiling

Benchmark setup:

| Setting | Value |
| --- | --- |
| Model | `deepseek-ai/DeepSeek-V4-Flash` |
| Batch size | 32 |
| Input / output len | 8192 / 1024 |
| Speculative config | steps=3, eagle top-k=1, draft tokens=4 |

### Profiler trace

FP8 before:

<img width="1631" height="747" alt="Screenshot 2026-06-12 193313" src="https://github.com/user-attachments/assets/a44eb439-a712-4f23-8364-687097ad730e" />

FP8 after:

<img width="1632" height="748" alt="Screenshot 2026-06-12 192549" src="https://github.com/user-attachments/assets/898d9c37-d537-48db-8477-8db9d5c95145" />

FP4 before:

<img width="1632" height="747" alt="Screenshot 2026-06-12 193058" src="https://github.com/user-attachments/assets/980c9cd2-f0ca-42d9-9cdd-bc3abc423005" />

FP4 after:

<img width="1632" height="747" alt="Screenshot 2026-06-12 192740" src="https://github.com/user-attachments/assets/9240ea4c-5518-4338-be87-5641cfaf1bd4" />

The FP8 and FP4 kernel names change from `<1u, ...>` to `<4u, ...>`, confirming that DeepGEMM sees `next_n=4` in the patched path.

### E2E numbers

| Indexer | Before out tok/s | After out tok/s | Diff | Accept len |
| --- | ---: | ---: | ---: | ---: |
| FP8 | 2902.38 | 3036.07 | +4.6% | 2.80 -> 2.78 |
| FP4 | 2934.26 | 3073.79 | +4.8% | 2.77 -> 2.77 |

































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28912115071](https://github.com/sgl-project/sglang/actions/runs/28912115071)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:white_check_mark: [Run #28912114993](https://github.com/sgl-project/sglang/actions/runs/28912114993)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
