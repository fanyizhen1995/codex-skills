---
source_id: nccl-nvidia-blog-wide
title: Achieving Peak System and Workload Efficiency on NVIDIA GB200 NVL72 with Slurm
  Block Scheduling
canonical_url: https://developer.nvidia.com/blog/achieving-peak-system-and-workload-efficiency-on-nvidia-gb200-nvl72-with-slurm-block-scheduling/
captured_at: '2026-06-26T01:57:10.842279+00:00'
content_hash: d8bc92f3334670f16875d253879bb685d684f9acdc610a929d1222598f6eb8fe
---
# Achieving Peak System and Workload Efficiency on NVIDIA GB200 NVL72 with Slurm Block Scheduling

URL: https://developer.nvidia.com/blog/achieving-peak-system-and-workload-efficiency-on-nvidia-gb200-nvl72-with-slurm-block-scheduling/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2026/05/nvidia-gb200-nvl72-768x432.png" style="display: block; margin-bottom: 5px; clear: both;" title="nvidia-gb200-nvl72" width="768" />NVIDIA GB200 NVL72 introduces a fundamentally new way to build GPU clusters by extending NVIDIA NVLink coherence across an entire rack. This design enables...

Article Body:
Data Center / Cloud

 

 
 

 

 
English
中文

 

 

 
Achieving Peak System and Workload Efficiency on NVIDIA GB200 NVL72 with Slurm Block Scheduling

 
 

 

 

 May 07, 2026
 

 

 By 
Felix Abecassis
, 
Vasileios Karakasis
, 
Bryan Nabong
 and 
Douglas Wightman
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
NVIDIA GB200 NVL72 extends NVLink coherent memory domains across an entire rack, enabling exascale GPU clusters with 72 Blackwell GPUs and delivering 130 TB/s aggregate bandwidth, but crossing domain boundaries causes sharp performance drops requiring new scheduling strategies.
The Slurm workload manager introduced the topology/block plugin and --segment argument to treat NVLink domains as rigid scheduling blocks, preventing job fragmentation across blocks and allowing precise control of node allocation according to application-specific NVLink locality requirements.
Advanced features in Slurm, including support for incomplete blocks, multiple topology plugins per cluster, and NVIDIA IMEX integration for driver-level GPU memory isolation, enable optimized rack-scale orchestration and maintain consistent high performance in NVIDIA GB200 NVL72 clusters.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

NVIDIA GB200 NVL72
 introduces a fundamentally new way to build GPU clusters by extending 
NVIDIA NVLink
 coherence across an entire rack. This design enables exascale performance, but it also changes the assumptions that many scheduling systems were built on.

As a result, “rack-scale locality” becomes a hard constraint. When workloads cross domain boundaries, performance drops sharply, and a scheduler that treats the network fabric as a best-effort tree topology will fragment allocations in ways that increase queue times and degrade application performance.

To address this, 
Slurm workload manager
 introduced the topology/block plugin and continues expanding its capabilities with segmented scheduling. The plugin enables administrators and users to express application-specific NVLink requirements as atomic blocks rather than loosely optimized allocations.

This post explains how 
NVIDIA GB200 NVL72
 architecture is unique, how Slurm block scheduling helps optimize placement and performance, and how to configure topology.yaml, 
--segment
, and related features so you can move from prototype clusters to production-grade rack-scale orchestration.

How is NVIDIA GB200 NVL72 architecture unique?

NVIDIA GB200 NVL72
 is an exascale computer in a single rack that represents a new paradigm in GPU cluster design. While previous generations of servers used 
NVIDIA NVLink
 within a single chassis, GB200 NVL72 extends this coherent memory domain across an entire rack: 72 
NVIDIA Blackwell
 GPUs spanning 18 compute trays, unified with fifth-generation NVLink.

 

 
Figure 1. The increasingly complex interconnects of GB200 NVL72 rack and NVLink topology require more advanced workload intelligence

All communications within the rack operate at NVLink speeds: NVIDIA GB200 NVL72 provides 1.8 TB/s bidirectional throughput per GPU, for a total of 130 TB/s aggregate bandwidth. Communication crossing domain boundaries faces a steep performance drop, typically 50 GB/s (400 Gb/s) through InfiniBand or Ethernet.

Operating GB200 NVL72 clusters at scale requires new workload scheduling algorithms to treat NVLink domains as hard boundaries for jobs. While these new algorithms are essential for efficient workload, they also require administrative awareness around system fragmentation. The topology/block Slurm plugin helps users and administrators with both of these.

How does block scheduling work in Slurm?

Slurm has long supported 
topology-aware job scheduling
: the topology/tree plugin has been the standard for large-scale clusters. It models the networking compute fabric as a hierarchical tree of switches and nodes. While the primary objective of topology/tree is to minimize the number of switches a job spans, it is a best-effort attempt. The job might end up being heavily fragmented across leaf switches in order to start sooner. 

For clusters with an InfiniBand fabric connecting all compute nodes, this trade-off makes sense. A job split across multiple leaf switches might run slightly slower than under one single leaf switch, but the tradeoff between start time and performance is generally considered acceptable.

The introduction of GB200 NVL72 and GB300 NVL72 required a new approach. From a joint effort between NVIDIA and SchedMD, the new topology/block plugin was introduced in the Slurm 23.11 release to support rack-scale architectures such as GB200 NVL72. 

 

 
Figure 2. Each multinode NVLink domain in the cluster is modeled as a block, which is a rigid scheduling unit

If a job submits an allocation request that fits within a single block (18 nodes or less), the nodes will always be allocated from one block and the job will not be fragmented.

 

 
Figure 3. Examples of job allocations (
-N12, -N8, -N32
) showing how nodes are assigned across blocks under default scheduling

With the default behavior of topology/block, a job requesting 16 nodes forces the scheduler to wait for a single multinode NVLink domain with 16 idle nodes. This can lead to increased job queueing times. In reality, the application might have NVLink connectivity requirements that are smaller than the full NVL72 domain. 

To enable users to communicate the topology requirements of their applications to the job scheduler, Slurm introduced the 
--segment
 argument for topology/block jobs. This acts as a knob that defines the atomic group of nodes that must be placed in the same block and helps balance scheduler efficiency against the actual hardware locality requirements of the application. 

By modifying this parameter, you can significantly ease scheduling constraints. For example, a job requesting 12 nodes but specifying 
--segment=4
 can be split across three separate blocks. This new job would not be able to run without 
--segment=4
, as there is no single block with 12 nodes available. 

 

 
Figure 4. Segmented allocation example (
-N12 --segment=4
) showing how jobs can be split across multiple blocks

How does Slurm block scheduling optimize performance?

An important subtlety that often surprises users is the fact that Slurm can assign multiple segments of the same job to the same block.

Using segments is essential for optimizing performance based on the specific locality requirements of the workload: 
Tensor Parallelism (TP)
 may require small, tight segments to keep latency-sensitive communication on the high-speed NVLink fabric, while 
Expert Parallelism (EP)
 may require larger segment sizes to enforce that all-to-all collective operations will always be performed within a single NVLink domain.

Using a large segment value such as 
--segment=16
 
is also a way to yield a balanced allocation of the nodes across blocks. Figure 4 shows 32 nodes split as 18 nodes on block 3 and 14 nodes on block 4. Using 
--segment=16
 instead would ensure exactly 16 nodes on each block, as shown in Figure 5.

 

 
Figure 5. Balanced allocation example (
-N32 --segment=16
) showing even distribution of nodes across blocks

The command-line arguments 
--consolidate-segments
 and 
--spread-segments
 introduced in Slurm 25.11 enable users to influence the placement of segments. 

How to configure Slurm block scheduling

For topology/block, our recommendation for Slurm administrators is to define one block for each GB200 NVL72 domain (18 nodes) in the cluster. For jobs smaller than 18 nodes and not specifying 
--segment
, Slurm will not fragment the allocation across block boundaries. Instead, it will keep the job queued until sufficient resources become available in the cluster. 

This guarantees that all the allocated nodes for this job will be able to communicate with NVLink, providing consistent performance regardless of the current state of the cluster. For jobs larger than 18 nodes and not specifying 
--segment
, Slurm will fit the allocation in the minimum amount of blocks required.

To configure topology/block it is recommended to rely on the file 
topology.yaml
, a feature introduced in Slurm 25.05. For example, to define two GB200 NVL72 domains use the following script:

---
- topology: gb200-nvl72
 cluster_default: true
 block:
 block_sizes:
 - 18
 blocks:
 - block: block01
 nodes: node[0001-0018]
 - block: block02
 nodes: node[0019-0036]

The Slurm topology/block plugin supports multiple levels of hierarchical grouping, where the first level would be the NVL72 domains, and the higher levels of blocks can reflect the physical reality of the compute fabric design such as the performance impact when crossing data center rows or data center halls. 

For a GB200 NVL72 cluster with a full 
fat-tree for the compute fabric
, it is recommended to use only a single level of Slurm blocks for the multinode NVLink domains, as the performance cliff for crossing leaf switches is not as steep as the performance cliff for crossing NVLink domains. The minimum schedulable unit is a single node (four GPUs).

The block topology created by Slurm can be verified with the following command:

$ scontrol show topology
BlockName=block01 BlockIndex=0 Nodes=node[0001-0018] BlockSize=18
BlockName=block02 BlockIndex=1 Nodes=node[0019-0036] BlockSize=18

To fully benefit from the new capability, and submit a job where the application could benefit from added topology requirements, cluster users want to submit jobs with a 
--segment
 argument that is now enabled at the cluster administration level. 
--segment=1
 should be used when NVLink is only needed across four GPUs (one node), as it allows for maximum placement flexibility for the scheduler. 

Using 
--segment=18
 
could be discouraged in favor of recommending 
--segment=16
. 
This provides more opportunities for Slurm to use blocks that have drained or downed nodes. Cluster administrators can also decide to switch from guidance to enforcement by rejecting jobs that do not meet cluster guidelines. This can be achieved using a simple 
cli_filter/lua
 script:

function slurm_cli_pre_submit(options, pack_offset)
 if options["segment"] == "18" then
 slurm.log_error("error: using --segment=18 is currently not allowed.")
 return slurm.ERROR
 end

 return slurm.SUCCESS
end

function slurm_cli_setup_defaults(options, early_pass)
 return slurm.SUCCESS
end

function slurm_cli_post_submit(offset, job_id, step_id)
 return slurm.SUCCESS
end

$ srun -N18 --segment=18 hostname
srun: error: lua: error: using --segment=18 is currently not allowed.
srun: error: cli_filter plugin terminated with error

How to configure NVIDIA IMEX

In addition to configuring block scheduling, it is beneficial to make sure 
NVIDIA IMEX
 service for NVLink networks is properly configured in Slurm for driver-level isolation between jobs running on the same multinode NVLink domain.

To enable GPU memory import and export across nodes within an NVLink domain, the NVIDIA IMEX service must be started on all compute nodes of the cluster. When the IMEX configuration file is static, the recommended approach is to simply start the 
nvidia-imex
 systemd service at boot time and keep the same instance of the service across all Slurm jobs. 

It is recommended to enable the switch/nvidia_imex plugin (introduced in Slurm 24.05) to allow Slurm to manage the allocation of an 
IMEX channel
 for each job. This provides driver-level isolation between jobs and prevents accidental interference. To enable the plugin, use the following single line in slurm.conf:

SwitchType=switch/nvidia_imex

With this approach, management of the IMEX service and channels does not require custom logic in the Slurm prolog and epilog scripts.

What are the topology/block advanced features?

After the initial release of the topology/block plugin, NVIDIA has been working closely with the Slurm community to introduce new features that provide more control over the behavior of the topology/block plugin.

Starting from Slurm 25.05, you can now declare incomplete blocks (blocks with fewer nodes than the defined block size) in the Slurm topology file. You can even declare a block with no nodes at all, as a placeholder. This is useful in the early stages of a cluster when all nodes in a domain are not yet online. Since Slurm 24.05 it is also possible to declare spare nodes in a domain: simply by listing more nodes than the defined block size.

The introduction of the topology.yaml file lifted one major constraint with the legacy approach: one can now use multiple topology plugins simultaneously on a Slurm cluster, and associate a different topology plugin for each Slurm partition. This feature is leveraged to define a way for cluster admins to bypass the topology/block plugin for troubleshooting purposes. This is achieved by defining a “flat” topology in topology.yaml:

- topology: gb200-flat
 cluster_default: false
 flat: true

Then associate this topology to an admin-only partition in slurm.conf:

PartitionName=admin-flat AllowAccounts=admin Default=NO Nodes=nodes[0001-0036] 
Hidden=YES Topology=gb200-flat

What is the impact of segment size on node availability?

To study the importance of setting 
--segmen
t appropriately, one can use a simplified mathematical model that demonstrates the impact of the segment size on the effective available cluster capacity for a given job. Administrators need to be aware of how segment size can affect node availability. 

 

 
Figure 6.
 
The impact on usable cluster capacity when a single very large job is using 
--segment
 as the unavailability rate λ
 
increases

You can also observe the impact of 
--segment=9
: the expected usable capacity degrades quickly as the node unavailability rate λ increases, since having only a single unavailable node means the domain can only contribute nine nodes for jobs using 
--segment=
9
. 
Whereas for 
--segment=16
, 
a domain will contribute 16 nodes as long as there are less than three unavailable nodes.

Get started optimizing your rack-scale architecture

Rack-scale architectures are the future of AI computing, and NVIDIA Blackwell GB200 NVL72 is the first iteration of this design as technology steers towards greater domain sizes. The software infrastructure needs to evolve to support this new paradigm. The Slurm topology/block plugin provides the foundation and the commitment to continue working with the Slurm community to make it easier to deploy, understand, optimize, and operate at scale.

Ready to optimize your rack-scale orchestration? Review the 
Slurm topology.yaml documentation
 and the 
NVIDIA MNNVL User Guide
 to start implementing block scheduling on your Blackwell clusters. To learn more, see 
Unlock Exascale Performance on NVIDIA GB200 NVL72 with Slurm Topology-Aware Job Scheduling
.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Center / Cloud
 | 
MLOps
 | 
Networking / Communications
 | 
HPC / Scientific Computing
 | 
Blackwell
 | 
DGX
 | 
GB200
 | 
NVLink
 | 
Intermediate Technical
 | 
Deep dive
 | 
featured
 | 
LLMs
 | 
Slurm
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Felix Abecassis
 

 

 
 Felix Abecassis is a Systems Software Engineer at NVIDIA working on making GPU applications easier to deploy and manage in data centers. He focuses on supporting GPU accelerated machine learning frameworks. He holds a MSc in Computer Science from the French school EPITA.
 
 
 

 

 View all posts by Felix Abecassis

 

 

 

 

 

 

 

 

 

 

 About Vasileios Karakasis
 

 

 
 Vasileios Karakasis is a senior systems software engineer at NVIDIA, specializing in systems performance and validation. He has developed software and tools for validating large HPC systems.
 
 
 

 

 View all posts by Vasileios Karakasis

 

 

 

 

 

 

 

 

 

 

 About Bryan Nabong
 

 

 
 Bryan Nabong is a technical program manager, data centers at NVIDIA with a background in microprocessor design and verification, and HPC systems.
 
 
 

 

 View all posts by Bryan Nabong

 

 

 

 

 

 

 

 

 

 

 About Douglas Wightman
 

 

 
 Douglas Wightman is a senior engineer at NVIDIA specializing in HPC scheduling, and Slurm in particular. He has spent his career developing system software for some of the largest systems on the planet.
 
 
 

 

 View all posts by Douglas Wightman

 

 

 

 

 

 

 

 

 

 

 
Comments
