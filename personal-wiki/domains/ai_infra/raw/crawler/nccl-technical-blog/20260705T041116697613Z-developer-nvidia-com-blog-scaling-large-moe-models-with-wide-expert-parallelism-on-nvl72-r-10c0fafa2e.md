---
source_id: nccl-technical-blog
title: Scaling Large MoE Models with Wide Expert Parallelism on NVL72 Rack Scale Systems
canonical_url: https://developer.nvidia.com/blog/scaling-large-moe-models-with-wide-expert-parallelism-on-nvl72-rack-scale-systems/
captured_at: '2026-07-05T04:11:16.697613+00:00'
content_hash: 10c0fafa2e04e441e423da9298c0a99926ecc050d5c62e2aa8cb29562c3f023c
---
# Scaling Large MoE Models with Wide Expert Parallelism on NVL72 Rack Scale Systems

URL: https://developer.nvidia.com/blog/scaling-large-moe-models-with-wide-expert-parallelism-on-nvl72-rack-scale-systems/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2025/10/image4-2-768x432-jpg.webp" style="display: block; margin-bottom: 5px; clear: both;" title="image4" width="768" />Modern AI workloads have moved well beyond single-GPU inference serving. Model parallelism, which efficiently splits computation across many GPUs, is now the...

Article Body:
Data Center / Cloud

 

 
 

 

 
English
中文

 

 

 
Scaling Large MoE Models with Wide Expert Parallelism on NVL72 Rack Scale Systems

 
 

 

 

 Oct 20, 2025
 

 

 By 
Eduardo Alvarez
, 
Chen Xiaoming
, 
Jun Yang
, 
Kaiyu Xie
 and 
Dongxu Yang
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
Expert parallelism (EP) is a model-parallel technique that distributes a mixture-of-experts (MoE) model's experts across multiple GPUs to take advantage of combined compute and memory bandwidth, with large-scale EP referring to distributing experts across eight or more GPUs.
NVIDIA TensorRT-LLM's Wide Expert Parallelism (Wide-EP) addresses the challenges of large-scale EP by reducing weight-loading pressure, improving GroupGEMM efficiency, and leveraging the 130 TB/s coherent NVLink domain of GB200 NVL72 to offset communication overhead.
Wide-EP on GB200 NVL72 achieves up to 1.8x higher per-GPU throughput compared to smaller EP configurations, improving tokens/second/GPU and lowering the overall cost of serving large models like DeepSeek-R1.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

Modern AI workloads have moved well beyond single-GPU inference serving. Model parallelism, which efficiently splits computation across many GPUs, is now the foundation of scalable, state-of-the-art deployments. The highest-performing models increasingly adopt 
mixture-of-experts
 (MoE) architectures, which are more efficient than dense models because they activate only a subset of trained parameters per token. However, scaling MoEs introduces more complex parallelism, communication, and scheduling requirements that must be carefully optimized.

Expert parallelism (EP), the strategic distribution of experts across multiple GPUs, is essential to overcoming these challenges and unlocking scalable performance. As models like DeepSeek-R1, with 256 experts and 671 billion parameters, continue to grow, new tools are needed—such as NVIDIA Tensor RT-LLM’s Wide Expert Parallelism, or Wide-EP. It makes large-scale deployment more efficient, improving both performance and total cost of ownership. 

In this blog, we break down how large-scale EP impacts performance and reshapes inference economics in the NVL72 rack-scale domain.

How to achieve large-scale expert parallelism

Expert parallelism (EP) is a model-parallel technique that distributes a MoE model’s experts across multiple GPUs to take advantage of combined compute and memory bandwidth. At smaller scales, EP helps reduce memory pressure and keep utilization high by balancing work across devices. 

 

 
Figure 1. Animation showing how small-scale EP deploys many experts per GPU, while large-scale EP spreads fewer experts per GPU across a much larger cluster, enabling efficient scaling of MoE layers.

As models like DeepSeek-R1 grow to hundreds of billions of parameters with hundreds of experts, these same techniques must expand in scope, leading to what we call large-scale EP. For the purposes of this blog, large-scale EP refers to the process of distributing experts across eight or more GPUs. This increases aggregated bandwidth for faster weight loading and supports larger effective batch sizes to improve overall GPU utilization.

What are memory and compute challenges of large-scale EP?

MoE models provide the added benefit of only activating a small subset of experts during inference—significantly reducing the per token compute requirement. To achieve this, MoEs dynamically load the weights of an activated expert on a per token per layer basis. In high throughput, latency-constrained scenarios, weight-loading overhead can quickly become a major bottleneck for a specific type of compute process called MoE GroupGEMMs. 

MoE GroupGEMMs are like sending all tokens to the same checkout lane at the same time, so they can be processed in one efficient batch. In practice, they are grouped matrix multiplications that batch tokens per expert into a single large calculation. That boosts arithmetic intensity, but it requires loading each expert’s weights into on-chip memory/registers before multiplication.

 

 
Figure 2. Tokens routed to the same expert are packed together and processed with a single fused GroupGEMM kernel for efficient MoE inference.

Large-scale EP addresses some of the MoE GroupGEMM bottlenecks by introducing more GPUs into the expert parallel configuration, efficiently reducing the number of experts held by each GPU. This results in:

Less weight-loading pressure (smaller set of expert weights per GPU)

Easier reuse of weights by the GroupGEMM kernel (higher arithmetic intensity—more FLOPs per byte of weight loaded)

Better compute/memory balance inside the kernel

While large-scale EP helps address the limitations of small-scale EP, it also introduces new system-level constraints that make scaling large MoEs difficult. TensorRT-LLM Wide-EP helps address these constraints by targeting compute and memory bottlenecks algorithmically while also tackling workload management at the system and architecture level. 

Let’s examine how wide-EP, when paired with GB200 NVL72, provides the foundation for scalable and efficient MoE inference.

What’s the system design and architecture?

Scaling expert parallelism requires more than adding GPUs. It depends on system design and architecture that keep memory movement and communication efficient. Interconnect bandwidth and topology provide the foundation, allowing activations and weights to flow smoothly across devices. 

On top of this, optimized software and kernels manage expert-to-expert traffic with communication primitives, bandwidth-aware scheduling, and load balancing. Together, these capabilities make large-scale EP practical and efficient.

Alleviating distributed expert communication overhead with NVLink

One of the biggest bottlenecks in large-scale EP is communication overhead. During the decode phase of inference, distributed experts must exchange information to consolidate the outputs of multiple GPUs across the system. For instance, when distributing DeepSeek-R1’s 256 experts across 64 GPUs with eight active experts per token (See Figure 3 below), the communication cost depends on which experts are activated at a given layer and where their weights are located.

 

 
Figure 3. Schematic diagram showing an MoE deployment with 232 experts per GPU and only four activated per layer, coordinated across 72 GPUs in a GB200 NVL72 NVLink domain.

While large-scale EP reduces weight-loading overhead for activated experts, these gains can be offset by token-gather collectives that must consolidate distributed outputs and reorder tokens before passing them to the next transformer block or the final softmax layer. Without the 130 TB/s of aggregate bandwidth provided by the NVL72, the complexity and overhead of this communication pattern would make large-scale EP impractical.

Optimizing kernels for optimal expert routing with NCCL

MoEs leverage a routing mechanism to dynamically select the most appropriate experts per token. This means that every transformer block requires per token dispatching and aggregation after they pass through expert layers. The all-to-all operations involved can quickly saturate an already memory-bound decode phase. 

To address these challenges, custom EP communication kernels are required. For GB200 NVL72, we have implemented custom kernels to address CUDA graph compatibility with multiple rack-scale deployment scenarios. Of note are custom high-performance NCCL kernels designed to handle non-static data sizes across large-scale EP deployments. These custom EP kernels are able to accept communication sizes directly from GPU memory and take advantage of the NVL72 aggregate memory. 

Load balancing wide experts

Load balancing is a classic distributed systems technique that assigns work based on resource availability to maximize utilization without overloading any single part of the system. In the case of large-scale EP workloads, load balancing is used to distribute experts among the available GPUs. For example, in a GB200 NVL72 rack running Wide-EP DeepSeek-R1 with EP=64 (for clean division), we would distribute four experts per GPU per layer, for a total of 232 experts assigned per GPU.

To prevent load-balancing scenarios where a collection of very popular “hot experts” all sit on the same GPU while other GPUs with less popular “cold experts” sit idle, Wide-EP’s Expert Parallel Load Balancer (EPLB) leverages a policy to redistribute hot experts alongside cold experts. This triggers a weight update process, addressed by using a containerized design that allows experts to flow in and out of container allocations without breaking the CUDA graph. These weight updates are performed in a non-blocking fashion by scheduling them between forward passes.

 

 
Figure 4. Diagram showing Expert Parallel Load Balancer (EPLB) redistributes experts to ensure balanced GPU workload, preventing over- and under-utilization.

The EPLB can operate in two different modes: 

Static EPLB:
 pre-computed expert-to-GPU mappings based on historical data patterns are used to optimize expert allocation.

Online EPLB:
 Experts are redistributed during runtime dynamically to adapt real-time to changing workload patterns. 

While static EPLB offers good baseline improvements over a non-EPLB approach, online EPLB provides the highest potential for optimal load balancing in real-time production systems. In our initial implementation of online EPLB, we encountered and patched several 
critical challenges
 associated with real-time weight-updating processes.

Wide-EP with TensorRT-LLM and NVIDIA Dynamo

When deploying MoE models like DeepSeek R1 or Llama 4 at scale, inference performance hinges on two key pillars: disaggregated serving and Wide-EP. NVIDIA Dynamo and TensorRT-LLM form the software backbone that enables both, transforming traditional bottlenecks into opportunities for massive throughput gains and efficient GPU utilization. The table below outlines the differences and synergies between Dynamo and Wide-EP.

Component
NVIDIA Dynamo
TensorRT-LLM Wide-EP
Role
Orchestration layer for disaggregated inference
Execution engine for expert-parallel decoding
Optimization Scope
Orchestrates prefill & decode phases across GPU pools
Distributes small number of experts per GPU to optimize per token memory and compute utilization
SLA Awareness
SLA-aware autoscaling and dynamic rate matching (TTFT & ITL) 
Maximizes batching & minimizes latency through efficient expert scheduling
Traffic Adaption
Reacts in real-time to ISL/OSL fluctuations via the Dynamo Planner
Load balances expert allocations to optimize compute utilization
Hardware Synergy
Scales via Kubernetes + Planner logic across disaggregated GPU domains
Leverages high-bandwidth domains (e.g. NVL72) for efficient expert communication
Table 1. Comparison of NVIDIA Dynamo and TensorRT-LLM Wide-EP for expert-parallel inference, highlighting roles, optimization scope, SLA awareness, traffic adaption, and hardware synergy.

For more insights into the relationships between NVIDIA Dynamo and TensorRT-LLM Wide-EP, we encourage you to review our blog on leveraging 
NVIDIA Dynamo
 for large-scale expert parallelism. 

What are the performance and workload economics?

When you have access to the coherent memory domain created by NVLink scale-up in an GB200 NVL72 rack, optimizing large-scale EP comes down to a few critical factors:

Model size and number of experts:
 Smaller models with fewer experts gain less from Wide-EP because communication overhead can outweigh the benefits of reduced weight loading and distributed compute.

System latency and concurrency goals:
 Large-scale EP is most effective when throughput is constrained by latency, allowing for greater per GPU throughput at iso-latency. 

Hardware capabilities:
 Aggregate memory bandwidth, inter-GPU bandwidth, and achievable compute determine whether the system can reach the optimal degree of parallelism.

In practice, models like DeepSeek-R1 are strong candidates for large-scale EP, where TensorRT-LLM’s Wide-EP on GB200 NVL72 rack-scale systems delivers the best balance of efficiency and throughput. The Pareto frontiers below highlight performance across different EP configurations.

 

 
Figure 5. Large-scale Expert Parallelism (EP) rank 32 delivers up to 1.8x higher output token throughput per GPU compared to small EP rank 8 at 100 tokens/sec per user. Both configurations leverage disaggregated serving and multi-token prediction (MTP).

Compared to the small EP configuration (EP8), the large EP configuration (EP32) achieves up to 1.8x more per-GPU throughput. This highlights the performance uplift opportunity from leveraging large-scale EP and Wide-EP. An additional opportunity exists to leverage speculative decoding with multi-token prediction (MTP) to boost per-user token throughput—this functionality is already compatible with Wide-EP.

Summary

Wide-EP on GB200 NVL72 provides a practical path to scaling large MoE models. Distributing experts across more GPUs reduces weight-loading pressure, improves GroupGEMM efficiency, and leverages GB200 NVL72’s 130 TB/s coherent NVLink domain to offset communication overhead. In testing, large EP configurations reached up to 1.8x higher per-GPU throughput than smaller EP setups. These gains shift the balance of throughput, latency, and utilization in favor of more efficient large-scale inference.

The broader impact is on system economics. By enabling higher concurrency and stronger GPU efficiency, Wide-EP on NVL72 improves tokens/second/GPU and lowers the overall cost of serving large models. For developers, this means exploring Wide-EP in TensorRT-LLM to find optimal configurations. For researchers, it creates room to refine scheduling, load balancing, and decoding strategies. For infrastructure teams, it highlights how GB200 NVL72 can change the TCO profile of trillion-parameter deployments.

For more, check out how large-scale EP with GB200 NVL72 led to the lowest TCO of all other system architectures in the latest 
InferenceMAX benchmarks
.

And for up-to-date performance insights check out the 
NVIDIA Inference Performance dashboard
.

Learn how NVIDIA Blackwell NVL72 runs 10x faster and delivers 1/10 the token cost for MoE models in this
 blog
.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Agentic AI / Generative AI
 | 
Data Center / Cloud
 | 
Networking / Communications
 | 
General
 | 
Blackwell
 | 
Dynamo
 | 
GB200
 | 
H100
 | 
H200
 | 
NCCL
 | 
NVLink
 | 
TensorRT-LLM
 | 
Intermediate Technical
 | 
Deep dive
 | 
featured
 | 
Inference Performance
 | 
LLMs
 | 
TensorRT
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Eduardo Alvarez
 

 

 
 Eduardo Alvarez is a senior technical lead at NVIDIA, where he focuses on AI inference at scale, performance optimization, workload economic analysis, and application enablement. He has a deep background in AI systems engineering, workload optimization, and accelerated computing—focused on translating innovations into real-world applications. Before NVIDIA, Eduardo held engineering roles at various semiconductor and energy tech companies.
 
 
 

 

 View all posts by Eduardo Alvarez

 

 

 

 

 

 

 

 

 

 

 About Chen Xiaoming
 

 

 
 Chen Xiaoming is a principal architect and senior manager at NVIDIA, interested in algorithm/software/hardware co-design for deep learning models. He has recently been working on performance modeling, benchmarking, analysis, and optimization for large language model inference.
 
 
 

 

 View all posts by Chen Xiaoming

 

 

 

 

 

 

 

 

 

 

 About Jun Yang
 

 

 
 Jun Yang is a senior engineering director at NVIDIA, where he focuses on E2E AI workload optimization. Currently, he is leading the overall engineering efforts of NVIDIA TensorRT-LLM. He holds a master’s degree in Computer Architecture from the Institute of Computing Technology Chinese Academy of Sciences.
 
 
 

 

 View all posts by Jun Yang

 

 

 

 

 

 

 

 

 

 

 About Kaiyu Xie
 

 

 
 Kaiyu Xie is a senior architect at NVIDIA who has been working on TensorRT-LLM, focusing on general performance optimization and system implementation.
 
 
 

 

 View all posts by Kaiyu Xie

 

 

 

 

 

 

 

 

 

 

 About Dongxu Yang
 

 

 
 Dongxu Yang is a principal architect at NVIDIA, working on parallel computing and performance optimization. He has recently focused on development and optimization for large language model inference. He eceived his B.S. and M.S. degrees from Tsinghua University, China in 2008 and 2011, respectively.
 
 
 

 

 View all posts by Dongxu Yang

 

 

 

 

 

 

 

 

 

 

 
Comments
