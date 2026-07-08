---
source_id: nccl-nvidia-blog-wide
title: One-Click Multi-Tenant Security with  NVIDIA Quantum InfiniBand
canonical_url: https://developer.nvidia.com/blog/one-click-multi-tenant-security-with-nvidia-quantum-infiniband/
captured_at: '2026-07-05T04:10:56.439652+00:00'
content_hash: 5b2cd4e1d4f6f48237e38186fb0dddcb51400b3ae4ba35ddd8d109e020fb4adc
---
# One-Click Multi-Tenant Security with  NVIDIA Quantum InfiniBand

URL: https://developer.nvidia.com/blog/one-click-multi-tenant-security-with-nvidia-quantum-infiniband/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2026/06/ethernet-tech-blog-networking-software-kv-1920x1080-5338100-768x432.png" style="display: block; margin-bottom: 5px; clear: both;" title="ethernet-tech-blog-networking-software-kv-1920x1080-5338100" width="768" />NVIDIA Quantum InfiniBand now offers intent-based security profiles in Unified Fabric Manager (UFM) that enable multi-tenant fabric security in a single...

Article Body:
Agentic AI / Generative AI

 

 
 

 

 
English
中文

 

 

 
One-Click Multi-Tenant Security with  NVIDIA Quantum InfiniBand

 
 

 

 

 Jun 11, 2026
 

 

 By 
David Slama
 and 
Michael Tahar
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
NVIDIA Quantum InfiniBand now features intent-based security profiles in Unified Fabric Manager, enabling rapid, automated multi-tenant fabric security and tenant isolation for large-scale GPU clusters.
Three predefined profiles-General, Bare Metal Cloud, and Secured Bare Metal Cloud-allow administrators to deploy robust security features like PKey isolation, MAD key protection, and GUID-based access control, reducing manual configuration errors and deployment time.
Continuous Security Verification (CSV) provides automated auditing and remediation guidance, giving users a real-time security health score to ensure ongoing protection and compliance across InfiniBand deployments.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

NVIDIA Quantum InfiniBand
 now offers intent-based security profiles in Unified Fabric Manager (UFM) that enable multi-tenant fabric security in a single click. 

NVIDIA Quantum InfiniBand supports three profiles: General, Bare Metal Cloud, and Secured Bare Metal Cloud. Network administrators can now auto-configure:

Partition Key (PKey) isolation

Management Datagram (MAD) key protection

Global Unique Identifier (GUID)-based access control

Continuous validation

This cuts deployment time to minutes from hours or days, letting cloud providers run hardware-enforced tenant isolation across tens of thousands of GPUs without manual Subnet Manager (SM) configuration. 

With the exponential growth of AI, HPC, and hyperscale cloud computing, the integrity of the network fabric is more critical than ever, yet many networks treat security as an afterthought.

InfiniBand takes the opposite approach: security extends across every layer of the fabric. While InfiniBand is best known for ultra-low latency, high throughput, and massive scalability, its 
multilayered security architecture
 is equally robust. 

This post explains how intent-based profiles make it easy to deploy.

Why traditional networks fall short on multi-tenant security

InfiniBand is a software-defined, centrally managed fabric. In traditional networking, endpoints often operate independently, making their own routing, resource, and policy decisions. This lack of centralized oversight can lead to misconfigurations, inconsistent policies, and security vulnerabilities. NVIDIA Quantum InfiniBand avoids this by centralizing control in UFM, which enforces global policies, optimizes routes, monitors health, and proactively secures the fabric.

Despite NVIDIA providing robust solutions such as integrity mechanisms and hardware-enforced tenant isolation, such features remain underutilized because Quantum InfiniBand isn’t as widely understood as Ethernet. 

There is currently a critical need to bridge the gap between InfiniBand’s advanced security capabilities and the user’s ability to easily implement them without deep domain expertise. In agentic AI environments that are connecting tens of thousands of GPUs with thousands of switches, even a minor configuration error in tenant isolation can compromise sensitive proprietary data or disrupt massive distributed workloads. Security features must be scalable and easy to deploy to make customers’ work easier and their clusters more secure.

To address these issues, NVIDIA presents a one-click solution for enabling InfiniBand security features.

What are intent-based security profiles for NVIDIA Quantum InfiniBand?

NVIDIA is introducing intent-based security profiles to simplify and standardize security configuration across different deployment models. Instead of manually configuring multiple parameters, users can select a predefined profile, and UFM will automatically orchestrate all underlying security settings.

The following are key benefits of intent-based profiles:

Fewer errors
: Profiles implement and deploy security features as NVIDIA engineering intends, protecting against misunderstandings or missing documentation.

Configuration time reduction
: Transitioning from manual, multi-step UFM/SM configurations to pre-configured, intent-based profiles can reduce learning, adapting configurations, and deployment and testing time to minutes from hours or days.

Zero-touch scaling
: Hundreds of nodes can be added to a multi-tenant environment without a linear increase in security management overhead.

No security downtime
: When a new security feature is added, it is added to the relevant profile configurations, removing the transition phase between releasing a new feature and enabling it in deployment.  

The General profile is designed for single-tenant environments with a basic out-of-the-box configuration. 

Bare Metal Cloud is tailored for multi-tenant cloud environments and Secured Bare Metal Cloud is a hardened profile for highly secure multi-tenant environments. 

The following sections will go into more detail about the Bare Metal Cloud and Secured Bare Metal Cloud profile types. 

The Bare Metal Cloud profile

The Bare Metal Cloud profile enables 
PKey-based isolation
, providing tenant separation within cloud environments over the InfiniBand management network.

Analogous to Ethernet VLANs, InfiniBand partitioning with PKeys defines which nodes or ports can access network resources, using hardware mechanisms to prevent ports in one partition from accessing another. 

What makes this mechanism particularly well-suited to multi-tenant deployments is that partition assignment is controlled entirely by the SM: Nodes can’t determine their own partitions, and applications can’t specify which partition to use; they can only reference partitions already assigned to their port. 

Port attributes are stored in hardware and are accessible only via the Management Key (MKey), which is known exclusively to the SM and the InfiniBand silicon. This architecture gives cloud service providers and data center operators a strong isolation guarantee. Tenants sharing the same physical InfiniBand fabric are cryptographically and logically separated at the hardware level, with no reliance on host-side software enforcement that a tenant with elevated privileges could circumvent.

The Secured Bare Metal Cloud profile

The Secured Bare Metal Cloud profile builds on PKey isolation and enables a comprehensive set of security features required for secure multi-tenant cloud environments:

Full MAD key protection with randomized seeds, including: MKEY, VSKEY, PMKEY, CCKEY, Class C key (N2N), AM and job keys, SMKEY, and SAKEY

GUID-based access control using the 
allowed_guid_list
 feature

Service-level authentication via 
service_key
 (e.g., for AM services)

Enhanced SA trust model applied to all commands

MAD rate limiting (MAD Limiter) to protect against abuse and congestion

DoS/DDoS Protection: Automatically identifies and limits excessive packet rates from individual nodes to protect the management node.

Source-Based Rate Limiting: Operates by monitoring and controlling traffic based on the source LID address of each node.

This approach reduces complexity, minimizes configuration errors, and ensures consistent security enforcement across deployments, allowing users to align infrastructure behavior with their intended operational model.

How to validate NVIDIA Quantum InfiniBand security posture with CSV

Another feature supported for NVIDIA Quantum InfiniBand deployments is Continuous Security Verification (CSV). This is a new UFM diagnostic capability that performs static analysis and log-based auditing. It provides users with a “Security Health Score” as well as specific, automated remediation steps for any detected vulnerabilities. 

Combined with intent-based profiles, this proactive diagnostic tool is critical for ensuring efficient and secure network operations.

In Figure 1, below, the screenshots show the flow for generating the security report.

In the System Health tab, users select Security from the top menu.

 

 
Figure 1: Users can validate network security posture with the System Health Security dashboard in UFM Cyber AI 

Next, users select the desired verbosity level (Errors, Errors and Warnings, and Info), as well as the option to test PKeys settings, and then run the report. See Figure 2, below: 

 

 
Figure 2: The security validation report displays different outputs based on selected verbosity 

Once the report is completed, the results will display a list of errors, warnings, and information messages based on the selected verbosity level. See Figure 3, below:

 

 
Figure 3: The System Health Security report displays a list of potential network security vulnerabilities

Going further 

For more information about guidelines and best practices for translating complex fabric security features into actionable deployment, learn more by reading the 
NVIDIA Quantum InfiniBand security white paper
.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Agentic AI / Generative AI
 | 
Networking / Communications
 | 
Trustworthy AI / Cybersecurity
 | 
Cloud Services
 | 
InfiniBand
 | 
Unified Fabric Manager
 | 
Intermediate Technical
 | 
Announcement
 | 
Tutorial
 | 
featured
 | 
Quantum Computing
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About David Slama
 

 

 
 David Slama serves as senior director of marketing for networking at NVIDIA, focusing on high performance computing, artificial intelligence, cloud solutions, and the InfiniBand technology. Slama joined Mellanox in 2005 as a SW engineer, and served in several SW management roles until 2020 at Mellanox. He lead Cloud Solutions, Ethernet & InfiniBand SW management, storage, automation solutions, and upstream activities such as Ansible, Kubernetes, OpenStack, puppet, chef, and more. Slama holds a patent in the field of ML and AI for networking. He has an MA in government and a BA in management and computer science.
 
 
 

 

 View all posts by David Slama

 

 

 

 

 

 

 

 

 

 

 About Michael Tahar
 

 

 
 Michael Tahar is a networking security architect, focusing on networking protocols and embedded security. He has worked at Nvidia since 2020, focusing on hardware and firmware security, and networking protocols such as InfiniBand, Ethernet and NVLink.
 
 
 

 

 View all posts by Michael Tahar

 

 

 

 

 

 

 

 

 

 

 
Comments
