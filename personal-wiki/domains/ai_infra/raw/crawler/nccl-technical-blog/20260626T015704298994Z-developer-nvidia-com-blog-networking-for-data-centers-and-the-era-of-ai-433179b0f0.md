---
source_id: nccl-technical-blog
title: Networking for Data Centers and the Era of AI
canonical_url: https://developer.nvidia.com/blog/networking-for-data-centers-and-the-era-of-ai/
captured_at: '2026-06-26T01:57:04.298994+00:00'
content_hash: 433179b0f04bc9b80963b90687150b3ae55cda291e0253b0055df018e2d9b4fc
---
# Networking for Data Centers and the Era of AI

URL: https://developer.nvidia.com/blog/networking-for-data-centers-and-the-era-of-ai/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2023/10/networking-data-center-ai-768x432.png" style="display: block; margin-bottom: 5px; clear: both;" title="networking-data-center-ai" width="768" />Traditional cloud data centers have served as the bedrock of computing infrastructure for over a decade, catering to a diverse range of users and applications....

Article Body:
Networking / Communications

 

 
 

 

 
English
中文

 

 

 
Networking for Data Centers and the Era of AI

 
 

 

 

 Oct 12, 2023
 

 

 By 
Brian Sparks
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
The emergence of AI factories and AI clouds is driving the need for specialized data centers that can handle the unique demands of AI workloads, which rely heavily on accelerated computing and distributed computing across multiple interconnected servers or nodes.
NVIDIA Quantum-2 InfiniBand is a key networking platform for AI factories, offering ultra-low latencies, in-network computing, and adaptive routing to optimize AI performance and efficiency.
NVIDIA Spectrum-X is a networking platform designed for AI clouds, built on the standard Ethernet protocol with RDMA over Converged Ethernet (RoCE) Extensions, to deliver high effective bandwidth and performance isolation needed for multi-tenant generative AI clouds.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

Traditional cloud data centers have served as the bedrock of computing infrastructure for over a decade, catering to a diverse range of users and applications. However, data centers have evolved in recent years to keep up with advancements in technology and the surging demand for AI-driven computing. This post explores the pivotal role that networking plays in shaping the future of data centers and facilitating the era of AI.

Specialized data centers: AI factories and AI clouds

Two distinct classes of data centers are currently emerging: AI factories and AI clouds. Both of these are tailored to meet the unique demands of AI workloads, which are characterized by their reliance on accelerated computing.

AI factories are designed to handle massive, large-scale workflows and the development of 
large language models
 (LLMs) and other foundational AI models. These models are the building blocks with which more advanced AI systems are constructed. To enable seamless scaling and efficient utilization of resources across thousands of GPUs, a robust and high-performance network is imperative.

AI clouds extend the capabilities of traditional cloud infrastructure to support large-scale 
generative AI
 applications. Generative AI goes beyond conventional AI systems by creating new content, such as images, text, and audio, based on the data it’s been trained on. Managing AI clouds with thousands of users requires advanced management tools and a networking infrastructure that can handle diverse workloads efficiently.

AI and distributed computing

AI workloads are computationally intensive, particularly those involving large and complex models like ChatGPT and BERT. To expedite model training and processing vast datasets, AI practitioners have turned to distributed computing. This approach involves distributing the workload across multiple interconnected servers or nodes connected through a high-speed, low-latency network.

Distributed computing is pivotal for the success of AI, and the network’s scalability and capacity to handle a growing number of nodes is crucial. A highly scalable network enables AI researchers to tap into more computational resources, leading to faster and improved performance.

When crafting the network architecture for AI data centers, it’s essential to create an integrated solution with distributed computing as a top priority. Data center architects must carefully consider network design and tailor solutions to the unique demands of the AI workloads they plan to deploy.

NVIDIA Quantum-2 InfiniBand
 and
 NVIDIA Spectrum-X
 are two networking platforms specifically designed and optimized to meet the networking challenges of the AI data center, each with its own unique features and innovations.
 

InfiniBand drives AI performance 

InfiniBand technology has been a driving force behind large-scale supercomputing deployments for complex distributed scientific computing. It has become the de facto network for AI factories. With ultra-low latencies, InfiniBand has become a linchpin for accelerating today’s mainstream high-performance computing (HPC) and AI applications. Many crucial network capabilities required for efficient AI systems are native to the NVIDIA Quantum-2 InfiniBand platform.

In-network computing, driven by InfiniBand, integrates hardware-based computing engines into the network. This offloads complex operations at scale and utilizes the NVIDIA Scalable Hierarchical Aggregation and Reduction Protocol (SHARP), an in-network aggregation mechanism. SHARP supports multiple concurrent collective operations, doubling data bandwidth for data reductions and performance enhancements.

The InfiniBand adaptive routing optimally spreads traffic, mitigating congestion and enhancing resource utilization. Directed by a Subnet Manager, InfiniBand selects congestion-free routes based on network conditions, maximizing efficiency without compromising order of packet arrival.

The InfiniBand Congestion Control Architecture guarantees deterministic bandwidth and latency. It uses a three-stage process to manage congestion, preventing performance bottlenecks in AI workloads.

These inherent optimizations empower InfiniBand to meet the demands of AI applications, ultimately driving superior performance and efficiency.

Navigating Ethernet for AI deployments

Deploying Ethernet networks for an AI infrastructure requires addressing needs specific to the Ethernet protocol. Over time, Ethernet has incorporated an expansive, comprehensive, and (at times) complex feature set that caters to a huge range of network scenarios. 

As such, out-of-the-box or traditional Ethernet isn’t explicitly designed for high performance. AI clouds that use traditional Ethernet for their compute fabric can only achieve a fraction of the performance that they would achieve with an optimized network.

In multi-tenant environments where multiple AI jobs run simultaneously, performance isolation is critical to prevent further degradation of performance. If there is a link fault, the traditional Ethernet fabric can cause the cluster’s AI performance to drop by half. This is because traditional Ethernet has primarily been optimized for everyday enterprise workflows and isn’t designed to meet the demands of high-performance AI applications that rely on the 
NVIDIA Collective Communications Library (NCCL)
.

These performance issues are due to factors inherent to traditional Ethernet, including:

Higher switch latencies, common across commodity ASICs

Split buffer switch architecture, which can lead to bandwidth unfairness

Load balancing that is suboptimized for the large flows generated by AI workloads

Performance isolation and noisy neighbor issues

The Spectrum-X networking platform solves these issues and more. Spectrum-X builds on the standard Ethernet protocol with RDMA over Converged Ethernet (RoCE) Extensions, enhancing performance for AI. These extensions leverage the best practices native to InfiniBand and bring innovations such as adaptive routing and congestion control to Ethernet. 

Spectrum-X is the only Ethernet platform that delivers the high effective bandwidth and performance isolation needed for multi-tenant generative AI clouds, enabled due to Spectrum-4 working in close coordination with 
NVIDIA BlueField-3 DPUs
. 

Summary

The era of AI is here, and the network is the cornerstone of its success. To fully embrace the potential of AI, data center architects must carefully consider network design and tailor these designs to the unique demands of AI workloads. Addressing ‌networking considerations is key to unlocking the full potential of AI technologies and driving innovation in the data center industry.

NVIDIA Quantum InfiniBand
 is an ideal choice for AI factories, thanks to its ultra-low latencies, scalable performance, and advanced feature sets. 
NVIDIA Spectrum-X
, with its purpose-built technology innovations for AI, offers a groundbreaking solution for organizations building Ethernet-based AI clouds.

To learn more about AI performance demands and network requirements, see the 
Networking for the Era of AI
 whitepaper. Join the conversation in the 
NVIDIA Developer Infrastructure and Networking Forum
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
Hardware / Semiconductor
 | 
BlueField DPU
 | 
InfiniBand
 | 
General Interest
 | 
Beginner Technical
 | 
Best practice
 | 
Ethernet
 | 
featured
 | 
LLMs
 | 
NCCL
 | 
Spectrum Ethernet
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Brian Sparks
 

 

 
 Brian Sparks is a senior director of marketing for the NVIDIA InfiniBand and Ethernet networking platforms. With over 20 years of experience in the data center networking and security market, his responsibilities have included various marketing and communication leadership roles, and strategic HPC and networking ecosystem enablement. He currently holds Marketing Working Group Chair positions in the InfiniBand Trade Association (IBTA) and the Unified Communication Framework (UCF) Consortium. Brian holds a bachelor’s degree in Communications from San Jose State University.
 
 
 

 

 View all posts by Brian Sparks

 

 

 

 

 

 

 

 

 

 

 
Comments
