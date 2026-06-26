---
source_id: nccl-lambda-blog
title: How Kodiak trains the brain behind 28 driverless trucks
canonical_url: https://lambda.ai/blog/how-kodiak-trains-the-brain-behind-28-driverless-trucks
captured_at: '2026-06-26T01:57:17.263838+00:00'
content_hash: 4ca5accfea25f9ce6d22e6c8d0b48a39f8e2c5f5c2b970afe07d67e49bb79b37
---
# How Kodiak trains the brain behind 28 driverless trucks

URL: https://lambda.ai/blog/how-kodiak-trains-the-brain-behind-28-driverless-trucks

RSS Summary:
<div class="hs-featured-image-wrapper"> 
 <a class="hs-featured-image-link" href="https://lambda.ai/blog/how-kodiak-trains-the-brain-behind-28-driverless-trucks" title=""> <img alt="How Kodiak trains the brain behind 28 driverless trucks" class="hs-featured-image" src="https://lambda.ai/hubfs/lambda_blog-image_kodiak_1600x860-1.png" style="width: auto !important; float: left; margin: 0 15px 15px 0;" /> </a> 
</div> 
<p><span>Twenty-eight trucks, and no humans in the cab. As of </span><span>March 31, 2026</span><span>, Kodiak's autonomous driving system, the Kodiak Driver, runs commercial freight on public roads across long-haul trucking, and industrial applications. This is the forefront of ground autonomy. </span><span>At every mile, Kodiak’s core value proposition rests in setting new standards for safe and reliable freight hauling that reshape the road ahead.</span></p> 
<p><span>The system behind it is GigaFusionNet, powering their autonomous driving system. Autonomous driving at the level above human competency and safety demands a paradigm shift in how we build AI. GigaFusionNet is a large-scale neural network architecture meticulously designed to learn a comprehensive, unified understanding of the physical world and the complex dynamics inherent to driving. This singular, powerful model ingests and processes multimodal sensor data from cameras, LiDAR, and radar to construct a holistic representation of the driving environment. This rich representation then serves as the bedrock for all subsequent critical tasks, ranging from 3D bounding boxes and 3D scene understanding to end-to-end driving token prediction.</span></p> 
<p><span>Training large-scale Physical AI foundation models like GigaFusionNet requires tightly integrated accelerated computing infrastructure optimized for multimodal AI, distributed training, and high-throughput data movement.</span></p> 
<p><span><br /></span></p>

Article Body:
June 3, 2026

 
• 10 min read

 

 
 

 

 

 

 
Twenty-eight trucks, and no humans in the cab. As of 
March 31, 2026
, Kodiak's autonomous driving system, the Kodiak Driver, runs commercial freight on public roads across long-haul trucking, and industrial applications. This is the forefront of ground autonomy. 
At every mile, Kodiak’s core value proposition rests in setting new standards for safe and reliable freight hauling that reshape the road ahead.

The system behind it is GigaFusionNet, powering their autonomous driving system. Autonomous driving at the level above human competency and safety demands a paradigm shift in how we build AI. GigaFusionNet is a large-scale neural network architecture meticulously designed to learn a comprehensive, unified understanding of the physical world and the complex dynamics inherent to driving. This singular, powerful model ingests and processes multimodal sensor data from cameras, LiDAR, and radar to construct a holistic representation of the driving environment. This rich representation then serves as the bedrock for all subsequent critical tasks, ranging from 3D bounding boxes and 3D scene understanding to end-to-end driving token prediction.

Training large-scale Physical AI foundation models like GigaFusionNet requires tightly integrated accelerated computing infrastructure optimized for multimodal AI, distributed training, and high-throughput data movement.

Building the brain: the training problem

Creating a neural network capable of safely and competently navigating the real world is a monumental engineering challenge. It requires a model that internalizes the 
physics of the world:
 how objects move, interact, and behave under an infinite variety of conditions. GigaFusionNet's shared backbone needs to reason across three sensor modalities simultaneously. To extract this profound knowledge from the millions of autonomous miles logged by Kodiak's fleet, we employ a sophisticated, multi-stage AI training pipeline. 

1. Data curation: maximizing learning efficiency

The initial and arguably most critical step is intelligent 
data curation
. Not random sampling. Instead, Kodiak maximizes the 
entropy
 of the training data by actively seeking out and prioritizing samples that represent rare, challenging, or edge-case scenarios. This improves the model's generalization capabilities, prevents overfitting to common situations, and ensures maximum learning efficiency from available compute resources. Smart data curation is the key to scaling the model’s competency.

2. Pre-training a large-scale GigaFusionNet

The foundation of the entire system is laid during the pre-training phase. This necessitates a neural network 
architecture
 that can be effortlessly scaled up or down based on available compute resources. GigaFusionNet pre-trains on an enormous 
unlabeled dataset
 using a 
self-supervised or weakly supervised objective function
.

The objective function, which is a form of next-token prediction (or its equivalent in the multimodal, spatiotemporal domain), may force the AI to learn deep, general concepts about the physical world. These could include spatial relationships, temporal coherence, object permanence, and interaction dynamics, all learned without explicit, costly human labels. This pre-training process builds a robust, generic world knowledge base that is transferable across diverse driving scenarios.

3. Leveraging and specializing the knowledge base

The pre-trained model has acquired this fundamental understanding of the world, and is specialized for various specific autonomous driving tasks. The common, powerful foundation acquired during pre-training rapidly accelerates learning across all downstream applications, which include:

3D bounding box detection
 for accurate object localization.

3D surface understanding
 for modeling drivable space and road geometry.

World segmentation
 for a fine-grained understanding of all scene elements.

End-to-end driving VLA (Vision-Language Action) 
model
 
that directly maps sensor inputs to control commands.

4. Supervised Fine Tuning (SFT) for model alignment

Supervised Fine Tuning (SFT)
 is the final, critical step in model alignment. It involves training the pre-trained model on a smaller but extremely 
high-quality, human-labeled dataset
. It is essential to correct any unintended biases or subtle inaccuracies the model would have learned during the massive-scale pre-training phase. SFT solidifies critical safety behaviors and refines the model's output to meet the rigorous performance and safety standards required for commercial deployment.

"Creating the Kodiak Brain is a monumental engineering challenge that requires the model to internalize the physics of the world."
 
— Shubham Shrivastava, Head of AI, Kodiak

Training infrastructure: the Kodiak-Lambda partnership

Autonomous driving represents one of the most demanding Physical AI workloads, requiring massive-scale training infrastructure capable of processing multimodal sensor data and learning real-world spatiotemporal dynamics.

Training GigaFusionNet required a shared backbone reasoning simultaneously across cameras, LiDAR, and radar. This needed high GPU memory, high inter-node bandwidth, and sustained data throughput, all at once. When Kodiak's on-prem hardware hit its ceiling, the team needed to scale fast without moving petabytes of sensor data.

Hyperscalers were not the answer either. GPU nodes were geographically separated from Kodiak's data, resulting in slow data transport and training. The networking, built for general-purpose workloads, couldn't deliver the inter-node throughput required for distributed training. There was months of wait time to get the cluster, which is not feasible when iteration speed is a competitive variable.

Kodiak's partnership with 
Lambda
 provides NVIDIA HGX H100 accelerated computing infrastructure optimized for large-scale AI training, high-bandwidth GPU communication, and distributed multimodal model deployment, as training this model requires large GPU nodes working in parallel to handle the massive input data and model parameters. The NVIDIA Hopper architecture enabled efficient scaling through high-bandwidth HBM memory, Transformer Engine acceleration, and fast GPU-to-GPU communication via NVIDIA NVlink and InfiniBand networking.

Fast interconnects

Maintaining training efficiency requires high node-to-node throughput, which is facilitated by NVIDIA NVLink and high-speed NVIDIA networking technologies critical for distributed multimodal workloads. This allows for the quick exchange of gradients across the distributed cluster, alongside high data bandwidth and low-latency storage, to feed vast multimodal sensor data to the GPUs at a high, sustained rate, preventing I/O from becoming a bottleneck. Lambda's NVIDIA HGX H100 clusters connected via 
NVIDIA Quantum InfiniBand
 deliver the node-to-node throughput that GigaFusionNet's shared backbone requires, keeping the cluster training rather than waiting.

Data pipelines

A fast compute cluster starved of data is still a bottleneck. GigaFusionNet ingests multimodal sensor data, cameras, LiDAR, and radar, at volumes that can overwhelm conventional storage architectures. Lambda's S3 adapter lets Kodiak stream hundreds of terabytes of sensor data at the latency required by their training workload, keeping GPUs fed without diverting engineering attention to plumbing.

Co-engineering support

Distributed training at this scale breaks in unpredictable ways. A direct line to Lambda's team across real-time channels meant issues got resolved fast before they compounded into lost training cycles.

Kodiak was pre-training GigaFusionNet within a week and running twice as many experiments at twice the speed.

The autolabeling flywheel

The true power and longevity of Kodiak’s system are derived from its 
AI Flywheel,
 a self-reinforcing loop that drives continuous, autonomous improvement. This cycle is fundamentally enabled by 
autolabeling
.
 

 Autolabeling
 allows Kodiak to fully leverage the depth of millions of miles of autonomous driving data. Since manually labeling such a colossal volume of data is prohibitively expensive and slow, autolabeling provides a scalable, efficient solution for generating vast quantities of high-quality supervision data.

When smart 
data curation
 is paired with high-fidelity 
autolabeling
, it ensures the system not only has a large volume of data but also maximizes 
variation and distribution coverage
. This sophisticated process uses automated techniques to find various types of scenarios in the dataset, intelligently resampling them to "bubble up" the 
least representative data
. This iteratively improves the overall training distribution, constantly exposing the model to new challenges.

A key innovation is the ability to leverage future frames in the autolabeling process. This allows the model to learn from object trajectories and scene evolution, not just forward in time, but also backward in time. This enables a 
Teacher-Student regime
 of training GigaFusionNet. In this setup, a powerful, often less efficient "Teacher" model processes rich, spatiotemporal data to generate high-quality autolabels. These superior autolabels are then used to train a much more efficient "Student" model. This technique extracts the maximum amount of actionable information from every mile driven in the real world.

The consequence of this flywheel is that the majority of Kodiak’s models are primarily trained with autolabels today. While this ensures models constantly improve during real-world operation, a potential risk exists: the failure modes of current models might get exacerbated with reinforcement through the autolabeling feedback loop. This is precisely why the small, targeted amount of human-labeled data remains invaluable. It provides the critical external supervision necessary to correct and mitigate these potential cascading errors, ensuring the model's safety profile remains rigorous.

"The AI Flywheel is a self-reinforcing loop where autolabeling drives continuous, autonomous improvement across millions of miles." — Shubham Shrivastava, Head of AI, Kodiak

Kodiak brain: generalization across platforms and ODDs

The unified training methodology, combining large-scale autolabeled data with supervised fine-tuning yields a highly generalized
 
AI. This powerful knowledge base is architected to perform robustly across various Operational Design Domains (ODDs), such as highway, surface street, and off-road driving, under specific weather conditions and across different platforms, including various truck types and sensor configurations.

This generalized knowledge is then leveraged to train the final 
end-to-end driving VLA (Vision Language Action) model
. This VLA model can reason about the world and is conditioned on:

Spatiotemporal multimodal features
 derived from GigaFusionNet’s world model.

Ego history
 represents the vehicle's past movements and states.

Intent tokens
 to encode high-level goals or strategic decisions.

This conditioning allows the VLA model to reason about 
how to drive
 strategically and safely in complex, dynamic, and varied scenarios.

"The end-to-end driving VLA model conditions on world knowledge, ego history, and intent to reason about strategic and safe driving." 
— Shubham Shrivastava, Head of AI, Kodiak

From cloud to cab: distillation onto the 
NVIDIA DRIVE Hyperion platform

To achieve large-scale, commercial deployment, the immense power of these foundation models must be made computationally efficient for in-vehicle operation. Kodiak has partnered with NVIDIA to scale its driverless vehicle efforts using the 
NVIDIA DRIVE Hyperion architecture
.

"Kodiak's partnership with NVIDIA and the DRIVE Hyperion architecture is essential for achieving computationally efficient, in-vehicle operation and commercial deployment." — Shubham Shrivastava, Head of AI, Kodiak

Harnessing the immense power of large foundation models that encode a deep understanding of the physical world on the state-of-the-art 
NVIDIA AGX Thor X
 computing platform requires 
model distillation
. This technique involves distilling the complex, extensive 
world understanding
 from the large, resource-intensive "Teacher" GigaFusionNet model onto a much smaller, and more resource-efficient "Student" model. The ultimate goal is to create a student model that performs as well as the teacher model but with significantly lower latency and computational cost, making it viable for real-time operation in the vehicle.

The Kodiak-Lambda partnership accelerates this distillation process. Faster training iterations on Lambda clusters mean faster distillation cycles, which means faster deployment of improved models into the fleet at massive, commercial scale.

What's next

Twenty-eight driverless trucks on the road today. A foundation model that improves with every mile. A training pipeline that scales on Lambda's GPU infrastructure.

Kodiak's goal: autonomous driving at a level above human competency and safety. The Kodiak Driver gets closer with every training run.

Read more about 
Lambda's GPU clusters
 
 for autonomous vehicle training.

Written in collaboration with 
Shubham Shrivastava
, Head of AI, Kodiak.
