import { AlertTriangle, CalendarClock, GitCommit, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getHealth, getQueue, getRuns, getSources, getWikiMetrics, validateWiki } from "../api";
import { TrendChart, type TrendPoint } from "../components/TrendChart";
import { StatusBadge } from "../components/StatusBadge";
import type { FetchRun, HealthResponse, IngestTask, SourceProfile, Status, WikiMetricsResponse } from "../types";

function statusForHealth(health: HealthResponse | null, error: string): Status {
  if (error) {
    return "failed";
  }
  return health?.status === "ok" ? "ready" : "pending";
}

function timeLabel(value?: string) {
  if (!value) {
    return "未记录";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function sizeLabel(bytes?: number) {
  if (bytes === undefined) {
    return "未知";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

function otherWikiBytes(metrics: WikiMetricsResponse) {
  return Math.max(0, metrics.sizes.total_bytes - metrics.sizes.wiki_bytes - metrics.sizes.raw_bytes);
}

function scheduleLabel(schedule?: string) {
  const labels: Record<string, string> = {
    hourly: "每小时",
    daily: "每日",
    weekly: "每周",
    monthly: "每月",
    manual: "按需",
    on_demand: "按需"
  };
  if (!schedule) {
    return "未计划";
  }
  return labels[schedule] ?? schedule;
}

function coerceStatus(status?: string): Status {
  const validStatuses: Status[] = [
    "ready",
    "pending",
    "running",
    "succeeded",
    "failed",
    "needs_auth_config",
    "trusted",
    "untrusted"
  ];
  if (status && validStatuses.includes(status as Status)) {
    return status as Status;
  }
  return "pending";
}

function runTime(run: FetchRun) {
  return run.finished_at ?? run.started_at ?? `run-${run.id}`;
}

function trendLabel(run: FetchRun) {
  const raw = runTime(run);
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return raw;
  }
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function summarizeTrend(runs: FetchRun[]): TrendPoint[] {
  return runs
    .slice(0, 12)
    .reverse()
    .map((run) => ({
      label: trendLabel(run),
      fetched: run.fetched_count ?? 0,
      changed: run.changed_count ?? 0,
      failed: run.failed_count ?? (run.status === "failed" ? 1 : 0)
    }));
}

function statusCount(tasks: IngestTask[], status: string) {
  return tasks.filter((task) => task.status === status).length;
}

function runCountLabel(run: FetchRun) {
  return `已抓 ${run.fetched_count ?? 0}，更新 ${run.changed_count ?? 0}，失败 ${run.failed_count ?? 0}`;
}

function runFailureReason(run: FetchRun) {
  const reason = run.failure_reason ?? run.error;
  if (typeof reason === "string" && reason.trim() !== "") {
    return reason;
  }
  return `运行 #${run.id} 失败`;
}

interface FailureSummary {
  key: string;
  label: string;
  detail: string;
  count: number;
  sources: string[];
  reasons: string[];
  latestTime: string;
}

function classifyFailureReason(reason: string) {
  const normalized = reason.replace(/\s+/g, " ").trim();
  const lower = normalized.toLowerCase();
  const statusMatch = normalized.match(/\b([345]\d{2})\b/);
  if (lower.includes("timed out") || lower.includes("timeout")) {
    return { key: "timeout", label: "网络超时", detail: "目标站点响应超时，通常可稍后重试" };
  }
  if (statusMatch) {
    const code = statusMatch[1];
    if (code === "301" || code === "302" || code === "307" || code === "308") {
      return { key: `http-${code}`, label: `HTTP ${code} 重定向`, detail: "抓取地址发生跳转，需要更新信源 URL 或允许重定向" };
    }
    if (code === "502" || code === "503" || code === "504") {
      return { key: `http-${code}`, label: `HTTP ${code} 服务错误`, detail: "上游服务临时不可用，通常可稍后重试" };
    }
    return { key: `http-${code}`, label: `HTTP ${code}`, detail: "目标站点返回非成功状态码" };
  }
  if (lower.includes("ssl") || lower.includes("tls") || lower.includes("unexpected_eof")) {
    return { key: "tls-ssl", label: "TLS/SSL 连接中断", detail: "HTTPS 连接提前断开，可能是网络或服务端 TLS 问题" };
  }
  const fallback = normalized.length > 72 ? `${normalized.slice(0, 69)}...` : normalized;
  return { key: fallback, label: fallback, detail: "未分类运行错误" };
}

function summarizeFailures(runs: FetchRun[]): FailureSummary[] {
  const groups = new Map<string, FailureSummary>();
  runs.forEach((run) => {
    const reason = runFailureReason(run);
    const classified = classifyFailureReason(reason);
    const source = run.source_id ?? `运行 #${run.id}`;
    const latestTime = runTime(run);
    const existing = groups.get(classified.key);
    if (existing === undefined) {
      groups.set(classified.key, {
        key: classified.key,
        label: classified.label,
        detail: classified.detail,
        count: 1,
        sources: [source],
        reasons: [reason],
        latestTime
      });
      return;
    }
    existing.count += 1;
    if (!existing.sources.includes(source)) {
      existing.sources.push(source);
    }
    if (!existing.reasons.includes(reason)) {
      existing.reasons.push(reason);
    }
    if (latestTime > existing.latestTime) {
      existing.latestTime = latestTime;
    }
  });
  return Array.from(groups.values()).sort((a, b) => b.count - a.count || b.latestTime.localeCompare(a.latestTime));
}

interface InfoRowProps {
  title: string;
  meta?: string;
  detail?: string;
  badgeStatus?: Status;
  sideLabel?: string;
}

function InfoRow({ title, meta, detail, badgeStatus, sideLabel }: InfoRowProps) {
  return (
    <div className="info-row" title={[title, meta, detail].filter(Boolean).join("\n")}>
      <div className="info-main">
        <strong>{title}</strong>
        {meta && <span>{meta}</span>}
        {detail && <small>{detail}</small>}
      </div>
      {badgeStatus ? <StatusBadge status={badgeStatus} /> : sideLabel ? <b>{sideLabel}</b> : null}
    </div>
  );
}

export function OverviewPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sources, setSources] = useState<SourceProfile[]>([]);
  const [runs, setRuns] = useState<FetchRun[]>([]);
  const [queue, setQueue] = useState<IngestTask[]>([]);
  const [wikiMetrics, setWikiMetrics] = useState<WikiMetricsResponse | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    let cancelled = false;

    Promise.all([getHealth(), getSources(), getRuns(), getQueue(), getWikiMetrics()])
      .then(([nextHealth, nextSources, nextRuns, nextQueue, nextWikiMetrics]) => {
        if (cancelled) {
          return;
        }
        setHealth(nextHealth);
        setSources(nextSources);
        setRuns(nextRuns);
        setQueue(nextQueue);
        setWikiMetrics(nextWikiMetrics);
        setError("");
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "加载运行状态失败");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleRefreshValidation() {
    setValidating(true);
    setNotice("");
    setError("");
    try {
      const validation = await validateWiki(undefined);
      const nextWikiMetrics = await getWikiMetrics();
      setWikiMetrics(nextWikiMetrics);
      setNotice(`Wiki 校验${validation.status === "succeeded" ? "通过" : "失败"}`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "刷新 wiki 校验失败");
    } finally {
      setValidating(false);
    }
  }

  const trendData = useMemo(() => summarizeTrend(runs), [runs]);
  const scheduledSources = sources.filter((source) => source.enabled && source.schedule).slice(0, 6);
  const authWarnings = sources.filter((source) => source.auth_required && source.auth_state !== "ready");
  const failedRuns = runs.filter((run) => run.status === "failed" || (run.failed_count ?? 0) > 0).slice(0, 6);
  const sourceTypes = new Set(sources.map((source) => source.type)).size;
  const pendingCount = statusCount(queue, "pending");
  const runningCount = statusCount(queue, "running");
  const failedCount = statusCount(queue, "failed");
  const recentRuns = runs.slice(0, 6);
  const failureSummaries = summarizeFailures(failedRuns);

  return (
    <section className="page-section" aria-labelledby="overview-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">运行状态</p>
          <h1 id="overview-title">运维控制台</h1>
        </div>
        <StatusBadge status={statusForHealth(health, error)} />
      </div>

      {(error || notice) && <div className={error ? "warning" : "notice"}>{error || notice}</div>}

      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">运行健康</span>
          <strong>{health?.status ?? (loading ? "加载中" : "未知")}</strong>
          <span className="metric-help">
            {health ? `${health.bind_host}:${health.bind_port}` : loading ? "正在读取后端健康状态" : "暂无健康状态"}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">待处理入库</span>
          <strong>{queue.length}</strong>
          <span className="metric-help">
            {queue.length === 0 ? "暂无待处理任务" : `${pendingCount} 个待审批，${runningCount} 个运行中，${failedCount} 个失败`}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">来源覆盖</span>
          <strong>{sources.length === 0 ? "0 类" : `${sourceTypes} 类`}</strong>
          <span className="metric-help">
            {sources.length === 0 ? "暂无来源订阅" : `${sources.length} 个来源，${sources.filter((source) => source.enabled).length} 个启用`}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Wiki 资料</span>
          <strong>{wikiMetrics ? `${wikiMetrics.counts.wiki_page_count} 页` : loading ? "加载中" : "未知"}</strong>
          <span className="metric-help">
            {wikiMetrics
              ? `${wikiMetrics.counts.domain_count} 个 domain，${wikiMetrics.counts.raw_file_count} 个 raw 文件`
              : "正在读取 wiki 资料数量"}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Wiki 占用空间</span>
          <strong>{sizeLabel(wikiMetrics?.sizes.total_bytes)}</strong>
          {wikiMetrics ? (
            <span className="metric-breakdown" aria-label="Wiki 占用空间明细">
              <span>
                <span>wiki</span>
                <strong>{sizeLabel(wikiMetrics.sizes.wiki_bytes)}</strong>
              </span>
              <span>
                <span>raw</span>
                <strong>{sizeLabel(wikiMetrics.sizes.raw_bytes)}</strong>
              </span>
              <span>
                <span>其他</span>
                <strong>{sizeLabel(otherWikiBytes(wikiMetrics))}</strong>
              </span>
            </span>
          ) : (
            <span className="metric-help">正在读取 wiki 占用空间</span>
          )}
        </div>
        <div className="metric-card">
          <span className="metric-label">Wiki 健康度</span>
          <strong>{wikiMetrics ? `${wikiMetrics.health.score} 分` : loading ? "加载中" : "未知"}</strong>
          <span className="metric-help">
            {wikiMetrics
              ? `${wikiMetrics.health.summary}，最近校验：${wikiMetrics.health.latest_validation_status ?? "未校验"}`
              : "最近校验和运行状态汇总"}
          </span>
        </div>
      </div>

      <div className="panel-grid">
        <div className="work-panel">
          <h2>
            <RefreshCw aria-hidden="true" size={17} />
            Wiki 监控
          </h2>
          {wikiMetrics === null ? (
            <div className="empty-state">暂无 wiki 指标</div>
          ) : (
            <>
              <div className="info-list">
                <InfoRow
                  title="最近校验"
                  meta={wikiMetrics.health.summary}
                  detail={`时间：${timeLabel(wikiMetrics.health.latest_validation_at ?? undefined)}`}
                  badgeStatus={coerceStatus(wikiMetrics.health.latest_validation_status ?? "pending")}
                />
                <InfoRow
                  title="待处理/失败"
                  meta={`${wikiMetrics.health.pending_task_count} 个待处理`}
                  detail={`${wikiMetrics.health.failed_task_count} 个失败任务，${wikiMetrics.health.failed_run_count} 个失败运行`}
                  badgeStatus={
                    wikiMetrics.health.failed_task_count > 0 || wikiMetrics.health.failed_run_count > 0 ? "failed" : "ready"
                  }
                />
              </div>
              <button
                className="icon-button panel-action"
                type="button"
                aria-label="刷新 wiki 校验"
                onClick={handleRefreshValidation}
                disabled={validating}
              >
                <RefreshCw aria-hidden="true" size={16} />
                {validating ? "校验中" : "刷新校验"}
              </button>
            </>
          )}
        </div>

        <div className="work-panel">
          <h2>
            <CalendarClock aria-hidden="true" size={17} />
            下一批计划抓取
          </h2>
          <div className="compact-list">
            {scheduledSources.length === 0 ? (
              <div className="empty-state">暂无计划抓取</div>
            ) : (
              scheduledSources.map((source) => (
                <InfoRow
                  key={source.id}
                  title={source.name}
                  meta={`${source.type} · ${source.target_domain}`}
                  detail={source.auto_ingest ? "自动入库已开启" : "仅抓取，需人工入库"}
                  sideLabel={scheduleLabel(source.schedule)}
                />
              ))
            )}
          </div>
        </div>

        <div className="work-panel">
          <h2>
            <ShieldAlert aria-hidden="true" size={17} />
            认证告警
          </h2>
          {authWarnings.length === 0 ? (
            <div className="empty-state">暂无认证告警</div>
          ) : (
            <div className="info-list">
              {authWarnings.map((source) => (
                <InfoRow
                  key={source.id}
                  title={source.name}
                  meta={`${source.type} · ${source.target_domain}`}
                  detail={`当前：${source.auth_state}`}
                  badgeStatus={coerceStatus(source.auth_state)}
                />
              ))}
            </div>
          )}
        </div>

        <div className="work-panel">
          <h2>
            <AlertTriangle aria-hidden="true" size={17} />
            运行失败
          </h2>
          {failedRuns.length === 0 ? (
            <div className="empty-state">暂无运行失败记录</div>
          ) : (
            <div className="failure-list">
              {failureSummaries.map((failure) => (
                <div className="failure-row" key={failure.key} title={failure.reasons.slice(0, 3).join("\n\n")}>
                  <div>
                    <strong>{failure.label}</strong>
                    <span>{failure.detail}</span>
                    <small>
                      {failure.sources.slice(0, 3).join("、")}，最近 {timeLabel(failure.latestTime)}
                    </small>
                  </div>
                  <b>{failure.count} 次</b>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="work-panel">
          <h2>
            <GitCommit aria-hidden="true" size={17} />
            最近抓取运行
          </h2>
          {recentRuns.length === 0 ? (
            <div className="empty-state">暂无抓取运行记录</div>
          ) : (
            <div className="info-list">
              {recentRuns.map((run) => (
                <InfoRow
                  key={run.id}
                  title={run.source_id ?? `运行 #${run.id}`}
                  meta={runCountLabel(run)}
                  detail={`完成：${timeLabel(runTime(run))}`}
                  badgeStatus={coerceStatus(run.status)}
                />
              ))}
            </div>
          )}
        </div>

        <div className="work-panel">
          <h2>失败原因分布</h2>
          {failureSummaries.length === 0 ? (
            <div className="empty-state">暂无失败原因数据</div>
          ) : (
            <div className="failure-list compact">
              {failureSummaries.map((failure) => (
                <div className="failure-row" key={failure.key} title={failure.reasons.slice(0, 3).join("\n\n")}>
                  <div>
                    <strong>{failure.label}</strong>
                    <span>{failure.sources.length} 个来源：{failure.sources.slice(0, 3).join("、")}</span>
                  </div>
                  <b>{failure.count} 次</b>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="work-panel chart-panel">
        <h2>抓取趋势</h2>
        <TrendChart data={trendData} />
      </div>
    </section>
  );
}
