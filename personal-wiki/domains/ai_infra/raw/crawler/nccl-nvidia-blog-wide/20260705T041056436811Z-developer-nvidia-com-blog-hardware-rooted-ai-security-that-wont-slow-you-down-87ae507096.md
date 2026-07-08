---
source_id: nccl-nvidia-blog-wide
title: Hardware-Rooted AI Security That Won’t Slow You Down
canonical_url: https://developer.nvidia.com/blog/hardware-rooted-ai-security-that-wont-slow-you-down/
captured_at: '2026-07-05T04:10:56.436811+00:00'
content_hash: 87ae507096856416ab9a2af84c66c3c1e4b304b57b860c3c7a649fba05e481a9
---
# Hardware-Rooted AI Security That Won’t Slow You Down

URL: https://developer.nvidia.com/blog/hardware-rooted-ai-security-that-wont-slow-you-down/

RSS Summary:
<img alt="Decorative image." class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2025/02/cybersecurity-ai-featured-768x432.png" style="display: block; margin-bottom: 5px; clear: both;" title="cybersecurity-ai-featured" width="768" />AI has transformed how organizations operate, driving unprecedented levels of productivity and innovation. However, AI adoption can be impeded by concerns...

Article Body:
Trustworthy AI / Cybersecurity

 

 
 

 

 
 

 

 
Hardware-Rooted AI Security That Won’t Slow You Down

 

 NVIDIA Confidential Computing delivers security at 98% of performance of solutions that don’t enable CC 

 

 
 

 

 

 Jul 02, 2026
 

 

 By 
Sheel Pethe
, 
Vidhya Krishnan
, 
Aruna Manjunatha
, 
Matheen Raza
 and 
Jamie Li
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
NVIDIA Confidential Computing (CC) integrates hardware-level security across Blackwell GPUs, utilizing features such as fused private signing keys, NVLink encryption, and remote attestation via the NVIDIA Remote Attestation Service (NRAS) to ensure data, code, and model integrity during inference.
Benchmarking on the HGX B300 with the Qwen 3.5-397B-A17B-FP8 model demonstrated that enabling CC incurs minimal throughput and per-token latency overhead (typically under 8%) across varying concurrency, batch sizes, and token lengths, maintaining near-native inference performance.
Performance optimizationsincluding CC-safe autotuning in FlashInfer, async D2H copy worker, and piecewise CUDA graph support in SGLangmitigate the impact of secure work submission and encrypted bandwidth limitations, enabling secure, high-performance AI inference suitable for production-scale deployments with regulatory compliance.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

AI has transformed how organizations operate, driving unprecedented levels of productivity and innovation. However, AI adoption can be impeded by concerns surrounding data privacy, sovereignty and how to secure data while it is in use, or during inference and engagement with AI models. NVIDIA Confidential Computing (CC) was engineered to be a secure and performant solution for the era of agentic AI to scale any model securely. 

CC enables the protection of enterprise data and proprietary model weights and the model itself during active inference. In this post, we will provide an overview of CC and demonstrate benchmarks that show its inference performance is nearly identical (up to 98%) to solutions that don’t enable CC security. 

Data, code, and model integrity

CC provides a security layer that spans silicon, interconnect, and system software. Here’s how it works:

 

 
Figure 1. Confidential Computing provides data and code integrity and confidentiality

Hardware root of trust

NVIDIA Blackwell GPUs, including the NVIDIA RTX PRO 6000, HGX B200, and HGX B300, are engineered with CC embedded in the hardware. The HGX B200 and HGX B300 GPUs support confidential computing across multiple GPUs (up to 8) with NVIDIA NVLink encryption. At the silicon level, the GPU maintains a private signing key that is fused at the time of manufacturing and never exposed to software, firmware, or the host system. This key is the foundation of the attestation chain.

Attestation: Verification before execution

Before a confidential workload receives any secrets, it undergoes remote attestation. The NVIDIA Remote Attestation Service (NRAS) verifies a signed evidence bundle—the GPU’s hardware report combined with CPU TEE measurements (AMD SEV-SNP or Intel TDX)—against a known-good reference integrity manifest (RIM).

Once the Confidential VM (CVM) is in a verified, unmodified state, secrets such as  model decryption keys can be deployed into the CVM. The attestation handshake is typically a one-time startup event. Once the workload is running, attestation does not add latency to individual inference requests.

 

 

Figure 2. Attestation services remotely validate the identity, configuration, and integrity of Trusted Execution Environments and issue cryptographic proof

Optimizing AI inference performance in Confidential Computing

CC changes to AI inference performance on Blackwell GPUs can come from two areas: 

Secure work submission latency: 
 For inference, secure work submission latency is often the larger factor and due to the added overhead from encryption and kernel launches, smaller units of work are more affected. Increasing the amount of work performed per GPU work launch reduces the impact of the secure launch overhead. 

Reduced host-to-device CPU-to-GPU bandwidth:
 If a workload depends heavily on transferring inputs to the GPU, performance will depend on whether the required bandwidth to keep the GPU fully utilized exceeds the encrypted transfer bandwidth available in CC mode.

Several innovations optimize inference performance with CC including:

CC-safe autotuner timing:
 FlashInfer replaces event timers in CC mode with the GPU global timer register, allowing autotuners to accurately compare kernel candidates and select the fastest implementation for each shape.

Async D2H copy worker:
 SGLang moves per-step token readback off the scheduler’s critical path. This helps restore compute/copy overlap because CC can otherwise make many host-to-device and device-to-host copies effectively synchronous during cudaMemcpyAsync.

Piecewise CUDA graph support:
 SGLang adds CUDA graph replay for prefill and mixed batches, reducing kernel launch overhead that is amplified in CC mode.

NVIDIA continues to work with upstream communities for inference frameworks to ensure these frameworks are optimized for performance. 

We measured the inference performance of CC across different key metrics. Below are the details on the test setup and measurements. 

Benchmark results

Across all workload configurations tested, enabling CC mode produced minimal throughput and time per output token overhead during steady-state inference.

The following table summarizes CC throughput, TTFT, TPOT overhead on Blackwell Ultra (HGX B300) for model Qwen/Qwen3.5-397B-A17B-FP8

Relative Performance of Confidential Computing

Concurrency
ISL/OSL = 1024 / 1024
ISL/OSL = 8192 / 1024
Throughput/GPU (tok/s)
Median TPOT (ms)
Throughput/GPU (tok/s)
Median TPOT (ms)
Δ% vs OFF
Δ% vs OFF
Δ% vs OFF
Δ% vs OFF
4
-2.0%
-1.6%
-3.5%
-3.6%
8
-2.6%
-2.4%
-2.8%
-2.9%
16
-5.3%
-4.9%
-2.8%
-3.0%
32
-6.3%
-7.8%
-1.0%
-0.9%
64
-6.2%
-6.8%
-2.3%
-2.4%
128
-7.5%
-8.1%
-3.5%
-3.5%
256
-4.6%
-4.1%
-3.6%
-3.7%
Table 1. Relative performance impact of enabling NVIDIA Confidential Computing 

Test Setup

Benchmark:
 Qwen 3.5 397B-A17B model at FP8 precision
Environment:
 Virtual Machine with GPU passthrough
Baseline:
 Confidential Computing Off
Experiment:
 Confidential Computing On

All other variables held constant. 

Hardware Configurations

HGX B300 with Blackwell Ultra. 

Software Stack

Component
Version / Detail
Platform
Intel TDX
Host OS
Ubuntu 25.10
Host Kernel
6.17.0-20-generic
Guest OS
Ubuntu 24.04.4 LTS
Guest Kernel
6.8.0-124-generic
Guest vCPUs
256
Guest NUMA
2 nodes
NVIDIA Driver
595.71.05
VBIOS
FW 1.4.x [97.10.64.00.0C]
GPU Power Limit
1100.00
CUDA
13.2
SGlang
docker.io/lmsysorg/sglang:v0.5.12-cu130
PRs: 
28251
 (SGLang) and 
3638
 (FlashInfer)
NCCL
v2.28.9-1
OpenSSL
3.6.0
Orchestration
Docker Container + NVIDIA Container Toolkit
Table 2. Software configuration for test setup

Note: Please follow the CPU power and vCPU pinning configuration described in this 
document.
 

Workload Parameters

Each configuration was tested across a range of conditions representative of real enterprise inference workloads:

Input/output token lengths: 
8192/1024, 1024/1024
Batch sizes:
 4, 8, 16, 32, 64, 128 and 256 concurrent requests. 
Inference framework (Mode):
 SGLang (Server)
Baseline:
 Without –enable-symm-mem

Metrics Collected

Output Throughput per GPU (tokens/sec/gpu)
Median Time to First Token (TTFT)
 — latency from request submission to first token generated, in ms
Median Time Per Output Token (TPOT)
 — per-token generation latency in steady-state streaming, in ms

Path forward

Hardware-level security with CC protects sensitive AI workloads while preserving the performance needed for production AI workloads. 

CC provides a stronger security foundation for production inference workloads with minimal performance overheads. In our evaluation using Qwen 3.5 on SGLang, we observed  this across a sweep of concurrency levels, input sequence lengths, and output sequence lengths, proving that organizations can secure their AI workloads and data, and stay compliant to regulation without compromising on performance. 

Join NVIDIA and our partners to secure your AI workloads with CC on Blackwell by accessing the resources below.

Resources

NVIDIA Confidential Computing Documentation
NVIDIA Blackwell Architecture Whitepaper
NVIDIA GPU Operator and Container Toolkit
NVIDIA Remote Attestation Service (NRAS)
NIST SP 800-207 Zero Trust Architecture
HIPAA Security Rule (HHS)
GDPR Article 32 — Security of Processing

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Agentic AI / Generative AI
 | 
Data Center / Cloud
 | 
Trustworthy AI / Cybersecurity
 | 
General
 | 
Blackwell
 | 
Dynamo
 | 
NVLink
 | 
TensorRT
 | 
Intermediate Technical
 | 
Best practice
 | 
Deep dive
 | 
AI Agent
 | 
AI Inference
 | 
Cloud Services
 | 
Code / Software Generation
 | 
Inference Performance
 | 
Security for AI
 | 
Software-Defined Data Center
 | 
TensorRT-LLM
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Sheel Pethe
 

 

 
 Sheel Pethe is a senior system software engineer on the NVIDIA GPU kernel core OS team. Drawing on a background in virtualization and memory management, he develops the low-level systems that underpin secure, high-performance confidential computing. He holds a master's degree in computer science from Columbia University.
 
 
 

 

 View all posts by Sheel Pethe

 

 

 

 

 

 

 

 

 

 

 About Vidhya Krishnan
 

 

 
 Vidhya Krishnan is a distinguished architect and a lead hardware architect for NVIDIA GPU confidential compute. She has worked on GPUs for the majority of her career. She is passionate about confidential computing as a technology and looks forward to it becoming the default mode of deployment.
 
 
 

 

 View all posts by Vidhya Krishnan

 

 

 

 

 

 

 

 

 

 

 About Aruna Manjunatha
 

 

 
 Aruna Manjunatha is a director of system software at NVIDIA, leading teams that build foundational software for advanced GPU platforms and accelerated computing. She has nearly two decades of experience in system software, hardware–software co‑design, large‑scale platform enablement, and is a key contributor to NVIDIA’s first confidential GPUs. She holds an M.S. in electrical and computer engineering from Carnegie Mellon University.
 
 
 

 

 View all posts by Aruna Manjunatha

 

 

 

 

 

 

 

 

 

 

 About Matheen Raza
 

 

 
 Matheen is a principal product marketing manager in the NVIDIA Enterprise Products team, focused on the NVIDIA software portfolio for accelerated computing workloads. Matheen is a product and GTM professional with experience across multiple companies, including Amazon Web Services, Hewlett Packard Enterprise, Qubole, Infosys, and Intel. He holds B.Sc. and M.Sc. degrees in electrical engineering (from the University of Madras and Colorado State University), as well an MBA from University of California, Berkeley.
 
 
 

 

 View all posts by Matheen Raza

 

 

 

 

 

 

 

 

 

 

 About Jamie Li
 

 

 
 Jamie Li is a senior technical marketing engineer at NVIDIA focused on wrangling the latest technologies in AI inference. He brings a deep background in both AI software engineering and customer management, translating innovations into practical customer outcomes. Before NVIDIA, he held roles developing, breaking, and fixing AI solutions in the enterprise tech sector. He also did research in medical imaging and holds a master’s degree in Computer Science with an AI focus.
 
 
 

 

 View all posts by Jamie Li

 

 

 

 

 

 

 

 

 

 

 
Comments
