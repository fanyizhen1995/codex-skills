---
source_id: sglang-github-closed-issues-prs
title: Make mem_fraction_static reserve disaggregation-mode aware
canonical_url: https://github.com/sgl-project/sglang/pull/29615
captured_at: '2026-07-05T02:14:10.235470+00:00'
content_hash: 91cd0e967eda850b57f6dc6cc5b37c375aa68e4ab2fc644c868937c5c4225a87
---
# Make mem_fraction_static reserve disaggregation-mode aware

URL: https://github.com/sgl-project/sglang/pull/29615
State: closed
Labels: run-ci, run-ci-extra
Closed at: 2026-07-05T01:44:07Z
Merged at: 2026-07-05T01:44:07Z

## Motivation

When `--mem-fraction-static` is not set, SGLang auto-derives it by estimating reserved (non-KV) memory. Today that estimate always includes both prefill activation slack **and** decode/prefill CUDA-graph buffers, regardless of the node's role.

On PD-disaggregated deployments each node runs only one phase, so the other phase's reserve is dead headroom that needlessly shrinks the KV cache:
- A **prefill** node still reserves decode CUDA-graph + DP-attention padding memory it never uses.
- A **decode** node still sizes activation slack to prefill tokens and reserves prefill piecewise-CUDA-graph memory it never uses.

## Modification

Gate the reserve terms in `ServerArgs._handle_gpu_memory_settings` on `self.disaggregation_mode`:

- **Activation slack**: decode nodes size to the decode batch — `max(max_running_requests or decode max_bs or 1) * (speculative_num_draft_tokens or 1)`, floored at 2048, ×1.5 — instead of prefill-token sizing. Prefill / unified keep the existing chunked-prefill / max-prefill sizing.
- **Decode CUDA-graph term** and **DP-attention padding terms**: skipped when `disaggregation_mode == "prefill"` (the decode-graph term is additionally guarded on the decode graph backend being enabled).
- **Prefill piecewise CUDA-graph term**: skipped when `disaggregation_mode == "decode"`.

Net effect:
- decode-only nodes drop prefill activation sizing + prefill CUDA-graph reserve;
- prefill-only nodes drop decode CUDA-graph reserve + DP padding reserve;
- unified (non-disaggregated) behavior is unchanged.

The >60GiB 10GiB floor and all other terms are untouched.

## Checklist

- [x] Format with the existing pre-commit hooks.
- [x] No behavior change for non-disaggregated deployments.





























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28694459209](https://github.com/sgl-project/sglang/actions/runs/28694459209)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28694459160](https://github.com/sgl-project/sglang/actions/runs/28694459160)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
