---
source_id: sglang-github-closed-issues-prs
title: Fix index out of bounds in _modify_tuple for LoRA tensors
canonical_url: https://github.com/sgl-project/sglang/pull/11397
captured_at: '2026-07-10T23:37:20.318529+00:00'
content_hash: 21ae5ad07c408fe842409cfb31ae7d64b90cf1a52e0038acb42fd693c852eb8e
---
# Fix index out of bounds in _modify_tuple for LoRA tensors

URL: https://github.com/sgl-project/sglang/pull/11397
State: closed
Labels: 
Closed at: 2026-07-10T23:11:10Z
Merged at: 

## Problem
The `_modify_tuple` function in `python/sglang/srt/utils/patch_torch.py` crashes with IndexError when working with LoRA tensors that have fewer elements than expected. This occurs during multiturn VERL experiments that use both SGLang and vLLM with LoRA adaptation in the RL loop.

## Solution
Enhanced `_modify_tuple` to handle edge cases:
1. **Index beyond tuple length**: Returns original tuple unchanged
2. **Index at last element**: Handles correctly without creating empty tail slice
3. **Normal cases**: Preserves original behavior

## Testing
- [x] Verified fix handles out-of-bounds access
- [x] Confirmed last-element edge case works correctly
- [x] Ensured backward compatibility for existing use cases

## Context
This issue manifests when using LoRA adapters with SGLang in reinforcement learning scenarios where tensor shapes may vary from expected configurations.
