---
type: RawSource
title: NVIDIA DCGM User Guide
source_kind: web
url: https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/index.html
captured: 2026-07-07
status: ingested
---
# Source

Official NVIDIA Data Center GPU Manager user guide: https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/index.html

Captured as a concise source note for `ai_infra` evaluation, observability, and reliability coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- NVIDIA DCGM is a data-center GPU management and monitoring stack for GPU health, telemetry, diagnostics, and policy checks.
- DCGM exposes GPU field values and health information that can be consumed by host or cluster monitoring systems.
- DCGM diagnostics support active validation workflows for deployed GPU systems.
- DCGM profiling and field groups provide infrastructure signals that are broader than one communication library or one model-serving framework.
- DCGM evidence belongs in the platform-observability layer because it supports health and telemetry collection for GPU nodes, not benchmark scoring or model-quality evaluation.

# Use In Wiki

Use this source note for DCGM claims about GPU telemetry, health, diagnostics, field values, profiling support, and cluster-level platform observability for AI infrastructure.
