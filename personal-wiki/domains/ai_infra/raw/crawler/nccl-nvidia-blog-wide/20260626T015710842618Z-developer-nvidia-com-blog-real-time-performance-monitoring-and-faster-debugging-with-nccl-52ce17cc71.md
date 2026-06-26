---
source_id: nccl-nvidia-blog-wide
title: Real-Time Performance Monitoring and Faster Debugging with NCCL Inspector and
  Prometheus
canonical_url: https://developer.nvidia.com/blog/real-time-performance-monitoring-and-faster-debugging-with-nccl-inspector-and-prometheus/
captured_at: '2026-06-26T01:57:10.842618+00:00'
content_hash: 52ce17cc71e62518831378bddbc9f4405c028f9a7a302f033df55c6b1f062c8e
---
# Real-Time Performance Monitoring and Faster Debugging with NCCL Inspector and Prometheus

URL: https://developer.nvidia.com/blog/real-time-performance-monitoring-and-faster-debugging-with-nccl-inspector-and-prometheus/

RSS Summary:
<img alt="Decorative image." class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2026/05/NVIDIA-NCCL-Inspector-Real-Time-Performance-Monitoring-768x432.png" style="display: block; margin-bottom: 5px; clear: both;" title="NVIDIA-NCCL-Inspector-Real-Time-Performance-Monitoring" width="768" />Distributed deep learning depends on fast, reliable GPU-to-GPU communication using the NVIDIA Collective Communication Library (NCCL). When training slows down,...

Article Body:
Networking / Communications

 

 
 

 

 
English
中文

 

 

 
Real-Time Performance Monitoring and Faster Debugging with NCCL Inspector and Prometheus

 
 

 

 

 May 07, 2026
 

 

 By 
Ava Arnaz
, 
Sirshak Das
, 
Jill Foster
, 
Daniel Kim
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

 
 

 
 

Distributed deep learning depends on fast, reliable GPU-to-GPU communication using the 
NVIDIA Collective Communication Library (NCCL)
. When training slows down, it becomes challenging to determine why and what to do next. A problem can span computation, communication, a specific rank, or underlying hardware. 

NVIDIA NCCL Inspector accelerates triaging by providing a lightweight and continuous report of NCCL communication performance. It tracks operation type, size, and bandwidth across every rank, and with this latest enhancement, can facilitate real-time analysis with minimal overhead.

It also helps determine the optimal training recipe. A 
previous post
 introduced NCCL Inspector offline mode. While fine-grained analysis remains the standard for deep-dive data, this post introduces real-time monitoring, a new feature. Live, time-series visualizations can now be powered directly within a user’s infrastructure dashboard by integrating NCCL Inspector with Prometheus Exporter.

NCCL Inspector deployment architecture

NCCL 2.30 introduces 
Prometheus Mode
, a major enhancement for real-time performance monitoring of NCCL in AI workloads. The NCCL Inspector works in two modes, shown in Figures 1 and 2. 

 

 
Figure 1. NCCL Inspector in JSON mode (default/offline mode)

The JSON mode operates in a data collection and data analysis phase. First, the data collection phase generates performance metrics from each rank and stores them individually in a JSON file, typically on shared storage. Then, the data analysis phase processes the data. This method is considered offline since the processing isn’t completed in real time. 

 

 
Figure 2. NCCL Inspector in real-time Prometheus mode 

This new feature integrates NCCL Inspector metrics with Prometheus, converting them into time-series data suitable for visualization in Grafana dashboards. Prometheus mode eliminates the large storage requirements previously necessary for JSON mode. This metric data is moved by the node exporter to Prometheus—a scalable, cloud-native platform. The NCCL job output file is designed to be overwritten continuously. Once the node exporter collects the metrics, they’re no longer needed on disk.

Experimental setup for Prometheus Mode

Setting up the NCCL Inspector Profiler plugin requires building the plugin and setting the following required environment variables:

NCCL_PROFILER_PLUGIN=/path/to/nccl/plugins/profiler/inspector/libnccl-profiler-inspector.so
NCCL_INSPECTOR_ENABLE=1
NCCL_INSPECTOR_DUMP_THREAD_INTERVAL_MICROSECONDS=3000000
NCCL_INSPECTOR_PROM_DUMP=1
NCCL_INSPECTOR_DUMP_DIR=/path/to/node/exporter/log/location

The dump thread interval and dump directory should be set and tuned according to the node exporter used. Once configured, NCCL Inspector starts the process and dumps collective performance into the 
NCCL_INSPECTOR_DUMP_DIR
. The Prometheus Node Exporter then sends the metrics to the Prometheus time-series database. Finally, these time-series metrics are rendered as dashboard graphs with Graphana.

When running the job, the metrics are saved to a file with the format:  
nccl_inspector_metrics_<uuid_of_the_gpu>.prom
The UUID of the GPU is included in the file name since CUDA device IDs can overlap in a multi-user environment.
 

The NCCL job output file is in the Prometheus exposition format. Each metric is labeled with context, including NCCL version, Slurm job ID, node, GPU, communicator name, number of nodes, number of ranks, and message size. The following is an example:

nccl_p2p_bus_bandwidth_gbs{version="v5.1",slurm_job_id="1670760",node="nvl72033-T01",gpu="GPU0",comm_name="unknown",n_nodes="1",nranks="64",p2p_operation="Send",message_size="1-2MB"} 19.1634
nccl_p2p_exec_time_microseconds{version="v5.1",slurm_job_id="1670760",node="nvl72033-T01",gpu="GPU0",comm_name="unknown",n_nodes="1",nranks="64",p2p_operation="Send",message_size="1-2MB"} 92.8984
nccl_p2p_bus_bandwidth_gbs{version="v5.1",slurm_job_id="1670760",node="nvl72033-T01",gpu="GPU0",comm_name="unknown",n_nodes="1",nranks="64",p2p_operation="Recv",message_size="1-2MB"} 19.2396
nccl_p2p_exec_time_microseconds{version="v5.1",slurm_job_id="1670760",node="nvl72033-T01",gpu="GPU0",comm_name="unknown",n_nodes="1",nranks="64",p2p_operation="Recv",message_size="1-2MB"} 92.5781

nccl_bus_bandwidth_gbs{version="v5.1",slurm_job_id="1670760",node="nvl72033-T01",gpu="GPU0",comm_name="unknown",n_nodes="4",nranks="32",collective="ReduceScatter",message_size="134-135MB",algo_proto="RING_SIMPLE"} 44.1181
nccl_collective_exec_time_microseconds{version="v5.1",slurm_job_id="1670760",node="nvl72033-T01",gpu="GPU0",comm_name="unknown",n_nodes="4",nranks="32",collective="ReduceScatter",message_size="134-135MB",algo_proto="RING_SIMPLE"} 104164

Once these metrics land in a Prometheus DB, the next step is rendering them in Grafana.

Time series-based Grafana dashboards

Figure 3 shows an example of how time series dashboards look using the Prometheus labels categorized into NVLink collective dashboards and mixed i.e., Network + NVLink collectives:

 

 
Figure 3. Grafana time-series dashboard showing NCCL AllGather bus bandwidth (GB/s) for NVIDIA NVLink-only communicators on a single node (n_nodes==1), observed over a 6-minute window

 

 
Figure 4. Grafana time-series dashboard showing NCCL AllGather bus bandwidth (GB/s) for combined network (IB/RoCE/EFA) and NVLink communicators in a multi-node setting (n_nodes==4), observed over a six-minute window

Use cases for NCCL inspector 

To demonstrate the triage workflow, these two use cases highlight how the dashboards accelerate root cause identification.

Live observability

Use live dashboards for finding the root cause of performance slowdowns in a long-running AI workload. Observing changes on dashboards and correlating job-level degradations with underlying NCCL or network-layer metrics enables targeted triage based on where the anomaly originates. The team ran a large LLM pre-training job to show this strategy. 

Timeline A: Normal workflow

Figure 5 shows the AllGather bus bandwidth for the mixed network + NVLink collectives in one of the experiments. The compute performance for this AI pretraining workload was 
~310 TFLOPs/GPU
.

 

 
Figure 5. Grafana time-series dashboard showing NCCL AllGather bus bandwidth (GB/s) for mixed network + NVLink communicators during a normal AI pretraining workflow on four nodes, corresponding to an observed compute performance of ~310 TFLOPs/GPU

Timeline B: Network-induced slowdown

After introducing artificial network constraints, AllGather BusBw for mixed network + NVLink collectives shows compute performance decreased to ~268 TFLOPs per GPU (~13% degradation vs. baseline).

This example shows that a real-time dashboard improves observability of collective performance across mixed transport communicators (network + NVLink), enabling faster root cause identification and reducing mean time to resolution.

 

 
Figure 6. Grafana time-series dashboard showing NCCL AllGather bus bandwidth (GB/s) for mixed network + NVLink communicators during Timeline B, a network-induced slowdown scenario

Performance attribution

Another use case is the NCCL Inspector, which helps analyze performance degradation over a specific time period. For example, in one experiment, the performance degrades temporarily as shown:

[2026-03-19 14:39:47.098640] -> throughput per GPU: ~314 TFLOP/s/GPU
[2026-03-19 14:40:48.696103] -> throughput per GPU: ~295 TFLOP/s/GPU
[2026-03-19 14:42:00.816450] -> throughput per GPU: ~289 TFLOP/s/GPU
[2026-03-19 14:44:02.304347] -> throughput per GPU: ~311 TFLOP/s/GPU

Next, the observed degradation is examined to determine whether it correlates with a network anomaly during this period.

 

 
Figure 7. Grafana time-series dashboard showing NCCL ReduceScatter bus bandwidth (GB/s) for NVLink-only communicators during a performance attribution investigation on 2026-03-1

 

 
Figure 8. Grafana time-series dashboard showing NCCL ReduceScatter bus bandwidth (GB/s) for mixed Network + NVLink communicators during the same performance attribution window on 2026-03-19

The dashboard shows performance degradation in mixed transport communication (network + NVLink-based collectives). This correlation indicates that the root cause is a disruption/congestion in the network. This enables drilling down into per-host and network counters to isolate where the slowdown occurred. 

Next steps for real-time observability

The introduction of NCCL Inspector with Prometheus integration is designed to enhance network observability for AI workload performance analysis. This powerful combination enables a more scientific approach to performance analysis. Users can debug and understand the real-time performance characteristics of a running workload, triage slowdowns, fine-tune parameters, and measure the resulting performance changes using detailed metrics.

Get started

Refer to the GitHub 
README.md
 to:

Build and deploy the NCCL Inspector plugin in Prometheus mode.

Configure the Prometheus exporter to expose metrics for your cluster/environment.

Use the 
Grafana template
 to setup the grafana dashboard.

Acknowledgments

We would also like to thank our NVIDIA colleagues Nikhithkumar Kotagari, Giuseppe Congi, and Nishank Chandawala, and Ziyang Jia from the University of California, Riverside, for valuable input and reviews during the design process.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Science
 | 
Developer Tools & Techniques
 | 
Networking / Communications
 | 
Healthcare & Life Sciences
 | 
NCCL
 | 
Intermediate Technical
 | 
Deep dive
 | 
Accelerated Computing Libraries
 | 
featured
 | 
NVL72
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Ava Arnaz
 

 

 
 Ava Arnaz is a senior solutions architect specializing in AI. With extensive experience spanning model development, MLOps, and enterprise-scale deployments across multiple industries, she's driven by solving the complex challenges that define the future of intelligent systems.
 
 
 

 

 View all posts by Ava Arnaz

 

 

 

 

 

 

 

 

 

 

 About Sirshak Das
 

 

 
 Sirshak Das is a senior software engineer at NVIDIA, working in the AI Data-Infra Optimization group, where he focuses on optimizing communication efficiency for large-scale AI workloads. Before joining NVIDIA, he held engineering roles at several organizations, including Microsoft, Arm, Indiana University, Cisco, and Verizon, where he worked on technologies spanning cloud networking, FPGA- and DPU-based SmartNICs, user-space TCP/IP stacks, and router and switch operating systems.
 
 
 

 

 View all posts by Sirshak Das

 

 

 

 

 

 

 

 

 

 

 About Jill Foster
 

 

 
 Jill Foster is a senior AI-HPC cluster engineer at NVIDIA, working in the Managed AI Research Superclusters group, where she focuses on increasing researcher productivity. Jill has previously held senior architectural roles at Oracle and AWS, where she specialized in optimizing GPU-accelerated clusters and automating infrastructure. From her early work in global weather analytics to her current focus on cluster efficiency, Jill is dedicated to bridging the gap between cutting-edge research and the scalable infrastructure that makes it possible.
 
 
 

 

 View all posts by Jill Foster

 

 

 

 

 

 

 

 

 

 

 About Daniel Kim
 

 

 
 Daniel Kim is a senior AI infrastructure engineer at NVIDIA on the Global Compute Infrastructure team. He focuses on optimizing observability to provide deep and reliable insights through metrics, logs, and traces across GPU clusters spanning multiple CSPs for faster detection, diagnosis, and resolution of issues. Before NVIDIA, he built and scaled cloud-native platforms at UiPath, Omnitracs (SmartDrive), and SAP, spanning Kubernetes controllers, GitOps architecture, CI/CD standardization, and production reliability across on-prem and cloud environments. He holds an MS in Computer Science from Georgia Tech and a BS from UC San Diego.
 
 
 

 

 View all posts by Daniel Kim

 

 

 

 

 

 

 

 

 

 

 About Pavel Shamis
 

 

 
 Pavel (Pasha) Shamis is a distinguished engineer at NVIDIA in the AI Data-Infra Optimization group where his primary focus lies in optimizing efficiency of the AI software and hardware stack. Before joining NVIDIA, Pasha served as a senior principal research engineer at Arm for six years, working on co-designing software and hardware building blocks for large-scale distributed systems.
 
 
 

 

 View all posts by Pavel Shamis

 

 

 

 

 

 

 

 

 

 

 About Gargi Prasad
 

 

 
 Gargi Prasad is the program lead for resilience at NVIDIA in DGX Cloud. Her main focus areas are AI infrastructure resilience and performance optimization. Prior to NVIDIA, Gargi worked at Meta in the Core Infra serving large scale distributed systems. She has expertise in Software/System Engineering and Architecture and has worked for 15+ years in the industry. Gargi has a master’s degree in Computer Science from Delft University of Technology with a specialization in Parallel & Distributed Systems.
 
 
 

 

 View all posts by Gargi Prasad

 

 

 

 

 

 

 

 

 

 

 
Comments
