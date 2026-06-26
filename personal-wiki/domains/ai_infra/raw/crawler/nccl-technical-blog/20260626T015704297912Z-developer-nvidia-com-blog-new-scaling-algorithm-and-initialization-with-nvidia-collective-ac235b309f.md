---
source_id: nccl-technical-blog
title: New Scaling Algorithm and Initialization with NVIDIA Collective Communications
  Library 2.23
canonical_url: https://developer.nvidia.com/blog/new-scaling-algorithm-and-initialization-with-nvidia-collective-communications-library-2-23/
captured_at: '2026-06-26T01:57:04.297912+00:00'
content_hash: ac235b309fb193f2c128608999f6377794aea6c809ea46a2f812d47b888c7554
---
# New Scaling Algorithm and Initialization with NVIDIA Collective Communications Library 2.23

URL: https://developer.nvidia.com/blog/new-scaling-algorithm-and-initialization-with-nvidia-collective-communications-library-2-23/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2025/01/cubes-768x432.jpg" style="display: block; margin-bottom: 5px; clear: both;" title="cubes" width="768" />The NVIDIA Collective Communications Library (NCCL) implements multi-GPU and multinode communication primitives optimized for NVIDIA GPUs and networking. NCCL...

Article Body:
Networking / Communications

 

 
 

 

 
English
中文

 

 

 
New Scaling Algorithm and Initialization with NVIDIA Collective Communications Library 2.23

 
 

 

 

 Jan 31, 2025
 

 

 By 
Sylvain Jeaugey
, 
Giuseppe Congiu
, 
Thomas Gillis
, 
Ben Williams
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

 

 

 

 

 

 

 

 

 
The NVIDIA Collective Communications Library (NCCL) 2.23 introduces the Parallel Aggregated Trees (PAT) algorithm for AllGather and ReduceScatter operations, achieving logarithmic scaling and improving performance for small to medium message sizes.
NCCL 2.23 accelerates initialization with the new ncclCommInitRankScalable API, allowing multiple unique IDs to be used during communicator creation, and enabling in-band networking for bootstrap communication.
The release also includes intranode user buffer registration support for NvLink and PCIe P2P transports, and a new profiler plugin API to measure fine-grain NCCL performance, enabling domain-specific monitoring and diagnostic tools.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

The 
NVIDIA Collective Communications Library (NCCL)
 implements multi-GPU and multinode communication primitives optimized for NVIDIA GPUs and networking. NCCL is a central piece of software for multi-GPU deep learning training. It handles any kind of inter-GPU communication, be it over PCI, NVLink, or networking. It uses advanced topology detection, optimized communication graphs, and tuning models to get the best performance straight out of the box on NVIDIA GPU platforms.

In this post, we discuss the new features and fixes released in NCCL 2.23. Check out the 
NVIDIA/nccl
 GitHub repo. 

Release highlights and features 

NVIDIA Magnum IO
 NCCL is a library designed to optimize inter-GPU and multinode communication, crucial for efficient parallel computing in AI and high-performance computing (HPC) applications. The value of this release lies in its new features: 

New PAT algorithm for ReduceScatter and AllGather:
 We introduce the Parallel Aggregated Trees (PAT) algorithm, based on Brucks, for AllGather and ReduceScatter, achieving logarithmic scaling. 

Accelerated initialization: 
Improved initialization performance, including the ability to use in-band networking for bootstrap communication. 

ncclCommInitRankScalable
: 
A new initialization API, for using multiple 
ncclUniqueId
s to speed up initialization at large scales. 

Intranode user buffer registration:
 Take advantage of registered user buffers for intranode operations. 

New profiler plugin API:
 API hooks to measure fine-grain NCCL performance. 

The following sections dive deeper into the details of the new features: 

PAT logarithmic scaling for ReduceScatter and AllGather   

New 
ncclCommInitRankScalable
 API 

Accelerated bootstrap operations 

Intranode user buffer registration 

New profiler plugin API 

Bug fixes and minor features

PAT logarithmic scaling for ReduceScatter and AllGather 

The PAT algorithm is a variation of the Bruck algorithm, which features a logarithmic number of network steps for small sizes at scale, progressively increasing the number of network transfers as sizes increase, to keep buffering needs minimal. It applies to both AllGather and ReduceScatter. You can expect small to medium message sizes to perform better with PAT, with this improvement increasing as your workload scales. 

This algorithm is executing a binomial tree shifted for each rank. Its advantage compared to similar algorithms like recursive doubling is that it works on any number of ranks and does not require a power of two. 

Initially, PAT only supports one GPU per node. The case of one GPU per node ReduceScatter and AllGather is important for 
large language model (LLM)
 training, where pipeline parallelism and tensor parallelism are in dimensions orthogonal to data parallelism. The tensor parallelism dimension is usually aligned to the intranode NVLink connectivity, meaning that other dimensions will only have one GPU per node. 

Look for our forthcoming paper describing the details of the algorithm.

New 
ncclCommInitRankScalable
 API 

This feature adds a new initialization function, 
ncclCommInitRankScalable
, to enable leveraging multiple unique IDs during the communicator creation. This addition avoids the all-to-one communication patterns during the initialization and provides a more scalable initialization performance. 

At communicator creation, NCCL needs to obtain the addresses of all the communicator’s ranks (bootstrap step). To do so, NCCL relies on a unique ID known to all the ranks. During the bootstrap step of the communicator initialization, each rank exchanges its address with the known unique ID, creating an all-to-one communication pattern, and a significant bottleneck at scale. 

With 
ncclCommInitRankScalable
, the user is now free to provide more than one unique ID to be used during the bootstrap. To achieve the highest gain, NCCL will spread the load across multiple unique IDs, enabling a constant bootstrap time at scale, if the number of unique IDs provided scales with the size of the communicator. 

This new API requires multiple ranks to create a unique ID. To obtain the best performance, we recommend spreading the unique IDs as homogeneously as possible among the ranks. 

Accelerated bootstrap operations

In the 2.23 release, we improved the overall performance of the initialization code. We eliminated some of the bootstrap collectives needed, as well as performance tuning in the bootstrap step. 

You can now use the fast network (IB/RoCE/…) for out-of-band communication to speed up the two linear steps of the initialization, bootstrap and allgather. That feature is disabled by default to avoid using wrongly configured devices (the use of 
ncclNet
 devices happens before the topology detection). You can enable it with 
NCCL_OOB_NET_ENABLE=1
. 

Additionally, you can specify which interface should be used with 
NCCL_OOB_NET_IFNAME
. By default, NCCL will use the first 
ncclNet
 device found on that network.

Intranode user buffer registration 

NCCL never requires you as the user to register and maintain any persistent buffers to function. This is a great feature for ease of usability, but it does come with performance tradeoffs. Without direct access, more control flow and buffering must occur when NCCL transfers data. This consumes more GPU resources and results in higher overheads for moving the same amount of data compared to explicitly registered and mapped buffers.

Whenever possible, NCCL developers are advised to register their buffers using 
ncclCommRegister
 to allow NCCL to use all available optimizations. The NCCL team is always working to add more use cases for registered user buffers. The 2.23 release implements intranode user buffer (UB) registration support for NvLink and PCIe P2P transports.

The main benefit of Intranode UB registration is to avoid extra copies among peers. This reduces pressure on the memory subsystem, improves NCCL communication performance, and also improves the computation and communication overlap. All NCCL collectives and sendrecv-based operations are supported except for 
ncclReduce
 and 
ncclReduceScatter
 (they would not benefit). 

There are two ways to enable intranode UB registration. The first one is registering buffers through 
ncclCommRegister
 explicitly, and the buffers will be registered only when the corresponding NCCL collectives are called. The second is by capturing NCCL operations through CUDA Graphs, and all user buffers will be automatically registered during graph capture. For more guidelines and requirements, refer to the 
NCCL documentation
. 

In addition to intranode communication over NVLink and PCIe, the feature works on multinode NVLink (MNNVL) systems within each NVLink domain.

New profiler plugin API 

As the GPU clusters’ scale increases, performance anomalies become harder to detect and root cause. Domain-specific monitoring and diagnostic tools are needed to collect and analyze telemetry data with minimal overhead for the running jobs. The NCCL profiler plugin interface has been designed to address these concerns. The interface design also makes it easy to adopt by DL framework profilers such as PyTorch Kineto. 

The new 
NCCL_PROFILER_PLUGIN
 environment variable controls profiler plugin loading and initialization in the same way other NCCL plugins are loaded and initialized. Once loaded, the profiler plugin can enable NCCL events profiling by setting the event activation mask that NCCL exposes to the profiler during initialization. The event activation mask is a 32-bit integer where every bit represents a NCCL profiler event. Currently, NCCL supports the following events: 

ncclProfileGroup
 (bit-0): Group event 

ncclProfileColl
 (bit-1): Collective event 

ncclProfileP2p
 (bit-2): Point-to-point event 

ncclProfileProxyOp
 (bit-3): Proxy progress channel event 

ncclProfileProxyStep
 (bit-4): Proxy progress step event 

ncclProfileProxyCtrl
 (bit-5): Proxy progress internal state event 

NCCL expresses events in a hierarchical form. For example, collectives can be grouped together, and proxy operations assist the GPU with point-to-point transfer of individual data chunks across the available network communication channels. Therefore, NCCL presents the corresponding events to the profiler, preserving this relationship. A diagram for the NCCL event hierarchy is shown below:

ncclProfileGroup 
| 
+- ncclProfileColl 
| | 
| +- ncclProfileProxyOp 
| | 
| +- ncclProfileProxyStep 
| 
+- ncclProfileP2p 
 | 
 +- ncclProfileProxyOp 
 | 
 +- ncclProfileProxyStep 
 
ncclProfileProxyCtrl

This hierarchical representation enables profiler plugins to present events to users in a more meaningful and comprehensible form. 

NCCL also provides an example profiler plugin in the 
ext-profiler/example
 directory that can be used as a template to develop third-party profiler plugins. 

In total, the profiler plugin interface defines the following five function callbacks: 

ncclResult_t (*init)( 
 void** context, 
 int* eActivationMask); 
 
ncclResult_t (*startEvent)( 
 void* context, 
 void** eHandle, 
 ncclProfilerEventDescr_t* eDescr); 
 
ncclResult_t (*stopEvent)( 
 void* eHandle); 
 
ncclResult_t (*recordEventState)( 
 void* eHandle, 
 ncclProfilerEventState_t eState, 
 NcclProfilerEventStateArgs_t* eStateArgs); 
 
ncclResult_t (*finalize)(void* context);

The profiler 
init
 function takes an event activation mask pointer and returns an opaque context object to NCCL. The context provides isolation between profiler instances, while the event activation mask is used by the profiler to notify NCCL about what events should be profiled; for example, setting *eActivationMask = ncclProfileColl | ncclProfileProxyOp. 

The profiler 
startEvent
 
function takes a profiler context and an event descriptor. The profiler uses the descriptor information to allocate a new event object and initialize it. Afterwards, the profiler returns an opaque handle that NCCL can use to perform further operations on the event; for example, record state updates. 

The profiler 
stopEvent
 
function takes an event handle and marks the event as complete. Afterwards, the event handle can no longer be used (the profiler might internally recycle the corresponding object for future events). 

The profiler 
recordEventState
 
function takes an event handle, an event state, and (optionally) an event state argument object. This function enables the profiler to update events that can transition through different states in NCCL. One example is proxy events, where the proxy needs to coordinate with both the GPU and the network while transferring data, moving from one state to another in the process. 

The profiler 
finalize
 
function takes the profiler context and releases all the resources associated with it.

Bug fixes and minor features 

NCCL 2.23 provides the following additional updates: 

Asynchronous graph allocation makes calls to 
cudaMalloc
 and 
cudaMemcpy
 during graph allocation asynchronous. Significantly speeds up graph capture. 

Use fatal IB asynchronous events to stop network operations helps catch link down errors and other fatal asynchronous events within NCCL. 

Set P2P level to PXB on AMD CPUs when using more than two GPUs per node. 

Improve the 
init
 logs to report the actual NCCL function: Informs the user if NCCL is performing 
ncclCommInitRank
 or 
ncclCommSplit
. 

Add 
NCCL_CONF_FILE
 variable 

Increase default IB timeout from 18 to 20 

Add new check for NVIDIA peermem. Works with recent Linux kernels. 

Fix old performance regression. When mixing small and large operations. 

Fix crash when NUMA IDs are equal to -1. 

Fix tree graph search when 
NCCL_CROSS_NIC
 is set to 1. 

Summary

NVIDIA NCCL 2.23 introduces new features and improvements for optimizing inter-GPU and multinode communication, crucial for AI and HPC applications. Key enhancements include the new PAT Algorithm, accelerated initialization at scale, intranode user buffer registration, and the new profiler plugin API. 

To learn more about the previous release, see 
Memory Efficiency, Faster Initialization, and Cost Estimation with NVIDIA Collective Communications Library 2.22
. 

Learn more about 
Magnum IO
 and 
NCCL
.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Center / Cloud
 | 
Networking / Communications
 | 
Cloud Services
 | 
HPC / Scientific Computing
 | 
CUDA
 | 
Magnum IO
 | 
NCCL
 | 
NVSHMEM
 | 
Intermediate Technical
 | 
News
 | 
featured
 | 
Release
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Sylvain Jeaugey
 

 

 
 Sylvain Jeaugey is a senior software engineer at NVIDIA developing the NCCL library since its creation in 2015. He has 15 years of experience in large scale distributed computing. He has been working on various MPI implementations, developing and integrating high-speed networks technologies, and designing large network fabrics.
 
 
 

 

 View all posts by Sylvain Jeaugey

 

 

 

 

 

 

 

 

 

 

 About Giuseppe Congiu
 

 

 
 Giuseppe Congiu is a senior software engineer working on the NCCL team since January 2024. Before joining NVIDIA, he covered several positions, including research scientist at Innovating Computing Laboratory, postdoctoral fellow at Argonne National Laboratory, and software engineer at Seagate. In these positions, he worked on a range of exascale projects, including ExaPAPI, ExaMPI, and the EU-funded DEEP-ER project.
 
 
 

 

 View all posts by Giuseppe Congiu

 

 

 

 

 

 

 

 

 

 

 About Thomas Gillis
 

 

 
 Thomas Gillis is a senior software engineer at NVIDIA. He contributes to the NCCL library with a focus on initialization and network communication. He graduated from UCLouvain (Belgium) with an PhD in Mechanical Engineering in 2019, and a master’s degree in Applied Mathematics in 2015. Thomas previously held postdoctoral research positions at the Massachusetts Institute of Technology (MIT) and the Argonne National Laboratory.
 
 
 

 

 View all posts by Thomas Gillis

 

 

 

 

 

 

 

 

 

 

 About Ben Williams
 

 

 
 Ben Williams is a senior software engineer at NVIDIA. He is a developer of the NCCL library with an emphasis on GPU-network interactions and system topology. He graduated from Iowa State University with a master’s degree in Computer Engineering in 2017.
 
 
 

 

 View all posts by Ben Williams

 

 

 

 

 

 

 

 

 

 

 About Fred Oh
 

 

 
 Fred is a senior product marketing manager for CUDA, CUDA on WSL, and CUDA Python. Fred has a B.S. in Computer Science and Math from UC Davis. He began his career as a UNIX software engineer porting kernel services and device drivers to x86 architectures. He loves Star Wars, Star Trek and the NBA Warriors.
 
 
 

 

 View all posts by Fred Oh

 

 

 

 

 

 

 

 

 

 

 
Comments
