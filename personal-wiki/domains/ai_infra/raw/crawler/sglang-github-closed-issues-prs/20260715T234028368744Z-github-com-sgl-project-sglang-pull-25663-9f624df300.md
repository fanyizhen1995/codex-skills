---
source_id: sglang-github-closed-issues-prs
title: '[MoE Refactor] [NPU] Refactor Ascend MoE implementation to reduce code duplication
  and align with community design'
canonical_url: https://github.com/sgl-project/sglang/pull/25663
captured_at: '2026-07-15T23:40:28.368744+00:00'
content_hash: 9f624df30003574c067dc572494533e5f033d8af6fc7fd0d71e41ca0713031e8
---
# [MoE Refactor] [NPU] Refactor Ascend MoE implementation to reduce code duplication and align with community design

URL: https://github.com/sgl-project/sglang/pull/25663
State: closed
Labels: documentation, quant, amd, Multi-modal, deepseek, speculative-decoding, hicache, npu, run-ci, diffusion, model-gateway, jit-kernel
Closed at: 2026-07-15T11:59:42Z
Merged at: 2026-07-15T11:59:42Z

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Overview

This PR addresses two major issues in the current Ascend MoE (Mixture of Experts) implementation:

1. **High code duplication** – Many places required changes whenever the MoE logic was updated, leading to high maintenance overhead and inconsistency risks.
2. **Deviation from community design** – dispatching and grouped-GEMM were hard‑coded in a monolithic `apply` flow and scattered across multiple files to handle different quantization formats, blocking integration with the standard **All‑to‑All backend** and **MoE Runner** pattern defined in [#8715](https://github.com/sgl-project/sglang/issues/8715).

This PR solves both issues with a clean **issue → solution** approach:

- **5‑component decomposition** eliminates duplication and makes each piece independently testable and swappable which allow, for example independent quantization **for each matmul**.
- **New Ascend MoE Runner** and **Ascend A2A Backend** fully align with the community routing architecture and separate computation from communication.

The result is a maintainable, extensible NPU MoE stack that works uniformly across all quantization schemes (Unquant, AWQ, GPTQ, ModelSlim, CompressedTensors, GGUF) and all dispatchers (NPU native, DeepEP normal/low‑latency, FuseEP).

## Issue 1: Code Duplication → 5‑Component Decomposition

### The problem

Before this PR, the MoE forward pass was duplicated in multiple places. Each copy repeated the same sequence of steps: ```tokens routing```, ```first w13 gate_up_proj grouped matmul```, ```activation```, ```second w2 down_proj grouped matmul```, and ```finalize routing```. When a new kernel arrived or a bug was found, developers had to track down **every** copy and apply the same fix. This was error‑prone and discouraged experimentation.

### Legacy Code Disunity Map
```text
LEGACY FRAGMENTED FILESYSTEM
python/sglang/srt/layers/quantization/
 │
 ├── 📄 unquant.py ──► [Routing V2] ──► [w13 MatMul] ──► [Swiglu, Gelu, Swiglu_oai] ──► [w2 MatMul] ──► [Finalize]
 ├── 📄 gguf.py ──► [Routing V1] ──► [w13 MatMul] ──► [Swiglu] ──► [w2 MatMul] ──► [Finalize]
 │
‎python/sglang/srt/hardware_backend/npu/quantization/fused_moe_method_npu.py
 │
 ├── 📄 w4a4 apply() ──► [Routing V2] ──► [w13 MatMul] ──► [Swiglu] ──► [w2 MatMul] ──► [Finalize]
 │    │         
 │    └── 📄 w4a4 apply_without_routing() ──► [w13 MatMul] ──► [Swiglu] ──► [w2 MatMul]
 │
 ├── 📄 w4a8 apply() ──► [Routing V2] ──► [w13 MatMul] ──► [Swiglu] ──► [w2 MatMul] ──► [Unpermute]
 │    │       
 │    └── 📄 w4a8 apply_without_routing() ──► [w13 MatMul] ──► [Swiglu_quant] ──► [w2 MatMul]
 │
 ├── 📄 w8a8 apply_prefill() ──► [Routing V1] ──► [w13 MatMul] ──► [dequant_swiglu_quant] ──► [w2 MatMul] ──► [Finalize]
 │    │
 │    📄 w8a8 apply_decode() ──► [Routing V2] ──► [w13 MatMul] ──► [dequant_swiglu_quant] ──► [w2 MatMul] ──► [Unpermute]
 │    │     
 │    └── 📄 w8a8 apply_without_routing() ──► [w13 MatMul] ──► [dequant_swiglu_quant] ──► [w2 MatMul]
 │
 └── 📄 w4a16 apply() ──► [Routing V1] ──► [w13 MatMul] ──► [Swiglu] ──► [w2 MatMul] ──► [Finalize]
      │     
      └── 📄 w4a16 apply_without_routing() ──► [w13 MatMul] ──► [Swiglu] ──► [w2 MatMul]
                                                                       │                                                                                             
                                   🚨 Maintenance Bottleneck: ─────────┘
                                   Updating any kernel or fixing a bug required 
                                   updating identical code logic across ALL 10 isolated places.
```

### The solution: 5 reusable components

<img width="546" height="435" alt="image" src="https://github.com/user-attachments/assets/803c32d6-e5c2-4512-aa34-278c20395e7a" />

We split the pipeline into five abstract components and just call each of them when they are needed, each with a clear `Base*` interface:

| Component | Responsibility | File path |
|-----------|----------------|----------------|
| **Initial Routing** | Maps tokens to target experts (top-k processing and token permutation) | [python/sglang/srt/hardware_backend/npu/moe/init_routing.py](https://github.com/sgl-project/sglang/pull/25663/changes#diff-f02f1521aae576082ebb67fce7f43977bfbfc95395cd80266167d91696a08d78) |
| **Hidden States Quant** | Optional dynamic/static quantisation of activations before matmul | [python/sglang/srt/hardware_backend/npu/moe/hidden_states_quant.py](https://github.com/sgl-project/sglang/pull/25663/changes#diff-2cc1b30a86e9efba3c06e5bd2c7d6d4e8cfbfecbcc130a16d9fdc856fbe45126) |
| **Grouped Matmul** | Coordinates expert-parallel matrix multiplications across arbitrary precision variants (FP16, W4A4, W8A8, etc.) | [python/sglang/srt/hardware_backend/npu/moe/matmul.py](https://github.com/sgl-project/sglang/pull/25663/changes#diff-a1fa2ce9efcc44edc1fa3f19f3e2183227da34602667cee2b8cee2c724150908) |
| **Activation** | Processes non-linear operations (SwiGLU, GELU) along with integrated dequantization or/and quantization steps | [‎python/sglang/srt/hardware_backend/npu/moe/activation.py](https://github.com/sgl-project/sglang/pull/25663/changes#diff-ba4346a5deb6a84d17b721af656d30bf50c1164e16b21db349e2ffaf142fdc7c) |
| **Finalize Routing** | Reassembles expert outputs into original token order | [python/sglang/srt/hardware_backend/npu/moe/finalize_routing.py](https://github.com/sgl-project/sglang/pull/25663/changes#diff-9045dc3acd5ac53496c175a744aa85c0137cbb1ee5d1779a0d1b4704188c37c5)  |

Every component has NPU‑specific implementations (e.g., `NPUMoEInitRouting_v1`, `NPUSwigluQuant`, `GroupedMatmul`). The runner selects the right set at runtime based on the model config and quantization scheme. 

Example of [‎python/sglang/srt/hardware_backend/npu/moe/activation.py](https://github.com/sgl-project/sglang/pull/25663/changes#diff-ba4346a5deb6a84d17b721af656d30bf50c1164e16b21db349e2ffaf142fdc7c) scheme

```text
Activation.py Orchestration Layer
 ├── BaseActivation (Abstract Base Interface)
 │    └── Unified execution signature: forward(x, *args, **kwargs)
 │
 ├── Standard Precision Kernels
 │    ├── NPUSwiglu             -> Traditional SwiGLU operation
 │    ├── NPUGeluAndMul         -> GELU-based gated linear unit variations
 │    └── NPUSwigluOAI          -> Open AI style compatible SwiGLU formulation
 │
 ├── Quantization & Specialized Kernels
 │    ├── NPUSwigluQuant           -> SwiGLU with integrated INT8 quantization processing
 │    ├── NPUSwigluQuantWithScales -> SwiGLU with precision-aware scaling factor handling
 │    └── NPUSwigluStepAndMul      -> Multi-step fused activation logic
 │
 └── Dispatcher Integrations
      └── NPUSwigluDeepEPKernel    -> Low-latency communication-fused activation for DeepEP
```

## Issue 2: Community Design → Ascend MoE Runner & A2A Backend

The legacy codebase lacked alignment with the standardized SGLang community routing model laid out in [issue #8715](https://github.com/sgl-project/sglang/issues/8715). Multi-NPU Tensor Parallelism (TP) was implemented via fragmented, ad-hoc routines. Functions like ```apply()``` and ```apply_without_routing()``` mixed core mathematical calculations with distributed communication primitives, preventing proper support for optimized dispatches like DeepEP. 

### The solution: Unified AscendRunnerCore & Ascend A2A Backend

We designed a unified MoE Runner (AscendRunnerCore) to manage the centralized execution block, completely deprecating legacy apply_without_routing routines. Alongside this, we implemented a dedicated NPU All-to-All (A2A) backend leveraging and follow community scheme:

```text
[input_hidden_states]
          |
          v
     TopK.forward -> `select_experts` / `triton_kernels.routing` / bypass
          |
          V
     [TopKOutput]
          |
          v
   FusedMoE.forward -> Dispatcher.dispatch -> DeepEP / AscendTP <-- NEW A2A Backend
          |                     |
          |                     v
          |              [DispatchOutput]
          |                     |
          |                     v
          |             quant_method.apply -> AscendMoeRunner.run <-- NEW MoE Runner
          |                     |                                |
          |                     |                                v
          |                     |            pre-permute + grouped_gemm + post-permute
          |                     |                                |
          |                     |--------------------------------
          |                     v
          |               [CombineInput]
          |                     |
          |                     v
          |            Dispatcher.combine -> DeepEP / AscendTP / bypass
          |                     |
          |---------------------                  
          v
[final_hidden_states]
```

### AscendMoERunner and  – from monolithic `apply` to composable stages

Structural Evolution: Old vs. New Execution Flow
The mathematical operations (matmul1, activation, matmul2) have been extracted from monolithic wrapper configurations into separate sequential execution stages managed cleanly by the new runner core:

<img width="1822" height="1782" alt="Untitled Diagram drawio" src="https://github.com/user-attachments/assets/cdfd87fb-9e57-424a-b74c-98118bf3ac23" />

- Matmul, activation, and the second matmul have been moved out of the old `apply` blob into **independent, swappable stages**.  
- The runner can now support **any** quantisation (unquant, W4A4, W8A8, etc.) by simply picking the right component implementations.  
- It fully supports DeepEP normal and low‑latency modes through pre/post‑permute hooks, without duplicating the core pipeline.

### Mapping the old monolithic file to the new composable structure

The diff in `fused_moe_method_npu.py` looks large because we **deleted all the duplicated kernel‑calling logic** and replaced it with thin method wrappers.  
The actual computation was moved into five reusable components (listed in the table and picture above) and a new file that holds the `AscendMoERunner` orchestration.

| Old location (`fused_moe_method_npu.py`)              | New location(s)                                                                 |
|-------------------------------------------------------|----------------------------------------------------------------------------------|
| `npu_fused_experts_w4a4()`                            | Removed – handled by `AscendMoERunner` + `AscendTPDispatcher`  |
| `npu_fused_experts()`                                 | Removed – same pattern as above, now in `AscendMoERunner` + `AscendTPDispatcher`,  bf16 code is separated into new `NPUUnquantMoEMethod` in new `moe_methods.py` file |
| `npu_fused_experts_w8a8_decode()`                     | Removed – decode‑specific path merged with `npu_fused_experts()` prefill‑specific path (The measurements did not show the advantages of separation) |
| `npu_fused_moe_without_routing_weights_bf16()`        | Removed – logic moved to `AscendMoERunner` pre/post-permute DeepEP hooks |
| `fused_moe_npu()` (deprecated)                        | Kept with deprecation warning to ensure backward compatibility with models that do not use the FusedMoE class yet |
| `maybe_apply_deepep_npu()`                            | Removed – logic moved to `AscendMoERunner` pre/post-permute DeepEP hooks     |
| `maybe_apply_fuseep_weights()`                        | The logic is preserved and adapted to the existing structure in new `moe_methods.py`, does not use Runner infrastructure |
| `NPUW4A4Int4DynamicMoEMethod`                         | Rewritten as `NPUW4A4Int4MoEMethod` in new `moe_methods.py` – now it is used for each MatMul separately   |
| `NPUW8A8Int8DynamicMoEMethod`                         | Rewritten as `NPUW8A8Int8MoEMethod` – same way                          |
| `NPUW4A8Int8DynamicMoEMethod`                         | Rewritten as `NPUW4A8Int8MoEMethod` – same way                            |
| `NPUW4A16Int4DynamicMoEMethod`                        | Rewritten as `NPUWNA16Int4MoEMethod` – same way                           |
| `_NPUFusedMoEMethodBase`                              | Replaced by `_NPUMoEMethodBase` in new `moe_methods.py` file                                     |

The **new file** (`python/sglang/srt/hardware_backend/npu/quantization/moe_methods.py`) now contains **only** the configuration and lightweight delegation code; the heavy logic lives in:

- `AscendMoERunner` – `python/sglang/srt/layers/moe/moe_runner/ascend.py`
- `AscendTPDispatcher`   – `python/sglang/srt/layers/moe/token_dispatcher/ascend_tp.py`
- `InitRouting` – `python/sglang/srt/hardware_backend/npu/moe/init_routing.py`
- `HiddenStatesQuant` – `python/sglang/srt/hardware_backend/npu/moe/hidden_states_quant.py`
- `GroupedMatmul` – `python/sglang/srt/hardware_backend/npu/moe/matmul.py`
- `Activation` – `python/sglang/srt/hardware_backend/npu/moe/activation.py`
- `FinalizeRouting` – `python/sglang/srt/hardware_backend/npu/moe/finalize_routing.py`

### AscendA2ABackend – clean separation of TP communication

Tensor‑parallel expert routing (All‑to‑All) used to be buried inside the old `apply` functions. The new **AscendA2ABackend** extracts this into a dedicated communication module that implements:

- `init_routing` – dispatches tokens to the correct expert shards across NPUs.  
- `finalize_routing` – collects sharded expert outputs and reassembles them in the original token order.

**Advantages:**

1. **Testability** – the routing logic can be unit‑tested in isolation (no real computation needed).  
2. **Portability** – different hardware backends (e.g., NVIDIA NCCL, Ascend HCCL) can provide their own A2A implementations while the MoE runner stays unchanged.  
3. **Extensibility** – upcoming communication backends (DeepEP, FuseEP) can be integrated without touching the core MoE logic.

By moving TP init/finalize routing out of the monolithic `apply` and into this backend, the architecture now mirrors exactly the community pattern from [#8715](https://github.com/sgl-project/sglang/issues/8715), enabling future shared improvements across all backends.

---

## Additional Improvements (Side Effects of the Refactor)

- **AWQ**, **GGUF**, **GPTQ**, **Auto-round** now can be used with DeepEP (previously it didn't work for this quantization frameworks).
- **AWQ** models compatibility were improved by implementing new unquant path for Linear to to circumvent ```torch_npu.npu_weight_quant_batchmatmul``` kernel limitations. 
- **AWQ** MoE now uses 2x times less memory after ```process_weights_after_loading``` redesign.
- **Modelslim** now supports mix-bits quantized MoE models (with different w13/w2 quant schemes).
- **GGUF** performance were improved by adding npu_format_cast to enable NZ weights format.
- **GPTQ** performance and accuracy were improved by using new kernels versions.
- **GPTQ** add scales expanded size does not match K_shard warning and support negative-scale correction skipping.
- **W4A4 NZ format fix** – the NPU kernel now correctly uses the native NZ memory layout (instead of forced ND), giving up to **5-10% speedup**.  
- **Improved int4 packing** – support improved int4 packing using ```SGLANG_NPU_W4A4_NEW_PACKING=True``` env variable, two int4 values are now stored in one int8, halving the memory footprint during weight loading.  
- **def fused_moe_npu()** now deprecated and will be removed in future releases. 

Reverts https://github.com/sgl-project/sglang/pull/29503 to avoid performance drops

---

## Accuracy Tests

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->

<img width="2039" height="627" alt="image" src="https://github.com/user-attachments/assets/2eea9438-0e27-4c24-ac4d-ce958b08c0ac" />

## Speed Tests and Profiling

<!-- If this pull request impacts inference speed, provide benchmarking and profiling results. -->

<img width="1742" height="495" alt="image" src="https://github.com/user-attachments/assets/090fd789-bfde-4b06-8a8e-50e6e8312edd" />

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
4. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
5. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.















































































































































































































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:hourglass_flowing_sand: [Run #29395737061](https://github.com/sgl-project/sglang/actions/runs/29395737061)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29395736920](https://github.com/sgl-project/sglang/actions/runs/29395736920)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
