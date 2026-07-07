---
type: RawSource
title: AWS Elastic Fabric Adapter AI Cluster Networking Documentation
source_kind: web
url: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html
related_urls:
  - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa-start.html
captured: 2026-07-07
status: ingested
---
# Source

Official AWS documentation:

- Elastic Fabric Adapter: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html
- Get started with EFA and MPI: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa-start.html

Captured as a concise source note for `ai_infra` network-storage-cluster coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Elastic Fabric Adapter is an AWS network interface for Amazon EC2 instances that targets high-performance computing and machine-learning workloads.
- EFA exposes normal Elastic Network Adapter behavior plus an EFA communication path for supported applications and instance types.
- AWS positions EFA around OS-bypass communication, where supported applications can communicate with the network interface with less operating-system involvement than the standard TCP/IP path.
- EFA software setup includes the EFA installer and libfabric integration, so the application/runtime stack must use compatible libraries rather than treating EFA as only a bandwidth field on an instance table.
- EFA is cluster fabric evidence for EC2-based AI/HPC jobs. It should not be used as proof of storage behavior, cost attribution, queue governance, or generic cloud capacity availability without separate sources.

# Use In Wiki

Use this source note for source-backed claims about AWS EFA as an AI/HPC cluster networking interface, especially OS-bypass communication and libfabric-backed runtime integration boundaries.
