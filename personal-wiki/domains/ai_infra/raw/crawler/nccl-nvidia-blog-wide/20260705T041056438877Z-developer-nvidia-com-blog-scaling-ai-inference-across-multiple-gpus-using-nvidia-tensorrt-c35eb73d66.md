---
source_id: nccl-nvidia-blog-wide
title: Scaling AI Inference Across Multiple GPUs Using NVIDIA TensorRT with Multi-Device
  Inference Support
canonical_url: https://developer.nvidia.com/blog/scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-with-multi-device-inference-support/
captured_at: '2026-07-05T04:10:56.438877+00:00'
content_hash: c35eb73d661d4b0fe8b89db86ff9c8ac92324072485f38d7220276daa114754d
---
# Scaling AI Inference Across Multiple GPUs Using NVIDIA TensorRT with Multi-Device Inference Support

URL: https://developer.nvidia.com/blog/scaling-ai-inference-across-multiple-gpus-using-nvidia-tensorrt-with-multi-device-inference-support/

RSS Summary:
<img alt="Decorative image." class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2026/06/AI-Inference-768x432.jpg" style="display: block; margin-bottom: 5px; clear: both;" title="AI-Inference" width="768" />Generative AI workloads are rapidly outgrowing the memory and compute budget of single GPUs. For inference developers building media generation pipelines, the...

Article Body:
Developer Tools & Techniques

 

 
 

 

 
English
中文

 

 

 
Scaling AI Inference Across Multiple GPUs Using NVIDIA TensorRT with Multi-Device Inference Support

 
 

 

 

 Jun 25, 2026
 

 

 By 
Peter Kisfaludi
, 
Zhaoyuan He
, 
Daisy Chu
, 
Joseph Loftin
 and 
Byungsoo Jeon
 

 

 

 
 
 

 
 

 Like

 

 

 

 
 Discuss (0)
 

 

 

 

 

 

 

 

 

 
L

 
T

 
F

 
R

 
E

 
 

 

 

 

 

 

 

 
AI-Generated Summary

 

 

 

 

 

 

 

 

 
Like

 

 

 

 

 

 

 
Dislike

 

 

 

 

 

 

 

 

 
TensorRT 11.0 introduced native multi-device inference, leveraging NVIDIA NCCL for high-throughput distributed collectives and enabling seamless scaling of generative AI pipelines across multiple GPUs, including edge deployments.
Context parallelism, supported via IDistCollectiveLayer primitives in TensorRT 11.0, partitions input sequences across GPUs and is optimized through strategies like AllGather KV, Ring Attention, and DeepSpeed Ulysses, each balancing compute, memory, and communication overhead for long-sequence attention workloads.
Benchmarks on NVIDIA Cosmos 3 and FLUX.1 pipelines indicate DeepSpeed Ulysses consistently delivers the lowest latency for diffusion-based media generation at extreme context lengths, while Ring Attention also provides strong scaling up to 4 GPUs.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

Generative AI workloads are rapidly outgrowing the memory and compute budget of single GPUs. For inference developers building media generation pipelines, the challenge is scaling across multiple devices without sacrificing the critical optimizations—like kernel fusions, memory planning, and quantization—that NVIDIA TensorRT delivers for production deployments. 

Multi-device inference support, a new feature introduced in TensorRT 11.0, brings native high-performance multi-GPU inference to the TensorRT runtime, enabling multi-device production deployments targeting edge devices.

Combining the multi-device inference support in TensorRT with 
Torch-TensorRT
, developers can convert and deploy massive PyTorch models out-of-framework, shattering single-device memory and compute limits.

Download TensorRT 11.0 with multi-device inference support from 
NVIDIA Developer Portal
 to unlock native, high-performance multi-device acceleration for your models.

NVIDIA NCCL: The transport layer for distributed inference

The NVIDIA Collective Communications Library (NCCL) provides high-performance multi-GPU and multi-node collective operations powering large-scale model training across thousands of GPUs. NCCL automatically selects the optimal transport for a given topology, abstracting NVIDIA NVLink, NVIDIA NVSwitch, PCIe, and InfiniBand behind a uniform interface. By integrating directly with NCCL, TensorRT inherits this transport optimization for inference workloads, when running multi-device inference. For more information on NCCL, see 
https://developer.nvidia.com/nccl
.

The new multi-device feature covers the full set of NVIDIA NCCL distributed collectives: 
AllReduce
, 
Broadcast
, 
Reduce
, 
AllGather
, 
ReduceScatter
, 
AlltoAll
, 
Gather
, and 
Scatter
.

Parallelism strategies for distributed inference

Distributed inference can be expressed using several parallelism strategies, each with different trade-offs between memory savings, compute scaling, and communication overhead. The most common strategies are tensor parallelism and context parallelism.

Tensor parallelism

In tensor parallelism, the weights of a single layer are partitioned across GPUs. Each GPU computes a shard of the layer’s matrix multiplication and then combines partial results through a collective to produce the full output. This reduces per-device memory weight, making it the natural (and often the only) choice when an individual layer’s weights exceed the memory of a single GPU, independent of the input sequence length or batch size. 

In a transformer block, column-parallel projections (for example, QKV and the MLP up-projection) are paired with row-parallel projections (the attention output and the MLP down-projection) so that each block requires only a single AllReduce, keeping communication overhead bounded.

 

 
Figure 1. Column-wise and row-wise parallel projections

Context parallelism 

In context parallelism, the input sequence is partitioned across GPUs along the sequence dimension. Each GPU processes only a slice of the sequence, while collective operations make the global sequence available where needed, such as during attention. Context parallelism is particularly effective for long-sequence workloads, where attention’s quadratic scaling with sequence length makes it the dominant consumer of compute and memory.

It is also an especially natural fit for diffusion and DiT models, whose bidirectional attention sidesteps the load-imbalance issues that arise with causal masks.

Read the 
Context Parallelism for Scalable Million-Token Inference
 article for additional details on context parallelism.

NVIDIA TensorRT 11.0 introduces support for the `IDistCollectiveLayer` primitives required by the various parallelization strategies. The remainder of this post focuses on context parallelism, which directly addresses the dominant cost in modern generative media pipelines: long-sequence attention.

Context parallelism for generative media

Diffusion-based image and video generation pipelines spend a large fraction of their compute and memory budget inside attention blocks operating over long token sequences. A high-resolution image latent or a multi-frame video clip can produce sequences of tens of thousands of tokens per block, and attention scales quadratically with sequence length.

AllGather KV

Context parallelism partitions the sequence across GPUs. Each rank processes a slice of the queries (Q) corresponding to its sequence partition. A straightforward way to implement context parallelism is the AllGather KV approach, where ranks exchange their key (K) and value (V) shards through an AllGather collective before computing local attention, enabling each rank to attend over the full sequence. The result is a per-rank attention output covering the full sequence at the cost of one additional collective per attention block, while the local Q × Kᵀ matrix multiplication shrinks proportionally to the number of ranks.

For video and high-resolution image diffusion, this trade-off compounds favorably across denoising steps. Communication overhead per step remains bounded by the sequence-dimension AllGather, while compute and memory savings apply to every attention layer in every step.

 

 
Figure 2. AllGather KV strategy for context parallelism

Ring Attention

Context parallelism can be implemented in various ways, each presenting distinct trade-offs. 

One potential improvement over the AllGather KV method is Ring Attention, where communication and computation are overlapped. This enables each GPU to process its local Q simultaneously as the K and V continuously stream past in a ring topology. Ring Attention also reduces the memory footprint: using an online softmax, the full-size K and V tensors do not need to be materialized on any GPU. Read the 
Ring Attention with Blockwise Transformers for Near-Infinite Context
 article to learn more about Ring Attention. 

 

 
Figure 3. Ring Attention strategy for context parallelism

DeepSpeed Ulysses

For long context (tens of thousands of tokens), an alternative context parallelism implementation approach is DeepSpeed Ulysses. It initially partitions individual samples along the sequence dimension across participating GPUs. Before the attention computation, it employs an all-to-all communication collective on the partitioned Q, K, and V.

This ensures that each GPU receives the full sequence length, but only for a non-overlapping subset of the attention heads, enabling them to compute attention in parallel. Finally, a second all-to-all communication gathers the results across the attention heads while repartitioning them along the sequence dimension. Read more about context parallelism for long context in the article 
DeepSpeed Ulysses: System Optimizations for Enabling Training of Extreme Long Sequence Transformer Models
.

 

 
Figure 4. DeepSpeed Ulysses strategy for context parallelism

Benchmarks: Media generation with context parallelism in C++ 

The following benchmarks evaluate multi-device TensorRT inference for media generation workloads intended for C++ production deployment. Two representative generative AI pipelines are used: a video generation pipeline based on NVIDIA Cosmos 3 and an image generation pipeline based on FLUX.1.

These pipelines were first authored in PyTorch, then converted out of the framework using 
Torch-TensorRT
 to produce NVIDIA TensorRT engines suitable for deployment in C++ inference applications. This workflow enables developers to retain PyTorch as the model development environment while deploying optimized TensorRT engines in production systems.

The benchmarks compare end-to-end latency across different context parallelism strategies: AllGather KV, Ring Attention, and Ulysses. All results were collected on a single node with 8 GPUs.

Video generation with NVIDIA Cosmos 3
 

The 
NVIDIA Cosmos
 model platform is a world foundation model platform, and the 
Cosmos3-Nano
 model can generate images, video, audio, and other formats based on multimodal inputs, including text, images, and video. We used the 
example prompt file
 for our benchmarks. Based on these benchmarks, Ulysses is the clear winner when a diffusion model has excessively long context lengths (in the order of tens of thousands of input tokens).

 

 
Figure 5. NVIDIA Cosmos 3 E2E latencies i
n milliseconds
 on N GPUs with different CP strategies

 

 
Figure 6. NVIDIA Cosmos 3 backbone speedup on GPUs with different context parallelism strategies

 

 
Figure 7. Sample outputs of the NVIDIA Cosmos 3 model on 8 GPUs with different CP strategies

Image generation with Flux.1

The 
FLUX.1-dev
 model from Black Forest Labs can generate images from text descriptions. We used the prompt: “a beautiful photograph of Mt. Fuji during cherry blossom” for our benchmarks. Based on the benchmarks, the Ulysses strategy is the winner in the case of image generation as well, but it’s worth noting that Ring Attention also scaled well to 4 GPUs.

 

 
Figure 8. Flux E2E latencies in milliseconds on N GPUs with different CP strategies

 

 
Figure 9. Flux backbone speedup on GPUs with different CP strategies

 

 
Figure 10. Sample outputs of the Black Forest Lab Flux.1 model on 8 GPUs with different CP strategies

Getting started using TensorRT with the multi-device feature

TensorRT supports multi-device inference, enabling a single network to execute across multiple GPUs through integrated distributed communication primitives. The core workflow is similar to that of single-device TensorRT. The difference is that the network can now include distributed communication layers. 

In this guide, it’s assumed that the same network is deployed on all GPU ranks, but this isn’t a strict requirement, and, in theory, each rank can run a different model.

A working sample is provided in the 
TensorRT repository
. The following guide provides a step-by-step description of how to use the new multi-device feature.

Prerequisites

Download TensorRT 11 from the 
NVIDIA Developer Portal
.

Install TensorRT 11 following 
these instructions
.

Get a single-node, multi-GPU machine.

Install 
OpenMPI
 in your chosen development environment (bare metal or in a container)

Create a network for multi-device inference

At the network level, multi-device inference is enabled through 
IDistCollectiveLayer
 for cross-GPU communication. Collective operations can be added directly to a TensorRT network using 
INetworkDefinition::addDistCollective
:

using namespace nvinfer1;
// create empty network
auto network = 
 std::unique_ptr<INetworkDefinition>(builder->createNetworkV2(
 1U << static_cast<uint32_t>(kSTRONGLY_TYPED)));
auto* input =
 network->addInput("input", DataType::kFLOAT, Dims2{3, 4});
ITensor& inputTensor = *network->getInput(0);
auto* collectiveLayer = network->addDistCollective(
 inputTensor,
 CollectiveOperation::kALL_REDUCE,
 ReduceOperation::kSUM,
 -1, // root: -1 for collectives without a root rank
 nullptr, // groups: nullptr means all ranks participate
 0 // groupSize
);

// set the world size aka total number of GPUs
collectiveLayer->setNbRanks(8);

For reduction collectives such as 
ALL_REDUCE
, 
REDUCE
, and 
REDUCE_SCATTER
, specify a valid 
ReduceOperation
, such as 
kSUM
. For non-reduction collectives such as 
ALL_GATHER
, 
BROADCAST
, 
ALL_TO_ALL
, 
GATHER
, and 
SCATTER
, use 
ReduceOperation::kNONE
. Root-based operations, including 
BROADCAST
, 
REDUCE
, 
GATHER
, and 
SCATTER
, require a valid root rank.

Build an engine

// create builder config
auto builderConfig = std::unique_ptr<IBuilderConfig>(builder->createBuilderConfig());
// build engine
auto serializedEngine = std::unique_ptr<IHostMemory>(builder->buildSerializedNetwork
(*network, *builderConfig));

Create execution context

auto runtime = std::unique_ptr<IRuntime>(createInferRuntime(
sample::gLogger.getTRTLogger()));

Bind IO tensors

 char const* inputName = engine->getIOTensorName(0);
 char const* outputName = engine->getIOTensorName(1);

 std::vector<float> const& inputChunk = (rank == 0) ? config.rank0Input : config.rank1Input;
 std::vector<float> outputChunk(config.outputElementCount, 0.0F);

 size_t const inputBytes = inputChunk.size() * sizeof(float);
 size_t const outputBytes = outputChunk.size() * sizeof(float);

 void* dInput = nullptr;
 void* dOutput = nullptr;
 CHECK_CUDA(cudaMalloc(&dInput, inputBytes));
 CHECK_CUDA(cudaMalloc(&dOutput, outputBytes));

 // Copy input data to GPU asynchronously
 CHECK_CUDA(cudaMemcpyAsync(dInput, inputChunk.data(), inputBytes, cudaMemcpyHostToDevice, stream));

 // Set input/output tensor addresses in the execution context
 context->setInputTensorAddress(inputName, dInput);
 context->setTensorAddress(outputName, dOutput);
 context->setInputShape(inputName, Dims2{kINPUT_ROWS, kINPUT_COLS});

Set communicator and enqueue inference

context->setCommunicator(comm);
context->enqueueV3(stream);

Note: the NCCL communicator must also remain valid for the lifetime of the execution context that uses it.

Kick off inference

Run the application with OpenMPI on 8 GPUs. Each rank selects its local CUDA device, initializes NCCL, creates its own TensorRT engine, creates its own execution context, and attaches the NCCL communicator.

mpirun -np 8 bash -lc 'export TRT_MY_RANK=$OMPI_COMM_WORLD_RANK; \
export TRT_WORLD_SIZE=$OMPI_COMM_WORLD_SIZE; \
export TRT_NCCL_ID_FILE=/tmp/nccl_id.txt; \
./sample_dist_collective --op all_reduce'

Learn more

If you want to learn more about the topics introduced in this article, we included some useful links for further reading.

NCCL:
 
NVIDIA Collective Communications Library (NCCL)

Parallelism:

Context Parallelism for Scalable Million-Token Inference

Ring Attention with Blockwise Transformers for Near-Infinite Context

DeepSpeed Ulysses: System Optimizations for Enabling Training of Extreme Long Sequence Transformer Models

NVIDIA TensorRT:

NVIDIA TensorRT Product Page

Download NVIDIA TensorRT

NVIDIA TensorRT GitHub Repository

NVIDIA Torch-TensorRT:
 
Torch-TensorRT Documentation

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Agentic AI / Generative AI
 | 
Developer Tools & Techniques
 | 
Edge Computing
 | 
General
 | 
TensorRT
 | 
Advanced Technical
 | 
Benchmark
 | 
C++
 | 
featured
 | 
Inference Performance
 | 
NCCL
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Peter Kisfaludi
 

 

 
 Peter Kisfaludi is a senior software engineer working in the TensorRT Multi-Device team. In this role, he focuses on developing scalable runtime architectures and optimizing communication overhead to deliver low-latency execution for multi-GPU model serving. Before joining NVIDIA in 2022, Peter was an independent consultant designing low-latency, mission critical software for real-time embedded systems.
 
 
 

 

 View all posts by Peter Kisfaludi

 

 

 

 

 

 

 

 

 

 

 About Zhaoyuan He
 

 

 
 Zhaoyuan He is a senior deep learning software engineer on the NVIDIA TensorRT team, specializing in efficient GPU inference for large language models. His technical interests span the performance optimization techniques that power modern inference frameworks, including kernel development, graph optimization, runtime execution, quantization, and distributed inference with collective communication optimizations. He works on advancing these techniques to deliver higher throughput and lower latency for end-to-end LLM serving on NVIDIA platforms. Zhaoyuan holds a Ph.D. in computer science from The University of Texas at Austin and an M.S. in electrical and computer engineering from the University of California, San Diego.
 
 
 

 

 View all posts by Zhaoyuan He

 

 

 

 

 

 

 

 

 

 

 About Daisy Chu
 

 

 
 Daisy Chu is a senior systems software engineer on the NVIDIA TensorRT team, specializing in multi-device architectures. Her work centers on building production-grade inference systems, with an emphasis on performance optimization, correctness validation, and scalable execution across single- and multi-GPU environments. Daisy is instrumental in enabling efficient multi-GPU inference for large language and multimodal models, ensuring high scalability and robustness. She holds a master’s degree in Computer Science from the University of Illinois Urbana-Champaign.
 
 
 

 

 View all posts by Daisy Chu

 

 

 

 

 

 

 

 

 

 

 About Joseph Loftin
 

 

 
 Joseph Loftin is a deep learning software inference engineer on the NVIDIA TensorRT team. His work focuses on enabling and optimizing multi-device inference through graph parallelism implementations, compiler enhancements, distributed collective development, and specialized kernels. He holds a master’s degree in computer science from Georgia Institute of Technology and a bachelor’s degree in electrical engineering from the University of Louisiana at Lafayette.
 
 
 

 

 View all posts by Joseph Loftin

 

 

 

 

 

 

 

 

 

 

 About Byungsoo Jeon
 

 

 
 Byungsoo Jeon is a senior system software engineer on the NVIDIA TensorRT compiler backend team, specializing in high-performance distributed ML systems for LLMs. His expertise spans ML compiler optimization, multi-GPU parallelism, operator fusion, and custom GPU kernel development across both training and inference. Byungsoo holds a Ph.D. in Computer Science from Carnegie Mellon University, where his dissertation focused on automated and portable machine learning systems.
 
 
 

 

 View all posts by Byungsoo Jeon

 

 

 

 

 

 

 

 

 

 

 
Comments
