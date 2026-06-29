---
source_id: sglang-github-closed-issues-prs
title: Fix dummy weight init for tensor subclasses
canonical_url: https://github.com/sgl-project/sglang/pull/29229
captured_at: '2026-06-29T04:09:41.031216+00:00'
content_hash: f44fad04155de86326f343cacc5b709b2aedc59b185e38bc0f53eebc1f3a036d
---
# Fix dummy weight init for tensor subclasses

URL: https://github.com/sgl-project/sglang/pull/29229
State: closed
Labels: run-ci
Closed at: 2026-06-28T17:17:01Z
Merged at: 2026-06-28T17:17:01Z

## Summary

Fix `initialize_dummy_weights()` so tensor subclasses are classified by their logical dtype instead of their raw storage dtype.

## Motivation

Some tensor subclasses expose low-bit storage through `.data`, while the wrapper tensor itself reports the logical dtype that its tensor operations support. For example, MXFP wrappers can have a logical `bfloat16` dtype while `.data` is FP8 storage.

The previous dummy init check used `param.data.dtype`, which sent these wrappers through the low-bit fallback path. That fallback only rewrites the raw storage tensor and bypasses wrapper `uniform_()` logic that also updates side tensors such as block scales.

Using `param.dtype` keeps plain low-bit tensors on the fallback path, while allowing tensor subclasses with supported logical dtypes to use their own `uniform_()` implementation.





















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28141477996](https://github.com/sgl-project/sglang/actions/runs/28141477996)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28141479837](https://github.com/sgl-project/sglang/actions/runs/28141479837)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
