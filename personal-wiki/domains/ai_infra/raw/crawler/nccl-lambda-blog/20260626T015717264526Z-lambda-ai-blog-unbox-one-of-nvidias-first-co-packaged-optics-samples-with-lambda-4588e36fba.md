---
source_id: nccl-lambda-blog
title: Unbox one of NVIDIA's first co-packaged optics switches with us. See why we
  bet on CPO early.
canonical_url: https://lambda.ai/blog/unbox-one-of-nvidias-first-co-packaged-optics-samples-with-lambda
captured_at: '2026-06-26T01:57:17.264526+00:00'
content_hash: 4588e36fba3da66efea1ba332bd599c226644fcd64cf3ee533dcb286d2abc5fd
---
# Unbox one of NVIDIA's first co-packaged optics switches with us. See why we bet on CPO early.

URL: https://lambda.ai/blog/unbox-one-of-nvidias-first-co-packaged-optics-samples-with-lambda

RSS Summary:
<div class="hs-featured-image-wrapper"> 
 <a class="hs-featured-image-link" href="https://lambda.ai/blog/unbox-one-of-nvidias-first-co-packaged-optics-samples-with-lambda" title=""> <img alt="Unbox one of NVIDIA's first co-packaged optics switches with us. See why we bet on CPO early." class="hs-featured-image" src="https://lambda.ai/hubfs/lambda_blog-image_first-look-CPO_1600x860.png" style="width: auto !important; float: left; margin: 0 15px 15px 0;" /> </a> 
</div> 
<p>When we design large GPU clusters, the network is no longer a background system. It's part of the compute envelope. At the 800G and NVIDIA GB300 NVL72 scale, the back-end fabric <a href="https://developer.nvidia.com/blog/scaling-ai-factories-with-co-packaged-optics-for-better-power-efficiency/"><span>accounts for 86% of networking power</span></a> in a three-layer cluster.</p> 
<p>This matters even more as we shift towards agentic workloads. A single request can fan out across multiple model calls, tool calls, retrieval steps, and reasoning passes. That creates more east-west traffic inside the cluster and puts the network closer to the critical path of token generation. If GPUs are waiting on data or recovering from failures, token throughput drops.</p> 
<p>Lambda is taking an early look at co-packaged optics, starting with the NVIDIA Quantum-X InfiniBand Photonics Q3450-LD switch. In this post, you'll learn what the hardware is, what changes operationally, insights from the unboxing, and why this architecture fits large NVIDIA GB300 NVL72 clusters.</p>

Article Body:
June 1, 2026

 
• 6 min read

 

 
 

 

 

 

 
When we design large GPU clusters, the network is no longer a background system. It's part of the compute envelope. At the 800G and NVIDIA GB300 NVL72 scale, the back-end fabric 
accounts for 86% of networking power
 in a three-layer cluster.

This matters even more as we shift towards agentic workloads. A single request can fan out across multiple model calls, tool calls, retrieval steps, and reasoning passes. That creates more east-west traffic inside the cluster and puts the network closer to the critical path of token generation. If GPUs are waiting on data or recovering from failures, token throughput drops.

Lambda is taking an early look at co-packaged optics, starting with the NVIDIA Quantum-X InfiniBand Photonics Q3450-LD switch. In this post, you'll learn what the hardware is, what changes operationally, insights from the unboxing, and why this architecture fits large NVIDIA GB300 NVL72 clusters.

 

 

 

 

 

 

 

But before we dive into it...

Why we made this bet

The decision came down to power, reliability, and timing.

Power.
 CPO reduces the power consumed by the switching layer. The practical result is more headroom for GPUs inside the same facility envelope.

GB300 NVL72 cluster size

CPO switches

Network power freed

Power-equivalent extra GPUs

576 GPUs

12

37 kW

+26 GPUs

4,608 GPUs

100

305 kW

+217 GPUs

10,368 GPUs

216

658 kW

+470 GPUs

41,472 GPUs

1,440

4392 kW

+3137 GPUs

NVIDIA Photonics CPO switch: 3.95 kW. Standard switch: 7.0 kW. 3.05 kW savings per switch. NVIDIA Blackwell Ultra GPU TDP: 1,400 W.

Rack layout, cooling distribution, cluster design, hardware, and power distribution determine how many of those watts become GPUs. CPO doesn’t automatically add to the number of deployable GPUs, but it’s the right mental model for infrastructure planning. When the network uses less power, the same footprint can support more useful compute and more tokens per watt.

Reliability.
 A 128,000-GPU data center using traditional pluggable transceivers requires roughly 655,000 discrete transceiver modules across the switching fabric. Each one is a potential failure point. CPO removes that component class entirely, dramatically reducing active optical components in the fabric.

For training jobs that can checkpoint and resume, a network interruption is an inconvenience. For agentic workloads, where long-running chains of work can’t easily resume mid-task, network instability directly impacts job completion and throughput. Fewer failure points means more continuous GPU time and fewer idle accelerators.

Timing.
 Engineering samples are a chance to work through rack design, cooling, power delivery, fiber routing, and the installation process with the vendor while the product is still becoming real. Early access means solving those problems before production, not during it.

The hardware: NVIDIA Quantum-X Photonics Q3450-LD

Front panel of the NVIDIA Quantum-X Photonics Q3450-LD. Fiber-array connections replace traditional OSFP transceiver cages. 18 removable light-source modules feed 144 MPO ports.

The front panel is the most visible difference from any other engineering sample switching rack today. Whereas a traditional switch has rows of OSFP cages, the Q3450-LD has fiber-array connections that feed directly into the silicon photonics engines on the switch package. The switch supports 18 removable external light-source modules, each feeding eight MPO ports. Lasers stay external because they need to remain field-serviceable. Everything else in the optical path is inside the sealed package.

Rear panel: 48V DC busbar power input and UDQ4 liquid cooling quick disconnects. Same infrastructure model as NVIDIA GB300 NVL72 racks.

The rear makes the infrastructure shift visible. Power enters via 48V DC DGX-compliant busbar connectors. Cooling runs through four UDQ4 liquid cooling connections with dual internal loops. If you’ve already deployed GB300 NVL72 racks, the infrastructure model is familiar. The switch is part of the same liquid-cooled, busbar-powered layer. More planning discipline up front. Less power is wasted on the network over time.

The Q3450-LD installed in a rack-scale deployment. 4U form factor, liquid-cooled, 115.2 Tb/s non-blocking switching capacity.

Spec

Detail

Form factor

4U

ASIC

NVIDIA Quantum-X800

Ports

144 x 800G InfiniBand

Optical connectivity

144 MPO connectors

Switching capacity

115.2 Tb/s non-blocking

Power input

48V DC busbar

Cooling

Liquid, dual loop

Light source

18 removable external modules (one per eight ports)

What changes operationally

In a traditional switch, the optical module is mounted on the faceplate. The switch ASIC sends electrical signals across the board to pluggable transceivers, which convert those signals into light. A digital signal processor inside each transceiver compensates for signal degradation accumulated across that path.

Co-packaged optics moves that conversion next to the switch ASIC. The electrical path is measured in micrometers instead of centimeters. Signal loss drops from roughly 20dB to 4dB. The DSP is no longer needed, which removes both its power draw and its latency contribution from every hop in the fabric.

The physical change is the point. CPO also changes how the switch is installed and serviced. More integration means cooling, fiber management, and installation require more upfront planning than a pluggable transceiver switch.

What we learned installing it

Engineering samples are where the clean architecture diagram meets the real rack.

The work goes beyond powering on the switch. It’s proving that the whole operating model works: rack fit, busbar alignment, liquid-cooling connections, pressure checks, fiber routing, and the installation procedure end-to-end. Lambda and NVIDIA worked together on rack design, power delivery, cooling, and fiber termination. When first-of-kind hardware surfaces unexpected requirements during installation, both teams work through them in the room.

Being early means access to the lessons: how the switch fits, how it’s cooled, how fiber should be managed, what the installation procedure actually requires, and how operational support needs to change. For customers, that means when CPO switches are broadly available, the procedures have been tested by teams running them in a real rack environment, not only in a lab.

Lambda has held NVIDIA Exemplar Cloud status. This engagement goes deeper than previous ones. NVIDIA's engineering team is embedded at the deployment level, working through the same infrastructure details alongside Lambda's team.

Why this architecture fits large NVIDIA GB300 NVL72 clusters

Agentic workloads change the pressure on the network. A traditional inference request is relatively self-contained. An agentic request can involve planning, retrieval, tool use, multiple model calls, and follow-up reasoning. More data moving across the cluster. More points where network latency or failure affects the outcome.

As Ashkan Seyedi, Director of Product Marketing for Networking at NVIDIA, describes it: "Multi-agentic inference needs elastic and resilient data movement, so GPUs are not waiting for data, while maintaining tokens per second and fast time to first token."

CPO connects directly to the token economy. Network power is overhead: it keeps GPUs connected but doesn't generate tokens. Network failures are also overhead: they turn provisioned GPU capacity into idle capacity. CPO addresses both by reducing network power draw and removing a large class of pluggable optical components from the fabric.

Infrastructure change

Customer outcome

Less switch power

More power available for GPUs

More compute in the same footprint

Higher token capacity per data center

Fewer pluggable optical parts

Fewer network-related service events

Liquid-cooled switch architecture

Consistent with GB300-class infrastructure

What's next

CPO changes where optical conversion occurs, how the switch is cooled, how fiber is planned, and how much of the cluster's power budget goes to networking rather than compute.

Large GPU clusters are becoming power-bound, reliability-bound, and network-bound simultaneously. Co-packaged optics is one path toward more compute in the same data center footprint, fewer discrete failure points, and better tokens per watt. As workloads shift toward agentic inference, where the network sits within the token-generation path on every call, that pressure grows.

More GPUs in the same data center. Fewer interruptions. More tokens per watt. Lambda is committed to being first.

To learn more about Lambda CPO, view our 
Supercluster page
 or 
talk to our team
.
