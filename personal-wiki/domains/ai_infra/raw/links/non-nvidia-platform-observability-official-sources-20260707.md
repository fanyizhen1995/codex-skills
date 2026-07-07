---
type: RawSource
title: Non NVIDIA Platform Observability Official Sources
source_kind: web
url: https://instinct.docs.amd.com/projects/device-metrics-exporter/en/latest/
secondary_urls:
  - https://rocm.docs.amd.com/projects/rocm_smi_lib/en/latest/
  - https://docs.habana.ai/en/latest/Orchestration/Prometheus_Metric_Exporter.html
captured: 2026-07-07
status: ingested
---
# Source

Official AMD Device Metrics Exporter documentation: https://instinct.docs.amd.com/projects/device-metrics-exporter/en/latest/

Official AMD ROCm SMI library documentation: https://rocm.docs.amd.com/projects/rocm_smi_lib/en/latest/

Official Intel Gaudi Prometheus Metric Exporter documentation: https://docs.habana.ai/en/latest/Orchestration/Prometheus_Metric_Exporter.html

Captured as a concise source note for `ai_infra` non-NVIDIA accelerator observability coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- AMD Device Metrics Exporter provides Prometheus-format metrics for AMD GPUs and NICs in HPC and AI environments.
- AMD Device Metrics Exporter lists a Prometheus-compatible endpoint, GPU telemetry, Kubernetes Helm integration, Slurm integration, configurable ports, and container-based deployment.
- AMD GPU metrics include temperature, utilization, memory utilization, clock speed, power, energy, VRAM, PCIe bandwidth, link speed, and PCIe error-count signals.
- AMD NIC metrics include port, frame, octet, pause, priority-frame, error-count, LIF, drop, queue-pair, congestion, RDMA, CNP, ECN, request/response error, and Ethtool-style signals.
- ROCm SMI is a Linux user-space library in the ROCm software stack that lets applications monitor and control GPU applications.
- AMD SMI is documented as the successor to ROCm SMI and is intended as a unified system-management interface for querying driver and GPU information and controlling GPU applications.
- Intel Gaudi Prometheus Metric Exporter is documented as an exporter for collecting Intel Gaudi AI accelerator metrics in container clusters.
- Intel Gaudi Prometheus Metric Exporter supports Docker and Kubernetes deployment and recommends kube-prometheus integration with a ServiceMonitor for Kubernetes use.
- Intel Gaudi exporter metrics include device information, SoC clocks, ECC status, energy, free/used/total memory, NIC port status, PCIe speed/width/throughput/replay counters, power, board/on-chip temperatures, thermal thresholds, and device utilization.
- The Google Cloud TPU monitoring page was considered during source selection, but it was not promoted into this note because the web probe did not return reliable content in this run.

# Use In Wiki

Use this source note for bounded non-NVIDIA observability mechanics: AMD Prometheus exporter telemetry, ROCm/AMD SMI management surfaces, AMD NIC/RDMA counters, and Intel Gaudi Prometheus exporter metrics. Do not use it to claim production AMD, TPU, XPU, or Gaudi reliability; measured benchmark baselines; alert thresholds; or incident remediation without additional run artifacts or postmortem evidence.
