---
source_id: sglang-github-closed-issues-prs
title: '[Disagg][Qwen3.5] Fix heterogeneous attn-TP scatter transfer: GDN conv sub-block
  slice + GQA replicated-KV head map'
canonical_url: https://github.com/sgl-project/sglang/pull/30997
captured_at: '2026-07-15T23:40:28.355612+00:00'
content_hash: 8fda1aa71b60220581c9921c0ca50a2d1bea89be65cba1d79b906a213bdbd39f
---
# [Disagg][Qwen3.5] Fix heterogeneous attn-TP scatter transfer: GDN conv sub-block slice + GQA replicated-KV head map

URL: https://github.com/sgl-project/sglang/pull/30997
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-15T18:31:38Z
Merged at: 2026-07-15T18:31:38Z

## Motivation

PD disaggregation of a hybrid GDN + GQA model (Qwen3.5) silently corrupts decode output when prefill and decode use different attention-TP sizes on the **scatter** direction (`prefill attn_tp < decode attn_tp`, e.g. `DEP4` prefill → `TP4` decode): gsm8k drops to ~0.44 vs 0.99 aggregation. Two independent bugs in the hetero-TP state transfer cause it:

1. **GDN `conv_state`** is `cat([q | k | v])` with each sub-block head-sharded independently, but was sliced as one contiguous `1/tp` block — decode ranks `> 0` straddle the q/k/v boundaries and get wrong channels.
2. **GQA KV with replicated heads** (`num_key_value_heads < decode attn_tp`) mapped decode rank → source head with modulo (`r % nkv`) instead of `QKVParallelLinear`'s `tp_rank // num_kv_head_replicas`, so replicated ranks fetch the wrong head.

PR #19086 fixed the head map for the gather direction only; this completes the scatter side. The same two bugs were first fixed by @lixuwei2333 in #23744 against an earlier `main` (before the disaggregation state-transfer refactor).

## Modifications

- **conv_state sub-block slice**: record `conv_shard_groups = [key_dim, key_dim, value_dim]` on `Mamba2StateShape`, plumb it per-tensor to the mooncake/nixl senders, and slice each sub-block independently in both the scatter and aggregation directions. Empty for non-GDN states, so temporal_state and all Mamba2 models keep the single contiguous slice (byte-identical).
- **GQA replicated-KV head map** (mooncake sender + staging helper), scatter branch:
  ```python
  dst_replication = max(1, dst_attn_tp_size // total_kv_heads)
  unique_dst_head_idx = dst_tp_rank_in_group // dst_replication
  src_head_start = (unique_dst_head_idx * dst_heads_per_rank) % src_heads_per_rank
  ```
  `dst_replication == 1` for equal-TP / `nkv ≥ tp`, so behavior is unchanged there.
- Add `TestDisaggregationGDNHybridHeteroTP` (prefill TP1 → decode TP4, small GDN-hybrid model).

Files: `configs/{mamba_utils,qwen3_next}.py`, `disaggregation/{base/conn,utils,mooncake/conn,nixl/conn,common/staging_buffer}.py`, `mem_cache/memory_pool.py`, and the test.

## Accuracy Tests

Qwen3.5-397B-A17B-FP8, `DEP4` prefill → `TP4` decode:

| Benchmark | Without fix | With fix |
|---|---|---|
| gsm8k (1319) | 0.44 | **0.9756** (agg 0.99, TP4→TP4 0.97) |

Applying only the conv-state fix reaches 0.58; the KV-GQA head-map fix recovers the rest.

## Speed Tests and Profiling

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

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29368198247](https://github.com/sgl-project/sglang/actions/runs/29368198247)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29368198093](https://github.com/sgl-project/sglang/actions/runs/29368198093)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
