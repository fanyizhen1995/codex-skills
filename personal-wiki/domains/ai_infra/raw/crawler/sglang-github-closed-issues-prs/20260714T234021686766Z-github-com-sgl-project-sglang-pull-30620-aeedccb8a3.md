---
source_id: sglang-github-closed-issues-prs
title: Allow prefill breakable CUDA graph for Qwen3.5 via multimodal opt-in allowlist
canonical_url: https://github.com/sgl-project/sglang/pull/30620
captured_at: '2026-07-14T23:40:21.686766+00:00'
content_hash: aeedccb8a3ee565eaf42d1d03d34f7e1f27e7174539ba81dd57b503a6246a00c
---
# Allow prefill breakable CUDA graph for Qwen3.5 via multimodal opt-in allowlist

URL: https://github.com/sgl-project/sglang/pull/30620
State: closed
Labels: run-ci, bypass-fastfail
Closed at: 2026-07-14T01:39:45Z
Merged at: 2026-07-14T01:39:45Z

## Motivation

Since #29458, breakable CUDA graph (BCG) is the default prefill CUDA graph backend on CUDA, but the generic "multimodal model" rule in `_disable_breakable_cudagraph_if_incompatible` turns it off for every arch in `multimodal_model_archs`. Qwen3.5 (`Qwen3_5[Moe]ForConditionalGeneration`) is caught by this rule even for text-only serving, although its GDN/GQA prefill path fully supports BCG capture/replay.

The failure mode the rule protects against ("multimodal prefill replay faults") is real: the captured graph embeds from `input_ids` only, while multimodal batches merge mm embeddings in the outer model wrapper, which capture bypasses — replaying them silently drops image inputs. The existing `can_run_graph` guard only covered `input_embeds` / `replace_embeds`; this PR extends it to batches carrying `mm_inputs` (caught by `test_vlm_tp4.py` MMMU dropping to 0.50 on the first CI run of this PR; multimodal batches now fall back to eager prefill, which is today's behavior).

## Modifications

Mirror the existing tc_piecewise opt-in pattern (`multimodal_piecewise_cuda_graph_supported_model_archs`) with a BCG-specific allowlist:

- `model_config.py`: add `multimodal_breakable_cuda_graph_supported_model_archs` (Qwen3.5 dense + MoE) and the corresponding `ModelConfig` field.
- `server_args.py`: the BCG "multimodal model" rule becomes `is_multimodal and not is_multimodal_breakable_cuda_graph_supported`.
- `prefill_cuda_graph_runner.py`: `can_run_graph` rejects batches carrying `mm_inputs`, so multimodal batches run eager prefill while text-only batches replay the graph. `mm_inputs` persists on the request until it finishes, so every prefill chunk of a multimodal request is covered.

No behavior change for any arch not on the allowlist.

## Accuracy Tests

## Speed Tests and Profiling

Qwen3.5-397B-A17B-FP8, single node TP4 (GB200), 1k1k random dataset, closed-loop client (range-ratio 0.8, num-prompts 10×conc, request-rate inf). Server args follow the InferenceX/InferenceMAX qwen3.5 fp8 configs (`trtllm_mha` attention, `flashinfer_trtllm` MoE, fp8_e4m3 KV cache, `--enable-symm-mem`, `--disable-radix-cache`). "BCG off" = same build with `--disable-prefill-cuda-graph`, which is the effective status quo for Qwen3.5 today.

| Config | Concurrency | BCG on: total tok/s / p50 TTFT | BCG off: total tok/s / p50 TTFT | Δ throughput | Δ TTFT |
|---|---|---|---|---|---|
| TP4 | 4 | 1241.3 / 208.6 ms | 1139.6 / 361.0 ms | **+8.9%** | **−42.2%** |
| TP4 + EAGLE MTP | 16 | 4955.4 / 464.6 ms | 4382.8 / 540.6 ms | **+13.1%** | **−14.1%** |
| TP4 | 64 | 7369.1 / 466.8 ms | 6758.5 / 532.9 ms | **+9.0%** | **−12.4%** |

EAGLE accept length is unchanged between the two arms (2.956 vs 2.931). One-time capture cost: ~41 s at startup, 1.83 GB per GPU (chunked-prefill 16384 bucket set).

Note: the numbers above were measured with #27918 (restores the fused Triton MRoPE path under BCG) applied on top; that fix is complementary and tracked separately.

### Unit test

`test/registered/unit/server_args/test_server_args.py::TestBreakableCudaGraphMultimodalAllowlist` covers the new rule (allowlisted arch keeps `breakable`, non-allowlisted multimodal arch resolves to `disabled`) and allowlist membership. Verified together with the neighboring `TestCudaGraphDisaggregationRoles`: 7 passed.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #29230286789](https://github.com/sgl-project/sglang/actions/runs/29230286789)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29230286551](https://github.com/sgl-project/sglang/actions/runs/29230286551)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
