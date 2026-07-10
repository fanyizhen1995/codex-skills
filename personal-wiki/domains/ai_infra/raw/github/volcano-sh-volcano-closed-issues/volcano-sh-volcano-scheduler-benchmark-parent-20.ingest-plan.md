# Ingest Plan

Source paths:
- `raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-index.json`
- `raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz`

## Selected Slice

Continuation parent-20 promotes only the following local `volcano-sh/volcano`
closed issue records:

- #999, "Benchmark on volcano scheduler": benchmark-design request for scalability dimensions such as large pod counts, thousands of nodes, scheduler throughput, scheduling latency, and device-aware repeats.
- #1740, "Optimize the throughput of scheduler": throughput-requirement signal for high-performance workload submission at large scale.
- #1059, "better log level to improve scheduler performance": reporter-stated performance incident where Volcano v1.0.1 on Kubernetes 1.14 took nearly 30 minutes to schedule 1k podgroups with 1w pods in a 1w-node cluster, with log volume at level 3 reported as a scheduler performance factor.
- #5536, "Add skip check in `predicateByStablefilter`": stable-filter hot-path evidence where `predicateByStablefilter` needed to honor `PreFilter` skip state before calling `Filter()` for every node.

## Duplicate Boundaries

Do not re-promote parent-5 DRA/device-plugin/vGPU/Hami upgrade-adjacent issue
records as parent-20 evidence: Volcano #5119, #4692, #5335, #5361, and #2965;
Kueue #12207 and #9868; Kubernetes #139016, #137617, #138882, #135661,
#133702, #133488, #135901, and #138407.

Earlier orchestration text already covers Kueue admission and preemption
examples, Volcano gang scheduling, GPU sharing, vGPU, scheduler panic, and
upgrade/quota examples. Parent-20 adds only benchmark-design, throughput-demand,
log-volume sensitivity, and stable-filter skip-path evidence.

## Curated Targets

- `wiki/references/orchestration-scheduling-infrastructure.md`
- `wiki/references/kubernetes-volcano-kueue-github-closed-issues.md`
- `wiki/references/ai-infra-coverage-map.md`
- `coverage-map.json`
- `loop-state.json`
- `ingest.md`

## Non-Promoted Claims

This slice must not claim controlled benchmark results, production SLOs,
service-impact timelines, remediation ownership, full benchmark submissions,
or reproducible scheduler baselines. #999 and #1740 remain request or
requirement evidence; #1059 remains a reporter observation scoped to its stated
Volcano and Kubernetes versions; #5536 remains hot-path optimization evidence
without measured output.
