---
source_id: sglang-github-closed-issues-prs
title: '[fix] Only enable flashinfer all reduce fusion by default for single-node
  servers'
canonical_url: https://github.com/sgl-project/sglang/pull/12724
captured_at: '2026-07-07T23:35:30.918286+00:00'
content_hash: 0f71aab6a8883bc43c04d5c899a2e3f86222ce18ed432db03170a4857f8bfde1
---
# [fix] Only enable flashinfer all reduce fusion by default for single-node servers

URL: https://github.com/sgl-project/sglang/pull/12724
State: closed
Labels: run-ci
Closed at: 2025-11-06T19:53:58Z
Merged at: 2025-11-06T19:53:58Z

## Motivation

Currently multi-node non-data-parallel inference does not work for `DeepseekV3ForCausalLM` models.
This is due to a bug in flashinfer: https://github.com/flashinfer-ai/flashinfer/issues/2006

## Modifications

Currently enable_flashinfer_allreduce_fusion is enabled by default for `DeepseekV3ForCausalLM` and `GptOssForCausalLM`.  Because of the flashinfer all reduce fusion bug, a workaround is to only enable flashinfer all reduce fusion if a single node is used.
