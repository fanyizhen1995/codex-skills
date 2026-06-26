---
source_id: nccl-technical-blog
title: Memory Efficiency, Faster Initialization, and Cost Estimation with NVIDIA Collective
  Communications Library 2.22
canonical_url: https://developer.nvidia.com/blog/memory-efficiency-faster-initialization-and-cost-estimation-with-nvidia-collective-communications-library-2-22/
captured_at: '2026-06-26T01:57:04.298674+00:00'
content_hash: 32a1d0c11887317fef8c74c55e7c7ac0946eb5b1eedf177cf85dbacebcc031f3
---
# Memory Efficiency, Faster Initialization, and Cost Estimation with NVIDIA Collective Communications Library 2.22

URL: https://developer.nvidia.com/blog/memory-efficiency-faster-initialization-and-cost-estimation-with-nvidia-collective-communications-library-2-22/

RSS Summary:
<img alt="Decorative image of a cube of green cubes, surrounded by other cubes on a dark background." class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2024/08/cube-of-light-featured-768x432.jpg" style="display: block; margin-bottom: 5px; clear: both;" title="cube-of-light-featured" width="768" />For the past few months, the NVIDIA Collective Communications Library (NCCL) developers have been working hard on a set of new library features and bug fixes....

Article Body:
Networking / Communications

 

 
 

 

 
English
中文

 

 

 
Memory Efficiency, Faster Initialization, and Cost Estimation with NVIDIA Collective Communications Library 2.22

 
 

 

 

 Sep 16, 2024
 

 

 By 
Giuseppe Congiu
, 
Kamil Iskra
, 
Ben Williams
, 
Sylvain Jeaugey
, 
Harry Petty
 and 
Fred Oh
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
The NVIDIA Collective Communications Library (NCCL) 2.22 release introduces lazy connection establishment, which delays the creation of connections until they are needed, reducing GPU memory overhead.
NCCL 2.22 includes a new API, ncclGroupSimulateEnd, to help application developers estimate the time it takes to complete a given operation, allowing for better compute and communication overlap.
The release also optimizes ncclCommInitRank initialization time by up to 90% through lazy connection establishment and intra-node topology fusion, significantly reducing the time it takes to create many communicators.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

For the past few months, the NVIDIA Collective Communications Library (NCCL) developers have been working hard on a set of new library features and bug fixes. In this post, we discuss the details of the 
NCCL 2.22
 release and the pain points addressed.

Release highlights

NVIDIA Magnum IO NCCL is a library designed to optimize inter-GPU and multi-node communication, crucial for efficient parallel computing in AI and HPC applications. The value of this release lies in its new features:

Lazy connection establishment for GPU memory saving: 
Delays the creation of connections until they are needed, reducing the GPU memory overhead.

New API for cost estimation and workload balancing:
 Exposes a new API to help you optimize compute and communication overlap or research the NCCL cost model.

Optimizations and instrumentation for 
ncclCommInitRank
: Eliminates redundant topology queries, accelerating initialization by up to  90% for applications that create many communicators.

Support for multiple subnets with IB Router: 
Adds support for communication in jobs spanning multiple InfiniBand subnets, which enables DL training jobs to run on InfiniBand networks that are larger than 40K endpoints.

Features

In this section, we dive deeper into the details of each new feature:

Lazy connection establishment

New cost model API

Initialization optimizations and instrumentation

New tuner plugin interface

Static plugin linking

Group semantics for abort or destroy

IB Router support

Lazy connection establishment

NCCL works with a set of persistent, statically allocated connections and buffers for the operation of its eager data transfer protocol. For every given algorithm and protocol that NCCL supports, it creates a separate set of connections and buffers, each requiring multiple megabytes of GPU memory.

For reference, an 
algorithm
 defines the high-level movement of data among participants for a given collective, and a 
protocol
 defines the way NCCL sends data. A given algorithm and protocol are chosen based on the operation, message size, scale, and topology to achieve optimal performance.

Before 2.22, NCCL would form connections between peers for every combination
 
of these, potentially wasting megabytes of GPU memory for algorithms and protocols that would never be used. 

Now, NCCL waits to form connections for a given algorithm until the first time it’s needed. This decreases the NCCL memory overhead by a good margin, especially when NCCL is used in a narrow scope. For instance, if you only ever run 
ncclAllReduce
 at the same message size over and over, you should only be using one algorithm on a given system.

The feature is enabled by default but can be disabled by setting the env 
NCCL_RUNTIME_CONNECT=0
.

In the previous scenario on a single node DGX-H100, we saw a 3.5x reduction in GPU memory usage by NCCL only using the Ring algorithm, and a 1.47x reduction running only NVSwitch
–
based reductions.

New cost model API

Application developers want to take full advantage of the compute, memory, and bandwidth resources available on NVIDIA systems. 

Ideally, compute and communication are perfectly overlapped, both perfectly fed with work, and the full capabilities of your hardware are pushed to the max. Doing this is hard when running large-scale HPC and AI applications, especially with one codebase running on multiple platforms.

To help solve this problem, NCCL added a new API to enable you to see
 
how long it thinks a given operation will take. This API is called 
ncclGroupSimulateEnd
.
 It is used the same way as 
ncclGroupEnd
, 
which makes it easy for anyone familiar with writing NCCL code. 

The difference is it launches no communications operations. Instead, NCCL calculates how long it thinks the operation will take and sets this in the supplied 
ncclSimInfo_t
 structure.

ncclGroupStart()
ncclAllReduce()
ncclGroupSimulateEnd(sim_t)
printf("Estimated completion time=%f microseconds\n", sim.time);
configureComputeAmount(sim.time, &computeIters, &workItemSize);

However,  the values returned by this API do not perfectly align with reality. It’s an estimate based on the NCCL internal model. As of 2.22, this API only returns the estimated time of the last operation in the group.

Initialization optimizations and instrumentation

With the varied and ever-increasing scale of customer workloads, reducing overhead from NCCL initialization is an increasing priority for the NCCL team. 

Even with single-node jobs, the increased number of NVLink interconnects on NVIDIA Hopper GPUs that must be individually discovered and connected has resulted in a considerable initialization time increase.

We wanted to improve the initialization time, and we had to study the overhead of each initialization step. We started with instrumenting each phase within 
ncclCommInitRank
 and studied the timing of each at various scales. You now see this whenever you collect standard NCCL logs (
NCCL_DEBUG=INFO
).

There’s also a new 
NCCL_PROFILE
 debug subsystem that gives just the instrumentation information if you don’t care about the rest of the NCCL initialization logs (
NCCL_DEBUG=INFO NCCL_DEBUG_SUBSYS=PROFILE
).

One promising area for improvement was the previously discussed connection establishment. Switching to lazy establishment can save memory and also reduce initialization time.

Another area was topology discovery, which is an initialization step where every NCCL rank determines the hardware available on the node. This includes which GPUs and NICs are on the system, how many NVLink interconnects are present, as well as the PCI topology and NUMA affinities. 

As it turned out, the way NCCL performed NVLink discovery was suboptimal, because every rank was discovering all the links on its own, leading to redundancy and congestion.

To address this issue, we reused topology fusion code, first introduced in NCCL 2.21 as part of the Multi-Node NVLink (MNNVL) support, where partial information available on each node was being combined during bootstrap using inter-node communication, resulting in a complete picture of the NVLink topology. 

For 2.22, we extended this feature to work within each node. Now every rank discovers information about its own GPU only and then combines these results with its peers using intra-node topology fusion.

Together, lazy connection establishment and intra-node topology fusion can shave 90% (~6 seconds) off 
ncclCommInitRank
 execution time on a single 8x H100 GPU system. What formerly took ~6.7 seconds now takes ~0.7. For applications that create many communicators during their execution, this can reduce initialization time by a huge amount.

New tuner plugin interface

With the new tuner plugin interface (v3), NCCL supplies the plugin with a per-collective 2D cost table, reporting the estimated time needed to carry out the operation for every combination of algorithm and protocol. 

NCCL sets the table entries that are not compatible with the detected topology to 
-1
, to indicate to external tuners that these combinations are not supported/allowed to be overwritten. 

To select a specific combination, the external tuner updates the value for the desired algorithm or protocol combination to 
0
 or the minimum value across the whole table. After the plugin has updated the cost table, NCCL can use it to select the final configuration for the given collective.

Static plugin linking

The NCCL team exposes a plugin model for partners to provide their own tuning or network backend in place of the NCCL internal model and InfiniBand plugin. Some partners want to statically link these plugins against their application binaries for convenience’s sake and to avoid mishaps in loading the wrong one. 

If an application has statically linked either a network or tuner plugin, specify it by setting 
NCCL_NET_PLUGIN
 or 
NCCL_TUNER_PLUGIN
 to 
STATIC_PLUGIN
.

Group semantics for abort or destroy

Previously, 
ncclCommDestroy
 and 
ncclCommAbort
 would block the calling thread until completed. 

With multi-dimensional parallel ML workloads, one process manages multiple NCCL communicators, and each must be eventually torn down using these APIs. We provided semantics for these applications to destroy more than one communicator at a time in a grouped fashion to avoid deadlocks and provide a better user experience.

IB Router support

With this feature, NCCL can operate across different Infiniband subnets, connected by one or more routers. NCCL automatically detects when two communicating end-points are on different subnets of an InfiniBand network and exchanges GID information required to establish a connection and communicate. 

When routing between subnets, FLID can be used to identify a group of routers for forwarding and enable higher performance and adaptive routing between subnets. NCCL 2.22 automatically detects the presence of FLID and uses it for connections between endpoints on different subnets.

Bug fixes and minor features

NCCL 2.22 provides the following additional updates:

Added support for the 
allreduce
 tree algorithm on DGX Google Cloud.

Logged the NIC name in IB async errors.

Fixed aggregated collective performance.

Fixed the performance of registered send and receive operations.

Added infrastructure code for NVIDIA Trusted Computing Solutions.

Added separate traffic class for IB and RoCE control messages to enable advanced QoS (set with 
NCCL_IB_FIFO_TC
).

Added support for PCI peer-to-peer communications across sub-parts of partitioned Broadcom PCI switches.

 Summary

The NCCL 2.22 release introduces several significant features and optimizations aimed at improving performance and efficiency for high-performance computing (HPC) and AI applications. Improvements also include a new tuner plugin interface, support for static linking of plugins, and enhanced group semantics to prevent deadlocks.

For more information, see 
Magnum IO
 and 
NCCL
. Provide feedback on the 
GPU-Accelerated Libraries
 forum.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Center / Cloud
 | 
Networking / Communications
 | 
Simulation / Modeling / Design
 | 
Cloud Services
 | 
Magnum IO
 | 
NCCL
 | 
NVLink
 | 
Intermediate Technical
 | 
News
 | 
Accelerated Computing Libraries
 | 
featured
 | 
Internet/Communications
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Giuseppe Congiu
 

 

 
 Giuseppe Congiu is a senior software engineer working on the NCCL team since January 2024. Before joining NVIDIA, he covered several positions, including research scientist at Innovating Computing Laboratory, postdoctoral fellow at Argonne National Laboratory, and software engineer at Seagate. In these positions, he worked on a range of exascale projects, including ExaPAPI, ExaMPI, and the EU-funded DEEP-ER project.
 
 
 

 

 View all posts by Giuseppe Congiu

 

 

 

 

 

 

 

 

 

 

 About Kamil Iskra
 

 

 
 Kamil Iskra is a senior software engineer at NVIDIA working on NCCL. He has over 20 years of experience in large-scale parallel and distributed computing. He has worked on low-level system software in areas such as communication and I/O, memory management, and resource management.
 
 
 

 

 View all posts by Kamil Iskra

 

 

 

 

 

 

 

 

 

 

 About Ben Williams
 

 

 
 Ben Williams is a senior software engineer at NVIDIA. He is a developer of the NCCL library with an emphasis on GPU-network interactions and system topology. He graduated from Iowa State University with a master’s degree in Computer Engineering in 2017.
 
 
 

 

 View all posts by Ben Williams

 

 

 

 

 

 

 

 

 

 

 About Sylvain Jeaugey
 

 

 
 Sylvain Jeaugey is a senior software engineer at NVIDIA developing the NCCL library since its creation in 2015. He has 15 years of experience in large scale distributed computing. He has been working on various MPI implementations, developing and integrating high-speed networks technologies, and designing large network fabrics.
 
 
 

 

 View all posts by Sylvain Jeaugey

 

 

 

 

 

 

 

 

 

 

 About Harry Petty
 

 

 
 Harry Petty is a senior technical marketing manager for HPC and AI edge applications at NVIDIA. Previously, he was a principal engineer and marketing director at Cisco Systems where he brought SDN innovations to market for hybrid cloud, multitenant security, and data center application performance. Harry has an MBA from Booth Graduate School of Business and a BS in mathematics and computer science from the University of Dayton.
 
 
 

 

 View all posts by Harry Petty

 

 

 

 

 

 

 

 

 

 

 About Fred Oh
 

 

 
 Fred is a senior product marketing manager for CUDA, CUDA on WSL, and CUDA Python. Fred has a B.S. in Computer Science and Math from UC Davis. He began his career as a UNIX software engineer porting kernel services and device drivers to x86 architectures. He loves Star Wars, Star Trek and the NBA Warriors.
 
 
 

 

 View all posts by Fred Oh

 

 

 

 

 

 

 

 

 

 

 
Comments
