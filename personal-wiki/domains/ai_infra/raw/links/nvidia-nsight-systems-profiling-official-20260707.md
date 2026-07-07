---
type: RawSource
title: NVIDIA Nsight Systems User Guide
source_kind: web
url: https://docs.nvidia.com/nsight-systems/UserGuide/index.html
captured: 2026-07-07
status: ingested
---
# Source

Official NVIDIA Nsight Systems user guide: https://docs.nvidia.com/nsight-systems/UserGuide/index.html

Captured as a concise source note for `ai_infra` evaluation, observability, and reliability coverage. The full external page was not mirrored; the durable facts below are paraphrased from the official source.

# Captured Facts

- NVIDIA Nsight Systems is a system-wide performance analysis tool for profiling applications across CPU and GPU activity.
- The user guide documents timeline-oriented profiling for CUDA workloads and host-side execution, which helps operators inspect scheduling, synchronization, and bottlenecks.
- Nsight Systems captures traces that can include CUDA API activity, GPU kernels, memory operations, operating-system runtime activity, and process or thread behavior.
- Nsight Systems evidence is useful for diagnosing workload behavior and runtime bottlenecks, but it is not a service-level observability store by itself.
- Profiling captures should be tied to workload, hardware, software version, and configuration context before being used as benchmark evidence.

# Use In Wiki

Use this source note for Nsight Systems claims about CPU/GPU timeline profiling, CUDA workload diagnosis, synchronization analysis, and benchmark-environment context requirements.
