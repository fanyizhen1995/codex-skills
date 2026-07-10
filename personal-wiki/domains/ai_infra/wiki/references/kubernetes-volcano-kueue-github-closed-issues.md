---
type: Reference
title: Kubernetes, Volcano, And Kueue GitHub Closed Issues
description: Local raw corpus and monthly sync setup for closed GitHub issues from Kubernetes, Volcano, and Kueue.
domain: ai_infra
status: reviewed
tags:
  - kubernetes
  - volcano
  - kueue
  - github-issues
  - scheduling
source_refs:
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-index.json
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-api-pages.json.gz
  - ../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-issue-comments-api-pages.json.gz
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-index.json
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-api-pages.json.gz
  - ../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-issue-comments-api-pages.json.gz
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-index.json
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-api-pages.json.gz
  - ../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-issue-comments-api-pages.json.gz
updated: 2026-07-10
aliases:
  - Kubernetes closed issue corpus
  - Volcano closed issue corpus
  - Kueue closed issue corpus
related:
  - ../projects/kubernetes.md
  - ../projects/volcano.md
  - ../projects/kueue.md
---
# Summary

This reference indexes the local raw corpus for closed GitHub issues from `kubernetes/kubernetes`, `volcano-sh/volcano`, and `kubernetes-sigs/kueue`. The raw layer preserves GitHub API issue/search pages, issue-comment API pages, joined issue/comment records, summaries, indexes, and ingest plans.

The current backfill captures `volcano-sh/volcano` and `kubernetes-sigs/kueue` across their full closed-issue history, and captures `kubernetes/kubernetes` for issues closed on or after 2023-07-01. The Kubernetes window uses monthly GitHub Search ranges for issue discovery, while the all-time Volcano and Kueue backfills use the closed issues endpoint.

# Corpus Scope

| Repository | Issue pages | Closed issues | Comment pages | Joined comments | Reported GitHub comments | Comment mismatches | State reasons | Closed range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `kubernetes/kubernetes` | 79 | 5,897 | 300 | 6,386 | 65,276 | 5,493 issues | `completed`: 4,506; `duplicate`: 13; `not_planned`: 1,378 | 2023-07-01 to 2026-06-30 |
| `volcano-sh/volcano` | 49 | 1,772 | 267 | 8,369 | 8,368 | 1 issue | `completed`: 1,760; `duplicate`: 1; `not_planned`: 11 | 2019-03-20 to 2026-06-30 |
| `kubernetes-sigs/kueue` | 122 | 2,488 | 300 | 6,650 | 16,125 | 1,536 issues | `completed`: 2,294; `duplicate`: 2; `not_planned`: 192 | 2022-02-18 to 2026-06-30 |

For Volcano and Kueue, the issue endpoint was queried with `state=closed`, `sort=updated`, and `direction=desc`, then pull requests were filtered out of the joined corpus and index. For Kubernetes, monthly Search API windows queried `repo:kubernetes/kubernetes is:issue is:closed closed:<month-range>` and the joined corpus keeps only issues whose `closed_at` is on or after 2023-07-01.

The closed-issue sets are the intended corpus scope. The joined comment files are not full comment corpora: they were built from repository-level issue-comment pages and are marked with `comment_capture_complete: false` in the summaries and manifests. Use `reported_comment_count` when sizing the total GitHub discussion volume, and use `comment_count` only as the number of comments actually joined into the local raw corpus.

# Raw Files

Kubernetes:

- [Summary](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json)
- [Index](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-index.json)
- [Joined issues and comments](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz)
- [Closed issue API pages](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-api-pages.json.gz)
- [Issue comment API pages](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-issue-comments-api-pages.json.gz)

Volcano:

- [Summary](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json)
- [Index](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-index.json)
- [Joined issues and comments](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)
- [Closed issue API pages](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-api-pages.json.gz)
- [Issue comment API pages](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-issue-comments-api-pages.json.gz)

Kueue:

- [Summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
- [Index](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-index.json)
- [Joined issues and comments](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz)
- [Closed issue API pages](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-api-pages.json.gz)
- [Issue comment API pages](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-issue-comments-api-pages.json.gz)

# Capture Notes

GitHub `state_reason` is workflow metadata. `completed`, `duplicate`, and `not_planned` all represent closed issues, but only the linked issue details and comments can show whether a closure corresponds to an implemented fix, duplicate handling, stale cleanup, design decision, or unsupported request.

The corpus script stores tokens only through the `GITHUB_TOKEN` environment variable. The combined run manifest is under `.codex/github-closed-issues/github-closed-issues-volcano-kueue-full-k8s-3y-01/manifest.json` and records rate-limit metadata, raw paths, comment completeness fields, and partial reasons for the run.

The successful backfill ran with proxy environment variables unset. The script retries transient GitHub read failures and uses repository-level issue-comment pages for comment joining instead of one request per issue. That join strategy is efficient for evidence sampling and basic issue lookup, but it is not sufficient for complete per-issue comment capture on large repositories.

# Monthly Synchronization

Crawler Workbench source profiles are configured for monthly tracking:

| Source ID | Repository | Schedule | Auth |
| --- | --- | --- | --- |
| `kubernetes-github-closed-issues` | `kubernetes/kubernetes` | monthly | `GITHUB_TOKEN` environment token |
| `volcano-github-closed-issues` | `volcano-sh/volcano` | monthly | `GITHUB_TOKEN` environment token |
| `kueue-github-closed-issues` | `kubernetes-sigs/kueue` | monthly | `GITHUB_TOKEN` environment token |

The profile URLs include `state=closed` so monthly checks stay aligned with the closed-issue corpus scope.

# Retrieval Notes

Use the summary JSON files for counts, `state_reason` splits, top labels, capture limits, and comment completeness fields. Use the index JSON files for quick issue lookup by number, title, URL, labels, state reason, close time, and joined comment count. Use the joined `.json.gz` files when locally captured comment text, reported per-issue GitHub comment counters, or full GitHub issue objects are needed.

# Parent-5 DRA And Device-Plugin Slice

The continuation parent-5 retrieval pass used only the existing local GitHub corpora and checked the curated orchestration page, this corpus page, coverage map, loop state, ingest log, and prior parent manifests before promotion. Previously promoted duplicate-boundary issue numbers were left unchanged: Kueue #1726, #696, #6143, #1407, #3094, #2867, #2941; Volcano #452, #2547, #3329, #2701, #3384, #3301, #2416, #2379; and downstream SGLang #23627.

The newly promoted Kubernetes issue slice is DRA and device-management focused: #139016 for stuck pods when shared multi-node claims mix with per-node GPU claims, #137617 for gang scheduling with shared ResourceClaims repeatedly failing scheduling, #138882 for a kube-scheduler panic around `allocationMode: All` plus shared counters, #135661 for a DynamicResources CEL selector error on missing `gpu.nvidia.com` attributes, #133702 for device-plugin unhealthy-device endpoint state drift after a DRA extended-resource test, #133488 for device-plugin cleanup leaving extended resources in node allocatable/capacity, #135901 for kubelet handling of multiple ResourceClaims after one is prepared, and #138407 for flapping `resourceClaimStatuses`.

The Kueue slice adds #12207 as a DRA partitionable-device quota borrowing bug with OpenShift, Kueue Operator, NVIDIA GPU Operator, DRA Driver, and `DRAPartitionableDevices` context. Kueue #9868 is retained as a non-failure feature boundary showing why DRA extended resources bridge legacy extended-resource requests such as `nvidia.com/gpu` into ResourceClaims for quota accounting.

The Volcano slice adds #5119 for `ResourceClaimTemplate` preparation failure in `vcjob`, #4692 for an unreleased DRA PreBind lock blocking the main scheduling workflow until timeout, #5335 for stale vGPU annotations after dry-run rollback causing over-subscription, #5361 for Hami vGPU scheduling delays in a 200-node, 8-GPU-per-node cluster after a Volcano and device-plugin upgrade, and #2965 as an older device-plugin reinstall and node `OutOfSync` scheduling boundary.

This slice is local issue-level evidence. It is not a complete comment corpus, production postmortem set, scheduler benchmark corpus, Slurm-on-Kubernetes bridge proof, or GPU-operator upgrade incident closure.

# Parent-20 Volcano Scheduler Benchmark And Throughput Slice

The continuation parent-20 retrieval pass reused the local Volcano closed-issue index and joined-comment corpus. It first treated parent-5 as a duplicate boundary: parent-5 promoted Kubernetes DRA and device-management issues, Kueue DRA quota issues, and Volcano DRA/vGPU/device-plugin/Hami upgrade-adjacent issues, but did not promote scheduler benchmark or throughput issues #999, #1740, #1059, or #5536.

Volcano #999, "Benchmark on volcano scheduler", is retained as benchmark-design evidence. The issue asks for scalability performance testing, suggests Kubemark to simulate Kubernetes nodes, names dimensions such as large pod counts, 1k-5k nodes, scheduler throughput, average scheduling latency under fixed pod creation frequency, and advanced device tests such as GPU repeats. Its comments discuss a pressure simulator for scheduler performance. It does not contain controlled benchmark measurements.

Volcano #1740, "Optimize the throughput of scheduler", is retained as a throughput-requirement signal. The issue says high-performance workloads are moving to Kubernetes and that scheduler throughput did not meet large-scale job submission requirements; a maintainer comment asks for a performance report before additional improvement. This is requirement and design-pressure evidence, not measured throughput.

Volcano #1059, "better log level to improve scheduler performance", is retained as a reported performance incident. The reporter stated that Volcano v1.0.1 on Kubernetes 1.14 took nearly 30 minutes to schedule 1k podgroups with 1w pods in a 1w-node cluster, and that log growth around 2 MB/s at log level 3 affected scheduler performance. The source does not provide a controlled benchmark harness, repeated results, remediation timeline, or production impact boundary.

Volcano #5536, "Add skip check in `predicateByStablefilter`", is retained as stable-filter hot-path evidence. The issue reports that stable filter plugins such as `NodeAffinity` can have `PreFilter` return `Skip`, but `predicateByStablefilter` still called `Filter()` for every node without `handleSkipPredicatePlugin(state, name)`. This is scheduler hot-path optimization evidence, not latency or throughput measurement.

This slice updates the orchestration-scheduling gap from "scheduler benchmark evidence missing" to "controlled scheduler benchmark results still missing." Local issue records now cover benchmark dimensions, throughput demand, one reporter-stated performance incident, and a stable-filter skip optimization, while benchmark outputs with full environment and measured results remain unclosed.

# Relationships

- [Kubernetes](../projects/kubernetes.md) is the upstream orchestration project page.
- [Volcano](../projects/volcano.md) is the batch scheduling project page.
- [Kueue](../projects/kueue.md) is the job queueing project page.

# Citations

- [Kubernetes closed issues summary](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-summary.json)
- [Kubernetes joined issues and comments](../../raw/github/kubernetes-kubernetes-closed-issues/kubernetes-kubernetes-closed-issues-with-comments.json.gz)
- [Volcano closed issues summary](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-summary.json)
- [Volcano joined issues and comments](../../raw/github/volcano-sh-volcano-closed-issues/volcano-sh-volcano-closed-issues-with-comments.json.gz)
- [Kueue closed issues summary](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-summary.json)
- [Kueue joined issues and comments](../../raw/github/kubernetes-sigs-kueue-closed-issues/kubernetes-sigs-kueue-closed-issues-with-comments.json.gz)
