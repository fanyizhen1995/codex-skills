---
source_id: sglang-github-closed-issues-prs
title: Development Roadmap (2026 Q1)
canonical_url: https://github.com/sgl-project/sglang/issues/12780
captured_at: '2026-07-06T02:14:53.058622+00:00'
content_hash: 566ec56bb2cacf9a3eb2fdbf0984b5a0c737ee039dd83eb030d9333119588845
---
# Development Roadmap (2026 Q1)

URL: https://github.com/sgl-project/sglang/issues/12780
State: closed
Labels: inactive
Closed at: 2026-07-06T00:41:14Z
Merged at: 

# SGLang Roadmap — 2026 Q1

*Contributions and feedback are welcome*. [Join Slack](https://slack.sglang.ai).

## Focus

- **Feature compatibility & reliability**: Full compatibility and production-level reliability across P/D disaggregation, all parallelisms, speculative decoding, HiCache, and load balancing.
- **Usability**: Easy installation on NV/AMD/TPU/CPU; simple large-scale deployment (k8s, OME).
- **Kernel optimization** for next-gen hardware (GB300/GB200, B300/B200, MI350/MI355, TPU).
- **Reinforcement learning** framework integration and training-inference mismatch mitigation.
- **Multimodal**: Enhance diffusion models for video and image generation. Omni model support.

## Base Engine Features

- **Turn on overlap scheduler for speculative decoding by default**
  PoC: @hnyls2002  
  Slack: [#spec-decoding](https://sgl-fru7574.slack.com/archives/C09KELDAD8U)  
  Issue: https://github.com/sgl-project/sglang/issues/11762

- **Turn on prefill CUDA graph by default**  
  PoC: @Oasis-Git @ispobock @BBuf  
  Slack: [#piecewise-cuda-graph](https://sgl-fru7574.slack.com/archives/C09KZ1MV013)  
  Issue: https://github.com/sgl-project/sglang/issues/11490

- **General memory pool and prefix cache for hybrid models**  
  PoC: @cctry @xiezhq-hermann  
  Slack: [#prefix-cache](https://sgl-fru7574.slack.com/archives/C09QRSD94KE), [#kv-cache-store](https://sgl-fru7574.slack.com/archives/C095B2L7UEB)  
  Issue: https://github.com/sgl-project/sglang/issues/12587

- **Mixed chunked prefill refactor** 
  PoC: @hzh0425 @yizhang2077 
  Issue: https://github.com/sgl-project/sglang/issues/13626

- **Torch compile stack** (Looking for PoC)  
  Slack: [#torch-compile](https://sgl-fru7574.slack.com/archives/C09C35Q8ZGE)  
  PR: https://github.com/sgl-project/sglang/pull/10987  
  Issue: https://github.com/sgl-project/sglang/issues/10118

- **SRT core/plugin refactor**
  Goal: make the core reusable, so people can do customization easily and maintain their out-of-the-tree code.

- **DP attention and attention backend refactor**
  Goal: make attention backends fully stateless, unify the sync positions of dp attention.

<img width="707" height="220" alt="Image" src="https://github.com/user-attachments/assets/4536047f-bfa2-4845-9891-3f8b83e44c6f" />

## Parallelism

- **Pipeline parallelism** refactor for long-context prefill and high-throughput decoding  
  PoC: @ShangmingCai  
  Slack: [#pipeline-parallel](https://sgl-fru7574.slack.com/archives/C09J7BY42PP)  
  Issue: https://github.com/sgl-project/sglang/issues/11857

- **Expert parallelism** refactor  
  PoC: @ch-wan  
  Slack: [#expert-parallel](https://sgl-fru7574.slack.com/archives/C09QRUHFJTE)  
  Issue: https://github.com/sgl-project/sglang/issues/8715  
  Elastic parallel PRs: https://github.com/sgl-project/sglang/pull/10423, https://github.com/sgl-project/sglang/pull/11837

- **Context parallelism** 
Prefill CP: https://github.com/sgl-project/sglang/issues/16632
Megatron SP: https://github.com/sgl-project/sglang/pull/12820
Decode CP:
  - https://github.com/sgl-project/sglang/pull/14982
  - https://github.com/sgl-project/sglang/pull/14194
  - https://github.com/sgl-project/sglang/pull/18167
  - https://github.com/sgl-project/sglang/issues/19436

- **Compatibility goals**  
  - All parallelisms + speculative decoding  
  - All parallelisms + PD disaggregation  
  - Multiple load balancing strategies for DP attention/system (minimal tokens, shortest queue) https://github.com/sgl-project/sglang/issues/16080

- **GB200/GB300 NVL72 optimizations**  
  PoC: @Fridge003 @fzyzcjy  
  More details in PD Disaggregation/Large Scale Serving section of #17130
  Slack: [#deepseek-large-scale-serving](https://sgl-fru7574.slack.com/archives/C08QGMU93GX)

## Server Reliability

- Illegal memory access fixes. #11968
- Runtime memory/paging checker.
- Grammar crash fault tolerance.
- Server crash fault tolerance.

## Kernel

- JIT kernels 
   Roadmap: #17035 #17865
   PoC: @DarkSharpness  
 

- Integrate Flashinfer kernels
  More details in Flashinfer section of https://github.com/sgl-project/sglang/issues/17130
  Slack: [#flashinfer-kernels](https://sgl-fru7574.slack.com/archives/C09NG5Q0LEP)

- Tune FP8 gemm in Cutlass  
  Slack: [#kernel-dev](https://sgl-fru7574.slack.com/archives/C09NFSN642G)

- Communication kernel work  
  Slack: [#kernel-dev](https://sgl-fru7574.slack.com/archives/C09NFSN642G)  
  - NCCL symmetric memory (PRs: https://github.com/sgl-project/sglang/pull/8238, https://github.com/sgl-project/sglang/pull/12572)  
  - Overlap TP communication with compute (e.g., https://github.com/sgl-project/sglang/pull/9058)  
  - Integrate additional A2A kernels (e.g., pplx)

- Automated nightly fusion detection  
  Workflow: https://github.com/sgl-project/sglang/actions/runs/19004823026  
  Slack: [#ci-cd-build-release](https://sgl-fru7574.slack.com/archives/C09HCG2HM1T)

## Speculative Decoding
- General speculative algorithm abstraction to support multiple algorithms  
- Hybrid algorithm combining Eagle and ngram  
- Adaptive algorithm that adjusts speculative parameters during runtime  
- Support for dllm draft models in sglang, associated with SpecForge  https://github.com/sgl-project/SpecForge/issues/412 @jinleic  @yilian49 @xiaomin-D @sleepcoo 
- Slack: [#spec-decoding](https://sgl-fru7574.slack.com/archives/C09KELDAD8U)

## PD Disaggregation
- Support radix cache on decode engines https://github.com/sgl-project/sglang/pull/19746
- Refactor scheduler loop to reuse more code  
- More plans: https://github.com/sgl-project/sglang/issues/8210  
- Auto scaling in OME  
- Comprehensive NIXL and Dynamo integration  
- Slack: [#pd-disaggregation](https://sgl-fru7574.slack.com/archives/C08AP4WU8P3)

## KV Cache System & Memory Pool

- PoC: @xiezhq-hermann 
  Issue: https://github.com/sgl-project/sglang/issues/12826.
  slack [#kv-cache-store](https://sgl-fru7574.slack.com/archives/C095B2L7UEB)

- Sparse attention and KV cache scheduler for GPU/CPU
  PR: https://github.com/sgl-project/sglang/pull/11191

## Diffusion (Multimodal Generation)
- PoC: @mickqian
- Roadmap: 
   - 25Q3: #12799 
   - 26Q1: #18286
- Slack: [#diffusion](https://sgl-fru7574.slack.com/archives/C09P0HTKE6A)

## Multimodal Models

- Day-0 support for major models; add more OCR models  
  Contributors: @mick @JustinTong0323 @yuan-luo
- Performance improvements: better prefix & embedding cache
- Faster CUDA IPC in MQ for large video/images  
  PR: https://github.com/sgl-project/sglang/pull/11917
- Omni Support #16546 

  Slack: [#multi-modal](https://sgl-fru7574.slack.com/archives/C087RGPBC81)

## Quantization

- General support for various quantization formats and refactor
  Issue: https://github.com/sgl-project/sglang/issues/15194
- ModelOpt support  
  PoC: @Edwardf0t1  
  More details in Model Optimizer section of https://github.com/sgl-project/sglang/issues/17130
  Slack: [#modelopt](https://sgl-fru7574.slack.com/archives/C09NPJSBR32)
- Communication quantization (fp4/fp8 allreduce/allgather/alltoall)

  Slack: [#quantization](https://sgl-fru7574.slack.com/archives/C08976KGBQF)

## Multi-LoRA Serving

- Major roadmap: https://github.com/sgl-project/sglang/issues/2929  
  PoC: @Fridge003
- LoRA for speculative decoding #12903 
  Contributor: @ConnorLi96 @lifuhuang 
- Overlap Weight Loading with Compute https://github.com/sgl-project/sglang/pull/15512
  Contributor: @glenliu21 @ConnorLi96 @lifuhuang 
- LoRA for MoE layers  #14105
  Contributors: @ConnorLi96 @Jonahcb
  
Slack: [#lora](https://sgl-fru7574.slack.com/archives/C09JDPAP3FA)

## Prefill-Only
- Major roadmap: https://github.com/sgl-project/sglang/issues/15344
  PoC: @sundar24295s 

Slack: [#prefill-only](https://sgl-fru7574.slack.com/archives/C0AA2PD8CRW)

## RL Framework Integration

- AReaL, slime, verl integration (sorted alphabetically) 
- Customized weight refitting from RDMA, etc @zhaochenyang20 @JD-ETH
- Open recipe of large-scale MoE training (Deepseek/Kimi/GLM) + GRPO training  
- Systematic and algorithm mitigation for training-inference mismatch @zhaochenyang20 @fzyzcjy @Fridge003 @zyzshishui 
- Support SGLang Gateway as the DP scheduler for rollout in the RL framework
- Tinker-like serverless RL APIs; @zhaochenyang20 
- Native NVFP8 Training; @GeLee-Q @xieck13 @fy1214
- VLM RL with FSDP; @nanjiangwill @minleminzui 
- Speculative Training; @guapisolo 

Slack: [#reinforcement-learning](https://sgl-fru7574.slack.com/archives/C09HMG80PNE), [#slime-rl-framework](https://sgl-fru7574.slack.com/archives/C09E0QSGARH)

## Diffusion Language Models (DLLMs)

- PoC: [Zehuan Li](https://github.com/ClawSeven), [Jinwei Yao](https://github.com/Monstertail), [Chenyang Zhao](https://github.com/zhaochenyang20)

- RFC: [Block Diffusion Large Language Model (dLLM) Framework](https://github.com/sgl-project/sglang/issues/12766)

- Roadmap: [[Roadmap] Diffusion LLMs (2025 Q4 & 2026 Q1) #14199](https://github.com/sgl-project/sglang/issues/14199)

## Hardware

- AMD roadmap (2025 Q4): @HaiShaw  
  - https://github.com/sgl-project/sglang/issues/12890
- TPU roadmap (2025 Q4)
  - https://github.com/sgl-project/sglang-jax/issues/190
  - Slack: [#dev-jax-tpu](https://sgl-fru7574.slack.com/archives/C09EBE5HT5X)
- NPU roadmap (2025 Q4): @iforgetmyname @ZhengdQin 
  - https://github.com/sgl-project/sglang/issues/13664
- Intel CPU/XPU roadmap (2025 Q4): 
  - https://github.com/sgl-project/sglang/issues/12802
  - https://github.com/sgl-project/sglang/issues/12806
- Better multi-backend abstraction: @Alcanderian

## Model Coverage

- Day-0 model support for all major models  
  PoC: @wisclmy0611 @JustinTong0323  
  Slack: [#dev](https://sgl-fru7574.slack.com/archives/C07PEP77X6F)

## Model Gateway & API Layer

- Support multimodality and image processor in gRPC mode
- Support PII and classify API for classifying intent and complexity of the input
- Semantic Routing Support
- Allow Gateway to actively listen to SGLang server's KV cache events to better handle routing decisions in gRPC mode
- Allow SGLang server to start with both gRPC and HTTP server
- Model Gateway terminal UI
- Reactive UI to launch workers remotely; this should support both local machines and remote
- Natively support Anthropic Message API instead of wrapping around chat completion in gRPC mode
- Gateway SDK, supporting GoLang, Python, and Node.js for every Rust crate (policies, tokenizer, parsers, etc)
- Metrics enhancement, including tracing, model-specific metrics (TTFT, TPOT, etc)

- PoC: @slin1237  @CatherineSue 
  Issue: https://github.com/sgl-project/sglang/issues/13098
  Slack: [#router-sig](https://sgl-fru7574.slack.com/archives/C09E1U4LL6Q)

## Tracing and Profiling
 - Roadmap of request tracing: HiCache, PP, and SD. #13511 

## Advanced Priority Scheduling

- https://github.com/sgl-project/sglang/issues/13526
  PoC: @harrisonlimh 

## CI / Release / Maintenance

- CI suites refactor: https://github.com/sgl-project/sglang/issues/13808
  - PoC: @alisonshao @Kangyan-Zhou 
- Improve [CI monitor](https://github.com/sgl-project/sglang/actions/workflows/ci-monitor.yml) workflow
  - Automatically track accuracy & performance metrics with standard format  
  - Regression detection & alerts
  - Add performance dashboard for popular model (deepseek r1) in track of performance changes

- Improve [nightly tests](https://github.com/sgl-project/sglang/actions/workflows/nightly-test.yml) 
  - Add more models (Deepseek, GPT-OSS, Qwen3-next)

- Full feature coverage CI with all combinations (every two days)

- Coverage of latest hardware (B300/GB200)
   More details in CI/CD section of https://github.com/sgl-project/sglang/issues/17130

Slack: [#ci-cd-build-release](https://sgl-fru7574.slack.com/archives/C09HCG2HM1T), [#help-desk](https://sgl-fru7574.slack.com/archives/C07EFURPNN9)
