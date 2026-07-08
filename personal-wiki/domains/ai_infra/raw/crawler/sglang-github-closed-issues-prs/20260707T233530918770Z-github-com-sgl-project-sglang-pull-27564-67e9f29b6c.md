---
source_id: sglang-github-closed-issues-prs
title: 'feat(metrics): add Prometheus metrics for the EPD encoder server'
canonical_url: https://github.com/sgl-project/sglang/pull/27564
captured_at: '2026-07-07T23:35:30.918770+00:00'
content_hash: 67e9f29b6c91087b570d7c1d7531a7a45c38f816e03ab8aa0fdb49354f78340a
---
# feat(metrics): add Prometheus metrics for the EPD encoder server

URL: https://github.com/sgl-project/sglang/pull/27564
State: closed
Labels: run-ci
Closed at: 2026-07-07T04:04:51Z
Merged at: 2026-07-07T04:04:51Z

## Motivation

The EPD disaggregated encoder server currently exposes no Prometheus metrics. Operators running a standalone encoder fleet have no visibility into cache effectiveness, request throughput, latency breakdown, or—in DP mode—per-rank load balancing. 

This PR adds a Prometheus metrics surface for the encoder server, mirroring the observability that the scheduler and tokenizer already provide.

## Modifications

Adds `EncoderMetricsCollector` and wires it into the encoder server. All metrics are gated behind `--enable-metrics`; `/metrics` is mounted in both the single-instance and DP-main processes, and per-worker collectors in DP mode write to the shared `PROMETHEUS_MULTIPROC_DIR` so the main process serves an aggregated endpoint.

**Metrics added**:

| Metric | Type | Extra labels | Purpose |
|---|---|---|---|
| `encoder_requests_total` | Counter | `modality`, `status` | requests by success/error |
| `encoder_requests_received_total` | Counter | `modality` | per-rank QPS via `rate(...)` |
| `encoder_cache_hit_tokens_total` / `encoder_cache_total_tokens_total` | Counter | `modality` | embedding-cache token hit rate |
| `encoder_cache_hit_files_total` / `encoder_cache_total_files_total` | Counter | `modality` | embedding-cache file hit rate |
| `encoder_cache_evictions_total` | Counter | `modality` | LRU evictions |
| `encoder_cache_size_mb` / `encoder_cache_entries` | Gauge | — | cache occupancy |
| `encoder_mm_items_per_batch` / `encoder_mm_items_per_request` | Histogram | `modality` | batching distribution |
| `encoder_queue_wait_seconds` | Histogram | `modality` | scheduler queue wait |
| `encoder_preprocess_seconds` | Histogram | `modality` | data load + processor |
| `encoder_model_forward_seconds` | Histogram | `modality` | ViT forward |
| `encoder_transfer_seconds` | Histogram | `backend` | embedding transfer (zmq / mooncake) |
| `encoder_batch_e2e_latency_seconds` | Histogram | `modality` | per-batch end-to-end |
| `encoder_dp_pending_requests` | Gauge | `dp_rank` | per-rank in-flight depth (DP dispatcher; main process) |


## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [ ] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [ ] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [ ] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [ ] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

































































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28776711622](https://github.com/sgl-project/sglang/actions/runs/28776711622)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28776711506](https://github.com/sgl-project/sglang/actions/runs/28776711506)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
