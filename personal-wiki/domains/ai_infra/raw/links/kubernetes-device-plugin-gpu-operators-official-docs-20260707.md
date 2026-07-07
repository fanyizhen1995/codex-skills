---
type: RawSource
title: Kubernetes Device Plugin And GPU Operator Documentation
source_kind: web
url: https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/
related_urls:
  - https://github.com/NVIDIA/k8s-device-plugin
  - https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/overview.html
  - https://instinct.docs.amd.com/projects/gpu-operator/en/latest/
captured: 2026-07-07
status: ingested
---
# Source

Official Kubernetes, NVIDIA, and AMD documentation or primary repositories:

- Kubernetes Device Plugins: https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/
- NVIDIA Kubernetes device plugin: https://github.com/NVIDIA/k8s-device-plugin
- NVIDIA GPU Operator overview: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/overview.html
- AMD GPU Operator documentation: https://instinct.docs.amd.com/projects/gpu-operator/en/latest/

Captured as a concise source note for `ai_infra` accelerator orchestration coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official or primary project sources.

# Captured Facts

- Kubernetes device plugins let vendors advertise hardware resources that require vendor-specific setup, such as GPUs, NICs, FPGAs, and non-volatile memory, to the kubelet.
- The Kubernetes device plugin framework is the generic mechanism. Vendor plugins and operators are responsible for the hardware-specific runtime, discovery, health, and driver/container integration details.
- NVIDIA's Kubernetes device plugin is distributed as a DaemonSet and exposes GPU counts, tracks GPU health, and enables GPU-enabled containers. The repository states it is NVIDIA's official device plugin implementation.
- The NVIDIA GPU Operator automates Kubernetes provisioning of NVIDIA GPU software components including drivers, the Kubernetes GPU device plugin, NVIDIA Container Toolkit, GPU Feature Discovery, DCGM-based monitoring, MIG Manager, validators, and related components.
- AMD GPU Operator documentation says the operator simplifies deployment and management of AMD Instinct accelerators on Kubernetes, including driver management, AMD GPU device plugin deployment, DRA support, metrics export, worker node labeling, GPU resource allocation, health monitoring, and OpenShift/Kubernetes support.
- Device-plugin evidence supports scheduler-visible accelerator resources, while GPU-operator evidence supports node lifecycle, driver/runtime component management, labeling, health, and metrics boundaries.

# Use In Wiki

Use this source note for Kubernetes accelerator discovery, vendor device plugin behavior, NVIDIA and AMD GPU operator boundaries, node labeling, GPU health/metrics, driver/runtime management, and resource exposure. Do not use it for quota policy claims without Kueue or ResourceQuota evidence.
