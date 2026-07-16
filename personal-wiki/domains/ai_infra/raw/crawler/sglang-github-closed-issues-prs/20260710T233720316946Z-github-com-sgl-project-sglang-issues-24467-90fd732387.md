---
source_id: sglang-github-closed-issues-prs
title: '[Feature][RFC] Plug-in metrics backend via class-level DI for collectors'
canonical_url: https://github.com/sgl-project/sglang/issues/24467
captured_at: '2026-07-10T23:37:20.316946+00:00'
content_hash: 90fd7323870bba83d2172c0ced4be81c2c6a0ed60d517202178302f4b0b7c795
---
# [Feature][RFC] Plug-in metrics backend via class-level DI for collectors

URL: https://github.com/sgl-project/sglang/issues/24467
State: closed
Labels: inactive
Closed at: 2026-07-10T00:39:39Z
Merged at: 

### Checklist

- [x] If this is not a feature request but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Motivation


When SGLang runs as an embedded engine inside downstream serving infrastructure (Ray Serve LLM, custom inference platforms), the metric storage backend is locked to `prometheus_client` at import time. The five `*MetricsCollector` classes in `python/sglang/srt/observability/metrics_collector.py` instantiate `Counter`, `Gauge`, `Histogram`, and `Summary` directly. Embedded users have three workarounds today:

| Workaround | Cost |
|---|---|
| Tail `--export-metrics-to-file` output | Operational complexity; filesystem path coupling; file rotation handling |
| Scrape `PROMETHEUS_MULTIPROC_DIR` directly | Couples downstream code to internal metric names and label keys |

`RequestMetricsExporter` ([#11141](https://github.com/sgl-project/sglang/issues/11141) / [#10973](https://github.com/sgl-project/sglang/pull/10973)) opened the request-finish event layer to plug-ins. The storage layer behind every collector remains hardcoded. To close that gap and follow the pattern proven in vLLM (`vllm/v1/metrics/ray_wrappers.py` plus the `_gauge_cls` / `_counter_cls` / `_histogram_cls` indirection on `PrometheusStatLogger`), we propose two PRs:

**1. Class-level DI on collectors and `stat_loggers` Engine kwarg [[PR]](https://github.com/sgl-project/sglang/pull/24610):** Refactor the five `*MetricsCollector` classes to instantiate metrics through `_gauge_cls`, `_counter_cls`, `_histogram_cls`, and `_summary_cls` class attributes. Defaults stay at the current `prometheus_client` classes, so existing deployments see no change. Add an optional `Dict[str, type]` field `stat_loggers` on `ServerArgs`. Keys are collector roles; values are subclasses of the matching base collector. The five instantiation sites read from this map and fall back to the base class. Class-object kwarg only; CLI exposure is omitted because import-path string parsing is fragile and unnecessary for embedded use cases. The DI refactor and the kwarg ship together because the refactor alone has no public consumer.

   Affected collectors:

   | Collector | Metric count | Uses `Summary`? |
   |---|---|---|
   | `SchedulerMetricsCollector` | 77 | Yes (one feature-flagged metric, `eplb_balancedness`, gated on `SGLANG_ENABLE_EPLB_BALANCEDNESS_METRIC`) |
   | `TokenizerMetricsCollector` | 12 | No |
   | `StorageMetricsCollector` | 6 | No |
   | `RadixCacheMetricsCollector` | 4 | No |
   | `ExpertDispatchCollector` | 1 | No |

   `_summary_cls` is added on `SchedulerMetricsCollector` only.

**2. Reference Ray wrappers [PR]:** Add `python/sglang/srt/observability/ray_wrappers.py` mirroring vLLM's wrapper file. Provides `RayGaugeWrapper`, `RayCounterWrapper`, `RayHistogramWrapper`, `RaySummaryWrapper` on top of `ray.util.metrics`, plus five `Ray*MetricsCollector` subclasses overriding the class attrs from PR 1. The base class handles Ray Serve replica context (`_get_replica_id()`) and OTel-compliant name sanitization. `ray.util.metrics` rejects `:` in names, so `sglang:foo` becomes `sglang_foo`. Imported only when the caller routes metrics to Ray.

### Usage

Embedded users swap the metric storage backend in one place. Example for Ray Serve LLM:

```python
import sglang
from sglang.srt.observability.ray_wrappers import (
    RaySchedulerMetricsCollector,
    RayTokenizerMetricsCollector,
    RayStorageMetricsCollector,
    RayRadixCacheMetricsCollector,
    RayExpertDispatchCollector,
)

engine = sglang.Engine(
    model_path="meta-llama/Llama-3.1-8B-Instruct",
    enable_metrics=True,
    stat_loggers={
        "scheduler": RaySchedulerMetricsCollector,
        "tokenizer": RayTokenizerMetricsCollector,
        "storage": RayStorageMetricsCollector,
        "radix_cache": RayRadixCacheMetricsCollector,
        "expert_dispatch": RayExpertDispatchCollector,
    },
)
```

All ~100 `sglang:*` metrics now flow directly to `ray.util.metrics`, with Ray Serve labels (`application` / `deployment` / `replica`) appended automatically. The samples appear on Ray's Prometheus endpoint:

```bash
$ curl -s http://ray-cluster:8080/metrics | grep ray_serve_sglang_ | head
ray_serve_sglang_prompt_tokens_total{model_name="meta-llama/Llama-3.1-8B-Instruct",tp_rank="0",replica="...",...} 8128902
ray_serve_sglang_num_running_reqs{...} 8
ray_serve_sglang_token_usage{...} 0.28
ray_serve_sglang_time_to_first_token_seconds_bucket{le="0.1",...} 254
```

The same hook can target OpenTelemetry, Datadog, or in-house telemetry by supplying a different set of subclasses. SGLang itself does not integrate with any specific vendor.

For users not setting `stat_loggers`, behavior is unchanged. Existing CLI flags, `PROMETHEUS_MULTIPROC_DIR`, and Grafana dashboards keep working without modification.

### Backward compatibility

| Concern | Status |
|---|---|
| Existing `prometheus_client`-based deployments | No change. Defaults preserved |
| Existing metric names (`sglang:foo`) | No change. Only Ray wrapper sanitizes names |
| Existing Grafana dashboards | No change |
| Existing `PROMETHEUS_MULTIPROC_DIR` env behavior | No change |
| Existing CLI flags (`--enable-metrics`, `--export-metrics-to-file`, ...) | No change |
| Anyone not setting `stat_loggers` | Gets today's behavior |

### Related resources

| Reference | Purpose |
|---|---|
| [vllm-project/vllm `vllm/v1/metrics/ray_wrappers.py`](https://github.com/vllm-project/vllm/blob/main/vllm/v1/metrics/ray_wrappers.py) | Working implementation of the proposed pattern |
| [vllm-project/vllm `vllm/v1/metrics/loggers.py`](https://github.com/vllm-project/vllm/blob/main/vllm/v1/metrics/loggers.py) | `PrometheusStatLogger` showing the class-attr pattern |
| [ray-project/ray#62791](https://github.com/ray-project/ray/issues/62791) | Downstream tracking issue (use case driving this RFC) |
