import { AlertTriangle, CalendarClock, GitCommit, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getHealth, getQueue, getRuns, getSources } from "../api";
import { TrendChart, type TrendPoint } from "../components/TrendChart";
import { StatusBadge } from "../components/StatusBadge";
import type { FetchRun, HealthResponse, IngestTask, SourceProfile, Status } from "../types";

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

export function OverviewPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sources, setSources] = useState<SourceProfile[]>([]);
  const [runs, setRuns] = useState<FetchRun[]>([]);
  const [queue, setQueue] = useState<IngestTask[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    Promise.all([getHealth(), getSources(), getRuns(), getQueue()])
      .then(([nextHealth, nextSources, nextRuns, nextQueue]) => {
        if (cancelled) {
          return;
        }
        setHealth(nextHealth);
        setSources(nextSources);
        setRuns(nextRuns);
        setQueue(nextQueue);
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

  const trendData = useMemo(() => summarizeTrend(runs), [runs]);
  const scheduledSources = sources.filter((source) => source.enabled && source.schedule).slice(0, 6);
  const authWarnings = sources.filter((source) => source.auth_required && source.auth_state !== "ready");
  const validationFailures = runs.filter((run) => run.status === "failed" || (run.failed_count ?? 0) > 0).slice(0, 6);
  const sourceTypes = new Set(sources.map((source) => source.type)).size;
  const pendingCount = statusCount(queue, "pending");
  const runningCount = statusCount(queue, "running");
  const failedCount = statusCount(queue, "failed");
  const recentRuns = runs.slice(0, 6);
  const failureReasons = validationFailures
    .map((run) => run.failure_reason ?? `运行 #${run.id} 失败`)
    .filter((reason) => reason.trim() !== "");

  return (
    <section className="page-section" aria-labelledby="overview-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">运行状态</p>
          <h1 id="overview-title">运维控制台</h1>
        </div>
        <StatusBadge status={statusForHealth(health, error)} />
      </div>

      {error && <div className="warning">{error}</div>}

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
      </div>

      <div className="panel-grid">
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
                <div className="list-row" key={source.id}>
                  <span>{source.name}</span>
                  <strong>{source.schedule}</strong>
                  <span>{source.target_domain}</span>
                </div>
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
            <ul className="plain-list">
              {authWarnings.map((source) => (
                <li key={source.id}>
                  {source.name}：{source.auth_state}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="work-panel">
          <h2>
            <AlertTriangle aria-hidden="true" size={17} />
            校验失败
          </h2>
          {validationFailures.length === 0 ? (
            <div className="empty-state">暂无校验失败记录</div>
          ) : (
            <ul className="plain-list">
              {validationFailures.map((run) => (
                <li key={run.id}>
                  {run.source_id ?? `运行 #${run.id}`}：{run.failure_reason ?? run.status}
                </li>
              ))}
            </ul>
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
            <ul className="plain-list">
              {recentRuns.map((run) => (
                <li key={run.id}>
                  {run.source_id ?? `运行 #${run.id}`}：{run.status}，{timeLabel(runTime(run))}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="work-panel">
          <h2>失败原因分布</h2>
          {failureReasons.length === 0 ? (
            <div className="empty-state">暂无失败原因数据</div>
          ) : (
            <ul className="plain-list">
              {failureReasons.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              ))}
            </ul>
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
