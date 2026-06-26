---
source_id: nccl-nvidia-blog-wide
title: 'NVIDIA NVbandwidth: Your Essential Tool for Measuring GPU Interconnect and
  Memory Performance'
canonical_url: https://developer.nvidia.com/blog/nvidia-nvbandwidth-your-essential-tool-for-measuring-gpu-interconnect-and-memory-performance/
captured_at: '2026-06-26T01:57:10.842925+00:00'
content_hash: 9a6dc9cf64a00505a923e8eff0fb0b325163cfe4aae65c4bde6744d312210344
---
# NVIDIA NVbandwidth: Your Essential Tool for Measuring GPU Interconnect and Memory Performance

URL: https://developer.nvidia.com/blog/nvidia-nvbandwidth-your-essential-tool-for-measuring-gpu-interconnect-and-memory-performance/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2026/01/image1-1-768x432.jpg" style="display: block; margin-bottom: 5px; clear: both;" title="image1" width="768" />When you’re writing CUDA applications, one of the most important things you need to focus on to write great code is data transfer performance. This applies to...

Article Body:
Data Center / Cloud

 

 
 

 

 
English
中文

 

 

 
NVIDIA NVbandwidth: Your Essential Tool for Measuring GPU Interconnect and Memory Performance

 
 

 

 

 Apr 14, 2026
 

 

 By 
Eva Sitaridi
 and 
Banajit Goswami
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
NVbandwidth is a CUDA-based tool developed by NVIDIA for measuring bandwidth and latency of memory transfers in GPU systems, supporting a variety of test types including unidirectional, bidirectional, multi-GPU, and multi-node scenarios.
The tool offers both copy engine and kernel-based measurement methods, accommodates diverse interconnect topologies like NVLINK and PCIe, and provides flexible output options such as plain text and JSON.
NVbandwidth is used for performance optimization, system evaluation, troubleshooting, and hardware validation in CUDA applications, helping users identify bandwidth bottlenecks and benchmark interconnect performance across different system configurations.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

When you’re writing CUDA applications, one of the most important things you need to focus on to write great code is data transfer performance. This applies to both single-GPU and multi-GPU systems alike.  One of the tools you can use to understand the memory characteristics of your GPU system is NVIDIA 
NVbandwidth
.

In this blog post, we’ll explore what NVbandwidth is, how it works, its key features, and how you can use it to test and evaluate your own NVIDIA GPU systems. This post is intended for CUDA developers, system architects, and ML infrastructure engineers who need to measure and validate GPU interconnect performance.

What is NVbandwidth?

NVbandwidth is a CUDA-based tool that measures bandwidth and latency for various memory copy patterns across different links using either copy engine (CE) or kernel copy methods. It reports the current measured bandwidth on your system, providing valuable insights into the performance characteristics of your GPU setup. While modern GPUs boast impressive compute capabilities, their performance is frequently limited by how quickly data can be moved between different devices:

CPU memory to GPU memory

GPU memory to CPU memory

GPU memory to GPU memory

Understanding these performance characteristics helps developers:

Evaluate system performance

Measure memory access latency

Measure bandwidth in single and multi-node GPU deployments

Understand the performance implications of different memory transfer patterns

Diagnose bandwidth bottlenecks in CUDA applications

Optimize memory transfer patterns for specific workloads

Compare bandwidth and latency across multiple GPUs in a system

Performance monitoring and validation

Motivation

Memory bandwidth is a critical performance factor in modern GPU applications, such as LLMs. As models grow in size and complexity, efficient data movement becomes increasingly important for optimal performance in areas such as:

Model loading and initialization:
 Fast model loading is crucial for quick startup times

Inference performance:
 Affects real-time response capabilities

Training efficiency:
 Bandwidth limitations can affect the performance of different training phases:

Gradient updates

Parameter synchronization

Key features of NVbandwidth

Comprehensive bandwidth testing

NVbandwidth supports a wide range of bandwidth tests, including:

Unidirectional tests:

Host -> Device (H2D)

Device -> Host (D2H)

Device  ↔ Device (D2D)

Bidirectional tests:

Host ↔ Device

Device ↔ Device

Multi-GPU tests:

All to One (A2O)

One to All (O2A)

All to Host (A2H)

Host to All (H2A)

Multi-node tests (when built with MPI support):

Tests for measuring bandwidth across node boundaries in a cluster

Latency testing

Host ↔ Device latency

Device ↔ Device latency

Multiple copy methods

The tool implements two primary methods for memory transfers:

Copy Engine (CE)
: Uses CUDA’s built-in asynchronous memory copy functions

Streaming Multiprocessor (SM)
: Uses custom CUDA kernels to perform copies through the SM

This dual approach allows for a more comprehensive understanding of your system’s bandwidth capabilities.

Topology agnostic design

NVbandwidth is designed to work efficiently across different GPU interconnect topologies within a single-node or multi-node system, whether using NVLINK, NVLink C2C or PCIe. It doesn’t require explicit user knowledge of the system’s topology to function, making its use largely topology agnostic in practice. 

Flexible output options

Results can be displayed in:

Plain text format (default)

JSON format (using the -j option)

System requirements

To use nvbandwidth, you’ll need:

CUDA-enabled NVIDIA GPU

CUDA toolkit (version 11.X or above for the single-node version and 12.3 for the multinode version)

NVIDIA display driver compatible with the CUDA toolkit version

C++17 compatible compiler (GCC 7.x or above for Linux)

CMake (version 3.20 or above, 3.24+ recommended)

Boost program options library

Multi-node version only:

CUDA 12.3 toolkit and 550 driver or above

MPI installation

For more detailed build instructions interested users can refer to the 
README instructions
. 

Using NVbandwidth

Basic usage

To comprehensively measure your system’s interconnect bandwidth, simply run:

./nvbandwidth

Suppose you want to measure device-to-device bandwidth using the copy engine method, with a 1GiB buffer and 10 iterations, and output the results in JSON format:

./nvbandwidth -t device_to_device_memcpy_read_ce -b 1024 -i 10 -j

Example output

Here’s an example of what the output looks like when running a host-to-device copy test: 

Running host_to_device_memcpy_ce.
memcpy CE CPU(row) -> GPU(column) bandwidth (GB/s)
 0 1
 0 55.63 55.64
SUM host_to_device_memcpy_ce 111.27
COEFFICIENT_OF_VARIATION host_to_device_memcpy_ce 0.00
NOTE: The reported results may not reflect the full capabilities of the platform.
Performance can vary with software drivers, hardware clocks, and system topology.

Under the hood: How NVbandwidth works

Architecture

NVbandwidth follows a modular design that separates test definition, memory operations, and result reporting into distinct subsystems:

CLI interface: Handles user inputs and orchestrates test execution

Test case framework: Provides a standard interface for defining different bandwidth tests

Memory copy framework: Core component that performs memory operations

CUDA kernels: Specialized CUDA kernels for performing memory operations

Output System: Formats and presents test results NVbandwidth.cpp:178-246

Measurement details

The tool uses the following approach to measure performance accurately:

First, it enqueues a spin kernel that spins on a flag in host memory

The spin kernel spins on the device until all events for measurement have been fully enqueued

Next, it enqueues a start event, a certain count of memcpy iterations, and finally a stop event

Finally, it releases the flag to start the measurement

This process ensures that the overhead of enqueuing operations is excluded from the measurement of actual transfer over the interconnect.

Bidirectional bandwidth tests

For bidirectional tests, NVbandwidth measures bandwidth when data is flowing in both directions simultaneously. See Figure 1, below:

 

 
Figure 1: CPU and GPU connected by H2D and D2H data directions

CE copies

Stream A (measured stream) performs writes to the device, while Stream B in the opposite direction produces reads.

SM copies

The test launches a kernel copy where alternating thread warps are copying data in alternating directions.

Multi-node operation

Running NVbandwidth in multi-node mode requires additional setup and configuration.

Start the NVIDIA Internode Memory Exchange Service (IMEX):

sudo systemctl start nvidia-imex.service

Configure node addresses in 
/etc/nvidia-imex/nodes_config.cf
g

2. Run with MPI:

mpirun --allow-run-as-root --map-by ppr:4:node --bind-to core -np 8 --report-bindings \ 
 -q -mca btl_tcp_if_include enP5p9s0 --hostfile /etc/nvidia-imex/nodes_config.cfg ./nvbandwidth -p multinode

NVIDIA Multi-Node NVLink
 (MNNVL) systems require a fully configured and operational IMEX domain for all the nodes that form the NVLink domain. NVbandwidth uses MPI for coordinating measurements across nodes. See Figure 2, below:

 

 
Figure 2: Example multi-node, multi-GPU system connected with NVLink.

Example output

Here’s an example of what the output looks like when measuring peer-to-peer performance between nodes on a multi-node system.

Running multinode_device_to_device_memcpy_read_ce.
memcpy CE GPU(row) -> GPU(column) bandwidth (GB/s)
 0 1 2 3 4 5 6 7
 0 N/A 397.39 397.44 397.59 397.50 397.52 397.66 397.55
 1 397.65 N/A 397.35 397.46 397.48 397.53 397.53 397.59
 2 397.65 397.35 N/A 397.57 397.39 397.55 397.53 397.50
 3 397.57 397.37 397.35 N/A 397.50 397.50 397.52 397.53
 4 397.68 397.30 397.44 397.55 N/A 397.53 397.52 397.52
 5 397.66 397.26 397.48 397.46 397.52 N/A 397.50 397.59
 6 397.68 397.39 397.48 397.59 397.52 397.44 N/A 397.61
 7 397.68 397.41 397.42 397.48 397.52 397.50 397.53 N/A

NVbandwidth use cases

Performance optimization

By understanding the bandwidth characteristics of your system, you can optimize your CUDA applications to make better use of available bandwidth. For example, you might discover that certain transfer patterns are more efficient than others for your specific hardware configuration.

System evaluation and testing

NVbandwidth provides a standardized way to measure and compare bandwidth performance across different systems, making it valuable for testing and system evaluation. 

Troubleshooting

If your CUDA application is experiencing performance issues, NVbandwidth can help identify if bandwidth limitations are a contributing factor. NVbandwidth reports the current measured bandwidth on a specific system configuration. Performance results may vary significantly based on multiple factors, such as GPU model, interconnect generation, current clocks and other aspects of system configuration.

Hardware validation
: After installing new GPUs, upgrading drivers, or making system changes, NVbandwidth can verify that memory bandwidth performance meets performance expectations. This helps identify hardware issues, driver problems, or configuration errors that might impact application performance.

Performance regression testing
: When deploying new software versions or system updates, NVbandwidth provides a baseline for detecting performance regressions. By comparing bandwidth measurements before and after changes, you can quickly identify if updates have negatively impacted system performance.

Going further

NVbandwidth is an indispensable tool for measuring and understanding the bandwidth characteristics of NVIDIA GPU systems. It provides valuable insights for optimizing CUDA applications, evaluating system performance, and troubleshooting issues by offering a comprehensive test suite, flexible configuration options, and support for both single-node and multi-node deployments.

By leveraging NVbandwidth, you can make informed decisions to maximize the performance of your CUDA applications and ensure optimal data transfer capabilities within your GPU setup. As GPU clusters evolve in size and complexity, NVbandwidth continues to advance, addressing new challenges in bandwidth measurement and analysis, including testing performance scalability.Notes

For more in-depth information, explore these additional resources.

Overview (NVIDIA/nvbandwidth)

Architecture (NVIDIA/nvbandwidth)

Building and Running (NVIDIA/nvbandwidth)

To begin optimizing your GPU system’s performance, download and try NVbandwidth today!

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Center / Cloud
 | 
Developer Tools & Techniques
 | 
Networking / Communications
 | 
HPC / Scientific Computing
 | 
CUDA
 | 
NCCL
 | 
Intermediate Technical
 | 
featured
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Eva Sitaridi
 

 

 
 Eva Sitaridi is a senior system software engineer on NVIDIA’s CUDA Performance team, where she works at the intersection of GPU architecture, system software, and performance engineering. Her work focuses on understanding and optimizing how GPU‑accelerated systems behave in practice by analyzing performance across the stack. She holds a PhD in Computer Science from Columbia University, where her research centered on GPU‑accelerated in‑memory data analytics.
 
 
 

 

 View all posts by Eva Sitaridi

 

 

 

 

 

 

 

 

 

 

 About Banajit Goswami
 

 

 
 Banajit Goswami is an engineering manager at NVIDIA, where he leads the CUDA performance team. Before diving deep into CUDA performance, Banajit worked on systems software for embedded platforms, focusing on power and performance optimization. He holds bachelor’s degrees in electronics and telecommunication engineering from Gauhati University.
 
 
 

 

 View all posts by Banajit Goswami

 

 

 

 

 

 

 

 

 

 

 
Comments
