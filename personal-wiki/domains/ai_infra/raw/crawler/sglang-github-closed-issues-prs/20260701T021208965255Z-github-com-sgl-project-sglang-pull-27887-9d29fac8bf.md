---
source_id: sglang-github-closed-issues-prs
title: '[Model] Add HrmTextForCausalLM (Hierarchical Reasoning Model - Text)'
canonical_url: https://github.com/sgl-project/sglang/pull/27887
captured_at: '2026-07-01T02:12:08.965255+00:00'
content_hash: 9d29fac8bf2610a2541fe01c4a8163a511d89901d8cbb59b23d8cb8ee6121b0d
---
# [Model] Add HrmTextForCausalLM (Hierarchical Reasoning Model - Text)

URL: https://github.com/sgl-project/sglang/pull/27887
State: closed
Labels: run-ci
Closed at: 2026-06-30T05:32:33Z
Merged at: 2026-06-30T05:32:33Z

HRM-Text shipped in [transformers 5.9.0](https://github.com/huggingface/transformers/pull/46025). The model runs a hierarchical recurrent forward over two transformer stacks (`H` slow, `L` fast) inside nested H/L cycle loops; each recurrence step consumes a distinct KV cache slot, matching transformers' `cycle_offset` formula. Attention uses a sigmoid gate (Qwen3Next-style) and a fused gate+q+k+v projection on disk.

This PR adds the model file plus two small touch points in `model_config.py` and `model_runner.py` (explained below). It mirrors our vLLM implementation of the same model.

## Architecture

- `models/hrm_text.py`: full model. Each recurrence step gets its own `RadixAttention` instance under an `nn.ModuleDict`, with a unique `layer_id = step * num_layers_per_stack + layer_in_stack`, so a distinct KV cache slot is allocated per cycle step. Total slots = `num_layers_per_stack * H_cycles * (L_cycles + 1)`, equal to `config.num_hidden_layers` after HF's `__post_init__` inflation.
- The HF on-disk schema fuses gate/q/k/v into a single `attn.gqkv_proj.weight` (rows `[gate | q | k | v]`) and gate/up into `mlp.gate_up_proj.weight`. Both load directly via `MergedColumnParallelLinear`'s fused-on-disk path; `load_weights` only renames the `.attn.` prefix to `.self_attn.`. Sigmoid attention gate, parameterless RMSNorm, `embedding_scale`, and a frozen `z_L_init` round out the model.
- `model_config.py`: a `num_attention_layers` branch computing the unrolled KV-slot count for HRM (so KV allocation is correct regardless of how `num_hidden_layers` is carried).

## PrefixLM attention and the two open questions

HRM-Text is a PrefixLM: the prompt attends bidirectionally during prefill, the completion is causal at decode. I'd appreciate guidance on the two points below, since both touch SGLang internals beyond the model file.

1. **Bidirectional attention is backend-limited.** I express it via `AttentionType.DECODER_BIDIRECTIONAL`, which today is only honored by the Triton backend (and only when cuda graph + chunked prefill are off). FlashInfer/FA3 recognize `ENCODER_ONLY` but not `DECODER_BIDIRECTIONAL`. So the model is effectively pinned to Triton. Is there a preferred way to make bidirectional-prefill backend-agnostic?

2. **Bidirectional prefill is incompatible with chunked-prefill and radix cache.** Both assume causal attention: chunking the prompt freezes early-chunk tokens before later prompt tokens exist, and radix cache reuses KV keyed by token-id prefix, but bidirectional KV at position i depends on the whole prompt, not just 0..i. I currently force `chunked_prefill_size=-1` + `disable_radix_cache` + `disable_cuda_graph` + Triton in `model_runner.model_specific_adjustment` for `prefix_lm` models. This works but is heavy-handed and lives in a core file. Is there a cleaner per-model / per-layer hook you'd prefer (e.g. a flag the scheduler reads)?

## Validation

`HRM-Text-1B`, GSM8K (first 50): 41/50 at tp=2, 40/50 at tp=1, matching our vLLM reference (the tp=1/tp=2 difference is greedy-decode tie-breaking, not a correctness gap). Requires transformers >= 5.9.0 for the native `hrm_text` config.

























































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28002067096](https://github.com/sgl-project/sglang/actions/runs/28002067096)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #28084166670](https://github.com/sgl-project/sglang/actions/runs/28084166670)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
