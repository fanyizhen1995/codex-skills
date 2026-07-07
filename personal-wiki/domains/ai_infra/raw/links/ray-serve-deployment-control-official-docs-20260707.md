---
type: RawSource
title: Ray Serve Deployment Control Documentation
source_kind: web
url: https://docs.ray.io/en/latest/serve/autoscaling-guide.html
related_urls:
  - https://docs.ray.io/en/latest/serve/resource-allocation.html
  - https://docs.ray.io/en/latest/serve/advanced-guides/gang-scheduling.html
  - https://docs.ray.io/en/latest/serve/advanced-guides/inplace-updates.html
captured: 2026-07-07
status: ingested
---
# Source

Official Ray Serve documentation:

- Ray Serve autoscaling guide: https://docs.ray.io/en/latest/serve/autoscaling-guide.html
- Ray Serve resource allocation: https://docs.ray.io/en/latest/serve/resource-allocation.html
- Ray Serve gang scheduling: https://docs.ray.io/en/latest/serve/advanced-guides/gang-scheduling.html
- Ray Serve in-place updates: https://docs.ray.io/en/latest/serve/advanced-guides/inplace-updates.html

Captured as a concise source note for `ai_infra` inference deployment-control coverage. The full external pages were not mirrored; the durable facts below are paraphrased from official Ray documentation.

# Captured Facts

- Ray Serve autoscaling is configured on deployments through an autoscaling configuration rather than a fixed replica count.
- The autoscaling surface includes minimum replicas, maximum replicas, target ongoing requests per replica, and up/down delay controls for reacting to request load.
- Ray Serve resource allocation is set through deployment actor options such as CPU, GPU, custom resources, accelerator type, and memory choices.
- Resource allocation docs distinguish logical Ray resources from physical accelerator assignment, so placement claims should cite the configured resource request and Ray scheduling behavior rather than assuming a device layout.
- Ray Serve gang scheduling uses Ray placement groups for deployments whose replica needs multiple colocated actors, such as multi-GPU or multi-node model-serving replicas.
- Gang-scheduled deployments specify placement-group bundles and a placement-group strategy so the actors that make up one replica are scheduled as a unit.
- The in-place update guide separates lightweight config changes from updates that replace running replicas, so model-serving deployment changes can be rolled through the Serve control plane instead of manual process restarts.
- The update guidance is deployment-control evidence, not a complete production canary or incident record by itself; it does not provide service-impact timelines, rollback ownership, or SLO validation.

# Use In Wiki

Use this source note for Ray Serve autoscaling controls, request-load scaling boundaries, deployment resource and accelerator placement inputs, placement-group or gang-scheduled model-serving replicas, and Serve-controlled deployment updates. Do not use it as evidence for KServe, Knative, Kubernetes HPA, or a production postmortem without separate source material.
