---
type: RawSource
title: Evaluation SLO Alerting Official Sources
source_kind: web
url: https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
secondary_urls:
  - https://prometheus.io/docs/alerting/latest/configuration/
  - https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/notification-policies/
  - https://grafana.com/docs/grafana-cloud/alerting-and-irm/slo/
  - https://grafana.com/docs/grafana-cloud/machine-learning/ai-observability/guides/dashboards/
captured: 2026-07-07
status: ingested
---
# Source

Official Prometheus alerting-rules documentation: https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/

Official Alertmanager configuration documentation: https://prometheus.io/docs/alerting/latest/configuration/

Official Grafana notification-policies documentation: https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/notification-policies/

Official Grafana SLO documentation: https://grafana.com/docs/grafana-cloud/alerting-and-irm/slo/

Official Grafana AI Observability dashboard documentation: https://grafana.com/docs/grafana-cloud/machine-learning/ai-observability/guides/dashboards/

Captured as a concise source note for `ai_infra` evaluation, alerting, SLO, and notification-routing mechanics. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Prometheus alerting rules define alert conditions with PromQL expressions and can attach alert labels and annotations for severity, ownership, summaries, and runbook-style context.
- Prometheus alert rules support a `for` duration before an active condition becomes firing and a `keep_firing_for` duration to reduce noisy resolve/re-fire behavior after the condition stops matching.
- Prometheus examples show threshold-style alert expressions such as high request latency and unreachable instances, but those examples are mechanics examples rather than production LLM service objectives.
- Prometheus sends firing alert state to Alertmanager; the Prometheus documentation separates rule evaluation from the richer notification layer.
- Alertmanager configuration centers on a routing tree, receivers, inhibition rules, and time intervals. A route node can group alerts by labels, match alerts by label matchers, set receiver behavior, and use wait, interval, repeat, mute, and active-time controls.
- Alertmanager route inheritance lets child routes reuse parent timing and grouping defaults unless the child route overrides them.
- Grafana notification policies route alert instances by label matchers, group multiple alert instances into a notification, and deliver the result to a contact point.
- Grafana notification policies are arranged as a tree with a default root policy, optional child policies, sibling policies, and deepest-match routing behavior unless sibling continuation is enabled.
- Grafana SLO frames service reliability around service-level indicators and objectives, acceptable service levels, reliability over time, alert fatigue reduction, SLO alert rules, SLO dashboards, burn-rate views, and error-budget views.
- Grafana AI Observability dashboards expose LLM application signals for activity, latency, time to first token, error rate, token usage, cost, cache efficiency, tool behavior, quality scores, and quality trends.
- Grafana AI Observability documents Prometheus metrics for LLM call duration, token usage, time to first token, tool calls, build version labels, and optional evaluation metrics; it also describes alert examples for error-rate thresholds, p95 latency against SLO targets, daily cost budgets, and evaluation-score drops.

# Use In Wiki

Use this source note for bounded mechanics claims about alert-rule expressions, alert stabilization windows, Alertmanager/Grafana routing trees, contact-point routing, SLO/SLI/error-budget mechanics, and LLM application metrics that can feed alerting. Do not use it to claim a validated production LLM SLO, a chosen production alert threshold, a real escalation policy, an incident timeline, a postmortem, or a local benchmark baseline without additional service-specific run evidence.
