---
source_id: sglang-github-closed-issues-prs
title: '[DeepSeek V3] Reland: run routed experts on main stream in dual-stream MoE'
canonical_url: https://github.com/sgl-project/sglang/pull/29463
captured_at: '2026-07-01T02:12:08.973641+00:00'
content_hash: f6727ba994a22ba53e0f4e14bee83f2594f75d0579a39030264510a46457d89c
---
# [DeepSeek V3] Reland: run routed experts on main stream in dual-stream MoE

URL: https://github.com/sgl-project/sglang/pull/29463
State: closed
Labels: deepseek
Closed at: 2026-06-29T22:05:02Z
Merged at: 2026-06-29T22:05:02Z

## Motivation

Reland of #29142, which was reverted in #29452 because it dropped `test_moe_ep_extra.py`'s gsm8k from ~0.7 to **0.005**.

## Root cause

Not a cross-stream race. The hazard is a **host-side mutation of the input tensor's metadata** between two CUDA kernel launches inside the captured decode graph.

`python/sglang/srt/layers/moe/moe_runner/deep_gemm.py:567-606`, `pre_permute_standard_to_deep_gemm` (called as part of the routed `self.experts(hidden_states, topk_output)` call):

```python
hidden_states_ref = hidden_states          # original input tensor
masked_m, expected_m, src2dst, hidden_states, hidden_states_scale = (
    moe_ep_deepgemm_preprocess(topk_ids, ..., hidden_states, ...)
)
dispose_tensor(hidden_states_ref)          # <-- repoints the *original* tensor
```

`python/sglang/srt/utils/common.py:3152-3169`, `dispose_tensor`:

```python
def dispose_tensor(x):
    if is_in_tc_piecewise_cuda_graph():
        return                              # skipped during prefill capture
    x.set_(torch.empty((0,), device=x.device, dtype=x.dtype))
```

`dispose_tensor` calls `.set_(torch.empty(0))` on the original input tensor — repointing its storage to a zero-sized buffer (host-side; no CUDA kernel). Under `tc_piecewise` (prefill) it short-circuits to avoid exactly this hazard; under decode `full` capture it fires.

**Any subsequent kernel-launch that consumes `hidden_states` then reads `data_ptr() == 0`** and bakes that address into its captured graph node. At replay the kernel reads from null → garbage logits → gsm8k 0.005.

PR #29142 reordered Python statements so the routed call (which fires `dispose_tensor` inside) ran *before* the shared-expert launch on alt — capturing the post-dispose null pointer into the shared expert's GEMM node. The "cross-stream race" framing and the "torch.compile-flattening" framing were both wrong; the cross-stream sync doesn't matter here.

**Writer / reader:**
- *Writer*: host-side `hidden_states.set_(empty(0))` inside `pre_permute_standard_to_deep_gemm` during the routed `self.experts(...)` call.
- *Reader*: the shared-expert GEMM kernel-launch in `_forward_shared_experts(hidden_states, ...)`, which records `hidden_states.data_ptr()` at capture time.

Whichever launch runs *first in Python wall-clock* during capture wins. The fix is just to launch the reader first.

## Bisection

| Variant | Streams | Python order | gsm8k |
|---|---|---|---|
| OLD (current main, reverted) | shared→main, routed→alt | shared first | ~0.7 ✓ |
| PR #29142 | shared→alt, routed→main | **routed first** | 0.005 ✗ |
| **This PR (reland)** | shared→alt, routed→main | **shared first** | **0.66** ✓ |

Test B was byte-equivalent to PR #29142 except the alt-stream `with`-block moved before the routed pipeline. Same streams, same kernels, same fork/join, same `has_shared_output` naming — only the Python statement position changed. Score 0.66 confirms source-order alone is sufficient.

## Modifications

`python/sglang/srt/models/deepseek_v2.py:forward_normal_dual_stream`:

- Keep #29142's stream assignment — routed on main, shared on alt — so the routed expert is the last kernel on the main stream and can PDL-fuse with the post-MoE residual add (preserves the per-layer ~1µs / ~1% target-verify perf win from #29142).
- Move the `with torch.cuda.stream(self.alt_stream): shared_output = ...` block **before** the routed pipeline so the shared expert's GEMM captures the valid `hidden_states.data_ptr()` *before* the routed call's `dispose_tensor` zeroes it.

## Accuracy / Speed Tests

Verified locally on 2× H200, exact CI args (`--tp 2 --ep-size 2 --quantization fp8 --moe-runner-backend deep_gemm`):

```
[CI Test Method] TestEpDeepGEMM.test_gsm8k
Ran 1 test in 282.790s
OK
Score: 0.645
```

Plus the bisection Test B (PR #29142 byte-equivalent except the `with`-block moved up): score **0.660** on the same test.

vs. PR #29142's 0.005. Threshold is 0.60.

The dual-stream perf path (Kimi-K2.5 NVFP4 etc.) is the same as #29142 — last kernel on main is the routed expert.

## Follow-ups worth flagging

- This is still timing-by-construction (the read happens to be launched before the dispose). A semantically robust fix would either drop `dispose_tensor`'s `set_()` in the deep_gemm preprocess, or have it run on the dispatched/permuted buffer rather than the original. Out of scope here.
- The same Python-order trap could bite future dual-stream additions in other model files. The comment in `forward_normal_dual_stream` documents the invariant.

## Checklist

- [x] Format code with pre-commit.
- [x] Provide accuracy and speed benchmark results.

🤖 Generated with [Claude Code](https://claude.com/claude-code)



















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28271631176](https://github.com/sgl-project/sglang/actions/runs/28271631176)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28271631128](https://github.com/sgl-project/sglang/actions/runs/28271631128)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
