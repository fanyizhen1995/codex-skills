---
source_id: nccl-technical-blog
title: Enhancing Communication Observability of AI Workloads with NCCL Inspector
canonical_url: https://developer.nvidia.com/blog/enhancing-communication-observability-of-ai-workloads-with-nccl-inspector/
captured_at: '2026-07-05T04:11:16.696530+00:00'
content_hash: 436a69980320501863030eb86ef4efc09b21c5931e52a6e419b38de4d01127c8
---
# Enhancing Communication Observability of AI Workloads with NCCL Inspector

URL: https://developer.nvidia.com/blog/enhancing-communication-observability-of-ai-workloads-with-nccl-inspector/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2025/12/computing-performance-analysis-768x432-png.webp" style="display: block; margin-bottom: 5px; clear: both;" title="computing-performance-analysis" width="768" />When using the NVIDIA Collective Communication Library (NCCL) to run a deep learning training or inference workload that uses collective operations (such as...

Article Body:
Networking / Communications

 

 
 

 

 
English
한국어
中文

 

 

 
Enhancing Communication Observability of AI Workloads with NCCL Inspector

 
 

 

 

 Dec 10, 2025
 

 

 By 
Sirshak Das
, 
Jason Sewall
, 
Giuseppe Congiu
, 
Pavel Shamis
 and 
Gargi Prasad
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
NCCL Inspector Profiler Plugin provides granular, low-overhead, always-on observability for distributed deep learning workloads, with per-communicator, per-collective performance and metadata logging, integrating via the plugin interface introduced in NCCL 2.23 for seamless adoption in production environments.
Performance monitoring and analysis include direct measurement of algorithmic bandwidth, bus bandwidth, execution time, message sizes, and collective types, collected at the granularity of every communicator and rank, with configurable data output intervals, and verbose event tracing capabilities for kernel-level performance profiling.
The Performance Summary Exporter and dashboard integration enable ingestion of diverse output formats (log, JSONL, compressed), transformation to Parquet for efficient analytics, and generation of detailed visualizations and statistical summaries, supporting differentiation of collective communication patterns (e.g., NVLink vs. HCA), and facilitating root-cause analysis, optimization, and continuous monitoring at scale for frameworks leveraging NVIDIA NCCL.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

When using the 
NVIDIA Collective Communication Library (NCCL)
 to run a deep learning training or inference workload that uses collective operations (such as AllReduce, AllGather, and ReduceScatter), it can be challenging to determine how NCCL is performing during the actual workload run.

This post introduces the 
NCCL Inspector Profiler Plugin
, which addresses this problem. It offers a way for comprehensive, low-overhead always-on performance observability for distributed deep learning training and inference workloads. 

What is NCCL Inspector?

NCCL Inspector is a profiling and analysis tool that provides detailed, per-communicator, per-collective performance and metadata logging. This tool features two main steps: data collection and data analysis.

NCCL Inspector can help answer questions on a variety of topics, including: 

Intra-job collective performance comparison:
 How are AllReduce, AllGather, ReduceScatter, and other collectives performing in the Data Parallel domain compared to the Tensor Parallel domain?

Inter-job collective performance comparison:
 Did the congestion in the network yesterday cause collectives to perform poorly? Was it the reason for the decrease in compute performance?

Compute-network performance correlation:
 If there is an overall dip in compute performance (TFLOPs), was the network performance dip the cause?

The NCCL Inspector logs the collective bandwidth and duration of every rank in the communicator to disk at regular intervals. After the job has completed, this performance data is analyzed and correlated over the lifetime of the job. The performance of the NCCL collectives are then characterized during the lifetime of the multi-GPU job.

As a critical component for multi-GPU and multi-node communication, every framework using NCCL can benefit from the detailed observability provided by NCCL Inspector.

NCCL Inspector leverages the plugin interface introduced in NCCL 2.23 to enable always-on observability for production workloads, while minimizing performance overheads.

During the data collection step, the NCCL Inspector library instructs NCCL about the specific collective events it should emit. Users can load the library (for example, DL frameworks) through the 
NCCL_PROFILER_PLUGIN
 environment variable. Then, NCCL Inspector listens to the subscribed events emitted by NCCL and generates structured JSON output for each of them, enabling deep insights into performance characteristics of NCCL collectives. 

Post-job completion analysis and visualization are generated and executed through example Python scripts provided in the NCCL repo. This JSON output is later fed into analysis scripts and various observability platforms to give insight into the performance of NCCL during a production workload run.

Key features of NCCL Inspector

Some of the key standout features of NCCL Inspector that make it useful include:

Per-communicator tracking
: NCCL Inspector maintains separate tracking for each NCCL communicator. This is particularly valuable in complex distributed applications like AI workloads where multiple communicators may be used for different purposes like parallelism domains.

Always-on low overhead
: NCCL Inspector low-overhead performance tracking means it can be enabled in production workloads, providing “always-on” continuous observability of NCCL performance without significant performance degradation.

Performance metrics
: NCCL Inspector calculates and reports key performance metrics including:

Algorithmic bandwidth

Bus bandwidth

Execution time in microseconds

Message sizes and collective types

Network technology agnostic: 
NCCL Inspector leverages the plugin interface to integrate with NCCL. It is agnostic to various network technologies supported by NCCL (RoCE, IB, EFA, and so on).

Data collection phase

For the data collection
 
phase, NCCL Inspector is initialized through several environment variables.

Required variables:

NCCL_PROFILER_PLUGIN
: Path to the plugin library binary.

NCCL_INSPECTOR_ENABLE=1

NCCL_INSPECTOR_DUMP_THREAD_INTERVAL_MICROSECONDS
: Sets the interval for output writing

Optional variables:

NCCL_INSPECTOR_DUMP_DIR
: Output directory for logs

NCCL_INSPECTOR_DUMP_VERBOSE(Optional)
: Enables verbose output with event trace information

Example use (SLURM)

To enable NCCL Inspector and start the data collection phase, insert the following setting of environment variables to the SBATCH script in SLURM: 

export NCCL_PROFILER_PLUGIN=/path/to/nccl/ext-profiler/inspector/libnccl-profiler-inspector.so
export NCCL_INSPECTOR_ENABLE=1
export NCCL_INSPECTOR_DUMP_THREAD_INTERVAL_MICROSECONDS=500
export NCCL_INSPECTOR_DUMP_DIR=/path/to/logs/${SLURM_JOB_ID}/

srun your_nccl_application

Example output format

{
 "header": {
 "id": "0x7f8c496ae9f661", // communicator id
 "rank": 2,
 "n_ranks": 8,
 "nnodes": 1
 },
 "metadata": {
 "inspector_output_format_version": "v4.0",
 "git_rev": "",
 "rec_mechanism": "profiler_plugin",
 "dump_timestamp_us": 1748030377748202,
 "hostname": "hostname",
 "pid": 1639453
 },
 "coll_perf": {
 "coll": "AllReduce",
 "coll_sn": 1407,
 "coll_msg_size_bytes": 17179869184,
 "coll_exec_time_us": 61974,
 "coll_algobw_gbs": 277.210914,
 "coll_busbw_gbs": 485.119099
 }
}

Verbose output

When verbose mode is enabled with 
NCCL_INSPECTOR_DUMP_VERBOSE=1
, the output per kernel (SM) performance is as follows:

{
 "header": {
 "id": "0xe62dedaa97644a", //communicator info
 "rank": 4, // communicator id
 "n_ranks": 8,
 "nnodes": 1
 },
 "metadata": {
 "inspector_output_format_version": "v4.0",
 "git_rev": "9019a1912-dirty",
 "rec_mechanism": "nccl_profiler_interface",
 "dump_timestamp_us": 1752867229276385,
 "hostname": "hostname",
 "pid": 438776
 },
 "coll_perf": {
 "coll": "ReduceScatter",
 "coll_sn": 1231,
 "coll_msg_size_bytes": 2147483648,
 "coll_exec_time_us": 41057,
 "coll_timing_source": "kernel_gpu",
 "coll_algobw_gbs": 418.439467,
 "coll_busbw_gbs": 366.134533,
 "event_trace_sn": {
 "coll_start_sn": 1,
 "coll_stop_sn": 2,
 "kernel_events": [
 {
 "channel_id": 0,
 "kernel_start_sn": 3,
 "kernel_stop_sn": 48,
 "kernel_record_sn": 47
 }
 ]
 },
 "event_trace_ts": {
 "coll_start_ts": 1752867229235059,
 "coll_stop_ts": 1752867229235064,
 "kernel_events": [
 {
 "channel_id": 0,
 "kernel_start_ts": 1752867229235181,
 "kernel_stop_ts": 1752867229275811,
 "kernel_record_ts": 1752867229275811
 }
 ]
 }
 }
}

Data analysis phase

NCCL Inspector includes an example comprehensive performance analysis and visualization tool that processes log files and generates detailed performance reports. The Performance Summary Exporter tool provides rich visualizations and statistical analysis of collective communication performance.

Performance Summary Exporter 

This stand-alone Performance Summary Exporter is a Python-based analysis tool located in 
ext-profiler/inspector/exporter/example/
. This tool performs the following tasks:

Processes NCCL Inspector logs in multiple formats (
.log
, 
.log.gz
, 
.jsonl
, 
.jsonl.gz
)

Exports data to Parquet format for efficient processing

Generates statistical summaries for collective operations

Creates visualizations including scatter plots, histograms, and box plots

Classifies communication patterns

single-rank

nvlink-only

hca-only

mixed

Dashboard integration

The NVIDIA team has integrated this data from NCCL Inspector to dashboards, which can give per SLURM job overview of NCCL performance. 

 

 
Figure 1. Per-job collective performance integration with elastic dashboard

 

 
Figure 2. Per-collective type performance, for example performance of NVLink only collectives used for tensor parallelism

Use cases and applications

You can leverage NCCL Inspector for a range of applications and use cases, including performance analysis, research and development, and production monitoring.

Performance analysis

The Inspector enables detailed analysis of collective communication performance, helping identify bottlenecks and optimization opportunities in distributed training workloads.

Research and development

Researchers can use the detailed event traces and performance metrics to develop new communication patterns and algorithms.

Production monitoring

The always-on nature of the Inspector makes it suitable for continuous monitoring of production workloads, providing insights into communication performance over time.

Get started with NCCL Inspector

NCCL Inspector
 provides a powerful tool for understanding and optimizing collective communication performance in distributed training workloads. Its low-overhead design makes it suitable for production use, while its detailed event tracing and performance metrics enable deep analysis of communication patterns.

To get started and learn more about NCCL and related tools, visit the 
NVIDIA/nccl NCCL
 GitHub repo and explore the
 NVIDIA Magnum IO documentation
.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Center / Cloud
 | 
Developer Tools & Techniques
 | 
Networking / Communications
 | 
Cloud Services
 | 
Magnum IO
 | 
NCCL
 | 
Intermediate Technical
 | 
Tutorial
 | 
featured
 | 
Multi-GPU
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Sirshak Das
 

 

 
 Sirshak Das is a senior software engineer at NVIDIA, working in the AI Data-Infra Optimization group, where he focuses on optimizing communication efficiency for large-scale AI workloads. Before joining NVIDIA, he held engineering roles at several organizations, including Microsoft, Arm, Indiana University, Cisco, and Verizon, where he worked on technologies spanning cloud networking, FPGA- and DPU-based SmartNICs, user-space TCP/IP stacks, and router and switch operating systems.
 
 
 

 

 View all posts by Sirshak Das

 

 

 

 

 

 

 

 

 

 

 About Jason Sewall
 

 

 
 Jason Sewall is a principal software architect at NVIDIA, where he works on AI infrastructure, which includes performance tuning, failure diagnostics, and software stack improvements. Jason has a PhD and a master’s degree in Computer Science from the University of North Carolina, as well as bachelor’s degrees in Computer Science and Mathematics from the University of Maine. Jason has been at NVIDIA since 2022 after a long career at Intel. He lives in coastal Maine.
 
 
 

 

 View all posts by Jason Sewall

 

 

 

 

 

 

 

 

 

 

 About Giuseppe Congiu
 

 

 
 Giuseppe Congiu is a senior software engineer working on the NCCL team since January 2024. Before joining NVIDIA, he covered several positions, including research scientist at Innovating Computing Laboratory, postdoctoral fellow at Argonne National Laboratory, and software engineer at Seagate. In these positions, he worked on a range of exascale projects, including ExaPAPI, ExaMPI, and the EU-funded DEEP-ER project.
 
 
 

 

 View all posts by Giuseppe Congiu

 

 

 

 

 

 

 

 

 

 

 About Pavel Shamis
 

 

 
 Pavel (Pasha) Shamis is a distinguished engineer at NVIDIA in the AI Data-Infra Optimization group where his primary focus lies in optimizing efficiency of the AI software and hardware stack. Before joining NVIDIA, Pasha served as a senior principal research engineer at Arm for six years, working on co-designing software and hardware building blocks for large-scale distributed systems.
 
 
 

 

 View all posts by Pavel Shamis

 

 

 

 

 

 

 

 

 

 

 About Gargi Prasad
 

 

 
 Gargi Prasad is the program lead for resilience at NVIDIA in DGX Cloud. Her main focus areas are AI infrastructure resilience and performance optimization. Prior to NVIDIA, Gargi worked at Meta in the Core Infra serving large scale distributed systems. She has expertise in Software/System Engineering and Architecture and has worked for 15+ years in the industry. Gargi has a master’s degree in Computer Science from Delft University of Technology with a specialization in Parallel & Distributed Systems.
 
 
 

 

 View all posts by Gargi Prasad

 

 

 

 

 

 

 

 

 

 

 
Comments
