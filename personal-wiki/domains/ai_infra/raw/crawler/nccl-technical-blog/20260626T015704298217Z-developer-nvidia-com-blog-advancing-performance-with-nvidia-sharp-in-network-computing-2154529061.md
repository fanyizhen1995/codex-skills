---
source_id: nccl-technical-blog
title: Advancing Performance with NVIDIA SHARP In-Network Computing
canonical_url: https://developer.nvidia.com/blog/advancing-performance-with-nvidia-sharp-in-network-computing/
captured_at: '2026-06-26T01:57:04.298217+00:00'
content_hash: 2154529061db86695cea78ccd122908f26a319fbbe3fdb3ec80cc13993613131
---
# Advancing Performance with NVIDIA SHARP In-Network Computing

URL: https://developer.nvidia.com/blog/advancing-performance-with-nvidia-sharp-in-network-computing/

RSS Summary:
<img alt="Picture of servers in a data center." class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2024/10/nvidia-sharp-featured-768x432.png" style="display: block; margin-bottom: 5px; clear: both;" title="nvidia-sharp-featured" width="768" />AI and scientific computing applications are great examples of distributed computing problems. The problems are too large and the computations too intensive to...

Article Body:
Networking / Communications

 

 
 

 

 
English
中文

 

 

 
Advancing Performance with NVIDIA SHARP In-Network Computing

 
 

 

 

 Oct 25, 2024
 

 

 By 
Scot Schultz
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
The NVIDIA Scalable Hierarchical Aggregation and Reduction Protocol (SHARP) is a technology that accelerates collective communication in distributed computing systems by offloading operations like all-reduce, reduce, and broadcast from servers to network switches.
SHARP has evolved through three generations, with the first generation supporting scientific computing, the second generation adding support for AI workloads, and the third generation enabling multi-tenant in-network computing for AI workloads.
By integrating SHARP with the NVIDIA Collective Communication Library (NCCL), distributed AI training frameworks can significantly improve scalability and performance, with some service providers reporting 10-20% performance improvements for in-house AI workloads.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

AI and scientific computing applications are great examples of distributed computing problems. The problems are too large and the computations too intensive to run on a single machine. These computations are broken down into parallel tasks that are distributed across thousands of compute engines, such as CPUs and GPUs. 

To achieve scalable performance, the system relies on dividing workloads like training data, model parameters, or both, across multiple nodes. These nodes must then frequently exchange information, such as gradients of newly-processed model computations during backpropagation in model training, requiring efficient collective communications like all-reduce, broadcast, and gather and scatter operations. 

These collective communication patterns ensure the synchronization and convergence of model parameters across the distributed system. The efficiency of these operations is crucial for minimizing communication overhead and maximizing parallel computation, as poorly optimized collective communications can lead to bottlenecks, limiting scalability.

The bottlenecks arise from several factors:

Latency and bandwidth limitations:
 Collective operations rely on high-speed data transfers across nodes, which are constrained by the physical network’s latency and bandwidth. As the scale of the system increases, the amount of data to be exchanged grows, and the time taken for communication becomes a dominant factor over computation.

Synchronization overhead:
 Many collective operations require synchronization points where all participating nodes must reach the same state before proceeding. If certain nodes are slower, the entire system experiences delays, causing inefficiencies known as 
stragglers
.

Network contention:
 As the network becomes more congested with larger numbers of nodes trying to communicate simultaneously, contention for bandwidth and network resources increases, further slowing down collective operations.

Non-optimal communication patterns:
 Some collective communication algorithms (e.g., tree-based reductions or ring-based all-reduce) are not always well-optimized for large-scale systems, leading to inefficient use of available resources and increased latency.

Overcoming this bottleneck requires advancements in network technologies (for example, InfiniBand or RDMA) and algorithmic optimizations (for example, hierarchical all-reduce or pipelining techniques) to minimize synchronization delays, reduce contention, and optimize data flow across distributed systems.

Creation of NVIDIA SHARP

The key collective communications enable all compute engines to exchange data between themselves. Managing such communication on a NIC or server requires exchanging massive amounts of data, and is exposed to the variance of latency or collective performance, also known as 
server jitter
. 

Migrating the responsibility to manage and execute these collective communications on the switch fabric reduces the amount of transferred data by half and minimizes jitter. NVIDIA Scalable Hierarchical Aggregation and Reduction Protocol (SHARP) is the technology implementing that concept and introduced the concept of 
in-network computing
. It is incorporated in the switch ASIC and designed to accelerate collective communication in distributed computing systems. 

Introduced with 
NVIDIA InfiniBand networks
, SHARP offloads collective communication operations—like all-reduce, reduce, and broadcast—from the server’s compute engines to the network switches. By performing reductions (summing, averaging, and so on) directly within the network fabric, SHARP improves these operations and the overall application performance. 

Generational advancements with NVIDIA SHARP

The first generation of SHARP was specifically designed for scientific computing applications, with a focus on small-message reduction operations. It was introduced with NVIDIA EDR 100Gb/s switch generation, and was quickly supported by leading Message Passing Interface (MPI) libraries. SHARPv1 small message reduction supported multiple scientific computing applications in parallel. 

MVAPICH2 is an open-source implementation of the MPI standard, specifically designed for high-performance computing (HPC) environments. The Ohio State University team responsible for the MVAPICH MPI library has demonstrated the performance achievement of SHARP on the Texas Advanced Computing Center Frontera supercomputer. From 5x higher performance for MPI AllReduce and up to 9x for MPI Barrier collective communications. For more information, see 
Scalable MPI Collectives using SHARP: Large Scale Performance Evaluation on the TACC Frontera System
.

The second generation of SHARP was introduced with the NVIDIA HDR 200Gb/s Quantum InfiniBand switch generation and added support for AI workloads. SHARPv2 includes support for large message reduction operations, supporting a single workload at a time. This version further improved the scalability and flexibility of the technology by supporting more complex data types and aggregation operations. 

SHARPv2 performance advantage was demonstrated with NVIDIA MLPerf submission and results in June 2021, demonstrating 17% higher BERT training performance. For more information, see 
MLPerf v1.0 Training Benchmarks: Insights into a Record-Setting NVIDIA Performance
.

Michael Houston, vice president and chief architect of AI systems at NVIDIA, presented the 
AllReduce performance benefits of SHARPv2
, in a UC Berkeley’s Machine Learning Systems course.

The 2x performance benefit of the AllReduce bandwidth translated into 17% higher BERT training performance.

 

 
Figure 1. Example from UC Berkeley’s Machine Learning Systems course 
(source:
 
Distributed deep learning, Part II: Scaling Constraints
)

Most recently, the third generation of SHARP was introduced with the 
NVIDIA Quantum-2 NDR 400G InfiniBand
 platform. SHARPv3 supports multi-tenant in-network computing for AI workloads, meaning that multiple AI workloads are supported in parallel compared to the single workload with SHARPv2.

SHARPv3 performance was presented by Jithin Jose, principal software engineer at Microsoft Azure in the session, 
Transforming Clouds to Cloud-Native Supercomputing: Best Practices with Microsoft Azure
. Jithin covered InfiniBand’s in-network computing technologies at Azure and showcased nearly an order of magnitude performance benefits for AllReduce latency.

 

 
Figure 2. AllReduce latency performance benefits for SHARPv3

End-to-end AI system optimization

A powerful example of SHARP can be seen with the all-reduce operation. Gradients are summed across multiple GPUs or nodes during model training, and SHARP aggregates the gradients in-network, avoiding the need to send full data sets between GPUs or across nodes. This reduces the communication time, leading to faster iteration times and higher throughput for AI workloads.

Before the era of in-network computing and SHARP, NVIDIA Collective Communication Library (NCCL) communication software would copy all the model weights from the graph, perform an all-reduce operation to sum the weights, and then write the updated weights back to the graph, resulting in multiple data copies. 

In 2021, the NCCL team began integrating SHARP, introducing user buffer registration. This enabled NCCL collectives to use pointers directly, eliminating the need to copy data back and forth during the process and improving efficiency.

Today, SHARP is tightly integrated with NCCL, which is widely used in distributed AI training frameworks. NCCL is optimized to take advantage of SHARP by offloading key collective communication operations to the network, significantly improving both the scalability and performance of distributed deep learning workloads.

SHARP technology helps to increase the performance of distributed computing applications. SHARP is being used by HPC supercomputing centers for their scientific computing workloads, and also by AI supercomputers for the AI applications. SHARP is the “secret sauce” that is enabling a competitive advantage. A large service provider uses SHARP to improve its performance across in-house AI workloads from 10–20%.  

SHARPv4

SHARPv4 introduces new algorithms to support a larger variety of collective communications that are now used in leading AI training applications. It will be released with the 
NVIDIA Quantum-X800 XDR InfiniBand switch platforms
, delivering the next level of in-network computing.

Summary

For more information, see the following resources:

Technical Blog posts:

NVIDIA Slashes BERT Training and Inference Times

Boosting NVIDIA MLPerf Training v1.1 Performance with Full Stack Optimization

Setting New Records at Data Center Scale Using NVIDIA H100 GPUs and NVIDIA Quantum-2 InfiniBand

Videos:

Tutorial: SHARP: In-Network Scalable Hierarchical Aggregation and Reduction Protocol

In-Network Computing with NVIDIA SHARP

Behind the Scenes with Azure AI Infrastructure (Presented by Microsoft) | GTC 24 2024 | NVIDIA On-Demand

Scalable MPI Collectives using SHARP: Large Scale Performance Evaluation on the TACC Frontera System

Run NCCL tests on GPU to check performance and configuration

Scalable Hierarchical Aggregation Protocol : A Hardware Architecture for Efficient Data Reduction

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Networking / Communications
 | 
Hardware / Semiconductor
 | 
NCCL
 | 
Intermediate Technical
 | 
Deep dive
 | 
featured
 | 
InfiniBand
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Scot Schultz
 

 

 
 Scot Schultz is an HPC technology specialist with a focus on artificial intelligence and machine learning systems. Scot has broad knowledge in distributed computing, operating systems, AI frameworks, high speed interconnects, and processor technologies. Throughout his career, with more than 25 years of experience in high-performance computing systems, his responsibilities included various engineering and leadership roles, including strategic HPC technology ecosystem enablement. Scot has been instrumental with the growth and development of numerous industry-standards organizations.
 
 
 

 

 View all posts by Scot Schultz

 

 

 

 

 

 

 

 

 

 

 
Comments
