---
source_id: sglang-github-closed-issues-prs
title: '[NPU] Add Ascend NPU support for DeepSeek-V4'
canonical_url: https://github.com/sgl-project/sglang/pull/25144
captured_at: '2026-07-05T02:14:10.241057+00:00'
content_hash: 48a93af318f663494bbda5caccb9a32a1e38dff5f69c311600494e2d0a0246be
---
# [NPU] Add Ascend NPU support for DeepSeek-V4

URL: https://github.com/sgl-project/sglang/pull/25144
State: closed
Labels: deepseek, npu, run-ci, jit-kernel
Closed at: 2026-06-18T07:30:26Z
Merged at: 2026-06-18T07:30:26Z

## Summary

Adds end-to-end Ascend NPU support for the **DeepSeek-V4** architecture, covering both the **V4-Flash** and **V4-Pro** variants (hybrid-SWA with c1 / c4 / c128 compression ratios, 256 experts, EP).

## What's new

### New NPU core files (DSV4 backend, pools, allocator)

| File | Change |
| --- | --- |
| `hardware_backend/npu/attention/ascend_dsv4_backend.py` | **new (1192)** — DSV4 NPU attention backend. Subclasses the Ascend backend, mixes in Compressor / C4-indexer, builds the PA_ND block tables for c4/c128/SWA/state, and drives `npu_sparse_attn_sharedkv` plus the on-chip fused compressor (incl. Walsh–Hadamard transform). |
| `hardware_backend/npu/dsv4_memory_pool.py` | **new (612)** — NPU-specific KV pools: paged `NPUCompressStatePool` (`cache_mode=1`, required by the fused compressor) replacing the ring buffer, plus a bf16 / PA_ND single-KV pool (A3 has no ring `cache_mode=2`). |
| `hardware_backend/npu/dsv4_allocator.py` | **new (580)** — SWA + c4/c128 paged allocator: on top of the parent full/SWA slots, allocates per-ratio compressed-KV slots and tail state slots, returning a packed `DSV4OutCacheLoc` bundle. |
| `hardware_backend/npu/dsv4_common_hooks.py` | **new (354)** — hooks called from `mem_cache/common.py`: after each alloc_extend / decode, unpack `batch.out_cache_loc_dsv4` and write each pool's slots into the per-req tables (no-op off the DSV4 path). |
| `hardware_backend/npu/dsv4_req_to_token_pool.py` | **new (142)** — per-request mapping pool: adds swa / c4 / c128 / c4_state / c128_state auxiliary tables on top of `ReqToTokenPool` for paged block-table construction. |

### Framework integration (allocation / forward-batch / scheduling)

| File | Change |
| --- | --- |
| `mem_cache/common.py` | Platform-agnostic alloc flow wired for DSV4: compute `DSV4StateLens`, stash the allocator bundle in `batch.out_cache_loc_dsv4`, and on NPU invoke the dsv4 hooks to fill per-req tables. |
| `model_executor/forward_batch_info.py` | Add `DSV4OutCacheLoc` (six-tuple slot bundle) and `DSV4StateLens` dataclasses, plus an `out_cache_loc_dsv4` field on `ForwardBatch`. |
| `model_executor/model_runner_kv_cache_mixin.py` | Pool init dispatches to `DSV4NPUReqToTokenPool` / `DSV4NPUTokenToKVPool` for "DSV4 and NPU", and recomputes state-pool size by the NPU paged formula. |
| `managers/schedule_batch.py` | Req / ScheduleBatch compute DSV4 state-lens (`_compute_dsv4_state_lens_{extend,decode}`) so the allocator can size compressed-state slots. |
| `mem_cache/deepseek_v4_memory_pool.py` | Factor the base DSV4 KV pool's state-pool / single-KV factory methods into overridable hooks so the NPU subclass can swap in paged / bf16 variants (CUDA fp8 layout unchanged). |
| `mem_cache/deepseek_v4_compress_state.py` | Factor state-pool sizing into an interface overridable by `NPUCompressStatePool` (paged vs ring). |
| `arg_groups/deepseek_v4_hook.py` | DSV4 launch hook forces the prefill/decode attention backend to `dsv4` on NPU (overriding the generic NPU `ascend` default). |

### Attention / RoPE / model

| File | Change |
| --- | --- |
| `models/deepseek_v4.py` | NPU branches in the model: `torch_npu.npu_rms_norm` instead of triton RMSNorm, torch_npu binding, NPU RoPE. |
| `layers/deepseek_v4_rope.py` | NPU interleaved-RoPE fallback `v4_rope_inplace_npu` + contiguous cos/sin cache; tilelang import made optional so the module loads on Ascend images. |
| `layers/attention/dsv4/compressor.py` | Compressor gains `forward_npu`: delegates compression to `attn_backend.forward_compress` in natural-ape layout (incl. CP all-gather). |
| `layers/mhc.py` | mhc fused kernel makes its tilelang import optional so the module loads on NPU images without tilelang. |
| `layers/attention/attention_registry.py` | Register the `dsv4` backend; on NPU resolves to the Ascend V4 subclass in `ascend_dsv4_backend`. |
| `hardware_backend/npu/attention/ascend_backend.py` | Ascend base backend gains the few hooks / fields the DSV4 subclass needs. |

### Quantization / MoE / misc

| File | Change |
| --- | --- |
| `layers/quantization/compressed_tensors/.../compressed_tensors_w8a8_int8_moe.py` | New `NPUCompressedTensorsW8A8Int8DynamicMoE` scheme wiring W8A8-int8 MoE to the NPU `NPUW8A8Int8DynamicMoEMethod` kernel. |
| `layers/quantization/modelslim/modelslim.py` | ModelSlim recognizes DSV4 (`hc_head_` prefix) and remaps weight names to DeepSeek HF format. |
| `hardware_backend/npu/moe/topk.py` | Add `fused_hash_topk_npu` routing via `torch.ops.custom.npu_moe_gating_top_k`. |
| `layers/moe/hash_topk.py` | Hash-topk layer gains an NPU branch routing to `fused_hash_topk_npu`. |
| `speculative/draft_utils.py` | Add a `dsv4` entry to the spec-decode backend table; its NPU draft path reuses the Ascend multi-step draft backend. |
| `layers/communicator.py` | NPU branch importing `npu.cmo.prepare_weight_cache`. |
| `hardware_backend/npu/graph_runner/npu_graph_runner.py` | Minor NPU graph-runner adaptation for the DSV4 path. |
| `hardware_backend/npu/utils.py` | NPU default-args tweak (page_size / attention-backend default). |

## Launch command (NPU)

```bash
# --- Ascend toolkit env ---
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /usr/local/Ascend/nnal/atb/set_env.sh
source /usr/local/Ascend/ascend-toolkit/latest/opp/vendors/customize/bin/set_env.bash
source /usr/local/Ascend/ascend-toolkit/latest/opp/vendors/custom_transformer/bin/set_env.bash

# --- NPU runtime ---
export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export STREAMS_PER_DEVICE=32
export INF_NAN_MODE_FORCE_DISABLE=1            # required: W8A8 overflow else produces NaN

# --- DeepEP ---
export HCCL_BUFFSIZE=2000
export DEEP_NORMAL_MODE_USE_INT8_QUANT=1
export SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=64

# --- DSV4 ---
export IS_DEEPSEEK_V4=1
export USE_FUSED_HC_PRE_ASCENDC=1
export SGLANG_DSV4_NPU_FUSED_COMPRESSOR=1
export SGLANG_DSV4_NPU_FUSED_COMPRESSOR_PREFILL=0

# --- skip GPU-only branches (modelslim W8A8 weights have no blockwise-FP8 scales) ---
export SGLANG_OPT_FP8_WO_A_GEMM=0              # else MQALayer.__init__ asserts on W8A8
export SGLANG_OPT_USE_OVERLAP_STORE_CACHE=False
export FORCE_DRAFT_MODEL_NON_QUANT=1
export SGLANG_DSV4_FP4_EXPERTS=False
export SGLANG_OPT_FUSE_WQA_WKV=0
export SGLANG_OPT_BF16_FP32_GEMM_ALGO=torch
export SGLANG_OPT_USE_FUSED_HASH_TOPK=False
export SGLANG_OPT_USE_TILELANG_MHC_PRE=False
export SGLANG_OPT_DEEPGEMM_HC_PRENORM=False
export SGLANG_OPT_USE_TILELANG_MHC_POST=False

# --- launch (tp=dp=16, max-running-requests=16) ---
python3 -m sglang.launch_server \
    --model-path /path/to/DeepSeek-V4-Flash-W8A8 \
    --trust-remote-code \
    --device npu --attention-backend dsv4 \
    --quantization modelslim --kv-cache-dtype auto \
    --tp-size 16 --dp-size 16 --enable-dp-attention --enable-dp-lm-head \
    --moe-a2a-backend deepep --deepep-mode auto \
    --page-size 128 --max-running-requests 16 \
    --mem-fraction-static 0.65 \
    --disable-radix-cache --chunked-prefill-size -1 \
    --disable-overlap-schedule --skip-server-warmup \
    --watchdog-timeout 9000 \
    --cuda-graph-bs 1 2 4 \
    --host 0.0.0.0 --port 30000
```

## Accuracy

Evaluated with [EvalScope](https://github.com/modelscope/evalscope) against the NPU server (DeepSeek-V4-Flash-W8A8, modelslim, `--attention-backend dsv4`, full DP-attention), OpenAI-compatible API, `temperature=1`, `top_p=1`.

| Benchmark | Mode | Accuracy |
| --- | --- | ---: |
| AIME 2026 (30 questions) | thinking on | **96.67%** (29/30) |
| GPQA-Diamond (198 questions) | thinking on | **86.36%** (171/198) |
| GPQA-Diamond (198 questions) | thinking off | **73.23%** (145/198) |

## Known limitations / follow-ups

- **A3 NPU has no fp8 / fp4** — KV cache stays `bf16`, quant route is W8A8-int8 throughout, gated by `_is_npu`.
- **CI on NPU** — would need an NPU runner; please advise.































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #27741539561](https://github.com/sgl-project/sglang/actions/runs/27741539561)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #27741539537](https://github.com/sgl-project/sglang/actions/runs/27741539537)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
