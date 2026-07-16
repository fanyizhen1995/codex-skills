---
source_id: sglang-github-closed-issues-prs
title: '[RFC] Faster loading for MoE models using TP'
canonical_url: https://github.com/sgl-project/sglang/issues/20332
captured_at: '2026-07-10T23:37:20.317527+00:00'
content_hash: 9d6afd3e87aca5b9951d84abeaed229c5e61b5e25bafe618edce85b3f751c7fd
---
# [RFC] Faster loading for MoE models using TP

URL: https://github.com/sgl-project/sglang/issues/20332
State: closed
Labels: inactive, nvidia, RFC
Closed at: 2026-07-10T00:39:36Z
Merged at: 

### Checklist

- [x] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

# Problem
For the purposes of this discussion, the majority of weights is in MoE and we'll be ignoring the rest.

When loading models such as deepseek-R1 using TP8, the loading times can be extremely long (~1hour), bottlenecked at disk IO. In contrast, when using TEP8/DEP8, the loading time is significantly shorter (~2min). However, all three settings read the same number of bytes on each rank, so the main culprit is the access pattern.

Safetensors are stored parameter-by-parameter, meaning each safetensor stores several parameters contiguously. In EP, the access pattern is simple: either read an entire parameter or skip it. In TP, the weights are striped. For example, for TP2, the two gemm weights look like
```
+----------+         +-----------+
|#####-----|         |###########|
|#####-----|         |###########|
|#####-----|         |-----------|
|#####-----|         |-----------|
+----------+         +-----------+
```
This pattern is horrible for disk IO, even with all the mmap and caching involved.

# Solution

A solution is to load in a pattern that is disk IO friendly. Namely, we can load weights as-if using EP, then use device-to-device (D2D) memory transfers to restore the weights into what TP needs. A proof-of-concept implementation (including a unit test) can be found at https://github.com/sgl-project/sglang/compare/main...nvjullin:sglang:claude-tp-to-ep.

This solution is premised on several factors:
1. EP weight loading is fast, which varies with the disk setup
2. TP weight loading is slow, which varies with the disk setup
3. D2D is fast, which varies with GPU topology

So it's not a universal solution for all setups. In our setup, the solution makes weight loading go from ~1hour to ~2min because D2D is virtually free.

This solution does not work generically across models. Diffusion models won't benefit from this, but the same principle can be ported over (with effort).

There is a slight memory overhead of additional buffers used during D2D. It is on the order of the weights of a single layer. For deepseek-R1 with 61 layers, this is ~2% overhead, which is unlikely to be problematic.

# Alternative Solutions

#19758 implements an alternative format InstantTensor. I am not familiar with its technical details.
It doesn't describe what scenario it excels at, nor its solution.



### Related resources

_No response_
