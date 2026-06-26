---
source_id: nccl-technical-blog
title: Navigating Generative AI for Network Admins
canonical_url: https://developer.nvidia.com/blog/navigating-generative-ai-for-network-admins/
captured_at: '2026-06-26T01:57:04.299877+00:00'
content_hash: 594fc9fadcd99fdbda5948cedcff46a4c59509502c10d6c32fbee5fdc4a52558
---
# Navigating Generative AI for Network Admins

URL: https://developer.nvidia.com/blog/navigating-generative-ai-for-network-admins/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2023/05/NVIDIA-DataCenter-Lifestyle-2023-7009-768x432.jpg" style="display: block; margin-bottom: 5px; clear: both;" title="NVIDIA-DataCenter-Lifestyle-2023-7009" width="768" />We all know that AI is changing the world. For network admins, AI can improve day-to-day operations in some amazing ways: Automation of repetitive tasks: This...

Article Body:
Networking / Communications

 

 
 

 

 
English
中文

 

 

 
Navigating Generative AI for Network Admins

 
 

 

 

 May 25, 2023
 

 

 By 
Amit Katz
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
AI is changing network administration by automating tasks such as monitoring, troubleshooting, and upgrades, improving network security, optimizing network topology, and enabling proactive network planning.
The NVIDIA Collective Communications Library (NCCL) is crucial for high-performance AI clusters, controlling traffic patterns and requiring optimized network design, monitoring tools, and Ethernet switches.
To guarantee AI cluster performance, following NVIDIA-published AI reference architectures and using infrastructure with AI-visibility features is recommended, as NVIDIA provides necessary tools, support, and training for AI networking success.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

We all know that AI is changing the world. For network admins, AI can improve day-to-day operations in some amazing ways:

Automation of repetitive tasks:
 This includes monitoring, troubleshooting, and upgrades, saving time while lowering the risk of human errors.

Network security:
 AI can help detect and respond to security threats in real time. For example, NVIDIA Morpheus enables cybersecurity developers to create optimized AI pipelines of real-time data.

Topology optimization:
 With the right telemetry, AI can analyze traffic patterns and suggest changes to optimize network performance.

Proactive network planning:
 AI can use that same advanced network telemetry to evaluate trends to predict potential issues and suggest changes to avoid the issues before they happen.

However, AI is no replacement for the know-how of an experienced network admin. AI is meant to augment your capabilities, like a virtual assistant. So, AI may become your best friend, but generative AI is also a new data center workload that brings a new paradigm shift: NVIDIA Collective Communications Library (NCCL).

The evolution of the data center

Network admins have had to deal with many other recent changes:

How to configure networks

How to monitor and manage networks

How to design networks

The protocols and workloads on networks

Not that long ago, we might have measured the value of a new network admin by the level of expertise in a particular networking command line interface (CLI). With the advent of hybrid cloud computing and DevOps, there is a growing move from CLIs to APIs. Skills in Ansible, SALT, and Python now have more value than a Cisco certification.

Even the way that you monitor and manage networks has changed. You’ve moved from tools that polled devices across the data center using SNMP and NetFlow to new switch-based telemetry models where the switches proactively stream flow-based diagnostic details.

You’re all practiced hands at introducing new workloads into data centers, many with unique networking requirements. You’ve seen legacy databases replaced with data analytics and big data clusters.

Now when tasked with building an AI cluster, it is tempting to think that AI is just a bigger and faster big data application. But AI is different
, 
and AI can be hard without the right tools.

The impact of generative AI and NCCL

You are a network admin for a large enterprise. Your CTO attended GTC 2023 and heard about generative AI. They want to change the way you do business by building a large language model like ChatGPT to respond and interact with end users. The model must be trained. This requires a large AI training cluster with many GPU-accelerated servers connected through a lightning-fast, high-speed network.

This AI training cluster brings many new challenges:

Network traffic patterns and flow characteristics change significantly in ways that don’t play well with traditional ECMP.

AI cluster reference designs require dedicated networks for compute/GPU, storage, and even in-band management.

Network traffic is heterogeneous and generated by CPU-to-CPU and GPU-to-GPU communications.

AI clusters must be ready to accommodate jobs running on one server, multiple servers, and even multiple jobs on one server, all concurrently.

Network configurations change, with parameters to optimize RoCE and GPU Direct communication.

AI jobs must have consistent and predictable job completion times over multiple iterations.

New flatter topologies with higher bandwidth switches.

New acronyms to learn: CUDA, NVIDIA DOCA, BERT, LLM, DLRM, and NCCL.

New monitoring tools: How do they know if AI and NCCL are performing well?

So, what is NCCL? Here’s the textbook answer:

The NVIDIA Collective Communication Library (NCCL) implements multi-GPU and multi-node communication primitives optimized for NVIDIA GPUs and Networking. NCCL provides routines such as all-gather, all-reduce, broadcast, reduce, and reduce-scatter, as well as point-to-point send and receive, that are optimized to achieve high bandwidth and low latency over PCIe and NVLink high-speed interconnects within a node and over the NVIDIA Mellanox Network across nodes. 

Source: 
NVIDIA Collective Communication Library (NCCL)

For the network admin, NCCL controls the traffic patterns of your shiny new AI cluster. This means that you need a network design that is optimized for NCCL, network monitoring tools optimized for NCCL, and Ethernet switches optimized for NCCL.

NCCL is the key to high performance, consistency, and predictability of the workloads running on the AI cluster. NCCL is also the intersection point: both the network admin and data scientist must speak it and understand it. And when both speak it fluently, NCCL can be the Rosetta Stone between these professionals with different and needed skill sets.

Given the importance of NCCL, the right network can make or break an AI cluster’s performance. AI clusters have some unique requirements:

Resilient to noise

Resilient to failures

Rail-optimized topology

Lossless network forwarding

Performance isolation

Non-blocking network architecture

So, what’s next?

It’s your job to keep the network from slowing the AI cluster, but what’s required for AI networking? High bandwidth, low latency, and high resiliency are necessary but not sufficient. How would you pick the right infrastructure?

Based on the datasheet? Not really.

Based on what the vendors tell you? A bit risky, as they want to sell you something.

Based on what the data scientists ask for? They are not networking experts, so most of them don’t know.

Based on what an experienced network admin recommends? There’s a high chance that they think in CPU, not GPU, and requirements have changed.

Networking for AI can be hard. The adage of “no one ever got fired for buying X” is about as dated as Moore’s law because the X factor for AI is different than general-purpose computing. Even large IT shops with dedicated AI engineering teams that pre-test cluster performance are frequently surprised when performance drops precipitously as more users are added and multiple jobs are run simultaneously.

The best way to guarantee the performance of an AI cluster is to follow one of the NVIDIA-published AI reference architectures and to use infrastructure that has the AI-visibility features to verify the health and feeding of your AI cluster. 

Whether your AI cluster uses Ethernet or InfiniBand, NVIDIA provides the tools, support, and training that you need for succeeding and becoming an expert at networking for AI.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Center / Cloud
 | 
Networking / Communications
 | 
Cloud Services
 | 
Telecommunications
 | 
Morpheus
 | 
NCCL
 | 
Business / Executive
 | 
Deep dive
 | 
Ethernet
 | 
featured
 | 
InfiniBand
 | 
Infrastructure
 | 
News
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Amit Katz
 

 

 
 Amit Katz is vice president of Ethernet Switch at NVIDIA. He has served as senior director of worldwide Ethernet switch sales since 2014, and previously worked in various product management roles at Mellanox beginning in 2011. Prior to that, Amit held various product management positions at Voltaire and at RAD Data Communications. He graduated from the Academic College of Tel Aviv-Yaffo with a BA in computer science and an MBA from Bar Ilan University.
 
 
 

 

 View all posts by Amit Katz

 

 

 

 

 

 

 

 

 

 

 
Comments
