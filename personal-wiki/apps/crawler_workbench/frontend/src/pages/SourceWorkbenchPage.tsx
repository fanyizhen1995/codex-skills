import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getRuns, getSources } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { FetchRun, SourceProfile, Status } from "../types";

interface CoveragePoint {
  name: string;
  value: number;
}

interface TimelinePoint {
  label: string;
  runs: number;
  changed: number;
}

interface TopicPoint {
  topic: string;
  rss: number;
  github: number;
  arxiv: number;
  web: number;
}

interface FailurePoint {
  name: string;
  value: number;
  color: string;
}

const failureColors = ["#b04545", "#c17a2d", "#7a5c28", "#6b7280", "#4f7f9f"];

function statusForWorkbench(sources: SourceProfile[], runs: FetchRun[], error: string): Status {
  if (error) {
    return "failed";
  }
  if (sources.some((source) => source.auth_required && source.auth_state !== "ready")) {
    return "needs_auth_config";
  }
  if (runs.some((run) => run.status === "failed")) {
    return "failed";
  }
  return "trusted";
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

function summarizeCoverage(sources: SourceProfile[]): CoveragePoint[] {
  const counts = new Map<string, number>();
  sources.forEach((source) => counts.set(source.type, (counts.get(source.type) ?? 0) + 1));
  return Array.from(counts, ([name, value]) => ({ name, value })).sort((a, b) => a.name.localeCompare(b.name));
}

function summarizeTimeline(runs: FetchRun[]): TimelinePoint[] {
  return runs
    .slice(0, 12)
    .reverse()
    .map((run) => ({
      label: timeLabel(run.finished_at ?? run.started_at),
      runs: 1,
      changed: run.changed_count ?? 0
    }));
}

function summarizeTopics(sources: SourceProfile[]): TopicPoint[] {
  const byTopic = new Map<string, TopicPoint>();
  sources.forEach((source) => {
    const topic = source.topic || "未分类";
    const current = byTopic.get(topic) ?? { topic, rss: 0, github: 0, arxiv: 0, web: 0 };
    const type = source.type.toLowerCase();
    if (type === "rss" || type === "github" || type === "arxiv" || type === "web") {
      current[type] += 1;
    }
    byTopic.set(topic, current);
  });
  return Array.from(byTopic.values()).sort((a, b) => a.topic.localeCompare(b.topic));
}

function summarizeFailures(runs: FetchRun[]): FailurePoint[] {
  const counts = new Map<string, number>();
  runs.forEach((run) => {
    const failedCount = run.failed_count ?? (run.status === "failed" ? 1 : 0);
    if (failedCount <= 0) {
      return;
    }
    const reason = run.failure_reason ?? run.status ?? "失败";
    counts.set(reason, (counts.get(reason) ?? 0) + failedCount);
  });
  return Array.from(counts, ([name, value], index) => ({
    name,
    value,
    color: failureColors[index % failureColors.length]
  }));
}

export function SourceWorkbenchPage() {
  const [sources, setSources] = useState<SourceProfile[]>([]);
  const [runs, setRuns] = useState<FetchRun[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    Promise.all([getSources(), getRuns()])
      .then(([nextSources, nextRuns]) => {
        if (cancelled) {
          return;
        }
        setSources(nextSources);
        setRuns(nextRuns);
        setMessage("");
      })
      .catch((error) => {
        if (!cancelled) {
          setMessage(error instanceof Error ? error.message : "加载来源诊断数据失败");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const coverageData = useMemo(() => summarizeCoverage(sources), [sources]);
  const timelineData = useMemo(() => summarizeTimeline(runs), [runs]);
  const topicData = useMemo(() => summarizeTopics(sources), [sources]);
  const failureData = useMemo(() => summarizeFailures(runs), [runs]);

  return (
    <section className="page-section" aria-labelledby="source-workbench-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">来源诊断</p>
          <h1 id="source-workbench-title">来源工作台</h1>
        </div>
        <StatusBadge status={statusForWorkbench(sources, runs, message)} />
      </div>

      {message && <small role="status">{message}</small>}

      <div className="panel-grid">
        <div className="work-panel chart-panel">
          <h2>来源覆盖</h2>
          <div className="chart-frame">
            {coverageData.length === 0 ? (
              <div className="empty-state">暂无来源覆盖数据</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={coverageData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                  <CartesianGrid stroke="#e5ebef" strokeDasharray="3 3" />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} width={34} />
                  <Tooltip />
                  <Bar dataKey="value" name="来源数" fill="#2f6f73" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="work-panel chart-panel">
          <h2>抓取时间线</h2>
          <div className="chart-frame">
            {timelineData.length === 0 ? (
              <div className="empty-state">暂无抓取时间线数据</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timelineData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                  <CartesianGrid stroke="#e5ebef" strokeDasharray="3 3" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} width={34} />
                  <Tooltip />
                  <Line type="monotone" dataKey="runs" name="抓取" stroke="#2f6f73" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="changed" name="变更" stroke="#7a5c28" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="work-panel chart-panel">
          <h2>主题热力</h2>
          <div className="chart-frame">
            {topicData.length === 0 ? (
              <div className="empty-state">暂无主题热力数据</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topicData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                  <CartesianGrid stroke="#e5ebef" strokeDasharray="3 3" />
                  <XAxis dataKey="topic" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} width={34} />
                  <Tooltip />
                  <Bar dataKey="rss" name="RSS" stackId="topic" fill="#2f6f73" />
                  <Bar dataKey="github" name="GitHub" stackId="topic" fill="#4f7f9f" />
                  <Bar dataKey="arxiv" name="Arxiv" stackId="topic" fill="#7a5c28" />
                  <Bar dataKey="web" name="Web" stackId="topic" fill="#b04545" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="work-panel chart-panel">
          <h2>失败原因分布</h2>
          <div className="chart-frame">
            {failureData.length === 0 ? (
              <div className="empty-state">暂无失败原因数据</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip />
                  <Pie data={failureData} dataKey="value" nameKey="name" outerRadius={82} label>
                    {failureData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
